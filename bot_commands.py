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
