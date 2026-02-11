"""HTTP client for the Formlabs Web API (api.formlabs.com/developer/v1/).

Handles OAuth2 authentication, rate limiting, and pagination.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.formlabs.com/developer/v1"
TOKEN_URL = f"{BASE_URL}/o/token/"
REVOKE_URL = f"{BASE_URL}/o/revoke_token/"


class WebAPIError(Exception):
    """Raised when a Formlabs Web API call fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Web API error {status_code}: {detail}")


class FormlabsWebClient:
    """Client for the Formlabs Web API with OAuth2 auth and rate limiting."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
    ):
        self.client_id = client_id or os.getenv("FORMLABS_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("FORMLABS_CLIENT_SECRET", "")
        self._access_token = access_token
        self._token_expires_at: float = 0
        self.session = requests.Session()
        self._request_timestamps: list[float] = []

    # ── Authentication ──────────────────────────────────────────────

    def authenticate(self) -> dict:
        """Obtain an access token using client credentials."""
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise WebAPIError(resp.status_code, resp.text)

        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 86400) - 60
        self.session.headers.update(
            {"Authorization": f"Bearer {self._access_token}"}
        )
        return data

    def revoke_token(self) -> None:
        """Revoke the current access token."""
        if not self._access_token:
            return
        requests.post(
            REVOKE_URL,
            data={
                "token": self._access_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=10,
        )
        self._access_token = None
        self._token_expires_at = 0

    def _ensure_auth(self) -> None:
        """Auto-refresh token if expired."""
        if self._access_token and time.time() < self._token_expires_at:
            return
        if self.client_id and self.client_secret:
            self.authenticate()
        elif self._access_token:
            self.session.headers.update(
                {"Authorization": f"Bearer {self._access_token}"}
            )

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token)

    # ── Rate Limiting ───────────────────────────────────────────────

    def _check_rate_limit(self) -> None:
        """Simple rate limiter: max 80 req/sec (buffer from 100 limit)."""
        now = time.time()
        self._request_timestamps = [
            t for t in self._request_timestamps if now - t < 1.0
        ]
        if len(self._request_timestamps) >= 80:
            sleep_time = 1.0 - (now - self._request_timestamps[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        self._request_timestamps.append(time.time())

    # ── HTTP Helpers ────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        data: dict | None = None,
        timeout: float = 30.0,
    ) -> Any:
        self._ensure_auth()
        self._check_rate_limit()

        url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
        resp = self.session.request(
            method, url, json=json, params=params, data=data, timeout=timeout
        )

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            time.sleep(retry_after)
            return self._request(method, path, json=json, params=params, data=data, timeout=timeout)

        if resp.status_code >= 400:
            raise WebAPIError(resp.status_code, resp.text[:500])

        if not resp.content:
            return {"status": "ok"}

        return resp.json()

    def _get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs: Any) -> Any:
        return self._request("POST", path, **kwargs)

    def _paginate_all(self, path: str, **params: Any) -> list[dict]:
        """Fetch all pages of a paginated endpoint."""
        results: list[dict] = []
        page = 1
        while True:
            params["page"] = page
            resp = self._get(path, params=params)
            if isinstance(resp, list):
                results.extend(resp)
                break
            results.extend(resp.get("results", []))
            if not resp.get("next"):
                break
            page += 1
        return results

    # ── Printers ────────────────────────────────────────────────────

    def list_printers(self) -> list[dict]:
        """GET /printers/ - List all printers."""
        result = self._get("/printers/")
        return result if isinstance(result, list) else result.get("results", [])

    def get_printer(self, serial: str) -> dict:
        """GET /printers/{serial}/ - Get printer details."""
        return self._get(f"/printers/{serial}/")

    # ── Prints ──────────────────────────────────────────────────────

    def list_prints(self, **filters: Any) -> dict:
        """GET /prints/ - List prints with filters (status, date__gt, date__lt, material, printer, page, per_page)."""
        return self._get("/prints/", params={k: v for k, v in filters.items() if v is not None})

    def list_all_prints(self, **filters: Any) -> list[dict]:
        """Fetch all pages of prints."""
        return self._paginate_all("/prints/", **{k: v for k, v in filters.items() if v is not None})

    def get_printer_prints(self, serial: str, **filters: Any) -> dict:
        """GET /printers/{serial}/prints/ - Prints for a specific printer."""
        return self._get(f"/printers/{serial}/prints/", params={k: v for k, v in filters.items() if v is not None})

    # ── Tanks ───────────────────────────────────────────────────────

    def list_tanks(self, page: int = 1, per_page: int = 50) -> dict:
        """GET /tanks/ - List resin tanks."""
        return self._get("/tanks/", params={"page": page, "per_page": per_page})

    def list_all_tanks(self) -> list[dict]:
        """Fetch all tanks across pages."""
        return self._paginate_all("/tanks/")

    # ── Cartridges ──────────────────────────────────────────────────

    def list_cartridges(self, page: int = 1, per_page: int = 50) -> dict:
        """GET /cartridges/ - List resin cartridges."""
        return self._get("/cartridges/", params={"page": page, "per_page": per_page})

    def list_all_cartridges(self) -> list[dict]:
        """Fetch all cartridges across pages."""
        return self._paginate_all("/cartridges/")

    # ── Events ──────────────────────────────────────────────────────

    def list_events(self, **filters: Any) -> dict:
        """GET /events/ - List events with filters."""
        return self._get("/events/", params={k: v for k, v in filters.items() if v is not None})

    # ── Groups ──────────────────────────────────────────────────────

    def list_groups(self) -> list[dict]:
        """GET /groups/ - List all printer groups."""
        result = self._get("/groups/")
        return result if isinstance(result, list) else result.get("results", [])

    def get_group_queue(self, group_id: str) -> list[dict]:
        """GET /groups/{group_id}/queue/ - List group queue items."""
        result = self._get(f"/groups/{group_id}/queue/")
        return result if isinstance(result, list) else result.get("results", [])
