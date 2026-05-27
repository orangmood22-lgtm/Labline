#!/usr/bin/env python3
"""Codex MCP Server — wraps OpenAI-compatible API for Claude Code.

Reads API key and model from ~/.codex/config.toml and ~/.codex/auth.json.
Exposes two tools: `codex` (fresh review) and `codex-reply` (continue session).

Install in Claude Code via .mcp.json:
  {
    "mcpServers": {
      "codex": {
        "command": "python3",
        "args": ["path/to/mcp-servers/codex-review/server.py"]
      }
    }
  }
"""

import json
import os
import sys
import base64
import urllib.request
import urllib.error
import uuid
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SERVER_NAME = "codex-review"
DEBUG_LOG = Path(tempfile.gettempdir()) / "codex-review-mcp-debug.log"

# ─── Config loading ──────────────────────────────────────────────────────────


def load_codex_config():
    """Load API config from ~/.codex/ with env var overrides."""
    config = {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-5.5",
        "wire_api": "chat_completions",
    }

    toml_path = Path.home() / ".codex" / "config.toml"
    if toml_path.is_file():
        try:
            raw = toml_path.read_text()
            provider_name = None
            current_section = None
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Track section
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].strip()
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip().strip('"'), v.strip().strip('"')
                # Top-level keys
                if current_section is None:
                    if k == "model" and v:
                        config["model"] = v
                    elif k == "base_url" and v:
                        config["base_url"] = v.rstrip("/")
                    elif k == "wire_api" and v:
                        config["wire_api"] = v
                    elif k == "model_provider" and v:
                        provider_name = v
                # Provider section keys (override top-level)
                elif provider_name and current_section == f"model_providers.{provider_name}":
                    if k == "base_url" and v:
                        config["base_url"] = v.rstrip("/")
                    elif k == "wire_api" and v:
                        config["wire_api"] = v
                    elif k == "model" and v:
                        config["model"] = v
        except OSError:
            pass

    # try auth.json for key
    auth_path = Path.home() / ".codex" / "auth.json"
    if auth_path.is_file():
        try:
            auth_data = json.loads(auth_path.read_text())
            for provider_name, provider_data in auth_data.items():
                # Codex stores keys as either:
                #   {"provider": {"key": "sk-..."}}  (dict form)
                #   {"OPENAI_API_KEY": "sk-..."}     (flat string form)
                if isinstance(provider_data, dict):
                    key = provider_data.get("key") or provider_data.get("api_key") or ""
                    if key:
                        config["api_key"] = key
                        break
                elif isinstance(provider_data, str) and provider_data.startswith("sk-"):
                    config["api_key"] = provider_data
                    break
        except (json.JSONDecodeError, OSError):
            pass

    # env var overrides
    if os.environ.get("CODEX_API_KEY"):
        config["api_key"] = os.environ["CODEX_API_KEY"]
    if os.environ.get("CODEX_BASE_URL"):
        config["base_url"] = os.environ["CODEX_BASE_URL"].rstrip("/")
    if os.environ.get("CODEX_MODEL"):
        config["model"] = os.environ["CODEX_MODEL"]

    return config


CONFIG = load_codex_config()

# ─── MCP protocol helpers ────────────────────────────────────────────────────


def debug(msg):
    try:
        DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except OSError:
        pass


def send(resp):
    payload = json.dumps(resp, ensure_ascii=False)
    sys.stdout.write(payload + "\n")
    sys.stdout.flush()


def read_msg():
    line = sys.stdin.readline()
    if not line:
        return None
    text = line.rstrip("\r\n")
    if not text:
        return None
    if text.lower().startswith("content-length:"):
        # Standard MCP stdio framing: Content-Length: N\r\n\r\n{body}
        try:
            cl = int(text.split(":", 1)[1].strip())
        except ValueError:
            return None
        while True:
            h = sys.stdin.readline()
            if not h or h in {"\r\n", "\n"}:
                break
        body = sys.stdin.read(cl)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None
    else:
        # NDJSON (newline-delimited JSON) — used by newer Claude Code
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            debug(f"PARSE_ERROR first_line={text[:200]}")
            return None


