# Kim Formlabs Bot - Simplified Setup

## 🎯 What We Built

A **seamless multi-tenant 3D printing farm manager** that:
- ✅ Uses ONE bot (your existing bot)
- ✅ No conflicts with OpenClaw
- ✅ Works 24/7 from your Mac
- ✅ Global access via `https://kim.harwav.com`

## Architecture

```
You (OpenClaw) ◄─────► Telegram ◄─────► Users worldwide
     │
     │ MCP tool: generate_login_url()
     ▼
Auth Server (Mac) ◄─────► Cloudflare Tunnel ◄─────► https://kim.harwav.com
     │
     │ Stores token
     ▼
Keychain (secure) ◄─────► PreForm Server ◄─────► Printers
```

## 🚀 Quick Start

### Step 1: Start Auth Server

Run this in your terminal and keep it open:

```bash
cd ~/.openclaw/workspace-kim/mcp-formlabs-server
./start_auth_only.sh
```

You'll see:
```
╔════════════════════════════════════════════════════════════════╗
║  🔐 Kim Auth Server                                            ║
║  https://kim.harwav.com                                        ║
╚════════════════════════════════════════════════════════════════╝

✅ Auth server is LIVE at: https://kim.harwav.com
```

### Step 2: Test It!

**Send me:** `/login`

I should reply with a secure link to `https://kim.harwav.com`

## 📱 User Experience

| Command | What Happens |
|---------|---------------|
| `/login` | I generate secure link → User clicks → Enters credentials → Token saved |
| `/status` | I check Keychain for their token |
| `/printers` | I use their token to list their printers |
| `/jobs` | I fetch their print jobs |

## 🔧 How It Works

**OpenClaw (me)** - Running via your OpenClaw server:
- Handles ALL Telegram messages
- Uses MCP tool `generate_login_url()` to create login links
- Calls other MCP tools to interact with Formlabs API

**Auth Server** - Running on your Mac:
- ONLY serves the web login page
- NO Telegram connection (no conflict!)
- Available globally via `kim.harwav.com`

**PreForm Server** - Already running on your Mac:
- Local 3D printing engine
- Accessible only from your Mac

## ✅ Status Check

To verify everything:

```bash
# Check auth server health
curl http://127.0.0.1:8765/health

# Should return: {"status":"ok"}

# Check tunnel
cloudflared tunnel list

# Should show: kim-formlabs
```

## 🔄 Auto-Start (Optional)

To start automatically when Mac boots:

1. **Create LaunchAgent:**
```bash
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.kim.formlabs.auth.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kim.formlabs.auth</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/markus/.openclaw/workspace-kim/mcp-formlabs-server/start_auth_only.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/kim-auth.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/kim-auth.err</string>
</dict>
</plist>
EOF
```

2. **Load it:**
```bash
launchctl load ~/Library/LaunchAgents/com.kim.formlabs.auth.plist
```

## ❓ Troubleshooting

**Auth server already running:**
```bash
lsof -ti:8765 | xargs kill -9
```

**Tunnel issues:**
```bash
cloudflared tunnel cleanup
cloudflared tunnel run kim-formlabs
```

**Keychain access denied:**
- First login may prompt for Keychain access
- Click "Always Allow"

## 📁 Files

| File | Purpose |
|------|---------|
| `start_auth_only.sh` | Start auth server + tunnel (USE THIS) |
| `start_kim_bot.sh` | Full bot (deprecated - don't use) |
| `src/mcp_formlabs/auth_server.py` | Web login form |
| `src/mcp_formlabs/server.py` | MCP tools (I use these) |
| `src/mcp_formlabs/keychain.py` | Secure token storage |

## 🎉 You're Ready!

1. ✅ Run `./start_auth_only.sh`
2. ✅ Keep terminal open
3. ✅ Send me `/login` to test

**Multi-tenant support:** Each user gets their own isolated token in Keychain. They can only access their own printers.

**24/7 operation:** As long as your Mac is on and the terminal is running, users worldwide can log in.
