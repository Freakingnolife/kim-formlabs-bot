"""HTTP client for the Formlabs PreForm Local API (localhost:44388)."""

from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "http://localhost:44388"
POLL_INTERVAL = 1.0
POLL_TIMEOUT = 300.0


class PreFormError(Exception):
    """Raised when a PreForm API call fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"PreForm API error {status_code}: {detail}")


class PreFormClient:
    """Stateful HTTP client for the PreForm Local API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (
            base_url or os.getenv("PREFORM_API_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ── helpers ──────────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        data: Any = None,
        files: dict | None = None,
        timeout: float = 30.0,
    ) -> dict | list | str:
        headers = {}
        if files:
            # Let requests set the multipart content-type
            headers["Content-Type"] = None

        resp = self.session.request(
            method,
            self._url(path),
            json=json,
            params=params,
            data=data,
            files=files,
            headers=headers,
            timeout=timeout,
        )

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise PreFormError(resp.status_code, str(detail))

        if not resp.content:
            return {"status": "ok"}

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return resp.json()
        return resp.text

    def _get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs: Any) -> Any:
        return self._request("POST", path, **kwargs)

    def _poll_operation(self, path: str, timeout: float = POLL_TIMEOUT) -> dict:
        """Poll a long-running operation until it completes."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self._get(path)
            if isinstance(result, dict):
                status = result.get("status", "").lower()
                if status in ("done", "success", "completed", "ready"):
                    return result
                if status in ("error", "failed"):
                    raise PreFormError(500, f"Operation failed: {result}")
            time.sleep(POLL_INTERVAL)
        raise PreFormError(504, f"Operation timed out after {timeout}s")

    # ── API methods ──────────────────────────────────────────────────

    def list_devices(
        self, group: str | None = None, can_print: bool = False
    ) -> list[dict]:
        """GET /devices/ — list fleet printers."""
        params: dict[str, Any] = {}
        if group:
            params["group"] = group
        if can_print:
            params["can_print"] = "true"
        return self._get("/devices/", params=params)

    def login(self, username: str, password: str) -> dict:
        """POST /login — authenticate with Formlabs Dashboard."""
        return self._post("/login", json={"username": username, "password": password})

    def create_scene(
        self,
        printer_type: str,
        material: str,
        layer_height: float,
    ) -> dict:
        """POST /scene/ — create a new scene."""
        payload = {
            "machine_type": printer_type,
            "material_code": material,
            "layer_thickness_mm": layer_height,
            "print_setting": f"{material}_{layer_height}",
        }
        return self._post("/scene/", json=payload)

    def import_model(
        self,
        scene_id: str,
        file_path: str,
        auto_orient: bool = True,
        repair: bool = False,
    ) -> dict:
        """POST /scene/{id}/import-model/ — import a 3D model file."""
        expanded = os.path.expanduser(file_path)
        with open(expanded, "rb") as f:
            files = {"file": (os.path.basename(expanded), f)}
            data = {}
            if auto_orient:
                data["auto_orient"] = "true"
            if repair:
                data["repair"] = "true"
            return self._post(
                f"/scene/{scene_id}/import-model/",
                files=files,
                data=data,
                timeout=120.0,
            )

    def duplicate_model(
        self,
        scene_id: str,
        count: int,
        model_id: str | None = None,
    ) -> dict:
        """POST /scene/{id}/duplicate-model/ — duplicate parts in a scene."""
        payload: dict[str, Any] = {"count": count}
        if model_id:
            payload["model_id"] = model_id
        return self._post(f"/scene/{scene_id}/duplicate-model/", json=payload)

    def auto_orient(self, scene_id: str) -> dict:
        """POST /scene/{id}/auto-orient/ — auto-orient models."""
        return self._post(f"/scene/{scene_id}/auto-orient/")

    def auto_support(self, scene_id: str, mode: str = "auto-v2") -> dict:
        """POST /scene/{id}/auto-support/ — generate supports."""
        return self._post(
            f"/scene/{scene_id}/auto-support/", json={"mode": mode}
        )

    def auto_layout(self, scene_id: str) -> dict:
        """POST /scene/{id}/auto-layout/ — auto-layout models on build plate."""
        return self._post(f"/scene/{scene_id}/auto-layout/")

    def screenshot(self, scene_id: str) -> dict:
        """POST /scene/{id}/screenshot/ — generate a preview screenshot."""
        return self._post(f"/scene/{scene_id}/screenshot/")

    def slice(self, scene_id: str) -> dict:
        """POST /scene/{id}/slice/ — slice the scene for printing."""
        return self._post(f"/scene/{scene_id}/slice/", timeout=180.0)

    def print_scene(
        self,
        scene_id: str,
        *,
        printer_id: str | None = None,
        group_id: str | None = None,
        job_name: str | None = None,
        queue: bool = True,
    ) -> dict:
        """POST /print/ or /remote-print/ — send scene to a printer."""
        payload: dict[str, Any] = {"scene_id": scene_id}
        if job_name:
            payload["job_name"] = job_name

        # If a group_id is specified, use remote-print (fleet queue).
        if group_id:
            payload["group_id"] = group_id
            payload["queue"] = queue
            return self._post("/remote-print/", json=payload, timeout=60.0)

        if printer_id:
            payload["printer_id"] = printer_id
        return self._post("/print/", json=payload, timeout=60.0)

    def get_scene(self, scene_id: str) -> dict:
        """GET /scene/{id}/ — get scene information."""
        return self._get(f"/scene/{scene_id}/")

    def delete_scene(self, scene_id: str) -> dict:
        """DELETE /scene/{id}/ — delete a scene."""
        return self._request("DELETE", f"/scene/{scene_id}/")
