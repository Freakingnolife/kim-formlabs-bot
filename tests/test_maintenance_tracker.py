"""Tests for maintenance_tracker.py."""

import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_formlabs.maintenance_tracker import (
    MaintenanceTracker,
    MAINTENANCE_TASKS,
    format_maintenance_status,
)


class TestMaintenanceTracker:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.tmp.name)
        self.tracker = MaintenanceTracker(db_path=self.db_path)

    def teardown_method(self):
        self.db_path.unlink(missing_ok=True)

    def test_mark_done_valid_task(self):
        assert self.tracker.mark_done(1, "ABC", "optical_window_clean")

    def test_mark_done_invalid_task(self):
        assert not self.tracker.mark_done(1, "ABC", "nonexistent_task")

    def test_get_last_done_never(self):
        result = self.tracker.get_last_done(1, "ABC", "optical_window_clean")
        assert result is None

    def test_get_last_done_after_mark(self):
        self.tracker.mark_done(1, "ABC", "optical_window_clean")
        result = self.tracker.get_last_done(1, "ABC", "optical_window_clean")
        assert result is not None
        assert isinstance(result, datetime)

    def test_get_due_tasks_all_never_done(self):
        tasks = self.tracker.get_due_tasks(1, "ABC")
        assert len(tasks) == len(MAINTENANCE_TASKS)
        for t in tasks:
            assert t["status"] == "never_done"

    def test_get_due_tasks_after_completion(self):
        self.tracker.mark_done(1, "ABC", "optical_window_clean")
        tasks = self.tracker.get_due_tasks(1, "ABC")
        optical = next(t for t in tasks if t["task_id"] == "optical_window_clean")
        assert optical["status"] == "ok"

    def test_different_printers_isolated(self):
        self.tracker.mark_done(1, "ABC", "optical_window_clean")
        tasks = self.tracker.get_due_tasks(1, "DEF")
        optical = next(t for t in tasks if t["task_id"] == "optical_window_clean")
        assert optical["status"] == "never_done"

    def test_different_users_isolated(self):
        self.tracker.mark_done(1, "ABC", "optical_window_clean")
        tasks = self.tracker.get_due_tasks(2, "ABC")
        optical = next(t for t in tasks if t["task_id"] == "optical_window_clean")
        assert optical["status"] == "never_done"


class TestFormatMaintenanceStatus:
    def test_format_all_overdue(self):
        tasks = [
            {"task_id": "t1", "name": "Clean Optics", "status": "never_done", "severity": "warning", "days_overdue": 14, "description": ""},
        ]
        text = format_maintenance_status(tasks, "ABC123")
        assert "ABC123" in text
        assert "Overdue" in text

    def test_format_all_ok(self):
        tasks = [
            {"task_id": "t1", "name": "Clean Optics", "status": "ok", "severity": "info", "days_overdue": -5, "description": ""},
        ]
        text = format_maintenance_status(tasks, "ABC123")
        assert "up to date" in text.lower()
