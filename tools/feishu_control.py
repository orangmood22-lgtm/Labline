#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import secrets
import string
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCHEMA_VERSION = 1
DEFAULT_LEASE_TTL_SECONDS = 1800


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_iso(value: str | None) -> datetime:
    if not value:
        return utc_now()
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def state_root(args: argparse.Namespace) -> Path:
    if args.state_root:
        return Path(args.state_root)
    project_root = Path(args.project_root or ".")
    return project_root / ".aris" / "feishu-control"


def state_file(root: Path) -> Path:
    return root / "sessions.json"


def approval_file(root: Path, code: str) -> Path:
    return root / "approvals" / f"{code}.json"


def inbox_file(root: Path, session_id: str) -> Path:
    return root / "inbox" / f"{session_id}.jsonl"


def outbox_file(root: Path, session_id: str) -> Path:
    return root / "outbox" / f"{session_id}.jsonl"


def empty_state() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "active_session_id": None,
        "sessions": {},
        "leases": {},
    }


def read_state(root: Path) -> dict:
    path = state_file(root)
    if not path.exists():
        return empty_state()
    for attempt in range(3):
        text = path.read_text(encoding="utf-8")
        if text.strip():
            return json.loads(text)
        if attempt < 2:
            time.sleep(0.05)
    return empty_state()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_state(root: Path, data: dict) -> None:
    write_json(state_file(root), data)


def emit(data: dict, exit_code: int = 0) -> int:
    print(json.dumps(data, ensure_ascii=False, sort_keys=True))
    return exit_code


