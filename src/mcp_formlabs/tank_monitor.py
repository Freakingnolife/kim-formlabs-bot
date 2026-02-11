"""Tank lifecycle monitoring and replacement prediction."""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Estimated max layers by tank type (conservative estimates)
TANK_MAX_LAYERS = {
    "standard": 15000,
    "lft": 25000,      # Long Life Tank
    "form4": 20000,    # Form 4 specific
    "default": 15000,
}

# Severity thresholds (percentage of life used)
THRESHOLD_WARNING = 70
THRESHOLD_CRITICAL = 90


def estimate_tank_life(tank: dict) -> dict:
    """Estimate remaining tank life.

    Args:
        tank: Tank dict from Web API

    Returns:
        Dict with lifecycle analysis
    """
    layers = tank.get("layers_printed", 0) or 0
    tank_type = (tank.get("tank_type", "") or "").lower()
    max_layers = TANK_MAX_LAYERS.get(tank_type, TANK_MAX_LAYERS["default"])

    percent_used = min(100.0, (layers / max_layers) * 100) if max_layers > 0 else 0
    remaining_layers = max(0, max_layers - layers)

    if percent_used >= THRESHOLD_CRITICAL:
        severity = "critical"
    elif percent_used >= THRESHOLD_WARNING:
        severity = "warning"
    else:
        severity = "good"

    return {
        "serial": tank.get("serial", "unknown"),
        "material": tank.get("material", "unknown"),
        "display_name": tank.get("display_name", ""),
        "layers_printed": layers,
        "max_layers": max_layers,
        "remaining_layers": remaining_layers,
        "percent_used": round(percent_used, 1),
        "severity": severity,
        "tank_type": tank_type or "standard",
        "inside_printer": tank.get("inside_printer"),
        "last_print_date": tank.get("last_print_date"),
        "manufacture_date": tank.get("manufacture_date"),
        "heatmap_url": tank.get("heatmap"),
    }


def format_tank_status(tanks: list[dict]) -> str:
    """Format tank status as a Telegram message.

    Args:
        tanks: List of tank dicts from Web API
    """
    if not tanks:
        return "🪣 No tanks found."

    analyses = [estimate_tank_life(t) for t in tanks]
    analyses.sort(key=lambda a: a["percent_used"], reverse=True)

    lines = [
        "🪣 *Tank Status*",
        f"{'=' * 28}",
        "",
    ]

    for a in analyses:
        if a["severity"] == "critical":
            icon = "🔴"
        elif a["severity"] == "warning":
            icon = "🟡"
        else:
            icon = "🟢"

        bar = _progress_bar(a["percent_used"])
        name = a["display_name"] or a["serial"][:12]
        lines.append(f"{icon} *{name}*")
        lines.append(f"   Material: {a['material']}")
        lines.append(f"   Life: {bar} {a['percent_used']:.0f}%")
        lines.append(f"   Layers: {a['layers_printed']:,}/{a['max_layers']:,}")
        if a["inside_printer"]:
            lines.append(f"   In: {a['inside_printer']}")
        lines.append("")

    critical = sum(1 for a in analyses if a["severity"] == "critical")
    warning = sum(1 for a in analyses if a["severity"] == "warning")
    if critical:
        lines.append(f"⚠️ {critical} tank(s) need replacement soon!")
    if warning:
        lines.append(f"💡 {warning} tank(s) approaching end of life.")

    return "\n".join(lines)


def _progress_bar(percent: float, width: int = 10) -> str:
    filled = int(percent / 100 * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"
