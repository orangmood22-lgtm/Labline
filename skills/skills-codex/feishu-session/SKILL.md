---
name: feishu-session
description: Manage Feishu/Lark remote Codex or Claude Code access, with lark-channel-bridge as the default transport and Labline phone-session reports as legacy/fallback audit support. Use when user mentions Feishu/Lark control, phone control, mobile takeover, session merge, or wants to start/stop/report a Feishu-controlled coding session.
argument-hint: "[start|mark-seen|report|merge]"
allowed-tools: Bash(*), Read
caller: any
platform: codex
status: needs-runtime-adaptation
consumes:
  - .labline/feishu-control/
produces:
  - .labline/feishu-control/reports/<session_id>.md
examples:
  - "/feishu-session start leader-phone"
  - "/feishu-session report leader-phone"
  - "把手机 session 合并回来"
---

# Feishu Session

Use this skill to control an auditable Feishu/Lark-facing Codex or Claude Code session. Prefer `lark-channel-bridge` as the transport adapter for normal Feishu/Lark remote control. Use the in-repo Labline Feishu runner only as a legacy/fallback path when you need Labline-managed inbox/outbox files, phone-session merge reports, or tmux live-TUI injection.

The bridge is transport, not workflow runtime: it forwards messages/status between Feishu/Lark and a local agent process. It does not become the Labline Leader, own workflow decisions, or execute research work outside the active Codex/Claude Code session's normal permissions.

## Core rule

Do not claim hidden model context moved between sessions. Phone control is a fork. Merge only auditable state: user messages, Codex replies, files, commands, decisions, and open questions.

## Default transport: lark-channel-bridge

Use the Labline wrapper for the external bridge:

```bash
lane feishu install
lane feishu doctor
```

Default install is user-local under `~/.labline/node`, so shared servers do not need sudo. Use `lane feishu install --scope system` only for an intentional admin-managed system install.

Start a Codex profile in the target workspace:

```bash
cd "[你的project位置]"
lane feishu run
```

Or run it as a background service:

```bash
cd "[你的project位置]"
lane feishu start
lane feishu status
```

For Claude Code, use a separate profile:

```bash
cd "[你的project位置]"
lane feishu run --profile labline-claude --agent claude
```

Local management:

```bash
lane feishu restart
lane feishu stop
lane feishu logs --tail 50
```

Common Feishu/Lark-side controls:

- `/cd <path>`: switch the current workspace.
- `/ws`: manage saved workspaces.
- `/status`: inspect profile, agent, workspace, session, identity, and run state.

Keep merge discipline even with the default bridge: before resuming locally from a phone-controlled thread, inspect the visible transcript, `git status --short`, and `git diff`; summarize files changed, commands run, decisions made, and open questions.

## Legacy/fallback Labline runner

Use this path only when the default transport cannot provide the audit surface you need, especially `.labline/feishu-control/` reports or tmux live-TUI injection.

### Health check

```bash
curl -sS http://127.0.0.1:5000/health
curl -sS http://127.0.0.1:5000/control/sessions
```

If the bridge is not running:

```bash
LABLINE_REPO="${LABLINE_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .labline/installed-skills-codex.txt 2>/dev/null)}"
[ -n "$LABLINE_REPO" ] || { echo "ERROR: LABLINE_REPO not set. Install Labline Codex skills or export LABLINE_REPO=/path/to/Labline."; exit 1; }
PYTHON="${LABLINE_FEISHU_PYTHON:-$LABLINE_REPO/.venv-feishu/bin/python}"
[ -x "$PYTHON" ] || PYTHON=python3
cd "$LABLINE_REPO"
set -a; source .env; set +a
export FEISHU_ENABLE_WS=1
export LABLINE_PROJECT_ROOT="[你的project位置]"
"$PYTHON" "$LABLINE_REPO/mcp-servers/feishu-bridge/server.py"
```

### Start phone runner

Prefer live TUI takeover when the local Codex CLI is in tmux:

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_command}'
```

Then inject Feishu messages into that exact pane:

```bash
LABLINE_REPO="${LABLINE_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .labline/installed-skills-codex.txt 2>/dev/null)}"
[ -n "$LABLINE_REPO" ] || { echo "ERROR: LABLINE_REPO not set. Install Labline Codex skills or export LABLINE_REPO=/path/to/Labline."; exit 1; }
PYTHON="${LABLINE_FEISHU_PYTHON:-$LABLINE_REPO/.venv-feishu/bin/python}"
[ -x "$PYTHON" ] || PYTHON=python3
"$PYTHON" "$LABLINE_REPO/tools/labline_feishu_session.py" \
  --session-id leader-phone \
  --role leader \
  --project-root "[你的project位置]" \
  --bridge-url http://127.0.0.1:5000 \
  --tmux-pane dev:1.0 \
  --feishu-status-interval-seconds 15
```

Do not run this and a fresh `codex exec` runner on the same `--session-id`.

### Generate phone report

```bash
LABLINE_REPO="${LABLINE_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .labline/installed-skills-codex.txt 2>/dev/null)}"
[ -n "$LABLINE_REPO" ] || { echo "ERROR: LABLINE_REPO not set. Install Labline Codex skills or export LABLINE_REPO=/path/to/Labline."; exit 1; }
PYTHON="${LABLINE_FEISHU_PYTHON:-$LABLINE_REPO/.venv-feishu/bin/python}"
[ -x "$PYTHON" ] || PYTHON=python3
"$PYTHON" "$LABLINE_REPO/tools/labline_feishu_session.py" \
  --session-id leader-phone \
  --project-root "[你的project位置]" \
  --write-report
```

This writes `.labline/feishu-control/reports/leader-phone.md`.

### Merge back locally

```bash
LABLINE_REPO="${LABLINE_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .labline/installed-skills-codex.txt 2>/dev/null)}"
[ -n "$LABLINE_REPO" ] || { echo "ERROR: LABLINE_REPO not set. Install Labline Codex skills or export LABLINE_REPO=/path/to/Labline."; exit 1; }
PYTHON="${LABLINE_FEISHU_PYTHON:-$LABLINE_REPO/.venv-feishu/bin/python}"
[ -x "$PYTHON" ] || PYTHON=python3
"$PYTHON" "$LABLINE_REPO/tools/labline_feishu_session.py" \
  --session-id leader-phone \
  --project-root "[你的project位置]" \
  --merge-prompt
```

Use the printed prompt in the local Codex thread. The local thread must read the report and inspect `git status --short` / `git diff` before continuing.
