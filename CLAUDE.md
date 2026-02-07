# CLAUDE.md - Kim Formlabs Bot

> **Note:** This project follows the [global CLAUDE.md](../CLAUDE.md) rules.
> 
> **Universal Rule:** Use Claude Code CLI for all coding tasks.

---

## Project-Specific Rules

### 1. Coding Tasks

Follow global rule: Use `claude` CLI command.

```bash
cd mcp-formlabs-server
claude "implement feature..."
```

### 2. Testing Commands

After CLI writes code, use direct mode for:
```bash
# Check if server is running
curl http://127.0.0.1:8765/health

# Check auth server logs
tail -f /tmp/kim-auth.log

# Test command
python3 run_command.py /printers --user-id 6217674573
```

### 3. File Locations

| File | Purpose |
|------|---------|
| `start_auth_only.sh` | Start auth server |
| `bot_commands.py` | Telegram command handlers |
| `access_control.py` | User approval system |
| `src/mcp_formlabs/` | Core modules |

### 4. Development Workflow

1. **Edit code:** Use `claude` CLI
2. **Test changes:** Use direct `exec` commands
3. **Commit:** Use direct `exec git` commands
4. **Deploy:** Use `claude` CLI for setup scripts

---

## References

- **Global Rules:** [../CLAUDE.md](../CLAUDE.md)
- **Settings:** ~/.claude/settings.json
- **PRD:** [PRD.md](PRD.md)
