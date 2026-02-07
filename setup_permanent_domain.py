#!/usr/bin/env python3
"""
Setup permanent domain kim.harwav.com for Formlabs Telegram Bot
This creates a named Cloudflare Tunnel that always uses the same URL
"""

import subprocess
import sys
import os
from pathlib import Path

def run(cmd, capture=True):
    """Run a shell command."""
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    return result

def check_cloudflared_auth():
    """Check if cloudflared is authenticated."""
    result = run("cloudflared tunnel list")
    if result.returncode != 0:
        print("⚠️  You need to authenticate cloudflared first.")
        print("")
        print("Please run this command and follow the browser login:")
        print("  cloudflared tunnel login")
        print("")
        print("After that, run this script again.")
        return False
    return True

def get_or_create_tunnel(name):
    """Get existing tunnel or create new one."""
    result = run(f"cloudflared tunnel list | grep '{name}'")
    
    if result.stdout.strip():
        # Tunnel exists
        tunnel_id = result.stdout.split()[0]
        print(f"✅ Tunnel '{name}' already exists: {tunnel_id[:8]}...")
        return tunnel_id
    
    # Create new tunnel
    print(f"🆕 Creating new tunnel: {name}")
    result = run(f"cloudflared tunnel create '{name}'")
    
    if result.returncode != 0:
        print(f"❌ Failed to create tunnel")
        print(f"Error: {result.stderr}")
        return None
    
    # Extract tunnel ID from output
    import re
    match = re.search(r'Created tunnel ([a-f0-9-]+)', result.stdout)
    if match:
        tunnel_id = match.group(1)
        print(f"✅ Tunnel created: {tunnel_id[:8]}...")
        return tunnel_id
    
    print("❌ Could not extract tunnel ID from output")
    return None

def create_config(tunnel_id, domain):
    """Create cloudflared config file."""
    config_dir = Path.home() / ".cloudflared"
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "config.yml"
    credentials_file = config_dir / f"{tunnel_id}.json"
    
    config_content = f"""tunnel: {tunnel_id}
credentials-file: {credentials_file}

ingress:
  - hostname: {domain}
    service: http://localhost:8765
  - service: http_status:404
"""
    
    config_file.write_text(config_content)
    print(f"✅ Configuration saved to {config_file}")

def setup_dns_route(tunnel_name, domain):
    """Setup DNS route for the domain."""
    result = run(f"cloudflared tunnel route dns '{tunnel_name}' '{domain}'")
    if result.returncode == 0:
        print(f"✅ DNS route configured: {domain}")
    else:
        print(f"⚠️  DNS route setup: {result.stderr or 'may already exist'}")

def create_startup_script(domain):
    """Create the startup script."""
    script_content = f'''#!/bin/bash
# Start Formlabs Telegram Bot with permanent domain {domain}

set -e

BOT_TOKEN="${{1:-$TELEGRAM_BOT_TOKEN}}"

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Error: No bot token provided"
    echo "Usage: ./start_permanent.sh YOUR_BOT_TOKEN"
    exit 1
fi

cd "$(dirname "$0")"
source .venv/bin/activate

echo "🚀 Starting Formlabs Telegram Bot with permanent domain"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🔗 PERMANENT LOGIN URL: https://{domain}"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Start auth server
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

# Start Cloudflare Tunnel
echo "🌐 Starting Cloudflare Tunnel ({domain})..."
cloudflared tunnel run kim-formlabs &
TUNNEL_PID=$!

export PUBLIC_AUTH_URL="https://{domain}"
export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"

sleep 3

echo ""
echo "✅ Ready! Your bot is running with permanent domain."
echo "🤖 Starting Telegram Bot..."
echo ""

python -m mcp_formlabs.telegram_bot

trap "echo ''; echo '👋 Stopping...'; kill \$AUTH_PID \$TUNNEL_PID 2>/dev/null; exit" INT TERM EXIT
'''
    
    script_path = Path("start_permanent.sh")
    script_path.write_text(script_content)
    script_path.chmod(0o755)
    print(f"✅ Created startup script: {script_path}")

def main():
    domain = "kim.harwav.com"
    tunnel_name = "kim-formlabs"
    
    print(f"🔧 Setting up permanent domain: {domain}")
    print("")
    print("This requires:")
    print("  1. A Cloudflare account (free)")
    print("  2. Your domain harwav.com managed by Cloudflare DNS")
    print("")
    
    # Check authentication
    if not check_cloudflared_auth():
        sys.exit(1)
    
    print("✅ Cloudflare authentication verified")
    print("")
    
    # Get or create tunnel
    tunnel_id = get_or_create_tunnel(tunnel_name)
    if not tunnel_id:
        sys.exit(1)
    
    print("")
    
    # Create config
    create_config(tunnel_id, domain)
    
    # Setup DNS
    setup_dns_route(tunnel_name, domain)
    
    # Create startup script
    create_startup_script(domain)
    
    print("")
    print("=" * 59)
    print("🎉 SETUP COMPLETE!")
    print("=" * 59)
    print("")
    print(f"Permanent URL: https://{domain}")
    print("")
    print("To start your bot with the permanent domain:")
    print("  ./start_permanent.sh YOUR_BOT_TOKEN")
    print("")
    print("Note: DNS changes may take 1-5 minutes to propagate")
    print("")

if __name__ == "__main__":
    main()
