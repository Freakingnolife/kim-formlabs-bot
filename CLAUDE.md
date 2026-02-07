# CLAUDE.md - Claude Code Configuration

## Workflow Rules

### 1. Coding Tasks

**MUST use Claude Code CLI** for all coding tasks:
```bash
claude [options] [command] [prompt]
```

**Model Configuration:**
- Set to `claude-opus-4-6-20250205` in `~/.claude/settings.json` ✓

**Permission Configuration:**
- `permissionMode: "bypassPermissions"` in `~/.claude/settings.json` ✓
- This skips all permission prompts by default

### 2. Default Behavior

With the current settings, running:
```bash
claude "your prompt"
```

Will automatically:
- Use Opus 4.6 model
- Bypass all permission checks
- No interactive prompts for file edits

### 3. Switching to Direct Mode

**NEVER switch without explicit approval.**

If Claude Code CLI is:
- Taking too long
- Stuck/failing
- Not working as expected

**Ask first:**
> "CLI is slow/stuck on [specific issue]. Want me to switch to direct mode or try different flags?"

### 4. Common Commands

**Start coding task (auto-skips permissions):**
```bash
cd /path/to/project
claude "implement feature X"
```

**Continue previous session:**
```bash
claude -c
```

**Resume specific session:**
```bash
claude --resume [session-id]
```

**Override with explicit permissions (if needed):**
```bash
claude --permission-mode default "your prompt"
```

### 5. Project Structure

When using Claude Code:
1. Navigate to project directory first
2. Ensure `.git` is initialized
3. Use absolute paths in prompts if needed

### 6. Settings Location

**User settings:** `~/.claude/settings.json`
```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "claude-opus-4-6-20250205",
  "permissionMode": "bypassPermissions"
}
```

## References

- Settings: `~/.claude/settings.json`
- Sessions: `~/.claude/sessions/`
- Documentation: https://docs.anthropic.com/en/docs/claude-code
