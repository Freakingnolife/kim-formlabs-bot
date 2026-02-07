# 🔐 Global Access Control - Implementation Guide

## What This Is

**System-level security** for Kim (OpenClaw). Only approved users can message the bot at all.

**Before:** Anyone could send any message to you
**After:** Unknown users are blocked immediately with "Access Pending"

## How It Works

```
New User Messages You
         ↓
   [Access Check]
         ↓
   ┌─────────┐
   │ Approved?│
   └────┬────┘
      Yes/No
       /   \
      ↓     ↓
 Process  Block + 
 Message  Notify Admin
```

## Files

- `access_control.py` - Core access control logic
- `check_access.py` - Wrapper for OpenClaw integration
- `approved_users.json` - Database
- `access_requests.log` - Audit log

## Integration with OpenClaw

### Step 1: Add to OpenClaw Message Handler

At the VERY START of your message processing (before any other logic):

```python
from check_access import check_access, handle_admin_command

# In your message handler
def on_message(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # CHECK ACCESS FIRST
    allowed, response = check_access(user_id, username, first_name)
    
    if not allowed:
        # User not approved - send the response and stop
        send_message(response)
        
        # Also notify admin (you)
        admin_msg = get_admin_notification(user_id, username, first_name)
        send_message_to_admin(admin_msg)
        return
    
    # User approved - continue with normal processing
    process_message(message)
```

### Step 2: Admin Commands

Add these commands for admin (you):

```python
if message.text.startswith('/approve'):
    result = handle_admin_command('/approve', user_id, [target_user_id])
    send_message(result)
    
    # Also notify the approved user
    send_message_to_user(target_user_id, get_approved_notification())

if message.text.startswith('/reject'):
    result = handle_admin_command('/reject', user_id, [target_user_id])
    send_message(result)

if message.text == '/access_stats':
    result = handle_admin_command('/access_stats', user_id)
    send_message(result)
```

## User Experience

### New Unknown User

**User sends:** "Hello"

**Bot replies:**
```
⏳ Access Pending

Hello! This is a private bot.

Your request has been sent to the admin for approval.
You'll be notified once access is granted.

_Please do not send multiple messages - this won't speed up the process._
```

**You (admin) receive:**
```
🔔 New Access Request

Name: John Doe
Username: @johndoe
Telegram ID: 123456789

To approve:
/approve 123456789

To reject:
/reject 123456789

_Pending requests: 3_
```

### After Approval

**You send:** `/approve 123456789`

**Bot replies to you:** `✅ User 123456789 approved!`

**User receives:**
```
✅ Access Granted!

You can now use this bot.

Available commands:
• /help - See all commands
• Formlabs features (if logged in)

Welcome!
```

**Now they can message you normally!**

## Admin Commands

| Command | Description |
|---------|-------------|
| `/approve USER_ID` | Allow user to access bot |
| `/reject USER_ID` | Block user permanently |
| `/access_stats` | See approval statistics |

## Current Status

You (ID: 6217674573) are already:
- ✅ Approved
- ✅ Admin

## Testing

Test the system:

```bash
cd mcp-formlabs-server
python3 check_access.py check --user-id 99999 --username testuser
```

## Security Features

- ✅ Blocks all messages from unknown users
- ✅ Audit log of all access requests
- ✅ Persistent storage (survives restarts)
- ✅ Admin-only approval commands
- ✅ Automatic user notification

## Notes

- This is **in addition to** the Formlabs approval system
- First layer: Can they talk to Kim? (this system)
- Second layer: Can they use Formlabs? (previous system)
- You control both layers independently

---

**Your bot is now fully secured with two-layer access control!**
