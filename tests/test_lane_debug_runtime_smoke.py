from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LANE_CLI = REPO_ROOT / "tools" / "lane"


def run_lane(args: list[str], cwd: Path, workspace: Path, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["LABLINE_WORKSPACE"] = str(workspace)
    result = subprocess.run(
        [sys.executable, str(LANE_CLI), *args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"lane failed: {result.stderr}\nstdout:\n{result.stdout}")
    return result


def init_real_project(root: Path, workspace: Path) -> Path:
    project = root / "real-project"
    run_lane(
        [
            "project",
            "init",
            str(project),
            "--name",
            "real-project",
            "--direction",
            "debug runtime smoke",
            "--no-commit",
            "--labline-repo",
            str(REPO_ROOT),
            "--quiet",
        ],
        cwd=root,
        workspace=workspace,
    )
    return project


def test_debug_runtime_smoke_copy_mode_writes_report_without_mutating_source_project():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        workspace.mkdir()
        project = init_real_project(root, workspace)
        assert not (project / ".labline" / "runtime").exists()

        result = run_lane(
            [
                "debug",
                "runtime-smoke",
                "--project",
                str(project),
                "--labline-repo",
                str(REPO_ROOT),
                "--json",
                "--now",
                "2026-06-30T00:05:00Z",
            ],
            cwd=root,
            workspace=workspace,
        )

        report = json.loads(result.stdout)
        assert report["status"] == "pass"
        assert report["in_place"] is False
        assert report["source_project"] == str(project.resolve())
        assert report["working_project"] != report["source_project"]
        assert Path(report["report_dir"]).is_dir()
        assert Path(report["report_json"]).exists()
        assert Path(report["report_md"]).exists()
        assert (Path(report["working_project"]) / ".labline" / "runtime").is_dir()
        assert not (project / ".labline" / "runtime").exists()
        assert not (project / "PIPELINE_STATE.json").exists()

        checks = {check["name"]: check for check in report["checks"]}
        for name in [
            "project_update",
            "project_doctor",
            "no_root_pipeline_state",
            "runtime_init",
            "runtime_task_create",
            "status_json",
            "heartbeat_dry_run",
            "heartbeat",
            "remote_observation_route",
            "no_remote_identity_leak",
        ]:
            assert checks[name]["status"] == "pass"
        assert checks["remote_observation_route"]["details"]["route"] == "observation"


def test_debug_runtime_smoke_in_place_requires_explicit_yes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        workspace.mkdir()
        project = init_real_project(root, workspace)

        result = run_lane(
            [
                "debug",
                "runtime-smoke",
                "--project",
                str(project),
                "--in-place",
                "--labline-repo",
                str(REPO_ROOT),
            ],
            cwd=root,
            workspace=workspace,
            check=False,
        )

        assert result.returncode == 2
        assert "--in-place requires --yes" in result.stderr
        assert not (project / ".labline" / "runtime").exists()


def test_debug_longtask_smoke_copy_mode_runs_detached_job_to_terminal_escalation():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        workspace.mkdir()
        project = init_real_project(root, workspace)
        assert not (project / ".labline" / "runtime").exists()

        result = run_lane(
            [
                "debug",
                "longtask-smoke",
                "--project",
                str(project),
                "--labline-repo",
                str(REPO_ROOT),
                "--json",
                "--seconds",
                "1",
                "--now-running",
                "2026-07-02T00:05:00Z",
                "--now-terminal",
                "2026-07-02T00:10:00Z",
            ],
            cwd=root,
            workspace=workspace,
        )

        report = json.loads(result.stdout)
        assert report["status"] == "pass"
        assert report["in_place"] is False
        assert report["source_project"] == str(project.resolve())
        assert report["working_project"] != report["source_project"]
        assert Path(report["report_json"]).exists()
        assert Path(report["report_md"]).exists()
        assert not (project / ".labline" / "runtime").exists()

        working_project = Path(report["working_project"])
        assert (working_project / "outputs" / "labline-debug-longtask" / "result.json").exists()
        escalations = list((working_project / ".labline" / "runtime" / "escalations").glob("*.json"))
        assert escalations

        checks = {check["name"]: check for check in report["checks"]}
        for name in [
            "project_update",
            "project_doctor",
            "runtime_init",
            "longtask_process_start",
            "runtime_task_create_detached",
            "heartbeat_running",
            "longtask_process_wait",
            "runtime_task_complete",
            "heartbeat_terminal",
        ]:
            assert checks[name]["status"] == "pass"
        assert checks["heartbeat_running"]["details"]["healthy"] == 1
        assert checks["heartbeat_terminal"]["details"]["escalated"] == 1


def test_debug_longtask_smoke_heartbeats_only_the_new_task_with_existing_runtime_history():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        workspace.mkdir()
        project = init_real_project(root, workspace)

        run_lane(["runtime", "init", "--project", str(project), "--labline-repo", str(REPO_ROOT)], cwd=root, workspace=workspace)
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "source_stale_terminal",
                "--project",
                str(project),
                "--labline-repo",
                str(REPO_ROOT),
                "--kind",
                "debug",
                "--title",
                "source stale terminal task",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--observation",
                "enabled",
                "--heartbeat",
                "passive",
                "--status",
                "completed",
                "--next-expected-update",
                "1970-01-01T00:00:00Z",
            ],
            cwd=root,
            workspace=workspace,
        )

        result = run_lane(
            [
                "debug",
                "longtask-smoke",
                "--project",
                str(project),
                "--labline-repo",
                str(REPO_ROOT),
                "--json",
                "--seconds",
                "1",
                "--now-running",
                "2026-07-02T00:05:00Z",
                "--now-terminal",
                "2026-07-02T00:10:00Z",
            ],
            cwd=root,
            workspace=workspace,
        )

        report = json.loads(result.stdout)
        assert report["status"] == "pass"
        checks = {check["name"]: check for check in report["checks"]}
        running_payload = json.loads(checks["heartbeat_running"]["details"]["stdout"])
        terminal_payload = json.loads(checks["heartbeat_terminal"]["details"]["stdout"])

        assert running_payload["checked_count"] == 1
        assert running_payload["action_counts"]["healthy"] == 1
        assert running_payload["action_counts"]["escalated"] == 0
        assert terminal_payload["checked_count"] == 1
        assert terminal_payload["action_counts"]["escalated"] == 1
        assert all(action["task_id"].startswith("debug_longtask_") for action in running_payload["actions"])
        assert all(action["task_id"].startswith("debug_longtask_") for action in terminal_payload["actions"])

        source_task_files = {path.name for path in (project / ".labline" / "runtime" / "tasks").glob("*.json")}
        assert "source_stale_terminal.json" in source_task_files
        assert not any(name.startswith("debug_longtask_") for name in source_task_files)
