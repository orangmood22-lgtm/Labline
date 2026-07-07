#!/usr/bin/env python3
"""Labline project runtime state helpers.

This module implements the project-local runtime protocol slices that are
stable enough for CLI use: runtime root initialization, append-only events,
task lifecycle records, and derived status summaries. It deliberately does not
own Feishu state, heartbeat scheduling, or component-specific status.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


STATE_DIR_NAME = ".labline"
RUNTIME_DIR_NAME = "runtime"
RUNTIME_SCHEMA_VERSION = "0.1"
RUNTIME_DIRS = [
    "agents",
    "jobs",
    "queues",
    "watchdog",
    "pipelines",
    "tasks",
    "events",
    "leases",
    "heartbeats",
    "escalations",
    "wakeups",
    "transports",
    "summaries",
]
AGENT_RUNNING_STATUSES = {"starting", "running", "waiting_on_job"}
AGENT_STATUS_MAP = {
    "starting": "running",
    "running": "running",
    "in_progress": "running",
    "waiting_on_job": "running",
    "blocked": "blocked",
    "done": "completed",
    "complete": "completed",
    "failed": "failed",
}
DEFAULT_AGENT_NO_DEADLINE_STALE_AFTER_SECONDS = 900
SUMMARY_COUNT_KEYS = ["running", "stale", "blocked", "need_decision", "ready_to_continue", "anomaly", "recently_completed", "failed"]
EXECUTION_MODES = {"inline", "agent_turn", "detached_job"}
DURABILITY_VALUES = {"ephemeral", "resumable", "supervised"}
OBSERVATION_VALUES = {"disabled", "enabled"}
HEARTBEAT_VALUES = {"none", "passive", "escalation_gated"}
TASK_STATUSES = {
    "new",
    "dispatching",
    "handoff_verifying",
    "running",
    "waiting_on_job",
    "stale",
    "blocked",
    "anomaly",
    "need_decision",
    "ready_to_continue",
    "recovering",
    "superseded",
    "resolved",
    "completed",
    "failed",
    "cancelled",
}
TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled", "superseded", "resolved"}
WAKEUP_TERMINAL_TASK_STATUSES = {"failed", "cancelled"}
TASK_RESOLUTION_EVENT_TYPES = {"task.superseded", "task.resolved", "task.resolved_by"}
TASK_TERMINAL_DECISION_EVENT_TYPES = {"leader.decision"}
RISK_LEVELS = {"low", "medium", "high"}
CONFIRMATION_STATUSES = {"not_required", "required", "confirmed", "rejected"}
HEARTBEAT_ENABLED_VALUES = {"passive", "escalation_gated"}
HEARTBEAT_ESCALATION_STATUSES = {"stale", "blocked", "anomaly", "need_decision"}
DELEGATED_AGENT_KINDS = {"agent", "child_agent", "delegated_agent"}
SUCCESS_TERMINAL_TASK_STATUSES = {"completed", "resolved"}
WAKEUP_BACKENDS = {"prompt-only", "native-codex"}
PHASE_BOUNDARY_READY_ESCALATION = "phase_boundary_ready"
PHASE_BOUNDARY_CONTEXT_KEYS = [
    "phase_boundary",
    "phase_boundary_evidence",
    "phase_boundary_readiness_evidence",
    "readiness_evidence",
    "prerequisite_task_ids",
    "prerequisite_tasks",
    "required_artifacts",
    "required_gate_verdicts",
    "required_reviewer_verdicts",
    "next_leader_question",
    "next_leader_prompt",
]
PHASE_BOUNDARY_SUCCESS_STATUSES = {"completed", "resolved"}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str | None = None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_utc_or_none(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        return parse_utc(str(value))
    except (TypeError, ValueError):
        return None


def resolve_project(path: Path | None = None) -> Path:
    return (path or Path.cwd()).expanduser().resolve()


def runtime_root(project: Path | None = None) -> Path:
    return resolve_project(project) / STATE_DIR_NAME / RUNTIME_DIR_NAME


def init_runtime_root(project: Path | None = None) -> Path:
    root = runtime_root(project)
    for rel in RUNTIME_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    return root


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def parse_event_payload(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON payload: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("invalid JSON payload: expected object")
    return parsed


def build_event(event_type: str, task_id: str | None = None, payload: dict[str, Any] | None = None, source: dict[str, Any] | None = None) -> dict[str, Any]:
    event: dict[str, Any] = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "event_id": "evt_" + uuid.uuid4().hex,
        "event_type": event_type,
        "created_at": utc_stamp(),
        "source": source or {"entry": "lane"},
        "payload": payload or {},
    }
    if task_id:
        event["task_id"] = task_id
    return event


def append_runtime_event(project: Path | None, event_type: str, task_id: str | None = None, payload: dict[str, Any] | None = None, source: dict[str, Any] | None = None) -> Path:
    root = init_runtime_root(project)
    path = root / "events" / "runtime.jsonl"
    append_jsonl(path, build_event(event_type, task_id=task_id, payload=payload, source=source))
    return path


def runtime_task_path(root: Path, task_id: str) -> Path:
    return root / "tasks" / f"{safe_filename(task_id)}.json"


def runtime_lease_path(root: Path, lease_id: str) -> Path:
    return root / "leases" / f"{safe_filename(lease_id)}.json"


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "task"


def rel_ref(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path)


def read_json_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def iter_json_objects(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    if not root.exists():
        return []
    items = []
    for path in sorted(root.glob("*.json")):
        items.append((path, read_json_file(path)))
    return items


def due_at_passed(value: Any, now: datetime | None) -> bool:
    if not now or not value:
        return False
    try:
        return parse_utc(str(value)) <= now
    except ValueError:
        return True


def agent_no_deadline_stale(snapshot: dict[str, Any], status: str, job_handles: list[Any], now: datetime | None) -> bool:
    if not now or status not in AGENT_RUNNING_STATUSES:
        return False
    if job_handles or snapshot.get("next_expected_update"):
        return False
    updated = parse_utc_or_none(snapshot.get("last_updated") or snapshot.get("updated_at") or snapshot.get("started_at"))
    if not updated:
        return False
    stale_after = timedelta(seconds=DEFAULT_AGENT_NO_DEADLINE_STALE_AFTER_SECONDS)
    return updated + stale_after <= now


def agent_executor_lost(snapshot: dict[str, Any], job_handles: list[Any], now: datetime | None) -> bool:
    if str(snapshot.get("status") or "") != "starting":
        return False
    if job_handles:
        return False
    return due_at_passed(snapshot.get("next_expected_update"), now)


def agent_snapshot_to_task(project: Path, path: Path, snapshot: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    agent_id = str(snapshot.get("agent_id") or path.stem)
    agent_status = str(snapshot.get("status") or "running")
    job_handles = snapshot.get("job_handles") if isinstance(snapshot.get("job_handles"), list) else []
    next_expected_update = snapshot.get("next_expected_update")
    updated_at = snapshot.get("last_updated") or snapshot.get("updated_at") or snapshot.get("started_at")
    observability_failure = snapshot.get("observability_failure") is True
    observability_failure_type = snapshot.get("observability_failure_type")
    if agent_executor_lost(snapshot, job_handles, now):
        status = "anomaly"
        heartbeat = "escalation_gated"
        blocker = snapshot.get("blocker") or "agent executor did not progress past starting before next_expected_update"
        observability_failure = True
        observability_failure_type = observability_failure_type or "boot_no_progress"
    else:
        status = AGENT_STATUS_MAP.get(agent_status, agent_status)
        if status in AGENT_RUNNING_STATUSES and not job_handles and due_at_passed(next_expected_update, now):
            status = "stale"
            heartbeat = "escalation_gated"
            blocker = snapshot.get("blocker") or "agent status did not update before next_expected_update"
            observability_failure = True
            observability_failure_type = observability_failure_type or "missed_expected_update"
        elif agent_no_deadline_stale(snapshot, status, job_handles, now):
            status = "stale"
            heartbeat = "escalation_gated"
            blocker = snapshot.get("blocker") or f"agent status did not update for {DEFAULT_AGENT_NO_DEADLINE_STALE_AFTER_SECONDS // 60} minutes and has no next_expected_update"
            observability_failure = True
            observability_failure_type = observability_failure_type or "missing_expected_update"
        else:
            heartbeat = "passive" if next_expected_update and status in AGENT_RUNNING_STATUSES else "none"
            blocker = snapshot.get("blocker")
    task = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "derived": True,
        "task_id": f"agent:{agent_id}",
        "kind": "agent_status",
        "title": snapshot.get("task") or agent_id,
        "execution_mode": "agent_turn",
        "durability": "supervised" if job_handles else "ephemeral",
        "observation": "enabled",
        "heartbeat": heartbeat,
        "status": status,
        "owner": snapshot.get("role"),
        "current_action": snapshot.get("current_action"),
        "created_at": snapshot.get("created_at"),
        "updated_at": updated_at,
        "next_expected_update": next_expected_update,
        "next_check_reason": snapshot.get("next_check_reason"),
        "job_handles": job_handles,
        "artifacts": snapshot.get("artifacts") if isinstance(snapshot.get("artifacts"), list) else [],
        "blocker": blocker,
        "source_refs": [rel_ref(project, path)],
        "last_ingested_at": utc_stamp(),
    }
    if observability_failure:
        task["observability_failure"] = True
        if observability_failure_type:
            task["observability_failure_type"] = observability_failure_type
    return task


def count_tasks(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key in SUMMARY_COUNT_KEYS}
    for task in tasks:
        status = task.get("status")
        if status == "completed":
            counts["recently_completed"] += 1
        elif status in counts:
            counts[status] += 1
    return counts


def runtime_metrics(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    delegated_agent_tasks = [task for task in tasks if task.get("kind") == "agent_status"]
    observability_failures = [
        task
        for task in delegated_agent_tasks
        if task.get("observability_failure") is True
    ]
    total = len(delegated_agent_tasks)
    failure_count = len(observability_failures)
    rate = round(failure_count / total, 6) if total else 0.0
    return {
        "delegated_agent_observability": {
            "delegated_agent_tasks": total,
            "observability_failures": failure_count,
            "observability_failure_rate": rate,
            "failure_task_ids": [str(task.get("task_id")) for task in observability_failures],
        }
    }


def task_resolution_status(event_type: str, payload: dict[str, Any]) -> str:
    raw_status = str(payload.get("status") or payload.get("resolution_status") or "")
    status = AGENT_STATUS_MAP.get(raw_status, raw_status)
    if status in TERMINAL_TASK_STATUSES:
        return status
    if event_type in {"task.resolved", "task.resolved_by"}:
        return "resolved"
    return "superseded"


def task_resolution_successor(payload: dict[str, Any]) -> str | None:
    for key in ("resolved_by_task_id", "superseded_by_task_id", "successor_task_id", "by_task_id"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def task_resolution_task_ids(event: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    task_ids: list[str] = []

    def add(value: Any) -> None:
        if value is None:
            return
        text = str(value)
        if text and text not in task_ids:
            task_ids.append(text)

    add(event.get("task_id"))
    for key in ("task_id", "target_task_id"):
        add(payload.get(key))
    affected = payload.get("affected_tasks")
    if isinstance(affected, list):
        for value in affected:
            add(value)
    else:
        add(affected)
    return task_ids


def collect_task_resolutions(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    resolutions: dict[str, dict[str, Any]] = {}
    for event in events:
        event_type = str(event.get("event_type") or "")
        if event_type not in TASK_RESOLUTION_EVENT_TYPES and event_type not in TASK_TERMINAL_DECISION_EVENT_TYPES:
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if event_type in TASK_TERMINAL_DECISION_EVENT_TYPES:
            raw_status = str(payload.get("status") or payload.get("resolution_status") or "")
            status = AGENT_STATUS_MAP.get(raw_status, raw_status)
            if status not in TERMINAL_TASK_STATUSES:
                continue
        else:
            status = task_resolution_status(event_type, payload)
        resolution = {
            "event_id": event.get("event_id"),
            "event_type": event_type,
            "created_at": event.get("created_at"),
            "status": status,
            "reason": payload.get("reason"),
            "resolved_by_task_id": task_resolution_successor(payload),
            "source": event.get("source") if isinstance(event.get("source"), dict) else {},
        }
        for task_id in task_resolution_task_ids(event, payload):
            resolutions[task_id] = {
                key: value
                for key, value in resolution.items()
                if value is not None and value != ""
            }
    return resolutions


def apply_task_resolutions(project: Path, root: Path, tasks: list[dict[str, Any]], resolutions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not resolutions:
        return tasks
    event_ref = rel_ref(project, root / "events" / "runtime.jsonl")
    resolved_tasks: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task.get("task_id") or "")
        resolution = resolutions.get(task_id)
        if not resolution:
            resolved_tasks.append(task)
            continue
        resolved = dict(task)
        status = str(resolution.get("status") or "superseded")
        resolved.update(
            {
                "status": status,
                "heartbeat": "none",
                "blocker": None,
                "next_expected_update": None,
                "next_check_reason": "resolved by runtime resolution event",
                "resolution": resolution,
            }
        )
        successor = resolution.get("resolved_by_task_id")
        if successor:
            resolved["resolved_by_task_id"] = successor
        refs = resolved.get("source_refs") if isinstance(resolved.get("source_refs"), list) else []
        if event_ref not in refs:
            refs = [*refs, event_ref]
        resolved["source_refs"] = refs
        resolved_tasks.append(resolved)
    return resolved_tasks


def render_summary_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Labline Runtime Status",
        "",
        f"Generated: {summary['generated_at']}",
        f"Project: {summary['project']}",
        "",
        "## Counts",
    ]
    for key in SUMMARY_COUNT_KEYS:
        lines.append(f"- {key}: {summary['counts'].get(key, 0)}")
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    delegated_observability = metrics.get("delegated_agent_observability") if isinstance(metrics.get("delegated_agent_observability"), dict) else {}
    if delegated_observability:
        rate = float(delegated_observability.get("observability_failure_rate") or 0.0)
        failures = int(delegated_observability.get("observability_failures") or 0)
        total = int(delegated_observability.get("delegated_agent_tasks") or 0)
        lines.extend(
            [
                "",
                "## Metrics",
                f"- delegated_agent_observability_failure_rate: {rate:.3f} ({failures}/{total})",
            ]
        )
    lines.extend(["", "## Tasks"])
    tasks = summary.get("tasks") or []
    if not tasks:
        lines.append("- none")
    for task in tasks:
        owner = f" {task.get('owner')}" if task.get("owner") else ""
        action = f": {task.get('current_action')}" if task.get("current_action") else ""
        lines.append(f"- [{task.get('status')}] {task.get('task_id')}{owner}{action}")
    sources = summary.get("sources") if isinstance(summary.get("sources"), dict) else {}
    queues = sources.get("queues") if isinstance(sources.get("queues"), list) else []
    if queues:
        lines.extend(["", "## Queues"])
        for item in queues:
            payload = item.get("payload") if isinstance(item, dict) else {}
            if not isinstance(payload, dict):
                continue
            queue_id = payload.get("queue_id") or Path(str(item.get("path", "queue"))).stem
            state = payload.get("state") if isinstance(payload.get("state"), dict) else payload
            jobs = state.get("jobs") if isinstance(state.get("jobs"), list) else []
            status_counts: dict[str, int] = {}
            for job in jobs:
                if isinstance(job, dict):
                    status = str(job.get("status") or "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
            parts = [f"jobs={len(jobs)}"]
            for status in ["running", "pending", "completed", "failed_oom", "failed_other", "stuck"]:
                if status_counts.get(status):
                    parts.append(f"{status}={status_counts[status]}")
            lines.append(f"- {queue_id}: {' '.join(parts)}")
    watchdog_summaries = sources.get("watchdog_summaries") if isinstance(sources.get("watchdog_summaries"), list) else []
    if watchdog_summaries:
        lines.extend(["", "## Watchdog"])
        for item in watchdog_summaries:
            payload = item.get("payload") if isinstance(item, dict) else {}
            if not isinstance(payload, dict):
                continue
            task_id = payload.get("task_id") or f"watchdog:{payload.get('watchdog_task') or Path(str(item.get('path', 'watchdog'))).parent.name}"
            status = payload.get("status") or "unknown"
            watchdog_payload = payload.get("watchdog") if isinstance(payload.get("watchdog"), dict) else {}
            msg = watchdog_payload.get("msg") or payload.get("msg") or ""
            suffix = f" {msg}" if msg else ""
            lines.append(f"- {task_id}: {status}{suffix}")
    return "\n".join(lines) + "\n"


def collect_runtime_sources(project: Path, root: Path, now: datetime | None = None) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    source_counts = {
        "runtime_tasks": 0,
        "agents": 0,
        "jobs": 0,
        "queues": 0,
        "watchdog_summaries": 0,
        "pipelines": 0,
        "legacy_pipeline_state": 0,
        "task_resolutions": 0,
    }
    sources: dict[str, Any] = {
        "runtime_tasks": [],
        "jobs": [],
        "queues": [],
        "watchdog_summaries": [],
        "pipelines": [],
        "legacy_pipeline_state": None,
        "task_resolutions": [],
    }

    for path, payload in iter_json_objects(root / "tasks"):
        if payload.get("derived") is True:
            continue
        source_counts["runtime_tasks"] += 1
        payload = dict(payload)
        refs = payload.get("source_refs") if isinstance(payload.get("source_refs"), list) else []
        payload["source_refs"] = refs or [rel_ref(project, path)]
        tasks.append(payload)
        sources["runtime_tasks"].append({"path": rel_ref(project, path), "task_id": payload.get("task_id")})

    agent_paths: list[tuple[Path, dict[str, Any]]] = []
    seen_agents: set[str] = set()
    for path, snapshot in iter_json_objects(root / "agents"):
        agent_id = str(snapshot.get("agent_id") or path.stem)
        seen_agents.add(agent_id)
        agent_paths.append((path, snapshot))
    for path, snapshot in iter_json_objects(project / STATE_DIR_NAME / "status" / "agents"):
        agent_id = str(snapshot.get("agent_id") or path.stem)
        if agent_id in seen_agents:
            continue
        agent_paths.append((path, snapshot))
    for path, snapshot in agent_paths:
        tasks.append(agent_snapshot_to_task(project, path, snapshot, now=now))
    source_counts["agents"] = len(agent_paths)

    for path, payload in iter_json_objects(root / "jobs"):
        source_counts["jobs"] += 1
        sources["jobs"].append({"path": rel_ref(project, path), "payload": payload})
    for path, payload in iter_json_objects(root / "queues"):
        source_counts["queues"] += 1
        sources["queues"].append({"path": rel_ref(project, path), "payload": payload})
    for path in sorted((root / "watchdog").glob("**/summary.json")) if (root / "watchdog").exists() else []:
        payload = read_json_file(path)
        source_counts["watchdog_summaries"] += 1
        sources["watchdog_summaries"].append({"path": rel_ref(project, path), "payload": payload})
    for path, payload in iter_json_objects(root / "pipelines"):
        source_counts["pipelines"] += 1
        sources["pipelines"].append({"path": rel_ref(project, path), "payload": payload})

    legacy_pipeline = project / "PIPELINE_STATE.json"
    if legacy_pipeline.exists():
        source_counts["legacy_pipeline_state"] = 1
        sources["legacy_pipeline_state"] = {"path": rel_ref(project, legacy_pipeline), "payload": read_json_file(legacy_pipeline)}

    resolutions = collect_task_resolutions(iter_runtime_events(root))
    if resolutions:
        tasks = apply_task_resolutions(project, root, tasks, resolutions)
        source_counts["task_resolutions"] = len(resolutions)
        sources["task_resolutions"] = [
            {"task_id": task_id, "resolution": resolution}
            for task_id, resolution in sorted(resolutions.items())
        ]

    return sorted(tasks, key=lambda item: str(item.get("task_id"))), source_counts, sources


def write_derived_tasks(root: Path, tasks: list[dict[str, Any]]) -> None:
    for task in tasks:
        task_id = str(task.get("task_id") or "task")
        atomic_write_json(runtime_task_path(root, task_id), task)


def summarize_runtime(project: Path | None = None, write: bool = True) -> tuple[dict[str, Any], str]:
    project_root = resolve_project(project)
    root = init_runtime_root(project_root)
    now = datetime.now(timezone.utc)
    tasks, source_counts, sources = collect_runtime_sources(project_root, root, now=now)
    summary = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "derived": True,
        "generated_at": utc_stamp(),
        "project": str(project_root),
        "counts": count_tasks(tasks),
        "metrics": runtime_metrics(tasks),
        "source_counts": source_counts,
        "tasks": tasks,
        "sources": sources,
    }
    summary_md = render_summary_md(summary)
    if write:
        write_derived_tasks(root, tasks)
        atomic_write_json(root / "summaries" / "current.json", summary)
        atomic_write_text(root / "summaries" / "current.md", summary_md)
    return summary, summary_md


def summarize_runtime_readonly(project: Path | None, generated_at: str) -> dict[str, Any]:
    project_root = resolve_project(project)
    root = runtime_root(project_root)
    tasks, source_counts, sources = collect_runtime_sources(project_root, root, now=parse_utc(generated_at))
    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "derived": True,
        "generated_at": generated_at,
        "project": str(project_root),
        "counts": count_tasks(tasks),
        "metrics": runtime_metrics(tasks),
        "source_counts": source_counts,
        "tasks": tasks,
        "sources": sources,
    }


def load_task(project: Path | None, task_id: str) -> dict[str, Any]:
    root = runtime_root(project)
    path = root / "tasks" / f"{task_id}.json"
    if not path.exists():
        path = runtime_task_path(root, task_id)
    if not path.exists():
        raise FileNotFoundError(f"runtime task not found: {task_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_tasks(project: Path | None) -> list[dict[str, Any]]:
    tasks_dir = runtime_root(project) / "tasks"
    if not tasks_dir.exists():
        return []
    tasks = []
    for path in sorted(tasks_dir.glob("*.json")):
        tasks.append(json.loads(path.read_text(encoding="utf-8")))
    return tasks


def parse_json_objects(values: list[str] | None, label: str) -> list[dict[str, Any]]:
    parsed = []
    for value in values or []:
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid {label}: {exc.msg}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"invalid {label}: expected object")
        parsed.append(data)
    return parsed


def role_name(task: dict[str, Any]) -> str:
    return str(task.get("owner") or task.get("role") or "").strip().lower()


def is_delegated_agent_task(task: dict[str, Any]) -> bool:
    return str(task.get("kind") or "") in DELEGATED_AGENT_KINDS


def task_identity_equal(left: Any, right: Any) -> bool:
    def normalize(value: Any) -> str:
        text = str(value or "")
        return text[6:] if text.startswith("agent:") else text

    return normalize(left) == normalize(right)


def task_artifact_path(project: Path | None, artifact: str) -> Path:
    path = Path(artifact)
    if path.is_absolute():
        return path
    root = resolve_project(project)
    return root / path


def validate_terminal_artifacts(task: dict[str, Any], project: Path | None) -> None:
    if task.get("status") not in SUCCESS_TERMINAL_TASK_STATUSES:
        return
    required_artifacts = task.get("required_artifacts") if isinstance(task.get("required_artifacts"), list) else []
    missing = [
        str(artifact)
        for artifact in required_artifacts
        if not task_artifact_path(project, str(artifact)).exists()
    ]
    if missing:
        raise ValueError(f"terminal task missing required artifacts: {', '.join(missing)}")
    verdict_artifact = task.get("verdict_artifact")
    if role_name(task) == "reviewer":
        if not verdict_artifact:
            raise ValueError("reviewer terminal tasks require --verdict-artifact")
        if not task_artifact_path(project, str(verdict_artifact)).exists():
            raise ValueError(f"terminal task missing verdict artifact: {verdict_artifact}")


def validate_task(task: dict[str, Any], project: Path | None = None) -> None:
    required = ["task_id", "kind", "title", "execution_mode", "durability", "observation", "heartbeat", "status"]
    for field in required:
        if not task.get(field):
            raise ValueError(f"task missing {field}")
    if task["execution_mode"] not in EXECUTION_MODES:
        raise ValueError(f"invalid execution_mode={task['execution_mode']}")
    if task["durability"] not in DURABILITY_VALUES:
        raise ValueError(f"invalid durability={task['durability']}")
    if task["observation"] not in OBSERVATION_VALUES:
        raise ValueError(f"invalid observation={task['observation']}")
    if task["heartbeat"] not in HEARTBEAT_VALUES:
        raise ValueError(f"invalid heartbeat={task['heartbeat']}")
    if task["status"] not in TASK_STATUSES:
        raise ValueError(f"invalid status={task['status']}")
    if task["heartbeat"] != "none" and not task.get("next_expected_update"):
        raise ValueError("heartbeat requires --next-expected-update")
    job_handles = task.get("job_handles") if isinstance(task.get("job_handles"), list) else []
    if task["durability"] == "ephemeral" and job_handles:
        raise ValueError("ephemeral tasks cannot declare job handles")
    if task["execution_mode"] == "detached_job" and task["status"] not in {"new", "dispatching", "handoff_verifying"} and not job_handles:
        raise ValueError("detached_job running tasks require at least one job handle")
    if is_delegated_agent_task(task) and task["status"] not in TERMINAL_TASK_STATUSES and not task.get("next_expected_update"):
        raise ValueError("delegated agent tasks require --next-expected-update")
    retry_of = task.get("retry_of")
    if retry_of and task_identity_equal(task.get("task_id"), retry_of):
        raise ValueError("retry task must use a new task_id distinct from retry_of")
    validate_terminal_artifacts(task, project)


def build_task_from_args(args: argparse.Namespace, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    now = utc_stamp()
    job_handles = parse_json_objects(getattr(args, "job_handle", None), "--job-handle")
    artifacts = list(getattr(args, "artifact", None) or [])
    required_artifacts = list(getattr(args, "required_artifact", None) or [])
    task = dict(existing or {})
    task.update(
        {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "derived": False,
            "task_id": getattr(args, "task_id"),
            "kind": getattr(args, "kind", None) or task.get("kind") or "general",
            "title": getattr(args, "title", None) or task.get("title") or getattr(args, "task_id"),
            "execution_mode": getattr(args, "execution_mode", None) or task.get("execution_mode") or "agent_turn",
            "durability": getattr(args, "durability", None) or task.get("durability") or "ephemeral",
            "observation": getattr(args, "observation", None) or task.get("observation") or "enabled",
            "heartbeat": getattr(args, "heartbeat", None) or task.get("heartbeat") or "none",
            "status": getattr(args, "status", None) or task.get("status") or "new",
            "owner": getattr(args, "owner", None) if getattr(args, "owner", None) is not None else task.get("owner"),
            "parent_task_id": getattr(args, "parent_task_id", None) if getattr(args, "parent_task_id", None) is not None else task.get("parent_task_id"),
            "current_action": getattr(args, "current_action", None) if getattr(args, "current_action", None) is not None else task.get("current_action"),
            "next_expected_update": getattr(args, "next_expected_update", None) if getattr(args, "next_expected_update", None) is not None else task.get("next_expected_update"),
            "next_check_reason": getattr(args, "next_check_reason", None) if getattr(args, "next_check_reason", None) is not None else task.get("next_check_reason"),
            "blocker": getattr(args, "blocker", None) if getattr(args, "blocker", None) is not None else task.get("blocker"),
            "updated_at": now,
        }
    )
    for field in ("retry_of", "supersedes", "verdict_artifact"):
        value = getattr(args, field, None)
        if value is not None:
            task[field] = value
    if "created_at" not in task or not task["created_at"]:
        task["created_at"] = now
    if job_handles:
        task["job_handles"] = job_handles
    else:
        task.setdefault("job_handles", [])
    if artifacts:
        task["artifacts"] = artifacts
    else:
        task.setdefault("artifacts", [])
    if required_artifacts:
        task["required_artifacts"] = required_artifacts
    else:
        task.setdefault("required_artifacts", [])
    task.setdefault("source_refs", [])
    validate_task(task, project=getattr(args, "project", None))
    return task


def write_task(project: Path | None, task: dict[str, Any], event_type: str, event_payload: dict[str, Any] | None = None) -> Path:
    root = init_runtime_root(project)
    path = runtime_task_path(root, str(task["task_id"]))
    atomic_write_json(path, task)
    append_runtime_event(project, event_type, task_id=str(task["task_id"]), payload=event_payload or {"status": task.get("status")})
    return path


def create_task(args: argparse.Namespace) -> dict[str, Any]:
    task = build_task_from_args(args)
    write_task(getattr(args, "project", None), task, "task.created")
    return task


def update_task(args: argparse.Namespace, event_type: str = "task.updated") -> dict[str, Any]:
    existing = load_task(getattr(args, "project", None), args.task_id)
    if existing.get("derived") is True:
        raise ValueError("cannot update derived runtime task")
    task = build_task_from_args(args, existing=existing)
    write_task(getattr(args, "project", None), task, event_type)
    return task


def lease_is_active(lease: dict[str, Any], now: datetime) -> bool:
    expires_at = parse_utc(lease.get("expires_at"))
    return expires_at > now


def build_lease(lease_id: str, owner: str, ttl: int, purpose: str, now: datetime) -> dict[str, Any]:
    if ttl <= 0:
        raise ValueError("--ttl must be positive")
    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "lease_id": lease_id,
        "owner": owner,
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "acquired_at": format_utc(now),
        "expires_at": format_utc(now + timedelta(seconds=ttl)),
        "ttl_seconds": ttl,
        "purpose": purpose,
    }


def acquire_lease(args: argparse.Namespace) -> dict[str, Any]:
    project = getattr(args, "project", None)
    root = init_runtime_root(project)
    now = parse_utc(getattr(args, "now", None))
    path = runtime_lease_path(root, args.lease_id)
    previous = read_json_file(path) if path.exists() else None
    if previous and lease_is_active(previous, now) and previous.get("owner") != args.owner:
        raise ValueError(f"lease held: {args.lease_id} by {previous.get('owner')} until {previous.get('expires_at')}")

    if previous and not lease_is_active(previous, now) and previous.get("owner") != args.owner:
        append_runtime_event(
            project,
            "lease.stolen",
            payload={
                "lease_id": args.lease_id,
                "previous_owner": previous.get("owner"),
                "previous_expires_at": previous.get("expires_at"),
                "new_owner": args.owner,
            },
        )
    lease = build_lease(args.lease_id, args.owner, args.ttl, args.purpose, now)
    atomic_write_json(path, lease)
    append_runtime_event(project, "lease.acquired", payload=lease)
    return lease


def release_lease(args: argparse.Namespace) -> dict[str, Any]:
    project = getattr(args, "project", None)
    root = init_runtime_root(project)
    path = runtime_lease_path(root, args.lease_id)
    if not path.exists():
        raise FileNotFoundError(f"lease not found: {args.lease_id}")
    lease = read_json_file(path)
    if lease.get("owner") != args.owner:
        raise ValueError(f"lease owner mismatch: {args.lease_id} held by {lease.get('owner')}")
    path.unlink()
    payload = {"lease_id": args.lease_id, "owner": args.owner, "status": "released", "released_at": utc_stamp()}
    append_runtime_event(project, "lease.released", payload=payload)
    return payload


def lease_status(args: argparse.Namespace) -> Any:
    project = getattr(args, "project", None)
    root = init_runtime_root(project)
    now = parse_utc(getattr(args, "now", None))
    if getattr(args, "lease_id", None):
        path = runtime_lease_path(root, args.lease_id)
        if not path.exists():
            return {"lease_id": args.lease_id, "status": "missing"}
        lease = read_json_file(path)
        lease["active"] = lease_is_active(lease, now)
        return lease
    leases = []
    for path in sorted((root / "leases").glob("*.json")):
        lease = read_json_file(path)
        lease["active"] = lease_is_active(lease, now)
        leases.append(lease)
    return leases


def emit_json_or_error(func, args: argparse.Namespace) -> int:
    try:
        payload = func(args)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2 if isinstance(exc, ValueError) else 1
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def parse_target(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        target = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid --target: {exc.msg}") from exc
    if not isinstance(target, dict):
        raise ValueError("invalid --target: expected object")
    return target


def submit_control_intent(args: argparse.Namespace) -> dict[str, Any]:
    if args.risk_level not in RISK_LEVELS:
        raise ValueError(f"invalid risk_level={args.risk_level}")
    if args.confirmation_status not in CONFIRMATION_STATUSES:
        raise ValueError(f"invalid confirmation_status={args.confirmation_status}")
    if args.source_entry == "feishu" and not args.archive_ref:
        raise ValueError("feishu control intents require --archive-ref")
    now = parse_utc(getattr(args, "now", None))
    intent = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "intent_id": getattr(args, "intent_id", None) or "intent_" + uuid.uuid4().hex,
        "source": {"entry": args.source_entry, "archive_ref": args.archive_ref},
        "action": args.action,
        "risk_level": args.risk_level,
        "confirmation_status": args.confirmation_status,
        "target": parse_target(args.target),
        "lease_scope": args.lease_scope,
        "status": "pending",
        "created_at": format_utc(now),
    }
    append_runtime_event(getattr(args, "project", None), "control_intent.submitted", payload=intent)
    return intent


def heartbeat_due(task: dict[str, Any], now: datetime, forced: bool) -> bool:
    if forced:
        return True
    due_at = task.get("next_expected_update")
    if not due_at:
        return False
    try:
        return parse_utc(str(due_at)) <= now
    except ValueError:
        return True


def heartbeat_text(task: dict[str, Any]) -> str:
    fields = [
        task.get("status"),
        task.get("blocker"),
        task.get("next_check_reason"),
        task.get("current_action"),
        task.get("title"),
    ]
    return " ".join(str(value) for value in fields if value).lower()


def classify_heartbeat_escalation(task: dict[str, Any]) -> tuple[str, str] | None:
    status = str(task.get("status") or "")
    if status in TERMINAL_TASK_STATUSES:
        return "terminal_result", f"task reached terminal status {status}"
    if status == "need_decision":
        return "due_decision", "task requires a decision"
    if status in HEARTBEAT_ESCALATION_STATUSES:
        return status, f"task status is {status}"

    text = heartbeat_text(task)
    detectors = [
        ("oom", r"\b(oom|out of memory)\b"),
        ("nan", r"\bnan\b"),
        ("dead", r"\bdead\b"),
        ("stalled", r"\bstall(?:ed|ing)?\b"),
    ]
    for escalation_type, pattern in detectors:
        if re.search(pattern, text):
            return escalation_type, f"task text matched {escalation_type}"
    return None


def copy_phase_boundary_context(source: dict[str, Any], target: dict[str, Any]) -> None:
    for key in PHASE_BOUNDARY_CONTEXT_KEYS:
        value = source.get(key)
        if value is None or value == "":
            continue
        target[key] = value


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []


def phase_boundary_evidence(task: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for key in ("phase_boundary_evidence", "phase_boundary_readiness_evidence", "readiness_evidence"):
        value = task.get(key)
        if isinstance(value, dict):
            evidence.update(value)
    for key in PHASE_BOUNDARY_CONTEXT_KEYS:
        if key in task and key not in {"phase_boundary_evidence", "phase_boundary_readiness_evidence", "readiness_evidence"}:
            evidence.setdefault(key, task[key])
    return evidence


def verdicts_satisfied(value: Any) -> bool:
    if value in (None, "", []):
        return True
    allowed = {"pass", "passed", "ok", "approved", "complete", "completed", "resolved", "success", "succeeded"}
    if isinstance(value, dict):
        verdict = value.get("verdict") or value.get("status") or value.get("result")
        if verdict is None and value:
            return all(verdicts_satisfied(item) for item in value.values())
        return str(verdict).lower() in allowed
    if isinstance(value, list):
        return all(verdicts_satisfied(item) for item in value)
    return str(value).lower() in allowed


def phase_boundary_evidence_is_satisfied(
    project: Path,
    task: dict[str, Any],
    tasks_by_id: dict[str, dict[str, Any]],
) -> bool:
    if task.get("kind") != "phase_boundary":
        return False
    evidence = phase_boundary_evidence(task)
    if not evidence:
        return False
    if not (evidence.get("next_leader_question") or evidence.get("next_leader_prompt")):
        return False
    prerequisite_task_ids = string_list(evidence.get("prerequisite_task_ids") or evidence.get("prerequisite_tasks"))
    for prerequisite_task_id in prerequisite_task_ids:
        prerequisite = tasks_by_id.get(prerequisite_task_id)
        if not prerequisite or prerequisite.get("status") not in PHASE_BOUNDARY_SUCCESS_STATUSES:
            return False
    for artifact in string_list(evidence.get("required_artifacts")):
        path = Path(artifact)
        if not path.is_absolute():
            path = project / path
        if not path.exists():
            return False
    if not verdicts_satisfied(evidence.get("required_gate_verdicts")):
        return False
    if not verdicts_satisfied(evidence.get("required_reviewer_verdicts")):
        return False
    return True


def action_counts(actions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"escalated": 0, "healthy": 0, "skipped": 0}
    for action in actions:
        name = action.get("action")
        if name in counts:
            counts[name] += 1
    return counts


def write_heartbeat_escalation(root: Path, now_stamp: str, runner: str, task: dict[str, Any], escalation_type: str, reason: str, lease_scope: str) -> tuple[dict[str, Any], Path]:
    escalation = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "escalation_id": "esc_" + uuid.uuid4().hex,
        "created_at": now_stamp,
        "runner": runner,
        "task_id": task.get("task_id"),
        "status": task.get("status"),
        "escalation_type": escalation_type,
        "reason": reason,
        "lease_scope": lease_scope,
        "resume_allowed": True,
        "source": {"entry": "lane heartbeat"},
    }
    copy_phase_boundary_context(task, escalation)
    path = root / "escalations" / f"{now_stamp.replace(':', '').replace('-', '')}-{safe_filename(str(task.get('task_id') or 'task'))}-{escalation['escalation_id']}.json"
    atomic_write_json(path, escalation)
    return escalation, path


def run_heartbeat(args: argparse.Namespace) -> dict[str, Any]:
    project = getattr(args, "project", None)
    project_root = resolve_project(project)
    root = runtime_root(project_root)
    now = parse_utc(getattr(args, "now", None))
    now_stamp = format_utc(now)
    runner = getattr(args, "runner", None) or "local-heartbeat"
    dry_run = bool(getattr(args, "dry_run", False))
    explicit_task = getattr(args, "task_id", None)
    forced = bool(getattr(args, "force", False) or explicit_task)

    summary, _summary_md = summarize_runtime(project_root, write=not dry_run)
    tasks = summary.get("tasks") or []
    if explicit_task:
        tasks = [task for task in tasks if task.get("task_id") == explicit_task]
        if not tasks:
            raise FileNotFoundError(f"runtime task not found: {explicit_task}")

    actions: list[dict[str, Any]] = []
    for task in tasks:
        heartbeat_mode = task.get("heartbeat")
        if heartbeat_mode not in HEARTBEAT_ENABLED_VALUES:
            continue
        task_forced = forced
        is_due = heartbeat_due(task, now, forced=False)
        if not (is_due or task_forced):
            continue

        task_id = str(task.get("task_id") or "")
        base_action = {
            "task_id": task_id,
            "status": task.get("status"),
            "heartbeat": heartbeat_mode,
            "due": is_due,
            "forced": task_forced,
        }
        escalation = classify_heartbeat_escalation(task)
        if escalation:
            escalation_type, reason = escalation
            lease_scope = f"task:{task_id}"
            action = {
                **base_action,
                "action": "escalated",
                "escalation_type": escalation_type,
                "reason": reason,
                "lease_scope": lease_scope,
            }
            if not dry_run:
                try:
                    acquire_lease(
                        argparse.Namespace(
                            project=project_root,
                            lease_id=lease_scope,
                            owner=runner,
                            ttl=getattr(args, "lease_ttl", 60),
                            purpose=f"heartbeat escalation for {task_id}",
                            now=now_stamp,
                        )
                    )
                except ValueError as exc:
                    skipped = {
                        **base_action,
                        "action": "skipped",
                        "reason": "lease_unavailable",
                        "lease_scope": lease_scope,
                        "detail": str(exc),
                    }
                    actions.append(skipped)
                    append_runtime_event(project_root, "heartbeat.skipped", task_id=task_id, payload=skipped)
                    continue
                escalation_payload, path = write_heartbeat_escalation(root, now_stamp, runner, task, escalation_type, reason, lease_scope)
                action["escalation_ref"] = rel_ref(project_root, path)
                append_runtime_event(project_root, "heartbeat.escalation", task_id=task_id, payload=escalation_payload)
            actions.append(action)
            continue

        action = {**base_action, "action": "healthy", "reason": "no_change_but_healthy"}
        actions.append(action)
        if not dry_run:
            append_runtime_event(project_root, "task.no_change_but_healthy", task_id=task_id, payload=action)

    counts = action_counts(actions)
    result = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "runner": runner,
        "checked_at": now_stamp,
        "dry_run": dry_run,
        "checked_count": len(actions),
        "action_counts": counts,
        "actions": actions,
    }
    if not dry_run:
        runner_state = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "runner": runner,
            "last_checked_at": now_stamp,
            "last_checked_count": len(actions),
            "last_action_counts": counts,
            "actions": actions,
        }
        atomic_write_json(root / "heartbeats" / f"{safe_filename(runner)}.json", runner_state)
        append_runtime_event(project_root, "heartbeat.checked", payload={key: result[key] for key in ["runner", "checked_at", "checked_count", "action_counts"]})
    return result


def iter_runtime_events(root: Path) -> list[dict[str, Any]]:
    path = root / "events" / "runtime.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid runtime event log line {line_no}: {exc.msg}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"invalid runtime event log line {line_no}: expected object")
        events.append(event)
    return events


def high_risk_pending_intents(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("event_type") != "control_intent.submitted":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        intent_id = str(payload.get("intent_id") or "")
        if not intent_id:
            continue
        by_id[intent_id] = payload
    return [
        intent
        for intent in by_id.values()
        if intent.get("status") == "pending"
        and intent.get("risk_level") == "high"
        and intent.get("confirmation_status") not in {"confirmed", "not_required"}
    ]


def wakeup_intent_payload(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent_id": intent.get("intent_id"),
        "action": intent.get("action"),
        "risk_level": intent.get("risk_level"),
        "confirmation_status": intent.get("confirmation_status"),
        "lease_scope": intent.get("lease_scope"),
        "target": intent.get("target") if isinstance(intent.get("target"), dict) else {},
    }


def lease_plan(root: Path, lease_id: str, owner: str, now: datetime) -> dict[str, Any]:
    path = runtime_lease_path(root, lease_id)
    base: dict[str, Any] = {"lease_id": lease_id, "available": True}
    if not path.exists():
        return base
    lease = read_json_file(path)
    active = lease_is_active(lease, now)
    base.update(
        {
            "active": active,
            "holder": lease.get("owner"),
            "expires_at": lease.get("expires_at"),
        }
    )
    if active and lease.get("owner") != owner:
        base["available"] = False
        base["reason"] = "lease_unavailable"
    return base


def phase_boundary_ready_candidate_from_task(
    project: Path,
    task: dict[str, Any],
    tasks_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if task.get("status") != "ready_to_continue":
        return None
    if not phase_boundary_evidence_is_satisfied(project, task, tasks_by_id):
        return None
    task_id = str(task.get("task_id") or "")
    if not task_id:
        return None
    candidate = {
        "source": "runtime_task",
        "task_id": task_id,
        "status": task.get("status"),
        "title": task.get("title"),
        "category": PHASE_BOUNDARY_READY_ESCALATION,
        "reason": "phase boundary ready for Leader orchestration",
        "lease_scope": f"task:{task_id}",
        "source_refs": task.get("source_refs") if isinstance(task.get("source_refs"), list) else [],
    }
    copy_phase_boundary_context(task, candidate)
    return candidate


def escalation_candidate_from_task(task: dict[str, Any]) -> dict[str, Any] | None:
    escalation = classify_heartbeat_escalation(task)
    if not escalation:
        return None
    escalation_type, reason = escalation
    if escalation_type == "terminal_result":
        return None
    task_id = str(task.get("task_id") or "")
    if not task_id:
        return None
    candidate = {
        "source": "runtime_task",
        "task_id": task_id,
        "status": task.get("status"),
        "title": task.get("title"),
        "escalation_type": escalation_type,
        "reason": reason,
        "lease_scope": f"task:{task_id}",
        "source_refs": task.get("source_refs") if isinstance(task.get("source_refs"), list) else [],
    }
    copy_phase_boundary_context(task, candidate)
    return candidate


def terminal_result_candidate_from_task(task: dict[str, Any]) -> dict[str, Any] | None:
    if task.get("derived") is True and task.get("kind") == "agent_status":
        return None
    status = str(task.get("status") or "")
    if status not in WAKEUP_TERMINAL_TASK_STATUSES:
        return None
    task_id = str(task.get("task_id") or "")
    if not task_id:
        return None
    candidate = {
        "source": "runtime_task",
        "task_id": task_id,
        "status": task.get("status"),
        "title": task.get("title"),
        "escalation_type": "terminal_result",
        "reason": f"task reached terminal status {status}",
        "lease_scope": f"task:{task_id}",
        "source_refs": task.get("source_refs") if isinstance(task.get("source_refs"), list) else [],
    }
    copy_phase_boundary_context(task, candidate)
    return candidate


def tmux_session_active(project: Path, session: str) -> bool | None:
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session],
            cwd=str(project),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return None
    return result.returncode == 0


def missing_required_artifact_refs(project: Path, task: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for artifact in string_list(task.get("required_artifacts")):
        path = Path(artifact)
        if not path.is_absolute():
            path = project / path
        if not path.exists():
            missing.append(artifact)
    return missing


def read_exit_code_ref(project: Path, ref: str) -> int | None:
    if not ref:
        return None
    path = Path(ref)
    if not path.is_absolute():
        path = project / path
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    try:
        return int(text.split()[0])
    except (IndexError, ValueError):
        return None


def detached_job_candidate_from_task(project: Path, task: dict[str, Any]) -> dict[str, Any] | None:
    if task.get("execution_mode") != "detached_job":
        return None
    if task.get("status") not in {"running", "waiting_on_job"}:
        return None
    task_id = str(task.get("task_id") or "")
    if not task_id:
        return None
    job_handles = task.get("job_handles") if isinstance(task.get("job_handles"), list) else []
    tmux_handles = [
        handle
        for handle in job_handles
        if isinstance(handle, dict) and (handle.get("type") == "tmux" or handle.get("backend") == "tmux")
    ]
    if not tmux_handles:
        return None

    inactive_handles: list[dict[str, Any]] = []
    for handle in tmux_handles:
        session = str(handle.get("session") or "")
        if not session:
            continue
        active = tmux_session_active(project, session)
        if active is True:
            return None
        if active is False:
            inactive_handles.append(handle)
    if not inactive_handles:
        return None

    required_artifacts = string_list(task.get("required_artifacts"))
    missing_artifacts = missing_required_artifact_refs(project, task)
    exit_codes: list[dict[str, Any]] = []
    nonzero_exit_codes: list[dict[str, Any]] = []
    for handle in inactive_handles:
        exit_code_ref = str(handle.get("exit_code_ref") or "")
        exit_code = read_exit_code_ref(project, exit_code_ref)
        if exit_code is None:
            continue
        exit_record = {
            "session": str(handle.get("session") or ""),
            "exit_code": exit_code,
            "exit_code_ref": exit_code_ref,
        }
        exit_codes.append(exit_record)
        if exit_code != 0:
            nonzero_exit_codes.append(exit_record)

    if nonzero_exit_codes:
        escalation_type = "detached_job_exited"
        reason = "detached tmux job session is no longer active; exit code is non-zero"
    elif required_artifacts and not missing_artifacts:
        escalation_type = "detached_job_completed"
        reason = "detached tmux job session is no longer active and required artifacts exist"
    else:
        escalation_type = "detached_job_exited"
        reason = "detached tmux job session is no longer active"
        if missing_artifacts:
            reason += "; required artifacts are missing"

    candidate = {
        "source": "runtime_task",
        "task_id": task_id,
        "status": task.get("status"),
        "title": task.get("title"),
        "escalation_type": escalation_type,
        "reason": reason,
        "lease_scope": f"task:{task_id}",
        "source_refs": task.get("source_refs") if isinstance(task.get("source_refs"), list) else [],
        "job_handles": inactive_handles,
    }
    if required_artifacts:
        candidate["required_artifacts"] = required_artifacts
    if missing_artifacts:
        candidate["missing_artifacts"] = missing_artifacts
    if exit_codes:
        candidate["exit_codes"] = exit_codes
    if nonzero_exit_codes:
        candidate["nonzero_exit_codes"] = nonzero_exit_codes
    copy_phase_boundary_context(task, candidate)
    return candidate


def escalation_candidate_from_file(project: Path, path: Path, escalation: dict[str, Any]) -> dict[str, Any] | None:
    if escalation.get("resume_allowed") is False:
        return None
    task_id = str(escalation.get("task_id") or "")
    if not task_id:
        return None
    escalation_type = escalation.get("escalation_type")
    if escalation_type == PHASE_BOUNDARY_READY_ESCALATION:
        return None
    candidate = {
        "source": "runtime_escalation",
        "task_id": task_id,
        "status": escalation.get("status"),
        "escalation_id": escalation.get("escalation_id"),
        "reason": escalation.get("reason"),
        "lease_scope": escalation.get("lease_scope") or f"task:{task_id}",
        "source_refs": [rel_ref(project, path)],
    }
    candidate["escalation_type"] = escalation_type
    copy_phase_boundary_context(escalation, candidate)
    return candidate


def collect_wakeup_candidates(
    project: Path,
    root: Path,
    tasks: list[dict[str, Any]],
    task_id: str | None = None,
    resolved_task_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    resolved_task_ids = resolved_task_ids or set()
    tasks_by_id = {str(task.get("task_id")): task for task in tasks if task.get("task_id")}
    retried_task_ids = {str(task.get("retry_of")) for task in tasks if task.get("retry_of")}
    for path, escalation in iter_json_objects(root / "escalations"):
        candidate = escalation_candidate_from_file(project, path, escalation)
        if not candidate:
            continue
        if candidate.get("task_id") in resolved_task_ids or candidate.get("task_id") in retried_task_ids:
            continue
        if task_id and candidate.get("task_id") != task_id:
            continue
        key = (
            str(candidate.get("source")),
            str(candidate.get("task_id")),
            str(candidate.get("escalation_id") or wakeup_candidate_category(candidate)),
        )
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    for task in tasks:
        if task.get("task_id") in resolved_task_ids or task.get("task_id") in retried_task_ids:
            continue
        candidate = (
            phase_boundary_ready_candidate_from_task(project, task, tasks_by_id)
            or detached_job_candidate_from_task(project, task)
            or terminal_result_candidate_from_task(task)
            or escalation_candidate_from_task(task)
        )
        if not candidate:
            continue
        if task_id and candidate.get("task_id") != task_id:
            continue
        key = ("runtime_task", str(candidate.get("task_id")), wakeup_candidate_category(candidate))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    return candidates


def build_wakeup_plan(args: argparse.Namespace) -> dict[str, Any]:
    project = resolve_project(getattr(args, "project", None))
    root = runtime_root(project)
    now = parse_utc(getattr(args, "now", None))
    now_stamp = format_utc(now)
    owner = getattr(args, "owner", None) or "labline-wakeup"
    task_id = getattr(args, "task_id", None)
    force = bool(getattr(args, "force", False))
    summary = summarize_runtime_readonly(project, now_stamp)
    events = iter_runtime_events(root)
    resolutions = collect_task_resolutions(events)
    candidates = collect_wakeup_candidates(
        project,
        root,
        summary.get("tasks") or [],
        task_id=task_id,
        resolved_task_ids=set(resolutions),
    )
    base = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "generated_at": now_stamp,
        "dry_run": True,
        "project": str(project),
        "owner": owner,
        "summary_counts": summary.get("counts") or {},
        "summary_metrics": summary.get("metrics") or {},
        "candidates": candidates,
    }
    if force:
        base["force"] = True
        base["force_reason"] = "user_requested_retry"

    intents = high_risk_pending_intents(events)
    if intents:
        return {
            **base,
            "action": "needs_confirmation",
            "reason": "high_risk_intent_requires_confirmation",
            "intent": wakeup_intent_payload(intents[0]),
        }

    if not candidates:
        return {**base, "action": "skip", "reason": "healthy_or_no_escalation"}

    skipped_started_candidates: list[dict[str, Any]] = []
    forced_started_candidates: list[dict[str, Any]] = []
    candidate: dict[str, Any] | None = None
    wakeup_key: str | None = None
    for item in candidates:
        item_wakeup_key = candidate_wakeup_key(item)
        if wakeup_has_started(events, item_wakeup_key):
            marker = started_wakeup_candidate_marker(item, item_wakeup_key)
            if force:
                forced_started_candidates.append(marker)
                candidate = item
                wakeup_key = item_wakeup_key
                break
            skipped_started_candidates.append(marker)
            continue
        candidate = item
        wakeup_key = item_wakeup_key
        break
    if candidate is None or wakeup_key is None:
        first_candidate = candidates[0]
        first_wakeup_key = candidate_wakeup_key(first_candidate)
        return {
            **base,
            "action": "skip",
            "reason": "wakeup_already_started",
            "candidate": first_candidate,
            "wakeup_key": first_wakeup_key,
            "skipped_started_candidates": skipped_started_candidates,
        }

    leader_lease = lease_plan(root, "leader_session", owner, now)
    if not leader_lease.get("available"):
        result = {
            **base,
            "action": "skip",
            "reason": "lease_unavailable",
            "candidate": candidate,
            "wakeup_key": wakeup_key,
            "skipped_started_candidates": skipped_started_candidates,
            "lease": leader_lease,
        }
        if forced_started_candidates:
            result["forced_started_candidates"] = forced_started_candidates
        return result

    result = {
        **base,
        "action": "acquire_lease",
        "next_action": "start_leader_turn",
        "reason": wakeup_plan_reason(candidate),
        "candidate": candidate,
        "wakeup_key": wakeup_key,
        "skipped_started_candidates": skipped_started_candidates,
        "lease": leader_lease,
    }
    if forced_started_candidates:
        result["forced_started_candidates"] = forced_started_candidates
    return result


def wakeup_candidate_category(candidate: dict[str, Any]) -> str:
    return str(candidate.get("category") or candidate.get("escalation_type") or "status")


def wakeup_plan_reason(candidate: dict[str, Any]) -> str:
    if wakeup_candidate_category(candidate) == PHASE_BOUNDARY_READY_ESCALATION:
        return PHASE_BOUNDARY_READY_ESCALATION
    return "escalation_candidate"


def candidate_wakeup_key(candidate: dict[str, Any]) -> str:
    escalation_id = candidate.get("escalation_id")
    if escalation_id:
        return f"escalation:{escalation_id}"
    task_id = candidate.get("task_id") or "task"
    category = wakeup_candidate_category(candidate)
    status = candidate.get("status") or "unknown"
    return f"task:{task_id}:{category}:{status}"


def started_wakeup_candidate_marker(candidate: dict[str, Any], wakeup_key: str) -> dict[str, Any]:
    marker = {
        "task_id": candidate.get("task_id"),
        "status": candidate.get("status"),
        "wakeup_key": wakeup_key,
    }
    if candidate.get("escalation_type"):
        marker["escalation_type"] = candidate.get("escalation_type")
    elif candidate.get("category"):
        marker["category"] = candidate.get("category")
    return marker


def wakeup_has_started(events: list[dict[str, Any]], wakeup_key: str) -> bool:
    for event in events:
        if event.get("event_type") != "wakeup.started":
            continue
        payload = event.get("payload")
        if isinstance(payload, dict) and payload.get("wakeup_key") == wakeup_key:
            return True
    return False


def build_leader_prompt(project: Path, plan: dict[str, Any], wakeup_key: str) -> str:
    candidate = plan.get("candidate") if isinstance(plan.get("candidate"), dict) else {}
    refs = candidate.get("source_refs") if isinstance(candidate.get("source_refs"), list) else []
    ref_lines = "\n".join(f"- {ref}" for ref in refs) if refs else "- .labline/runtime/"
    counts = json.dumps(plan.get("summary_counts") or {}, ensure_ascii=False, sort_keys=True)
    metrics = json.dumps(plan.get("summary_metrics") or {}, ensure_ascii=False, sort_keys=True)
    category = wakeup_candidate_category(candidate)
    phase_boundary_context = ""
    if category == PHASE_BOUNDARY_READY_ESCALATION:
        evidence = {
            key: candidate[key]
            for key in PHASE_BOUNDARY_CONTEXT_KEYS
            if key in candidate
        }
        evidence_text = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)
        phase_boundary_context = (
            "## Phase-Boundary Ready Context\n"
            "This is a `phase_boundary_ready` wakeup for a `ready_to_continue` Runtime Task. "
            "It is not a human approval request.\n"
            "Inspect the evidence, choose the next Leader orchestration outcome, and do not auto-launch high-cost, remote, deployment, or training work from readiness alone.\n\n"
            "Machine-readable context:\n"
            "```json\n"
            f"{evidence_text}\n"
            "```\n\n"
        )
        instructions = (
            "## Instructions\n"
            "- Read the project runtime state under `.labline/runtime/` before acting.\n"
            "- Treat this as a clean phase-boundary continuation, not as failure recovery or a human approval request.\n"
            "- Inspect the machine-readable evidence and choose the next Leader orchestration outcome: next role, next gate, next checkpoint, or a separate human-decision Runtime Task.\n"
            "- Do not auto-launch high-cost, remote, deployment, SSH, or training work from readiness alone.\n"
            "- After recording the next orchestration outcome, consume this phase-boundary task by making it terminal, and represent any follow-up work as a new Runtime Task.\n"
            "- Record any project-state change through Labline runtime events or task updates.\n"
            "- Write the user-facing final answer in Chinese. Keep code identifiers, paths, task ids, and literal status values unchanged, but explain every decision and required action in Chinese.\n"
            "- Do not emit an English-only final decision such as `Decision` / `Required action`; use concise Chinese headings instead.\n"
            "- 面向飞书用户的最终回复必须使用中文；不要只输出英文监控结论。可以保留英文状态值、路径和任务 id，但需要用中文解释含义和下一步。\n"
        )
    else:
        instructions = (
            "## Instructions\n"
            "- Read the project runtime state under `.labline/runtime/` before acting.\n"
            "- Do not rely on Feishu chat history or private remote identities.\n"
            "- Decide whether the task should continue, stop, ask the user, or record a terminal result.\n"
            "- Record any project-state change through Labline runtime events or task updates.\n"
            "- If a later task or artifact has replaced this task, append a machine-readable `task.superseded` or `task.resolved_by` runtime event for the old task. Include `resolved_by_task_id` and a concise `reason` in the event payload so runtime summaries stop counting the old blocker as active.\n"
            "- Write the user-facing final answer in Chinese. Keep code identifiers, paths, task ids, and literal status values unchanged, but explain every decision and required action in Chinese.\n"
            "- Do not emit an English-only final decision such as `Decision` / `Required action`; use concise Chinese headings instead.\n"
            "- 面向飞书用户的最终回复必须使用中文；不要只输出英文监控结论。可以保留英文状态值、路径和任务 id，但需要用中文解释含义和下一步。\n"
        )
    return (
        "# Labline Auto-Wakeup Leader Turn\n\n"
        f"Project: {project}\n"
        f"Wakeup key: {wakeup_key}\n"
        f"Task: {candidate.get('task_id') or 'unknown'}\n"
        f"Title: {candidate.get('title') or 'unknown'}\n"
        f"Status: {candidate.get('status') or 'unknown'}\n"
        f"Category: {category}\n"
        f"Reason: {candidate.get('reason') or plan.get('reason') or 'unknown'}\n"
        f"Runtime summary counts: {counts}\n\n"
        f"Runtime summary metrics: {metrics}\n\n"
        "## Relevant Runtime References\n"
        f"{ref_lines}\n\n"
        f"{phase_boundary_context}"
        f"{instructions}"
    )


def write_wakeup_prompt(project: Path, wakeup_id: str, wakeup_key: str, plan: dict[str, Any]) -> Path:
    root = init_runtime_root(project)
    path = root / "wakeups" / f"{safe_filename(wakeup_key)}-{safe_filename(wakeup_id)}.md"
    atomic_write_text(path, build_leader_prompt(project, plan, wakeup_key))
    return path


def append_wakeup_skipped(project: Path, result: dict[str, Any]) -> None:
    reason = result.get("reason")
    if reason == "healthy_or_no_escalation":
        return
    candidate = result.get("candidate") if isinstance(result.get("candidate"), dict) else {}
    task_id = str(candidate.get("task_id") or "") or None
    append_runtime_event(project, "wakeup.skipped", task_id=task_id, payload=result)


def append_wakeup_retry_requested(project: Path, plan: dict[str, Any], wakeup_key: str, owner: str, now_stamp: str) -> None:
    candidate = plan.get("candidate") if isinstance(plan.get("candidate"), dict) else {}
    payload = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "generated_at": now_stamp,
        "owner": owner,
        "force": True,
        "force_reason": plan.get("force_reason") or "user_requested_retry",
        "wakeup_key": wakeup_key,
        "candidate": candidate,
        "forced_started_candidates": plan.get("forced_started_candidates") or [],
    }
    task_id = str(candidate.get("task_id") or "") or None
    append_runtime_event(project, "wakeup.retry_requested", task_id=task_id, payload=payload)


def normalize_wakeup_backend(value: str | None) -> str:
    if value in {None, "prompt-only", "prompt_only"}:
        return "prompt_only"
    return str(value)


def wakeup_output_path(project: Path, wakeup_id: str, suffix: str) -> Path:
    root = init_runtime_root(project)
    return root / "wakeups" / f"{safe_filename(wakeup_id)}.{suffix}"


def transport_output_path(project: Path, transport_id: str, suffix: str) -> Path:
    root = init_runtime_root(project)
    return root / "transports" / f"{safe_filename(transport_id)}.{suffix}"


def runtime_job_record_path(project: Path, job_id: str) -> Path:
    root = init_runtime_root(project)
    return root / "jobs" / f"{safe_filename(job_id)}.json"


def runtime_agent_status_path(project: Path, agent_id: str) -> Path:
    root = init_runtime_root(project)
    return root / "agents" / f"{safe_filename(agent_id)}.json"


CODEX_SANDBOX_MODES = {"read-only", "workspace-write", "danger-full-access"}


def native_codex_sandbox(args: argparse.Namespace) -> str:
    sandbox = getattr(args, "codex_sandbox", None) or os.environ.get("LABLINE_AUTO_WAKEUP_CODEX_SANDBOX") or "danger-full-access"
    if sandbox not in CODEX_SANDBOX_MODES:
        raise ValueError(f"invalid codex sandbox mode: {sandbox}")
    return sandbox


def native_codex_command(args: argparse.Namespace, project: Path, prompt: str, output_path: Path) -> list[str]:
    command = [getattr(args, "codex_bin", None) or "codex", "exec", "-s", native_codex_sandbox(args), "-C", str(project)]
    profile = getattr(args, "codex_profile", None)
    if profile:
        command.extend(["-p", profile])
    command.extend(["-o", str(output_path), "-"])
    return command


def native_codex_env() -> dict[str, str]:
    env = os.environ.copy()
    mappings = [
        ("LABLINE_AGENT_HTTP_PROXY", "http_proxy", "HTTP_PROXY"),
        ("LABLINE_AGENT_HTTPS_PROXY", "https_proxy", "HTTPS_PROXY"),
        ("LABLINE_AGENT_ALL_PROXY", "all_proxy", "ALL_PROXY"),
        ("LABLINE_AGENT_NO_PROXY", "no_proxy", "NO_PROXY"),
    ]
    for source, lower, upper in mappings:
        value = os.environ.get(source)
        if value:
            env[lower] = value
            env[upper] = value
    return env


def run_native_codex_backend(args: argparse.Namespace, project: Path, wakeup_id: str, prompt_path: Path) -> dict[str, Any]:
    output_path = wakeup_output_path(project, wakeup_id, "native-codex.txt")
    stdout_path = wakeup_output_path(project, wakeup_id, "native-codex.stdout.txt")
    stderr_path = wakeup_output_path(project, wakeup_id, "native-codex.stderr.txt")
    prompt = prompt_path.read_text(encoding="utf-8")
    command = native_codex_command(args, project, prompt, output_path)
    timeout = getattr(args, "codex_timeout", None) or 600
    sandbox = native_codex_sandbox(args)
    profile = getattr(args, "codex_profile", None)
    recorded_command = [command[0], "exec", "-s", sandbox, "-C", str(project)]
    if profile:
        recorded_command.extend(["-p", profile])
    recorded_command.extend(["-o", rel_ref(project, output_path), "<prompt>"])
    result: dict[str, Any] = {
        "command": recorded_command,
        "output_ref": rel_ref(project, output_path),
        "stdout_ref": rel_ref(project, stdout_path),
        "stderr_ref": rel_ref(project, stderr_path),
        "sandbox": sandbox,
        "timeout_seconds": timeout,
    }
    try:
        completed = subprocess.run(
            command,
            cwd=str(project),
            env=native_codex_env(),
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        atomic_write_text(stdout_path, completed.stdout)
        atomic_write_text(stderr_path, completed.stderr)
        result["returncode"] = completed.returncode
        result["status"] = "completed" if completed.returncode == 0 else "failed"
        return result
    except subprocess.TimeoutExpired as exc:
        atomic_write_text(stdout_path, exc.stdout if isinstance(exc.stdout, str) else "")
        atomic_write_text(stderr_path, exc.stderr if isinstance(exc.stderr, str) else "")
        result["returncode"] = None
        result["status"] = "failed"
        result["timed_out"] = True
        result["error"] = f"native codex timed out after {timeout}s"
        return result
    except OSError as exc:
        atomic_write_text(stdout_path, "")
        atomic_write_text(stderr_path, str(exc))
        result["returncode"] = None
        result["status"] = "failed"
        result["error"] = str(exc)
        return result


def resolve_project_relative_path(project: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project / path


def recorded_native_codex_command(args: argparse.Namespace, project: Path, output_path: Path) -> list[str]:
    sandbox = native_codex_sandbox(args)
    profile = getattr(args, "codex_profile", None)
    recorded = [getattr(args, "codex_bin", None) or "codex", "exec", "-s", sandbox, "-C", str(project)]
    if profile:
        recorded.extend(["-p", profile])
    recorded.extend(["-o", rel_ref(project, output_path), "<prompt>"])
    return recorded


def run_native_codex_prompt(args: argparse.Namespace, project: Path, prompt_path: Path, output_path: Path, stdout_path: Path, stderr_path: Path) -> dict[str, Any]:
    prompt = prompt_path.read_text(encoding="utf-8")
    command = native_codex_command(args, project, prompt, output_path)
    timeout = getattr(args, "codex_timeout", None) or 600
    result: dict[str, Any] = {
        "command": recorded_native_codex_command(args, project, output_path),
        "output_ref": rel_ref(project, output_path),
        "stdout_ref": rel_ref(project, stdout_path),
        "stderr_ref": rel_ref(project, stderr_path),
        "sandbox": native_codex_sandbox(args),
        "timeout_seconds": timeout,
    }
    try:
        completed = subprocess.run(
            command,
            cwd=str(project),
            env=native_codex_env(),
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        atomic_write_text(stdout_path, completed.stdout)
        atomic_write_text(stderr_path, completed.stderr)
        result["returncode"] = completed.returncode
        result["status"] = "completed" if completed.returncode == 0 else "failed"
        return result
    except subprocess.TimeoutExpired as exc:
        atomic_write_text(stdout_path, exc.stdout if isinstance(exc.stdout, str) else "")
        atomic_write_text(stderr_path, exc.stderr if isinstance(exc.stderr, str) else "")
        result["returncode"] = None
        result["status"] = "failed"
        result["timed_out"] = True
        result["error"] = f"native codex timed out after {timeout}s"
        return result
    except OSError as exc:
        atomic_write_text(stdout_path, "")
        atomic_write_text(stderr_path, str(exc))
        result["returncode"] = None
        result["status"] = "failed"
        result["error"] = str(exc)
        return result


def write_foreground_agent_status(
    project: Path,
    *,
    agent_id: str,
    role: str,
    status: str,
    task_title: str,
    current_action: str,
    next_expected_update: str | None,
    next_check_reason: str,
    job_handle: dict[str, Any],
    artifacts: list[str],
    blocker: str | None,
    prompt_ref: str,
    trace_path: str,
    last_updated: str,
    review_independence: str,
) -> Path:
    terminal = status in {"blocked", "done", "failed"}
    snapshot = {
        "schema_version": 1,
        "agent_id": agent_id,
        "role": role,
        "status": status,
        "task": task_title,
        "last_updated": last_updated,
        "current_action": current_action,
        "next_expected_update": None if terminal else next_expected_update,
        "next_check_reason": "terminal" if terminal else next_check_reason,
        "job_handles": [job_handle],
        "artifacts": artifacts,
        "blocker": blocker,
        "transport": "cli_session",
        "review_independence": review_independence,
        "input_scope": [prompt_ref],
        "trace_path": trace_path,
    }
    path = runtime_agent_status_path(project, agent_id)
    atomic_write_json(path, snapshot)
    return path


def write_tmux_agent_status(
    project: Path,
    *,
    agent_id: str,
    role: str,
    status: str,
    task_title: str,
    current_action: str,
    next_expected_update: str | None,
    next_check_reason: str,
    job_handle: dict[str, Any],
    artifacts: list[str],
    blocker: str | None,
    last_updated: str,
) -> Path:
    terminal = status in {"blocked", "done", "failed"}
    snapshot = {
        "schema_version": 1,
        "agent_id": agent_id,
        "role": role,
        "status": status,
        "task": task_title,
        "last_updated": last_updated,
        "current_action": current_action,
        "next_expected_update": None if terminal else next_expected_update,
        "next_check_reason": "terminal" if terminal else next_check_reason,
        "job_handles": [job_handle],
        "artifacts": artifacts,
        "blocker": blocker,
        "transport": "tmux",
        "trace_path": job_handle.get("job_ref"),
    }
    path = runtime_agent_status_path(project, agent_id)
    atomic_write_json(path, snapshot)
    return path


def missing_task_artifacts(project: Path, task: dict[str, Any]) -> list[str]:
    required_artifacts = task.get("required_artifacts") if isinstance(task.get("required_artifacts"), list) else []
    return [str(artifact) for artifact in required_artifacts if not task_artifact_path(project, str(artifact)).exists()]


def foreground_review_task_update_args(
    project: Path,
    task: dict[str, Any],
    *,
    status: str,
    current_action: str,
    next_expected_update: str | None,
    next_check_reason: str,
    job_handle: dict[str, Any],
    artifacts: list[str],
    verdict_artifact: str,
    blocker: str | None,
) -> argparse.Namespace:
    durability = task.get("durability") or "supervised"
    if durability == "ephemeral":
        durability = "supervised"
    heartbeat = task.get("heartbeat") or "escalation_gated"
    if heartbeat == "none" and status not in TERMINAL_TASK_STATUSES:
        heartbeat = "escalation_gated"
    return argparse.Namespace(
        project=project,
        task_id=task["task_id"],
        kind=task.get("kind") or "agent",
        title=task.get("title") or task["task_id"],
        owner=task.get("owner") or "Reviewer",
        parent_task_id=task.get("parent_task_id"),
        execution_mode=task.get("execution_mode") or "agent_turn",
        durability=durability,
        observation=task.get("observation") or "enabled",
        heartbeat=heartbeat,
        status=status,
        current_action=current_action,
        next_expected_update=next_expected_update,
        next_check_reason=next_check_reason,
        job_handle=[json.dumps(job_handle, ensure_ascii=False)],
        artifact=artifacts,
        required_artifact=[],
        verdict_artifact=verdict_artifact,
        retry_of=None,
        supersedes=None,
        blocker=blocker,
    )


def run_foreground_review(args: argparse.Namespace) -> dict[str, Any]:
    project = resolve_project(getattr(args, "project", None))
    now = parse_utc(getattr(args, "now", None))
    now_stamp = format_utc(now)
    task = load_task(project, args.task_id)
    prompt_path = resolve_project_relative_path(project, args.prompt_file)
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt file not found: {prompt_path}")
    verdict_artifact = getattr(args, "verdict_artifact", None) or task.get("verdict_artifact")
    if not verdict_artifact:
        raise ValueError("foreground-review requires --verdict-artifact")

    timeout = getattr(args, "codex_timeout", None) or 600
    next_expected_update = (
        getattr(args, "next_expected_update", None)
        or task.get("next_expected_update")
        or format_utc(now + timedelta(seconds=timeout + 300))
    )
    next_check_reason = (
        getattr(args, "next_check_reason", None)
        or task.get("next_check_reason")
        or "foreground cli_session transport deadline"
    )
    agent_id = str(getattr(args, "agent_id", None) or task.get("owner") or args.task_id)
    derived_agent_task_id = f"agent:{agent_id}"
    if safe_filename(str(task["task_id"])) == safe_filename(derived_agent_task_id):
        raise ValueError(
            "foreground-review task_id collides with derived agent-status task id; "
            f"use a non-colliding Runtime Task id such as task-{agent_id}"
        )
    role = str(getattr(args, "role", None) or task.get("owner") or "Reviewer")
    review_independence = getattr(args, "review_independence", None) or "fresh_original_inputs"
    transport_id = "transport_" + uuid.uuid4().hex
    output_path = transport_output_path(project, transport_id, "codex.txt")
    stdout_path = transport_output_path(project, transport_id, "codex.stdout.txt")
    stderr_path = transport_output_path(project, transport_id, "codex.stderr.txt")
    prompt_ref = rel_ref(project, prompt_path)
    task_path = runtime_task_path(init_runtime_root(project), str(task["task_id"]))
    trace_path = rel_ref(project, task_path)
    job_handle = {
        "type": "cli_session",
        "backend": "codex_exec",
        "transport_id": transport_id,
        "task_id": str(task["task_id"]),
        "agent_id": agent_id,
        "prompt_ref": prompt_ref,
        "output_ref": rel_ref(project, output_path),
        "stdout_ref": rel_ref(project, stdout_path),
        "stderr_ref": rel_ref(project, stderr_path),
        "started_at": now_stamp,
        "timeout_seconds": timeout,
    }

    running_action = "foreground review transport running"
    running_task = update_task(
        foreground_review_task_update_args(
            project,
            task,
            status="running",
            current_action=running_action,
            next_expected_update=next_expected_update,
            next_check_reason=next_check_reason,
            job_handle=job_handle,
            artifacts=[],
            verdict_artifact=str(verdict_artifact),
            blocker=None,
        )
    )
    write_foreground_agent_status(
        project,
        agent_id=agent_id,
        role=role,
        status="running",
        task_title=str(running_task.get("title") or running_task["task_id"]),
        current_action=running_action,
        next_expected_update=next_expected_update,
        next_check_reason=next_check_reason,
        job_handle=job_handle,
        artifacts=[],
        blocker=None,
        prompt_ref=prompt_ref,
        trace_path=trace_path,
        last_updated=now_stamp,
        review_independence=review_independence,
    )
    started_payload = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "transport": "cli_session",
        "transport_id": transport_id,
        "task_id": str(task["task_id"]),
        "agent_id": agent_id,
        "started_at": now_stamp,
        "job_handle": job_handle,
    }
    append_runtime_event(project, "transport.started", task_id=str(task["task_id"]), payload=started_payload)

    codex_result = run_native_codex_prompt(args, project, prompt_path, output_path, stdout_path, stderr_path)
    verdict_exists = task_artifact_path(project, str(verdict_artifact)).exists()
    latest_task = load_task(project, str(task["task_id"]))
    missing_required = missing_task_artifacts(project, latest_task)
    completed_at = format_utc(parse_utc(getattr(args, "now", None)))
    codex_ok = codex_result.get("status") == "completed"
    if codex_ok and verdict_exists and not missing_required:
        artifacts = [str(verdict_artifact)]
        final = {
            "action": "completed",
            "status": "completed",
            "transport": "cli_session",
            "transport_id": transport_id,
            "task_id": str(task["task_id"]),
            "agent_id": agent_id,
            "started_at": now_stamp,
            "completed_at": completed_at,
            "prompt_ref": prompt_ref,
            "verdict_ref": str(verdict_artifact),
            "job_handle": job_handle,
            "codex": codex_result,
        }
        append_runtime_event(project, "transport.completed", task_id=str(task["task_id"]), payload=final)
        final_task = update_task(
            foreground_review_task_update_args(
                project,
                latest_task,
                status="completed",
                current_action="foreground review completed; verdict artifact present",
                next_expected_update=next_expected_update,
                next_check_reason=next_check_reason,
                job_handle=job_handle,
                artifacts=artifacts,
                verdict_artifact=str(verdict_artifact),
                blocker=None,
            ),
            event_type="task.completed",
        )
        final["task"] = final_task
        write_foreground_agent_status(
            project,
            agent_id=agent_id,
            role=role,
            status="done",
            task_title=str(final_task.get("title") or final_task["task_id"]),
            current_action="foreground review completed; verdict artifact present",
            next_expected_update=next_expected_update,
            next_check_reason=next_check_reason,
            job_handle=job_handle,
            artifacts=artifacts,
            blocker=None,
            prompt_ref=prompt_ref,
            trace_path=trace_path,
            last_updated=completed_at,
            review_independence=review_independence,
        )
        return final

    if not codex_ok:
        failure_type = "CODEX_EXECUTION_FAILURE"
        blocker = f"CODEX_EXECUTION_FAILURE: codex exec failed with returncode={codex_result.get('returncode')}"
    elif not verdict_exists:
        failure_type = "NO_VERDICT_EXECUTION_FAILURE"
        blocker = f"NO_VERDICT_EXECUTION_FAILURE: codex exec completed but missing verdict artifact: {verdict_artifact}"
    else:
        failure_type = "REQUIRED_ARTIFACT_MISSING"
        blocker = f"REQUIRED_ARTIFACT_MISSING: {', '.join(missing_required)}"
    artifacts = [str(verdict_artifact)] if verdict_exists else []
    final = {
        "action": "failed",
        "status": "failed",
        "failure_type": failure_type,
        "blocker": blocker,
        "transport": "cli_session",
        "transport_id": transport_id,
        "task_id": str(task["task_id"]),
        "agent_id": agent_id,
        "started_at": now_stamp,
        "completed_at": completed_at,
        "prompt_ref": prompt_ref,
        "verdict_ref": str(verdict_artifact),
        "job_handle": job_handle,
        "codex": codex_result,
    }
    append_runtime_event(project, "transport.failed", task_id=str(task["task_id"]), payload=final)
    failed_task = update_task(
        foreground_review_task_update_args(
            project,
            latest_task,
            status="failed",
            current_action="foreground review failed; terminal artifact gate not satisfied",
            next_expected_update=next_expected_update,
            next_check_reason=next_check_reason,
            job_handle=job_handle,
            artifacts=artifacts,
            verdict_artifact=str(verdict_artifact),
            blocker=blocker,
        ),
        event_type="task.failed",
    )
    final["task"] = failed_task
    write_foreground_agent_status(
        project,
        agent_id=agent_id,
        role=role,
        status="failed",
        task_title=str(failed_task.get("title") or failed_task["task_id"]),
        current_action="foreground review failed; terminal artifact gate not satisfied",
        next_expected_update=next_expected_update,
        next_check_reason=next_check_reason,
        job_handle=job_handle,
        artifacts=artifacts,
        blocker=blocker,
        prompt_ref=prompt_ref,
        trace_path=trace_path,
        last_updated=completed_at,
        review_independence=review_independence,
    )
    return final


def tmux_job_update_args(
    project: Path,
    task: dict[str, Any],
    *,
    status: str,
    current_action: str,
    next_expected_update: str | None,
    next_check_reason: str,
    job_handle: dict[str, Any],
    artifacts: list[str],
    required_artifacts: list[str],
    blocker: str | None,
) -> argparse.Namespace:
    heartbeat = task.get("heartbeat") or "escalation_gated"
    if heartbeat == "none" and status not in TERMINAL_TASK_STATUSES:
        heartbeat = "escalation_gated"
    return argparse.Namespace(
        project=project,
        task_id=task["task_id"],
        kind=task.get("kind") or "agent",
        title=task.get("title") or task["task_id"],
        owner=task.get("owner") or "Deployer",
        parent_task_id=task.get("parent_task_id"),
        execution_mode="detached_job",
        durability="supervised",
        observation=task.get("observation") or "enabled",
        heartbeat=heartbeat,
        status=status,
        current_action=current_action,
        next_expected_update=next_expected_update,
        next_check_reason=next_check_reason,
        job_handle=[json.dumps(job_handle, ensure_ascii=False)] if job_handle else [],
        artifact=artifacts,
        required_artifact=required_artifacts,
        verdict_artifact=None,
        retry_of=None,
        supersedes=None,
        blocker=blocker,
    )


def start_tmux_job(args: argparse.Namespace) -> dict[str, Any]:
    project = resolve_project(getattr(args, "project", None))
    now = parse_utc(getattr(args, "now", None))
    now_stamp = format_utc(now)
    task = load_task(project, args.task_id)
    agent_id = str(getattr(args, "agent_id", None) or task.get("owner") or args.task_id)
    derived_agent_task_id = f"agent:{agent_id}"
    if safe_filename(str(task["task_id"])) == safe_filename(derived_agent_task_id):
        raise ValueError(
            "tmux-job task_id collides with derived agent-status task id; "
            f"use a non-colliding Runtime Task id such as task-{agent_id}"
        )
    session = str(getattr(args, "session", None) or "")
    if not session:
        raise ValueError("tmux-job requires --session")
    command = str(getattr(args, "command", None) or "")
    if not command:
        raise ValueError("tmux-job requires --command")
    tmux_bin = getattr(args, "tmux_bin", None) or "tmux"
    log_ref = str(getattr(args, "log", None) or f".labline/runtime/jobs/{safe_filename(session)}.log")
    log_path = resolve_project_relative_path(project, log_ref)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    required_artifacts = list(getattr(args, "required_artifact", None) or [])
    if not required_artifacts:
        required_artifacts = [str(item) for item in task.get("required_artifacts", []) if item]
    next_expected_update = (
        getattr(args, "next_expected_update", None)
        or task.get("next_expected_update")
        or format_utc(now + timedelta(minutes=30))
    )
    next_check_reason = (
        getattr(args, "next_check_reason", None)
        or task.get("next_check_reason")
        or "tmux job heartbeat deadline"
    )
    current_action = getattr(args, "current_action", None) or f"tmux job running in session {session}"
    role = str(getattr(args, "role", None) or task.get("owner") or "Deployer")
    title = str(getattr(args, "title", None) or task.get("title") or task["task_id"])

    existing = subprocess.run([tmux_bin, "has-session", "-t", session], cwd=str(project), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if existing.returncode == 0:
        raise ValueError(f"tmux session already exists: {session}")

    job_id = "job_" + uuid.uuid4().hex
    job_path = runtime_job_record_path(project, job_id)
    exit_code_path = job_path.with_suffix(".exitcode")
    job_handle = {
        "type": "tmux",
        "backend": "tmux",
        "job_id": job_id,
        "task_id": str(task["task_id"]),
        "agent_id": agent_id,
        "session": session,
        "log_ref": rel_ref(project, log_path),
        "job_ref": rel_ref(project, job_path),
        "exit_code_ref": rel_ref(project, exit_code_path),
        "started_at": now_stamp,
    }
    wrapped_command = (
        "set -o pipefail; "
        f"mkdir -p {shlex.quote(str(log_path.parent))} {shlex.quote(str(exit_code_path.parent))}; "
        f"{{ {command}; }} 2>&1 | tee -a {shlex.quote(str(log_path))}; "
        "rc=${PIPESTATUS[0]}; "
        f"printf '%s\\n' \"$rc\" > {shlex.quote(str(exit_code_path))}; "
        'exit "$rc"'
    )
    tmux_command = f"bash -lc {shlex.quote(wrapped_command)}"
    launched = subprocess.run(
        [tmux_bin, "new-session", "-d", "-s", session, tmux_command],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if launched.returncode != 0:
        blocker = f"TMUX_LAUNCH_FAILED: {launched.stderr.strip() or launched.stdout.strip() or 'tmux new-session failed'}"
        job_record = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "job_id": job_id,
            "task_id": str(task["task_id"]),
            "agent_id": agent_id,
            "status": "failed",
            "backend": "tmux",
            "session": session,
            "command": command,
            "wrapped_command": wrapped_command,
            "log_ref": rel_ref(project, log_path),
            "exit_code_ref": rel_ref(project, exit_code_path),
            "started_at": now_stamp,
            "failed_at": format_utc(parse_utc(getattr(args, "now", None))),
            "blocker": blocker,
            "required_artifacts": required_artifacts,
        }
        atomic_write_json(job_path, job_record)
        failed_task = update_task(
            tmux_job_update_args(
                project,
                task,
                status="failed",
                current_action="tmux job failed to launch",
                next_expected_update=next_expected_update,
                next_check_reason=next_check_reason,
                job_handle=job_handle,
                artifacts=[],
                required_artifacts=required_artifacts,
                blocker=blocker,
            ),
            event_type="task.failed",
        )
        write_tmux_agent_status(
            project,
            agent_id=agent_id,
            role=role,
            status="failed",
            task_title=title,
            current_action="tmux job failed to launch",
            next_expected_update=next_expected_update,
            next_check_reason=next_check_reason,
            job_handle=job_handle,
            artifacts=[],
            blocker=blocker,
            last_updated=now_stamp,
        )
        result = {
            "action": "failed",
            "status": "failed",
            "failure_type": "TMUX_LAUNCH_FAILED",
            "blocker": blocker,
            "task_id": str(task["task_id"]),
            "agent_id": agent_id,
            "session": session,
            "job_id": job_id,
            "job_ref": rel_ref(project, job_path),
            "job_handle": job_handle,
            "returncode": launched.returncode,
            "task": failed_task,
        }
        append_runtime_event(project, "job.failed", task_id=str(task["task_id"]), payload=result)
        return result

    job_record = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "job_id": job_id,
        "task_id": str(task["task_id"]),
        "agent_id": agent_id,
        "status": "running",
        "backend": "tmux",
        "session": session,
        "command": command,
        "wrapped_command": wrapped_command,
        "log_ref": rel_ref(project, log_path),
        "exit_code_ref": rel_ref(project, exit_code_path),
        "started_at": now_stamp,
        "required_artifacts": required_artifacts,
    }
    atomic_write_json(job_path, job_record)
    updated_task = update_task(
        tmux_job_update_args(
            project,
            task,
            status="waiting_on_job",
            current_action=current_action,
            next_expected_update=next_expected_update,
            next_check_reason=next_check_reason,
            job_handle=job_handle,
            artifacts=[],
            required_artifacts=required_artifacts,
            blocker=None,
        )
    )
    write_tmux_agent_status(
        project,
        agent_id=agent_id,
        role=role,
        status="waiting_on_job",
        task_title=title,
        current_action=current_action,
        next_expected_update=next_expected_update,
        next_check_reason=next_check_reason,
        job_handle=job_handle,
        artifacts=[],
        blocker=None,
        last_updated=now_stamp,
    )
    result = {
        "action": "started",
        "status": "waiting_on_job",
        "transport": "tmux",
        "job_id": job_id,
        "task_id": str(task["task_id"]),
        "agent_id": agent_id,
        "session": session,
        "log_ref": rel_ref(project, log_path),
        "job_ref": rel_ref(project, job_path),
        "job_handle": job_handle,
        "task": updated_task,
    }
    append_runtime_event(project, "job.started", task_id=str(task["task_id"]), payload=result)
    return result


def release_wakeup_lease(project: Path, owner: str, result: dict[str, Any]) -> None:
    try:
        release_lease(argparse.Namespace(project=project, lease_id="leader_session", owner=owner))
    except (FileNotFoundError, ValueError) as exc:
        result["lease_release_error"] = str(exc)


def run_wakeup(args: argparse.Namespace) -> dict[str, Any]:
    project = resolve_project(getattr(args, "project", None))
    root = runtime_root(project)
    now = parse_utc(getattr(args, "now", None))
    now_stamp = format_utc(now)
    owner = getattr(args, "owner", None) or "labline-wakeup"
    lease_ttl = getattr(args, "lease_ttl", None) or 600
    backend = normalize_wakeup_backend(getattr(args, "backend", None))
    plan = build_wakeup_plan(args)
    base = {**plan, "dry_run": False, "backend": backend}

    if plan.get("action") != "acquire_lease":
        result = {**base, "action": plan.get("action"), "reason": plan.get("reason")}
        append_wakeup_skipped(project, result)
        return result

    candidate = plan.get("candidate") if isinstance(plan.get("candidate"), dict) else {}
    wakeup_key = candidate_wakeup_key(candidate)
    events = iter_runtime_events(root)
    started_before = wakeup_has_started(events, wakeup_key)
    force = bool(plan.get("force"))
    if started_before and not force:
        result = {
            **base,
            "action": "skip",
            "reason": "wakeup_already_started",
            "wakeup_key": wakeup_key,
        }
        append_wakeup_skipped(project, result)
        return result
    if started_before and force:
        append_wakeup_retry_requested(project, plan, wakeup_key, owner, now_stamp)

    try:
        lease = acquire_lease(
            argparse.Namespace(
                project=project,
                lease_id="leader_session",
                owner=owner,
                ttl=lease_ttl,
                purpose=f"auto wakeup for {candidate.get('task_id') or 'runtime'}",
                now=now_stamp,
            )
        )
    except ValueError as exc:
        result = {
            **base,
            "action": "skip",
            "reason": "lease_unavailable",
            "detail": str(exc),
            "wakeup_key": wakeup_key,
        }
        append_wakeup_skipped(project, result)
        return result

    wakeup_id = "wakeup_" + uuid.uuid4().hex
    prompt_path = write_wakeup_prompt(project, wakeup_id, wakeup_key, plan)
    result = {
        **base,
        "action": "started",
        "status": "queued",
        "started_at": now_stamp,
        "wakeup_id": wakeup_id,
        "wakeup_key": wakeup_key,
        "leader_prompt_ref": rel_ref(project, prompt_path),
        "lease": lease,
    }
    task_id = str(candidate.get("task_id") or "") or None
    append_runtime_event(project, "wakeup.started", task_id=task_id, payload=result)
    if backend == "prompt_only":
        return result

    if backend == "native-codex":
        codex_result = run_native_codex_backend(args, project, wakeup_id, prompt_path)
        final_action = "completed" if codex_result.get("status") == "completed" else "failed"
        final = {
            **result,
            "action": final_action,
            "status": final_action,
            "completed_at": format_utc(parse_utc(getattr(args, "now", None))),
            "codex": codex_result,
        }
        append_runtime_event(project, f"wakeup.{final_action}", task_id=task_id, payload=final)
        release_wakeup_lease(project, owner, final)
        return final

    return result


def cmd_init(args: argparse.Namespace) -> int:
    print(init_runtime_root(getattr(args, "project", None)))
    return 0


def cmd_event_append(args: argparse.Namespace) -> int:
    try:
        payload = parse_event_payload(getattr(args, "json_payload", None))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    path = append_runtime_event(
        getattr(args, "project", None),
        args.event_type,
        task_id=getattr(args, "task_id", None),
        payload=payload,
    )
    print(path)
    return 0


def cmd_task_get(args: argparse.Namespace) -> int:
    try:
        task = load_task(getattr(args, "project", None), args.task_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_task_list(args: argparse.Namespace) -> int:
    print(json.dumps(list_tasks(getattr(args, "project", None)), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def emit_task_or_error(func, args: argparse.Namespace) -> int:
    try:
        task = func(args)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2 if isinstance(exc, ValueError) else 1
    print(json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_task_create(args: argparse.Namespace) -> int:
    return emit_task_or_error(create_task, args)


def cmd_task_update(args: argparse.Namespace) -> int:
    return emit_task_or_error(update_task, args)


def cmd_task_complete(args: argparse.Namespace) -> int:
    args.status = "completed"
    return emit_task_or_error(lambda parsed: update_task(parsed, event_type="task.completed"), args)


def cmd_task_fail(args: argparse.Namespace) -> int:
    args.status = "failed"
    return emit_task_or_error(lambda parsed: update_task(parsed, event_type="task.failed"), args)


def cmd_task_cancel(args: argparse.Namespace) -> int:
    args.status = "cancelled"
    return emit_task_or_error(lambda parsed: update_task(parsed, event_type="task.cancelled"), args)


def cmd_lease_acquire(args: argparse.Namespace) -> int:
    return emit_json_or_error(acquire_lease, args)


def cmd_lease_release(args: argparse.Namespace) -> int:
    return emit_json_or_error(release_lease, args)


def cmd_lease_status(args: argparse.Namespace) -> int:
    return emit_json_or_error(lease_status, args)


def cmd_intent_submit(args: argparse.Namespace) -> int:
    return emit_json_or_error(submit_control_intent, args)


def cmd_heartbeat(args: argparse.Namespace) -> int:
    return emit_json_or_error(run_heartbeat, args)


def cmd_wakeup_plan(args: argparse.Namespace) -> int:
    return emit_json_or_error(build_wakeup_plan, args)


def cmd_wakeup(args: argparse.Namespace) -> int:
    return emit_json_or_error(run_wakeup, args)


def cmd_foreground_review(args: argparse.Namespace) -> int:
    return emit_json_or_error(run_foreground_review, args)


def cmd_tmux_job(args: argparse.Namespace) -> int:
    return emit_json_or_error(start_tmux_job, args)


def cmd_status(args: argparse.Namespace) -> int:
    summary, summary_md = summarize_runtime(getattr(args, "project", None), write=True)
    if getattr(args, "json_output", False):
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(summary_md, end="")
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    return cmd_status(args)


def add_project_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", type=Path)


def add_task_write_args(parser: argparse.ArgumentParser, include_create_required: bool = False) -> None:
    add_project_arg(parser)
    parser.add_argument("--kind", required=include_create_required)
    parser.add_argument("--title", required=include_create_required)
    parser.add_argument("--owner")
    parser.add_argument("--parent-task-id")
    parser.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES))
    parser.add_argument("--durability", choices=sorted(DURABILITY_VALUES))
    parser.add_argument("--observation", choices=sorted(OBSERVATION_VALUES))
    parser.add_argument("--heartbeat", choices=sorted(HEARTBEAT_VALUES))
    parser.add_argument("--status", choices=sorted(TASK_STATUSES))
    parser.add_argument("--current-action")
    parser.add_argument("--next-expected-update")
    parser.add_argument("--next-check-reason")
    parser.add_argument("--job-handle", action="append", default=[])
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--required-artifact", action="append", default=[])
    parser.add_argument("--verdict-artifact")
    parser.add_argument("--retry-of")
    parser.add_argument("--supersedes")
    parser.add_argument("--blocker")


def add_now_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--now")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labline_runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    add_project_arg(init)
    init.set_defaults(func=cmd_init)

    event = sub.add_parser("event")
    event_sub = event.add_subparsers(dest="event_command", required=True)
    event_append = event_sub.add_parser("append")
    add_project_arg(event_append)
    event_append.add_argument("--type", dest="event_type", required=True)
    event_append.add_argument("--task-id")
    event_append.add_argument("--json", dest="json_payload")
    event_append.set_defaults(func=cmd_event_append)

    task = sub.add_parser("task")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_get = task_sub.add_parser("get")
    add_project_arg(task_get)
    task_get.add_argument("task_id")
    task_get.set_defaults(func=cmd_task_get)
    task_list = task_sub.add_parser("list")
    add_project_arg(task_list)
    task_list.set_defaults(func=cmd_task_list)
    task_create = task_sub.add_parser("create")
    task_create.add_argument("task_id")
    add_task_write_args(task_create, include_create_required=True)
    task_create.set_defaults(func=cmd_task_create)
    task_update = task_sub.add_parser("update")
    task_update.add_argument("task_id")
    add_task_write_args(task_update)
    task_update.set_defaults(func=cmd_task_update)
    task_complete = task_sub.add_parser("complete")
    task_complete.add_argument("task_id")
    add_task_write_args(task_complete)
    task_complete.set_defaults(func=cmd_task_complete)
    task_fail = task_sub.add_parser("fail")
    task_fail.add_argument("task_id")
    add_task_write_args(task_fail)
    task_fail.set_defaults(func=cmd_task_fail)
    task_cancel = task_sub.add_parser("cancel")
    task_cancel.add_argument("task_id")
    add_task_write_args(task_cancel)
    task_cancel.set_defaults(func=cmd_task_cancel)

    lease = sub.add_parser("lease")
    lease_sub = lease.add_subparsers(dest="lease_command", required=True)
    lease_acquire = lease_sub.add_parser("acquire")
    add_project_arg(lease_acquire)
    lease_acquire.add_argument("lease_id")
    lease_acquire.add_argument("--owner", required=True)
    lease_acquire.add_argument("--ttl", type=int, required=True)
    lease_acquire.add_argument("--purpose", required=True)
    add_now_arg(lease_acquire)
    lease_acquire.set_defaults(func=cmd_lease_acquire)
    lease_release = lease_sub.add_parser("release")
    add_project_arg(lease_release)
    lease_release.add_argument("lease_id")
    lease_release.add_argument("--owner", required=True)
    lease_release.set_defaults(func=cmd_lease_release)
    lease_status = lease_sub.add_parser("status")
    add_project_arg(lease_status)
    lease_status.add_argument("lease_id", nargs="?")
    add_now_arg(lease_status)
    lease_status.set_defaults(func=cmd_lease_status)

    intent = sub.add_parser("intent")
    intent_sub = intent.add_subparsers(dest="intent_command", required=True)
    intent_submit = intent_sub.add_parser("submit")
    add_project_arg(intent_submit)
    intent_submit.add_argument("--intent-id")
    intent_submit.add_argument("--action", required=True)
    intent_submit.add_argument("--risk-level", required=True, choices=sorted(RISK_LEVELS))
    intent_submit.add_argument("--confirmation-status", required=True, choices=sorted(CONFIRMATION_STATUSES))
    intent_submit.add_argument("--target", default="{}")
    intent_submit.add_argument("--source-entry", default="local")
    intent_submit.add_argument("--archive-ref")
    intent_submit.add_argument("--lease-scope", required=True)
    add_now_arg(intent_submit)
    intent_submit.set_defaults(func=cmd_intent_submit)

    summarize = sub.add_parser("summarize")
    add_project_arg(summarize)
    summarize.add_argument("--json", dest="json_output", action="store_true")
    summarize.add_argument("--brief", action="store_true")
    summarize.set_defaults(func=cmd_summarize)

    status = sub.add_parser("status")
    add_project_arg(status)
    status.add_argument("--json", dest="json_output", action="store_true")
    status.add_argument("--brief", action="store_true")
    status.set_defaults(func=cmd_status)

    heartbeat = sub.add_parser("heartbeat")
    add_project_arg(heartbeat)
    heartbeat.add_argument("--dry-run", action="store_true")
    heartbeat.add_argument("--task", dest="task_id")
    heartbeat.add_argument("--runner", default="local-heartbeat")
    heartbeat.add_argument("--lease-ttl", type=int, default=60)
    heartbeat.add_argument("--force", action="store_true")
    add_now_arg(heartbeat)
    heartbeat.set_defaults(func=cmd_heartbeat)

    workflow = sub.add_parser("workflow")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    wakeup_plan = workflow_sub.add_parser("wakeup-plan")
    add_project_arg(wakeup_plan)
    wakeup_plan.add_argument("--json", dest="json_output", action="store_true")
    wakeup_plan.add_argument("--task", dest="task_id")
    wakeup_plan.add_argument("--owner", default="labline-wakeup")
    wakeup_plan.add_argument("--force", action="store_true")
    add_now_arg(wakeup_plan)
    wakeup_plan.set_defaults(func=cmd_wakeup_plan)
    wakeup = workflow_sub.add_parser("wakeup")
    add_project_arg(wakeup)
    wakeup.add_argument("--json", dest="json_output", action="store_true")
    wakeup.add_argument("--task", dest="task_id")
    wakeup.add_argument("--owner", default="labline-wakeup")
    wakeup.add_argument("--force", action="store_true")
    wakeup.add_argument("--lease-ttl", type=int, default=600)
    wakeup.add_argument("--backend", choices=sorted(WAKEUP_BACKENDS), default="prompt-only")
    wakeup.add_argument("--codex-bin", default="codex")
    wakeup.add_argument("--codex-profile")
    wakeup.add_argument("--codex-sandbox", choices=sorted(CODEX_SANDBOX_MODES))
    wakeup.add_argument("--codex-timeout", type=int, default=600)
    add_now_arg(wakeup)
    wakeup.set_defaults(func=cmd_wakeup)

    foreground_review = workflow_sub.add_parser("foreground-review")
    add_project_arg(foreground_review)
    foreground_review.add_argument("task_id")
    foreground_review.add_argument("--json", dest="json_output", action="store_true")
    foreground_review.add_argument("--agent-id", required=True)
    foreground_review.add_argument("--role", default="Reviewer")
    foreground_review.add_argument("--prompt-file", type=Path, required=True)
    foreground_review.add_argument("--verdict-artifact", required=True)
    foreground_review.add_argument("--review-independence", default="fresh_original_inputs")
    foreground_review.add_argument("--next-expected-update")
    foreground_review.add_argument("--next-check-reason")
    foreground_review.add_argument("--codex-bin", default="codex")
    foreground_review.add_argument("--codex-profile")
    foreground_review.add_argument("--codex-sandbox", choices=sorted(CODEX_SANDBOX_MODES))
    foreground_review.add_argument("--codex-timeout", type=int, default=600)
    add_now_arg(foreground_review)
    foreground_review.set_defaults(func=cmd_foreground_review)

    tmux_job = workflow_sub.add_parser("tmux-job")
    add_project_arg(tmux_job)
    tmux_job.add_argument("task_id")
    tmux_job.add_argument("--json", dest="json_output", action="store_true")
    tmux_job.add_argument("--agent-id", required=True)
    tmux_job.add_argument("--role", default="Deployer")
    tmux_job.add_argument("--title")
    tmux_job.add_argument("--session", required=True)
    tmux_job.add_argument("--command", required=True)
    tmux_job.add_argument("--log", type=Path, required=True)
    tmux_job.add_argument("--current-action")
    tmux_job.add_argument("--next-expected-update")
    tmux_job.add_argument("--next-check-reason")
    tmux_job.add_argument("--required-artifact", action="append")
    tmux_job.add_argument("--tmux-bin", default="tmux")
    add_now_arg(tmux_job)
    tmux_job.set_defaults(func=cmd_tmux_job)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
