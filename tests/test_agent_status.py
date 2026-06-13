from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_STATUS = REPO_ROOT / "tools" / "agent_status.py"


def run_agent_status(args, cwd=REPO_ROOT, check=True):
    return subprocess.run(
        [sys.executable, str(AGENT_STATUS), *args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def read_status(root: Path, agent_id: str):
    return json.loads((root / "agents" / f"{agent_id}.json").read_text(encoding="utf-8"))


def test_start_creates_agent_status_snapshot_in_status_root():
    with tempfile.TemporaryDirectory() as tmp:
        status_root = Path(tmp)

        result = run_agent_status(
            [
                "--status-root",
                str(status_root),
                "start",
                "--agent-id",
                "deployer-001",
                "--role",
                "deployer",
                "--task",
                "run sanity experiment",
                "--current-action",
                "starting remote sanity",
                "--next-expected-update",
                "+10m",
                "--next-check-reason",
                "remote sanity run",
            ]
        )

        snapshot = read_status(status_root, "deployer-001")
        assert result.stdout.strip() == str(status_root / "agents" / "deployer-001.json")
        assert snapshot["schema_version"] == 1
        assert snapshot["agent_id"] == "deployer-001"
        assert snapshot["role"] == "deployer"
        assert snapshot["status"] == "starting"
        assert snapshot["task"] == "run sanity experiment"
        assert snapshot["current_action"] == "starting remote sanity"
        assert snapshot["next_check_reason"] == "remote sanity run"
        assert snapshot["job_handles"] == []
        assert snapshot["artifacts"] == []
        assert snapshot["blocker"] is None


def test_update_rewrites_current_snapshot_without_touching_other_agents():
    with tempfile.TemporaryDirectory() as tmp:
        status_root = Path(tmp)
        run_agent_status(
            [
                "--status-root",
                str(status_root),
                "start",
                "--agent-id",
                "deployer-001",
                "--role",
                "deployer",
                "--task",
                "run full experiments",
                "--current-action",
                "starting",
                "--next-expected-update",
                "+5m",
                "--next-check-reason",
                "initial update",
            ]
        )
        run_agent_status(
            [
                "--status-root",
                str(status_root),
                "update",
                "--agent-id",
                "deployer-001",
                "--status",
                "waiting_on_job",
                "--current-action",
                "training in tmux exp01",
                "--next-expected-update",
                "+30m",
                "--next-check-reason",
                "stable training",
                "--job-handle",
                '{"type":"tmux","server":"3090x2","session":"exp01"}',
                "--artifact",
                "refine-logs/EXPERIMENT_RESULTS/exp01.json",
            ]
        )

        snapshot = read_status(status_root, "deployer-001")
        assert snapshot["status"] == "waiting_on_job"
        assert snapshot["current_action"] == "training in tmux exp01"
        assert snapshot["next_check_reason"] == "stable training"
        assert snapshot["job_handles"] == [{"type": "tmux", "server": "3090x2", "session": "exp01"}]
        assert snapshot["artifacts"] == ["refine-logs/EXPERIMENT_RESULTS/exp01.json"]


def test_finish_marks_terminal_status_and_blocker():
    with tempfile.TemporaryDirectory() as tmp:
        status_root = Path(tmp)
        run_agent_status(
            [
                "--status-root",
                str(status_root),
                "start",
                "--agent-id",
                "coder-001",
                "--role",
                "coder",
                "--task",
                "implement model",
                "--current-action",
                "starting",
                "--next-expected-update",
                "+5m",
                "--next-check-reason",
                "short task",
            ]
        )

        run_agent_status(
            [
                "--status-root",
                str(status_root),
                "finish",
                "--agent-id",
                "coder-001",
                "--status",
                "blocked",
                "--current-action",
                "blocked on missing dataset",
                "--blocker",
                "dataset path not found",
                "--artifact",
                "BLOCKED_REPORT.md",
            ]
        )

        snapshot = read_status(status_root, "coder-001")
        assert snapshot["status"] == "blocked"
        assert snapshot["current_action"] == "blocked on missing dataset"
        assert snapshot["blocker"] == "dataset path not found"
        assert snapshot["artifacts"] == ["BLOCKED_REPORT.md"]


def test_summary_derives_stale_task_alive_without_mutating_snapshot():
    with tempfile.TemporaryDirectory() as tmp:
        status_root = Path(tmp)
        run_agent_status(
            [
                "--status-root",
                str(status_root),
                "start",
                "--agent-id",
                "deployer-001",
                "--role",
                "deployer",
                "--task",
                "run full experiments",
                "--current-action",
                "training in tmux exp01",
                "--next-expected-update",
                "2026-06-13T21:05:00Z",
                "--next-check-reason",
                "first 20 minutes of formal training",
            ]
        )
        run_agent_status(
            [
                "--status-root",
                str(status_root),
                "update",
                "--agent-id",
                "deployer-001",
                "--status",
                "waiting_on_job",
                "--job-handle",
                '{"type":"tmux","server":"3090x2","session":"exp01"}',
            ]
        )

        before = read_status(status_root, "deployer-001")
        result = run_agent_status(
            [
                "--status-root",
                str(status_root),
                "summary",
                "--now",
                "2026-06-13T21:06:00Z",
            ]
        )
        after = read_status(status_root, "deployer-001")

        assert "deployer-001 deployer agent_stale_task_alive training in tmux exp01" in result.stdout
        assert after == before


def test_validate_reports_invalid_snapshot_schema():
    with tempfile.TemporaryDirectory() as tmp:
        status_root = Path(tmp)
        agents_dir = status_root / "agents"
        agents_dir.mkdir()
        (agents_dir / "bad.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "bad",
                    "role": "coder",
                    "status": "lost",
                }
            ),
            encoding="utf-8",
        )

        result = run_agent_status(
            ["--status-root", str(status_root), "validate"],
            check=False,
        )

        assert result.returncode == 1
        assert "bad.json: missing task" in result.stdout
        assert "bad.json: invalid status=lost" in result.stdout


