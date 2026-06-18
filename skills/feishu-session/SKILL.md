---
name: feishu-session
description: Manage Feishu/Lark remote Codex or Claude Code access, with lark-channel-bridge as the default transport and Labline phone-session reports as legacy/fallback audit support. Use when user mentions Feishu/Lark control, phone control, mobile takeover, session merge, or wants to start/stop/report a Feishu-controlled coding session.
argument-hint: "[start|mark-seen|report|merge]"
allowed-tools: Bash(*), Read
caller: any
platform: both
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
cd "[你的framework位置]"
set -a; source .env; set +a
export FEISHU_ENABLE_WS=1
export LABLINE_PROJECT_ROOT="[你的project位置]"
.venv-feishu/bin/python mcp-servers/feishu-bridge/server.py
```

### Start phone runner

Prefer live TUI takeover when the local Codex CLI is in tmux:

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_command}'
```

Then inject Feishu messages into that exact pane:

```bash
cd "[你的framework位置]"
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root "[你的project位置]" \
  --bridge-url http://127.0.0.1:5000 \
  --tmux-pane dev:1.0 \
  --feishu-status-interval-seconds 15
```

Live mode waits 0.5 seconds after paste, submits with `Enter`, updates one Feishu status card while Codex is processing, then sends the final `task_complete.last_agent_message` back to Feishu. If the TUI inserts a newline instead of submitting, restart with a larger `--tmux-submit-delay-seconds`, such as `1.0`.

Status cards are intentionally minimal: short state + time, e.g. ``leader-phone · 思考中 · 15s``. `--feishu-status-style warm` is kept for compatibility but does not add extra copy by default.

If transcript auto-detection chooses the wrong file, restart with `--codex-transcript ~/.codex/sessions/YYYY/MM/DD/rollout-....jsonl`.

Do not run this and a fresh `codex exec` runner on the same `--session-id`.

Live control commands:

- `/interrupt`: send `C-c` to the live tmux Codex pane and mark the status card interrupted.
- `/btw <question>`: run an isolated side-channel `codex exec` using current transcript tail as read-only context; Feishu gets immediate/status/final cards, main CLI thread remains untouched.

Use fresh exec mode only when no live TUI should be controlled:

```bash
cd "[你的framework位置]"
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root "[你的project位置]" \
  --bridge-url http://127.0.0.1:5000 \
  --feishu-format card \
  --yolo
```

Use `tmux` for long-running runners:

```bash
tmux new -d -s feishu-runner-leader-phone \
  '.venv-feishu/bin/python tools/labline_feishu_session.py --session-id leader-phone --role leader --project-root "[你的project位置]" --bridge-url http://127.0.0.1:5000 --feishu-format card --yolo'
```

Avoid `--resume-last` while a local Codex TUI is active. It can attach to the live TUI and produce an empty runner response.

### Mark old messages seen

Use before starting a runner if the inbox contains stale messages:

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root "[你的project位置]" \
  --mark-seen \
  --once
```

### Generate phone report

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root "[你的project位置]" \
  --write-report
```

This writes `.labline/feishu-control/reports/leader-phone.md`.

### Merge back locally

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root "[你的project位置]" \
  --merge-prompt
```

Use the printed prompt in the local Codex thread. The local thread must read the report and inspect `git status --short` / `git diff` before continuing.
