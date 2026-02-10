# Bob - Kim Formlabs Telegram Bot

Bob is the Telegram bot interface for the Kim Formlabs printing assistant. He helps users manage their Formlabs printers, monitor print jobs, and provides advanced 3D printing utilities.

## Features

### Core Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and bot introduction |
| `/login` | Secure login to Formlabs Dashboard via web link |
| `/logout` | Disconnect Formlabs account |
| `/status` | Check connection status and fleet overview |
| `/printers` or `/printer` | List all printers across your fleet |
| `/jobs` | View print jobs (optionally filter by status) |
| `/materials` | Show available Formlabs materials |
| `/help` | Show available commands |

### Admin Commands

| Command | Description |
|---------|-------------|
| `/approve USER_ID` | Approve a new user (admin only) |
| `/reject USER_ID` | Reject/remove a user (admin only) |
| `/users` | List all approved users (admin only) |

### Advanced Features

#### 1. Fixture Generator (`/fixture`)
Generate custom holding jigs and fixtures for your prints.

**Usage:**
```
/fixture <object> [--operation <op>] [--clearance <mm>]
```

**Operations:** drilling, soldering, painting, cnc, inspection

**Examples:**
- `/fixture iphone_15_pro --operation soldering`
- `/fixture my_part.stl --operation drilling --clearance 10`

**Standard Library Objects:** iPhone models, common tools, etc.

#### 2. Resin Prophet (`/resin`)
Track resin cartridges and get low-resin alerts.

**Usage:**
```
/resin              # Show resin status
/resin add <code> <name>  # Add new cartridge
/resin alert        # Check for low resin alerts
```

#### 3. CSI: Print Crime Scene Investigation (`/csi`)
Analyze failed print photos to diagnose issues.

**Usage:**
Upload a photo with caption `/csi`

**Detects:**
- Support failures
- Layer shifts
- Warping
- Resin contamination
- Exposure issues
- And more...

## Architecture

```
Bob (Telegram Bot)
├── Auth Server (localhost:8765)
│   └── Secure credential handling
├── Formlabs API Client
│   └── PreForm Local API integration
└── Feature Modules
    ├── fixture_generator.py
    ├── resin_prophet.py
    └── csi_analyzer.py
```

## Security

- User approval system (admin must approve new users)
- Credentials stored in macOS Keychain
- Secure login via web link (password never sent through Telegram)
- Token-based authentication with Formlabs API

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Set your bot token
export TELEGRAM_BOT_TOKEN="your_token_here"

# Run Bob
python -m bob

# Or
python bob/bot.py
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `BOB_TELEGRAM_TOKEN` | Alternative token variable |
| `OPENAI_API_KEY` | Required for CSI analyzer |
| `PREFORM_API_URL` | PreForm server URL (default: http://localhost:44388) |

## File Structure

```
bob/
├── __init__.py      # Package initialization
├── __main__.py      # Module entry point
├── bot.py           # Main bot runner and handlers
└── commands.py      # Command implementations
```

## License

MIT
