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
    """Check login status."""
    creds = get_token(telegram_user_id)
    
    if not creds:
        return (
            "❌ *Not connected*\n\n"
            "Use /login to connect your Formlabs account."
        )
    
    status_msg = (
        f"✅ *Connected to Formlabs*\n\n"
        f"• Account: {creds.username}\n"
        f"• Telegram ID: {creds.telegram_user_id}\n"
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
        "/login - Connect your Formlabs account\n"
        "/status - Check connection status\n"
        "/logout - Disconnect your account\n"
        "/printers - List your printers\n"
        "/materials - Show available materials\n"
        "/jobs - View print jobs\n"
        "/help - Show this help message"
    )
    
    if is_user_admin:
        help_text += (
            "\n\n*Admin Commands:*\n"
            "/approve USER_ID - Approve a new user\n"
            "/reject USER_ID - Reject/remove a user\n"
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


# Command dispatcher
COMMANDS = {
    '/login': cmd_login,
    '/status': cmd_status,
    '/logout': cmd_logout,
    '/printers': cmd_printers,
    '/materials': cmd_materials,
    '/jobs': cmd_jobs,
    '/help': cmd_help,
    '/approve': cmd_approve,
    '/reject': cmd_reject,
    '/users': cmd_list_users,
    # New features
    '/fixture': cmd_fixture,
    '/resin': cmd_resin,
    '/csi': cmd_csi_command,
}


def handle_command(command: str, telegram_user_id: int, args: list = None, username: str = None) -> str:
    """Handle a bot command."""
    cmd_func = COMMANDS.get(command.lower())
    
    if not cmd_func:
        return f"Unknown command: {command}. Use /help for available commands."
    
    # Handle admin commands
    if command.lower() in ['/approve', '/reject']:
        if not args:
            return f"Usage: {command} USER_ID"
        try:
            target_id = int(args[0])
            return cmd_func(telegram_user_id, target_id)
        except ValueError:
            return f"Invalid user ID. Usage: {command} USER_ID"
    
    # Handle fixture command with args
    if command.lower() == '/fixture':
        return cmd_fixture(telegram_user_id, args)
    
    # Handle resin command with args
    if command.lower() == '/resin':
        return cmd_resin(telegram_user_id, args)
    
    # Handle CSI command (needs image path)
    if command.lower() == '/csi':
        # Image path would be passed separately in real implementation
        return cmd_csi_command(telegram_user_id, args)
    
    # Handle commands that need username
    if command.lower() == '/login':
        return cmd_func(telegram_user_id, username)
    
    # Call the command function
    if command.lower() == '/jobs' and args:
        return cmd_jobs(telegram_user_id, status_filter=args[0] if args else None)
    
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
