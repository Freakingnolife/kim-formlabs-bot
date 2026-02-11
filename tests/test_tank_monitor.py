"""Tests for tank_monitor.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_formlabs.tank_monitor import (
    estimate_tank_life,
    format_tank_status,
    TANK_MAX_LAYERS,
    THRESHOLD_WARNING,
    THRESHOLD_CRITICAL,
)


class TestEstimateTankLife:
    def test_new_tank(self):
        tank = {"serial": "T1", "material": "FLGPGR05", "layers_printed": 100, "tank_type": "standard"}
        result = estimate_tank_life(tank)
        assert result["severity"] == "good"
        assert result["percent_used"] < THRESHOLD_WARNING

    def test_warning_tank(self):
        max_l = TANK_MAX_LAYERS["standard"]
        tank = {"serial": "T2", "material": "FLGPGR05", "layers_printed": int(max_l * 0.75), "tank_type": "standard"}
        result = estimate_tank_life(tank)
        assert result["severity"] == "warning"

    def test_critical_tank(self):
        max_l = TANK_MAX_LAYERS["standard"]
        tank = {"serial": "T3", "material": "FLGPGR05", "layers_printed": int(max_l * 0.95), "tank_type": "standard"}
        result = estimate_tank_life(tank)
        assert result["severity"] == "critical"

    def test_zero_layers(self):
        tank = {"serial": "T4", "material": "FLGPGR05", "layers_printed": 0, "tank_type": "standard"}
        result = estimate_tank_life(tank)
        assert result["percent_used"] == 0
        assert result["severity"] == "good"

    def test_exceeded_max(self):
        tank = {"serial": "T5", "material": "FLGPGR05", "layers_printed": 20000, "tank_type": "standard"}
        result = estimate_tank_life(tank)
        assert result["percent_used"] == 100.0
        assert result["remaining_layers"] == 0

    def test_unknown_tank_type(self):
        tank = {"serial": "T6", "material": "FLGPGR05", "layers_printed": 1000, "tank_type": "unknown_type"}
        result = estimate_tank_life(tank)
        assert result["max_layers"] == TANK_MAX_LAYERS["default"]

    def test_missing_fields(self):
        tank = {}
        result = estimate_tank_life(tank)
        assert result["serial"] == "unknown"
        assert result["layers_printed"] == 0


class TestFormatTankStatus:
    def test_empty_tanks(self):
        result = format_tank_status([])
        assert "No tanks" in result

    def test_single_tank(self):
        tanks = [{"serial": "T1", "material": "FLGPGR05", "display_name": "Grey Tank", "layers_printed": 5000, "tank_type": "standard", "inside_printer": "ABC"}]
        result = format_tank_status(tanks)
        assert "Grey Tank" in result
        assert "Tank Status" in result

    def test_critical_alert(self):
        max_l = TANK_MAX_LAYERS["standard"]
        tanks = [{"serial": "T1", "material": "FLGPGR05", "layers_printed": int(max_l * 0.95), "tank_type": "standard"}]
        result = format_tank_status(tanks)
        assert "replacement" in result.lower()
