#!/usr/bin/env python3
"""
Bob - Kim Formlabs Telegram Bot

The main bot runner that starts the Telegram bot and auth server.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from mcp_formlabs.auth_server import get_auth_server, set_login_callback
from mcp_formlabs.keychain import get_token, delete_token

# Import command handlers from commands module
from .commands import handle_command, is_approved

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    await update.message.reply_text(
        f"Welcome {user.first_name}! 👋\n\n"
        "I'm Bob, your Formlabs Dashboard assistant. I can help you:\n"
        "• Check printer status\n"
        "• Monitor print jobs\n"
        "• Manage your print queue\n\n"
        "Use /login to connect your Formlabs account.\n"
        "Use /status to check your login status.\n"
        "Use /logout to disconnect your account."
    )


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /login command - generates secure login link."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Check if already logged in
    existing = get_token(user_id)
    if existing:
        await update.message.reply_text(
            f"You're already logged in as {existing.username}.\n"
            "Use /logout first if you want to switch accounts."
        )
        return

    # Start auth server if not running
    auth_server = get_auth_server()
    if not auth_server.is_running:
        auth_server.start()
        await asyncio.sleep(0.5)

    # Generate login URL
    login_url = auth_server.get_login_url(user_id)

    # Set up callback for login completion
    async def on_login_complete(success: bool, message: str) -> None:
        if success:
            await update.message.reply_text(
                f"✅ {message}\n\n"
                "You can now use Formlabs commands:\n"
                "• /printers - List your printers\n"
                "• /jobs - View print jobs\n"
                "• /status - Check connection status"
            )
        else:
            await update.message.reply_text(f"❌ Login failed: {message}")

    def sync_callback(success: bool, message: str) -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(on_login_complete(success, message))
        except Exception:
            pass

    # Register callback
    token = login_url.split("/")[-1]
    set_login_callback(token, sync_callback)

    await update.message.reply_text(
        "🔐 *Secure Login*\n\n"
        "Click the link below to enter your Formlabs credentials securely:\n\n"
        f"👉 {login_url}\n\n"
        "_Your password is never sent through Telegram._\n"
        "_The link expires in 10 minutes._",
        parse_mode="Markdown",
    )


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /logout command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    existing = get_token(user_id)
    if not existing:
        await update.message.reply_text("You're not currently logged in.")
        return

    if delete_token(user_id):
        await update.message.reply_text(
            f"✅ Logged out successfully.\n"
            f"Your Formlabs credentials for {existing.username} have been removed."
        )
    else:
        await update.message.reply_text(
            "❌ Failed to log out. Please try again or contact support."
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    
    # Use the command handler from commands module
    result = handle_command('/status', user_id)
    await update.message.reply_text(result, parse_mode="Markdown")


async def printers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /printers command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    result = handle_command('/printers', user_id)
    await update.message.reply_text(result, parse_mode="Markdown")


async def printer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /printer command (alias for /printers)."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    result = handle_command('/printer', user_id)
    await update.message.reply_text(result, parse_mode="Markdown")


async def jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /jobs command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    args = context.args
    result = handle_command('/jobs', user_id, args=args)
    await update.message.reply_text(result, parse_mode="Markdown")


async def materials_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /materials command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    result = handle_command('/materials', user_id)
    await update.message.reply_text(result, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    result = handle_command('/help', user_id)
    await update.message.reply_text(result, parse_mode="Markdown")


async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /approve command (admin only)."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    args = context.args
    result = handle_command('/approve', user_id, args=args)
    await update.message.reply_text(result, parse_mode="Markdown")


async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reject command (admin only)."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    args = context.args
    result = handle_command('/reject', user_id, args=args)
    await update.message.reply_text(result, parse_mode="Markdown")


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /users command (admin only)."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    result = handle_command('/users', user_id)
    await update.message.reply_text(result, parse_mode="Markdown")


def create_bot(token: str | None = None) -> Application:
    """Create and configure Bob."""
    bot_token = token or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOB_TELEGRAM_TOKEN")
    if not bot_token:
        raise ValueError(
            "Telegram bot token required. Set TELEGRAM_BOT_TOKEN or BOB_TELEGRAM_TOKEN env var."
        )

    application = Application.builder().token(bot_token).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("printers", printers_command))
    application.add_handler(CommandHandler("printer", printer_command))
    application.add_handler(CommandHandler("jobs", jobs_command))
    application.add_handler(CommandHandler("materials", materials_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("reject", reject_command))
    application.add_handler(CommandHandler("users", users_command))

    return application


async def run_bot(token: str | None = None) -> None:
    """Run Bob."""
    # Start auth server
    auth_server = get_auth_server()
    auth_server.start()
    logger.info(f"Auth server started on http://{auth_server.host}:{auth_server.port}")

    # Create and run bot
    application = create_bot(token)
    logger.info("Starting Bob...")

    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        auth_server.stop()


def main():
    """Entry point for Bob."""
    import argparse

    parser = argparse.ArgumentParser(description="Bob - Kim Formlabs Telegram Bot")
    parser.add_argument(
        "--token",
        help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_bot(args.token))
    except KeyboardInterrupt:
        logger.info("Bob stopped by user")


if __name__ == "__main__":
    main()
