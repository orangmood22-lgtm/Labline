#!/usr/bin/env python3
"""
Feishu Bridge Server — provides HTTP API for ARIS skills to send messages
to Feishu and poll for user replies.

Endpoints:
  POST /send   — send a card message to Feishu user, return message_id
  GET  /poll    — wait for user reply (long-poll with timeout)
  GET  /health  — health check

Requires:
  pip install lark-oapi

Environment variables:
  FEISHU_APP_ID      — Feishu app ID
  FEISHU_APP_SECRET  — Feishu app secret
  FEISHU_USER_ID     — Target user's open_id (who receives notifications)
  BRIDGE_PORT        — HTTP port (default: 5000)
"""

import os
import sys
import json
import time
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        CreateMessageRequest, CreateMessageRequestBody,
        PatchMessageRequest, PatchMessageRequestBody,
    )
except ImportError:
    print("Error: lark-oapi not installed. Run: pip install lark-oapi", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
APP_ID = os.environ.get("FEISHU_APP_ID", "")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
USER_ID = os.environ.get("FEISHU_USER_ID", "")
RECEIVE_ID_TYPE = os.environ.get("FEISHU_RECEIVE_ID_TYPE", "open_id")
PORT = int(os.environ.get("BRIDGE_PORT", "5000"))
ENABLE_WS = os.environ.get("FEISHU_ENABLE_WS", "").lower() in {"1", "true", "yes", "on"}
SEND_QUEUE_ACK = os.environ.get("FEISHU_SEND_QUEUE_ACK", "").lower() in {"1", "true", "yes", "on"}
REPO_ROOT = Path(__file__).resolve().parents[2]
FEISHU_CONTROL = REPO_ROOT / "tools" / "feishu_control.py"
CONTROL_ROOT = os.environ.get("ARIS_FEISHU_CONTROL_ROOT", "")
PROJECT_ROOT = os.environ.get("ARIS_PROJECT_ROOT", str(REPO_ROOT))

if not APP_ID or not APP_SECRET:
    print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET are required", file=sys.stderr)
    sys.exit(1)

if not USER_ID:
    print("Warning: FEISHU_USER_ID not set — /send will require user_id in request body", file=sys.stderr)

# --- Lark Client ---
client = lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()

# --- Reply Store (thread-safe) ---
reply_store = {}
reply_lock = threading.Lock()
reply_events = {}


def build_card_content(title: str, body: str, color: str = "blue") -> str:
    return json.dumps({
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": color,
        },
        "elements": [
            {"tag": "markdown", "content": body}
        ]
    })


def send_card(user_id: str, title: str, body: str, color: str = "blue") -> dict:
    """Send an interactive card to a Feishu user."""
    card = build_card_content(title, body, color)

    request = CreateMessageRequest.builder() \
        .receive_id_type(RECEIVE_ID_TYPE) \
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(user_id)
            .msg_type("interactive")
            .content(card)
            .build()
        ).build()

    response = client.im.v1.message.create(request)

    if not response.success():
        return {"error": response.msg, "code": response.code}

    msg_id = response.data.message_id
    # Prepare reply event for this message
    with reply_lock:
        reply_events[msg_id] = threading.Event()
        reply_store[msg_id] = None

    return {"ok": True, "message_id": msg_id}


def update_card(message_id: str, title: str, body: str, color: str = "blue") -> dict:
    """Update an existing Feishu interactive card message."""
    request = PatchMessageRequest.builder() \
        .message_id(message_id) \
        .request_body(
            PatchMessageRequestBody.builder()
            .content(build_card_content(title, body, color))
            .build()
        ).build()

    response = client.im.v1.message.patch(request)

    if not response.success():
        return {"error": response.msg, "code": response.code}

    return {"ok": True, "message_id": message_id}


def send_text(user_id: str, text: str) -> dict:
    """Send a plain text message to a Feishu user."""
    request = CreateMessageRequest.builder() \
        .receive_id_type(RECEIVE_ID_TYPE) \
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(user_id)
            .msg_type("text")
            .content(json.dumps({"text": text}))
            .build()
        ).build()

    response = client.im.v1.message.create(request)

    if not response.success():
        return {"error": response.msg, "code": response.code}

    return {"ok": True, "message_id": response.data.message_id}


