---
name: git-guardrails
description: Set up Claude Code or Codex guardrails to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. Use when user wants to prevent destructive git operations, add git safety hooks, or block git push/reset.
caller: any
platform: both
status: needs-codex-adaptation
examples:
  - "/git-guardrails"
  - "add git safety hooks"
  - "block dangerous git commands"
---

# Setup Git Guardrails

Sets up a command guardrail that intercepts and blocks dangerous git commands before the agent executes them.

Claude Code uses `PreToolUse` hooks. Codex should use an equivalent `PreToolUse:Bash` hook when available in the local Codex config; if the runtime has no hook support, install a shell wrapper and keep destructive commands on explicit user confirmation.

## What Gets Blocked

- `git push` (all variants including `--force`)
- `git reset --hard`
- `git clean -f` / `git clean -fd`
- `git branch -D`
- `git checkout .` / `git restore .`

When blocked, the agent sees a message telling it that it does not have authority to run these commands.

## Steps

### 1. Ask scope

Ask the user:

- target runtime: **Claude Code** or **Codex**
- scope: **this project only** or **all projects**

### 2. Copy the hook script

The bundled script is at: [scripts/block-dangerous-git.sh](scripts/block-dangerous-git.sh)

Copy it to the target location based on runtime and scope:

- **Claude project**: `.claude/hooks/block-dangerous-git.sh`
- **Claude global**: `~/.claude/hooks/block-dangerous-git.sh`
- **Codex project**: `.codex/hooks/block-dangerous-git.sh`
- **Codex global**: `~/.codex/hooks/block-dangerous-git.sh`

Make it executable with `chmod +x`.

### 3. Add hook to settings

Add to the appropriate settings file:

**Project** (`.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/block-dangerous-git.sh"
          }
        ]
      }
    ]
  }
}
```

**Codex project/global**:

Use the local Codex hook config format for `PreToolUse:Bash` and point it at the copied script. If the installed Codex version does not expose hooks, do not claim guardrails are active; instead write a short note to `AGENTS.md` that destructive git commands require explicit user confirmation and suggest using a shell wrapper outside Codex.

**Global** (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/block-dangerous-git.sh"
          }
        ]
      }
    ]
  }
}
```

If the settings file already exists, merge the hook into existing `hooks.PreToolUse` array — don't overwrite other settings.

### 4. Ask about customization

Ask if user wants to add or remove any patterns from the blocked list. Edit the copied script accordingly.

### 5. Verify

Run a quick test:

```bash
echo '{"tool_input":{"command":"git push origin main"}}' | <path-to-script>
```

Should exit with code 2 and print a BLOCKED message to stderr.
