# MCP Servers

Labline keeps reviewer/chat/notification bridges under `mcp-servers/`. Some entries are true MCP stdio servers; `feishu-bridge` is an HTTP bridge kept here because it serves the same agent-integration layer.

## Index

| Path | Type | Tools / endpoints | Required env | Status |
|------|------|-------------------|--------------|--------|
| [claude-review/](claude-review/) | MCP reviewer | `review`, `review_reply`, `review_start`, `review_reply_start`, `review_status` | Claude CLI/API auth | Active |
| [codex-review/](codex-review/) | MCP reviewer | `codex`, `codex-reply` | `CODEX_API_KEY` or OpenAI-compatible config | Active |
| [gemini-review/](gemini-review/) | MCP reviewer | `review`, `review_reply`, `review_start`, `review_reply_start`, `review_status` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Active |
| [llm-chat/](llm-chat/) | MCP chat | `chat` | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | Generic fallback |
| [minimax-chat/](minimax-chat/) | MCP chat | `minimax_chat` | `MINIMAX_API_KEY` | Provider fallback |
| [feishu-bridge/](feishu-bridge/) | HTTP bridge | `POST /send`, `POST /update`, `GET /poll`, `POST /reply`, `GET /health`, `/control/*` | `FEISHU_APP_ID`, `FEISHU_APP_SECRET` | Notification and session-control bridge |
| [codex-image2/](codex-image2/) | MCP image bridge | `generate_start`, `generate_status` | local Codex app-server | Experimental |

## Local Checks

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  mcp-servers/claude-review/server.py \
  mcp-servers/codex-review/server.py \
  mcp-servers/codex-review/bridge.py \
  mcp-servers/gemini-review/server.py \
  mcp-servers/codex-image2/server.py
```

Provider smoke tests need live API keys and are intentionally manual.

## Feishu Control Endpoints

`feishu-bridge` exposes local HTTP endpoints for opt-in Codex Session control. The bridge records messages and approvals; it does not execute shell commands, tools, or skills itself.

| Endpoint | Purpose |
|----------|---------|
| `POST /control/register` | Register a Feishu-Controlled Session |
| `GET /control/sessions` | List sessions and active session |
| `POST /control/message` | Route Feishu text to the active or addressed session inbox |
| `POST /control/local-input` | Queue local input when the Control Lease allows it |
| `POST /control/request-approval` | Create a single-action Remote Action Approval |
| `POST /control/respond` | Record a Codex Session response in the outbox |

Runtime state defaults to `.labline/feishu-control/` under `LABLINE_PROJECT_ROOT`. Override with `LABLINE_FEISHU_CONTROL_ROOT` for tests or isolated deployments.

Feishu message sending defaults to `FEISHU_RECEIVE_ID_TYPE=open_id`. If `FEISHU_USER_ID` is a Feishu user ID or union ID, set `FEISHU_RECEIVE_ID_TYPE=user_id` or `FEISHU_RECEIVE_ID_TYPE=union_id`.

Set `FEISHU_ENABLE_WS=1` to enable Feishu long-connection inbound messages. Inbound private messages are routed into `/control/message`, so they enter the active Remote Session Inbox instead of executing tools in the bridge.

Run the bridge:

```bash
set -a; source .env; set +a
export FEISHU_ENABLE_WS=1
export LABLINE_PROJECT_ROOT="$PWD"
python mcp-servers/feishu-bridge/server.py
```

Run a managed Codex session that consumes the active inbox and replies through Feishu:

```bash
python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root "$PWD" \
  --profile leader \
  --bridge-url http://127.0.0.1:5000
```

Runner responses are sent as Feishu interactive cards by default (`--feishu-format card`) so Markdown can render. Use `--feishu-format text` for plain text.

To continue the most recent saved Codex conversation for each Feishu message, add `--resume-last`. To bind to a specific saved conversation, use `--codex-session-id <id>`. This uses `codex exec resume`; it does not inject text into an already-open TUI.

Avoid `--resume-last` when the latest Codex session is an active TUI. It can attach to the live session and leave the runner output file empty.

Add `--yolo` to pass Codex `--dangerously-bypass-approvals-and-sandbox`; use only on trusted machines and projects.

If the inbox contains old messages, run the session once with `--mark-seen --once` before starting the long-running runner.
