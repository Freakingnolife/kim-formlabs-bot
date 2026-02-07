#!/bin/bash
# Quick start script for Formlabs Telegram Bot with Cloudflare Tunnel
# Usage: ./start.sh YOUR_BOT_TOKEN

if [ -z "$1" ]; then
    echo "Usage: ./start.sh YOUR_BOT_TOKEN"
    echo ""
    echo "Get your token from @BotFather on Telegram:"
    echo "1. Open Telegram and search for @BotFather"
    echo "2. Send /newbot and follow instructions"
    echo "3. Copy the API token and run:"
    echo "   ./start.sh YOUR_TOKEN_HERE"
    exit 1
fi

export TELEGRAM_BOT_TOKEN="$1"
python3 start_bot_with_tunnel.py
