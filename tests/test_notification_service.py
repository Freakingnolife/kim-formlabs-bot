"""Tests for notification_service.py."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_formlabs.notification_service import NotificationDB, NotificationService


class TestNotificationDB:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.tmp.name)
        self.db = NotificationDB(db_path=self.db_path)

    def teardown_method(self):
        self.db_path.unlink(missing_ok=True)

    def test_subscribe(self):
        self.db.subscribe(123)
        assert self.db.is_subscribed(123)

    def test_unsubscribe(self):
        self.db.subscribe(123)
        self.db.unsubscribe(123)
        assert not self.db.is_subscribed(123)

    def test_not_subscribed_by_default(self):
        assert not self.db.is_subscribed(999)

    def test_get_subscribers(self):
        self.db.subscribe(1)
        self.db.subscribe(2)
        subs = self.db.get_subscribers()
        user_ids = [s["user_id"] for s in subs]
        assert 1 in user_ids
        assert 2 in user_ids

    def test_subscribe_specific_printer(self):
        self.db.subscribe(123, "ABC123")
        subs = self.db.get_subscribers()
        assert any(s["printer_serial"] == "ABC123" for s in subs)

    def test_tracked_prints(self):
        self.db.update_tracked_print("guid-1", 123, "ABC", "test.stl", "PRINTING")
        status = self.db.get_tracked_status("guid-1")
        assert status == "PRINTING"

    def test_tracked_print_update(self):
        self.db.update_tracked_print("guid-1", 123, "ABC", "test.stl", "PRINTING")
        self.db.update_tracked_print("guid-1", 123, "ABC", "test.stl", "FINISHED")
        status = self.db.get_tracked_status("guid-1")
        assert status == "FINISHED"

    def test_tracked_print_not_found(self):
        status = self.db.get_tracked_status("nonexistent")
        assert status is None


class TestNotificationService:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.tmp.name)
        self.db = NotificationDB(db_path=self.db_path)
        self.send_message = AsyncMock()
        self.mock_client = MagicMock()
        self.mock_client.is_authenticated = True
        self.mock_client.list_prints.return_value = {"results": []}

        self.service = NotificationService(
            send_message=self.send_message,
            get_web_client=lambda uid: self.mock_client,
            db=self.db,
            poll_interval=1,
        )

    def teardown_method(self):
        self.db_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_notify_on_status_change(self):
        self.db.subscribe(123)
        # First, track as PRINTING
        self.db.update_tracked_print("guid-1", 123, "ABC", "test.stl", "PRINTING")

        # Now simulate FINISHED
        self.mock_client.list_prints.return_value = {
            "results": [
                {
                    "guid": "guid-1",
                    "name": "test.stl",
                    "printer": "ABC",
                    "status": "FINISHED",
                    "volume_ml": 10.0,
                    "elapsed_duration_ms": 3600000,
                }
            ]
        }

        await self.service._check_user(123)
        self.send_message.assert_called_once()
        msg = self.send_message.call_args[0][1]
        assert "completed" in msg.lower()

    @pytest.mark.asyncio
    async def test_no_notify_same_status(self):
        self.db.subscribe(123)
        self.db.update_tracked_print("guid-1", 123, "ABC", "test.stl", "PRINTING")

        self.mock_client.list_prints.return_value = {
            "results": [
                {"guid": "guid-1", "name": "test.stl", "printer": "ABC", "status": "PRINTING"}
            ]
        }

        await self.service._check_user(123)
        self.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_notify_unauthenticated(self):
        self.db.subscribe(123)
        self.mock_client.is_authenticated = False
        await self.service._check_user(123)
        self.mock_client.list_prints.assert_not_called()
