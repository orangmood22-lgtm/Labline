# Feishu Integration

ARIS Feishu integration lets you receive notifications, send messages from Feishu into an opt-in Codex Session, and receive Codex responses back in Feishu.

## What Works

| Direction | Status | Path |
|-----------|--------|------|
| Local to Feishu | Supported | `POST /send`, `POST /update` for card updates |
| Feishu to local | Supported | Feishu long connection -> `/control/message` |
| Feishu message to Codex | Supported | `tools/aris_feishu_session.py` consumes inbox and runs `codex exec` |
| Codex response to Feishu | Supported | runner writes outbox and calls `/send` |
| Already-open Codex TUI takeover | Supported when TUI is in tmux | `--tmux-pane <target>` injects Feishu text into the live pane |

The bridge does not execute shell commands, tools, or skills itself. It only records messages and approvals. Codex execution happens inside the opt-in session runner.

## Terms

- **Feishu Bridge**: `mcp-servers/feishu-bridge/server.py`, local HTTP + Feishu long-connection process.
- **Remote Session Inbox**: `.aris/feishu-control/inbox/<session_id>.jsonl`.
- **Feishu-Controlled Session**: a registered session consumed by `tools/aris_feishu_session.py`.
- **Control Lease**: input ownership marker. Feishu messages can take remote priority; `/release` returns control to local.

See [CONTEXT.md](../CONTEXT.md) for stable terminology. Detailed ADRs are kept in the dev checkout and are not part of stable releases.

## Feishu App Setup

Create an internal app at <https://open.feishu.cn/app>.

Required app capability:

- Bot

Required permissions:

- `im:message`
- `im:message:send_as_bot`
- `im:message.p2p_msg:readonly`
- `im:message.group_at_msg:readonly`

Required event:

- `im.message.receive_v1`

Use long connection mode for local/server deployment. After changing permissions or events, create and publish a new app version. Ensure app visibility includes your account.

## Local Config

Create `.env` in the framework or project root. Do not commit it.

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_USER_ID=ou_xxx
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_ENABLE_WS=1
BRIDGE_PORT=5000
ARIS_PROJECT_ROOT=/aris/aris-dev
ARIS_FEISHU_CONTROL_ROOT=
```

`FEISHU_USER_ID` must match `FEISHU_RECEIVE_ID_TYPE`:

| ID value | `FEISHU_RECEIVE_ID_TYPE` |
|----------|---------------------------|
| `ou_...` | `open_id` |
| tenant user id | `user_id` |
| union id | `union_id` |

Install Python deps:

```bash
python3 -m venv .venv-feishu
.venv-feishu/bin/pip install -r mcp-servers/feishu-bridge/requirements.txt
```

If network fails because of proxy mismatch, make upper/lower proxy env vars consistent:

```bash
export HTTP_PROXY=http://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export https_proxy=http://127.0.0.1:7897
export NO_PROXY=127.0.0.1,localhost
export no_proxy=127.0.0.1,localhost
```

Adjust port to your local proxy.

## Start Bridge

Terminal 1:

```bash
cd /aris/aris-dev
set -a; source .env; set +a
export FEISHU_ENABLE_WS=1
export ARIS_PROJECT_ROOT=/aris/aris-dev
.venv-feishu/bin/python mcp-servers/feishu-bridge/server.py
```

Expected output includes:

```text
Feishu WS receiver enabled
connected to wss://msg-frontier.feishu.cn/ws/v2...
```

Smoke test:

```bash
curl -sS http://127.0.0.1:5000/health
curl -sS -X POST http://127.0.0.1:5000/send \
  -H 'Content-Type: application/json' \
  -d '{"type":"text","content":"ARIS Feishu bridge live test"}'
```

## Start Codex Runner

Terminal 2:

```bash
cd /aris/aris-dev
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /aris/aris-dev \
  --profile leader \
  --bridge-url http://127.0.0.1:5000
```

Codex replies are sent back to Feishu as interactive cards by default, so basic Markdown renders in Feishu. Use `--feishu-format text` to send plain text instead.

YOLO mode passes Codex `--dangerously-bypass-approvals-and-sandbox`:

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /aris/aris-dev \
  --profile leader \
  --bridge-url http://127.0.0.1:5000 \
  --feishu-format card \
  --yolo
```

Use YOLO only on a trusted machine and trusted project. In this mode, Codex can run commands without approval prompts.

Then send a private message to the Feishu bot. Flow:

```text
Feishu -> bridge -> Remote Session Inbox -> codex exec -> outbox -> Feishu
```

## Live TUI Takeover

If the Codex CLI you are looking at is inside tmux, Feishu can inject messages into that exact live thread:

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_command}'
```

Start the runner in live injection mode:

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /aris/aris-dev \
  --bridge-url http://127.0.0.1:5000 \
  --tmux-pane dev:1.0 \
  --feishu-status-interval-seconds 15
```

This sends Feishu messages directly into the active Codex TUI, waits 0.5 seconds, then submits with `Enter` by default. The bridge silently queues inbound messages by default; the runner updates one status card while Codex is processing and sends the final `task_complete.last_agent_message` back to Feishu.

Status card body is intentionally minimal:

