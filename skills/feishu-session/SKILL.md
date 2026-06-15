---
name: feishu-session
description: Manage Feishu-controlled Codex sessions, phone runners, and auditable phone-session merge reports. Use when user mentions Feishu control, phone control, mobile takeover, session merge, or wants to start/stop/report a Feishu Codex runner.
argument-hint: "[start|mark-seen|report|merge]"
allowed-tools: Bash(*), Read
caller: any
platform: both
status: needs-runtime-adaptation
consumes:
  - .aris/feishu-control/
produces:
  - .aris/feishu-control/reports/<session_id>.md
examples:
  - "/feishu-session start leader-phone"
  - "/feishu-session report leader-phone"
  - "把手机 session 合并回来"
---

# Feishu Session

Use this skill to operate the Feishu bridge and the opt-in Codex runner. The bridge records messages; the runner either injects into a live tmux Codex TUI or runs Codex in a separate exec session.

## Core rule

Do not claim hidden model context moved between sessions. Phone control is a fork. Merge only auditable state: user messages, Codex replies, files, commands, decisions, and open questions.

## Health check

```bash
curl -sS http://127.0.0.1:5000/health
curl -sS http://127.0.0.1:5000/control/sessions
```

If the bridge is not running:

```bash
cd /aris/aris-dev
set -a; source .env; set +a
export FEISHU_ENABLE_WS=1
export ARIS_PROJECT_ROOT=/aris/aris-dev
.venv-feishu/bin/python mcp-servers/feishu-bridge/server.py
```

## Start phone runner

Prefer live TUI takeover when the local Codex CLI is in tmux:

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_command}'
```

Then inject Feishu messages into that exact pane:

```bash
cd /aris/aris-dev
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /aris/aris-dev \
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
cd /aris/aris-dev
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /aris/aris-dev \
  --bridge-url http://127.0.0.1:5000 \
  --feishu-format card \
  --yolo
```

Use `tmux` for long-running runners:

```bash
tmux new -d -s feishu-runner-leader-phone \
  '.venv-feishu/bin/python tools/aris_feishu_session.py --session-id leader-phone --role leader --project-root /aris/aris-dev --bridge-url http://127.0.0.1:5000 --feishu-format card --yolo'
```

Avoid `--resume-last` while a local Codex TUI is active. It can attach to the live TUI and produce an empty runner response.

## Mark old messages seen

Use before starting a runner if the inbox contains stale messages:

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --project-root /aris/aris-dev \
  --mark-seen \
  --once
```

## Generate phone report

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --project-root /aris/aris-dev \
  --write-report
```

This writes `.aris/feishu-control/reports/leader-phone.md`.

## Merge back locally

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --project-root /aris/aris-dev \
  --merge-prompt
```

Use the printed prompt in the local Codex thread. The local thread must read the report and inspect `git status --short` / `git diff` before continuing.
