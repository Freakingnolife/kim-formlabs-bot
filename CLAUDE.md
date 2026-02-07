# CLAUDE.md - Claude Code Configuration

## Workflow Rules

### 1. Coding Tasks

**MUST use Claude Code CLI** for all coding tasks:
```bash
claude [options] [command] [prompt]
```

**Model Configuration:**
- Set to `claude-opus-4-6-20250205` in `~/.claude/settings.json`
- This is already configured ✓

### 2. Permission Handling

**Option A - Skip permissions (for trusted projects):**
```bash
claude --dangerously-skip-permissions [prompt]
```

**Option B - Use permission mode:**
```bash
claude --permission-mode bypassPermissions [prompt]
```

**Available modes:**
- `acceptEdits` - Auto-accept edit suggestions
- `bypassPermissions` - Skip all permission checks
- `dontAsk` - Don't ask for confirmation
- `default` - Normal interactive mode
- `plan` - Plan mode (review before executing)

**Option C - Non-interactive (for scripts):**
```bash
claude -p --dangerously-skip-permissions "your prompt"
```

### 3. Switching to Direct Mode

**NEVER switch without explicit approval.**

If Claude Code CLI is:
- Taking too long
- Stuck on prompts
- Failing repeatedly

**Ask first:**
> "CLI is slow/stuck on [specific issue]. Want me to switch to direct mode or try different flags?"

### 4. Common Commands

**Start coding task:**
```bash
cd /path/to/project
claude --dangerously-skip-permissions "implement feature X"
```

**Continue previous session:**
```bash
claude -c
```

**Resume specific session:**
```bash
claude --resume [session-id]
```

**With specific model:**
```bash
claude --model opus "your prompt"
```

### 5. Project Structure

When using Claude Code:
1. Navigate to project directory first
2. Ensure `.git` is initialized
3. Use absolute paths in prompts if needed

### 6. Safety

- `--dangerously-skip-permissions` is safe in:
  - Your own projects
  - Git-tracked repos
  - Non-production environments

- Do NOT use in:
  - Untrusted repositories
  - Production systems
  - Shared/multi-user environments

## References

- Settings: `~/.claude/settings.json`
- Sessions: `~/.claude/sessions/`
- Documentation: https://docs.anthropic.com/en/docs/claude-code
