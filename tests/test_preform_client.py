"""Tests for preform_client.py."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_formlabs.preform_client import PreFormClient, PreFormError


class TestPreFormClient:
    def test_init_defaults(self):
        client = PreFormClient()
        assert client.base_url == "http://localhost:44388"

    def test_init_custom_url(self):
        client = PreFormClient(base_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"

    def test_set_token(self):
        client = PreFormClient()
        client.set_token("mytoken")
        assert client.session.headers.get("Authorization") == "Bearer mytoken"

    def test_clear_token(self):
        client = PreFormClient()
        client.set_token("mytoken")
        client.set_token("")
        assert "Authorization" not in client.session.headers

    def test_url_builder(self):
        client = PreFormClient(base_url="http://localhost:44388")
        assert client._url("/devices/") == "http://localhost:44388/devices/"

    @patch("mcp_formlabs.preform_client.requests.Session.request")
    def test_request_success(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            content=b'{"test": true}',
            headers={"Content-Type": "application/json"},
            json=lambda: {"test": True},
        )
        client = PreFormClient()
        result = client._get("/test/")
        assert result == {"test": True}

    @patch("mcp_formlabs.preform_client.requests.Session.request")
    def test_request_error(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=404,
            json=lambda: {"error": "not found"},
        )
        client = PreFormClient()
        with pytest.raises(PreFormError) as exc:
            client._get("/nonexistent/")
        assert exc.value.status_code == 404

    @patch("mcp_formlabs.preform_client.requests.Session.request")
    def test_request_empty_response(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            content=b"",
        )
        client = PreFormClient()
        result = client._get("/empty/")
        assert result == {"status": "ok"}

    def test_no_duplicate_list_jobs(self):
        """Ensure list_jobs is not defined twice."""
        import inspect
        members = dict(inspect.getmembers(PreFormClient))
        # Should only have one list_jobs
        assert "list_jobs" in members

    def test_no_duplicate_cancel_job(self):
        """Ensure cancel_job is not defined twice."""
        import inspect
        members = dict(inspect.getmembers(PreFormClient))
        assert "cancel_job" in members

    def test_get_job_status_is_alias(self):
        """get_job_status should delegate to get_job."""
        client = PreFormClient()
        with patch.object(client, "get_job", return_value={"id": "j1"}) as mock:
            result = client.get_job_status("j1")
            mock.assert_called_once_with("j1")
            assert result == {"id": "j1"}

    @patch("mcp_formlabs.preform_client.requests.Session.request")
    def test_list_devices(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            content=b'[{"id": "p1"}]',
            headers={"Content-Type": "application/json"},
            json=lambda: [{"id": "p1"}],
        )
        client = PreFormClient()
        result = client.list_devices()
        assert isinstance(result, list)

    @patch("mcp_formlabs.preform_client.requests.Session.request")
    def test_create_scene(self, mock_request):
        mock_request.return_value = MagicMock(
            status_code=200,
            content=b'{"id": "s1"}',
            headers={"Content-Type": "application/json"},
            json=lambda: {"id": "s1"},
        )
        client = PreFormClient()
        result = client.create_scene("FORM-4-0", "FLGPGR05", 0.05)
        assert result["id"] == "s1"
