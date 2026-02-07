# Kim Formlabs Bot - Complete Setup

## 🎯 Architecture (Simplified!)

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR MAC (24/7 Online)                                     │
│                                                             │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │  OpenClaw       │────▶│  PreForm Server │               │
│  │  (Telegram Bot) │     │  localhost:44388│               │
│  └─────────────────┘     └─────────────────┘               │
│           │                                                 │
│           │  /login command                                 │
│           ▼                                                 │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │  Auth Server    │────▶│  Cloudflare     │               │
│  │  localhost:8765 │     │  kim.harwav.com │               │
│  └─────────────────┘     └─────────────────┘               │
│           │                    │                            │
│           │  token             │  Web login                 │
│           ▼                    ▼                            │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │  Keychain       │     │  User Browser   │               │
│  │  (secure store) │     │  (credentials)  │               │
│  └─────────────────┘     └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Step 1: Start the Auth Server

This runs the web login page at `https://kim.harwav.com`:

```bash
cd ~/.openclaw/workspace-kim/mcp-formlabs-server
./start_auth_only.sh
```

You should see:
```
╔════════════════════════════════════════════════════════════════╗
║  🔐 Kim Auth Server                                            ║
║  https://kim.harwav.com                                        ║
╚════════════════════════════════════════════════════════════════╝

✅ Auth server is LIVE at: https://kim.harwav.com
```

**Keep this terminal window open!**

### Step 2: That's It!

OpenClaw (me) will now use this auth server for all `/login` requests.

## 📱 User Experience

1. **User sends `/login`** → I reply with secure link
2. **User clicks `https://kim.harwav.com/login/...`** → Enters credentials
3. **Token saved to Keychain** → User is authenticated
4. **User can now use**:
   - `/printers` - List their printers
   - `/jobs` - View print jobs
   - `/print` - Send print jobs

## 🔧 How It Works

- **OpenClaw**: Handles all Telegram messages (you're talking to me right now!)
- **Auth Server**: Only handles web logins (no Telegram connection)
- **PreForm Server**: Your local 3D printing engine
- **No conflicts**: They work together seamlessly

## 🛠️ Files

| File | Purpose |
|------|---------|
| `start_auth_only.sh` | Starts just the auth server + tunnel |
| `start_kim_bot.sh` | Full bot (not needed - OpenClaw handles Telegram) |
| `src/mcp_formlabs/auth_server.py` | Web login form server |
| `src/mcp_formlabs/keychain.py` | Secure token storage |

## ✅ Status Check

To verify everything is working:
```bash
# Check auth server
curl http://127.0.0.1:8765/health

# Check tunnel
cloudflared tunnel list
```

## 🔄 Auto-Start on Boot (Optional)

To start automatically when your Mac boots:
1. Open **System Settings** → **General** → **Login Items**
2. Add `start_auth_only.sh`
3. Enable "Run in background"

Or use `launchd` for more control (ask me for details).

## ❓ Troubleshooting

**Port 8765 already in use:**
```bash
lsof -ti:8765 | xargs kill -9
```

**Tunnel not working:**
```bash
cloudflared tunnel list
cloudflared tunnel run kim-formlabs
```

**Auth server not responding:**
Check if terminal is still running the script.

## 🎉 You're All Set!

Once `./start_auth_only.sh` is running:
- ✅ Global access via `https://kim.harwav.com`
- ✅ OpenClaw handles all Telegram interactions
- ✅ Multi-tenant support (each user gets their own token)
- ✅ 24/7 operation (as long as your Mac is on)

Try it now: Send me `/login`!