def tool_ok(req_id, data):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]},
    }


def tool_err(req_id, msg):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": json.dumps({"error": msg}, ensure_ascii=False)}], "isError": True},
    }


# ─── API call ────────────────────────────────────────────────────────────────


def call_chat_completions_api(prompt, model, system, messages=None):
    """Call /chat/completions endpoint."""
    url = f"{CONFIG['base_url']}/chat/completions"
    if messages:
        body = {"model": model, "messages": list(messages), "temperature": 0.2, "max_tokens": 16384}
    else:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        body = {"model": model, "messages": msgs, "temperature": 0.2, "max_tokens": 16384}
    return _post_json(url, body, model)


def call_responses_api(prompt, model, system, messages=None):
    """Call /responses endpoint (OpenAI Responses API)."""
    url = f"{CONFIG['base_url']}/responses"
    if messages:
        # Convert chat-completion messages to Responses API input array
        body = {"model": model, "input": list(messages), "temperature": 0.2, "max_output_tokens": 16384}
    else:
        body = {"model": model, "input": prompt, "temperature": 0.2, "max_output_tokens": 16384}
        if system:
            body["instructions"] = system
    result = _post_json(url, body, model)
    if result is None:
        return None
    outputs = result.get("_raw", {}).get("output", [])
    text = ""
    for item in outputs:
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text += c.get("text", "")
    return {"response": text.strip(), "model": model, "stop_reason": result.get("_raw", {}).get("status")}


def _post_json(url, body, model):
    """POST JSON to an OpenAI-compatible endpoint, return parsed response or None."""
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {CONFIG['api_key']}"},
        method="POST",
    )
    debug(f"CALL {url} model={model} key_set={bool(CONFIG['api_key'])} wire_api={CONFIG.get('wire_api','chat_completions')}")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        # For chat_completions wire_api, parse the standard format
        if CONFIG.get("wire_api") != "responses":
            choice = data.get("choices", [{}])[0]
            text = choice.get("message", {}).get("content", "") or choice.get("text", "")
            return {"response": text.strip(), "model": model, "stop_reason": choice.get("finish_reason")}
        # For responses wire_api, return raw for caller to parse
        return {"_raw": data, "model": model}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        debug(f"HTTP {e.code}: {err_body}")
        return None
    except Exception as e:
        debug(f"API error: {e}")
        return None


def call_openai_api(prompt, model=None, system=None, messages=None):
    """Route to the correct API endpoint based on wire_api config."""
    effective_model = model or CONFIG["model"]
    wire = CONFIG.get("wire_api", "chat_completions")
    if wire == "responses":
        return call_responses_api(prompt, effective_model, system, messages=messages)
    return call_chat_completions_api(prompt, effective_model, system, messages=messages)


# ─── Thread history (simple file-based) ──────────────────────────────────────


THREADS_DIR = Path.home() / ".codex" / "state" / "codex-review" / "threads"
THREADS_DIR.mkdir(parents=True, exist_ok=True)


def load_thread(tid):
    p = THREADS_DIR / f"{tid}.json"
    if p.is_file():
        return json.loads(p.read_text())
    return {"threadId": tid, "messages": []}


def save_thread(tid, msgs):
    THREADS_DIR.mkdir(parents=True, exist_ok=True)
    (THREADS_DIR / f"{tid}.json").write_text(json.dumps({"threadId": tid, "messages": msgs}, ensure_ascii=False, indent=2))


# ─── Request handler ─────────────────────────────────────────────────────────


