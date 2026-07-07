from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LANE_CLI = REPO_ROOT / "tools" / "lane"
REMOTE_OBSERVATION = REPO_ROOT / "tools" / "labline_remote_observation.py"


def run_lane(args: list[str], cwd: Path, workspace: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["LABLINE_WORKSPACE"] = str(workspace or cwd.parent)
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


def run_remote(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, str(REMOTE_OBSERVATION), *args],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"remote observation failed: {result.stderr}\nstdout:\n{result.stdout}")
    return result


def runtime_text(project: Path) -> str:
    root = project / ".labline" / "runtime"
    if not root.exists():
        return ""
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


def test_project_init_release_smoke_keeps_legacy_pipeline_state_out_of_new_projects():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        workspace.mkdir()
        project = root / "release-demo"

        result = run_lane(
            [
                "project",
                "init",
                str(project),
                "--name",
                "release-demo",
                "--direction",
                "runtime release smoke",
                "--no-commit",
                "--labline-repo",
                str(REPO_ROOT),
                "--quiet",
            ],
            cwd=root,
            workspace=workspace,
        )

        assert result.returncode == 0
        assert (project / "project.yaml").exists()
        assert (project / ".labline" / "manifest.json").exists()
        assert (project / ".labline" / "installed-skills.txt").exists()
        assert (project / ".labline" / "installed-skills-codex.txt").exists()
        assert not (project / "PIPELINE_STATE.json").exists()


def test_runtime_cli_release_smoke_covers_task_status_and_heartbeat_entrypoints():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        init = run_lane(["runtime", "init"], cwd=project)
        assert init.stdout.strip() == str(project / ".labline" / "runtime")

        created = json.loads(
            run_lane(
                [
                    "runtime",
                    "task",
                    "create",
                    "release_smoke",
                    "--kind",
                    "maintenance",
                    "--title",
                    "release smoke task",
                    "--execution-mode",
                    "inline",
                    "--durability",
                    "ephemeral",
                    "--observation",
                    "enabled",
                    "--heartbeat",
                    "none",
                ],
                cwd=project,
            ).stdout
        )
        assert created["task_id"] == "release_smoke"

        status = json.loads(run_lane(["status", "--json"], cwd=project).stdout)
        assert status["source_counts"]["runtime_tasks"] == 1
        assert status["counts"]["running"] == 0
        assert (project / ".labline" / "runtime" / "summaries" / "current.json").exists()

        heartbeat = json.loads(run_lane(["heartbeat", "--dry-run"], cwd=project).stdout)
        assert heartbeat["dry_run"] is True
        assert heartbeat["checked_count"] == 0
        assert not (project / ".labline" / "runtime" / "heartbeats" / "local-heartbeat.json").exists()


def test_feishu_projection_release_contract_keeps_remote_identity_and_text_bridge_owned():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state_root = root / "bridge-state"
        project = root / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "release_smoke",
                "--kind",
                "experiment",
                "--title",
                "release smoke task",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "running",
            ],
            cwd=project,
        )

        archived = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "archive-message",
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--chat-id",
                    "oc_release_secret",
                    "--sender-open-id",
                    "ou_release_secret",
                    "--message-id",
                    "om_release_001",
                    "--text",
                    "现在怎么样了",
                ]
            ).stdout
        )
        routed = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "route-message",
                    "--project",
                    str(project),
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--archive-ref",
                    archived["archive_ref"],
                    "--chat-id",
                    "oc_release_secret",
                    "--sender-open-id",
                    "ou_release_secret",
                    "--text",
                    "现在怎么样了",
                ]
            ).stdout
        )

        assert routed["route"] == "observation"
        assert routed["inject_tui"] is False
        bridge_archive = "\n".join(path.read_text(encoding="utf-8") for path in (state_root / "archive").glob("*.json"))
        assert "oc_release_secret" in bridge_archive
        assert "ou_release_secret" in bridge_archive
        assert "现在怎么样了" in bridge_archive
        project_runtime = runtime_text(project)
        assert "oc_release_secret" not in project_runtime
        assert "ou_release_secret" not in project_runtime
        assert "现在怎么样了" not in project_runtime


def test_runtime_user_docs_expose_release_surface_and_boundaries():
    readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    operations = (REPO_ROOT / "docs" / "OPERATIONS_GUIDE.md").read_text(encoding="utf-8")
    feishu = (REPO_ROOT / "docs" / "FEISHU_INTEGRATION.md").read_text(encoding="utf-8")
    project_files = (REPO_ROOT / "docs" / "PROJECT_FILES_GUIDE.md").read_text(encoding="utf-8")
    tools_index = (REPO_ROOT / "docs" / "TOOLS_INDEX.md").read_text(encoding="utf-8")

    assert "TOOLS_INDEX.md" in readme
    for token in ["lane runtime init", "lane status --json", "lane status --brief", "lane heartbeat"]:
        assert token in operations
    for token in ["/follow", "/status", "Remote Observation", "bridge-owned", ".labline/runtime/"]:
        assert token in feishu
    for token in [".labline/runtime/", "Runtime Task", "PIPELINE_STATE.json"]:
        assert token in project_files
    for token in [
        "lane runtime",
        "lane status",
        "lane heartbeat",
        "lane debug runtime-smoke",
        "lane debug longtask-smoke",
        "tools/labline_remote_observation.py",
    ]:
        assert token in tools_index