def test_list_outputs_known_agents():
    with tempfile.TemporaryDirectory() as tmp:
        status_root = Path(tmp)
        for agent_id, role in [("coder-001", "coder"), ("writer-001", "writer")]:
            run_agent_status(
                [
                    "--status-root",
                    str(status_root),
                    "start",
                    "--agent-id",
                    agent_id,
                    "--role",
                    role,
                    "--task",
                    f"{role} task",
                    "--current-action",
                    "starting",
                    "--next-expected-update",
                    "+5m",
                    "--next-check-reason",
                    "short task",
                ]
            )

        result = run_agent_status(["--status-root", str(status_root), "list"])

        assert result.stdout.splitlines() == [
            "coder-001 coder starting",
            "writer-001 writer starting",
        ]


def test_project_root_writes_project_runtime_state():
    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp) / "project"
        project_root.mkdir()

        run_agent_status(
            [
                "--project-root",
                str(project_root),
                "start",
                "--agent-id",
                "writer-001",
                "--role",
                "writer",
                "--task",
                "draft method",
                "--current-action",
                "starting draft",
                "--next-expected-update",
                "+20m",
                "--next-check-reason",
                "writing agent",
            ]
        )

        snapshot_path = project_root / ".aris" / "status" / "agents" / "writer-001.json"
        assert snapshot_path.exists()
        assert json.loads(snapshot_path.read_text(encoding="utf-8"))["role"] == "writer"


def test_start_accepts_reviewer_transport_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        status_root = Path(tmp)

        run_agent_status(
            [
                "--status-root",
                str(status_root),
                "start",
                "--agent-id",
                "reviewer-001",
                "--role",
                "reviewer",
                "--task",
                "audit experiment",
                "--current-action",
                "reviewing original inputs",
                "--next-expected-update",
                "+20m",
                "--next-check-reason",
                "reviewer call",
                "--transport",
                "mcp_codex",
                "--review-independence",
                "fresh_original_inputs",
                "--input-scope",
                "refine-logs/EXPERIMENT_PLAN.md",
                "--input-scope",
                "refine-logs/EXPERIMENT_RESULTS/",
                "--trace-path",
                ".aris/traces/experiment-audit/20260613_run01/",
            ]
        )

        snapshot = read_status(status_root, "reviewer-001")
        assert snapshot["transport"] == "mcp_codex"
        assert snapshot["review_independence"] == "fresh_original_inputs"
        assert snapshot["input_scope"] == [
            "refine-logs/EXPERIMENT_PLAN.md",
            "refine-logs/EXPERIMENT_RESULTS/",
        ]
        assert snapshot["trace_path"] == ".aris/traces/experiment-audit/20260613_run01/"


if __name__ == "__main__":
    tests = [
        test_start_creates_agent_status_snapshot_in_status_root,
        test_update_rewrites_current_snapshot_without_touching_other_agents,
        test_finish_marks_terminal_status_and_blocker,
        test_summary_derives_stale_task_alive_without_mutating_snapshot,
        test_validate_reports_invalid_snapshot_schema,
        test_list_outputs_known_agents,
        test_project_root_writes_project_runtime_state,
        test_start_accepts_reviewer_transport_metadata,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"OK {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
    sys.exit(1 if failed else 0)
