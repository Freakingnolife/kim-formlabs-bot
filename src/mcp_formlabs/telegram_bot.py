"""Telegram bot handlers for Formlabs Dashboard authentication.

Provides /login command that generates a secure web link for credential input.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from mcp_formlabs.auth_server import get_auth_server, set_login_callback
from mcp_formlabs.keychain import get_token, delete_token, StoredCredentials

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
        "I'm your Formlabs Dashboard assistant. I can help you:\n"
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
        await asyncio.sleep(0.5)  # Give server time to start

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

    # Note: callback needs to be sync for the auth server
    def sync_callback(success: bool, message: str) -> None:
        # Schedule the async callback in the event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(on_login_complete(success, message))
        except Exception:
            pass  # Best effort notification

    # Register callback (token is in the URL path)
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
    """Handle /logout command - removes stored credentials."""
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
    """Handle /status command - shows login status."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    creds = get_token(user_id)
    if creds:
        status_msg = (
            "✅ *Connected to Formlabs*\n\n"
            f"• Account: {creds.username}\n"
            f"• Telegram ID: {creds.telegram_user_id}\n"
        )
        if creds.expires_at:
            status_msg += f"• Token expires: {creds.expires_at}\n"

        await update.message.reply_text(status_msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "❌ *Not connected*\n\n"
            "Use /login to connect your Formlabs account.",
            parse_mode="Markdown",
        )


async def printers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /printers command - lists available printers."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    creds = get_token(user_id)
    if not creds:
        await update.message.reply_text(
            "Please /login first to access your printers."
        )
        return

    # Import here to avoid circular dependency
    from mcp_formlabs.preform_client import PreFormClient, PreFormError

    client = PreFormClient()
    # TODO: Add token to client session headers for authenticated requests

    try:
        devices = client.list_devices()
        if not devices:
            await update.message.reply_text("No printers found in your fleet.")
            return

        msg = "🖨 *Your Printers*\n\n"
        for device in devices[:10]:  # Limit to 10
            name = device.get("name", "Unknown")
            status = device.get("status", "unknown")
            emoji = "🟢" if status == "ready" else "🟡" if status == "printing" else "🔴"
            msg += f"{emoji} {name} - {status}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except PreFormError as e:
        await update.message.reply_text(f"❌ Error fetching printers: {e}")


async def jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /jobs command - lists print jobs."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    creds = get_token(user_id)
    if not creds:
        await update.message.reply_text("Please /login first to view your jobs.")
        return

    from mcp_formlabs.preform_client import PreFormClient, PreFormError

    client = PreFormClient()

    try:
        jobs = client.list_jobs()
        if not jobs:
            await update.message.reply_text("No print jobs found.")
            return

        msg = "📋 *Print Jobs*\n\n"
        for job in jobs[:10]:  # Limit to 10
            name = job.get("name", "Unnamed")
            status = job.get("status", "unknown")
            emoji = (
                "✅" if status == "completed" else
                "🔄" if status == "printing" else
                "⏳" if status == "queued" else "❓"
            )
            msg += f"{emoji} {name} - {status}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except PreFormError as e:
        await update.message.reply_text(f"❌ Error fetching jobs: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.message:
        return

    await update.message.reply_text(
        "*Formlabs Bot Commands*\n\n"
        "/login - Connect your Formlabs account\n"
        "/logout - Disconnect your account\n"
        "/status - Check connection status\n"
        "/printers - List your printers\n"
        "/jobs - View print jobs\n"
        "/help - Show this help message",
        parse_mode="Markdown",
    )


def create_bot(token: str | None = None) -> Application:
    """Create and configure the Telegram bot application.

    Args:
        token: Telegram bot token. If None, reads from TELEGRAM_BOT_TOKEN env var.

    Returns:
        Configured Application instance
    """
    bot_token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError(
            "Telegram bot token required. Set TELEGRAM_BOT_TOKEN env var."
        )

    application = Application.builder().token(bot_token).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("printers", printers_command))
    application.add_handler(CommandHandler("jobs", jobs_command))
    application.add_handler(CommandHandler("help", help_command))

    return application


async def run_bot(token: str | None = None) -> None:
    """Run the Telegram bot.

    Args:
        token: Telegram bot token. If None, reads from TELEGRAM_BOT_TOKEN env var.
    """
    # Start auth server
    auth_server = get_auth_server()
    auth_server.start()
    logger.info(f"Auth server started on http://{auth_server.host}:{auth_server.port}")

    # Create and run bot
    application = create_bot(token)
    logger.info("Starting Telegram bot...")

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
    """Entry point for the Telegram bot."""
    import argparse

    parser = argparse.ArgumentParser(description="Formlabs Telegram Bot")
    parser.add_argument(
        "--token",
        help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)",
    )
    parser.add_argument(
        "--auth-host",
        default="127.0.0.1",
        help="Auth server host",
    )
    parser.add_argument(
        "--auth-port",
        type=int,
        default=8765,
        help="Auth server port",
    )
    args = parser.parse_args()

    # Configure auth server
    from mcp_formlabs.auth_server import _auth_server, AuthServer
    global _auth_server
    _auth_server = AuthServer(host=args.auth_host, port=args.auth_port)

    try:
        asyncio.run(run_bot(args.token))
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


if __name__ == "__main__":
    main()
