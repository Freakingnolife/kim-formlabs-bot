# Kim Formlabs Bot - Complete Setup Guide

## 🎯 What You Have Now

A fully-functional multi-tenant 3D printing farm manager:

- ✅ **Telegram Bot Skills** - `/login`, `/printers`, `/materials`, `/jobs`, `/status`, `/logout`
- ✅ **Secure Auth** - Web login at `https://kim.harwav.com`
- ✅ **Multi-tenant** - Each user gets isolated token storage
- ✅ **84 Printers** - Full APAC fleet access

## 🚀 Quick Reference

### Available Commands

| Command | Description | Who Can Use |
|---------|-------------|-------------|
| `/login` | Get secure login link | Anyone |
| `/status` | Check login status | Logged in users |
| `/printers` | List all your printers | Logged in users |
| `/materials` | Show available resins | Anyone |
| `/jobs` | View print queue | Logged in users |
| `/logout` | Remove credentials | Logged in users |
| `/help` | Show all commands | Anyone |

## 📱 How to Use

### For You (Admin)

1. **Ensure auth server is running:**
   ```bash
   cd mcp-formlabs-server
   ./start_auth_only.sh
   ```

2. **Test commands:**
   - Send me `/printers` → Shows your 84 printers
   - Send me `/materials` → Shows available resins
   - Send me `/jobs` → Shows print queue

### For New Users

1. **User sends `/login`**
2. **They click the secure link** (`https://kim.harwav.com`)
3. **Enter Formlabs credentials**
4. **Now they can use all commands**

Each user only sees **their own printers** - complete isolation!

## 🔧 Technical Details

### Architecture
```
User Telegram Message
       ↓
   OpenClaw (me)
       ↓
  run_command.py
       ↓
  bot_commands.py
       ↓
  ┌─────────────┐     ┌─────────────┐
  │ Auth Server │────▶│ kim.harwav  │ (for /login)
  └─────────────┘     └─────────────┘
       ↓
  PreFormClient (with user's token)
       ↓
  PreForm Server (localhost:44388)
       ↓
   Formlabs API
```

### Files

| File | Purpose |
|------|---------|
| `start_auth_only.sh` | Start the auth server + tunnel |
| `bot_commands.py` | All bot command handlers |
| `run_command.py` | Wrapper for OpenClaw |
| `src/mcp_formlabs/` | Core modules (client, keychain, etc.) |

## 🔄 Integration with OpenClaw

To integrate with your OpenClaw bot, add this to your OpenClaw configuration:

```python
# When user sends /printers
if message.text == '/printers':
    import subprocess
    result = subprocess.run(
        ['python3', 'run_command.py', '/printers', str(user_id)],
        capture_output=True,
        text=True,
        cwd='/path/to/mcp-formlabs-server'
    )
    reply(result.stdout)
```

Or simply use the `bot_commands.py` module directly!

## 🎉 Test It Now

**Try these commands:**
- `/printers` - See your 84 printers
- `/materials` - See available resins
- `/status` - Check your login
- `/help` - See all commands

## 🔒 Security

- Tokens stored in **macOS Keychain** (encrypted)
- Each user **isolated** - can't see others' data
- Passwords **never pass through Telegram**
- Web login uses **HTTPS** via Cloudflare

## 📝 Next Steps

1. ✅ Keep `start_auth_only.sh` running 24/7
2. ✅ Share bot with users
3. ✅ They `/login` → Use commands
4. ✅ You manage the entire APAC fleet from Telegram!

---

**Questions?** Just ask!
