#!/usr/bin/env python3
"""Bridge-owned remote observation state for Labline runtime projections.

This helper stores Feishu/Lark observation metadata outside project runtime.
Project runtime may reference archive/projection ids, but chat ids, open ids,
message text, and delivery failures stay in this bridge-owned state root.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1"
DEFAULT_THROTTLE_SECONDS = 300
DEFAULT_STALE_PROJECTION_SECONDS = 900
DEFAULT_EXPECTED_UPDATE_GRACE_SECONDS = 300
REPO_ROOT = Path(__file__).resolve().parents[1]
LABLINE_RUNTIME = REPO_ROOT / "tools" / "labline_runtime.py"
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
FRESH_REPLY_STATUSES = TERMINAL_STATUSES | {"blocked", "need_decision", "anomaly"}
ACTIVE_STATUSES = {"new", "dispatching", "handoff_verifying", "running", "waiting_on_job", "stale", "anomaly", "need_decision", "recovering"}
STALE_PROJECTION_STATUSES = {"new", "dispatching", "handoff_verifying", "running", "waiting_on_job", "recovering"}
STALE_PROJECTION_REASON = "stale_projection"
CONTROL_PATTERNS = [
    r"\b(stop|cancel|interrupt|kill|delete)\b",
    r"(停掉|停止|取消|中断|杀掉|删除)",
]
STATUS_PATTERNS = [
    r"\b(status|progress|update)\b",
    r"(现在怎么样|怎么样了|状态|进度|到哪了|跑完了吗)",
]
BTW_PATTERNS = [
    r"\b(btw|why|explain|meaning)\b",
    r"(顺便|解释|为什么|为何|什么意思|含义|怎么理解)",
]
NEW_WORK_PATTERNS = [
    r"\b(start|run|create|implement|build)\b",
    r"(新开|开始|实现|做一个|跑一个|启动)",
]
STUCK_DISPLAY_PATTERNS = [
    r"(正在调用工具|正在输出|输出中)",
    r"\b(calling|running)\s+(a\s+)?tool\b",
    r"\btool\s+call(?:ing)?\b",
    r"\bstreaming\s+output\b",
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str | None = None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(microsecond=0)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "item"


def stable_hash(*parts: Any, length: int = 16) -> str:
    text = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def state_root(args: argparse.Namespace) -> Path:
    if args.state_root:
        return Path(args.state_root).expanduser().resolve()
    env = os.environ.get("LABLINE_REMOTE_OBSERVATION_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".labline" / "remote-observation"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def event(root: Path, event_type: str, payload: dict[str, Any]) -> None:
    append_jsonl(
        root / "events" / "remote_observation.jsonl",
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": "evt_" + uuid.uuid4().hex,
            "event_type": event_type,
            "created_at": utc_stamp(),
            "payload": payload,
        },
    )


def archive_ref(profile: str, workspace: str, archive_id: str) -> str:
    return f"bridge://{safe_filename(profile)}/{stable_hash(workspace)}/archive/{archive_id}"


def cmd_archive_message(args: argparse.Namespace) -> int:
    root = state_root(args)
    now = format_utc(parse_utc(args.now))
    archive_id = "arc_" + stable_hash(args.profile, args.workspace, args.message_id or uuid.uuid4().hex)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "archive_id": archive_id,
        "archive_ref": archive_ref(args.profile, args.workspace, archive_id),
        "profile": args.profile,
        "workspace_hash": stable_hash(args.workspace),
        "chat_id": args.chat_id,
        "sender_open_id": args.sender_open_id,
        "message_id": args.message_id,
        "text": args.text,
        "created_at": now,
    }
    atomic_write_json(root / "archive" / f"{archive_id}.json", payload)
    event(root, "remote_message.archived", {"archive_ref": payload["archive_ref"], "archive_id": archive_id})
    return emit({"archive_ref": payload["archive_ref"], "archive_id": archive_id})


def subscription_identity(args: argparse.Namespace) -> tuple[str, str, str, str]:
    project = str(Path(args.project).expanduser().resolve())
    target_type = "task" if getattr(args, "task_id", None) else "project"
    target_id = args.task_id or "project"
    subscription_id = "sub_" + stable_hash(args.profile, args.workspace, args.chat_id, project, target_type, target_id)
    delivery_key = "del_" + stable_hash(args.profile, args.workspace, subscription_id, target_type, target_id)
    projection_id = "proj_" + stable_hash(subscription_id, target_type, target_id)
    return subscription_id, delivery_key, projection_id, project


def subscription_path(root: Path, subscription_id: str) -> Path:
    return root / "subscriptions" / f"{safe_filename(subscription_id)}.json"


def delivery_path(root: Path, delivery_key: str) -> Path:
    return root / "deliveries" / f"{safe_filename(delivery_key)}.json"


def route_path(root: Path, route_id: str) -> Path:
    return root / "routes" / f"{safe_filename(route_id)}.json"


def btw_thread_path(root: Path, thread_id: str) -> Path:
    return root / "btw_threads" / f"{safe_filename(thread_id)}.json"


def cmd_follow(args: argparse.Namespace) -> int:
    root = state_root(args)
    now = format_utc(parse_utc(args.now))
    subscription_id, delivery_key, projection_id, project = subscription_identity(args)
    existing = read_json(subscription_path(root, subscription_id)) if subscription_path(root, subscription_id).exists() else {}
    subscription = {
        "schema_version": SCHEMA_VERSION,
        "subscription_id": subscription_id,
        "status": "active",
        "profile": args.profile,
        "workspace_hash": stable_hash(args.workspace),
        "chat_id": args.chat_id,
        "project_root": project,
        "target_type": "task" if args.task_id else "project",
        "target_id": args.task_id or "project",
        "archive_ref": args.archive_ref,
        "delivery_key": delivery_key,
        "projection_id": projection_id,
        "created_at": existing.get("created_at") or now,
        "updated_at": now,
    }
    atomic_write_json(subscription_path(root, subscription_id), subscription)
    event(root, "remote_observation.followed", {"subscription_id": subscription_id, "archive_ref": args.archive_ref})
    return emit(
        {
            "status": "followed",
            "subscription_id": subscription_id,
            "target_type": subscription["target_type"],
            "target_id": subscription["target_id"],
            "archive_ref": args.archive_ref,
            "delivery_key": delivery_key,
            "projection_id": projection_id,
        }
    )


def cmd_unfollow(args: argparse.Namespace) -> int:
    root = state_root(args)
    now = format_utc(parse_utc(args.now))
    if args.subscription_id:
        subscription_id = args.subscription_id
    else:
        subscription_id, _delivery_key, _projection_id, _project = subscription_identity(args)
    path = subscription_path(root, subscription_id)
    if not path.exists():
        return emit({"status": "missing", "subscription_id": subscription_id})
    subscription = read_json(path)
    subscription["status"] = "inactive"
    subscription["updated_at"] = now
    atomic_write_json(path, subscription)
    event(root, "remote_observation.unfollowed", {"subscription_id": subscription_id})
    return emit({"status": "unfollowed", "subscription_id": subscription_id})


def load_runtime_module():
    spec = importlib.util.spec_from_file_location("labline_runtime", LABLINE_RUNTIME)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runtime helper: {LABLINE_RUNTIME}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime_summary(project: Path) -> dict[str, Any]:
    runtime = load_runtime_module()
    summary, _summary_md = runtime.summarize_runtime(project, write=False)
    return summary


def append_runtime_event(project: Path, event_type: str, payload: dict[str, Any], task_id: str | None = None) -> None:
    runtime = load_runtime_module()
    runtime.append_runtime_event(project, event_type, task_id=task_id, payload=payload, source={"entry": "remote_observation"})


def text_matches(text: str, patterns: list[str]) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns)


def active_tasks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = summary.get("tasks") if isinstance(summary.get("tasks"), list) else []
    return [task for task in tasks if task.get("status") in ACTIVE_STATUSES]


def projection_tasks(summary: dict[str, Any], subscription: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = summary.get("tasks") if isinstance(summary.get("tasks"), list) else []
    if subscription.get("target_type") == "task":
        return [task for task in tasks if task.get("task_id") == subscription.get("target_id")]
    return tasks


def resolve_route_task(args: argparse.Namespace, summary: dict[str, Any]) -> str | None:
    if args.quoted_task_id:
        return args.quoted_task_id
    if args.task_id:
        return args.task_id
    tasks = summary.get("tasks") if isinstance(summary.get("tasks"), list) else []
    text = args.text
    for task in tasks:
        task_id = str(task.get("task_id") or "")
        title = str(task.get("title") or "")
        if task_id and task_id in text:
            return task_id
        if title and title in text:
            return task_id
    running = active_tasks(summary)
    if len(running) == 1:
        return str(running[0].get("task_id") or "")
    return None


def classify_route(text: str, has_active_task: bool) -> tuple[str, str, bool, str, str | None]:
    stripped = text.strip()
    if stripped.startswith("/"):
        command = stripped.split(maxsplit=1)[0]
        if command in {"/status", "/follow", "/unfollow"}:
            return "observation", command.removeprefix("/") or "status_projection", True, "explicit_read_only_command", None
        if command == "/btw":
            return "btw", "answer_read_only", True, "explicit_btw_command", None
        return "explicit_command", command.removeprefix("/") or "command", False, "explicit_command", None
    if text_matches(stripped, CONTROL_PATTERNS):
        return "control_intent", "stop_task", False, "control_keyword", "high"
    if text_matches(stripped, STATUS_PATTERNS):
        return "observation", "status_projection", True, "status_question", None
    if text_matches(stripped, BTW_PATTERNS):
        return "btw", "answer_read_only", True, "side_question", None
    if text_matches(stripped, NEW_WORK_PATTERNS):
        return "normal_project_interaction", "create_or_queue_task", False, "new_work_keyword", "medium"
    if has_active_task:
        return "btw", "answer_read_only", True, "uncertain_active_task_read_only", None
    return "normal_project_interaction", "create_or_queue_task", False, "no_active_task", "medium"


def route_record(args: argparse.Namespace, route_id: str, project: Path, route: str, action: str, read_only: bool, reason: str, task_id: str | None, risk_level: str | None, now: str) -> dict[str, Any]:
    record = {
        "schema_version": SCHEMA_VERSION,
        "route_id": route_id,
        "profile": args.profile,
        "workspace_hash": stable_hash(args.workspace),
        "project_root": str(project),
        "archive_ref": args.archive_ref,
        "route": route,
        "action": action,
        "read_only": read_only,
        "route_reason": reason,
        "task_id": task_id,
        "risk_level": risk_level,
        "text_hash": stable_hash(args.text, length=24),
        "created_at": now,
    }
    if args.chat_id:
        record["chat_id"] = args.chat_id
    if args.sender_open_id:
        record["sender_open_id"] = args.sender_open_id
    return record


def sanitized_route_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "route_id": record["route_id"],
        "archive_ref": record["archive_ref"],
        "route": record["route"],
        "action": record["action"],
        "read_only": record["read_only"],
        "route_reason": record["route_reason"],
        "task_id": record.get("task_id"),
        "risk_level": record.get("risk_level"),
    }


def upsert_btw_thread(root: Path, args: argparse.Namespace, project: Path, task_id: str | None, route_id: str, reason: str, now: str) -> dict[str, Any]:
    thread_id = "btw_" + stable_hash(args.profile, args.workspace, str(project), task_id or "project")
    path = btw_thread_path(root, thread_id)
    thread = read_json(path) if path.exists() else {
        "schema_version": SCHEMA_VERSION,
        "btw_thread_id": thread_id,
        "profile": args.profile,
        "workspace_hash": stable_hash(args.workspace),
        "project_root": str(project),
        "task_id": task_id,
        "scope": "task" if task_id else "project",
        "read_only": True,
        "status": "open",
        "archive_refs": [],
        "answer_refs": [],
        "route_ids": [],
        "created_at": now,
    }
    if args.archive_ref not in thread["archive_refs"]:
        thread["archive_refs"].append(args.archive_ref)
    if route_id not in thread["route_ids"]:
        thread["route_ids"].append(route_id)
    thread["last_route_reason"] = reason
    thread["updated_at"] = now
    atomic_write_json(path, thread)
    return thread


def submit_control_intent(project: Path, args: argparse.Namespace, route_id: str, task_id: str | None, action: str, risk_level: str, now: str) -> dict[str, Any]:
    intent = {
        "schema_version": SCHEMA_VERSION,
        "intent_id": "intent_" + stable_hash(route_id, args.archive_ref),
        "source": {"entry": "feishu", "archive_ref": args.archive_ref},
        "action": action,
        "risk_level": risk_level,
        "confirmation_status": "required" if risk_level == "high" else "not_required",
        "target": {"task_id": task_id} if task_id else {"project": str(project)},
        "lease_scope": f"task:{task_id}" if task_id else "leader_session",
        "status": "pending",
        "created_at": now,
        "route_id": route_id,
    }
    append_runtime_event(project, "control_intent.submitted", intent, task_id=task_id)
    return intent


def cmd_route_message(args: argparse.Namespace) -> int:
    root = state_root(args)
    project = Path(args.project).expanduser().resolve()
    now = format_utc(parse_utc(args.now))
    summary = runtime_summary(project)
    task_id = resolve_route_task(args, summary)
    route, action, read_only, reason, risk_level = classify_route(args.text, has_active_task=bool(active_tasks(summary)))
    route_id = "route_" + stable_hash(args.profile, args.workspace, args.archive_ref)
    record = route_record(args, route_id, project, route, action, read_only, reason, task_id, risk_level, now)
    atomic_write_json(route_path(root, route_id), record)
    sanitized = sanitized_route_payload(record)
    append_runtime_event(project, "remote_message.routed", sanitized, task_id=task_id)
    event(root, "remote_message.routed", {"route_id": route_id, "archive_ref": args.archive_ref, "route": route})

    output = {
        "status": "routed",
        "route_id": route_id,
        "route": route,
        "action": action,
        "read_only": read_only,
        "route_reason": reason,
        "task_id": task_id,
        "inject_tui": False,
    }
    if risk_level:
        output["risk_level"] = risk_level
    if route == "btw":
        thread = upsert_btw_thread(root, args, project, task_id, route_id, reason, now)
        payload = {**sanitized, "btw_thread_id": thread["btw_thread_id"], "scope": thread["scope"]}
        append_runtime_event(project, "btw.question_received", payload, task_id=task_id)
        output["btw_thread_id"] = thread["btw_thread_id"]
    elif route == "control_intent":
        intent = submit_control_intent(project, args, route_id, task_id, action, risk_level or "medium", now)
        output["intent_id"] = intent["intent_id"]
        output["lease_scope"] = intent["lease_scope"]
    return emit(output)


def cmd_btw_answer(args: argparse.Namespace) -> int:
    root = state_root(args)
    project = Path(args.project).expanduser().resolve()
    now = format_utc(parse_utc(args.now))
    path = btw_thread_path(root, args.btw_thread_id)
    if not path.exists():
        print(f"btw thread not found: {args.btw_thread_id}", file=sys.stderr)
        return 1
    thread = read_json(path)
    if args.archive_ref not in thread.setdefault("archive_refs", []):
        thread["archive_refs"].append(args.archive_ref)
    if args.answer_ref not in thread.setdefault("answer_refs", []):
        thread["answer_refs"].append(args.answer_ref)
    thread["last_answer_hash"] = stable_hash(args.text, length=24)
    thread["updated_at"] = now
    atomic_write_json(path, thread)
    payload = {
        "btw_thread_id": args.btw_thread_id,
        "archive_ref": args.archive_ref,
        "answer_ref": args.answer_ref,
        "task_id": thread.get("task_id"),
        "read_only": True,
    }
    append_runtime_event(project, "btw.answered", payload, task_id=thread.get("task_id"))
    event(root, "btw.answered", {"btw_thread_id": args.btw_thread_id, "archive_ref": args.archive_ref, "answer_ref": args.answer_ref})
    return emit({"status": "answered", "btw_thread_id": args.btw_thread_id, "answer_ref": args.answer_ref})


def state_signature(summary: dict[str, Any], subscription: dict[str, Any]) -> str:
    target_type = subscription.get("target_type")
    target_id = subscription.get("target_id")
    tasks = projection_tasks(summary, subscription)
    compact = {
        "counts": summary.get("counts"),
        "target_type": target_type,
        "target_id": target_id,
        "tasks": [
            {
                "task_id": task.get("task_id"),
                "status": task.get("status"),
                "updated_at": task.get("updated_at"),
                "current_action": task.get("current_action"),
                "blocker": task.get("blocker"),
                "artifacts": task.get("artifacts"),
            }
            for task in tasks
        ],
    }
    return stable_hash(json.dumps(compact, ensure_ascii=False, sort_keys=True), length=24)


def has_escalation(project: Path) -> bool:
    return any((project / ".labline" / "runtime" / "escalations").glob("*.json"))


def parse_utc_or_none(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return parse_utc(str(value))
    except ValueError:
        return None


def task_matches_stuck_display(task: dict[str, Any]) -> bool:
    current_action = str(task.get("current_action") or "")
    return text_matches(current_action, STUCK_DISPLAY_PATTERNS)


def stale_projection_deadline(task: dict[str, Any]) -> tuple[datetime, str] | None:
    expected = parse_utc_or_none(task.get("next_expected_update"))
    if expected:
        return expected + timedelta(seconds=DEFAULT_EXPECTED_UPDATE_GRACE_SECONDS), "next_expected_update"
    if not task_matches_stuck_display(task):
        return None
    updated = parse_utc_or_none(task.get("updated_at"))
    if not updated:
        return None
    return updated + timedelta(seconds=DEFAULT_STALE_PROJECTION_SECONDS), "updated_at"


def stale_projection_hint(
    summary: dict[str, Any],
    subscription: dict[str, Any],
    previous: dict[str, Any],
    signature: str,
    now: datetime,
) -> dict[str, Any] | None:
    if previous.get("state_signature") != signature or previous.get("status") != "delivered":
        return None
    for task in projection_tasks(summary, subscription):
        status = str(task.get("status") or "")
        if status not in STALE_PROJECTION_STATUSES:
            continue
        deadline = stale_projection_deadline(task)
        if not deadline:
            continue
        stale_after, source = deadline
        if now < stale_after:
            continue
        return {
            "kind": STALE_PROJECTION_REASON,
            "task_id": task.get("task_id"),
            "status": status,
            "current_action": task.get("current_action"),
            "stale_after": format_utc(stale_after),
            "source": source,
            "message": "飞书卡片可能停在旧阶段；本地 runtime 还没有看到新的状态变化。任务可能仍在运行，后续以 runtime 终态或 /status 为准。",
        }
    return None


def urgent_reason(summary: dict[str, Any], subscription: dict[str, Any], project: Path) -> str | None:
    if has_escalation(project):
        return "escalation"
    for task in projection_tasks(summary, subscription):
        status = task.get("status")
        if status in TERMINAL_STATUSES:
            return "terminal"
        if status in FRESH_REPLY_STATUSES:
            return str(status)
    return None


def projection_plan_payload(
    root: Path,
    subscription: dict[str, Any],
    project: Path,
    *,
    explicit_status: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    runtime = load_runtime_module()
    summary, _summary_md = runtime.summarize_runtime(project, write=False)
    signature = state_signature(summary, subscription)
    delivery_key = subscription["delivery_key"]
    projection_id = subscription["projection_id"]
    previous = read_json(delivery_path(root, delivery_key)) if delivery_path(root, delivery_key).exists() else {}
    now = now or parse_utc()
    reason = urgent_reason(summary, subscription, project)
    attention_hint: dict[str, Any] | None = None
    action = "fresh_reply" if reason else "patch"
    if explicit_status:
        action = "patch"
        reason = "explicit_status"
    elif reason and previous.get("state_signature") == signature:
        if previous.get("status") == "delivered":
            action = "skip"
            reason = "already_delivered"
        else:
            next_allowed = parse_utc(previous.get("next_allowed_at")) if previous.get("next_allowed_at") else None
            if next_allowed and now < next_allowed:
                action = "skip"
                reason = "delivery_retry_throttled"
    elif not reason:
        attention_hint = stale_projection_hint(summary, subscription, previous, signature, now)
        if attention_hint:
            action = "fresh_reply"
            reason = STALE_PROJECTION_REASON
            if previous.get("state_signature") == signature and previous.get("reason") == STALE_PROJECTION_REASON:
                if previous.get("status") == "delivered":
                    action = "skip"
                    reason = "already_delivered"
                else:
                    next_allowed = parse_utc(previous.get("next_allowed_at")) if previous.get("next_allowed_at") else None
                    if next_allowed and now < next_allowed:
                        action = "skip"
                        reason = "delivery_retry_throttled"
        elif previous.get("state_signature") == signature:
            next_allowed = parse_utc(previous.get("next_allowed_at")) if previous.get("next_allowed_at") else None
            if next_allowed and now < next_allowed:
                action = "skip"
                reason = "throttled_no_significant_change"
            else:
                action = "skip"
                reason = "no_significant_change"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "action": action,
        "reason": reason or "progress",
        "subscription_id": subscription["subscription_id"],
        "delivery_key": delivery_key,
        "projection_id": projection_id,
        "state_signature": signature,
    }
    if previous.get("message_id"):
        payload["previous_message_id"] = previous["message_id"]
    if previous.get("delivery_mode"):
        payload["previous_delivery_mode"] = previous["delivery_mode"]
    if attention_hint:
        payload["attention_hint"] = attention_hint
    return payload


def cmd_projection_plan(args: argparse.Namespace) -> int:
    root = state_root(args)
    subscription = read_json(subscription_path(root, args.subscription_id))
    project = Path(args.project).expanduser().resolve()
    payload = projection_plan_payload(
        root,
        subscription,
        project,
        explicit_status=args.explicit_status,
        now=parse_utc(args.now),
    )
    return emit(payload)


def iter_active_subscriptions(root: Path, profile: str | None = None) -> list[dict[str, Any]]:
    subscriptions: list[dict[str, Any]] = []
    for path in sorted((root / "subscriptions").glob("*.json")):
        try:
            subscription = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if subscription.get("status") != "active":
            continue
        if profile and subscription.get("profile") != profile:
            continue
        subscriptions.append(subscription)
    return subscriptions


def cmd_projection_poll(args: argparse.Namespace) -> int:
    root = state_root(args)
    now = parse_utc(args.now)
    project_filter = Path(args.project).expanduser().resolve() if args.project else None
    plans: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    profile_filter = None if args.include_cross_profile else args.profile
    for subscription in iter_active_subscriptions(root, profile_filter):
        project = Path(str(subscription.get("project_root") or "")).expanduser().resolve()
        if project_filter and project != project_filter:
            continue
        if not project.exists():
            errors.append(
                {
                    "subscription_id": str(subscription.get("subscription_id") or ""),
                    "error": f"project not found: {project}",
                }
            )
            continue
        try:
            plan = projection_plan_payload(root, subscription, project, now=now)
        except Exception as exc:  # Polling must keep other subscriptions observable.
            errors.append(
                {
                    "subscription_id": str(subscription.get("subscription_id") or ""),
                    "error": str(exc),
                }
            )
            continue
        if plan["action"] == "skip":
            continue
        plans.append(
            {
                **plan,
                "project_root": str(project),
                "chat_id": subscription.get("chat_id"),
                "target_type": subscription.get("target_type"),
                "target_id": subscription.get("target_id"),
            }
        )
        if len(plans) >= args.limit:
            break
    return emit(
        {
            "schema_version": SCHEMA_VERSION,
            "status": "ok",
            "profile": args.profile,
            "include_cross_profile": bool(args.include_cross_profile),
            "plans": plans,
            "errors": errors,
        }
    )


def cmd_delivery_targets(args: argparse.Namespace) -> int:
    root = state_root(args)
    project_filter = Path(args.project).expanduser().resolve() if args.project else None
    task_id = args.task_id
    targets: list[dict[str, Any]] = []
    seen_chats: set[str] = set()
    profile_filter = None if args.include_cross_profile else args.profile
    for subscription in iter_active_subscriptions(root, profile_filter):
        project = Path(str(subscription.get("project_root") or "")).expanduser().resolve()
        if project_filter and project != project_filter:
            continue
        target_type = str(subscription.get("target_type") or "")
        target_id = str(subscription.get("target_id") or "")
        if task_id and target_type == "task" and target_id != task_id:
            continue
        chat_id = str(subscription.get("chat_id") or "")
        if not chat_id or chat_id in seen_chats:
            continue
        seen_chats.add(chat_id)
        targets.append(
            {
                "chat_id": chat_id,
                "subscription_id": str(subscription.get("subscription_id") or ""),
                "profile": str(subscription.get("profile") or ""),
                "target_type": target_type,
                "target_id": target_id,
                "project_root": str(project),
            }
        )
        if len(targets) >= args.limit:
            break
    return emit(
        {
            "schema_version": SCHEMA_VERSION,
            "status": "ok",
            "profile": args.profile,
            "include_cross_profile": bool(args.include_cross_profile),
            "project_root": str(project_filter) if project_filter else None,
            "task_id": task_id,
            "targets": targets,
        }
    )


def cmd_delivery_record(args: argparse.Namespace) -> int:
    root = state_root(args)
    now = parse_utc(args.now)
    next_allowed = now + timedelta(seconds=args.throttle_seconds)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "delivery_key": args.delivery_key,
        "subscription_id": args.subscription_id,
        "projection_id": args.projection_id,
        "status": args.status,
        "state_signature": args.state_signature,
        "updated_at": format_utc(now),
        "next_allowed_at": format_utc(next_allowed),
    }
    if args.error:
        payload["error"] = args.error
    if args.reason:
        payload["reason"] = args.reason
    if args.message_id:
        payload["message_id"] = args.message_id
    if args.delivery_mode:
        payload["delivery_mode"] = args.delivery_mode
    atomic_write_json(delivery_path(root, args.delivery_key), payload)
    event(
        root,
        "projection.delivery_recorded",
        {
            "delivery_key": args.delivery_key,
            "subscription_id": args.subscription_id,
            "projection_id": args.projection_id,
            "status": args.status,
        },
    )
    return emit({key: payload[key] for key in ["delivery_key", "subscription_id", "projection_id", "status", "next_allowed_at"]})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labline_remote_observation")
    parser.add_argument("--state-root", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)

    archive = sub.add_parser("archive-message")
    archive.add_argument("--profile", required=True)
    archive.add_argument("--workspace", required=True)
    archive.add_argument("--chat-id", required=True)
    archive.add_argument("--sender-open-id", required=True)
    archive.add_argument("--message-id", required=True)
    archive.add_argument("--text", required=True)
    archive.add_argument("--now")
    archive.set_defaults(func=cmd_archive_message)

    follow = sub.add_parser("follow")
    follow.add_argument("--profile", required=True)
    follow.add_argument("--workspace", required=True)
    follow.add_argument("--project", required=True)
    follow.add_argument("--chat-id", required=True)
    follow.add_argument("--archive-ref", required=True)
    follow.add_argument("--task-id")
    follow.add_argument("--now")
    follow.set_defaults(func=cmd_follow)

    unfollow = sub.add_parser("unfollow")
    unfollow.add_argument("--subscription-id")
    unfollow.add_argument("--profile")
    unfollow.add_argument("--workspace")
    unfollow.add_argument("--project")
    unfollow.add_argument("--chat-id")
    unfollow.add_argument("--task-id")
    unfollow.add_argument("--now")
    unfollow.set_defaults(func=cmd_unfollow)

    plan = sub.add_parser("projection-plan")
    plan.add_argument("--project", required=True)
    plan.add_argument("--subscription-id", required=True)
    plan.add_argument("--explicit-status", action="store_true")
    plan.add_argument("--now")
    plan.set_defaults(func=cmd_projection_plan)

    poll = sub.add_parser("projection-poll")
    poll.add_argument("--profile", required=True)
    poll.add_argument("--project")
    poll.add_argument("--limit", type=int, default=20)
    poll.add_argument("--include-cross-profile", action="store_true")
    poll.add_argument("--now")
    poll.set_defaults(func=cmd_projection_poll)

    targets = sub.add_parser("delivery-targets")
    targets.add_argument("--profile", required=True)
    targets.add_argument("--project")
    targets.add_argument("--task-id")
    targets.add_argument("--limit", type=int, default=20)
    targets.add_argument("--include-cross-profile", action="store_true")
    targets.set_defaults(func=cmd_delivery_targets)

    delivery = sub.add_parser("delivery-record")
    delivery.add_argument("--delivery-key", required=True)
    delivery.add_argument("--subscription-id", required=True)
    delivery.add_argument("--projection-id", required=True)
    delivery.add_argument("--status", required=True, choices=["pending", "delivered", "failed", "skipped"])
    delivery.add_argument("--state-signature", required=True)
    delivery.add_argument("--reason")
    delivery.add_argument("--error")
    delivery.add_argument("--message-id")
    delivery.add_argument("--delivery-mode")
    delivery.add_argument("--throttle-seconds", type=int, default=DEFAULT_THROTTLE_SECONDS)
    delivery.add_argument("--now")
    delivery.set_defaults(func=cmd_delivery_record)

    route = sub.add_parser("route-message")
    route.add_argument("--project", required=True)
    route.add_argument("--profile", required=True)
    route.add_argument("--workspace", required=True)
    route.add_argument("--archive-ref", required=True)
    route.add_argument("--text", required=True)
    route.add_argument("--task-id")
    route.add_argument("--quoted-task-id")
    route.add_argument("--chat-id")
    route.add_argument("--sender-open-id")
    route.add_argument("--now")
    route.set_defaults(func=cmd_route_message)

    btw_answer = sub.add_parser("btw-answer")
    btw_answer.add_argument("--project", required=True)
    btw_answer.add_argument("--btw-thread-id", required=True)
    btw_answer.add_argument("--archive-ref", required=True)
    btw_answer.add_argument("--answer-ref", required=True)
    btw_answer.add_argument("--text", required=True)
    btw_answer.add_argument("--now")
    btw_answer.set_defaults(func=cmd_btw_answer)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
