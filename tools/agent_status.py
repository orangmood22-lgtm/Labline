#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCHEMA_VERSION = 1
STATUSES = {"starting", "running", "waiting_on_job", "blocked", "done", "failed"}
TERMINAL_STATUSES = {"blocked", "done", "failed"}
TRANSPORTS = {"local_agent", "background_agent", "mcp_codex", "mcp_gemini", "cli_session", "external_api"}
REQUIRED_FIELDS = [
    "schema_version",
    "agent_id",
    "role",
    "status",
    "task",
    "last_updated",
    "current_action",
    "next_expected_update",
    "next_check_reason",
    "job_handles",
    "artifacts",
    "blocker",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str, now: datetime | None = None) -> str:
    now = now or utc_now()
    match = re.fullmatch(r"\+(\d+)([mhd])", value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == "m":
            delta = timedelta(minutes=amount)
        elif unit == "h":
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(days=amount)
        return isoformat(now + delta)
    return value


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def resolve_status_root(args: argparse.Namespace) -> Path:
    if args.status_root:
        return Path(args.status_root)
    project_root = Path(args.project_root or ".")
    return project_root / ".labline" / "runtime"


def resolve_legacy_status_root(args: argparse.Namespace) -> Path:
    project_root = Path(args.project_root or ".")
    return project_root / ".labline" / "status"


def resolve_read_roots(args: argparse.Namespace) -> list[Path]:
    primary = resolve_status_root(args)
    roots = [primary]
    if not args.status_root:
        legacy = resolve_legacy_status_root(args)
        if legacy != primary:
            roots.append(legacy)
    return roots


def agent_file(status_root: Path, agent_id: str) -> Path:
    return status_root / "agents" / f"{agent_id}.json"


def write_snapshot(path: Path, snapshot: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_snapshot(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_json_values(values: list[str]) -> list[dict]:
    parsed = []
    for value in values:
        data = json.loads(value)
        if not isinstance(data, dict):
            raise ValueError("--job-handle must be a JSON object")
        parsed.append(data)
    return parsed


def cmd_start(args: argparse.Namespace) -> int:
    status_root = resolve_status_root(args)
    path = agent_file(status_root, args.agent_id)
    now = utc_now()
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "agent_id": args.agent_id,
        "role": args.role,
        "status": "starting",
        "task": args.task,
        "last_updated": isoformat(now),
        "current_action": args.current_action,
        "next_expected_update": parse_time(args.next_expected_update, now),
        "next_check_reason": args.next_check_reason,
        "job_handles": [],
        "artifacts": [],
        "blocker": None,
    }
    add_optional_metadata(snapshot, args)
    write_snapshot(path, snapshot)
    print(path)
    return 0


def add_optional_metadata(snapshot: dict, args: argparse.Namespace) -> None:
    if getattr(args, "transport", None):
        snapshot["transport"] = args.transport
    if getattr(args, "review_independence", None):
        snapshot["review_independence"] = args.review_independence
    if getattr(args, "input_scope", None):
        snapshot["input_scope"] = args.input_scope
    if getattr(args, "trace_path", None):
        snapshot["trace_path"] = args.trace_path


def cmd_update(args: argparse.Namespace) -> int:
    status_root = resolve_status_root(args)
    path = agent_file(status_root, args.agent_id)
    snapshot = read_snapshot(path)
    now = utc_now()

    if args.status:
        if args.status not in STATUSES:
            raise SystemExit(f"invalid status: {args.status}")
        snapshot["status"] = args.status
    if args.current_action:
        snapshot["current_action"] = args.current_action
    if args.next_expected_update:
        snapshot["next_expected_update"] = parse_time(args.next_expected_update, now)
    if args.next_check_reason:
        snapshot["next_check_reason"] = args.next_check_reason
    if args.job_handle:
        snapshot["job_handles"] = parse_json_values(args.job_handle)
    if args.artifact:
        snapshot["artifacts"] = args.artifact
    add_optional_metadata(snapshot, args)
    snapshot["last_updated"] = isoformat(now)

    write_snapshot(path, snapshot)
    print(path)
    return 0


def cmd_finish(args: argparse.Namespace) -> int:
    if args.status not in TERMINAL_STATUSES:
        raise SystemExit(f"finish status must be one of: {', '.join(sorted(TERMINAL_STATUSES))}")
    status_root = resolve_status_root(args)
    path = agent_file(status_root, args.agent_id)
    snapshot = read_snapshot(path)
    now = utc_now()

    snapshot["status"] = args.status
    snapshot["current_action"] = args.current_action
    snapshot["last_updated"] = isoformat(now)
    snapshot["next_expected_update"] = None
    snapshot["next_check_reason"] = "terminal"
    snapshot["blocker"] = args.blocker
    if args.artifact:
        snapshot["artifacts"] = args.artifact

    write_snapshot(path, snapshot)
    print(path)
    return 0


def iter_snapshots(status_root: Path) -> list[dict]:
    agents_dir = status_root / "agents"
    if not agents_dir.exists():
        return []
    snapshots = []
    for path in sorted(agents_dir.glob("*.json")):
        snapshots.append(read_snapshot(path))
    return snapshots


def iter_snapshots_for_args(args: argparse.Namespace) -> list[dict]:
    by_agent_id: dict[str, dict] = {}
    for root in resolve_read_roots(args):
        for snapshot in iter_snapshots(root):
            agent_id = str(snapshot.get("agent_id") or "")
            if not agent_id:
                continue
            by_agent_id.setdefault(agent_id, snapshot)
    return [by_agent_id[key] for key in sorted(by_agent_id)]


def derived_state(snapshot: dict, now: datetime) -> str:
    status = snapshot.get("status", "")
    if status in TERMINAL_STATUSES:
        return status
    expected = parse_iso(snapshot.get("next_expected_update"))
    if expected and expected < now:
        return "agent_stale_task_alive" if snapshot.get("job_handles") else "agent_stale_task_unknown"
    return status


def cmd_summary(args: argparse.Namespace) -> int:
    now = parse_iso(args.now) if args.now else utc_now()
    assert now is not None
    for snapshot in iter_snapshots_for_args(args):
        state = derived_state(snapshot, now)
        print(
            " ".join(
                [
                    snapshot.get("agent_id", "<missing-agent-id>"),
                    snapshot.get("role", "<missing-role>"),
                    state,
                    snapshot.get("current_action", ""),
                ]
            ).rstrip()
        )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    for snapshot in iter_snapshots_for_args(args):
        print(
            " ".join(
                [
                    snapshot.get("agent_id", "<missing-agent-id>"),
                    snapshot.get("role", "<missing-role>"),
                    snapshot.get("status", "<missing-status>"),
                ]
            )
        )
    return 0


def validate_snapshot(snapshot: dict, filename: str) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in snapshot:
            errors.append(f"{filename}: missing {field}")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{filename}: invalid schema_version={snapshot.get('schema_version')}")
    status = snapshot.get("status")
    if status not in STATUSES:
        errors.append(f"{filename}: invalid status={status}")
    if not isinstance(snapshot.get("job_handles", []), list):
        errors.append(f"{filename}: job_handles must be list")
    if not isinstance(snapshot.get("artifacts", []), list):
        errors.append(f"{filename}: artifacts must be list")
    return errors


def cmd_validate(args: argparse.Namespace) -> int:
    errors = []
    seen_agent_ids: set[str] = set()
    for status_root in resolve_read_roots(args):
        agents_dir = status_root / "agents"
        for path in sorted(agents_dir.glob("*.json")) if agents_dir.exists() else []:
            try:
                snapshot = read_snapshot(path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{path.name}: invalid json: {exc}")
                continue
            agent_id = str(snapshot.get("agent_id") or path.stem)
            if agent_id in seen_agent_ids:
                continue
            seen_agent_ids.add(agent_id)
            errors.extend(validate_snapshot(snapshot, path.name))
    for error in errors:
        print(error)
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read/write Labline agent status snapshots.")
    parser.add_argument("--project-root")
    parser.add_argument("--status-root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--agent-id", required=True)
    start.add_argument("--role", required=True)
    start.add_argument("--task", required=True)
    start.add_argument("--current-action", required=True)
    start.add_argument("--next-expected-update", required=True)
    start.add_argument("--next-check-reason", required=True)
    add_metadata_args(start)
    start.set_defaults(func=cmd_start)

    update = subparsers.add_parser("update")
    update.add_argument("--agent-id", required=True)
    update.add_argument("--status")
    update.add_argument("--current-action")
    update.add_argument("--next-expected-update")
    update.add_argument("--next-check-reason")
    update.add_argument("--job-handle", action="append", default=[])
    update.add_argument("--artifact", action="append", default=[])
    add_metadata_args(update)
    update.set_defaults(func=cmd_update)

    finish = subparsers.add_parser("finish")
    finish.add_argument("--agent-id", required=True)
    finish.add_argument("--status", required=True, choices=sorted(TERMINAL_STATUSES))
    finish.add_argument("--current-action", required=True)
    finish.add_argument("--blocker")
    finish.add_argument("--artifact", action="append", default=[])
    finish.set_defaults(func=cmd_finish)

    summary = subparsers.add_parser("summary")
    summary.add_argument("--now")
    summary.set_defaults(func=cmd_summary)

    list_cmd = subparsers.add_parser("list")
    list_cmd.set_defaults(func=cmd_list)

    validate = subparsers.add_parser("validate")
    validate.set_defaults(func=cmd_validate)

    return parser


def add_metadata_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--transport", choices=sorted(TRANSPORTS))
    parser.add_argument("--review-independence")
    parser.add_argument("--input-scope", action="append", default=[])
    parser.add_argument("--trace-path")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
