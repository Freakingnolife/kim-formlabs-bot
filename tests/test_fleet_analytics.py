"""Tests for fleet_analytics.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_formlabs.fleet_analytics import (
    compute_fleet_stats,
    format_fleet_overview,
    format_fleet_stats,
)


class TestComputeFleetStats:
    def test_empty_fleet(self):
        stats = compute_fleet_stats([], [])
        assert stats["total_printers"] == 0
        assert stats["total_prints"] == 0

    def test_basic_stats(self, mock_web_client):
        printers = mock_web_client.list_printers()
        prints = mock_web_client.list_prints()["results"]
        stats = compute_fleet_stats(printers, prints)

        assert stats["total_printers"] == 2
        assert stats["online"] == 2
        assert stats["printing"] == 1
        assert stats["idle"] == 1
        assert stats["total_prints"] == 2

    def test_success_rate(self):
        printers = []
        prints = [
            {"status": "FINISHED", "volume_ml": 10, "estimated_duration_ms": 1000, "printer": "A"},
            {"status": "FINISHED", "volume_ml": 10, "estimated_duration_ms": 1000, "printer": "A"},
            {"status": "ERROR", "volume_ml": 10, "estimated_duration_ms": 1000, "printer": "B"},
        ]
        stats = compute_fleet_stats(printers, prints)
        assert stats["success_rate"] == round(2 / 3 * 100, 1)

    def test_volume_aggregation(self):
        printers = []
        prints = [
            {"status": "FINISHED", "volume_ml": 50.5, "printer": "A"},
            {"status": "FINISHED", "volume_ml": 30.0, "printer": "A"},
        ]
        stats = compute_fleet_stats(printers, prints)
        assert stats["total_volume_ml"] == 80.5

    def test_busiest_printer(self):
        printers = []
        prints = [
            {"status": "FINISHED", "printer": "A"},
            {"status": "FINISHED", "printer": "A"},
            {"status": "FINISHED", "printer": "B"},
        ]
        stats = compute_fleet_stats(printers, prints)
        assert stats["busiest_printer"] == "A"
        assert stats["busiest_count"] == 2


class TestFormatFleetOverview:
    def test_empty_fleet(self):
        result = format_fleet_overview([])
        assert "No printers" in result

    def test_with_printers(self, mock_web_client):
        printers = mock_web_client.list_printers()
        result = format_fleet_overview(printers)
        assert "Fleet Dashboard" in result
        assert "Form4-Alpha" in result


class TestFormatFleetStats:
    def test_format(self):
        stats = {
            "total_printers": 3,
            "online": 2,
            "printing": 1,
            "idle": 1,
            "offline": 1,
            "total_prints": 50,
            "completed": 45,
            "failed": 5,
            "success_rate": 90.0,
            "total_volume_ml": 5000.0,
            "total_duration_hours": 100.0,
            "avg_print_time_hours": 2.0,
            "busiest_printer": "ABC",
            "busiest_count": 20,
            "least_used_printer": "DEF",
            "least_used_count": 5,
        }
        text = format_fleet_stats(stats)
        assert "Fleet Statistics" in text
        assert "90.0%" in text
        assert "ABC" in text
