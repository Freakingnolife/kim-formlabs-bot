# Bob Deployment Guide

## Quick Start (Local)

If you just want to run Bob on your local machine:

```bash
# 1. Clone the repo (if on a new machine)
git clone https://github.com/Freakingnolife/kim-formlabs-bot.git
cd kim-formlabs-bot

# 2. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Set environment variables
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"

# Optional: For new features
export FORMLABS_CLIENT_ID="your-formlabs-client-id"
export FORMLABS_CLIENT_SECRET="your-formlabs-client-secret"
export ANTHROPIC_API_KEY="your-anthropic-key"  # For Kim LLM

# 4. Run Bob
python -m bob
```

**That's it!** Bob will start and respond to Telegram messages.

---

## Production Deployment

### Option 1: systemd Service (Linux Server)

**1. Create a service file:**

```bash
sudo nano /etc/systemd/system/bob-telegram-bot.service
```

**2. Add this configuration:**

```ini
[Unit]
Description=Bob - Formlabs Telegram Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/kim-formlabs-bot
Environment="TELEGRAM_BOT_TOKEN=your-token"
Environment="FORMLABS_CLIENT_ID=your-client-id"
Environment="FORMLABS_CLIENT_SECRET=your-client-secret"
Environment="ANTHROPIC_API_KEY=your-anthropic-key"
ExecStart=/home/your-username/kim-formlabs-bot/.venv/bin/python -m bob
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**3. Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable bob-telegram-bot
sudo systemctl start bob-telegram-bot

# Check status
sudo systemctl status bob-telegram-bot

# View logs
sudo journalctl -u bob-telegram-bot -f
```

---

### Option 2: Docker Container

**1. Create Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose auth server port
EXPOSE 8765

# Run bot
CMD ["python", "-m", "bob"]
```

**2. Create docker-compose.yml:**

```yaml
version: '3.8'

services:
  bob:
    build: .
    container_name: bob-telegram-bot
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - FORMLABS_CLIENT_ID=${FORMLABS_CLIENT_ID}
      - FORMLABS_CLIENT_SECRET=${FORMLABS_CLIENT_SECRET}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data  # Persist SQLite databases
    ports:
      - "8765:8765"  # Auth server
```

**3. Create .env file:**

```bash
TELEGRAM_BOT_TOKEN=your-token
FORMLABS_CLIENT_ID=your-client-id
FORMLABS_CLIENT_SECRET=your-client-secret
ANTHROPIC_API_KEY=your-anthropic-key
```

**4. Deploy:**

```bash
docker-compose up -d

# View logs
docker-compose logs -f bob

# Restart
docker-compose restart bob
```

---

### Option 3: Cloud Hosting (Railway/Render/Fly.io)

#### Railway.app

1. Connect your GitHub repo at https://railway.app
2. Add environment variables in Railway dashboard:
   - `TELEGRAM_BOT_TOKEN`
   - `FORMLABS_CLIENT_ID`
   - `FORMLABS_CLIENT_SECRET`
   - `ANTHROPIC_API_KEY`
3. Railway auto-detects Python and deploys
4. Your auth server will be at `https://your-app.railway.app`

#### Render.com

1. Create a new Web Service
2. Connect GitHub repo
3. Set environment variables
4. Deploy command: `pip install -r requirements.txt && python -m bob`

#### Fly.io

1. Install `flyctl`: https://fly.io/docs/hands-on/install-flyctl/
2. Create `fly.toml`:

```toml
app = "bob-formlabs-bot"

[build]
  builder = "paketobuildpacks/builder:base"

[[services]]
  internal_port = 8765
  protocol = "tcp"

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

[env]
  PORT = "8765"
```

3. Deploy:

