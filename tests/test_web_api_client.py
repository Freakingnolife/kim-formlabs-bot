"""Tests for web_api_client.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_formlabs.web_api_client import FormlabsWebClient, WebAPIError


class TestFormlabsWebClient:
    def test_init_defaults(self):
        client = FormlabsWebClient()
        assert client.client_id == ""
        assert client.client_secret == ""
        assert not client.is_authenticated

    def test_init_with_credentials(self):
        client = FormlabsWebClient(client_id="id", client_secret="secret")
        assert client.client_id == "id"
        assert client.client_secret == "secret"

    def test_init_with_token(self):
        client = FormlabsWebClient(access_token="tok123")
        assert client.is_authenticated

    @patch("mcp_formlabs.web_api_client.requests.post")
    def test_authenticate_success(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"access_token": "tok", "expires_in": 86400},
        )
        client = FormlabsWebClient(client_id="id", client_secret="sec")
        result = client.authenticate()
        assert result["access_token"] == "tok"
        assert client.is_authenticated

    @patch("mcp_formlabs.web_api_client.requests.post")
    def test_authenticate_failure(self, mock_post):
        mock_post.return_value = MagicMock(status_code=400, text="bad creds")
        client = FormlabsWebClient(client_id="id", client_secret="sec")
        with pytest.raises(WebAPIError):
            client.authenticate()

    def test_list_printers(self):
        client = FormlabsWebClient(access_token="tok")
        with patch.object(client, "_get", return_value=[{"serial": "ABC"}]) as mock:
            result = client.list_printers()
            assert len(result) == 1
            assert result[0]["serial"] == "ABC"
            mock.assert_called_once_with("/printers/")

    def test_get_printer(self):
        client = FormlabsWebClient(access_token="tok")
        with patch.object(client, "_get", return_value={"serial": "ABC"}) as mock:
            result = client.get_printer("ABC")
            assert result["serial"] == "ABC"
            mock.assert_called_once_with("/printers/ABC/")

    def test_list_prints(self):
        client = FormlabsWebClient(access_token="tok")
        with patch.object(client, "_get", return_value={"count": 1, "results": [{"guid": "x"}]}) as mock:
            result = client.list_prints(status="PRINTING")
            assert result["count"] == 1
            mock.assert_called_once()

    def test_list_cartridges(self):
        client = FormlabsWebClient(access_token="tok")
        with patch.object(client, "_get", return_value={"count": 0, "results": []}) as mock:
            result = client.list_cartridges()
            assert result["count"] == 0

    def test_list_tanks(self):
        client = FormlabsWebClient(access_token="tok")
        with patch.object(client, "_get", return_value={"count": 0, "results": []}) as mock:
            result = client.list_tanks()
            assert result["count"] == 0

    def test_list_groups(self):
        client = FormlabsWebClient(access_token="tok")
        with patch.object(client, "_get", return_value=[{"id": "g1"}]) as mock:
            result = client.list_groups()
            assert len(result) == 1

    def test_get_group_queue(self):
        client = FormlabsWebClient(access_token="tok")
        with patch.object(client, "_get", return_value=[]) as mock:
            result = client.get_group_queue("g1")
            assert result == []

    def test_list_events(self):
        client = FormlabsWebClient(access_token="tok")
        with patch.object(client, "_get", return_value={"count": 0, "results": []}) as mock:
            result = client.list_events(printer="ABC")
            assert result["count"] == 0

    def test_paginate_all(self):
        client = FormlabsWebClient(access_token="tok")
        responses = [
            {"results": [{"id": 1}], "next": "page2"},
            {"results": [{"id": 2}], "next": None},
        ]
        with patch.object(client, "_get", side_effect=responses):
            result = client._paginate_all("/test/")
            assert len(result) == 2

    def test_rate_limit_tracking(self):
        client = FormlabsWebClient(access_token="tok")
        # Simulate adding timestamps
        import time
        for _ in range(5):
            client._request_timestamps.append(time.time())
        assert len(client._request_timestamps) <= 80  # Well under limit
