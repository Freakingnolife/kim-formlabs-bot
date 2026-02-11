"""Fleet utilization analytics and dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def compute_fleet_stats(printers: list[dict], prints: list[dict]) -> dict:
    """Compute fleet utilization statistics.

    Args:
        printers: List of Printer dicts from Web API
        prints: List of PrintRun dicts from Web API (for the analysis period)

    Returns:
        Fleet statistics dict
    """
    total = len(printers)
    online = 0
    printing = 0
    idle = 0
    offline = 0

    for p in printers:
        status_info = p.get("printer_status", {})
        status = (status_info.get("status", "") or "").lower()

        if status in ("offline", ""):
            offline += 1
        elif status_info.get("current_print_run"):
            printing += 1
            online += 1
        else:
            idle += 1
            online += 1

    # Print statistics
    completed = sum(1 for p in prints if (p.get("status", "") or "").upper() == "FINISHED")
    failed = sum(1 for p in prints if (p.get("status", "") or "").upper() in ("ERROR", "ABORTED"))
    total_prints = len(prints)

    total_volume = sum(p.get("volume_ml", 0) or 0 for p in prints)
    total_duration_ms = sum(p.get("estimated_duration_ms", 0) or 0 for p in prints)

    success_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0

    # Per-printer stats
    printer_print_counts: dict[str, int] = {}
    for p in prints:
        serial = p.get("printer", "unknown")
        printer_print_counts[serial] = printer_print_counts.get(serial, 0) + 1

    busiest = max(printer_print_counts.items(), key=lambda x: x[1]) if printer_print_counts else ("N/A", 0)
    least_used = min(printer_print_counts.items(), key=lambda x: x[1]) if printer_print_counts else ("N/A", 0)

    return {
        "total_printers": total,
        "online": online,
        "printing": printing,
        "idle": idle,
        "offline": offline,
        "total_prints": total_prints,
        "completed": completed,
        "failed": failed,
        "success_rate": round(success_rate, 1),
        "total_volume_ml": round(total_volume, 1),
        "total_duration_hours": round(total_duration_ms / 3_600_000, 1) if total_duration_ms else 0,
        "avg_print_time_hours": round(total_duration_ms / total_prints / 3_600_000, 1) if total_prints else 0,
        "busiest_printer": busiest[0],
        "busiest_count": busiest[1],
        "least_used_printer": least_used[0],
        "least_used_count": least_used[1],
    }


def format_fleet_overview(printers: list[dict]) -> str:
    """Format a quick fleet overview."""
    if not printers:
        return "🏭 No printers found."

    total = len(printers)
    online = 0
    printing = 0
    idle = 0
    offline = 0

    printer_lines = []
    for p in printers:
        status_info = p.get("printer_status", {})
        status = (status_info.get("status", "") or "").lower()
        alias = p.get("alias", p.get("serial", "unknown"))

        if status in ("offline", ""):
            offline += 1
            icon = "⚫"
            state = "Offline"
        elif status_info.get("current_print_run"):
            printing += 1
            online += 1
            icon = "🟢"
            run = status_info["current_print_run"]
            name = run.get("name", "Unknown") if isinstance(run, dict) else "printing"
            state = f"Printing: {name}"
        else:
            idle += 1
            online += 1
            icon = "🟡"
            state = "Idle"

        printer_lines.append(f"  {icon} {alias}: {state}")

    lines = [
        "🏭 *Fleet Dashboard*",
        f"{'=' * 28}",
        f"Printers: {total} total | {online} online | {printing} printing | {idle} idle | {offline} offline",
        "",
    ]
    lines.extend(printer_lines[:15])
    if len(printer_lines) > 15:
        lines.append(f"  ... and {len(printer_lines) - 15} more")

    return "\n".join(lines)


def format_fleet_stats(stats: dict) -> str:
    """Format fleet statistics as a Telegram message."""
    lines = [
        "📊 *Fleet Statistics*",
        f"{'=' * 28}",
        "",
        f"*Current Status:*",
        f"  {stats['total_printers']} printers | {stats['online']} online | {stats['printing']} printing",
        "",
        f"*Print History:*",
        f"  Total: {stats['total_prints']} prints",
        f"  Completed: {stats['completed']} | Failed: {stats['failed']}",
        f"  Success Rate: {stats['success_rate']}%",
        "",
        f"*Resource Usage:*",
        f"  Resin: {stats['total_volume_ml']:,.0f} ml",
        f"  Print Time: {stats['total_duration_hours']:,.1f} hours",
        f"  Avg/Print: {stats['avg_print_time_hours']:.1f} hours",
        "",
        f"*Printer Activity:*",
        f"  Busiest: {stats['busiest_printer']} ({stats['busiest_count']} prints)",
        f"  Least Used: {stats['least_used_printer']} ({stats['least_used_count']} prints)",
    ]
    return "\n".join(lines)