def poll_reply(message_id: str, timeout: int = 300) -> dict:
    """Wait for a user reply to a specific message."""
    with reply_lock:
        event = reply_events.get(message_id)

    if not event:
        return {"error": "unknown message_id"}

    # Wait for reply or timeout
    got_reply = event.wait(timeout=timeout)

    with reply_lock:
        reply = reply_store.pop(message_id, None)
        reply_events.pop(message_id, None)

    if got_reply and reply:
        return {"reply": reply}
    else:
        return {"timeout": True}


def receive_reply(message_id: str, text: str):
    """Called when a user replies (webhook or external trigger)."""
    with reply_lock:
        if message_id in reply_store:
            reply_store[message_id] = text
            reply_events[message_id].set()


def run_control(args: list[str]) -> tuple[int, dict]:
    """Run the Feishu control CLI and return its JSON payload."""
    command = [sys.executable, str(FEISHU_CONTROL)]
    if CONTROL_ROOT:
        command.extend(["--state-root", CONTROL_ROOT])
    else:
        command.extend(["--project-root", PROJECT_ROOT])
    command.extend(args)
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"error": "invalid control response", "stdout": completed.stdout, "stderr": completed.stderr}
    if completed.stderr and "error" not in payload:
        payload["stderr"] = completed.stderr
    return completed.returncode, payload


def extract_message_text(content: str | None, message_type: str | None) -> str:
    """Extract plain user text from a Feishu message event."""
    if not content:
        return ""
    if message_type != "text":
        return f"[{message_type or 'unknown'} message]"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return content
    text = data.get("text", "")
    return text if isinstance(text, str) else ""


def event_sender_open_id(data) -> str:
    sender = getattr(getattr(data, "event", None), "sender", None)
    sender_id = getattr(sender, "sender_id", None)
    return getattr(sender_id, "open_id", "") or USER_ID


def handle_inbound_message_event(data) -> dict:
    """Route a Feishu inbound message into the active Remote Session Inbox."""
    event = getattr(data, "event", None)
    message = getattr(event, "message", None)
    text = extract_message_text(getattr(message, "content", None), getattr(message, "message_type", None))
    message_id = getattr(message, "message_id", "")
    if not text.strip():
        return {"status": "ignored_empty_message", "message_id": message_id}

    sender_open_id = event_sender_open_id(data)
    control_args = ["handle-message", "--text", text]
    if sender_open_id:
        control_args.extend(["--sender-open-id", sender_open_id])
    code, payload = run_control(control_args)
    payload["message_id"] = message_id
    payload["control_exit_code"] = code

    if code == 0 and SEND_QUEUE_ACK:
        try:
            send_text(sender_open_id, f"ARIS received: {payload.get('status', 'ok')}")
        except Exception as exc:
            payload["ack_error"] = str(exc)
    return payload


def start_ws_client() -> None:
    """Start Feishu long-connection event receiver. Blocks forever."""
    from lark_oapi.ws import Client as WSClient

    def on_message(data) -> None:
        result = handle_inbound_message_event(data)
        print(f"[feishu-ws] inbound message routed: {json.dumps(result, ensure_ascii=False)}", flush=True)

    handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_message)
        .build()
    )
    ws_client = WSClient(APP_ID, APP_SECRET, event_handler=handler)
    ws_client.start()