```bash
flyctl launch
flyctl secrets set TELEGRAM_BOT_TOKEN="your-token"
flyctl secrets set FORMLABS_CLIENT_ID="your-client-id"
flyctl secrets set FORMLABS_CLIENT_SECRET="your-client-secret"
flyctl secrets set ANTHROPIC_API_KEY="your-anthropic-key"
flyctl deploy
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ Yes | Bot token from @BotFather |
| `BOB_TELEGRAM_TOKEN` | Alternative | Alternative name for bot token |
| `FORMLABS_CLIENT_ID` | Optional | Web API OAuth2 client ID |
| `FORMLABS_CLIENT_SECRET` | Optional | Web API OAuth2 client secret |
| `ANTHROPIC_API_KEY` | Optional | For Kim LLM natural language |
| `ADMIN_USER_ID` | Optional | Override hardcoded admin (int) |
| `DATA_DIR` | Optional | Directory for SQLite databases (default: `./data`) |

---

## Post-Deployment Checklist

After deploying, verify everything works:

### 1. Check Bot is Running

Send `/help` to your bot on Telegram. You should see the help menu.

### 2. Test Login Flow

```
/login
```

Click the login link, authenticate with Formlabs, and verify the callback updates Telegram.

### 3. Test Basic Commands

```
/status     # Should show "Connected to PreForm" if PreForm is running
/printers   # Lists printers (requires PreForm or Web API)
/materials  # Shows material library
```

### 4. Test New Features (if Web API configured)

```
/cartridges  # Shows resin levels
/fleet       # Fleet utilization stats
/tanks       # Tank lifecycle status
/queue       # Print queue
/notify      # Subscribe to print alerts
```

### 5. Check Logs

Look for these startup messages:

```
INFO - Auth server started on http://127.0.0.1:8765
INFO - Starting Bob...
INFO - Bob is running! Press Ctrl+C to stop.
```

---

## Troubleshooting

### Bot doesn't respond

**Check:**
- Is the bot running? (`systemctl status bob-telegram-bot` or `docker ps`)
- Is `TELEGRAM_BOT_TOKEN` set correctly?
- Check logs for errors

### "Not approved" errors

**Solution:**
- Hardcoded admin is `6217674573`
- Set `ADMIN_USER_ID` env var to your Telegram user ID
- Or update `bot_commands.py` ADMIN_USER_ID

### Web API features fail

**Check:**
- Are `FORMLABS_CLIENT_ID` and `FORMLABS_CLIENT_SECRET` set?
- Test OAuth manually: https://api.formlabs.com/developer/v1/oauth/token
- Rate limit: 100 req/sec, 1500 req/hr

### Auth server not accessible

**If using Cloudflare Tunnel:**

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared  # macOS
# or download from https://github.com/cloudflare/cloudflared

# Create tunnel
cloudflared tunnel login
cloudflared tunnel create bob-tunnel
cloudflared tunnel route dns bob-tunnel kim.harwav.com
cloudflared tunnel run bob-tunnel
```

**If using ngrok:**

```bash
ngrok http 8765
# Update login URL in bot to use ngrok URL
```

---

## Updating Bob

### Local Deployment

```bash
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
# Restart: Ctrl+C and run python -m bob again
```

### systemd

```bash
cd /path/to/kim-formlabs-bot
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart bob-telegram-bot
```

### Docker

```bash
git pull origin main
docker-compose build
docker-compose up -d
```

### Cloud (Railway/Render/Fly)

Just push to GitHub - auto-deploys on new commits.

---

## Monitoring

### Health Checks

**Auth Server:** `http://your-domain:8765/health`

Returns 200 OK if running.

### Logs

**systemd:** `sudo journalctl -u bob-telegram-bot -f`
**Docker:** `docker-compose logs -f bob`
**Railway:** Check dashboard logs
**Fly.io:** `flyctl logs`

### Metrics

Monitor these in your logs:
- Telegram API errors (rate limits, auth failures)
- PreForm API connection status
- Web API OAuth token refresh
- Database write failures

---

## Security Notes

1. **Never commit secrets** - Use environment variables
2. **Restrict admin access** - Update `ADMIN_USER_ID`
3. **Enable approval system** - Users must be approved before access
4. **Use HTTPS** - Auth server should be behind reverse proxy
5. **Rate limiting** - Web API has limits (100/sec, 1500/hr)
6. **Keychain isolation** - Each user's Formlabs tokens stored separately

---

## What's Next?

1. **Wire up Kim LLM** - Add `/kim <question>` command handler
2. **Start notification polling** - Auto-start NotificationService background task
3. **Add more features** - Check GitHub issues for user requests
4. **Monitor usage** - Track which commands are most popular
5. **Optimize** - Cache Web API responses, reduce PreForm polling

---

## Need Help?

- **GitHub Issues:** https://github.com/Freakingnolife/kim-formlabs-bot/issues
- **Test Results:** See VERIFICATION_REPORT.md
- **API Docs:** See docs/ directory

Happy deploying! 🚀
