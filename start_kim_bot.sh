#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🤖 Kim Formlabs Bot                                          ║"
echo "║  https://kim.harwav.com                                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Start auth server
python3 -c "
import sys
sys.path.insert(0, 'src')
from mcp_formlabs.auth_server import get_auth_server
server = get_auth_server()
server.start()
import time
time.sleep(86400)
" &
AUTH_PID=$!
sleep 2

# Start tunnel
echo "🌐 Starting tunnel..."
cloudflared tunnel run kim-formlabs &
TUNNEL_PID=$!
sleep 3

export PUBLIC_AUTH_URL="https://kim.harwav.com"
export TELEGRAM_BOT_TOKEN="8562480815:AAHn7-C3_mcqgrAI026nCVN18keHSM67dzA"

echo "✅ Bot running! Press Ctrl+C to stop"
echo ""

python3 -m mcp_formlabs.telegram_bot

trap "echo ''; echo '👋 Stopping...'; kill \$AUTH_PID \$TUNNEL_PID 2>/dev/null; exit" INT TERM EXIT
