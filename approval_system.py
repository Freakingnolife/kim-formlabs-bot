#!/usr/bin/env python3
"""
User approval system for Kim Formlabs Bot
Only approved users can access Formlabs features
"""

import json
import os
from pathlib import Path

# File to store approved users
APPROVAL_FILE = Path(__file__).parent / "approved_users.json"

# Admin user IDs (you)
ADMIN_USERS = {6217674573}  # Markus


def _load_approved() -> set:
    """Load approved user IDs from file."""
    if not APPROVAL_FILE.exists():
        # Auto-approve admin
        _save_approved(ADMIN_USERS)
        return ADMIN_USERS
    
    try:
        with open(APPROVAL_FILE, 'r') as f:
            data = json.load(f)
            return set(data.get('approved', []))
    except Exception:
        return ADMIN_USERS


def _save_approved(approved: set):
    """Save approved user IDs to file."""
    with open(APPROVAL_FILE, 'w') as f:
        json.dump({
            'approved': list(approved),
            'admin': list(ADMIN_USERS)
        }, f, indent=2)


def is_approved(telegram_user_id: int) -> bool:
    """Check if a user is approved."""
    approved = _load_approved()
    return telegram_user_id in approved or telegram_user_id in ADMIN_USERS


def is_admin(telegram_user_id: int) -> bool:
    """Check if user is admin."""
    return telegram_user_id in ADMIN_USERS


def approve_user(telegram_user_id: int, approved_by: int) -> bool:
    """Approve a new user. Only admins can do this."""
    if not is_admin(approved_by):
        return False
    
    approved = _load_approved()
    approved.add(telegram_user_id)
    _save_approved(approved)
    return True


def reject_user(telegram_user_id: int, rejected_by: int) -> bool:
    """Remove a user's approval. Only admins can do this."""
    if not is_admin(rejected_by):
        return False
    
    approved = _load_approved()
    approved.discard(telegram_user_id)
    _save_approved(approved)
    return True


def get_pending_users() -> list:
    """Get list of users who tried to login but aren't approved yet.
    This would need to be integrated with the keychain system."""
    # For now, return empty - we'll track this separately if needed
    return []


def get_approved_count() -> int:
    """Get number of approved users."""
    return len(_load_approved())


# Approval-related messages

def get_approval_request_message(user_id: int, username: str = None) -> str:
    """Message shown to new users requesting approval."""
    name = username or f"User {user_id}"
    return (
        f"⏳ *Approval Required*\n\n"
        f"Hello {name}!\n\n"
        f"This is a private Formlabs bot. Your access request has been sent to the admin.\n\n"
        f"Your Telegram ID: `{user_id}`\n\n"
        f"Please contact @marcus_liangzhu for access."
    )


def get_admin_approval_notification(user_id: int, username: str = None) -> str:
    """Notification sent to admin when new user tries to login."""
    name = username or f"User {user_id}"
    return (
        f"🔔 *New User Request*\n\n"
        f"Name: {name}\n"
        f"Telegram ID: `{user_id}`\n\n"
        f"To approve, reply with:\n"
        f"`/approve {user_id}`\n\n"
        f"To reject:\n"
        f"`/reject {user_id}`"
    )


def get_approved_message() -> str:
    """Message shown to newly approved users."""
    return (
        "✅ *Access Granted!*\n\n"
        "You can now use Formlabs commands:\n"
        "• /login - Connect your Formlabs account\n"
        "• /printers - List your printers\n"
        "• /materials - View available materials\n"
        "• /help - See all commands"
    )


def get_rejected_message() -> str:
    """Message shown to rejected users."""
    return (
        "❌ *Access Denied*\n\n"
        "Your request to use this bot has been declined.\n\n"
        "If you believe this is an error, please contact @marcus_liangzhu"
    )
