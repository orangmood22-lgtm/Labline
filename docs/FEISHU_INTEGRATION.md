# Feishu / Lark Integration

For Codex + Claude Code remote control from Feishu/Lark, Labline recommends
[`lark-channel-bridge`](https://github.com/zarazhangrui/lark-coding-agent-bridge) as the default bridge. It is an external transport adapter for local Codex CLI or Claude Code sessions, with streaming cards, per-chat sessions, workspace switching, and first-run QR setup.

The older in-repo path, `mcp-servers/feishu-bridge` plus `tools/labline_feishu_session.py`, remains documented below as a legacy/fallback Labline-managed runner. Use it when you specifically need Labline inbox/outbox files, report generation, or tmux injection behavior.

## Recommended Path: `lark-channel-bridge`

`lark-channel-bridge` forwards Feishu/Lark messages to a local `codex` or `claude` process. It does not make Feishu a remote shell, does not become the Labline Leader, and does not own workflow decisions. Execution still happens in the local Codex/Claude Code session, under that agent's normal permissions and the selected workspace.

Labline wraps the external bridge with `lane feishu ...` so users do not need to remember the long bridge command. The wrapper does not vendor or reimplement `lark-channel-bridge`; it installs, launches, checks, and locates logs for the external CLI.

Prerequisites:

- Node.js >= 20.12
- Codex CLI or Claude Code installed and logged in locally
- A Feishu/Lark PersonalAgent app; the first-run QR wizard can create and bind one

Install:

```bash
lane feishu install
lane feishu doctor
```

`lane feishu install` defaults to a user-local npm prefix under `~/.labline/node`, so it works for non-root users on shared servers. Labline automatically adds that prefix's `bin` directory when running `lane feishu ...`. Administrators who intentionally want a system-wide install can use `lane feishu install --scope system`.

First-run foreground setup for the current project directory:

```bash
cd [你的project位置]
lane feishu run
```

This starts `lark-channel-bridge run --profile lane-codex --agent codex --workspace [当前目录]`. The first run opens the bridge QR wizard if the PersonalAgent app is not configured yet.

After the QR setup works, run the Codex profile as a background service:

```bash
cd [你的project位置]
lane feishu start
lane feishu status
```

For Claude Code, use a separate profile:

```bash
cd [你的project位置]
lane feishu run --profile lane-claude --agent claude
```

Useful local commands:

```bash
lane feishu stop
lane feishu restart
lane feishu logs --tail 50
```

If startup fails with `could not resolve bot identity` and the log shows `Request failed with status code 502`, retry without proxy. Some local HTTP proxies do not handle the Node SDK's Feishu API requests correctly, while direct access still works:

```bash
lane feishu run --no-proxy
lane feishu start --no-proxy
```

Common Feishu/Lark commands:

| Command | Effect |
|---------|--------|
| `/cd <path>` | Switch the current project/workspace directory |
| `/ws` | Manage saved workspaces, such as list/save/use |
| `/status` | Show profile, agent, working directory, session, identity, and run state |

Use `/cd [你的project位置]` after startup if you did not pass `--workspace`, or when moving a chat thread to another Labline project.

## Labline Boundary

Feishu/Lark integration is a Transport Adapter Skill boundary in Labline terms. The bridge transports messages, status, approvals, files, or reports between chat and a local agent process. It is not a Leader, not a workflow runtime, and not a remote shell. Research orchestration remains in the active Codex/Claude Code session and the Labline skills it invokes.

## Legacy / Fallback: Labline-Managed Runner

The sections below describe the older Labline-managed path:

```text
mcp-servers/feishu-bridge/server.py + tools/labline_feishu_session.py
```

Keep using this path only when you need Labline-managed runtime files, explicit inbox/outbox inspection, phone-session merge reports, or the tmux live-TUI injection flow.

## What Works

| Direction | Status | Path |
|-----------|--------|------|
| Local to Feishu | Supported | `POST /send`, `POST /update` for card updates |
| Feishu to local | Supported | Feishu long connection -> `/control/message` |
| Feishu message to Codex | Legacy/fallback | `tools/labline_feishu_session.py` consumes inbox and runs `codex exec` |
| Codex response to Feishu | Legacy/fallback | runner writes outbox and calls `/send` |
| Already-open Codex TUI takeover | Legacy/fallback | `--tmux-pane <target>` injects Feishu text into the live pane |

The bridge does not execute shell commands, tools, or skills itself. It only records messages and approvals. Codex execution happens inside the opt-in session runner.

## Terms

- **Recommended Bridge**: `lark-channel-bridge`, external Feishu/Lark transport adapter for local Codex CLI or Claude Code.
- **Legacy Feishu Bridge**: `mcp-servers/feishu-bridge/server.py`, local HTTP + Feishu long-connection process.
- **Remote Session Inbox**: `.labline/feishu-control/inbox/<session_id>.jsonl`.
- **Feishu-Controlled Session**: a legacy registered session consumed by `tools/labline_feishu_session.py`.
- **Control Lease**: input ownership marker. Feishu messages can take remote priority; `/release` returns control to local.

See [CONTEXT.md](../CONTEXT.md) for stable terminology. Detailed ADRs are kept in the dev checkout and are not part of stable releases.

## Legacy Feishu App Setup

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

## Legacy Local Config

Create `.env` in the framework or project root. Do not commit it.

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_USER_ID=ou_xxx
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_ENABLE_WS=1
BRIDGE_PORT=5000
LABLINE_PROJECT_ROOT=/lane/lane-dev
LABLINE_FEISHU_CONTROL_ROOT=
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

## Start Legacy Bridge

Terminal 1:

```bash
cd /lane/lane-dev
set -a; source .env; set +a
export FEISHU_ENABLE_WS=1
export LABLINE_PROJECT_ROOT=/lane/lane-dev
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
  -d '{"type":"text","content":"Labline Feishu bridge live test"}'
```

## Start Legacy Codex Runner

Terminal 2:

```bash
cd /lane/lane-dev
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /lane/lane-dev \
  --profile leader \
  --bridge-url http://127.0.0.1:5000
```

Codex replies are sent back to Feishu as interactive cards by default, so basic Markdown renders in Feishu. Use `--feishu-format text` to send plain text instead.

YOLO mode passes Codex `--dangerously-bypass-approvals-and-sandbox`:

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /lane/lane-dev \
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
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /lane/lane-dev \
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
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --bridge-url http://127.0.0.1:5000 \
  --resume-last
```

Do not use `--resume-last` while the newest Codex session is an active TUI you are currently using. `codex exec resume --last` can attach to that live session, while `--output-last-message` remains empty; the runner will then report that Codex produced no final message. Prefer fresh exec mode, or bind a specific inactive session with `--codex-session-id`.

If the inbox already contains old messages and you do not want to replay them:

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --bridge-url http://127.0.0.1:5000 \
  --mark-seen \
  --once
```

Bind a specific saved Codex conversation:

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --bridge-url http://127.0.0.1:5000 \
  --codex-session-id <codex-session-id>
```

## Legacy Feishu Commands

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

These are intentionally not executed by the legacy bridge.

## Legacy Runtime Files

Default root:

```text
.labline/feishu-control/
  sessions.json
  inbox/<session_id>.jsonl
  outbox/<session_id>.jsonl
  approvals/<code>.json
  runners/<session_id>.json
  reports/<session_id>.md
  responses/<session_id>/*.txt
```

These files are project runtime state and are ignored by Git.

## Legacy Phone Session Merge

Phone control is treated as a fork. Do not rely on hidden Codex context moving from phone runner back into the local TUI. Merge only auditable state.

Generate a report:

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --write-report
```

Generate a report and print a local merge prompt:

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --merge-prompt
```

The report includes inbox messages, outbox responses, runner state, `git status --short`, and `git diff --stat`. Use the printed prompt in the local Codex thread after returning to the computer.

The same fallback workflow is exposed as the `feishu-session` skill.

## Testing

Run focused tests:

```bash
.venv-feishu/bin/python -m pytest \
  tests/test_labline_feishu_session.py \
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
tail -5 .labline/feishu-control/inbox/<session_id>.jsonl
tail -5 .labline/feishu-control/outbox/<session_id>.jsonl
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

## Legacy Limitations

- The legacy fresh runner path invokes `codex exec` or `codex exec resume` for each Feishu message.
- Approval UI cards/buttons are backend-ready but not yet polished as interactive cards.
- The legacy bridge executes no tools. This is deliberate.
- The legacy path is Codex-oriented; use `lark-channel-bridge` for the default Codex + Claude Code remote-control bridge.
