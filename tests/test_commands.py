"""Tests for bot_commands.py command handlers."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestHandleCommand:
    def test_unknown_command(self):
        from bot_commands import handle_command
        result = handle_command("/nonexistent", 123)
        assert "Unknown command" in result

    def test_help_command(self):
        from bot_commands import handle_command
        result = handle_command("/help", 6217674573)
        assert "Kim Formlabs Bot" in result
        assert "/login" in result
        # Admin should see admin commands
        assert "Admin" in result

    def test_help_non_admin(self):
        from bot_commands import handle_command
        result = handle_command("/help", 99999)
        assert "Kim Formlabs Bot" in result
        assert "Admin Commands" not in result

    @patch("bot_commands.get_token")
    def test_status_not_logged_in(self, mock_get_token):
        mock_get_token.return_value = None
        from bot_commands import handle_command
        result = handle_command("/status", 123)
        assert "Not connected" in result

    @patch("bot_commands.get_token")
    def test_logout_not_logged_in(self, mock_get_token):
        mock_get_token.return_value = None
        from bot_commands import handle_command
        result = handle_command("/logout", 123)
        assert "not currently logged in" in result

    @patch("bot_commands.is_approved")
    def test_printers_not_approved(self, mock_approved):
        mock_approved.return_value = False
        from bot_commands import handle_command
        result = handle_command("/printers", 99999)
        assert "pending" in result.lower()

    @patch("bot_commands.is_approved")
    def test_materials_not_approved(self, mock_approved):
        mock_approved.return_value = False
        from bot_commands import handle_command
        result = handle_command("/materials", 99999)
        assert "pending" in result.lower()

    @patch("bot_commands.is_admin")
    def test_approve_non_admin(self, mock_admin):
        mock_admin.return_value = False
        from bot_commands import handle_command
        result = handle_command("/approve", 99999, args=["12345"])
        assert "admin" in result.lower()

    def test_approve_no_args(self):
        from bot_commands import handle_command
        result = handle_command("/approve", 6217674573)
        assert "Usage" in result

    def test_approve_invalid_id(self):
        from bot_commands import handle_command
        result = handle_command("/approve", 6217674573, args=["not_a_number"])
        assert "Invalid" in result

    @patch("bot_commands.is_approved")
    def test_cancel_not_approved(self, mock_approved):
        mock_approved.return_value = False
        from bot_commands import handle_command
        result = handle_command("/cancel", 99999, args=["job1"])
        assert "pending" in result.lower()

    @patch("bot_commands.is_approved")
    def test_cancel_no_args(self, mock_approved):
        mock_approved.return_value = True
        from bot_commands import handle_command
        result = handle_command("/cancel", 123)
        assert "Usage" in result

    @patch("bot_commands.is_approved")
    def test_notify_status(self, mock_approved):
        mock_approved.return_value = True
        from bot_commands import handle_command
        result = handle_command("/notify", 123, args=["status"])
        assert "Notifications" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_progress_no_web_client(self, mock_web, mock_approved):
        mock_approved.return_value = True
        mock_web.return_value = None
        from bot_commands import handle_command
        result = handle_command("/progress", 123)
        assert "Web API not configured" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_cartridges_no_web_client(self, mock_web, mock_approved):
        mock_approved.return_value = True
        mock_web.return_value = None
        from bot_commands import handle_command
        result = handle_command("/cartridges", 123)
        assert "Web API not configured" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_tanks_no_web_client(self, mock_web, mock_approved):
        mock_approved.return_value = True
        mock_web.return_value = None
        from bot_commands import handle_command
        result = handle_command("/tanks", 123)
        assert "Web API not configured" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_fleet_no_web_client(self, mock_web, mock_approved):
        mock_approved.return_value = True
        mock_web.return_value = None
        from bot_commands import handle_command
        result = handle_command("/fleet", 123)
        assert "Web API not configured" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_queue_no_web_client(self, mock_web, mock_approved):
        mock_approved.return_value = True
        mock_web.return_value = None
        from bot_commands import handle_command
        result = handle_command("/queue", 123)
        assert "Web API not configured" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_cost_no_web_client(self, mock_web, mock_approved):
        mock_approved.return_value = True
        mock_web.return_value = None
        from bot_commands import handle_command
        result = handle_command("/cost", 123)
        assert "Web API not configured" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_progress_with_mock_data(self, mock_web, mock_approved, mock_web_client):
        mock_approved.return_value = True
        mock_web.return_value = mock_web_client
        # Override to return PRINTING prints
        mock_web_client.list_prints.return_value = {
            "results": [{
                "guid": "r1", "name": "test.stl", "printer": "ABC",
                "status": "PRINTING", "currently_printing_layer": 50,
                "layer_count": 100, "estimated_time_remaining_ms": 1800000,
            }]
        }
        from bot_commands import handle_command
        result = handle_command("/progress", 123)
        assert "test.stl" in result
        assert "50%" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_cartridges_with_mock_data(self, mock_web, mock_approved, mock_web_client):
        mock_approved.return_value = True
        mock_web.return_value = mock_web_client
        from bot_commands import handle_command
        result = handle_command("/cartridges", 123)
        assert "Cartridge Status" in result
        assert "Grey V5" in result

    @patch("bot_commands.is_approved")
    @patch("bot_commands._get_web_client")
    def test_fleet_overview(self, mock_web, mock_approved, mock_web_client):
        mock_approved.return_value = True
        mock_web.return_value = mock_web_client
        from bot_commands import handle_command
        result = handle_command("/fleet", 123)
        assert "Fleet Dashboard" in result
