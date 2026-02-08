"""
Resin Prophet - Resin Depletion Prediction System

Predicts when resin cartridges/tanks will run out based on 
print queue, historical usage, and current levels.

Author: Kim (OpenClaw)
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ResinCartridge:
    """Represents a resin cartridge or tank."""
    id: str  # Unique identifier
    material_code: str  # e.g., "FLGPGR05"
    material_name: str  # e.g., "Grey V5"
    initial_volume_ml: float  # Initial capacity
    current_volume_ml: float  # Remaining
    printer_id: str | None = None  # Which printer it's in
    user_id: int | None = None  # Telegram user ID (for multi-tenant)
    installed_date: datetime | None = None
    last_updated: datetime | None = None
    status: Literal["active", "low", "critical", "empty", "removed"] = "active"
    
    @property
    def percent_remaining(self) -> float:
        """Calculate percentage remaining."""
        if self.initial_volume_ml <= 0:
            return 0.0
        return (self.current_volume_ml / self.initial_volume_ml) * 100
    
    @property
    def is_low(self) -> bool:
        """Check if resin is low (< 20%)."""
        return self.percent_remaining < 20.0
    
    @property
    def is_critical(self) -> bool:
        """Check if resin is critically low (< 10%)."""
        return self.percent_remaining < 10.0


@dataclass
class PrintJob:
    """Represents a print job for resin tracking."""
    id: str
    material_code: str
    estimated_resin_ml: float
    status: Literal["queued", "printing", "completed", "failed", "cancelled"]
    user_id: int
    actual_resin_ml: float | None = None
    printer_id: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class ResinPrediction:
    """Prediction result for resin depletion."""
    cartridge_id: str
    material_name: str
    current_volume_ml: float
    percent_remaining: float
    status: str
    
    # Predictions
    estimated_prints_remaining: int
    estimated_days_remaining: float | None
    estimated_depletion_date: datetime | None
    
    # Alerts
    alert_level: Literal["none", "info", "warning", "critical"]
    alert_message: str
    
    # Queue impact
    queued_jobs_count: int
    queued_jobs_volume_ml: float


# ============================================================================
# Database Manager
# ============================================================================

class ResinDatabase:
    """SQLite database for resin tracking."""
    
    def __init__(self, db_path: str | Path = "resin_prophet.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resin_cartridges (
                    id TEXT PRIMARY KEY,
                    material_code TEXT NOT NULL,
                    material_name TEXT NOT NULL,
                    initial_volume_ml REAL NOT NULL,
                    current_volume_ml REAL NOT NULL,
                    printer_id TEXT,
                    user_id INTEGER,
                    installed_date TEXT,
                    last_updated TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS print_jobs (
                    id TEXT PRIMARY KEY,
                    material_code TEXT NOT NULL,
                    estimated_resin_ml REAL NOT NULL,
                    actual_resin_ml REAL,
                    status TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    printer_id TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resin_usage_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    material_code TEXT NOT NULL,
                    user_id INTEGER,
                    volume_used_ml REAL NOT NULL,
                    print_count INTEGER NOT NULL
                )
            """)
            
            conn.commit()
    
    def add_cartridge(self, cartridge: ResinCartridge):
        """Add or update a cartridge."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO resin_cartridges 
                (id, material_code, material_name, initial_volume_ml, current_volume_ml,
                 printer_id, user_id, installed_date, last_updated, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cartridge.id,
                cartridge.material_code,
                cartridge.material_name,
                cartridge.initial_volume_ml,
                cartridge.current_volume_ml,
                cartridge.printer_id,
                cartridge.user_id,
                cartridge.installed_date.isoformat() if cartridge.installed_date else None,
                datetime.now().isoformat(),
                cartridge.status
            ))
            conn.commit()
    
    def get_cartridge(self, cartridge_id: str) -> ResinCartridge | None:
        """Get a cartridge by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM resin_cartridges WHERE id = ?",
                (cartridge_id,)
            ).fetchone()
            
            if row:
                return self._row_to_cartridge(row)
            return None
    
    def get_user_cartridges(self, user_id: int) -> list[ResinCartridge]:
        """Get all cartridges for a user."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM resin_cartridges WHERE user_id = ? AND status != 'removed'",
                (user_id,)
            ).fetchall()
            
            return [self._row_to_cartridge(row) for row in rows]
    
    def update_cartridge_volume(self, cartridge_id: str, new_volume_ml: float):
        """Update cartridge volume."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE resin_cartridges 
                SET current_volume_ml = ?, last_updated = ?
                WHERE id = ?
            """, (new_volume_ml, datetime.now().isoformat(), cartridge_id))
            conn.commit()
    
    def add_print_job(self, job: PrintJob):
        """Add a print job."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO print_jobs
                (id, material_code, estimated_resin_ml, actual_resin_ml, status,
                 user_id, printer_id, created_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.material_code,
                job.estimated_resin_ml,
                job.actual_resin_ml,
                job.status,
                job.user_id,
                job.printer_id,
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None
            ))
            conn.commit()
    
    def get_queued_jobs(self, user_id: int, material_code: str | None = None) -> list[PrintJob]:
        """Get queued jobs for a user."""
        with sqlite3.connect(self.db_path) as conn:
            if material_code:
                rows = conn.execute("""
                    SELECT * FROM print_jobs 
                    WHERE user_id = ? AND material_code = ? AND status IN ('queued', 'printing')
                    ORDER BY created_at
                """, (user_id, material_code)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM print_jobs 
                    WHERE user_id = ? AND status IN ('queued', 'printing')
                    ORDER BY created_at
                """, (user_id,)).fetchall()
            
            return [self._row_to_job(row) for row in rows]
    
    def get_usage_history(
        self, 
        user_id: int, 
        material_code: str, 
        days: int = 30
    ) -> list[dict]:
        """Get resin usage history."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT date, SUM(volume_used_ml) as total_volume, SUM(print_count) as total_prints
                FROM resin_usage_history
                WHERE user_id = ? AND material_code = ? AND date > ?
                GROUP BY date
                ORDER BY date
            """, (user_id, material_code, since)).fetchall()
            
            return [
                {"date": row[0], "volume_ml": row[1], "prints": row[2]}
                for row in rows
            ]
    
    def record_usage(self, user_id: int, material_code: str, volume_ml: float):
        """Record daily usage."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if entry exists for today
            existing = conn.execute(
                "SELECT id, volume_used_ml, print_count FROM resin_usage_history WHERE date = ? AND user_id = ? AND material_code = ?",
                (today, user_id, material_code)
            ).fetchone()
            
            if existing:
                # Update
                conn.execute("""
                    UPDATE resin_usage_history 
                    SET volume_used_ml = ?, print_count = ?
                    WHERE id = ?
                """, (existing[1] + volume_ml, existing[2] + 1, existing[0]))
            else:
                # Insert
                conn.execute("""
                    INSERT INTO resin_usage_history (date, material_code, user_id, volume_used_ml, print_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (today, material_code, user_id, volume_ml, 1))
            
            conn.commit()
    
    def _row_to_cartridge(self, row) -> ResinCartridge:
        """Convert database row to ResinCartridge."""
        return ResinCartridge(
            id=row[0],
            material_code=row[1],
            material_name=row[2],
            initial_volume_ml=row[3],
            current_volume_ml=row[4],
            printer_id=row[5],
            user_id=row[6],
            installed_date=datetime.fromisoformat(row[7]) if row[7] else None,
            last_updated=datetime.fromisoformat(row[8]) if row[8] else None,
            status=row[9]
        )
    
    def _row_to_job(self, row) -> PrintJob:
        """Convert database row to PrintJob."""
        return PrintJob(
            id=row[0],
            material_code=row[1],
            estimated_resin_ml=row[2],
            actual_resin_ml=row[3],
            status=row[4],
            user_id=row[5],
            printer_id=row[6],
            created_at=datetime.fromisoformat(row[7]),
            started_at=datetime.fromisoformat(row[8]) if row[8] else None,
            completed_at=datetime.fromisoformat(row[9]) if row[9] else None
        )


# ============================================================================
# Prediction Engine
# ============================================================================

class ResinProphet:
    """Main prediction engine for resin depletion."""
    
    # Standard cartridge sizes
    CARTRIDGE_SIZES = {
        "standard": 1000.0,  # 1L
        "tank": 2000.0,      # 2L for larger tanks
    }
    
    # Alert thresholds
    ALERT_THRESHOLDS = {
        "info": 30.0,      # 30% remaining
        "warning": 20.0,   # 20% remaining
        "critical": 10.0,  # 10% remaining
    }
    
    def __init__(self, db_path: str | Path = "resin_prophet.db"):
        self.db = ResinDatabase(db_path)
    
    def register_cartridge(
        self,
        cartridge_id: str,
        material_code: str,
        material_name: str,
        user_id: int,
        printer_id: str | None = None,
        initial_volume_ml: float = 1000.0,
        current_volume_ml: float | None = None
    ) -> ResinCartridge:
        """Register a new resin cartridge."""
        
        cartridge = ResinCartridge(
            id=cartridge_id,
            material_code=material_code,
            material_name=material_name,
            initial_volume_ml=initial_volume_ml,
            current_volume_ml=current_volume_ml or initial_volume_ml,
            printer_id=printer_id,
            user_id=user_id,
            installed_date=datetime.now(),
            last_updated=datetime.now(),
            status="active"
        )
        
        self.db.add_cartridge(cartridge)
        return cartridge
    
    def predict(self, cartridge_id: str, user_id: int) -> ResinPrediction | None:
        """Generate prediction for a cartridge."""
        
        cartridge = self.db.get_cartridge(cartridge_id)
        if not cartridge:
            return None
        
        # Check user access
        if cartridge.user_id != user_id:
            return None
        
        # Get queued jobs for this material
        queued_jobs = self.db.get_queued_jobs(user_id, cartridge.material_code)
        queued_volume = sum(job.estimated_resin_ml for job in queued_jobs)
        
        # Calculate prints remaining
        avg_print_volume = self._get_average_print_volume(user_id, cartridge.material_code)
        if avg_print_volume > 0:
            prints_remaining = int(cartridge.current_volume_ml / avg_print_volume)
        else:
            prints_remaining = 0
        
        # Calculate days remaining based on historical usage
        days_remaining = self._calculate_days_remaining(
            user_id, 
            cartridge.material_code, 
            cartridge.current_volume_ml
        )
        
        # Calculate depletion date
        if days_remaining is not None:
            depletion_date = datetime.now() + timedelta(days=days_remaining)
        else:
            depletion_date = None
        
        # Determine alert level
        percent = cartridge.percent_remaining
        if percent < self.ALERT_THRESHOLDS["critical"]:
            alert_level = "critical"
            alert_message = f"🚨 CRITICAL: {cartridge.material_name} at {percent:.1f}%. Order now!"
        elif percent < self.ALERT_THRESHOLDS["warning"]:
            alert_level = "warning"
            alert_message = f"⚠️ WARNING: {cartridge.material_name} at {percent:.1f}%. Plan reorder."
        elif percent < self.ALERT_THRESHOLDS["info"]:
            alert_level = "info"
            alert_message = f"ℹ️ {cartridge.material_name} at {percent:.1f}%. Monitor levels."
        else:
            alert_level = "none"
            alert_message = f"✅ {cartridge.material_name} level OK ({percent:.1f}%)"
        
        # Update status
        if percent < 5.0:
            cartridge.status = "empty"
        elif percent < 10.0:
            cartridge.status = "critical"
        elif percent < 20.0:
            cartridge.status = "low"
        else:
            cartridge.status = "active"
        
        self.db.add_cartridge(cartridge)
        
        return ResinPrediction(
            cartridge_id=cartridge.id,
            material_name=cartridge.material_name,
            current_volume_ml=cartridge.current_volume_ml,
            percent_remaining=percent,
            status=cartridge.status,
            estimated_prints_remaining=prints_remaining,
            estimated_days_remaining=days_remaining,
            estimated_depletion_date=depletion_date,
            alert_level=alert_level,
            alert_message=alert_message,
            queued_jobs_count=len(queued_jobs),
            queued_jobs_volume_ml=queued_volume
        )
    
    def get_all_predictions(self, user_id: int) -> list[ResinPrediction]:
        """Get predictions for all user's cartridges."""
        cartridges = self.db.get_user_cartridges(user_id)
        predictions = []
        
        for cartridge in cartridges:
            pred = self.predict(cartridge.id, user_id)
            if pred:
                predictions.append(pred)
        
        # Sort by alert level (critical first)
        alert_order = {"critical": 0, "warning": 1, "info": 2, "none": 3}
        predictions.sort(key=lambda p: alert_order.get(p.alert_level, 4))
        
        return predictions
    
    def consume_resin(
        self, 
        cartridge_id: str, 
        volume_ml: float, 
        user_id: int
    ) -> bool:
        """Record resin consumption from a print."""
        
        cartridge = self.db.get_cartridge(cartridge_id)
        if not cartridge or cartridge.user_id != user_id:
            return False
        
        # Update volume
        new_volume = max(0.0, cartridge.current_volume_ml - volume_ml)
        self.db.update_cartridge_volume(cartridge_id, new_volume)
        
        # Record usage
        self.db.record_usage(user_id, cartridge.material_code, volume_ml)
        
        return True
    
    def _get_average_print_volume(self, user_id: int, material_code: str) -> float:
        """Calculate average resin per print from history."""
        history = self.db.get_usage_history(user_id, material_code, days=30)
        
        if not history:
            # Default estimates by material
            defaults = {
                "FLGPGR05": 45.0,  # Grey V5
                "FLGPBK05": 45.0,  # Black V5
                "FLGPCL05": 45.0,  # Clear V5
                "FLTO2K02": 60.0,  # Tough 2000
                "FLDUCL21": 50.0,  # Durable
            }
            return defaults.get(material_code, 50.0)
        
        total_volume = sum(day["volume_ml"] for day in history)
        total_prints = sum(day["prints"] for day in history)
        
        if total_prints > 0:
            return total_volume / total_prints
        return 50.0
    
    def _calculate_days_remaining(
        self, 
        user_id: int, 
        material_code: str, 
        current_volume: float
    ) -> float | None:
        """Calculate estimated days until depletion."""
        
        history = self.db.get_usage_history(user_id, material_code, days=14)
        
        if not history:
            return None
        
        # Calculate daily usage rate
        total_volume = sum(day["volume_ml"] for day in history)
        days = len(history)
        
        if days > 0 and total_volume > 0:
            daily_usage = total_volume / days
            days_remaining = current_volume / daily_usage
            return days_remaining
        
        return None


# ============================================================================
# Command Handlers
# ============================================================================

def cmd_resin_status(user_id: int, prophet: ResinProphet | None = None) -> str:
    """Generate /resin status message."""
    
    if prophet is None:
        prophet = ResinProphet()
    
    predictions = prophet.get_all_predictions(user_id)
    
    if not predictions:
        return "📭 No resin cartridges registered.\nUse /resin_add to register a cartridge."
    
    lines = ["🧪 *Resin Status*\n", "=" * 30 + "\n"]
    
    for pred in predictions:
        # Emoji based on status
        emoji = {
            "critical": "🚨",
            "warning": "⚠️",
            "low": "🔶",
            "active": "✅"
        }.get(pred.status, "⬜")
        
        lines.append(f"{emoji} *{pred.material_name}*")
        lines.append(f"   {pred.percent_remaining:.1f}% remaining ({pred.current_volume_ml:.0f}ml)")
        
        if pred.estimated_days_remaining:
            lines.append(f"   ~{pred.estimated_days_remaining:.1f} days left")
        
        if pred.queued_jobs_count > 0:
            lines.append(f"   📋 {pred.queued_jobs_count} jobs queued ({pred.queued_jobs_volume_ml:.0f}ml)")
        
        lines.append("")
    
    return "\n".join(lines)


def cmd_resin_add(
    user_id: int,
    material_code: str,
    material_name: str,
    printer_id: str | None = None,
    prophet: ResinProphet | None = None
) -> str:
    """Handle /resin_add command."""
    
    if prophet is None:
        prophet = ResinProphet()
    
    cartridge_id = f"{material_code}_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    cartridge = prophet.register_cartridge(
        cartridge_id=cartridge_id,
        material_code=material_code,
        material_name=material_name,
        user_id=user_id,
        printer_id=printer_id
    )
    
    return (
        f"✅ Cartridge registered\n\n"
        f"ID: `{cartridge_id}`\n"
        f"Material: {material_name}\n"
        f"Volume: {cartridge.initial_volume_ml}ml\n"
        f"Status: {cartridge.status}"
    )


def cmd_resin_alert(user_id: int, prophet: ResinProphet | None = None) -> str:
    """Generate /resin_alert message (only low cartridges)."""
    
    if prophet is None:
        prophet = ResinProphet()
    
    predictions = prophet.get_all_predictions(user_id)
    
    # Filter to only alerts
    alerts = [p for p in predictions if p.alert_level in ["warning", "critical"]]
    
    if not alerts:
        return "✅ All resin levels OK. No alerts."
    
    lines = ["🚨 *Resin Alerts*\n", "=" * 30 + "\n"]
    
    for pred in alerts:
        lines.append(pred.alert_message)
        lines.append("")
    
    return "\n".join(lines)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example setup
    prophet = ResinProphet("./resin_test.db")
    user_id = 12345
    
    # Register cartridges
    print("Registering cartridges...")
    prophet.register_cartridge(
        cartridge_id="cart_001",
        material_code="FLGPGR05",
        material_name="Grey V5",
        user_id=user_id,
        printer_id="Form4-001",
        initial_volume_ml=1000.0,
        current_volume_ml=200.0  # Low for demo
    )
    
    prophet.register_cartridge(
        cartridge_id="cart_002",
        material_code="FLTO2K02",
        material_name="Tough 2000",
        user_id=user_id,
        printer_id="Form4-002",
        initial_volume_ml=1000.0,
        current_volume_ml=800.0  # OK level
    )
    
    # Simulate usage
    print("\nSimulating usage...")
    prophet.db.record_usage(user_id, "FLGPGR05", 45.0)
    prophet.db.record_usage(user_id, "FLGPGR05", 50.0)
    prophet.db.record_usage(user_id, "FLGPGR05", 42.0)
    
    # Get predictions
    print("\n" + cmd_resin_status(user_id, prophet))
    print("\n" + cmd_resin_alert(user_id, prophet))
