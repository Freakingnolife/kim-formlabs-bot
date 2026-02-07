#!/usr/bin/env python3
"""
Start Formlabs Telegram Bot with Cloudflare Tunnel

This script:
1. Starts the local auth server
2. Creates a Cloudflare Tunnel to expose it publicly
3. Captures the public URL
4. Starts the Telegram bot with the public URL configured

Usage:
    export TELEGRAM_BOT_TOKEN="your_token_here"
    python start_bot_with_tunnel.py
"""

import os
import subprocess
import sys
import time
import json
import urllib.request
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_formlabs.auth_server import get_auth_server


def start_auth_server():
    """Start the auth server."""
    print("📡 Starting auth server on http://127.0.0.1:8765...")
    server = get_auth_server()
    server.start()
    time.sleep(1)
    print("✅ Auth server started")
    return server


def start_cloudflare_tunnel():
    """Start Cloudflare Tunnel and return the process."""
    print("\n🌐 Starting Cloudflare Tunnel...")
    print("   Creating public URL for remote users...")
    print()
    
    # Start cloudflared
    process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    return process


def wait_for_tunnel_url(process, timeout=60):
    """Wait for and extract the Cloudflare Tunnel URL."""
    print("⏳ Waiting for tunnel to establish...")
    
    start_time = time.time()
    url = None
    
    while time.time() - start_time < timeout:
        # Try to read from stdout
        import select
        if process.poll() is not None:
            print("❌ Tunnel process died unexpectedly")
            return None
            
        # Try the metrics endpoint
        try:
            with urllib.request.urlopen('http://127.0.0.1:45679/metrics', timeout=1) as response:
                content = response.read().decode('utf-8')
                # Look for the tunnel URL in metrics
                import re
                match = re.search(r'(https://[a-z0-9-]+\.trycloudflare\.com)', content)
                if match:
                    url = match.group(1)
                    break
        except:
            pass
        
        # Also try parsing stdout
        import select
        if process.stdout:
            ready, _, _ = select.select([process.stdout], [], [], 0.5)
            if ready:
                line = process.stdout.readline()
                if line:
                    import re
                    match = re.search(r'(https://[a-z0-9-]+\.trycloudflare\.com)', line)
                    if match:
                        url = match.group(1)
                        break
        
        time.sleep(0.5)
        print(".", end="", flush=True)
    
    print()
    return url


def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        print("❌ Error: No bot token provided")
        print("\nUsage:")
        print("  export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("  python start_bot_with_tunnel.py")
        print("\nOr:")
        print("  TELEGRAM_BOT_TOKEN='your_token' python start_bot_with_tunnel.py")
        sys.exit(1)
    
    print("🚀 Starting Formlabs Telegram Bot with Cloudflare Tunnel\n")
    
    # Start auth server
    auth_server = start_auth_server()
    
    # Start tunnel
    tunnel_process = start_cloudflare_tunnel()
    
    # Wait for URL
    public_url = wait_for_tunnel_url(tunnel_process)
    
    if public_url:
        print(f"\n{'='*55}")
        print(f"  🔗 PUBLIC LOGIN URL: {public_url}")
        print(f"{'='*55}")
        print("\n✅ Remote users can now log in from anywhere!")
        print("   When they click /login in Telegram, they'll use this URL.")
        print()
        os.environ["PUBLIC_AUTH_URL"] = public_url
    else:
        print("\n⚠️  Could not detect tunnel URL automatically")
        print("   The bot will use localhost URLs (local testing only)")
        print()
    
    # Start telegram bot
    print("🤖 Starting Telegram Bot...\n")
    
    try:
        # Import and run the bot
        from mcp_formlabs.telegram_bot import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    finally:
        print("Stopping tunnel...")
        tunnel_process.terminate()
        tunnel_process.wait()
        print("✅ Services stopped")


if __name__ == "__main__":
    main()