```text
`leader-phone` · 已收到信息 · 0s
`leader-phone` · 思考中 · 15s
`leader-phone` · 处理中 · 30s
`leader-phone` · 已完成 · 61s
```

Use plain status text explicitly:

```bash
--feishu-status-style plain
```

Timeout updates the same card:

```text
`leader-phone` · 超时，未收到最终回复
```

To restore the old extra queue acknowledgement message, set:

```bash
FEISHU_SEND_QUEUE_ACK=1
```

If your TUI still inserts a newline instead of submitting, increase the delay or try a different submit key:

```bash
--tmux-submit-delay-seconds 1.0
--tmux-submit-key Enter
```

If the runner cannot locate the right Codex transcript automatically, bind it explicitly:

```bash
--codex-transcript ~/.codex/sessions/YYYY/MM/DD/rollout-....jsonl
```

Disable transcript mirroring if you only want injection acknowledgements:

```bash
--no-watch-codex-response
```

Disable heartbeat cards:

```bash
--no-feishu-status-updates
```

Force old behavior that sends a new status message each interval:

```bash
--feishu-status-mode send
```

Do not run live injection and fresh `codex exec` runner for the same `--session-id` at the same time; they will compete for the same inbox.

Continue newest saved Codex conversation:

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --project-root /aris/aris-dev \
  --bridge-url http://127.0.0.1:5000 \
  --resume-last
```

Do not use `--resume-last` while the newest Codex session is an active TUI you are currently using. `codex exec resume --last` can attach to that live session, while `--output-last-message` remains empty; the runner will then report that Codex produced no final message. Prefer fresh exec mode, or bind a specific inactive session with `--codex-session-id`.

If the inbox already contains old messages and you do not want to replay them:

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --project-root /aris/aris-dev \
  --bridge-url http://127.0.0.1:5000 \
  --mark-seen \
  --once
```

Bind a specific saved Codex conversation:

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --project-root /aris/aris-dev \
  --bridge-url http://127.0.0.1:5000 \
  --codex-session-id <codex-session-id>
```

## Feishu Commands

| Message | Effect |
|---------|--------|
| plain text | Sent to active session inbox |
| `$skill ...` | Sent to Codex runner as normal text; Codex decides skill/tool use |
| `/sessions` | List registered sessions |
| `/use <session_id>` | Switch active session |
| `@<session_id> message` | Route one message to a specific session |
| `/release` | Release Feishu Control Lease back to local |
| `/interrupt` | Interrupt the current live Codex TUI task with tmux `C-c` |
| `/btw <question>` | Ask a side-channel question using current transcript context; status updates in Feishu; answer returns to Feishu and does not enter the main CLI thread |
| `/approve <code>` | Approve one pending action |
| `/reject <code>` | Reject one pending action |
| `/resume <target>` | Record resume intent |

Rejected commands:

- `/run ...`
- `/tool ...`

These are intentionally not executed by the bridge.

## Runtime Files

Default root:

```text
.aris/feishu-control/
  sessions.json
  inbox/<session_id>.jsonl
  outbox/<session_id>.jsonl
  approvals/<code>.json
  runners/<session_id>.json
  reports/<session_id>.md
  responses/<session_id>/*.txt
```

These files are project runtime state and are ignored by Git.

## Phone Session Merge

Phone control is treated as a fork. Do not rely on hidden Codex context moving from phone runner back into the local TUI. Merge only auditable state.

Generate a report:

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --project-root /aris/aris-dev \
  --write-report
```

Generate a report and print a local merge prompt:

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --project-root /aris/aris-dev \
  --merge-prompt
```

The report includes inbox messages, outbox responses, runner state, `git status --short`, and `git diff --stat`. Use the printed prompt in the local Codex thread after returning to the computer.

The same workflow is exposed as the `feishu-session` skill.

## Testing

Run focused tests:

```bash
.venv-feishu/bin/python -m pytest \
  tests/test_aris_feishu_session.py \
  tests/test_feishu_control.py \
  tests/test_feishu_bridge_server.py \
  tests/test_agent_status.py -q
```

Manual live checks:

```bash
curl -sS http://127.0.0.1:5000/health
curl -sS http://127.0.0.1:5000/control/sessions
```

Send a private message to the bot and check:

```bash
tail -5 .aris/feishu-control/inbox/<session_id>.jsonl
tail -5 .aris/feishu-control/outbox/<session_id>.jsonl
```

## Troubleshooting

**Local can send to Feishu, but Feishu cannot message bot**

- Bot capability not enabled.
- App version not published.
- App visibility does not include your account.
- Missing `im:message.p2p_msg:readonly`.
- Missing `im.message.receive_v1` event.
- Long connection not running.

**`Invalid ids`**

`FEISHU_USER_ID` does not match `FEISHU_RECEIVE_ID_TYPE`. For `ou_...`, use `open_id`.

**No inbound messages**

Confirm bridge output says connected to `msg-frontier.feishu.cn`. If not, check app event mode and published version.

**Proxy connection refused**

Uppercase and lowercase proxy env vars may point to different ports. Make them consistent.

## Limitations

- Runner does not inject text into an already-open Codex TUI.
- Each Feishu message invokes `codex exec` or `codex exec resume`.
- Approval UI cards/buttons are backend-ready but not yet polished as interactive cards.
- Bridge executes no tools. This is deliberate.
