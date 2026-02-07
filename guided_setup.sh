#!/bin/bash
# Guided setup for Kim Formlabs Bot
# This runs INTERACTIVELY in your terminal

set -e

clear
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🤖 Kim Formlabs Bot Setup                                    ║"
echo "║  Domain: kim.harwav.com                                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "This setup requires ONE manual step: Cloudflare login"
echo ""

BOT_TOKEN="8562480815:AAHn7-C3_mcqgrAI026nCVN18keHSM67dzA"
DOMAIN="kim.harwav.com"
TUNNEL_NAME="kim-formlabs"

cd "$(dirname "$0")"

# Step 1: Cloudflare Login (Interactive)
echo "══════════════════════════════════════════════════════════════════"
echo "STEP 1: Cloudflare Authentication"
echo "══════════════════════════════════════════════════════════════════"
echo ""

if [ -f "$HOME/.cloudflared/cert.pem" ]; then
    echo "✅ Certificate already exists!"
else
    echo "🔐 You need to authenticate with Cloudflare"
    echo ""
    echo "About to run: cloudflared tunnel login"
    echo ""
    echo "WHAT WILL HAPPEN:"
    echo "  1. Your browser will open"
    echo "  2. Login with your Cloudflare account (same as harwav.com)"
    echo "  3. Click 'Authorize'"
    echo "  4. A 'cert.pem' file will be downloaded"
    echo "  5. Return here"
    echo ""
    read -p "Press ENTER to open browser and login..."
    echo ""
    
    # Run the login
    cloudflared tunnel login
    
    echo ""
    echo "══════════════════════════════════════════════════════════════════"
    echo "DID YOU SEE 'Success! You've logged in.' in the browser?"
    echo "══════════════════════════════════════════════════════════════════"
    echo ""
    
    # Check for cert file
    CERT_PATH=""
    POSSIBLE_PATHS=(
        "$HOME/Downloads/cert.pem"
        "$HOME/Downloads/cert-1.pem"
        "$HOME/Downloads/cert-2.pem"
        "$HOME/cert.pem"
    )
    
    for path in "${POSSIBLE_PATHS[@]}"; do
        if [ -f "$path" ]; then
            CERT_PATH="$path"
            break
        fi
    done
    
    if [ -n "$CERT_PATH" ]; then
        echo "✅ Found certificate at: $CERT_PATH"
        mv "$CERT_PATH" "$HOME/.cloudflared/cert.pem"
        chmod 600 "$HOME/.cloudflared/cert.pem"
        echo "✅ Certificate installed!"
    else
        echo "❌ Could not find cert.pem"
        echo ""
        echo "Please manually run these commands:"
        echo "  mv ~/Downloads/cert.pem ~/.cloudflared/"
        echo "  chmod 600 ~/.cloudflared/cert.pem"
        echo ""
        echo "Then run this script again:"
        echo "  ./guided_setup.sh"
        exit 1
    fi
fi

echo ""
echo "✅ Step 1 complete!"
echo ""

# Step 2: Create Tunnel
echo "══════════════════════════════════════════════════════════════════"
echo "STEP 2: Creating Cloudflare Tunnel"
echo "══════════════════════════════════════════════════════════════════"
echo ""

EXISTING_TUNNEL=$(cloudflared tunnel list 2>/dev/null | grep "$TUNNEL_NAME" | awk '{print $1}' || echo "")

if [ -n "$EXISTING_TUNNEL" ]; then
    echo "✅ Tunnel '$TUNNEL_NAME' already exists"
    TUNNEL_ID="$EXISTING_TUNNEL"
else
    echo "🆕 Creating tunnel: $TUNNEL_NAME"
    OUTPUT=$(cloudflared tunnel create "$TUNNEL_NAME" 2>&1)
    TUNNEL_ID=$(echo "$OUTPUT" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
    
    if [ -z "$TUNNEL_ID" ]; then
        echo "❌ Failed to create tunnel"
        echo "Error: $OUTPUT"
        exit 1
    fi
    
    echo "✅ Tunnel created!"
fi
echo ""

# Step 3: Configure
echo "══════════════════════════════════════════════════════════════════"
echo "STEP 3: Configuring $DOMAIN"
echo "══════════════════════════════════════════════════════════════════"
echo ""

cat > "$HOME/.cloudflared/config.yml" << EOF
tunnel: ${TUNNEL_ID}
credentials-file: ${HOME}/.cloudflared/${TUNNEL_ID}.json

ingress:
  - hostname: ${DOMAIN}
    service: http://localhost:8765
  - service: http_status:404
EOF

echo "✅ Configuration saved"

cloudflared tunnel route dns "$TUNNEL_NAME" "$DOMAIN" 2>/dev/null || true
echo "✅ DNS route configured"
echo ""

# Step 4: Create startup script
echo "══════════════════════════════════════════════════════════════════"
echo "STEP 4: Creating Startup Script"
echo "══════════════════════════════════════════════════════════════════"
echo ""

cat > start_kim_bot.sh << 'STARTER'
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
STARTER

chmod +x start_kim_bot.sh
echo "✅ Created: start_kim_bot.sh"
echo ""

# Done
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🎉 SETUP COMPLETE!                                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Your bot is configured with:"
echo "  🔗 Login URL: https://kim.harwav.com"
echo "  🤖 Bot: @marcus_liangzhu (your current bot)"
echo ""
echo "TO START YOUR BOT:"
echo "  ./start_kim_bot.sh"
echo ""
echo "NOTE: DNS may take 1-5 minutes to work the first time"
echo ""
read -p "Press ENTER to exit..."
