#!/usr/bin/env python3
"""
Access control wrapper for OpenClaw
Add this check at the START of message processing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from access_control import (
    is_allowed, request_access, approve_user, reject_user,
    get_stats, is_admin, get_admin_notification
)


def check_access(telegram_user_id: int, username: str = None, first_name: str = None) -> tuple[bool, str]:
    """
    Check if user is allowed to access Kim (OpenClaw).
    
    Returns:
        (allowed: bool, response: str)
        - If allowed=True, response is empty - process the message normally
        - If allowed=False, response is the message to send to user
    """
    from access_control import get_admin_notification
    
    # Check if already allowed
    if is_allowed(telegram_user_id):
        return True, ""
    
    # Request access
    allowed, message = request_access(telegram_user_id, username, first_name)
    
    return allowed, message


def handle_admin_command(command: str, admin_id: int, args: list = None) -> str:
    """
    Handle admin commands for access control.
    
    Commands:
    - /approve USER_ID
    - /reject USER_ID  
    - /access_stats
    """
    if not is_admin(admin_id):
        return "❌ This command is only for admins."
    
    if command == '/access_stats':
        stats = get_stats()
        return (
            f"📊 *Access Statistics*\n\n"
            f"✅ Approved: {stats['approved']}\n"
            f"⏳ Pending: {stats['pending']}\n"
            f"❌ Rejected: {stats['rejected']}\n"
            f"📈 Total Requests: {stats['total_requests']}"
        )
    
    if not args:
        return f"Usage: {command} USER_ID"
    
    try:
        target_id = int(args[0])
    except ValueError:
        return "Invalid user ID. Must be a number."
    
    if command == '/approve':
        if approve_user(target_id, admin_id):
            return f"✅ User {target_id} approved!"
        return "Failed to approve user."
    
    elif command == '/reject':
        if reject_user(target_id, admin_id):
            return f"🚫 User {target_id} rejected."
        return "Failed to reject user."
    
    return f"Unknown command: {command}"


if __name__ == "__main__":
    # Test mode
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("--user-id", type=int, default=12345)
    parser.add_argument("--username", default="testuser")
    args = parser.parse_args()
    
    if args.command == "check":
        allowed, msg = check_access(args.user_id, args.username)
        print(f"Allowed: {allowed}")
        if not allowed:
            print(f"Message: {msg}")
    elif args.command == "stats":
        print(get_stats())
    else:
        print(f"Unknown command: {args.command}")
