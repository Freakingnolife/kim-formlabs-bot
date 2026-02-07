#!/bin/bash
# Master setup script for Kim Formlabs Bot with kim.harwav.com
# Run this in your terminal: ./master_setup.sh

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Kim Formlabs Bot - Complete Setup                           ║"
echo "║  Permanent Domain: kim.harwav.com                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
BOT_TOKEN="8562480815:AAHn7-C3_mcqgrAI026nCVN18keHSM67dzA"
DOMAIN="kim.harwav.com"
TUNNEL_NAME="kim-formlabs"

cd "$(dirname "$0")"

# Step 1: Check/Fix Cloudflare Authentication
echo "🔐 Step 1: Cloudflare Authentication"
echo "─────────────────────────────────────────────────────────────"

if [ -f "$HOME/.cloudflared/cert.pem" ]; then
    echo "✅ Cloudflare certificate found"
else
    echo "⚠️  Cloudflare certificate not found."
    echo ""
    echo "Please run this command in your terminal:"
    echo "  cloudflared tunnel login"
    echo ""
    echo "Then come back and run this script again."
    echo ""
    exit 1
fi

# Test authentication
if ! cloudflared tunnel list >/devdev/null 2>&1; then
    echo "❌ Cloudflare authentication failed"
    echo "Please run: cloudflared tunnel login"
    exit 1
fi

echo "✅ Cloudflare authentication verified"
echo ""

# Step 2: Create Tunnel
echo "🌐 Step 2: Creating Cloudflare Tunnel"
echo "─────────────────────────────────────────────────────────────"

# Check if tunnel exists
EXISTING_TUNNEL=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}' || echo "")

if [ -n "$EXISTING_TUNNEL" ]; then
    echo "✅ Tunnel '$TUNNEL_NAME' already exists"
    TUNNEL_ID="$EXISTING_TUNNEL"
else
    echo "🆕 Creating tunnel: $TUNNEL_NAME"
    OUTPUT=$(cloudflared tunnel create "$TUNNEL_NAME" 2>&1)
    TUNNEL_ID=$(echo "$OUTPUT" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1 || echo "")
    
    if [ -z "$TUNNEL_ID" ]; then
        echo "❌ Failed to create tunnel"
        echo "Output: $OUTPUT"
        exit 1
    fi
    
    echo "✅ Tunnel created: ${TUNNEL_ID:0:8}..."
fi
echo ""

# Step 3: Configure DNS
echo "📡 Step 3: Configuring DNS for $DOMAIN"
echo "─────────────────────────────────────────────────────────────"

# Create config
cat > "$HOME/.cloudflared/config.yml" << EOF
tunnel: ${TUNNEL_ID}
credentials-file: ${HOME}/.cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: ${DOMAIN}
    service: http://localhost:8765
  - service: http_status:404
EOF

echo "✅ Configuration saved"

# Setup DNS route
cloudflared tunnel route dns "$TUNNEL_NAME" "$DOMAIN" 2>/dev/null || true
echo "✅ DNS route configured: $DOMAIN"
echo ""

# Step 4: Create Startup Script
echo "🚀 Step 4: Creating startup script"
echo "─────────────────────────────────────────────────────────────"

cat > start_kim_bot.sh << EOF
#!/bin/bash
# Start Kim Formlabs Bot with permanent domain kim.harwav.com

cd "$(dirname "$0")"
source .venv/bin/activate

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  🤖 Kim Formlabs Bot Starting...                             ║"
echo "║  🔗 https://${DOMAIN}                                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Start auth server
python3 -c "
import sys
sys.path.insert(0, 'src')
from mcp_formlabs.auth_server import get_auth_server
server = get_auth_server()
server.start()
import time
time.sleep(86400)  # Run for 24 hours
" &
AUTH_PID=\$!
sleep 2

# Start tunnel
echo "🌐 Starting Cloudflare Tunnel..."
cloudflared tunnel run ${TUNNEL_NAME} &
TUNNEL_PID=\$!
sleep 3

export PUBLIC_AUTH_URL="https://${DOMAIN}"
export TELEGRAM_BOT_TOKEN="${BOT_TOKEN}"

echo ""
echo "✅ Bot is running! Press Ctrl+C to stop"
echo ""

python3 -m mcp_formlabs.telegram_bot

# Cleanup on exit
trap "echo ''; echo '👋 Stopping bot...'; kill \$AUTH_PID \$TUNNEL_PID 2>/dev/null; exit" INT TERM EXIT
EOF

chmod +x start_kim_bot.sh
echo "✅ Created: start_kim_bot.sh"
echo ""

# Step 5: Done
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  🎉 SETUP COMPLETE!                                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Your permanent login URL: https://${DOMAIN}"
echo ""
echo "To start your bot, run:"
echo "  ./start_kim_bot.sh"
echo ""
echo "Note: DNS may take 1-5 minutes to propagate"
echo ""
