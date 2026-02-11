#!/usr/bin/env python3
"""
Kim Formlabs Bot - Telegram Command Handlers for OpenClaw

This module provides bot commands that can be used by OpenClaw
to interact with the Formlabs API.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_formlabs.preform_client import PreFormClient, PreFormError
from mcp_formlabs.keychain import get_token, delete_token
from mcp_formlabs.materials import MATERIALS
from approval_system import (
    is_approved, is_admin, approve_user, reject_user,
    get_approval_request_message, get_admin_approval_notification,
    get_approved_message, get_rejected_message, get_approved_count
)

# Import new features
try:
    from fixture_generator import generate_fixture, StandardLibrary
    HAS_FIXTURE = True
except ImportError:
    HAS_FIXTURE = False

try:
    from resin_prophet import ResinProphet, cmd_resin_status, cmd_resin_add, cmd_resin_alert
    HAS_RESIN = True
except ImportError:
    HAS_RESIN = False

try:
    from csi_analyzer import cmd_csi, cmd_analyze
    HAS_CSI = True
except ImportError:
    HAS_CSI = False


def get_client_for_user(telegram_user_id: int) -> PreFormClient | None:
    """Get a PreFormClient authenticated for a specific user."""
    client = PreFormClient()
    if not client.load_token_from_keychain(telegram_user_id):
        return None
    return client


def cmd_login(telegram_user_id: int, username: str = None) -> str:
    """Generate a login URL for the user."""
    import requests
    
    # Check if user is approved
    if not is_approved(telegram_user_id):
        # Notify admin
        for admin_id in [6217674573]:  # Markus
            # In real implementation, this would send a message to admin
            pass
        
        return get_approval_request_message(telegram_user_id, username)
    
    try:
        # Call the auth server API to create a token
        response = requests.post(
            "http://127.0.0.1:8765/api/create-token",
            json={"telegram_user_id": telegram_user_id},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            login_url = data.get("login_url", "")
            # Replace localhost with public URL if needed
            login_url = login_url.replace("http://127.0.0.1:8765", "https://kim.harwav.com")
            
            return (
                "🔐 *Secure Login*\n\n"
                "Click the link below to enter your Formlabs credentials:\n\n"
                f"👉 {login_url}\n\n"
                "_Your password is never sent through Telegram._\n"
                "_The link expires in 10 minutes._"
            )
        else:
            return "❌ Failed to generate login link. Please try again."
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_status(telegram_user_id: int) -> str:
    """Check login status and verify PreForm connection."""
    creds = get_token(telegram_user_id)
    
    if not creds:
        return (
            "❌ *Not connected*\n\n"
            "Use /login to connect your Formlabs account."
        )
    
    # Try to verify the connection actually works
    client = get_client_for_user(telegram_user_id)
    fleet_info = ""
    
    if client:
        try:
            result = client.list_devices()
            devices = result.get('devices', [])
            
            # Count actual printers
            total_printers = 0
            total_groups = 0
            for group in devices:
                printers = group.get('printers', [])
                if printers:
                    total_printers += len(printers)
                    total_groups += 1
            
            fleet_info = f"• Fleet: {total_printers} printers in {total_groups} groups\n"
        except Exception as e:
            fleet_info = f"• Fleet: Unable to fetch ({str(e)[:30]})\n"
    
    status_msg = (
        f"✅ *Connected to Formlabs*\n\n"
        f"• Account: {creds.username}\n"
        f"• Telegram ID: {creds.telegram_user_id}\n"
        f"{fleet_info}"
    )
    
    if creds.expires_at:
        status_msg += f"• Token expires: {creds.expires_at}\n"
    
    return status_msg


def cmd_logout(telegram_user_id: int) -> str:
    """Logout the user."""
    creds = get_token(telegram_user_id)
    
    if not creds:
        return "You're not currently logged in."
    
    if delete_token(telegram_user_id):
        return f"✅ Logged out successfully.\nYour Formlabs credentials for {creds.username} have been removed."
    else:
        return "❌ Failed to log out. Please try again."


def cmd_printers(telegram_user_id: int) -> str:
    """List all printers for the user."""
    # Check approval
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval. Please contact @marcus_liangzhu"
    
    client = get_client_for_user(telegram_user_id)
    
    if not client:
        return "❌ Not logged in. Use /login first."
    
    try:
        result = client.list_devices()
        devices = result.get('devices', [])
        
        if not devices:
            return "No printers found in your account."
        
        # Count printers per group
        total_printers = 0
        active_groups = []
        
        for group in devices:
            printers = group.get('printers', [])
            if printers:
                total_printers += len(printers)
                active_groups.append({
                    'name': group.get('id', 'Unknown'),
                    'count': len(printers),
                    'online': group.get('is_connected', False)
                })
        
        # Build response
        response = (
            f"🖨️ *Your Formlabs Fleet*\n"
            f"{total_printers} printers across {len(active_groups)} groups\n"
            f"{'=' * 30}\n\n"
        )
        
        # Show top groups (limit to avoid message too long)
        for group in active_groups[:10]:
            emoji = "🟢" if group['online'] else "🔴"
            response += f"{emoji} {group['name']}: {group['count']} printers\n"
        
        if len(active_groups) > 10:
            response += f"\n... and {len(active_groups) - 10} more groups"
        
        return response
        
    except PreFormError as e:
        return f"❌ API Error: {e.detail}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_materials(telegram_user_id: int) -> str:
    """List available materials."""
    # Check approval
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval. Please contact @marcus_liangzhu"
    
    response = (
        "🧪 *Available Materials*\n"
        "=" * 30 + "\n\n"
    )
    
    # Group by category
    categories = {}
    for code, info in MATERIALS.items():
        cat = info.get('category', 'Other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(info['name'])
    
    for category, names in categories.items():
        response += f"*{category}*\n"
        for name in names:
            response += f"  • {name}\n"
        response += "\n"
    
    return response


def cmd_jobs(telegram_user_id: int, status_filter: str | None = None) -> str:
    """List print jobs."""
    # Check approval
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval. Please contact @marcus_liangzhu"
    
    client = get_client_for_user(telegram_user_id)
    
    if not client:
        return "❌ Not logged in. Use /login first."
    
    try:
        jobs = client.list_jobs(status=status_filter)
        
        if not jobs:
            return "📭 No print jobs found."
        
        response = (
            f"📋 *Print Jobs*\n"
            f"{'=' * 30}\n\n"
        )
        
        # Show recent jobs (limit to 10)
        for job in jobs[:10]:
            job_name = job.get('name', 'Unnamed')
            job_status = job.get('status', 'Unknown')
            printer = job.get('printer', 'Unknown')
            
            # Status emoji
            status_emoji = {
                'printing': '▶️',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '🚫',
                'queued': '⏳'
            }.get(job_status.lower(), '⬜')
            
            response += f"{status_emoji} *{job_name}*\n"
            response += f"   Status: {job_status}\n"
            response += f"   Printer: {printer}\n\n"
        
        if len(jobs) > 10:
            response += f"... and {len(jobs) - 10} more jobs"
        
        return response
        
    except PreFormError as e:
        return f"❌ API Error: {e.detail}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_approve(admin_id: int, target_user_id: int) -> str:
    """Admin: Approve a new user."""
    if not is_admin(admin_id):
        return "❌ This command is only for admins."
    
    if approve_user(target_user_id, admin_id):
        return (
            f"✅ User {target_user_id} has been approved!\n\n"
            f"Total approved users: {get_approved_count()}"
        )
    else:
        return "❌ Failed to approve user."


def cmd_reject(admin_id: int, target_user_id: int) -> str:
    """Admin: Reject/remove a user."""
    if not is_admin(admin_id):
        return "❌ This command is only for admins."
    
    if reject_user(target_user_id, admin_id):
        return (
            f"🚫 User {target_user_id} has been rejected/removed.\n\n"
            f"Total approved users: {get_approved_count()}"
        )
    else:
        return "❌ Failed to reject user."


def cmd_list_users(admin_id: int) -> str:
    """Admin: List all approved users."""
    if not is_admin(admin_id):
        return "❌ This command is only for admins."
    
    from approval_system import _load_approved
    approved = _load_approved()
    
    lines = [
        f"👥 *Approved Users* ({len(approved)} total)",
        "=" * 30,
        ""
    ]
    
    for user_id in sorted(approved):
        is_admin_badge = "👑 " if user_id in [6217674573] else ""
        lines.append(f"{is_admin_badge}`{user_id}`")
    
    return "\n".join(lines)


def cmd_help(telegram_user_id: int) -> str:
    """Show help message."""
    is_user_admin = is_admin(telegram_user_id)

    help_text = (
        "🤖 *Kim Formlabs Bot Commands*\n\n"
        "*Account:*\n"
        "/login - Connect your Formlabs account\n"
        "/status - Check connection status\n"
        "/logout - Disconnect your account\n\n"
        "*Fleet:*\n"
        "/printers - List your printers\n"
        "/fleet - Fleet dashboard overview\n"
        "/fleet stats - Utilization statistics\n\n"
        "*Printing:*\n"
        "/jobs - View print jobs\n"
        "/progress - Active print progress & ETA\n"
        "/queue - View print queue\n"
        "/cancel JOB\\_ID - Cancel a print job\n\n"
        "*Consumables:*\n"
        "/cartridges - Resin cartridge levels\n"
        "/tanks - Tank lifecycle status\n"
        "/materials - Available materials\n\n"
        "*Tools:*\n"
        "/cost - Print cost estimation\n"
        "/maintenance - Maintenance schedule\n"
        "/notify on|off - Print notifications\n\n"
        "/kim on|off - Natural language mode\n"
        "/help - This message"
    )

    if is_user_admin:
        help_text += (
            "\n\n*Admin Commands:*\n"
            "/approve USER\\_ID - Approve a new user\n"
            "/reject USER\\_ID - Reject/remove a user\n"
            "/users - List all approved users"
        )

    return help_text


# ============================================================================
# NEW FEATURE COMMANDS
# ============================================================================

def cmd_fixture(telegram_user_id: int, args: list = None) -> str:
    """Generate fixture for object.
    
    Usage: /fixture <object> [--operation <op>] [--clearance <mm>]
    Examples:
      /fixture iphone_15_pro --operation soldering
      /fixture my_part.stl --operation drilling --clearance 10
    """
    if not HAS_FIXTURE:
        return "❌ Fixture generator not available. Install required dependencies."
    
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval. Please contact @marcus_liangzhu"
    
    if not args:
        # List available standard objects
        available = StandardLibrary.list_all()
        return (
            "🔧 *Fixture Generator*\n\n"
            "Generate custom holding jigs for your prints.\n\n"
            "*Usage:*\n"
            "/fixture <object> [--operation <op>]\n\n"
            "*Operations:* drilling, soldering, painting, cnc, inspection\n\n"
            "*Standard Objects:*\n"
            + "\n".join(f"  • {key}" for key in available[:10])
            + (f"\n  ... and {len(available)-10} more" if len(available) > 10 else "")
            + "\n\nOr upload an STL file:\n"
            "/fixture my_custom_part.stl --operation drilling"
        )
    
    target = args[0]
    
    # Parse options
    operation = "drilling"
    clearance = 5.0
    
    if "--operation" in args:
        idx = args.index("--operation")
        if idx + 1 < len(args):
            operation = args[idx + 1]
    
    if "--clearance" in args:
        idx = args.index("--clearance")
        if idx + 1 < len(args):
            try:
                clearance = float(args[idx + 1])
            except ValueError:
                pass
    
    # Generate fixture
    result = generate_fixture(
        target=target,
        operation=operation,
        clearance=clearance,
        output_dir=f"./fixtures/{telegram_user_id}"
    )
    
    if result["success"]:
        response = (
            f"✅ *Fixture Generated*\n\n"
            f"Object: {result['object_name']}\n"
            f"Operation: {operation}\n"
            f"Dimensions: {result['dimensions'][0]:.1f} x {result['dimensions'][1]:.1f} x {result['dimensions'][2]:.1f} mm\n\n"
        )
        
        if result.get("stl_path"):
            response += f"📁 STL: {result['stl_path']}\n"
        
        response += f"📁 OpenSCAD: {result['scad_path']}\n\n"
        response += "Send the SCAD file to OpenSCAD or use /print to queue it."
        
        return response
    else:
        return f"❌ {result.get('error', 'Unknown error')}"


def cmd_resin(telegram_user_id: int, args: list = None) -> str:
    """Show resin status."""
    if not HAS_RESIN:
        return "❌ Resin prophet not available."
    
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."
    
    if args and args[0] == "add":
        # Add cartridge
        if len(args) < 3:
            return "Usage: /resin add <material_code> <material_name>"
        
        return cmd_resin_add(telegram_user_id, args[1], args[2])
    
    if args and args[0] == "alert":
        return cmd_resin_alert(telegram_user_id)
    
    return cmd_resin_status(telegram_user_id)


def cmd_csi_command(telegram_user_id: int, args: list = None, image_path: str = None) -> str:
    """Analyze failed print photo.
    
    Usage: /csi (with attached photo)
    """
    if not HAS_CSI:
        return "❌ CSI analyzer not available. Set OPENAI_API_KEY environment variable."
    
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."
    
    if not image_path:
        return (
            "🔍 *CSI: Print Crime Scene Investigation*\n\n"
            "Upload a photo of your failed print and I'll analyze it.\n\n"
            "*What I can detect:*\n"
            "• Support failures\n"
            "• Layer shifts\n"
            "• Warping\n"
            "• Resin contamination\n"
            "• Exposure issues\n"
            "• And more...\n\n"
            "Send a photo with caption /csi"
        )
    
    return cmd_csi(image_path)


# ============================================================================
# WEB API FEATURE COMMANDS
# ============================================================================

def _get_web_client(telegram_user_id: int):
    """Get a FormlabsWebClient for the user. Returns None if not configured."""
    try:
        from mcp_formlabs.web_api_client import FormlabsWebClient
        client = FormlabsWebClient()
        if client.client_id and client.client_secret:
            client.authenticate()
            return client
    except Exception:
        pass
    return None


def cmd_cancel(telegram_user_id: int, args: list = None) -> str:
    """Cancel a print job."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    if not args:
        return "Usage: /cancel <job_id>\n\nUse /jobs to see active job IDs."

    client = get_client_for_user(telegram_user_id)
    if not client:
        return "❌ Not logged in. Use /login first."

    job_id = args[0]
    try:
        client.cancel_job(job_id)
        return f"🚫 Job `{job_id}` has been cancelled."
    except PreFormError as e:
        return f"❌ Cancel failed: {e.detail}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_progress(telegram_user_id: int, args: list = None) -> str:
    """Show progress of active prints."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    web_client = _get_web_client(telegram_user_id)
    if not web_client:
        return "❌ Web API not configured. Set FORMLABS_CLIENT_ID and FORMLABS_CLIENT_SECRET."

    try:
        result = web_client.list_prints(status="PRINTING", per_page=20)
        prints = result.get("results", []) if isinstance(result, dict) else result

        if not prints:
            return "📭 No active prints right now."

        lines = ["▶️ *Active Prints*", "=" * 28, ""]

        for p in prints:
            name = p.get("name", "Unknown")
            printer = p.get("printer", "unknown")
            current_layer = p.get("currently_printing_layer", 0) or 0
            total_layers = p.get("layer_count", 0) or 0
            eta_ms = p.get("estimated_time_remaining_ms", 0) or 0

            percent = (current_layer / total_layers * 100) if total_layers > 0 else 0
            bar_filled = int(percent / 100 * 15)
            bar = f"[{'█' * bar_filled}{'░' * (15 - bar_filled)}]"

            eta_str = ""
            if eta_ms > 0:
                hours = eta_ms // 3_600_000
                minutes = (eta_ms % 3_600_000) // 60_000
                eta_str = f" | ETA: {hours}h {minutes}m"

            lines.append(f"*{name}*")
            lines.append(f"  Printer: {printer}")
            lines.append(f"  {bar} {percent:.0f}%{eta_str}")
            lines.append(f"  Layer {current_layer:,}/{total_layers:,}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_cost(telegram_user_id: int, args: list = None) -> str:
    """Show print cost estimates."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    web_client = _get_web_client(telegram_user_id)
    if not web_client:
        return "❌ Web API not configured. Set FORMLABS_CLIENT_ID and FORMLABS_CLIENT_SECRET."

    try:
        from mcp_formlabs.cost_calculator import summarize_costs, format_cost_report
        from datetime import datetime, timedelta

        period = (args[0] if args else "month").lower()
        if period == "today":
            since = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        elif period == "week":
            since = (datetime.now() - timedelta(days=7)).isoformat()
        elif period == "all":
            since = None
        else:
            since = (datetime.now() - timedelta(days=30)).isoformat()

        params = {"status": "FINISHED", "per_page": 100}
        if since:
            params["date__gt"] = since

        result = web_client.list_prints(**params)
        prints = result.get("results", []) if isinstance(result, dict) else result
        summary = summarize_costs(prints)
        return format_cost_report(summary)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_cartridges(telegram_user_id: int) -> str:
    """Show cartridge status."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    web_client = _get_web_client(telegram_user_id)
    if not web_client:
        return "❌ Web API not configured. Set FORMLABS_CLIENT_ID and FORMLABS_CLIENT_SECRET."

    try:
        result = web_client.list_cartridges(per_page=50)
        carts = result.get("results", []) if isinstance(result, dict) else result

        if not carts:
            return "🧪 No cartridges found."

        lines = ["🧪 *Cartridge Status*", "=" * 28, ""]

        for c in carts:
            initial = c.get("initial_volume_ml", 0) or 0
            dispensed = c.get("volume_dispensed_ml", 0) or 0
            remaining = max(0, initial - dispensed)
            percent = (remaining / initial * 100) if initial > 0 else 0
            is_empty = c.get("is_empty", False)
            material = c.get("material", "unknown")

            if is_empty or percent < 10:
                icon = "🔴"
            elif percent < 30:
                icon = "🟡"
            else:
                icon = "🟢"

            bar_filled = int(percent / 100 * 10)
            bar = f"[{'█' * bar_filled}{'░' * (10 - bar_filled)}]"

            name = c.get("display_name", c.get("serial", "unknown")[:12])
            lines.append(f"{icon} *{name}*")
            lines.append(f"   Material: {material}")
            lines.append(f"   {bar} {percent:.0f}% ({remaining:.0f}ml / {initial:.0f}ml)")
            if c.get("inside_printer"):
                lines.append(f"   In: {c['inside_printer']}")
            lines.append("")

        low = sum(1 for c in carts if (c.get("initial_volume_ml", 0) or 0) - (c.get("volume_dispensed_ml", 0) or 0) < (c.get("initial_volume_ml", 1) or 1) * 0.3)
        if low:
            lines.append(f"⚠️ {low} cartridge(s) below 30% — consider reordering!")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_tanks(telegram_user_id: int) -> str:
    """Show tank status."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    web_client = _get_web_client(telegram_user_id)
    if not web_client:
        return "❌ Web API not configured. Set FORMLABS_CLIENT_ID and FORMLABS_CLIENT_SECRET."

    try:
        from mcp_formlabs.tank_monitor import format_tank_status
        result = web_client.list_tanks(per_page=50)
        tanks = result.get("results", []) if isinstance(result, dict) else result
        return format_tank_status(tanks)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_fleet(telegram_user_id: int, args: list = None) -> str:
    """Show fleet dashboard."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    web_client = _get_web_client(telegram_user_id)
    if not web_client:
        return "❌ Web API not configured. Set FORMLABS_CLIENT_ID and FORMLABS_CLIENT_SECRET."

    try:
        from mcp_formlabs.fleet_analytics import format_fleet_overview, format_fleet_stats, compute_fleet_stats
        from datetime import datetime, timedelta

        printers = web_client.list_printers()

        if args and args[0] == "stats":
            since = (datetime.now() - timedelta(days=30)).isoformat()
            result = web_client.list_prints(date__gt=since, per_page=100)
            prints = result.get("results", []) if isinstance(result, dict) else result
            stats = compute_fleet_stats(printers, prints)
            return format_fleet_stats(stats)

        return format_fleet_overview(printers)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_queue(telegram_user_id: int, args: list = None) -> str:
    """Show print queue."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    web_client = _get_web_client(telegram_user_id)
    if not web_client:
        return "❌ Web API not configured. Set FORMLABS_CLIENT_ID and FORMLABS_CLIENT_SECRET."

    try:
        groups = web_client.list_groups()
        all_items = []

        for group in groups:
            gid = group.get("id", "")
            gname = group.get("name", "Unknown")
            items = web_client.get_group_queue(gid)
            for item in items:
                item["_group_name"] = gname
                all_items.append(item)

        if not all_items:
            result = web_client.list_prints(status="QUEUED", per_page=20)
            queued = result.get("results", []) if isinstance(result, dict) else result
            if not queued:
                return "📭 Print queue is empty."

            lines = ["📋 *Print Queue*", "=" * 28, ""]
            for i, p in enumerate(queued, 1):
                name = p.get("name", "Unknown")
                material = p.get("material_name", p.get("material", "?"))
                lines.append(f"  {i}. {name} ({material})")
            return "\n".join(lines)

        lines = ["📋 *Print Queue*", "=" * 28, ""]
        for i, item in enumerate(all_items, 1):
            name = item.get("name", "Unknown")
            material = item.get("material_name", "?")
            group = item.get("_group_name", "?")
            lines.append(f"  {i}. {name} ({material}) — {group}")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_maintenance(telegram_user_id: int, args: list = None) -> str:
    """Show maintenance schedule."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    try:
        from mcp_formlabs.maintenance_tracker import MaintenanceTracker, format_maintenance_status

        tracker = MaintenanceTracker()

        if args and len(args) >= 3 and args[0] == "done":
            task_id = args[1]
            printer_serial = args[2]
            if tracker.mark_done(telegram_user_id, printer_serial, task_id):
                return f"✅ Marked *{task_id}* as done for {printer_serial}."
            return f"❌ Unknown task: {task_id}"

        # Get printers to show maintenance for
        web_client = _get_web_client(telegram_user_id)
        if not web_client:
            return "❌ Web API not configured. Set FORMLABS_CLIENT_ID and FORMLABS_CLIENT_SECRET."

        printers = web_client.list_printers()
        if not printers:
            return "No printers found."

        lines = ["🔧 *Maintenance Schedule*", "=" * 28, ""]
        for p in printers[:5]:
            serial = p.get("serial", "unknown")
            alias = p.get("alias", serial)
            tasks = tracker.get_due_tasks(telegram_user_id, serial)
            overdue = [t for t in tasks if t["status"] in ("overdue", "never_done")]
            if overdue:
                lines.append(f"⚠️ *{alias}* ({len(overdue)} overdue)")
                for t in overdue[:3]:
                    lines.append(f"   🔴 {t['name']}")
            else:
                lines.append(f"✅ *{alias}* — all up to date")
            lines.append("")

        lines.append("Details: `/maintenance done <task_id> <printer_serial>`")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cmd_notify(telegram_user_id: int, args: list = None) -> str:
    """Manage print notifications."""
    if not is_approved(telegram_user_id):
        return "⏳ Access pending approval."

    try:
        from mcp_formlabs.notification_service import NotificationDB

        db = NotificationDB()
        action = (args[0] if args else "status").lower()

        if action == "on":
            printer = args[1] if len(args) > 1 else "*"
            db.subscribe(telegram_user_id, printer)
            target = "all printers" if printer == "*" else printer
            return f"🔔 Notifications enabled for {target}.\n\nYou'll receive alerts when prints finish, fail, or encounter errors."

        if action == "off":
            db.unsubscribe(telegram_user_id)
            return "🔕 Notifications disabled."

        # Status
        is_sub = db.is_subscribed(telegram_user_id)
        if is_sub:
            return "🔔 Notifications: *Enabled*\n\nUse `/notify off` to disable."
        return "🔕 Notifications: *Disabled*\n\nUse `/notify on` to enable."
    except Exception as e:
        return f"❌ Error: {str(e)}"


# Command dispatcher
COMMANDS = {
    '/login': cmd_login,
    '/status': cmd_status,
    '/logout': cmd_logout,
    '/printers': cmd_printers,
    '/printer': cmd_printers,
    '/materials': cmd_materials,
    '/jobs': cmd_jobs,
    '/help': cmd_help,
    '/approve': cmd_approve,
    '/reject': cmd_reject,
    '/users': cmd_list_users,
    # Original advanced features
    '/fixture': cmd_fixture,
    '/resin': cmd_resin,
    '/csi': cmd_csi_command,
    # New features (Web API powered)
    '/cancel': cmd_cancel,
    '/progress': cmd_progress,
    '/cost': cmd_cost,
    '/cartridges': cmd_cartridges,
    '/tanks': cmd_tanks,
    '/fleet': cmd_fleet,
    '/queue': cmd_queue,
    '/maintenance': cmd_maintenance,
    '/notify': cmd_notify,
}


def handle_command(command: str, telegram_user_id: int, args: list = None, username: str = None) -> str:
    """Handle a bot command."""
    cmd_func = COMMANDS.get(command.lower())

    if not cmd_func:
        return f"Unknown command: {command}. Use /help for available commands."

    # Commands that take (user_id, target_id)
    if command.lower() in ['/approve', '/reject']:
        if not args:
            return f"Usage: {command} USER_ID"
        try:
            target_id = int(args[0])
            return cmd_func(telegram_user_id, target_id)
        except ValueError:
            return f"Invalid user ID. Usage: {command} USER_ID"

    # Commands that take (user_id, args)
    if command.lower() in ['/fixture', '/resin', '/csi', '/cancel', '/cost', '/fleet', '/queue', '/maintenance', '/notify']:
        return cmd_func(telegram_user_id, args)

    # Commands that need username
    if command.lower() == '/login':
        return cmd_func(telegram_user_id, username)

    # Commands with optional status filter
    if command.lower() == '/jobs' and args:
        return cmd_jobs(telegram_user_id, status_filter=args[0])

    # Simple commands (user_id only)
    return cmd_func(telegram_user_id)


if __name__ == "__main__":
    # Test mode
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("--user-id", type=int, default=6217674573)
    args = parser.parse_args()
    
    result = handle_command(args.command, args.user_id)
    print(result)
