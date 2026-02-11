"""Background notification service for print status changes.

Polls the Formlabs Web API for status changes and sends Telegram alerts.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "notifications.db"

# Statuses that trigger a notification
NOTIFY_STATUSES = {"FINISHED", "ERROR", "ABORTED"}
ACTIVE_STATUSES = {"PRINTING", "PREPRINT", "PREHEAT", "PRECOAT", "POSTCOAT"}


class NotificationDB:
    """SQLite storage for notification subscriptions and tracked print states."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id INTEGER NOT NULL,
                    printer_serial TEXT DEFAULT '*',
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, printer_serial)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_prints (
                    print_guid TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    printer_serial TEXT NOT NULL,
                    print_name TEXT DEFAULT '',
                    last_status TEXT DEFAULT '',
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def subscribe(self, user_id: int, printer_serial: str = "*") -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO subscriptions (user_id, printer_serial, enabled) VALUES (?, ?, 1)",
                (user_id, printer_serial),
            )

    def unsubscribe(self, user_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))

    def is_subscribed(self, user_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT enabled FROM subscriptions WHERE user_id=? AND enabled=1 LIMIT 1",
                (user_id,),
            ).fetchone()
        return row is not None

    def get_subscribers(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT user_id, printer_serial FROM subscriptions WHERE enabled=1"
            ).fetchall()
        return [{"user_id": r[0], "printer_serial": r[1]} for r in rows]

    def get_tracked_status(self, print_guid: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT last_status FROM tracked_prints WHERE print_guid=?",
                (print_guid,),
            ).fetchone()
        return row[0] if row else None

    def update_tracked_print(
        self, print_guid: str, user_id: int, printer_serial: str, name: str, status: str
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO tracked_prints
                   (print_guid, user_id, printer_serial, print_name, last_status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (print_guid, user_id, printer_serial, name, status, datetime.now().isoformat()),
            )

    def cleanup_old_prints(self, days: int = 7) -> None:
        cutoff = (datetime.now().replace(hour=0, minute=0, second=0) - __import__("datetime").timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tracked_prints WHERE updated_at < ?", (cutoff,))


class NotificationService:
    """Background polling service for print notifications."""

    def __init__(
        self,
        send_message: Callable[[int, str], Awaitable[None]],
        get_web_client: Callable[[int], Any],
        db: NotificationDB | None = None,
        poll_interval: int = 60,
    ):
        self.send_message = send_message
        self.get_web_client = get_web_client
        self.db = db or NotificationDB()
        self.poll_interval = poll_interval
        self._running = False

    async def start(self) -> None:
        """Start the polling loop."""
        self._running = True
        logger.info("Notification service started (interval=%ds)", self.poll_interval)
        while self._running:
            try:
                await self._poll_all()
            except Exception as e:
                logger.error("Notification poll error: %s", e)
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False

    async def _poll_all(self) -> None:
        subscribers = self.db.get_subscribers()
        user_ids = set(s["user_id"] for s in subscribers)

        for user_id in user_ids:
            try:
                await self._check_user(user_id)
            except Exception as e:
                logger.error("Error checking user %d: %s", user_id, e)

    async def _check_user(self, user_id: int) -> None:
        client = self.get_web_client(user_id)
        if not client or not client.is_authenticated:
            return

        # Get active and recently finished prints
        for status in list(ACTIVE_STATUSES) + list(NOTIFY_STATUSES):
            try:
                result = client.list_prints(status=status, per_page=20)
                prints_list = result.get("results", []) if isinstance(result, dict) else result
            except Exception:
                continue

            for p in prints_list:
                guid = p.get("guid", "")
                if not guid:
                    continue

                new_status = (p.get("status", "") or "").upper()
                old_status = self.db.get_tracked_status(guid)
                printer = p.get("printer", "unknown")
                name = p.get("name", "Unknown print")

                self.db.update_tracked_print(guid, user_id, printer, name, new_status)

                if old_status and old_status != new_status and new_status in NOTIFY_STATUSES:
                    await self._notify(user_id, name, printer, old_status, new_status, p)

    async def _notify(
        self, user_id: int, name: str, printer: str, old_status: str, new_status: str, print_data: dict
    ) -> None:
        if new_status == "FINISHED":
            icon = "✅"
            verb = "completed"
        elif new_status == "ERROR":
            icon = "❌"
            verb = "failed"
        elif new_status == "ABORTED":
            icon = "🚫"
            verb = "was cancelled"
        else:
            icon = "ℹ️"
            verb = f"changed to {new_status}"

        volume = print_data.get("volume_ml", 0) or 0
        duration_ms = print_data.get("elapsed_duration_ms", 0) or 0
        duration_str = ""
        if duration_ms > 0:
            hours = duration_ms // 3_600_000
            minutes = (duration_ms % 3_600_000) // 60_000
            duration_str = f"\nDuration: {hours}h {minutes}m"

        msg = (
            f"{icon} *Print {verb}!*\n\n"
            f"Name: {name}\n"
            f"Printer: {printer}\n"
            f"Status: {old_status} → {new_status}"
            f"{duration_str}"
        )
        if volume > 0:
            msg += f"\nResin: {volume:.1f} ml"

        try:
            await self.send_message(user_id, msg)
        except Exception as e:
            logger.error("Failed to send notification to %d: %s", user_id, e)
