#!/bin/bash
# Start Formlabs Telegram Bot with Cloudflare Tunnel
# Usage: ./start_bot.sh YOUR_BOT_TOKEN

set -e

BOT_TOKEN="${1:-$TELEGRAM_BOT_TOKEN}"

if [ -z "$BOT_TOKEN" ]; then
    echo "Error: No bot token provided"
    echo "Usage: ./start_bot.sh YOUR_BOT_TOKEN"
    echo "Or set TELEGRAM_BOT_TOKEN environment variable"
    exit 1
fi

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

echo "🚀 Starting Formlabs Telegram Bot with Cloudflare Tunnel..."
echo ""

# Start the auth server in background
echo "📡 Starting auth server on http://127.0.0.1:8765..."
python -c "
import sys
sys.path.insert(0, 'src')
from mcp_formlabs.auth_server import get_auth_server
server = get_auth_server()
server.start()
import time
time.sleep(60*60*24)  # Keep running
" &
AUTH_PID=$!

# Wait for auth server to start
sleep 2

echo ""
echo "🌐 Starting Cloudflare Tunnel..."
echo "   This will create a public URL that remote users can access"
echo "   (The URL will appear below - copy it for your users!)"
echo ""

# Create a temp file for the tunnel URL
TUNNEL_URL_FILE=$(mktemp)

# Start Cloudflare Tunnel and capture the URL
cloudflared tunnel --url http://localhost:8765 2>&1 &
TUNNEL_PID=$!

# Wait and extract the tunnel URL
echo "⏳ Waiting for tunnel to establish (this takes ~10 seconds)..."
for i in {1..30}; do
    sleep 1
    # Try to get the tunnel URL from cloudflared metrics
    URL=$(curl -s http://localhost:45679/metrics 2>/dev/null | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | head -1)
    if [ -n "$URL" ]; then
        echo ""
        echo "✅ Tunnel established!"
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "  🔗 PUBLIC LOGIN URL: $URL"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        echo "Users will use this URL when they click /login in Telegram"
        echo ""
        export PUBLIC_AUTH_URL="$URL"
        break
    fi
    echo -n "."
done

if [ -z "$PUBLIC_AUTH_URL" ]; then
    echo ""
    echo "⚠️  Could not detect tunnel URL automatically"
    echo "Look for the 'https://xxxx.trycloudflare.com' URL above"
    echo "The bot will use localhost URLs instead (works for local testing only)"
    echo ""
fi

echo ""
echo "🤖 Starting Telegram Bot..."
echo ""
export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"
python -m mcp_formlabs.telegram_bot

# Cleanup on exit
trap "echo ''; echo 'Stopping services...'; kill $AUTH_PID $TUNNEL_PID 2>/dev/null; exit" INT TERM EXIT
