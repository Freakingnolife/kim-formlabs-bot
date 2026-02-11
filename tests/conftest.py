"""Shared test fixtures."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root and src are on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@pytest.fixture
def mock_preform_client():
    """Mock PreFormClient."""
    client = MagicMock()
    client.list_devices.return_value = {
        "devices": [
            {
                "id": "group-1",
                "is_connected": True,
                "printers": [
                    {"id": "printer-1", "name": "Form4-Alpha"},
                    {"id": "printer-2", "name": "Form4-Beta"},
                ],
            }
        ]
    }
    client.list_jobs.return_value = [
        {"name": "test-job", "status": "printing", "printer": "Form4-Alpha"},
        {"name": "old-job", "status": "completed", "printer": "Form4-Beta"},
    ]
    client.cancel_job.return_value = {"status": "ok"}
    return client


@pytest.fixture
def mock_web_client():
    """Mock FormlabsWebClient."""
    client = MagicMock()
    client.is_authenticated = True
    client.list_printers.return_value = [
        {
            "serial": "ABC123",
            "alias": "Form4-Alpha",
            "machine_type_id": "FORM-4-0",
            "printer_status": {
                "status": "online",
                "current_print_run": {
                    "guid": "run-1",
                    "name": "gear_housing.stl",
                    "status": "PRINTING",
                    "currently_printing_layer": 150,
                    "layer_count": 300,
                    "estimated_time_remaining_ms": 3600000,
                },
            },
        },
        {
            "serial": "DEF456",
            "alias": "Form4-Beta",
            "machine_type_id": "FORM-4-0",
            "printer_status": {
                "status": "online",
                "current_print_run": None,
            },
        },
    ]
    client.list_prints.return_value = {
        "count": 2,
        "next": None,
        "results": [
            {
                "guid": "run-1",
                "name": "gear_housing.stl",
                "printer": "ABC123",
                "status": "PRINTING",
                "currently_printing_layer": 150,
                "layer_count": 300,
                "estimated_time_remaining_ms": 3600000,
                "estimated_duration_ms": 7200000,
                "elapsed_duration_ms": 3600000,
                "volume_ml": 45.5,
                "material": "FLGPGR05",
                "material_name": "Grey V5",
            },
            {
                "guid": "run-2",
                "name": "bracket.stl",
                "printer": "DEF456",
                "status": "FINISHED",
                "volume_ml": 12.3,
                "material": "FLGPBK05",
                "material_name": "Black V5",
                "estimated_duration_ms": 3600000,
            },
        ],
    }
    client.list_cartridges.return_value = {
        "count": 2,
        "results": [
            {
                "serial": "CART-001",
                "material": "FLGPGR05",
                "display_name": "Grey V5 Cart",
                "initial_volume_ml": 1000,
                "volume_dispensed_ml": 800,
                "is_empty": False,
                "inside_printer": "ABC123",
            },
            {
                "serial": "CART-002",
                "material": "FLGPBK05",
                "display_name": "Black V5 Cart",
                "initial_volume_ml": 1000,
                "volume_dispensed_ml": 200,
                "is_empty": False,
                "inside_printer": "DEF456",
            },
        ],
    }
    client.list_tanks.return_value = {
        "count": 2,
        "results": [
            {
                "serial": "TANK-001",
                "material": "FLGPGR05",
                "display_name": "Grey Tank",
                "layers_printed": 12000,
                "tank_type": "standard",
                "inside_printer": "ABC123",
                "heatmap": "https://example.com/heatmap.png",
                "manufacture_date": "2025-01-01",
                "last_print_date": "2026-02-10",
            },
            {
                "serial": "TANK-002",
                "material": "FLGPBK05",
                "display_name": "Black Tank",
                "layers_printed": 3000,
                "tank_type": "standard",
                "inside_printer": "DEF456",
                "heatmap": None,
                "manufacture_date": "2025-06-01",
                "last_print_date": "2026-02-09",
            },
        ],
    }
    client.list_groups.return_value = [
        {"id": "group-uuid-1", "name": "Main Lab"},
    ]
    client.get_group_queue.return_value = [
        {"id": "q1", "name": "next_print.stl", "material_name": "Grey V5"},
    ]
    client.list_events.return_value = {"count": 0, "results": []}
    return client


@pytest.fixture
def admin_user_id():
    return 6217674573


@pytest.fixture
def regular_user_id():
    return 99999999


@pytest.fixture(autouse=True)
def patch_keychain():
    """Prevent actual keychain access during tests."""
    with patch("mcp_formlabs.keychain.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        yield mock_sub
