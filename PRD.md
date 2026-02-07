# Product Requirements Document (PRD)
# Kim Formlabs Command Bot
## Version 1.0 - Command-Only (No LLM)

---

## 1. Executive Summary

A Telegram bot for managing Formlabs 3D printers via command-based interactions. **No LLM required** - all functionality implemented through explicit commands and API automation.

### Key Differentiators
- **$0 API costs** - No LLM subscriptions
- **Predictable UX** - Exact commands produce exact results
- **Fast responses** - No AI processing latency
- **Works offline** - Only needs PreForm Server + internet for Telegram

---

## 2. Product Vision

Enable Formlabs users to manage their 3D printing fleet through simple Telegram commands. From checking printer status to sending print jobs - all without opening the PreForm desktop application.

### Target Users
- Formlabs fleet managers (monitoring multiple printers)
- Individual users wanting mobile access
- Teams sharing printer access

---

## 3. Feature Specifications

### 3.1 Core Commands

| Command | Description | Parameters | Example |
|---------|-------------|------------|---------|
| `/login` | Authenticate with Formlabs | None | `/login` |
| `/logout` | Remove credentials | None | `/logout` |
| `/status` | Show connection status | None | `/status` |
| `/printers` | List all accessible printers | None | `/printers` |
| `/printer <id>` | Show specific printer details | Printer ID | `/printer Form4-123` |
| `/jobs` | List recent print jobs | Optional: status filter | `/jobs printing` |
| `/job <id>` | Show job details | Job ID | `/job abc123` |
| `/materials` | List available materials | None | `/materials` |
| `/cancel <id>` | Cancel a print job | Job ID | `/cancel abc123` |

### 3.2 Print Workflow Commands

| Command | Description | Parameters |
|---------|-------------|------------|
| `/upload` | Upload 3D model file | File attachment (STL/OBJ/3MF) |
| `/prepare` | Prepare scene with settings | `--material <code>` `--layer <height>` `--support <mode>` |
| `/preview` | Generate preview image | None |
| `/slice` | Slice and estimate time | None |
| `/send <printer>` | Send to specific printer | Printer ID or "auto" |
| `/print` | One-click print (upload→prepare→send) | File + options |

### 3.3 Batch Operations

| Command | Description |
|---------|-------------|
| `/duplicate <count>` | Duplicate current model N times |
| `/batch <folder>` | Import all files from folder |
| `/queue` | View print queue across all printers |

### 3.4 Admin Commands (Access Control)

| Command | Description | Who Can Use |
|---------|-------------|-------------|
| `/approve <user_id>` | Approve new user | Admin only |
| `/reject <user_id>` | Block/reject user | Admin only |
| `/users` | List approved users | Admin only |
| `/access_stats` | View access statistics | Admin only |

---

## 4. User Flows

### 4.1 New User Onboarding

```
1. User finds bot on Telegram
2. User sends any message
3. Bot responds: "⏳ Access pending approval..."
4. Admin receives notification
5. Admin runs: /approve <user_id>
6. User receives: "✅ Access granted!"
7. User can now use all commands
```

### 4.2 Print a Model (Full Workflow)

```
User: /upload (attaches model.stl)
Bot: ✅ File uploaded: model.stl
     Size: 24.5 MB
     Vertices: 125,000
     
User: /prepare --material FLGPGR05 --layer 0.05 --support auto-v2
Bot: ✅ Scene prepared
     Material: Grey V5
     Layer: 0.05mm
     Supports: Auto v2
     [Preview Button]

User: /preview
Bot: [Image: 3D preview of model with supports]

User: /slice
Bot: ✅ Sliced successfully
     Print time: 4h 32m
     Resin required: 45ml
     
User: /send Form4-AbidingRam
Bot: ✅ Job sent to Form4-AbidingRam
     Job ID: abc123
     Status: Queued
     
User: /jobs
Bot: 📋 Print Jobs
     ▶️ model.stl - Printing (67%)
     ⏳ part2.stl - Queued
     ✅ old_part.stl - Completed
```

### 4.3 Quick Print (One Command)

```
User: /print model.stl --material grey --quality standard --printer auto
Bot: 🔄 Processing...
     Step 1/4: Uploading... ✅
     Step 2/4: Preparing... ✅
     Step 3/4: Slicing... ✅
     Step 4/4: Sending to Form4-AbidingRam... ✅
     
     ✅ Print job started!
     Job ID: xyz789
     Est. time: 3h 15m
```

---

## 5. Technical Architecture

### 5.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│  USER DEVICE (Telegram)                                      │
│  └─ Telegram App                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  YOUR MAC (24/7 Server)                                      │
│  ├─ Auth Server (FastAPI)                                    │
│  │  └─ Port 8765 → Cloudflare Tunnel → https://kim.harwav.com│
│  ├─ Command Processor (Python)                               │
│  ├─ PreForm Client (API wrapper)                             │
│  ├─ PreForm Server (Formlabs, localhost:44388)              │
│  └─ Keychain (macOS secure storage)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  FORMLABS CLOUD                                              │
│  └─ Formlabs API (Fleet management)                          │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Data Flow

