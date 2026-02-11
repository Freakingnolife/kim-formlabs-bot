"""Tests for cost_calculator.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_formlabs.cost_calculator import (
    estimate_print_cost,
    summarize_costs,
    format_cost_report,
    RESIN_PRICES_PER_LITER,
)


class TestEstimatePrintCost:
    def test_grey_v5_cost(self):
        result = estimate_print_cost(10.0, "FLGPGR05")
        assert result["resin_cost_usd"] == round(10.0 * 149.0 / 1000, 2)
        assert result["volume_ml"] == 10.0
        assert result["material_code"] == "FLGPGR05"

    def test_with_duration(self):
        result = estimate_print_cost(10.0, "FLGPGR05", print_duration_ms=3_600_000)
        assert result["electricity_cost_usd"] == 0.05  # 1 hour * $0.05
        assert result["total_cost_usd"] == round(1.49 + 0.05, 2)

    def test_zero_volume(self):
        result = estimate_print_cost(0.0, "FLGPGR05")
        assert result["resin_cost_usd"] == 0.0
        assert result["total_cost_usd"] == 0.0

    def test_unknown_material_defaults(self):
        result = estimate_print_cost(10.0, "UNKNOWN")
        assert result["price_per_liter"] == 149.0

    def test_all_materials_have_prices(self):
        known = {"FLGPGR05", "FLGPBK05", "FLGPCL05", "FLGPWH05", "FLTO2K02", "FLTOTL02", "FLDUCL21", "FLELCL02", "FLFMGR01"}
        for code in known:
            assert code in RESIN_PRICES_PER_LITER


class TestSummarizeCosts:
    def test_empty_prints(self):
        result = summarize_costs([])
        assert result["total_prints"] == 0
        assert result["total_cost_usd"] == 0

    def test_single_print(self):
        prints = [{"volume_ml": 50.0, "material": "FLGPGR05", "estimated_duration_ms": 3600000, "material_name": "Grey V5"}]
        result = summarize_costs(prints)
        assert result["total_prints"] == 1
        assert result["total_volume_ml"] == 50.0
        assert result["total_cost_usd"] > 0

    def test_multiple_materials(self):
        prints = [
            {"volume_ml": 50.0, "material": "FLGPGR05", "material_name": "Grey V5"},
            {"volume_ml": 30.0, "material": "FLGPBK05", "material_name": "Black V5"},
        ]
        result = summarize_costs(prints)
        assert result["total_prints"] == 2
        assert len(result["material_breakdown"]) == 2

    def test_skips_zero_volume(self):
        prints = [
            {"volume_ml": 0, "material": "FLGPGR05"},
            {"volume_ml": 10.0, "material": "FLGPGR05", "material_name": "Grey V5"},
        ]
        result = summarize_costs(prints)
        assert result["total_prints"] == 1

    def test_avg_cost(self):
        prints = [
            {"volume_ml": 100.0, "material": "FLGPGR05", "material_name": "Grey V5"},
            {"volume_ml": 100.0, "material": "FLGPGR05", "material_name": "Grey V5"},
        ]
        result = summarize_costs(prints)
        assert result["avg_cost_per_print"] == result["total_cost_usd"] / 2


class TestFormatCostReport:
    def test_format_nonempty(self):
        summary = {
            "total_prints": 5,
            "total_volume_ml": 250.0,
            "total_cost_usd": 37.25,
            "avg_cost_per_print": 7.45,
            "material_breakdown": {
                "FLGPGR05": {"material_name": "Grey V5", "volume_ml": 250.0, "cost_usd": 37.25, "count": 5},
            },
        }
        text = format_cost_report(summary)
        assert "Cost Summary" in text
        assert "$37.25" in text
        assert "Grey V5" in text

    def test_format_empty(self):
        summary = {
            "total_prints": 0,
            "total_volume_ml": 0,
            "total_cost_usd": 0,
            "avg_cost_per_print": 0,
            "material_breakdown": {},
        }
        text = format_cost_report(summary)
        assert "Prints: 0" in text
