#!/bin/bash
# Start ONLY the auth server + Cloudflare Tunnel
# No Telegram bot - OpenClaw handles all Telegram messages

set -e

DOMAIN="kim.harwav.com"
TUNNEL_NAME="kim-formlabs"

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🔐 Kim Auth Server                                            ║"
echo "║  https://${DOMAIN}                                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Note: OpenClaw handles all Telegram messages"
echo "      This server only handles web logins"
echo ""

# Check if auth server port is already in use
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8765 is already in use"
    echo "    Checking if it's our auth server..."
    
    # Try to health check
    if curl -s http://127.0.0.1:8765/health >/dev/null 2>&1; then
        echo "✅ Auth server already running"
        RUNNING=1
    else
        echo "❌ Something else is using port 8765"
        echo "    Please stop it first: lsof -ti:8765 | xargs kill -9"
        exit 1
    fi
else
    RUNNING=0
fi

if [ $RUNNING -eq 0 ]; then
    # Activate virtual environment
    source .venv/bin/activate
    
    # Start the auth server
    echo "📡 Starting auth server on http://127.0.0.1:8765..."
    python3 -c "
import sys
sys.path.insert(0, 'src')
from mcp_formlabs.auth_server import get_auth_server
import time

server = get_auth_server()
server.start()
print('✅ Auth server started')

# Keep running
while True:
    time.sleep(1)
" &
    AUTH_PID=$!
    
    # Wait for server to start
    echo -n "⏳ Waiting for server"
    for i in {1..10}; do
        sleep 0.5
        if curl -s http://127.0.0.1:8765/health >/dev/null 2>&1; then
            echo " ✅"
            break
        fi
        echo -n "."
    done
    
    if ! curl -s http://127.0.0.1:8765/health >/dev/null 2>&1; then
        echo ""
        echo "❌ Auth server failed to start"
        kill $AUTH_PID 2>/dev/null || true
        exit 1
    fi
fi

# Start Cloudflare Tunnel
echo ""
echo "🌐 Starting Cloudflare Tunnel for ${DOMAIN}..."
cloudflared tunnel run ${TUNNEL_NAME} &
TUNNEL_PID=$!

sleep 2

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  ✅ Auth server is LIVE at: https://${DOMAIN}"
echo "══════════════════════════════════════════════════════════════════"
echo ""
echo "OpenClaw (Telegram) will now use this for logins."
echo ""
echo "To stop: Press Ctrl+C"
echo ""

# Keep script running
trap "echo ''; echo '👋 Stopping auth server...'; kill \$AUTH_PID \$TUNNEL_PID 2>/dev/null || true; exit" INT TERM EXIT

wait
