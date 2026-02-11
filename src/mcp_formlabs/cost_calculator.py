"""Print cost estimation based on resin volume and material pricing."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

# Approximate retail prices per liter (USD)
RESIN_PRICES_PER_LITER = {
    "FLGPGR05": 149.0,   # Grey V5
    "FLGPBK05": 149.0,   # Black V5
    "FLGPCL05": 149.0,   # Clear V5
    "FLGPWH05": 149.0,   # White V5
    "FLTO2K02": 189.0,   # Tough 2000 V2
    "FLTOTL02": 189.0,   # Tough 1500 V2
    "FLDUCL21": 175.0,   # Durable V2.1
    "FLELCL02": 199.0,   # Elastic 50A V2
    "FLFMGR01": 99.0,    # Fast Model V1
}

# Electricity cost per hour of printing (rough estimate)
ELECTRICITY_COST_PER_HOUR = 0.05  # USD


def estimate_print_cost(
    volume_ml: float,
    material_code: str,
    print_duration_ms: int = 0,
) -> dict:
    """Estimate the cost of a single print.

    Args:
        volume_ml: Resin volume in milliliters
        material_code: Formlabs material code
        print_duration_ms: Print duration in milliseconds (for electricity cost)

    Returns:
        Dict with cost breakdown
    """
    price_per_liter = RESIN_PRICES_PER_LITER.get(material_code, 149.0)
    resin_cost = volume_ml * (price_per_liter / 1000.0)

    electricity_cost = 0.0
    if print_duration_ms > 0:
        hours = print_duration_ms / 3_600_000
        electricity_cost = hours * ELECTRICITY_COST_PER_HOUR

    total = resin_cost + electricity_cost

    return {
        "resin_cost_usd": round(resin_cost, 2),
        "electricity_cost_usd": round(electricity_cost, 2),
        "total_cost_usd": round(total, 2),
        "volume_ml": round(volume_ml, 1),
        "material_code": material_code,
        "price_per_liter": price_per_liter,
    }


def summarize_costs(prints: list[dict]) -> dict:
    """Summarize costs across multiple prints.

    Args:
        prints: List of PrintRun dicts from the Web API

    Returns:
        Cost summary dict
    """
    total_volume = 0.0
    total_cost = 0.0
    material_breakdown: dict[str, dict] = {}
    print_count = 0

    for p in prints:
        volume = p.get("volume_ml", 0) or 0
        material = p.get("material", "") or p.get("print_settings_code", "")
        duration = p.get("estimated_duration_ms", 0) or 0

        if volume <= 0:
            continue

        cost = estimate_print_cost(volume, material, duration)
        total_volume += volume
        total_cost += cost["total_cost_usd"]
        print_count += 1

        if material not in material_breakdown:
            material_breakdown[material] = {
                "volume_ml": 0,
                "cost_usd": 0,
                "count": 0,
                "material_name": p.get("material_name", material),
            }
        material_breakdown[material]["volume_ml"] += volume
        material_breakdown[material]["cost_usd"] += cost["total_cost_usd"]
        material_breakdown[material]["count"] += 1

    return {
        "total_prints": print_count,
        "total_volume_ml": round(total_volume, 1),
        "total_cost_usd": round(total_cost, 2),
        "avg_cost_per_print": round(total_cost / print_count, 2) if print_count else 0,
        "material_breakdown": material_breakdown,
    }


def format_cost_report(summary: dict) -> str:
    """Format a cost summary as a Telegram-friendly message."""
    lines = [
        f"💰 *Cost Summary*",
        f"{'=' * 28}",
        f"",
        f"Prints: {summary['total_prints']}",
        f"Total Resin: {summary['total_volume_ml']:.0f} ml",
        f"Total Cost: ${summary['total_cost_usd']:.2f}",
        f"Avg/Print: ${summary['avg_cost_per_print']:.2f}",
    ]

    if summary["material_breakdown"]:
        lines.append("")
        lines.append("*By Material:*")
        for code, info in sorted(
            summary["material_breakdown"].items(),
            key=lambda x: x[1]["cost_usd"],
            reverse=True,
        ):
            name = info["material_name"] or code
            lines.append(
                f"  {name}: {info['volume_ml']:.0f}ml / ${info['cost_usd']:.2f} ({info['count']} prints)"
            )

    return "\n".join(lines)
