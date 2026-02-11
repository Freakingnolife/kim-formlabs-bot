"""Maintenance schedule tracking and reminders."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent.parent / "data" / "maintenance.db"

# Maintenance tasks with triggers
MAINTENANCE_TASKS = {
    "optical_window_clean": {
        "name": "Clean Optical Window",
        "interval_days": 14,
        "description": "Clean the optical window with PEC pads and IPA for best print quality.",
        "severity": "info",
    },
    "resin_tank_inspect": {
        "name": "Inspect Resin Tank",
        "interval_days": 30,
        "description": "Check tank for clouding, scratches, or cured resin particles.",
        "severity": "warning",
    },
    "build_platform_clean": {
        "name": "Clean Build Platform",
        "interval_days": 7,
        "description": "Remove any cured resin residue from the build platform surface.",
        "severity": "info",
    },
    "resin_filter": {
        "name": "Filter Resin",
        "interval_days": 30,
        "description": "Filter resin through a paint strainer to remove debris.",
        "severity": "info",
    },
    "firmware_check": {
        "name": "Check Firmware Updates",
        "interval_days": 30,
        "description": "Check for and apply printer firmware updates.",
        "severity": "info",
    },
}


class MaintenanceTracker:
    """Track maintenance schedules per printer."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    printer_serial TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_maintenance_user
                ON maintenance_log(user_id, printer_serial, task_id)
            """)

    def mark_done(
        self, user_id: int, printer_serial: str, task_id: str, notes: str = ""
    ) -> bool:
        """Mark a maintenance task as completed."""
        if task_id not in MAINTENANCE_TASKS:
            return False
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO maintenance_log (user_id, printer_serial, task_id, completed_at, notes) VALUES (?, ?, ?, ?, ?)",
                (user_id, printer_serial, task_id, datetime.now().isoformat(), notes),
            )
        return True

    def get_last_done(
        self, user_id: int, printer_serial: str, task_id: str
    ) -> datetime | None:
        """Get when a task was last completed."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT completed_at FROM maintenance_log WHERE user_id=? AND printer_serial=? AND task_id=? ORDER BY completed_at DESC LIMIT 1",
                (user_id, printer_serial, task_id),
            ).fetchone()
        if row:
            return datetime.fromisoformat(row[0])
        return None

    def get_due_tasks(
        self, user_id: int, printer_serial: str
    ) -> list[dict]:
        """Get all due/overdue maintenance tasks for a printer."""
        now = datetime.now()
        due = []
        for task_id, task in MAINTENANCE_TASKS.items():
            last = self.get_last_done(user_id, printer_serial, task_id)
            interval = timedelta(days=task["interval_days"])

            if last is None:
                days_overdue = task["interval_days"]
                status = "never_done"
            elif now - last > interval:
                days_overdue = (now - last).days - task["interval_days"]
                status = "overdue"
            else:
                days_until = (last + interval - now).days
                days_overdue = -days_until
                status = "ok"

            due.append({
                "task_id": task_id,
                "name": task["name"],
                "description": task["description"],
                "severity": task["severity"],
                "interval_days": task["interval_days"],
                "last_done": last.isoformat() if last else None,
                "status": status,
                "days_overdue": days_overdue,
            })

        due.sort(key=lambda d: d["days_overdue"], reverse=True)
        return due


def format_maintenance_status(
    tasks: list[dict], printer_serial: str
) -> str:
    """Format maintenance status as a Telegram message."""
    lines = [
        f"🔧 *Maintenance: {printer_serial}*",
        f"{'=' * 28}",
        "",
    ]

    overdue = [t for t in tasks if t["status"] in ("overdue", "never_done")]
    ok = [t for t in tasks if t["status"] == "ok"]

    if overdue:
        lines.append("*Overdue:*")
        for t in overdue:
            icon = "🔴" if t["severity"] == "warning" else "🟡"
            if t["status"] == "never_done":
                lines.append(f"  {icon} {t['name']} - Never done")
            else:
                lines.append(f"  {icon} {t['name']} - {t['days_overdue']}d overdue")
        lines.append("")

    if ok:
        lines.append("*Up to date:*")
        for t in ok:
            days_left = abs(t["days_overdue"])
            lines.append(f"  ✅ {t['name']} - due in {days_left}d")

    if not overdue:
        lines.append("✅ All maintenance up to date!")

    lines.append("")
    lines.append("Mark done: `/maintenance done <task_id> <printer>`")

    return "\n".join(lines)
