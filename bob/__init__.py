"""
Bob - Kim Formlabs Telegram Bot

Bob is the Telegram bot interface for the Kim Formlabs printing assistant.
He handles user commands, authentication, and integrates with the Formlabs API.

Usage:
    python -m bob
    
Or:
    python bob/bot.py
"""

__version__ = "1.0.0"
__author__ = "Markus"

from .bot import run_bot, create_bot
from .commands import handle_command, COMMANDS

__all__ = ["run_bot", "create_bot", "handle_command", "COMMANDS"]
