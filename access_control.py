#!/usr/bin/env python3
"""
Global Access Control for Kim (OpenClaw)
Only approved users can message the bot at all.
"""

import json
from pathlib import Path
from datetime import datetime

# Storage
ACCESS_FILE = Path(__file__).parent / "approved_users.json"
LOG_FILE = Path(__file__).parent / "access_requests.log"

# Admin users
ADMINS = {6217674573}  # Markus


def _load_data():
    """Load approved users data."""
    if not ACCESS_FILE.exists():
        data = {
            "approved": list(ADMINS),
            "pending": [],
            "rejected": [],
            "admin": list(ADMINS)
        }
        _save_data(data)
        return data
    
    try:
        with open(ACCESS_FILE, 'r') as f:
            data = json.load(f)
            # Ensure all keys exist
            for key in ["approved", "pending", "rejected", "admin"]:
                if key not in data:
                    data[key] = []
            return data
    except:
        return {"approved": list(ADMINS), "pending": [], "rejected": [], "admin": list(ADMINS)}


def _save_data(data):
    """Save approved users data."""
    with open(ACCESS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def _log_request(user_id: int, username: str, action: str):
    """Log access request."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] User {user_id} (@{username or 'unknown'}): {action}\n"
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)


def is_allowed(user_id: int) -> bool:
    """Check if user is allowed to access the bot."""
    data = _load_data()
    return user_id in data.get("approved", []) or user_id in ADMINS


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in ADMINS


def request_access(user_id: int, username: str = None, first_name: str = None) -> tuple[bool, str]:
    """
    Handle access request from new user.
    Returns: (allowed, message_to_user)
    """
    data = _load_data()
    
    # Check if already approved
    if user_id in data.get("approved", []):
        return True, ""
    
    # Check if already pending
    if user_id in data.get("pending", []):
        return False, get_pending_message()
    
    # Check if rejected
    if user_id in data.get("rejected", []):
        return False, get_rejected_message()
    
    # New request - add to pending
    data["pending"].append(user_id)
    _save_data(data)
    _log_request(user_id, username, "REQUESTED ACCESS")
    
    # Notify admin (this would be implemented in the bot layer)
    notify_admin_new_request(user_id, username, first_name)
    
    return False, get_pending_message()


def approve_user(user_id: int, admin_id: int) -> bool:
    """Admin approves a user."""
    if not is_admin(admin_id):
        return False
    
    data = _load_data()
    
    # Remove from pending/rejected if present
    if user_id in data.get("pending", []):
        data["pending"].remove(user_id)
    if user_id in data.get("rejected", []):
        data["rejected"].remove(user_id)
    
    # Add to approved
    if user_id not in data.get("approved", []):
        data["approved"].append(user_id)
    
    _save_data(data)
    _log_request(user_id, "", f"APPROVED by admin {admin_id}")
    
    return True


def reject_user(user_id: int, admin_id: int) -> bool:
    """Admin rejects a user."""
    if not is_admin(admin_id):
        return False
    
    data = _load_data()
    
    # Remove from pending/approved if present
    if user_id in data.get("pending", []):
        data["pending"].remove(user_id)
    if user_id in data.get("approved", []):
        data["approved"].remove(user_id)
    
    # Add to rejected
    if user_id not in data.get("rejected", []):
        data["rejected"].append(user_id)
    
    _save_data(data)
    _log_request(user_id, "", f"REJECTED by admin {admin_id}")
    
    return True


def get_stats() -> dict:
    """Get access statistics."""
    data = _load_data()
    return {
        "approved": len(data.get("approved", [])),
        "pending": len(data.get("pending", [])),
        "rejected": len(data.get("rejected", [])),
        "total_requests": sum([
            len(data.get("approved", [])),
            len(data.get("pending", [])),
            len(data.get("rejected", []))
        ]) - len(ADMINS)  # Exclude admins from count
    }


# Messages

def get_pending_message() -> str:
    return (
        "⏳ *Access Pending*\n\n"
        "Hello! This is a private bot.\n\n"
        "Your request has been sent to the admin for approval. "
        "You'll be notified once access is granted.\n\n"
        "_Please do not send multiple messages - this won't speed up the process._"
    )


def get_rejected_message() -> str:
    return (
        "❌ *Access Denied*\n\n"
        "Your request to use this bot has been declined.\n\n"
        "If you believe this is an error, please contact @marcus_liangzhu"
    )


def get_approved_notification() -> str:
    return (
        "✅ *Access Granted!*\n\n"
        "You can now use this bot.\n\n"
        "Available commands:\n"
        "• /help - See all commands\n"
        "• Formlabs features (if logged in)\n\n"
        "Welcome!"
    )


def notify_admin_new_request(user_id: int, username: str, first_name: str):
    """Notify admin of new access request."""
    # This would be implemented at the bot layer
    # For now, just log it
    name = first_name or username or f"User {user_id}"
    _log_request(user_id, username, f"NOTIFICATION: New request from {name}")


def get_admin_notification(user_id: int, username: str, first_name: str) -> str:
    """Get notification message for admin."""
    name = first_name or username or "Unknown"
    stats = get_stats()
    
    return (
        f"🔔 *New Access Request*\n\n"
        f"Name: {name}\n"
        f"Username: @{username or 'none'}\n"
        f"Telegram ID: `{user_id}`\n\n"
        f"To approve:\n"
        f"`/approve {user_id}`\n\n"
        f"To reject:\n"
        f"`/reject {user_id}`\n\n"
        f"_Pending requests: {stats['pending']}_"
    )