```
Command → Telegram → Bot Handler → Check Access → Load User Token
                                            ↓
                                   PreFormClient (with token)
                                            ↓
                                   PreForm Server (localhost:44388)
                                            ↓
                                   Formlabs API → Printers
                                            ↓
                                   Response → Telegram → User
```

### 5.3 File Structure

```
mcp-formlabs-server/
├── src/
│   └── mcp_formlabs/
│       ├── __init__.py
│       ├── auth_server.py      # Web login form (FastAPI)
│       ├── preform_client.py   # Formlabs API client
│       ├── keychain.py         # macOS Keychain integration
│       ├── materials.py        # Material definitions
│       ├── commands.py         # Telegram command handlers
│       └── access_control.py   # User approval system
├── uploads/                    # Temporary file storage
├── logs/                       # Application logs
├── approved_users.json         # Approved user database
├── access_requests.log         # Audit log
├── start_auth_only.sh          # Start auth server + tunnel
├── bot.py                      # Main Telegram bot (no LLM)
├── requirements.txt            # Python dependencies
└── README.md                   # Setup instructions
```

---

## 6. Technical Requirements

### 6.1 Dependencies

```
# Core
python-telegram-bot>=21.0
fastapi>=0.109.0
uvicorn>=0.27.0
requests>=2.31.0

# Utilities
pydantic>=2.0.0
python-dotenv>=1.0.0

# Optional (for advanced features)
trimesh>=4.0.0      # For STL validation
numpy>=1.26.0       # Required by trimesh
```

### 6.2 External Services

| Service | Purpose | Cost | Required |
|---------|---------|------|----------|
| Cloudflare Tunnel | Public URL for auth | Free | Yes |
| Telegram Bot API | Message handling | Free | Yes |
| PreForm Server | Local slicing/printing | Free (installed) | Yes |
| Formlabs API | Fleet management | Free (with account) | Yes |

### 6.3 Hardware Requirements

- **Mac with Apple Silicon or Intel** (running 24/7)
- **8GB+ RAM** (for PreForm Server)
- **SSD storage** (for 3D models)
- **Stable internet** (for Telegram + Formlabs API)

---

## 7. Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [ ] Set up project structure
- [ ] Implement auth server (FastAPI)
- [ ] Set up Cloudflare Tunnel
- [ ] Implement access control system
- [ ] Create admin approval workflow

### Phase 2: Basic Commands (Week 2)
- [ ] Telegram bot skeleton (no LLM)
- [ ] /login, /logout, /status commands
- [ ] /printers command
- [ ] /jobs command
- [ ] /materials command

### Phase 3: Print Workflow (Week 3)
- [ ] File upload handling
- [ ] Scene preparation (/prepare)
- [ ] Preview generation (/preview)
- [ ] Slicing (/slice)
- [ ] Job submission (/send)
- [ ] One-click print (/print)

### Phase 4: Polish & Testing (Week 4)
- [ ] Error handling
- [ ] Progress indicators
- [ ] Admin dashboard
- [ ] Documentation
- [ ] User testing

---

## 8. API Endpoints (Auth Server)

```
POST   /api/create-token           # Create login token
GET    /login/{token}              # Show login form
POST   /api/login                  # Process credentials
GET    /health                     # Health check
```

---

## 9. Security Considerations

### 9.1 Authentication Flow
1. User requests access via Telegram
2. Admin approves user ID
3. User /login → Gets secure web link
4. User enters credentials on web form
5. Token stored in macOS Keychain (encrypted)
6. Token used for all subsequent API calls

### 9.2 Access Control
- User approval required before any interaction
- Per-user token isolation
- Admin-only commands protected
- Audit logging for all access requests

### 9.3 Data Protection
- Credentials never stored in plaintext
- Tokens in Keychain (hardware encrypted)
- HTTPS for all web communications
- Local-only PreForm Server access

---

## 10. Success Metrics

| Metric | Target |
|--------|--------|
| Command response time | < 2 seconds |
| Uptime | 99%+ (Mac dependent) |
| Print job success rate | > 95% |
| User onboarding time | < 5 minutes |
| API costs | $0 |

---

## 11. Future Enhancements (Optional)

- [ ] Web dashboard (view printers in browser)
- [ ] Print notifications (job complete alerts)
- [ ] Batch job queue management
- [ ] Print analytics & reporting
- [ ] Mobile app (iOS/Android)
- [ ] Optional LLM for natural language (if budget allows)

---

## 12. Appendix

### A. Material Codes Reference

| Code | Name | Category |
|------|------|----------|
| FLGPGR05 | Grey V5 | Standard |
| FLGPBK05 | Black V5 | Standard |
| FLGPCL05 | Clear V5 | Standard |
| FLTO2K02 | Tough 2000 V2 | Engineering |
| FLTOTL02 | Tough 1500 V2 | Engineering |

### B. Printer Type Codes

| Code | Model |
|------|-------|
| FORM-4-0 | Form 4 |
| FRML-4-0 | Form 4L |
| FS30-1-0 | Fuse 1+ 30W |

### C. Support Modes

- `none` - No supports
- `reduced` - Reduced supports
- `auto-v1` - Automatic v1
- `auto-v2` - Automatic v2 (recommended)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-08
**Status:** Ready for Implementation
