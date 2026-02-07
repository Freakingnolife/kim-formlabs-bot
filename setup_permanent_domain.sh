#!/bin/bash
# Setup permanent domain kim.harwav.com for Formlabs Telegram Bot
# This creates a named Cloudflare Tunnel that always uses the same URL

set -e

echo "🔧 Setting up permanent domain: kim.harwav.com"
echo ""
echo "This requires:"
echo "  1. A Cloudflare account (free)"
echo "  2. Your domain harwav.com managed by Cloudflare DNS"
echo ""

# Check if cloudflared is logged in
if ! cloudflared tunnel list &>/dev/null; then
    echo "⚠️  You need to authenticate cloudflared first."
    echo ""
    echo "Please run this command and follow the browser login:"
    echo "  cloudflared tunnel login"
    echo ""
    echo "After that, run this script again."
    exit 1
fi

echo "✅ Cloudflare authentication verified"
echo ""

# Create the tunnel if it doesn't exist
TUNNEL_NAME="kim-formlabs"
EXISTING_TUNNEL=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')

if [ -n "$EXISTING_TUNNEL" ]; then
    echo "✅ Tunnel '$TUNNEL_NAME' already exists"
    TUNNEL_ID=$EXISTING_TUNNEL
else
    echo "🆕 Creating new tunnel: $TUNNEL_NAME"
    OUTPUT=$(cloudflared tunnel create "$TUNNEL_NAME" 2>&1)
    TUNNEL_ID=$(echo "$OUTPUT" | grep -oP '(?<=Created tunnel )[a-z0-9-]+' || echo "")
    
    if [ -z "$TUNNEL_ID" ]; then
        echo "❌ Failed to create tunnel"
        echo "Output: $OUTPUT"
        exit 1
    fi
    
    echo "✅ Tunnel created: $TUNNEL_ID"
fi

echo ""
echo "📋 Creating configuration..."

# Get the tunnel credentials file
CREDENTIALS_FILE="$HOME/.cloudflared/${TUNNEL_ID}.json"
if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "❌ Tunnel credentials not found at $CREDENTIALS_FILE"
    exit 1
fi

# Create config file
cat > "$HOME/.cloudflared/config.yml" << EOF
tunnel: ${TUNNEL_ID}
credentials-file: ${CREDENTIALS_FILE}

ingress:
  - hostname: kim.harwav.com
    service: http://localhost:8765
  - service: http_status:404
EOF

echo "✅ Configuration saved to ~/.cloudflared/config.yml"
echo ""

# Route the DNS
echo "🌐 Setting up DNS route for kim.harwav.com..."
cloudflared tunnel route dns "$TUNNEL_NAME" "kim.harwav.com" 2>/dev/null || echo "  (DNS route may already exist)"
echo "✅ DNS route configured"
echo ""

# Create startup script for permanent domain
cat > "$(dirname "$0")/start_permanent.sh" << 'EOF'
#!/bin/bash
# Start Formlabs Telegram Bot with permanent domain kim.harwav.com

set -e

BOT_TOKEN="${1:-$TELEGRAM_BOT_TOKEN}"

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Error: No bot token provided"
    echo "Usage: ./start_permanent.sh YOUR_BOT_TOKEN"
    echo "Or set TELEGRAM_BOT_TOKEN environment variable"
    exit 1
fi

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

echo "🚀 Starting Formlabs Telegram Bot with permanent domain"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🔗 PERMANENT LOGIN URL: https://kim.harwav.com"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Start the auth server in background
echo "📡 Starting auth server..."
python -c "
import sys
sys.path.insert(0, 'src')
from mcp_formlabs.auth_server import get_auth_server
server = get_auth_server()
server.start()
import time
time.sleep(60*60*24)
" &
AUTH_PID=$!

sleep 2

# Start Cloudflare Tunnel with the permanent domain
echo "🌐 Starting Cloudflare Tunnel (kim.harwav.com)..."
cloudflared tunnel run kim-formlabs &
TUNNEL_PID=$!

# Set the public URL
export PUBLIC_AUTH_URL="https://kim.harwav.com"
export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"

sleep 3

echo ""
echo "✅ Ready! Users can now log in at https://kim.harwav.com"
echo "🤖 Starting Telegram Bot..."
echo ""

python -m mcp_formlabs.telegram_bot

# Cleanup
trap "echo ''; echo '👋 Stopping services...'; kill \$AUTH_PID \$TUNNEL_PID 2>/dev/null; exit" INT TERM EXIT
EOF

chmod +x "$(dirname "$0")/start_permanent.sh"

echo "✅ Created startup script: start_permanent.sh"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🎉 SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Permanent URL: https://kim.harwav.com"
echo ""
echo "To start your bot with the permanent domain:"
echo "  ./start_permanent.sh YOUR_BOT_TOKEN"
echo ""
echo "Note: Make sure kim.harwav.com DNS is set to CNAME to"
echo "      the Cloudflare Tunnel target (automatically configured)"
echo ""
