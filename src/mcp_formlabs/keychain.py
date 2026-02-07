"""Secure token storage using macOS Keychain.

Stores Formlabs auth tokens per Telegram user ID for multi-tenant support.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

SERVICE_NAME = "mcp-formlabs"
ACCOUNT_PREFIX = "telegram-"


class KeychainError(Exception):
    """Raised when a Keychain operation fails."""


@dataclass
class StoredCredentials:
    """Credentials stored in Keychain."""

    telegram_user_id: int
    formlabs_token: str
    username: str
    expires_at: str | None = None

    def to_json(self) -> str:
        return json.dumps({
            "telegram_user_id": self.telegram_user_id,
            "formlabs_token": self.formlabs_token,
            "username": self.username,
            "expires_at": self.expires_at,
        })

    @classmethod
    def from_json(cls, data: str) -> "StoredCredentials":
        obj = json.loads(data)
        return cls(
            telegram_user_id=obj["telegram_user_id"],
            formlabs_token=obj["formlabs_token"],
            username=obj["username"],
            expires_at=obj.get("expires_at"),
        )


def _account_name(telegram_user_id: int) -> str:
    """Generate account name for a Telegram user."""
    return f"{ACCOUNT_PREFIX}{telegram_user_id}"


def store_token(
    telegram_user_id: int,
    formlabs_token: str,
    username: str,
    expires_at: str | None = None,
) -> None:
    """Store Formlabs auth token in Keychain for a Telegram user.

    Args:
        telegram_user_id: The Telegram user's unique ID
        formlabs_token: The auth token from Formlabs API
        username: The Formlabs username (for display)
        expires_at: Optional token expiration timestamp
    """
    creds = StoredCredentials(
        telegram_user_id=telegram_user_id,
        formlabs_token=formlabs_token,
        username=username,
        expires_at=expires_at,
    )

    account = _account_name(telegram_user_id)

    # First try to delete any existing entry
    delete_token(telegram_user_id)

    # Add new entry
    cmd = [
        "security",
        "add-generic-password",
        "-a", account,
        "-s", SERVICE_NAME,
        "-w", creds.to_json(),
        "-U",  # Update if exists
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise KeychainError(f"Failed to store token: {result.stderr}")


def get_token(telegram_user_id: int) -> StoredCredentials | None:
    """Retrieve Formlabs auth token from Keychain for a Telegram user.

    Args:
        telegram_user_id: The Telegram user's unique ID

    Returns:
        StoredCredentials if found, None otherwise
    """
    account = _account_name(telegram_user_id)

    cmd = [
        "security",
        "find-generic-password",
        "-a", account,
        "-s", SERVICE_NAME,
        "-w",  # Output password only
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    try:
        return StoredCredentials.from_json(result.stdout.strip())
    except (json.JSONDecodeError, KeyError):
        return None


def delete_token(telegram_user_id: int) -> bool:
    """Delete Formlabs auth token from Keychain for a Telegram user.

    Args:
        telegram_user_id: The Telegram user's unique ID

    Returns:
        True if deleted, False if not found
    """
    account = _account_name(telegram_user_id)

    cmd = [
        "security",
        "delete-generic-password",
        "-a", account,
        "-s", SERVICE_NAME,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def list_users() -> list[int]:
    """List all Telegram user IDs with stored tokens.

    Returns:
        List of Telegram user IDs
    """
    cmd = [
        "security",
        "dump-keychain",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []

    users = []
    for line in result.stdout.split("\n"):
        if f'"svce"<blob>="{SERVICE_NAME}"' in line or f'"acct"<blob>="{ACCOUNT_PREFIX}' in line:
            # Parse account name from dump
            if ACCOUNT_PREFIX in line:
                try:
                    start = line.find(ACCOUNT_PREFIX) + len(ACCOUNT_PREFIX)
                    end = line.find('"', start)
                    user_id = int(line[start:end])
                    if user_id not in users:
                        users.append(user_id)
                except (ValueError, IndexError):
                    continue
    return users


def get_formlabs_token_for_request(telegram_user_id: int) -> str | None:
    """Get just the Formlabs token for API requests.

    Args:
        telegram_user_id: The Telegram user's unique ID

    Returns:
        The Formlabs auth token string, or None if not found
    """
    creds = get_token(telegram_user_id)
    return creds.formlabs_token if creds else None