def append_jsonl(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")


def ensure_session(state: dict, session_id: str) -> dict:
    session = state.get("sessions", {}).get(session_id)
    if not session:
        raise SystemExit(f"unknown session_id: {session_id}")
    return session


def current_lease(state: dict, session_id: str, now: datetime) -> dict:
    lease = state.setdefault("leases", {}).get(session_id) or {"owner": "local", "expires_at": None}
    expires_at = lease.get("expires_at")
    if lease.get("owner") == "feishu" and expires_at and parse_iso(expires_at) <= now:
        lease = {"owner": "local", "expires_at": None}
        state["leases"][session_id] = lease
    return lease


def set_lease(state: dict, session_id: str, owner: str, now: datetime, ttl_seconds: int | None = None) -> None:
    expires_at = None
    if owner == "feishu":
        expires_at = isoformat(now + timedelta(seconds=ttl_seconds or DEFAULT_LEASE_TTL_SECONDS))
    state.setdefault("leases", {})[session_id] = {"owner": owner, "expires_at": expires_at}


def route_target(state: dict, text: str) -> tuple[str | None, str]:
    if text.startswith("@"):
        first, sep, rest = text.partition(" ")
        if sep:
            return first[1:], rest
    return state.get("active_session_id"), text


def remember_sender(state: dict, session_id: str, sender_open_id: str | None) -> None:
    if not sender_open_id:
        return
    session = ensure_session(state, session_id)
    session["last_sender_open_id"] = sender_open_id


def queue_message(root: Path, state: dict, session_id: str, text: str, source: str, now: datetime, sender_open_id: str | None = None) -> None:
    ensure_session(state, session_id)
    payload = {
        "received_at": isoformat(now),
        "session_id": session_id,
        "source": source,
        "text": text,
    }
    if sender_open_id:
        payload["sender_open_id"] = sender_open_id
    append_jsonl(inbox_file(root, session_id), payload)


def queue_response(root: Path, state: dict, session_id: str, text: str, now: datetime) -> None:
    ensure_session(state, session_id)
    append_jsonl(
        outbox_file(root, session_id),
        {
            "created_at": isoformat(now),
            "delivery_status": "pending",
            "session_id": session_id,
            "source": "codex_session",
            "text": text,
        },
    )


def unsupported_command(text: str) -> bool:
    return text.startswith("/run ") or text.startswith("/tool ")


def make_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def handle_command(root: Path, state: dict, text: str, now: datetime) -> tuple[dict, int]:
    parts = text.split()
    command = parts[0] if parts else ""

    if command == "/sessions":
        return {"status": "ok", "active_session_id": state.get("active_session_id"), "sessions": state.get("sessions", {})}, 0

    if command == "/use" and len(parts) == 2:
        ensure_session(state, parts[1])
        state["active_session_id"] = parts[1]
        return {"status": "active_session_changed", "active_session_id": parts[1]}, 0

    if command == "/release":
        session_id = state.get("active_session_id")
        if not session_id:
            return {"status": "no_active_session"}, 3
        set_lease(state, session_id, "local", now)
        return {"status": "released", "session_id": session_id}, 0

    if command in {"/approve", "/reject"} and len(parts) == 2:
        data, code = resolve_approval(root, parts[1], now)
        if data.get("status") != "pending":
            return {"status": "approval_already_resolved", "code": code}, 3
        if parse_iso(data["expires_at"]) <= now:
            data["status"] = "expired"
            data["resolved_at"] = isoformat(now)
            write_json(approval_file(root, code), data)
            return {"status": "approval_expired", "code": code}, 3
        data["status"] = "approved" if command == "/approve" else "rejected"
        data["resolved_at"] = isoformat(now)
        write_json(approval_file(root, code), data)
        return {"status": data["status"], "code": code, "action_id": data["action_id"]}, 0

    if command == "/status":
        return {"status": "ok", "active_session_id": state.get("active_session_id"), "lease": state.get("leases", {})}, 0

    if command == "/resume" and len(parts) >= 2:
        # The actual Codex launch belongs to aris-feishu-session. This command records intent only.
        session_id = state.get("active_session_id")
        if session_id:
            queue_message(root, state, session_id, text, "feishu", now)
        return {"status": "resume_requested", "target": parts[1]}, 0

    if command == "/interrupt":
        session_id = state.get("active_session_id")
        if not session_id:
            return {"status": "no_active_session"}, 3
        queue_message(root, state, session_id, text, "feishu", now)
        return {"status": "queued", "session_id": session_id, "control": "interrupt"}, 0

    if command == "/btw" and len(parts) >= 2:
        session_id = state.get("active_session_id")
        if not session_id:
            return {"status": "no_active_session"}, 3
        queue_message(root, state, session_id, text, "feishu", now)
        return {"status": "queued", "session_id": session_id, "control": "btw"}, 0

    return {"status": "unsupported_command", "command": command}, 4


def resolve_approval(root: Path, code: str, now: datetime) -> tuple[dict, str]:
    path = approval_file(root, code)
    if not path.exists():
        raise ApprovalError({"status": "unknown_approval_code", "code": code})
    return json.loads(path.read_text(encoding="utf-8")), code


class ApprovalError(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("status", "approval_error"))


def cmd_register(args: argparse.Namespace) -> int:
    root = state_root(args)
    state = read_state(root)
    now = parse_iso(args.now)
    session = {
        "session_id": args.session_id,
        "role": args.role,
        "project_root": args.session_project_root,
        "status": args.status,
        "registered_at": isoformat(now),
        "last_seen": isoformat(now),
        "inbox_path": str(inbox_file(root, args.session_id)),
        "outbox_path": str(outbox_file(root, args.session_id)),
    }
    state.setdefault("sessions", {})[args.session_id] = session
    state.setdefault("leases", {}).setdefault(args.session_id, {"owner": "local", "expires_at": None})
    if not state.get("active_session_id"):
        state["active_session_id"] = args.session_id
    write_state(root, state)
    return emit({"status": "registered", "session": session})


def cmd_sessions(args: argparse.Namespace) -> int:
    root = state_root(args)
    state = read_state(root)
    if args.json:
        return emit({"active_session_id": state.get("active_session_id"), "sessions": state.get("sessions", {})})
    for session_id, session in sorted(state.get("sessions", {}).items()):
        marker = "*" if session_id == state.get("active_session_id") else "-"
        print(f"{marker} {session_id} {session.get('role')} {session.get('status')} {session.get('project_root')}")
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    root = state_root(args)
    state = read_state(root)
    ensure_session(state, args.session_id)
    state["active_session_id"] = args.session_id
    write_state(root, state)
    return emit({"status": "active_session_changed", "active_session_id": args.session_id})


def cmd_handle_message(args: argparse.Namespace) -> int:
    root = state_root(args)
    state = read_state(root)
    now = parse_iso(args.now)
    text = args.text.strip()

    if unsupported_command(text):
        return emit({"status": "unsupported_command"}, 4)

    if text.startswith("/"):
        session_id = state.get("active_session_id")
        if session_id:
            remember_sender(state, session_id, args.sender_open_id)
        try:
            payload, code = handle_command(root, state, text, now)
        except ApprovalError as exc:
            return emit(exc.payload, 3)
        write_state(root, state)
        return emit(payload, code)

    session_id, routed_text = route_target(state, text)
    if not session_id:
        return emit({"status": "no_active_session"}, 3)
    ensure_session(state, session_id)
    remember_sender(state, session_id, args.sender_open_id)
    set_lease(state, session_id, "feishu", now, args.lease_ttl_seconds)
    queue_message(root, state, session_id, routed_text, "feishu", now, args.sender_open_id)
    write_state(root, state)
    return emit({"status": "queued", "session_id": session_id, "lease_owner": "feishu"})


def cmd_local_input(args: argparse.Namespace) -> int:
    root = state_root(args)
    state = read_state(root)
    now = parse_iso(args.now)
    ensure_session(state, args.session_id)
    lease = current_lease(state, args.session_id, now)
    if lease.get("owner") == "feishu":
        write_state(root, state)
        return emit({"status": "blocked_by_feishu", "session_id": args.session_id, "lease": lease}, 2)
    set_lease(state, args.session_id, "local", now)
    queue_message(root, state, args.session_id, args.text, "local", now)
    write_state(root, state)
    return emit({"status": "queued", "session_id": args.session_id, "lease_owner": "local"})


def cmd_request_approval(args: argparse.Namespace) -> int:
    root = state_root(args)
    state = read_state(root)
    ensure_session(state, args.session_id)
    now = parse_iso(args.now)
    code = args.code or make_code()
    approval = {
        "schema_version": SCHEMA_VERSION,
        "code": code,
        "session_id": args.session_id,
        "action_id": args.action_id,
        "description": args.description,
        "status": "pending",
        "requested_at": isoformat(now),
        "expires_at": isoformat(now + timedelta(seconds=args.ttl_seconds)),
        "resolved_at": None,
    }
    write_json(approval_file(root, code), approval)
    return emit({"status": "approval_requested", "code": code, "expires_at": approval["expires_at"]})


def cmd_respond(args: argparse.Namespace) -> int:
    root = state_root(args)
    state = read_state(root)
    now = parse_iso(args.now)
    queue_response(root, state, args.session_id, args.text, now)
    return emit({"status": "queued", "session_id": args.session_id})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage ARIS Feishu-controlled Codex sessions.")
    parser.add_argument("--state-root")
    parser.add_argument("--project-root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register")
    register.add_argument("--session-id", required=True)
    register.add_argument("--role", required=True)
    register.add_argument("--project-root", dest="session_project_root", required=True)
    register.add_argument("--status", default="running")
    register.add_argument("--now")
    register.set_defaults(func=cmd_register)

    sessions = subparsers.add_parser("sessions")
    sessions.add_argument("--json", action="store_true")
    sessions.set_defaults(func=cmd_sessions)

    use = subparsers.add_parser("use")
    use.add_argument("--session-id", required=True)
    use.set_defaults(func=cmd_use)

    handle = subparsers.add_parser("handle-message")
    handle.add_argument("--text", required=True)
    handle.add_argument("--sender-open-id", default="")
    handle.add_argument("--now")
    handle.add_argument("--lease-ttl-seconds", type=int, default=DEFAULT_LEASE_TTL_SECONDS)
    handle.set_defaults(func=cmd_handle_message)

    local = subparsers.add_parser("local-input")
    local.add_argument("--session-id", required=True)
    local.add_argument("--text", required=True)
    local.add_argument("--now")
    local.set_defaults(func=cmd_local_input)

    approval = subparsers.add_parser("request-approval")
    approval.add_argument("--session-id", required=True)
    approval.add_argument("--action-id", required=True)
    approval.add_argument("--description", required=True)
    approval.add_argument("--code")
    approval.add_argument("--now")
    approval.add_argument("--ttl-seconds", type=int, default=300)
    approval.set_defaults(func=cmd_request_approval)

    respond = subparsers.add_parser("respond")
    respond.add_argument("--session-id", required=True)
    respond.add_argument("--text", required=True)
    respond.add_argument("--now")
    respond.set_defaults(func=cmd_respond)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