# --- HTTP Handler ---
class BridgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._json_response({"status": "ok", "port": PORT, "receive_id_type": RECEIVE_ID_TYPE})
            return

        if self.path == "/control/sessions":
            code, payload = run_control(["sessions", "--json"])
            self._json_response(payload, 200 if code == 0 else 400)
            return

        if self.path.startswith("/poll"):
            # Parse query params
            params = {}
            if "?" in self.path:
                query = self.path.split("?", 1)[1]
                for pair in query.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v

            message_id = params.get("message_id", "")
            timeout = int(params.get("timeout", "300"))

            if not message_id:
                self._json_response({"error": "message_id required"}, 400)
                return

            result = poll_reply(message_id, timeout)
            self._json_response(result)
            return

        self._json_response({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == "/send":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}

            user_id = body.get("user_id", USER_ID)
            if not user_id:
                self._json_response({"error": "user_id required (set FEISHU_USER_ID or pass in body)"}, 400)
                return

            msg_type = body.get("type", "card")
            title = body.get("title", "ARIS Notification")
            content = body.get("body", body.get("content", ""))
            color = body.get("color", "blue")

            try:
                if msg_type == "text":
                    result = send_text(user_id, content)
                else:
                    result = send_card(user_id, title, content, color)
            except Exception as exc:
                result = {"error": str(exc), "exception": type(exc).__name__}

            self._json_response(result)
            return

        if self.path == "/update":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}

            message_id = body.get("message_id", "")
            if not message_id:
                self._json_response({"error": "message_id required"}, 400)
                return

            msg_type = body.get("type", "card")
            if msg_type != "card":
                self._json_response({"error": "only card update is supported"}, 400)
                return

            title = body.get("title", "ARIS Notification")
            content = body.get("body", body.get("content", ""))
            color = body.get("color", "blue")

            try:
                result = update_card(message_id, title, content, color)
            except Exception as exc:
                result = {"error": str(exc), "exception": type(exc).__name__}

            self._json_response(result, 200 if result.get("ok") else 400)
            return

        if self.path == "/control/register":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            args = [
                "register",
                "--session-id",
                body.get("session_id", ""),
                "--role",
                body.get("role", ""),
                "--project-root",
                body.get("project_root", PROJECT_ROOT),
            ]
            if body.get("status"):
                args.extend(["--status", body["status"]])
            if body.get("now"):
                args.extend(["--now", body["now"]])
            code, payload = run_control(args)
            self._json_response(payload, 200 if code == 0 else 400)
            return

        if self.path == "/control/message":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            args = ["handle-message", "--text", body.get("text", "")]
            if body.get("now"):
                args.extend(["--now", body["now"]])
            if body.get("lease_ttl_seconds") is not None:
                args.extend(["--lease-ttl-seconds", str(body["lease_ttl_seconds"])])
            code, payload = run_control(args)
            status = 200 if code == 0 else 400
            self._json_response(payload, status)
            return

        if self.path == "/control/local-input":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            args = [
                "local-input",
                "--session-id",
                body.get("session_id", ""),
                "--text",
                body.get("text", ""),
            ]
            if body.get("now"):
                args.extend(["--now", body["now"]])
            code, payload = run_control(args)
            self._json_response(payload, 200 if code == 0 else 423 if code == 2 else 400)
            return

        if self.path == "/control/request-approval":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            args = [
                "request-approval",
                "--session-id",
                body.get("session_id", ""),
                "--action-id",
                body.get("action_id", ""),
                "--description",
                body.get("description", ""),
            ]
            if body.get("code"):
                args.extend(["--code", body["code"]])
            if body.get("now"):
                args.extend(["--now", body["now"]])
            if body.get("ttl_seconds") is not None:
                args.extend(["--ttl-seconds", str(body["ttl_seconds"])])
            code, payload = run_control(args)
            self._json_response(payload, 200 if code == 0 else 400)
            return

        if self.path == "/control/respond":
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            args = [
                "respond",
                "--session-id",
                body.get("session_id", ""),
                "--text",
                body.get("text", ""),
            ]
            if body.get("now"):
                args.extend(["--now", body["now"]])
            code, payload = run_control(args)
            self._json_response(payload, 200 if code == 0 else 400)
            return

        if self.path == "/reply":
            # External hook: when user replies, call this endpoint
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}

            message_id = body.get("message_id", "")
            text = body.get("text", "")

            if message_id:
                receive_reply(message_id, text)
                self._json_response({"ok": True})
            else:
                self._json_response({"error": "message_id required"}, 400)
            return

        self._json_response({"error": "not found"}, 404)

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        # Quiet logging
        pass


def main():
    if ENABLE_WS:
        thread = threading.Thread(target=start_ws_client, name="feishu-ws", daemon=True)
        thread.start()
        print("Feishu WS receiver enabled")

    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    print(f"Feishu Bridge Server running on http://0.0.0.0:{PORT}")
    print(f"  POST /send   — send card/text to Feishu")
    print(f"  POST /update — update card message in Feishu")
    print(f"  GET  /poll   — wait for user reply")
    print(f"  POST /reply  — receive user reply (webhook)")
    print(f"  /control/*   — local Codex session control")
    print(f"  GET  /health — health check")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