def handle(req):
    rid = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})
    debug(f"REQ id={rid} method={method}")

    if rid is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": "1.0.0"},
            },
        }

    if method in ("ping", "notifications/initialized", "initialized"):
        return {"jsonrpc": "2.0", "id": rid, "result": {}}

    if method == "tools/list":
        base_schema = {
            "prompt": {"type": "string", "description": "Review prompt / task description"},
            "system": {"type": "string", "description": "Optional system prompt"},
            "model": {"type": "string", "description": f"Model override (default: {CONFIG['model']})"},
        }
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "tools": [
                    {
                        "name": "codex",
                        "description": "Start a fresh GPT review via Codex API. Returns response text and threadId.",
                        "inputSchema": {
                            "type": "object",
                            "properties": base_schema,
                            "required": ["prompt"],
                        },
                    },
                    {
                        "name": "codex-reply",
                        "description": "Continue a previous Codex session using threadId.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "threadId": {"type": "string", "description": "Thread ID from previous codex call"},
                                **base_schema,
                            },
                            "required": ["prompt", "threadId"],
                        },
                    },
                ]
            },
        }

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {}) or {}
        prompt = str(args.get("prompt", ""))
        sys_prompt = args.get("system") or None
        model = args.get("model") or None

        if name == "codex":
            result = call_openai_api(prompt, model=model, system=sys_prompt)
            if result is None:
                return tool_err(rid, "Codex API call failed. Check ~/.codex/ config and network.")
            tid = uuid.uuid4().hex
            save_thread(tid, [
                {"role": "system", "content": sys_prompt or ""},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": result["response"]},
            ])
            result["threadId"] = tid
            return tool_ok(rid, result)

        if name == "codex-reply":
            tid = args.get("threadId") or args.get("thread_id")
            if not tid:
                return tool_err(rid, "threadId is required")
            thread = load_thread(tid)
            history = thread.get("messages", [])
            msgs = [m for m in history if m.get("content")]
            msgs.append({"role": "user", "content": prompt})
            result = call_openai_api(prompt, model=model, system=None, messages=msgs)
            if result is None:
                return tool_err(rid, "Codex reply failed. Check ~/.codex/ config and network.")
            msgs.append({"role": "assistant", "content": result["response"]})
            save_thread(tid, msgs)
            result["threadId"] = tid
            return tool_ok(rid, result)

        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main():
    debug(f"=== {SERVER_NAME} startup === base_url={CONFIG['base_url']} model={CONFIG['model']} key_set={bool(CONFIG['api_key'])}")
    while True:
        try:
            req = read_msg()
            if req is None:
                break
            resp = handle(req)
            if resp is not None:
                send(resp)
        except Exception:
            import traceback
            debug(traceback.format_exc())
            break


def main_tcp(port=9876):
    """Run the MCP server over TCP (for cross-WSL-boundary use)."""
    import socketserver

    class MCPHandler(socketserver.StreamRequestHandler):
        def handle(self):
            debug(f"TCP client connected from {self.client_address}")
            try:
                while True:
                    # Read Content-Length header
                    line = self.rfile.readline()
                    if not line:
                        break
                    text = line.decode("utf-8").rstrip("\r\n")
                    if not text.lower().startswith("content-length:"):
                        continue
                    try:
                        cl = int(text.split(":", 1)[1].strip())
                    except ValueError:
                        continue
                    # Read blank line
                    while True:
                        h = self.rfile.readline()
                        if not h or h in {b"\r\n", b"\n"}:
                            break
                    # Read body
                    body = self.rfile.read(cl)
                    try:
                        req = json.loads(body.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue
                    debug(f"TCP REQ id={req.get('id')} method={req.get('method','')}")
                    resp = handle(req)
                    if resp is not None:
                        payload = json.dumps(resp, ensure_ascii=False).encode("utf-8")
                        header = f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
                        self.wfile.write(header + payload)
                        self.wfile.flush()
            except Exception:
                import traceback
                debug(f"TCP handler error: {traceback.format_exc()}")

    host = os.environ.get("CODEX_MCP_HOST", "127.0.0.1")
    with socketserver.ThreadingTCPServer((host, port), MCPHandler) as srv:
        debug(f"=== {SERVER_NAME} TCP listening on {host}:{port} === base_url={CONFIG['base_url']} model={CONFIG['model']} key_set={bool(CONFIG['api_key'])}")
        srv.serve_forever()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tcp", type=int, default=0, help="Run in TCP mode on the given port")
    opts = ap.parse_args()
    if opts.tcp:
        main_tcp(opts.tcp)
    else:
        main()
