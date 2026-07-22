from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LANE_CLI = REPO_ROOT / "tools" / "lane"


EXPECTED_RUNTIME_DIRS = [
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


def run_lane(args: list[str], cwd: Path, check: bool = True, env_update: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["LABLINE_WORKSPACE"] = str(cwd.parent)
    if env_update:
        env.update(env_update)
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


def runtime_root(project: Path) -> Path:
    return project / ".labline" / "runtime"


def read_events(project: Path) -> list[dict]:
    path = runtime_root(project) / "events" / "runtime.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_fake_codex(path: Path, exit_code: int = 0, message: str = "fake leader done") -> Path:
    script = path / "fake-codex.py"
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "args = sys.argv[1:]",
                "record = Path.cwd() / 'fake-codex-record.json'",
                "output = None",
                "for i, arg in enumerate(args):",
                "    if arg == '-o' and i + 1 < len(args):",
                "        output = Path(args[i + 1])",
                "prompt = sys.stdin.read() if args and args[-1] == '-' else (args[-1] if args else '')",
                "env_keys = ['http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY', 'no_proxy', 'NO_PROXY']",
                "record.write_text(json.dumps({'args': args, 'prompt': prompt, 'env': {k: os.environ.get(k) for k in env_keys if os.environ.get(k)}}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')",
                "if output is not None:",
                "    output.parent.mkdir(parents=True, exist_ok=True)",
                f"    output.write_text({message!r} + '\\n', encoding='utf-8')",
                "artifact = os.environ.get('FAKE_CODEX_ARTIFACT')",
                "if artifact:",
                "    artifact_path = Path(artifact)",
                "    artifact_path.parent.mkdir(parents=True, exist_ok=True)",
                "    artifact_path.write_text('fake verdict\\n', encoding='utf-8')",
                f"sys.exit({exit_code})",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def write_fake_tmux(path: Path) -> Path:
    script = path / "fake-tmux.py"
    script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "calls = Path(os.environ['FAKE_TMUX_CALLS'])",
                "calls.parent.mkdir(parents=True, exist_ok=True)",
                "args = sys.argv[1:]",
                "with calls.open('a', encoding='utf-8') as handle:",
                "    handle.write(json.dumps({'args': args}, ensure_ascii=False) + '\\n')",
                "if args[:1] == ['has-session']:",
                "    sys.exit(0 if os.environ.get('FAKE_TMUX_HAS_SESSION') == '1' else 1)",
                "if args[:1] == ['new-session']:",
                "    if os.environ.get('FAKE_TMUX_LAUNCH_FAIL') == '1':",
                "        print('fake tmux launch failed', file=sys.stderr)",
                "        sys.exit(2)",
                "    sys.exit(0)",
                "sys.exit(0)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def test_runtime_init_creates_expected_directories():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(["runtime", "init"], cwd=project)

        assert result.stdout.strip() == str(runtime_root(project))
        for rel in EXPECTED_RUNTIME_DIRS:
            assert (runtime_root(project) / rel).is_dir(), rel


def test_runtime_init_is_idempotent_and_preserves_existing_event_log():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(["runtime", "init"], cwd=project)
        events = runtime_root(project) / "events" / "runtime.jsonl"
        events.write_text('{"event_type":"keep"}\n', encoding="utf-8")

        run_lane(["runtime", "init"], cwd=project)

        assert events.read_text(encoding="utf-8") == '{"event_type":"keep"}\n'


def test_runtime_event_append_writes_jsonl_event_with_task_id_and_payload():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "task.started",
                "--task-id",
                "task_001",
                "--json",
                '{"status":"running"}',
            ],
            cwd=project,
        )

        events = read_events(project)
        assert result.stdout.strip() == str(runtime_root(project) / "events" / "runtime.jsonl")
        assert len(events) == 1
        event = events[0]
        assert event["schema_version"] == "0.1"
        assert event["event_type"] == "task.started"
        assert event["task_id"] == "task_001"
        assert event["payload"] == {"status": "running"}
        assert event["source"]["entry"] == "lane"
        assert event["event_id"].startswith("evt_")
        assert event["created_at"].endswith("Z")


def test_runtime_event_append_rejects_invalid_payload_without_partial_write():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(["runtime", "init"], cwd=project)
        events = runtime_root(project) / "events" / "runtime.jsonl"

        result = run_lane(
            ["runtime", "event", "append", "--type", "task.started", "--json", "{bad"],
            cwd=project,
            check=False,
        )

        assert result.returncode == 2
        assert "invalid JSON payload" in result.stderr
        assert not events.exists()


def test_runtime_task_list_outputs_empty_list_when_no_tasks_exist():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(["runtime", "init"], cwd=project)

        result = run_lane(["runtime", "task", "list"], cwd=project)

        assert json.loads(result.stdout) == []


def test_runtime_task_get_reports_missing_task():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(["runtime", "init"], cwd=project)

        result = run_lane(["runtime", "task", "get", "task_missing"], cwd=project, check=False)

        assert result.returncode == 1
        assert "runtime task not found: task_missing" in result.stderr


def test_status_json_aggregates_runtime_and_legacy_agent_status_and_writes_summary():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        legacy_agents = project / ".labline" / "status" / "agents"
        runtime_agents = runtime_root(project) / "agents"
        legacy_agents.mkdir(parents=True)
        runtime_agents.mkdir(parents=True)
        (legacy_agents / "deployer-001.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "deployer-001",
                    "role": "deployer",
                    "status": "waiting_on_job",
                    "task": "run full experiments",
                    "last_updated": "2026-06-30T00:00:00Z",
                    "current_action": "training in tmux exp01",
                    "next_expected_update": "2026-06-30T01:00:00Z",
                    "next_check_reason": "stable training",
                    "job_handles": [{"type": "tmux", "session": "exp01"}],
                    "artifacts": ["refine-logs/exp01.log"],
                    "blocker": None,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (runtime_agents / "coder-001.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-001",
                    "role": "coder",
                    "status": "blocked",
                    "task": "implement model",
                    "last_updated": "2026-06-30T00:05:00Z",
                    "current_action": "blocked on missing dataset",
                    "next_expected_update": None,
                    "next_check_reason": "terminal",
                    "job_handles": [],
                    "artifacts": ["BLOCKED_REPORT.md"],
                    "blocker": "dataset path not found",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        pipeline_dir = runtime_root(project) / "pipelines"
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "leader.json").write_text(
            json.dumps({"pipeline_id": "leader", "current_stage": "experiment", "status": "running"}) + "\n",
            encoding="utf-8",
        )

        result = run_lane(["status", "--json"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["schema_version"] == "0.1"
        assert payload["derived"] is True
        assert payload["counts"]["running"] == 1
        assert payload["counts"]["blocked"] == 1
        assert payload["source_counts"]["agents"] == 2
        assert payload["source_counts"]["pipelines"] == 1
        assert [task["task_id"] for task in payload["tasks"]] == ["agent:coder-001", "agent:deployer-001"]
        deployer = next(task for task in payload["tasks"] if task["task_id"] == "agent:deployer-001")
        assert deployer["status"] == "running"
        assert deployer["durability"] == "supervised"
        assert deployer["source_refs"] == [".labline/status/agents/deployer-001.json"]

        current_json = json.loads((runtime_root(project) / "summaries" / "current.json").read_text(encoding="utf-8"))
        current_md = (runtime_root(project) / "summaries" / "current.md").read_text(encoding="utf-8")
        assert current_json["counts"] == payload["counts"]
        assert "running: 1" in current_md
        assert "agent:deployer-001" in current_md
        assert (runtime_root(project) / "tasks" / "agent-coder-001.json").exists()
        assert not (project / "PIPELINE_STATE.json").exists()


def test_status_json_reports_delegated_agent_observability_failure_rate():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "reviewer-lost.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "reviewer-lost",
                    "role": "reviewer",
                    "status": "starting",
                    "task": "review stage gate",
                    "started_at": "2026-06-30T00:00:00Z",
                    "next_expected_update": "2026-06-30T00:02:00Z",
                    "job_handles": [],
                    "artifacts": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (agents / "coder-done.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-done",
                    "role": "coder",
                    "status": "completed",
                    "task": "write config",
                    "last_updated": "2026-06-30T00:01:00Z",
                    "next_expected_update": None,
                    "job_handles": [],
                    "artifacts": ["refine-logs/config.py"],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_lane(["status", "--json"], cwd=project)

        payload = json.loads(result.stdout)
        metric = payload["metrics"]["delegated_agent_observability"]
        assert metric == {
            "delegated_agent_tasks": 2,
            "observability_failures": 1,
            "observability_failure_rate": 0.5,
            "failure_task_ids": ["agent:reviewer-lost"],
        }
        lost = next(task for task in payload["tasks"] if task["task_id"] == "agent:reviewer-lost")
        assert lost["status"] == "anomaly"
        assert lost["observability_failure"] is True
        assert lost["observability_failure_type"] == "boot_no_progress"
        current_md = (runtime_root(project) / "summaries" / "current.md").read_text(encoding="utf-8")
        assert "delegated_agent_observability_failure_rate: 0.500 (1/2)" in current_md

        plan_result = run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:03:00Z"], cwd=project)
        plan = json.loads(plan_result.stdout)
        assert plan["summary_metrics"]["delegated_agent_observability"] == metric


def test_status_brief_outputs_human_readable_summary():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "writer-001.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "writer-001",
                    "role": "writer",
                    "status": "done",
                    "task": "draft results",
                    "last_updated": "2026-06-30T00:00:00Z",
                    "current_action": "draft complete",
                    "next_expected_update": None,
                    "next_check_reason": "terminal",
                    "job_handles": [],
                    "artifacts": ["paper/results.tex"],
                    "blocker": None,
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_lane(["status", "--brief"], cwd=project)

        assert "Labline Runtime Status" in result.stdout
        assert "recently_completed: 1" in result.stdout
        assert "agent:writer-001" in result.stdout


def test_status_brief_surfaces_queue_and_watchdog_runtime_sources():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        queue_dir = runtime_root(project) / "queues"
        watchdog_dir = runtime_root(project) / "watchdog" / "exp01"
        queue_dir.mkdir(parents=True)
        watchdog_dir.mkdir(parents=True)
        (queue_dir / "formal-exp.json").write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "queue_id": "formal-exp",
                    "state": {
                        "jobs": [
                            {"id": "job1", "status": "running"},
                            {"id": "job2", "status": "failed_oom"},
                            {"id": "job3", "status": "stuck"},
                        ]
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (watchdog_dir / "summary.json").write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "task_id": "watchdog:exp01",
                    "watchdog_task": "exp01",
                    "status": "DEAD",
                    "watchdog": {"msg": "screen session gone"},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_lane(["status", "--brief"], cwd=project)

        assert "formal-exp: jobs=3 running=1 failed_oom=1 stuck=1" in result.stdout
        assert "watchdog:exp01: DEAD screen session gone" in result.stdout


def test_runtime_task_create_writes_task_and_created_event():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "run sanity experiment",
                "--owner",
                "deployer",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "ephemeral",
                "--observation",
                "enabled",
                "--heartbeat",
                "none",
            ],
            cwd=project,
        )

        task = json.loads(result.stdout)
        assert task["task_id"] == "task_001"
        assert task["status"] == "new"
        assert task["derived"] is False
        stored = json.loads((runtime_root(project) / "tasks" / "task_001.json").read_text(encoding="utf-8"))
        assert stored == task
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["task.created"]
        assert events[0]["task_id"] == "task_001"


def test_status_json_includes_explicit_runtime_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "run sanity experiment",
                "--execution-mode",
                "agent_turn",
                "--status",
                "running",
            ],
            cwd=project,
        )

        result = run_lane(["status", "--json"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["counts"]["running"] == 1
        assert payload["source_counts"]["runtime_tasks"] == 1
        assert [task["task_id"] for task in payload["tasks"]] == ["task_001"]


def test_status_json_applies_task_superseded_resolution_without_counting_critical():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "coder-old.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-old",
                    "role": "Coder",
                    "status": "blocked",
                    "task": "old config attempt",
                    "last_updated": "2026-06-30T00:00:00Z",
                    "current_action": "blocked on old gate",
                    "next_expected_update": None,
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": "old gate failed",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (agents / "coder-new.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-new",
                    "role": "Coder",
                    "status": "done",
                    "task": "replacement config attempt",
                    "last_updated": "2026-06-30T00:10:00Z",
                    "current_action": "config ready",
                    "next_expected_update": None,
                    "job_handles": [],
                    "artifacts": ["refine-logs/R003/config.py"],
                    "blocker": None,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "task.superseded",
                "--task-id",
                "agent:coder-old",
                "--json",
                '{"resolved_by_task_id":"agent:coder-new","reason":"replacement config artifact is ready"}',
            ],
            cwd=project,
        )

        payload = json.loads(run_lane(["status", "--json"], cwd=project).stdout)

        assert payload["counts"]["blocked"] == 0
        assert payload["counts"]["recently_completed"] == 1
        assert payload["source_counts"]["task_resolutions"] == 1
        old = next(task for task in payload["tasks"] if task["task_id"] == "agent:coder-old")
        assert old["status"] == "superseded"
        assert old["heartbeat"] == "none"
        assert old["resolved_by_task_id"] == "agent:coder-new"
        assert old["resolution"]["reason"] == "replacement config artifact is ready"


def test_status_json_applies_leader_terminal_decision_without_counting_critical():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "coder-old.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-old",
                    "role": "Coder",
                    "status": "blocked",
                    "task": "old executor attempt",
                    "last_updated": "2026-06-30T00:00:00Z",
                    "current_action": "blocked on lost executor",
                    "next_expected_update": None,
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": "executor handle lost",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "leader.decision",
                "--task-id",
                "agent:coder-old",
                "--json",
                '{"action":"stop","status":"cancelled","reason":"terminal result recorded by Leader; do not resume stale executor"}',
            ],
            cwd=project,
        )

        payload = json.loads(run_lane(["status", "--json"], cwd=project).stdout)

        assert payload["counts"]["blocked"] == 0
        assert payload["source_counts"]["task_resolutions"] == 1
        old = next(task for task in payload["tasks"] if task["task_id"] == "agent:coder-old")
        assert old["status"] == "cancelled"
        assert old["heartbeat"] == "none"
        assert old["resolution"]["event_type"] == "leader.decision"
        assert old["resolution"]["reason"] == "terminal result recorded by Leader; do not resume stale executor"


def test_runtime_task_complete_updates_task_and_appends_terminal_event():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "writing",
                "--title",
                "draft report",
                "--owner",
                "writer",
            ],
            cwd=project,
        )

        result = run_lane(["runtime", "task", "complete", "task_001", "--artifact", "paper/report.md"], cwd=project)

        task = json.loads(result.stdout)
        assert task["status"] == "completed"
        assert task["artifacts"] == ["paper/report.md"]
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["task.created", "task.completed"]
        assert events[-1]["payload"]["status"] == "completed"


def test_runtime_task_create_rejects_inconsistent_capability_without_writing_task():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_bad",
                "--kind",
                "experiment",
                "--title",
                "bad detached task",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--status",
                "running",
            ],
            cwd=project,
            check=False,
        )

        assert result.returncode == 2
        assert "detached_job running tasks require at least one job handle" in result.stderr
        assert not (runtime_root(project) / "tasks" / "task_bad.json").exists()
        assert not (runtime_root(project) / "events" / "runtime.jsonl").exists()


def test_runtime_task_create_rejects_heartbeat_without_expected_update():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_bad",
                "--kind",
                "experiment",
                "--title",
                "missing heartbeat due time",
                "--heartbeat",
                "passive",
            ],
            cwd=project,
            check=False,
        )

        assert result.returncode == 2
        assert "heartbeat requires --next-expected-update" in result.stderr


def test_runtime_delegated_agent_create_requires_expected_update():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "task",
                "create",
                "agent-reviewer-001",
                "--kind",
                "agent",
                "--title",
                "review stage gate",
                "--owner",
                "Reviewer",
                "--status",
                "dispatching",
            ],
            cwd=project,
            check=False,
        )

        assert result.returncode == 2
        assert "delegated agent tasks require --next-expected-update" in result.stderr


def test_runtime_task_terminal_gate_requires_declared_artifacts_to_exist():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "agent-coder-001",
                "--kind",
                "agent",
                "--title",
                "write config",
                "--owner",
                "Coder",
                "--status",
                "running",
                "--next-expected-update",
                "2026-06-30T00:10:00Z",
                "--required-artifact",
                "refine-logs/config.py",
            ],
            cwd=project,
        )

        missing = run_lane(["runtime", "task", "complete", "agent-coder-001"], cwd=project, check=False)

        assert missing.returncode == 2
        assert "terminal task missing required artifacts: refine-logs/config.py" in missing.stderr

        artifact = project / "refine-logs" / "config.py"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("# config\n", encoding="utf-8")

        result = run_lane(["runtime", "task", "complete", "agent-coder-001"], cwd=project)

        task = json.loads(result.stdout)
        assert task["status"] == "completed"
        assert task["required_artifacts"] == ["refine-logs/config.py"]


def test_runtime_reviewer_terminal_gate_requires_verdict_artifact():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "agent-reviewer-001",
                "--kind",
                "agent",
                "--title",
                "review stage gate",
                "--owner",
                "Reviewer",
                "--status",
                "running",
                "--next-expected-update",
                "2026-06-30T00:10:00Z",
            ],
            cwd=project,
        )

        result = run_lane(["runtime", "task", "complete", "agent-reviewer-001"], cwd=project, check=False)

        assert result.returncode == 2
        assert "reviewer terminal tasks require --verdict-artifact" in result.stderr

        verdict = project / "refine-logs" / "REVIEW.md"
        verdict.parent.mkdir(parents=True)
        verdict.write_text("PASS\n", encoding="utf-8")

        completed = run_lane(
            [
                "runtime",
                "task",
                "complete",
                "agent-reviewer-001",
                "--verdict-artifact",
                "refine-logs/REVIEW.md",
            ],
            cwd=project,
        )

        task = json.loads(completed.stdout)
        assert task["status"] == "completed"
        assert task["verdict_artifact"] == "refine-logs/REVIEW.md"


def test_workflow_foreground_review_codex_completes_task_with_handle_status_and_verdict():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        prompt = project / "prompts" / "review.md"
        prompt.parent.mkdir()
        prompt.write_text("Review the gate and write the verdict artifact.\n", encoding="utf-8")
        fake_codex = write_fake_codex(tmp_path, message="foreground reviewer complete")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task-reviewer-001",
                "--kind",
                "agent",
                "--title",
                "review stage gate",
                "--owner",
                "Reviewer",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "dispatching",
                "--next-expected-update",
                "2026-06-30T00:10:00Z",
                "--required-artifact",
                "refine-logs/REVIEW.md",
                "--verdict-artifact",
                "refine-logs/REVIEW.md",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "foreground-review",
                "task-reviewer-001",
                "--json",
                "--agent-id",
                "reviewer-001",
                "--prompt-file",
                "prompts/review.md",
                "--verdict-artifact",
                "refine-logs/REVIEW.md",
                "--codex-bin",
                str(fake_codex),
                "--codex-timeout",
                "30",
                "--now",
                "2026-06-30T00:05:00Z",
            ],
            cwd=project,
            env_update={"FAKE_CODEX_ARTIFACT": "refine-logs/REVIEW.md"},
        )

        payload = json.loads(result.stdout)
        assert payload["action"] == "completed"
        assert payload["status"] == "completed"
        assert payload["transport"] == "cli_session"
        assert payload["codex"]["returncode"] == 0
        assert payload["verdict_ref"] == "refine-logs/REVIEW.md"
        handle = payload["job_handle"]
        assert handle["type"] == "cli_session"
        assert handle["backend"] == "codex_exec"
        assert handle["task_id"] == "task-reviewer-001"
        assert handle["agent_id"] == "reviewer-001"
        assert handle["prompt_ref"] == "prompts/review.md"
        assert handle["output_ref"].startswith(".labline/runtime/transports/")
        assert handle["stdout_ref"].startswith(".labline/runtime/transports/")
        assert handle["stderr_ref"].startswith(".labline/runtime/transports/")

        task = json.loads((runtime_root(project) / "tasks" / "task-reviewer-001.json").read_text(encoding="utf-8"))
        assert task["status"] == "completed"
        assert task["job_handles"] == [handle]
        assert task["artifacts"] == ["refine-logs/REVIEW.md"]
        assert task["verdict_artifact"] == "refine-logs/REVIEW.md"

        agent_status = json.loads((runtime_root(project) / "agents" / "reviewer-001.json").read_text(encoding="utf-8"))
        assert agent_status["status"] == "done"
        assert agent_status["transport"] == "cli_session"
        assert agent_status["job_handles"] == [handle]
        assert agent_status["artifacts"] == ["refine-logs/REVIEW.md"]
        assert agent_status["trace_path"] == ".labline/runtime/tasks/task-reviewer-001.json"

        events = read_events(project)
        assert [event["event_type"] for event in events] == [
            "task.created",
            "task.updated",
            "transport.started",
            "transport.completed",
            "task.completed",
        ]


def test_workflow_foreground_review_fails_when_verdict_artifact_missing():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        prompt = project / "prompts" / "review.md"
        prompt.parent.mkdir()
        prompt.write_text("Review the gate and write the verdict artifact.\n", encoding="utf-8")
        fake_codex = write_fake_codex(tmp_path, message="foreground reviewer complete")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task-reviewer-001",
                "--kind",
                "agent",
                "--title",
                "review stage gate",
                "--owner",
                "Reviewer",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "dispatching",
                "--next-expected-update",
                "2026-06-30T00:10:00Z",
                "--required-artifact",
                "refine-logs/REVIEW.md",
                "--verdict-artifact",
                "refine-logs/REVIEW.md",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "foreground-review",
                "task-reviewer-001",
                "--json",
                "--agent-id",
                "reviewer-001",
                "--prompt-file",
                "prompts/review.md",
                "--verdict-artifact",
                "refine-logs/REVIEW.md",
                "--codex-bin",
                str(fake_codex),
                "--codex-timeout",
                "30",
                "--now",
                "2026-06-30T00:05:00Z",
            ],
            cwd=project,
        )

        payload = json.loads(result.stdout)
        assert payload["action"] == "failed"
        assert payload["status"] == "failed"
        assert payload["codex"]["returncode"] == 0
        assert payload["failure_type"] == "NO_VERDICT_EXECUTION_FAILURE"
        assert "missing verdict artifact" in payload["blocker"]

        task = json.loads((runtime_root(project) / "tasks" / "task-reviewer-001.json").read_text(encoding="utf-8"))
        assert task["status"] == "failed"
        assert task["blocker"] == payload["blocker"]
        assert task["job_handles"] == [payload["job_handle"]]

        agent_status = json.loads((runtime_root(project) / "agents" / "reviewer-001.json").read_text(encoding="utf-8"))
        assert agent_status["status"] == "failed"
        assert agent_status["blocker"] == payload["blocker"]
        assert agent_status["artifacts"] == []

        events = read_events(project)
        assert [event["event_type"] for event in events] == [
            "task.created",
            "task.updated",
            "transport.started",
            "transport.failed",
            "task.failed",
        ]


def test_workflow_foreground_review_rejects_agent_status_task_filename_collision():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        prompt = project / "prompts" / "review.md"
        prompt.parent.mkdir()
        prompt.write_text("Review the gate and write the verdict artifact.\n", encoding="utf-8")
        fake_codex = write_fake_codex(tmp_path, message="foreground reviewer complete")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "agent-reviewer-001",
                "--kind",
                "agent",
                "--title",
                "review stage gate",
                "--owner",
                "Reviewer",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "dispatching",
                "--next-expected-update",
                "2026-06-30T00:10:00Z",
                "--verdict-artifact",
                "refine-logs/REVIEW.md",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "foreground-review",
                "agent-reviewer-001",
                "--json",
                "--agent-id",
                "reviewer-001",
                "--prompt-file",
                "prompts/review.md",
                "--verdict-artifact",
                "refine-logs/REVIEW.md",
                "--codex-bin",
                str(fake_codex),
                "--codex-timeout",
                "30",
                "--now",
                "2026-06-30T00:05:00Z",
            ],
            cwd=project,
            check=False,
        )

        assert result.returncode == 2
        assert "collides with derived agent-status task id" in result.stderr
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["task.created"]


def test_workflow_tmux_job_starts_detached_task_with_handle_status_and_job_record():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        fake_tmux = write_fake_tmux(tmp_path)
        tmux_calls = tmp_path / "tmux-calls.jsonl"
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task-deployer-001",
                "--kind",
                "agent",
                "--title",
                "train teacher",
                "--owner",
                "Deployer",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "dispatching",
                "--next-expected-update",
                "2026-06-30T01:00:00Z",
                "--required-artifact",
                "outputs/epoch_2.pth",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "tmux-job",
                "task-deployer-001",
                "--json",
                "--agent-id",
                "deployer-001",
                "--session",
                "train_teacher",
                "--command",
                "python train.py --epochs 2",
                "--log",
                "logs/train.log",
                "--required-artifact",
                "outputs/epoch_2.pth",
                "--next-expected-update",
                "2026-06-30T01:30:00Z",
                "--tmux-bin",
                str(fake_tmux),
                "--now",
                "2026-06-30T00:05:00Z",
            ],
            cwd=project,
            env_update={"FAKE_TMUX_CALLS": str(tmux_calls)},
        )

        payload = json.loads(result.stdout)
        assert payload["action"] == "started"
        assert payload["status"] == "waiting_on_job"
        assert payload["transport"] == "tmux"
        handle = payload["job_handle"]
        assert handle["type"] == "tmux"
        assert handle["backend"] == "tmux"
        assert handle["session"] == "train_teacher"
        assert handle["log_ref"] == "logs/train.log"
        assert handle["job_ref"].startswith(".labline/runtime/jobs/")
        assert handle["exit_code_ref"].startswith(".labline/runtime/jobs/")
        assert handle["exit_code_ref"].endswith(".exitcode")

        task = json.loads((runtime_root(project) / "tasks" / "task-deployer-001.json").read_text(encoding="utf-8"))
        assert task["status"] == "waiting_on_job"
        assert task["execution_mode"] == "detached_job"
        assert task["job_handles"] == [handle]
        assert task["required_artifacts"] == ["outputs/epoch_2.pth"]

        agent_status = json.loads((runtime_root(project) / "agents" / "deployer-001.json").read_text(encoding="utf-8"))
        assert agent_status["status"] == "waiting_on_job"
        assert agent_status["transport"] == "tmux"
        assert agent_status["job_handles"] == [handle]
        assert agent_status["trace_path"] == handle["job_ref"]

        job_record = json.loads((project / handle["job_ref"]).read_text(encoding="utf-8"))
        assert job_record["status"] == "running"
        assert job_record["session"] == "train_teacher"
        assert job_record["command"] == "python train.py --epochs 2"
        assert job_record["log_ref"] == "logs/train.log"
        assert job_record["exit_code_ref"] == handle["exit_code_ref"]

        calls = [json.loads(line)["args"] for line in tmux_calls.read_text(encoding="utf-8").splitlines()]
        assert calls[0] == ["has-session", "-t", "train_teacher"]
        assert calls[1][:4] == ["new-session", "-d", "-s", "train_teacher"]
        assert "python train.py --epochs 2" in calls[1][4]
        assert "{ python train.py --epochs 2; }" in calls[1][4]
        assert "logs/train.log" in calls[1][4]
        assert handle["exit_code_ref"] in calls[1][4]

        events = read_events(project)
        assert [event["event_type"] for event in events] == ["task.created", "task.updated", "job.started"]


def test_workflow_tmux_job_rejects_existing_session_without_overwriting_task():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        fake_tmux = write_fake_tmux(tmp_path)
        tmux_calls = tmp_path / "tmux-calls.jsonl"
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task-deployer-001",
                "--kind",
                "agent",
                "--title",
                "train teacher",
                "--owner",
                "Deployer",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "dispatching",
                "--next-expected-update",
                "2026-06-30T01:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "tmux-job",
                "task-deployer-001",
                "--json",
                "--agent-id",
                "deployer-001",
                "--session",
                "train_teacher",
                "--command",
                "python train.py",
                "--log",
                "logs/train.log",
                "--tmux-bin",
                str(fake_tmux),
            ],
            cwd=project,
            check=False,
            env_update={"FAKE_TMUX_CALLS": str(tmux_calls), "FAKE_TMUX_HAS_SESSION": "1"},
        )

        assert result.returncode == 2
        assert "tmux session already exists: train_teacher" in result.stderr
        task = json.loads((runtime_root(project) / "tasks" / "task-deployer-001.json").read_text(encoding="utf-8"))
        assert task["status"] == "dispatching"
        assert task["job_handles"] == []
        assert not (runtime_root(project) / "agents" / "deployer-001.json").exists()
        calls = [json.loads(line)["args"] for line in tmux_calls.read_text(encoding="utf-8").splitlines()]
        assert calls == [["has-session", "-t", "train_teacher"]]
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["task.created"]


def test_workflow_tmux_job_rejects_agent_status_task_filename_collision():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        fake_tmux = write_fake_tmux(tmp_path)
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "agent-deployer-001",
                "--kind",
                "agent",
                "--title",
                "train teacher",
                "--owner",
                "Deployer",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "dispatching",
                "--next-expected-update",
                "2026-06-30T01:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "tmux-job",
                "agent-deployer-001",
                "--json",
                "--agent-id",
                "deployer-001",
                "--session",
                "train_teacher",
                "--command",
                "python train.py",
                "--log",
                "logs/train.log",
                "--tmux-bin",
                str(fake_tmux),
            ],
            cwd=project,
            check=False,
            env_update={"FAKE_TMUX_CALLS": str(tmp_path / "tmux-calls.jsonl")},
        )

        assert result.returncode == 2
        assert "collides with derived agent-status task id" in result.stderr
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["task.created"]


def test_runtime_retry_identity_rejects_reused_task_id():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "task",
                "create",
                "agent-reviewer-001",
                "--kind",
                "agent",
                "--title",
                "retry same id",
                "--owner",
                "Reviewer",
                "--status",
                "dispatching",
                "--next-expected-update",
                "2026-06-30T00:10:00Z",
                "--retry-of",
                "agent-reviewer-001",
            ],
            cwd=project,
            check=False,
        )

        assert result.returncode == 2
        assert "retry task must use a new task_id distinct from retry_of" in result.stderr


def test_runtime_retry_identity_accepts_new_task_id_with_retry_link():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "task",
                "create",
                "agent-reviewer-001-retry1",
                "--kind",
                "agent",
                "--title",
                "retry reviewer",
                "--owner",
                "Reviewer",
                "--status",
                "dispatching",
                "--next-expected-update",
                "2026-06-30T00:10:00Z",
                "--retry-of",
                "agent-reviewer-001",
            ],
            cwd=project,
        )

        task = json.loads(result.stdout)
        assert task["task_id"] == "agent-reviewer-001-retry1"
        assert task["retry_of"] == "agent-reviewer-001"


def test_runtime_task_blocked_status_is_counted_and_heartbeat_escalates():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_blocked",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--blocker",
                "detector runtime gate failed",
            ],
            cwd=project,
        )

        status = json.loads(run_lane(["status", "--json"], cwd=project).stdout)
        assert status["counts"]["blocked"] == 1

        heartbeat = json.loads(
            run_lane(["heartbeat", "--dry-run", "--now", "2026-06-30T00:01:00Z"], cwd=project).stdout
        )
        assert heartbeat["action_counts"]["escalated"] == 1
        assert heartbeat["actions"][0]["escalation_type"] == "blocked"


def test_runtime_task_ready_to_continue_does_not_use_heartbeat_escalation_path():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "phase_boundary_results_ready",
                "--kind",
                "phase_boundary",
                "--title",
                "experiment block ready for Leader orchestration",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "ready_to_continue",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--next-check-reason",
                "phase boundary prerequisites satisfied",
            ],
            cwd=project,
        )

        status = json.loads(run_lane(["status", "--json"], cwd=project).stdout)
        assert status["counts"]["ready_to_continue"] == 1

        heartbeat = json.loads(
            run_lane(["heartbeat", "--dry-run", "--now", "2026-06-30T00:01:00Z"], cwd=project).stdout
        )
        assert heartbeat["action_counts"] == {"escalated": 0, "healthy": 1, "skipped": 0}
        assert heartbeat["actions"][0]["status"] == "ready_to_continue"
        assert "escalation_type" not in heartbeat["actions"][0]
        assert not list((runtime_root(project) / "escalations").glob("*.json"))


def test_runtime_task_need_decision_heartbeat_still_escalates_due_decision():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_need_decision",
                "--kind",
                "experiment",
                "--title",
                "manual decision gate",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "need_decision",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--blocker",
                "human approval required before launch",
            ],
            cwd=project,
        )

        heartbeat = json.loads(
            run_lane(["heartbeat", "--dry-run", "--now", "2026-06-30T00:01:00Z"], cwd=project).stdout
        )
        assert heartbeat["action_counts"]["escalated"] == 1
        assert heartbeat["actions"][0]["status"] == "need_decision"
        assert heartbeat["actions"][0]["escalation_type"] == "due_decision"


def test_runtime_lease_acquire_writes_ttl_lock_and_event():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "heartbeat",
                "--ttl",
                "60",
                "--purpose",
                "probe escalation",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        lease = json.loads(result.stdout)
        assert lease["lease_id"] == "leader_session"
        assert lease["owner"] == "heartbeat"
        assert lease["purpose"] == "probe escalation"
        assert lease["acquired_at"] == "2026-06-30T00:00:00Z"
        assert lease["expires_at"] == "2026-06-30T00:01:00Z"
        assert (runtime_root(project) / "leases" / "leader_session.json").exists()
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["lease.acquired"]


def test_runtime_lease_acquire_rejects_unexpired_lease_held_by_other_owner():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "local",
                "--ttl",
                "60",
                "--purpose",
                "local control",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "bridge",
                "--ttl",
                "60",
                "--purpose",
                "remote control",
                "--now",
                "2026-06-30T00:00:30Z",
            ],
            cwd=project,
            check=False,
        )

        assert result.returncode == 2
        assert "lease held: leader_session by local until 2026-06-30T00:01:00Z" in result.stderr
        lease = json.loads((runtime_root(project) / "leases" / "leader_session.json").read_text(encoding="utf-8"))
        assert lease["owner"] == "local"


def test_runtime_lease_acquire_steals_expired_lease_and_records_event():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "local",
                "--ttl",
                "60",
                "--purpose",
                "local control",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "bridge",
                "--ttl",
                "60",
                "--purpose",
                "remote control",
                "--now",
                "2026-06-30T00:02:00Z",
            ],
            cwd=project,
        )

        lease = json.loads(result.stdout)
        assert lease["owner"] == "bridge"
        assert lease["expires_at"] == "2026-06-30T00:03:00Z"
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["lease.acquired", "lease.stolen", "lease.acquired"]
        assert events[1]["payload"]["previous_owner"] == "local"


def test_runtime_lease_release_requires_matching_owner():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "local",
                "--ttl",
                "60",
                "--purpose",
                "local control",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        wrong_owner = run_lane(
            ["runtime", "lease", "release", "leader_session", "--owner", "bridge"],
            cwd=project,
            check=False,
        )
        assert wrong_owner.returncode == 2
        assert "lease owner mismatch: leader_session held by local" in wrong_owner.stderr
        assert (runtime_root(project) / "leases" / "leader_session.json").exists()

        released = run_lane(["runtime", "lease", "release", "leader_session", "--owner", "local"], cwd=project)

        assert json.loads(released.stdout)["status"] == "released"
        assert not (runtime_root(project) / "leases" / "leader_session.json").exists()
        assert read_events(project)[-1]["event_type"] == "lease.released"


def test_status_json_does_not_require_lease():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "local",
                "--ttl",
                "60",
                "--purpose",
                "local control",
            ],
            cwd=project,
        )

        result = run_lane(["status", "--json"], cwd=project)

        assert json.loads(result.stdout)["derived"] is True


def test_runtime_control_intent_submit_appends_event_without_private_chat_identity():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        result = run_lane(
            [
                "runtime",
                "intent",
                "submit",
                "--action",
                "approve",
                "--risk-level",
                "low",
                "--confirmation-status",
                "not_required",
                "--target",
                '{"decision_id":"decision_001"}',
                "--source-entry",
                "feishu",
                "--archive-ref",
                "bridge://profile/archive/msg_001",
                "--lease-scope",
                "leader_session",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        intent = json.loads(result.stdout)
        assert intent["intent_id"].startswith("intent_")
        assert intent["source"] == {"entry": "feishu", "archive_ref": "bridge://profile/archive/msg_001"}
        assert intent["status"] == "pending"
        events = read_events(project)
        assert events[0]["event_type"] == "control_intent.submitted"
        assert events[0]["payload"] == intent
        runtime_text = (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8")
        assert "chat_id" not in runtime_text
        assert "open_id" not in runtime_text


def test_workflow_wakeup_plan_reports_blocked_candidate_without_runtime_writes():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--blocker",
                "needs maintainer decision",
            ],
            cwd=project,
        )
        before_events = (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8")

        result = run_lane(["workflow", "wakeup-plan", "--project", str(project), "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["dry_run"] is True
        assert payload["action"] == "acquire_lease"
        assert payload["next_action"] == "start_leader_turn"
        assert payload["reason"] == "escalation_candidate"
        assert payload["candidate"]["task_id"] == "task_001"
        assert payload["candidate"]["escalation_type"] == "blocked"
        assert payload["lease"]["lease_id"] == "leader_session"
        assert payload["lease"]["available"] is True
        assert (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8") == before_events
        assert not (runtime_root(project) / "summaries" / "current.json").exists()


def test_workflow_wakeup_plan_reports_phase_boundary_ready_candidate_and_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        outputs = project / "outputs"
        outputs.mkdir()
        (outputs / "results.json").write_text('{"ok": true}\n', encoding="utf-8")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "run_seed_1",
                "--kind",
                "experiment",
                "--title",
                "finished seed",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "ephemeral",
                "--heartbeat",
                "none",
                "--status",
                "completed",
            ],
            cwd=project,
        )
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "phase_boundary_results_ready",
                "--kind",
                "phase_boundary",
                "--title",
                "experiment block ready for Leader orchestration",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "ready_to_continue",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--next-check-reason",
                "all prerequisite experiment tasks completed",
                "--artifact",
                "outputs/results.json",
            ],
            cwd=project,
        )
        task_path = runtime_root(project) / "tasks" / "phase_boundary_results_ready.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["phase_boundary_evidence"] = {
            "prerequisite_task_ids": ["run_seed_1", "run_seed_2"],
            "required_artifacts": ["outputs/results.json"],
            "required_gate_verdicts": ["pass"],
            "required_reviewer_verdicts": [{"verdict": "pass"}],
            "next_leader_question": "choose result-to-claim or request an audit",
        }
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "run_seed_2",
                "--kind",
                "experiment",
                "--title",
                "finished seed two",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "ephemeral",
                "--heartbeat",
                "none",
                "--status",
                "resolved",
            ],
            cwd=project,
        )
        task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        before_events = (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8")

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["reason"] == "phase_boundary_ready"
        assert plan["candidate"]["task_id"] == "phase_boundary_results_ready"
        assert plan["candidate"]["status"] == "ready_to_continue"
        assert plan["candidate"]["category"] == "phase_boundary_ready"
        assert "escalation_type" not in plan["candidate"]
        assert plan["candidate"]["phase_boundary_evidence"]["next_leader_question"] == "choose result-to-claim or request an audit"
        assert plan["wakeup_key"] == "task:phase_boundary_results_ready:phase_boundary_ready:ready_to_continue"
        assert (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8") == before_events

        wakeup = json.loads(run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:05:10Z"], cwd=project).stdout)
        prompt = (project / wakeup["leader_prompt_ref"]).read_text(encoding="utf-8")
        assert "phase_boundary_ready" in prompt
        assert "ready_to_continue" in prompt
        assert "not a human approval request" in prompt
        assert "Escalation:" not in prompt
        assert "due_decision" not in prompt
        assert "old blocker" not in prompt
        assert "clean phase-boundary continuation" in prompt


def test_workflow_wakeup_plan_skips_ready_to_continue_without_phase_boundary_evidence():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "plain_ready_task",
                "--kind",
                "experiment",
                "--title",
                "plain executor ready",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "ready_to_continue",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["summary_counts"]["ready_to_continue"] == 1
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_skips_phase_boundary_when_required_artifact_is_missing():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "phase_boundary_missing_artifact",
                "--kind",
                "phase_boundary",
                "--title",
                "ready boundary without artifact",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "ready_to_continue",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        task_path = runtime_root(project) / "tasks" / "phase_boundary_missing_artifact.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["phase_boundary_evidence"] = {
            "required_artifacts": ["outputs/missing.json"],
            "next_leader_question": "choose next gate",
        }
        task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_skips_phase_boundary_when_prerequisite_not_successful():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "run_seed_pending",
                "--kind",
                "experiment",
                "--title",
                "pending seed",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "ephemeral",
                "--heartbeat",
                "none",
                "--status",
                "running",
            ],
            cwd=project,
        )
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "phase_boundary_pending_prereq",
                "--kind",
                "phase_boundary",
                "--title",
                "ready boundary with pending prereq",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "ready_to_continue",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        task_path = runtime_root(project) / "tasks" / "phase_boundary_pending_prereq.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["phase_boundary_evidence"] = {
            "prerequisite_task_ids": ["run_seed_pending"],
            "next_leader_question": "choose next gate",
        }
        task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_ignores_phase_boundary_ready_escalation_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        outputs = project / "outputs"
        outputs.mkdir()
        (outputs / "results.json").write_text('{"ok": true}\n', encoding="utf-8")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "phase_boundary_results_ready",
                "--kind",
                "phase_boundary",
                "--title",
                "experiment block ready for Leader orchestration",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "ready_to_continue",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        task_path = runtime_root(project) / "tasks" / "phase_boundary_results_ready.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["phase_boundary_evidence"] = {
            "required_artifacts": ["outputs/results.json"],
            "next_leader_question": "choose next gate",
        }
        task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        escalations = runtime_root(project) / "escalations"
        escalations.mkdir(parents=True, exist_ok=True)
        (escalations / "phase-boundary-ready.json").write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "escalation_id": "esc_phase_boundary_ready",
                    "task_id": "phase_boundary_results_ready",
                    "status": "ready_to_continue",
                    "escalation_type": "phase_boundary_ready",
                    "reason": "legacy mirror should not own wakeup key",
                    "resume_allowed": True,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["candidate"]["source"] == "runtime_task"
        assert plan["candidate"]["category"] == "phase_boundary_ready"
        assert plan["wakeup_key"] == "task:phase_boundary_results_ready:phase_boundary_ready:ready_to_continue"


def test_workflow_wakeup_plan_skips_when_leader_session_lease_is_active():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "local",
                "--ttl",
                "600",
                "--purpose",
                "local leader turn",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["action"] == "skip"
        assert payload["reason"] == "lease_unavailable"
        assert payload["lease"]["lease_id"] == "leader_session"
        assert payload["lease"]["holder"] == "local"


def test_workflow_wakeup_plan_skips_healthy_running_task():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "healthy experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "passive",
                "--status",
                "running",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["action"] == "skip"
        assert payload["reason"] == "healthy_or_no_escalation"
        assert payload["candidates"] == []


def test_workflow_wakeup_plan_escalates_stale_starting_agent_without_job_handle():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "coder-lost.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-lost",
                    "role": "Coder",
                    "status": "starting",
                    "task": "implement runtime patch",
                    "last_updated": "2026-06-30T00:00:00Z",
                    "current_action": "reading required context before test edits",
                    "next_expected_update": "2026-06-30T00:10:00Z",
                    "next_check_reason": "TDD implementation in progress",
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": None,
                    "transport": "local_agent",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        status = json.loads(run_lane(["status", "--json"], cwd=project).stdout)
        task = status["tasks"][0]
        assert status["counts"]["anomaly"] == 1
        assert task["task_id"] == "agent:coder-lost"
        assert task["status"] == "anomaly"
        assert task["heartbeat"] == "escalation_gated"
        assert "did not progress past starting" in task["blocker"]

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:30:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["reason"] == "escalation_candidate"
        assert plan["candidate"]["task_id"] == "agent:coder-lost"
        assert plan["candidate"]["escalation_type"] == "anomaly"


def test_workflow_wakeup_plan_escalates_stale_running_agent_after_expected_update():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "deployer-phase3-local.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "deployer-phase3-local",
                    "role": "Deployer",
                    "status": "blocked",
                    "task": "old blocked deployer",
                    "last_updated": "2026-06-29T23:00:00Z",
                    "current_action": "blocked on old gate",
                    "next_expected_update": None,
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": "old blocker",
                    "transport": "local_agent",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (agents / "deployer-r002-full-runtime-gate.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "deployer-r002-full-runtime-gate",
                    "role": "Deployer",
                    "status": "running",
                    "task": "new R002 full runtime gate",
                    "last_updated": "2026-06-30T00:00:00Z",
                    "current_action": "inspecting nonzero R002 gate result",
                    "next_expected_update": "2026-06-30T00:10:00Z",
                    "next_check_reason": "record result or blocker",
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": None,
                    "transport": "local_agent",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "wakeup.started",
                "--json",
                '{"wakeup_key":"task:agent:deployer-phase3-local:blocked:blocked"}',
            ],
            cwd=project,
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:30:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["summary_counts"]["stale"] == 1
        assert plan["candidate"]["task_id"] == "agent:deployer-r002-full-runtime-gate"
        assert plan["candidate"]["status"] == "stale"
        assert plan["candidate"]["escalation_type"] == "stale"
        assert plan["wakeup_key"] == "task:agent:deployer-r002-full-runtime-gate:stale:stale"
        assert plan["skipped_started_candidates"] == [
            {
                "task_id": "agent:deployer-phase3-local",
                "status": "blocked",
                "escalation_type": "blocked",
                "wakeup_key": "task:agent:deployer-phase3-local:blocked:blocked",
            }
        ]


def test_workflow_wakeup_plan_ignores_superseded_task_and_stale_escalation_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        escalations = runtime_root(project) / "escalations"
        agents.mkdir(parents=True)
        escalations.mkdir(parents=True)
        (agents / "coder-old.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-old",
                    "role": "Coder",
                    "status": "blocked",
                    "task": "old blocked config attempt",
                    "last_updated": "2026-06-30T00:00:00Z",
                    "current_action": "blocked on old gate",
                    "next_expected_update": None,
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": "old gate failed",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (escalations / "old.json").write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "escalation_id": "esc_old",
                    "task_id": "agent:coder-old",
                    "status": "blocked",
                    "escalation_type": "blocked",
                    "reason": "old gate failed",
                    "resume_allowed": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "task.superseded",
                "--task-id",
                "agent:coder-old",
                "--json",
                '{"resolved_by_task_id":"agent:coder-new","reason":"new task completed the replacement"}',
            ],
            cwd=project,
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:30:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["summary_counts"]["blocked"] == 0
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_ignores_leader_terminal_decision_and_stale_escalation_file():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        root = runtime_root(project)
        agents = root / "agents"
        escalations = root / "escalations"
        agents.mkdir(parents=True)
        escalations.mkdir(parents=True)
        (agents / "coder-old.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-old",
                    "role": "Coder",
                    "status": "blocked",
                    "task": "old config attempt",
                    "last_updated": "2026-06-30T00:00:00Z",
                    "current_action": "blocked on old gate",
                    "next_expected_update": None,
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": "old gate failed",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (escalations / "old.json").write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "escalation_id": "esc_old",
                    "task_id": "agent:coder-old",
                    "status": "blocked",
                    "escalation_type": "blocked",
                    "reason": "old gate failed",
                    "resume_allowed": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "leader.decision",
                "--task-id",
                "agent:coder-old",
                "--json",
                '{"action":"stop","status":"cancelled","reason":"Leader recorded terminal stale executor result"}',
            ],
            cwd=project,
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:30:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["summary_counts"]["blocked"] == 0
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_escalates_running_agent_without_deadline_after_grace():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "coder-no-deadline.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "coder-no-deadline",
                    "role": "Coder",
                    "status": "in_progress",
                    "task": "implement small patch",
                    "updated_at": "2026-06-30T00:00:00Z",
                    "current_action": "editing tests",
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": None,
                    "transport": "local_agent",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:20:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["summary_counts"]["stale"] == 1
        assert plan["candidate"]["task_id"] == "agent:coder-no-deadline"
        assert plan["candidate"]["status"] == "stale"
        assert plan["candidate"]["escalation_type"] == "stale"


def test_agent_without_deadline_but_with_job_handle_stays_running():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "deployer-job.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "deployer-job",
                    "role": "Deployer",
                    "status": "running",
                    "task": "train in tmux",
                    "updated_at": "2026-06-30T00:00:00Z",
                    "current_action": "training",
                    "job_handles": [{"type": "tmux", "session": "exp01"}],
                    "artifacts": [],
                    "blocker": None,
                    "transport": "local_agent",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:30:00Z"], cwd=project).stdout)
        status = json.loads(run_lane(["status", "--json"], cwd=project).stdout)

        assert status["counts"]["running"] == 1
        assert status["counts"]["stale"] == 0
        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"


def test_workflow_wakeup_plan_reports_completed_detached_tmux_job_for_leader_inspection():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_tmux = write_fake_tmux(tmp_path)
        (bin_dir / "tmux").symlink_to(fake_tmux)
        artifact = project / "outputs" / "epoch_2.pth"
        artifact.parent.mkdir()
        artifact.write_text("checkpoint\n", encoding="utf-8")
        env = {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "FAKE_TMUX_CALLS": str(tmp_path / "tmux-calls.jsonl"),
            "FAKE_TMUX_HAS_SESSION": "0",
        }
        exit_code_ref = ".labline/runtime/jobs/job_retry3.exitcode"
        exit_code_path = project / exit_code_ref
        exit_code_path.parent.mkdir(parents=True, exist_ok=True)
        exit_code_path.write_text("0\n", encoding="utf-8")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_train_retry3",
                "--kind",
                "agent",
                "--title",
                "train retry3",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "waiting_on_job",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--job-handle",
                '{"type":"tmux","session":"train_retry3","job_id":"job_retry3","exit_code_ref":".labline/runtime/jobs/job_retry3.exitcode"}',
                "--required-artifact",
                "outputs/epoch_2.pth",
            ],
            cwd=project,
        )

        plan = json.loads(
            run_lane(
                ["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"],
                cwd=project,
                env_update=env,
            ).stdout
        )

        assert plan["action"] == "acquire_lease"
        assert plan["reason"] == "escalation_candidate"
        assert plan["candidate"]["task_id"] == "task_train_retry3"
        assert plan["candidate"]["escalation_type"] == "detached_job_completed"
        assert plan["candidate"]["required_artifacts"] == ["outputs/epoch_2.pth"]
        assert plan["candidate"]["exit_codes"] == [
            {
                "session": "train_retry3",
                "exit_code": 0,
                "exit_code_ref": exit_code_ref,
            }
        ]
        calls = [json.loads(line)["args"] for line in (tmp_path / "tmux-calls.jsonl").read_text(encoding="utf-8").splitlines()]
        assert calls == [["has-session", "-t", "train_retry3"]]


def test_workflow_wakeup_plan_reports_nonzero_exit_even_when_artifact_exists():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_tmux = write_fake_tmux(tmp_path)
        (bin_dir / "tmux").symlink_to(fake_tmux)
        artifact = project / "outputs" / "epoch_2.pth"
        artifact.parent.mkdir()
        artifact.write_text("checkpoint\n", encoding="utf-8")
        exit_code_ref = ".labline/runtime/jobs/job_retry3.exitcode"
        exit_code_path = project / exit_code_ref
        exit_code_path.parent.mkdir(parents=True, exist_ok=True)
        exit_code_path.write_text("2\n", encoding="utf-8")
        env = {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "FAKE_TMUX_CALLS": str(tmp_path / "tmux-calls.jsonl"),
            "FAKE_TMUX_HAS_SESSION": "0",
        }
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_train_retry3",
                "--kind",
                "agent",
                "--title",
                "train retry3",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "waiting_on_job",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--job-handle",
                '{"type":"tmux","session":"train_retry3","job_id":"job_retry3","exit_code_ref":".labline/runtime/jobs/job_retry3.exitcode"}',
                "--required-artifact",
                "outputs/epoch_2.pth",
            ],
            cwd=project,
        )

        plan = json.loads(
            run_lane(
                ["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"],
                cwd=project,
                env_update=env,
            ).stdout
        )

        assert plan["action"] == "acquire_lease"
        assert plan["candidate"]["task_id"] == "task_train_retry3"
        assert plan["candidate"]["escalation_type"] == "detached_job_exited"
        assert "exit code is non-zero" in plan["candidate"]["reason"]
        assert plan["candidate"]["required_artifacts"] == ["outputs/epoch_2.pth"]
        assert plan["candidate"]["nonzero_exit_codes"] == [
            {
                "session": "train_retry3",
                "exit_code": 2,
                "exit_code_ref": exit_code_ref,
            }
        ]
        status = json.loads(
            run_lane(
                ["workflow", "job-status", "task_train_retry3", "--json"],
                cwd=project,
                env_update=env,
            ).stdout
        )
        assert status["job_observations"][0]["observation_status"] == "exited_failed"
        assert status["job_observations"][0]["exit_code"] == 2
        assert status["wakeup_candidate"]["escalation_type"] == "detached_job_exited"


def test_workflow_job_status_reports_tmux_observation_and_wakeup_candidate():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_tmux = write_fake_tmux(tmp_path)
        (bin_dir / "tmux").symlink_to(fake_tmux)
        artifact = project / "outputs" / "epoch_2.pth"
        artifact.parent.mkdir()
        artifact.write_text("checkpoint\n", encoding="utf-8")
        exit_code_ref = ".labline/runtime/jobs/job_retry3.exitcode"
        exit_code_path = project / exit_code_ref
        exit_code_path.parent.mkdir(parents=True, exist_ok=True)
        exit_code_path.write_text("0\n", encoding="utf-8")
        env = {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "FAKE_TMUX_CALLS": str(tmp_path / "tmux-calls.jsonl"),
            "FAKE_TMUX_HAS_SESSION": "0",
        }
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_train_retry3",
                "--kind",
                "agent",
                "--title",
                "train retry3",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "waiting_on_job",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--job-handle",
                '{"type":"tmux","session":"train_retry3","job_id":"job_retry3","exit_code_ref":".labline/runtime/jobs/job_retry3.exitcode"}',
                "--required-artifact",
                "outputs/epoch_2.pth",
            ],
            cwd=project,
        )

        status = json.loads(
            run_lane(
                ["workflow", "job-status", "task_train_retry3", "--json"],
                cwd=project,
                env_update=env,
            ).stdout
        )

        observation = status["job_observations"][0]
        assert observation["backend"] == "tmux"
        assert observation["session"] == "train_retry3"
        assert observation["session_active"] is False
        assert observation["exit_code"] == 0
        assert observation["observation_status"] == "exited_completed"
        assert observation["missing_artifacts"] == []
        assert status["wakeup_candidate"]["escalation_type"] == "detached_job_completed"


def test_workflow_wakeup_plan_reports_exited_detached_tmux_job_when_artifact_missing():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_tmux = write_fake_tmux(tmp_path)
        (bin_dir / "tmux").symlink_to(fake_tmux)
        env = {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "FAKE_TMUX_CALLS": str(tmp_path / "tmux-calls.jsonl"),
            "FAKE_TMUX_HAS_SESSION": "0",
        }
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_train_retry3",
                "--kind",
                "agent",
                "--title",
                "train retry3",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "waiting_on_job",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--job-handle",
                '{"type":"tmux","session":"train_retry3","job_id":"job_retry3"}',
                "--required-artifact",
                "outputs/epoch_2.pth",
            ],
            cwd=project,
        )

        plan = json.loads(
            run_lane(
                ["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"],
                cwd=project,
                env_update=env,
            ).stdout
        )

        assert plan["action"] == "acquire_lease"
        assert plan["candidate"]["task_id"] == "task_train_retry3"
        assert plan["candidate"]["escalation_type"] == "detached_job_exited"
        assert plan["candidate"]["missing_artifacts"] == ["outputs/epoch_2.pth"]


def test_workflow_wakeup_plan_skips_detached_tmux_job_while_session_is_active():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_tmux = write_fake_tmux(tmp_path)
        (bin_dir / "tmux").symlink_to(fake_tmux)
        artifact = project / "outputs" / "epoch_2.pth"
        artifact.parent.mkdir()
        artifact.write_text("checkpoint\n", encoding="utf-8")
        env = {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "FAKE_TMUX_CALLS": str(tmp_path / "tmux-calls.jsonl"),
            "FAKE_TMUX_HAS_SESSION": "1",
        }
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_train_retry3",
                "--kind",
                "agent",
                "--title",
                "train retry3",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "waiting_on_job",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--job-handle",
                '{"type":"tmux","session":"train_retry3","job_id":"job_retry3"}',
                "--required-artifact",
                "outputs/epoch_2.pth",
            ],
            cwd=project,
        )

        plan = json.loads(
            run_lane(
                ["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"],
                cwd=project,
                env_update=env,
            ).stdout
        )

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_blocks_high_risk_pending_control_intent():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "intent",
                "submit",
                "--intent-id",
                "intent_stop_001",
                "--action",
                "stop_task",
                "--risk-level",
                "high",
                "--confirmation-status",
                "required",
                "--target",
                '{"task_id":"task_001"}',
                "--source-entry",
                "feishu",
                "--archive-ref",
                "bridge://profile/archive/msg_002",
                "--lease-scope",
                "leader_session",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        before_events = (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8")

        result = run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["action"] == "needs_confirmation"
        assert payload["reason"] == "high_risk_intent_requires_confirmation"
        assert payload["intent"]["intent_id"] == "intent_stop_001"
        assert payload["intent"]["lease_scope"] == "leader_session"
        assert (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8") == before_events


def test_workflow_wakeup_plan_accepts_heartbeat_escalation_with_task_lease():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "anomalous experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "anomaly",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--blocker",
                "loss is NaN",
            ],
            cwd=project,
        )
        run_lane(["heartbeat", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        result = run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:10Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["action"] == "acquire_lease"
        assert payload["candidate"]["source"] == "runtime_escalation"
        assert payload["candidate"]["task_id"] == "task_001"
        assert payload["lease"]["lease_id"] == "leader_session"
        assert payload["lease"]["available"] is True


def test_workflow_wakeup_apply_acquires_leader_lease_writes_prompt_and_started_event():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--blocker",
                "needs maintainer decision",
            ],
            cwd=project,
        )

        result = run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["dry_run"] is False
        assert payload["action"] == "started"
        assert payload["backend"] == "prompt_only"
        assert payload["lease"]["lease_id"] == "leader_session"
        assert payload["lease"]["owner"] == "labline-wakeup"
        prompt_path = project / payload["leader_prompt_ref"]
        assert prompt_path.exists()
        prompt = prompt_path.read_text(encoding="utf-8")
        assert "blocked experiment" in prompt
        assert "task_001" in prompt
        assert "Write the user-facing final answer in Chinese" in prompt
        assert "English-only final decision" in prompt
        assert "最终回复必须使用中文" in prompt
        assert "chat_id" not in prompt
        assert "open_id" not in prompt
        assert (runtime_root(project) / "leases" / "leader_session.json").exists()
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["task.created", "lease.acquired", "wakeup.started"]
        assert events[-1]["payload"]["wakeup_key"] == payload["wakeup_key"]
        assert events[-1]["payload"]["leader_prompt_ref"] == payload["leader_prompt_ref"]


def test_workflow_wakeup_apply_does_not_duplicate_same_wakeup_after_restart():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        first = json.loads(run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)
        run_lane(["runtime", "lease", "release", "leader_session", "--owner", "labline-wakeup"], cwd=project)

        second = json.loads(run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:06:00Z"], cwd=project).stdout)

        assert first["action"] == "started"
        assert second["action"] == "skip"
        assert second["reason"] == "wakeup_already_started"
        events = read_events(project)
        assert [event["event_type"] for event in events].count("wakeup.started") == 1


def test_workflow_wakeup_plan_skips_already_started_wakeup_key():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        first = json.loads(run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)
        run_lane(["runtime", "lease", "release", "leader_session", "--owner", "labline-wakeup"], cwd=project)

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:06:00Z"], cwd=project).stdout)

        assert first["action"] == "started"
        assert plan["action"] == "skip"
        assert plan["reason"] == "wakeup_already_started"
        assert plan["wakeup_key"] == first["wakeup_key"]
        events = read_events(project)
        assert [event["event_type"] for event in events].count("wakeup.started") == 1


def test_workflow_wakeup_plan_force_retries_already_started_wakeup_key():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        first = json.loads(run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)
        run_lane(["runtime", "lease", "release", "leader_session", "--owner", "labline-wakeup"], cwd=project)

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--force", "--now", "2026-06-30T00:06:00Z"], cwd=project).stdout)

        assert first["action"] == "started"
        assert plan["action"] == "acquire_lease"
        assert plan["reason"] == "escalation_candidate"
        assert plan["force"] is True
        assert plan["force_reason"] == "user_requested_retry"
        assert plan["candidate"]["task_id"] == "task_001"
        assert plan["wakeup_key"] == first["wakeup_key"]
        assert plan["forced_started_candidates"] == [
            {
                "task_id": "task_001",
                "status": "blocked",
                "escalation_type": "blocked",
                "wakeup_key": first["wakeup_key"],
            }
        ]
        events = read_events(project)
        assert [event["event_type"] for event in events].count("wakeup.started") == 1


def test_workflow_wakeup_apply_force_records_retry_and_duplicates_started_key():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        first = json.loads(run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)
        run_lane(["runtime", "lease", "release", "leader_session", "--owner", "labline-wakeup"], cwd=project)

        second = json.loads(run_lane(["workflow", "wakeup", "--json", "--force", "--now", "2026-06-30T00:06:00Z"], cwd=project).stdout)

        assert first["action"] == "started"
        assert second["action"] == "started"
        assert second["force"] is True
        assert second["force_reason"] == "user_requested_retry"
        assert second["wakeup_key"] == first["wakeup_key"]
        events = read_events(project)
        event_types = [event["event_type"] for event in events]
        assert event_types.count("wakeup.started") == 2
        assert event_types.count("wakeup.retry_requested") == 1
        assert event_types[-3:] == ["wakeup.retry_requested", "lease.acquired", "wakeup.started"]
        started_keys = [event["payload"]["wakeup_key"] for event in events if event["event_type"] == "wakeup.started"]
        assert started_keys == [first["wakeup_key"], first["wakeup_key"]]
        retry_payload = next(event["payload"] for event in events if event["event_type"] == "wakeup.retry_requested")
        assert retry_payload["wakeup_key"] == first["wakeup_key"]
        assert retry_payload["candidate"]["task_id"] == "task_001"


def test_workflow_wakeup_plan_chooses_next_candidate_when_first_wakeup_already_started():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        for task_id in ["task_a", "task_b"]:
            run_lane(
                [
                    "runtime",
                    "task",
                    "create",
                    task_id,
                    "--kind",
                    "experiment",
                    "--title",
                    f"blocked {task_id}",
                    "--execution-mode",
                    "agent_turn",
                    "--durability",
                    "resumable",
                    "--heartbeat",
                    "escalation_gated",
                    "--status",
                    "blocked",
                    "--next-expected-update",
                    "2026-06-30T00:00:00Z",
                ],
                cwd=project,
            )
        run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "wakeup.started",
                "--json",
                '{"wakeup_key":"task:task_a:blocked:blocked"}',
            ],
            cwd=project,
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["candidate"]["task_id"] == "task_b"
        assert plan["wakeup_key"] == "task:task_b:blocked:blocked"
        assert plan["skipped_started_candidates"] == [
            {
                "task_id": "task_a",
                "status": "blocked",
                "escalation_type": "blocked",
                "wakeup_key": "task:task_a:blocked:blocked",
            }
        ]


def test_workflow_wakeup_plan_reports_unresolved_failed_terminal_runtime_task():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_failed_retry2",
                "--kind",
                "delegated_agent",
                "--title",
                "train retry2",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "waiting_on_job",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--job-handle",
                '{"type":"tmux","session":"retry2","job_id":"job_retry2"}',
            ],
            cwd=project,
        )
        run_lane(
            [
                "runtime",
                "task",
                "fail",
                "task_failed_retry2",
                "--blocker",
                "tmux session exited; log shows ModuleNotFoundError: No module named mmdet",
            ],
            cwd=project,
        )
        before_events = (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8")

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["reason"] == "escalation_candidate"
        assert plan["candidate"]["source"] == "runtime_task"
        assert plan["candidate"]["task_id"] == "task_failed_retry2"
        assert plan["candidate"]["status"] == "failed"
        assert plan["candidate"]["escalation_type"] == "terminal_result"
        assert plan["candidate"]["reason"] == "task reached terminal status failed"
        assert plan["wakeup_key"] == "task:task_failed_retry2:terminal_result:failed"
        assert (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8") == before_events
        assert not list((runtime_root(project) / "escalations").glob("*.json"))


def test_workflow_wakeup_plan_skips_failed_task_replaced_by_retry():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        for task_id, retry_of in [("task_old", None), ("task_retry2", "task_old")]:
            args = [
                "runtime",
                "task",
                "create",
                task_id,
                "--kind",
                "experiment",
                "--title",
                task_id,
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "running",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ]
            if retry_of:
                args.extend(["--retry-of", retry_of])
            run_lane(args, cwd=project)
            run_lane(["runtime", "task", "fail", task_id, "--blocker", "attempt failed"], cwd=project)

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["candidate"]["task_id"] == "task_retry2"
        assert [candidate["task_id"] for candidate in plan["candidates"]] == ["task_retry2"]


def test_workflow_wakeup_plan_skips_failed_terminal_task_after_leader_decision():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_failed_retry2",
                "--kind",
                "delegated_agent",
                "--title",
                "train retry2",
                "--execution-mode",
                "detached_job",
                "--durability",
                "supervised",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "waiting_on_job",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--job-handle",
                '{"type":"tmux","session":"retry2","job_id":"job_retry2"}',
            ],
            cwd=project,
        )
        run_lane(["runtime", "task", "fail", "task_failed_retry2", "--blocker", "dependency missing"], cwd=project)
        run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "leader.decision",
                "--task-id",
                "agent:task_failed_retry2",
                "--json",
                '{"action":"stop","status":"failed","affected_tasks":["task_failed_retry2"],"reason":"Leader recorded the terminal failure"}',
            ],
            cwd=project,
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_skips_derived_terminal_agent_status_without_runtime_task():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        agents = runtime_root(project) / "agents"
        agents.mkdir(parents=True)
        (agents / "old-deployer.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "agent_id": "old-deployer",
                    "role": "Deployer",
                    "status": "failed",
                    "task": "old terminal agent mirror",
                    "updated_at": "2026-06-30T00:00:00Z",
                    "job_handles": [],
                    "artifacts": [],
                    "blocker": "already handled outside runtime task protocol",
                    "transport": "local_agent",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_ignores_terminal_runtime_task_statuses():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_done",
                "--kind",
                "experiment",
                "--title",
                "completed task",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "running",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        run_lane(["runtime", "task", "complete", "task_done", "--artifact", "outputs/result.json"], cwd=project)

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_ignores_terminal_ready_to_continue_task():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "phase_boundary_consumed",
                "--kind",
                "phase_boundary",
                "--title",
                "consumed phase boundary",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "ready_to_continue",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        run_lane(["runtime", "task", "complete", "phase_boundary_consumed", "--artifact", "outputs/orchestration.json"], cwd=project)

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["candidates"] == []


def test_workflow_wakeup_apply_records_skipped_event_when_leader_lease_conflicts():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "leader_session",
                "--owner",
                "local",
                "--ttl",
                "600",
                "--purpose",
                "local leader turn",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["action"] == "skip"
        assert payload["reason"] == "lease_unavailable"
        events = read_events(project)
        assert [event["event_type"] for event in events] == ["task.created", "lease.acquired", "wakeup.skipped"]
        assert events[-1]["payload"]["reason"] == "lease_unavailable"


def test_workflow_wakeup_native_codex_runs_fake_codex_records_completed_and_releases_lease():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        fake_codex = write_fake_codex(tmp_path, message="native leader complete")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "wakeup",
                "--json",
                "--backend",
                "native-codex",
                "--codex-bin",
                str(fake_codex),
                "--codex-timeout",
                "30",
                "--now",
                "2026-06-30T00:05:00Z",
            ],
            cwd=project,
        )

        payload = json.loads(result.stdout)
        assert payload["action"] == "completed"
        assert payload["backend"] == "native-codex"
        assert payload["codex"]["returncode"] == 0
        output_path = project / payload["codex"]["output_ref"]
        assert output_path.read_text(encoding="utf-8").strip() == "native leader complete"
        record = json.loads((project / "fake-codex-record.json").read_text(encoding="utf-8"))
        assert payload["codex"]["sandbox"] == "danger-full-access"
        assert record["args"][:5] == ["exec", "-s", "danger-full-access", "-C", str(project)]
        assert "-o" in record["args"]
        assert "blocked experiment" in record["prompt"]
        assert not (runtime_root(project) / "leases" / "leader_session.json").exists()
        events = read_events(project)
        assert [event["event_type"] for event in events] == [
            "task.created",
            "lease.acquired",
            "wakeup.started",
            "wakeup.completed",
            "lease.released",
        ]
        assert events[-2]["payload"]["codex"]["output_ref"] == payload["codex"]["output_ref"]


def test_workflow_wakeup_native_codex_maps_labline_agent_proxy_env():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        fake_codex = write_fake_codex(tmp_path, message="native leader complete")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "wakeup",
                "--json",
                "--backend",
                "native-codex",
                "--codex-bin",
                str(fake_codex),
                "--now",
                "2026-06-30T00:05:00Z",
            ],
            cwd=project,
            env_update={
                "LABLINE_AGENT_HTTP_PROXY": "http://127.0.0.1:7897",
                "LABLINE_AGENT_HTTPS_PROXY": "http://127.0.0.1:7897",
                "LABLINE_AGENT_NO_PROXY": "localhost,127.0.0.1,::1",
                "http_proxy": "",
                "HTTP_PROXY": "",
                "https_proxy": "",
                "HTTPS_PROXY": "",
            },
        )

        payload = json.loads(result.stdout)
        assert payload["action"] == "completed"
        record = json.loads((project / "fake-codex-record.json").read_text(encoding="utf-8"))
        assert record["env"]["http_proxy"] == "http://127.0.0.1:7897"
        assert record["env"]["HTTP_PROXY"] == "http://127.0.0.1:7897"
        assert record["env"]["https_proxy"] == "http://127.0.0.1:7897"
        assert record["env"]["HTTPS_PROXY"] == "http://127.0.0.1:7897"
        assert record["env"]["no_proxy"] == "localhost,127.0.0.1,::1"
        assert record["env"]["NO_PROXY"] == "localhost,127.0.0.1,::1"


def test_workflow_wakeup_native_codex_failure_records_failed_and_releases_lease():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        project.mkdir()
        fake_codex = write_fake_codex(tmp_path, exit_code=7, message="partial output")
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "blocked experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "blocked",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(
            [
                "workflow",
                "wakeup",
                "--json",
                "--backend",
                "native-codex",
                "--codex-bin",
                str(fake_codex),
                "--now",
                "2026-06-30T00:05:00Z",
            ],
            cwd=project,
        )

        payload = json.loads(result.stdout)
        assert payload["action"] == "failed"
        assert payload["backend"] == "native-codex"
        assert payload["codex"]["returncode"] == 7
        assert payload["codex"]["sandbox"] == "danger-full-access"
        assert not (runtime_root(project) / "leases" / "leader_session.json").exists()
        events = read_events(project)
        assert [event["event_type"] for event in events] == [
            "task.created",
            "lease.acquired",
            "wakeup.started",
            "wakeup.failed",
            "lease.released",
        ]
        assert events[-2]["payload"]["codex"]["returncode"] == 7


def test_heartbeat_due_passive_task_records_healthy_check_without_escalation():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "monitor stable training",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "passive",
                "--status",
                "running",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(["heartbeat", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["dry_run"] is False
        assert payload["checked_count"] == 1
        assert payload["action_counts"] == {"escalated": 0, "healthy": 1, "skipped": 0}
        assert payload["actions"][0]["action"] == "healthy"
        assert payload["actions"][0]["task_id"] == "task_001"
        runner = json.loads((runtime_root(project) / "heartbeats" / "local-heartbeat.json").read_text(encoding="utf-8"))
        assert runner["runner"] == "local-heartbeat"
        assert runner["last_checked_at"] == "2026-06-30T00:05:00Z"
        assert runner["last_action_counts"] == {"escalated": 0, "healthy": 1, "skipped": 0}
        assert not list((runtime_root(project) / "escalations").glob("*.json"))
        assert not list((runtime_root(project) / "leases").glob("*.json"))
        event_types = [event["event_type"] for event in read_events(project)]
        assert event_types == ["task.created", "task.no_change_but_healthy", "heartbeat.checked"]


def test_heartbeat_terminal_task_writes_escalation_and_acquires_task_lease():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "train final model",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "running",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )
        run_lane(["runtime", "task", "complete", "task_001", "--artifact", "outputs/final.json"], cwd=project)

        result = run_lane(["heartbeat", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["action_counts"] == {"escalated": 1, "healthy": 0, "skipped": 0}
        assert payload["actions"][0]["action"] == "escalated"
        assert payload["actions"][0]["escalation_type"] == "terminal_result"
        escalations = list((runtime_root(project) / "escalations").glob("*.json"))
        assert len(escalations) == 1
        escalation = json.loads(escalations[0].read_text(encoding="utf-8"))
        assert escalation["task_id"] == "task_001"
        assert escalation["escalation_type"] == "terminal_result"
        assert escalation["lease_scope"] == "task:task_001"
        assert (runtime_root(project) / "leases" / "task-task_001.json").exists()
        event_types = [event["event_type"] for event in read_events(project)]
        assert event_types == ["task.created", "task.completed", "lease.acquired", "heartbeat.escalation", "heartbeat.checked"]


def test_heartbeat_skips_escalation_when_task_lease_is_held_by_another_owner():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "investigate anomaly",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "escalation_gated",
                "--status",
                "anomaly",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--blocker",
                "loss is NaN",
            ],
            cwd=project,
        )
        run_lane(
            [
                "runtime",
                "lease",
                "acquire",
                "task:task_001",
                "--owner",
                "local",
                "--ttl",
                "600",
                "--purpose",
                "manual investigation",
                "--now",
                "2026-06-30T00:00:00Z",
            ],
            cwd=project,
        )

        result = run_lane(["heartbeat", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["action_counts"] == {"escalated": 0, "healthy": 0, "skipped": 1}
        assert payload["actions"][0]["action"] == "skipped"
        assert payload["actions"][0]["reason"] == "lease_unavailable"
        assert not list((runtime_root(project) / "escalations").glob("*.json"))
        event_types = [event["event_type"] for event in read_events(project)]
        assert event_types == ["task.created", "lease.acquired", "heartbeat.skipped", "heartbeat.checked"]


def test_heartbeat_dry_run_reports_explicit_task_without_runtime_writes():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "future check",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--heartbeat",
                "passive",
                "--status",
                "running",
                "--next-expected-update",
                "2026-06-30T01:00:00Z",
            ],
            cwd=project,
        )
        before_events = (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8")

        result = run_lane(["heartbeat", "--task", "task_001", "--dry-run", "--now", "2026-06-30T00:05:00Z"], cwd=project)

        payload = json.loads(result.stdout)
        assert payload["dry_run"] is True
        assert payload["checked_count"] == 1
        assert payload["actions"][0]["task_id"] == "task_001"
        assert payload["actions"][0]["action"] == "healthy"
        assert payload["actions"][0]["forced"] is True
        assert not (runtime_root(project) / "heartbeats" / "local-heartbeat.json").exists()
        assert not list((runtime_root(project) / "escalations").glob("*.json"))
        assert (runtime_root(project) / "events" / "runtime.jsonl").read_text(encoding="utf-8") == before_events


def test_workflow_wakeup_plan_reports_expected_update_due_passive_waiting_task():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_wait_r006",
                "--kind",
                "agent",
                "--title",
                "wait for R006 checkpoint",
                "--owner",
                "Leader",
                "--parent-task-id",
                "task_train_r006",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "supervised",
                "--heartbeat",
                "passive",
                "--status",
                "waiting_on_job",
                "--current-action",
                "waiting for upstream R006 checkpoint",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--next-check-reason",
                "verify R006 epoch_300.pth before dispatching R007",
                "--required-artifact",
                "outputs/r007/epoch_300.pth",
            ],
            cwd=project,
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["reason"] == "expected_update_due"
        assert plan["candidate"]["task_id"] == "task_wait_r006"
        assert plan["candidate"]["category"] == "expected_update_due"
        assert plan["candidate"]["next_check_reason"] == "verify R006 epoch_300.pth before dispatching R007"
        assert plan["wakeup_key"] == "task:task_wait_r006:expected_update_due:waiting_on_job:2026-06-30T00:00:00Z"

        wakeup = json.loads(run_lane(["workflow", "wakeup", "--json", "--now", "2026-06-30T00:05:10Z"], cwd=project).stdout)
        prompt = (project / wakeup["leader_prompt_ref"]).read_text(encoding="utf-8")
        assert "Expected Update Due Context" in prompt
        assert "read-only Leader status check" in prompt
        assert "Do not restart jobs" in prompt


def test_workflow_wakeup_plan_limits_expected_update_due_to_waiting_or_recovery_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        for task_id, status, due_at in (
            ("future_wait", "waiting_on_job", "2026-06-30T00:30:00Z"),
            ("running_monitor", "running", "2026-06-30T00:00:00Z"),
        ):
            run_lane(
                [
                    "runtime",
                    "task",
                    "create",
                    task_id,
                    "--kind",
                    "agent",
                    "--title",
                    task_id,
                    "--execution-mode",
                    "agent_turn",
                    "--durability",
                    "supervised",
                    "--heartbeat",
                    "passive",
                    "--status",
                    status,
                    "--next-expected-update",
                    due_at,
                    "--next-check-reason",
                    "read-only status check",
                ],
                cwd=project,
            )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T00:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "skip"
        assert plan["reason"] == "healthy_or_no_escalation"
        assert plan["candidates"] == []


def test_workflow_wakeup_plan_uses_new_expected_update_for_repeat_due_check():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_wait_r006",
                "--kind",
                "agent",
                "--title",
                "wait for R006 checkpoint",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "supervised",
                "--heartbeat",
                "passive",
                "--status",
                "waiting_on_job",
                "--next-expected-update",
                "2026-06-30T00:00:00Z",
                "--next-check-reason",
                "first checkpoint check",
            ],
            cwd=project,
        )
        run_lane(
            [
                "runtime",
                "event",
                "append",
                "--type",
                "wakeup.started",
                "--task-id",
                "task_wait_r006",
                "--json",
                '{"wakeup_key":"task:task_wait_r006:expected_update_due:waiting_on_job:2026-06-30T00:00:00Z"}',
            ],
            cwd=project,
        )
        run_lane(
            [
                "runtime",
                "task",
                "update",
                "task_wait_r006",
                "--next-expected-update",
                "2026-06-30T01:00:00Z",
                "--next-check-reason",
                "second checkpoint check",
            ],
            cwd=project,
        )

        plan = json.loads(run_lane(["workflow", "wakeup-plan", "--json", "--now", "2026-06-30T01:05:00Z"], cwd=project).stdout)

        assert plan["action"] == "acquire_lease"
        assert plan["reason"] == "expected_update_due"
        assert plan["candidate"]["next_check_reason"] == "second checkpoint check"
        assert plan["wakeup_key"] == "task:task_wait_r006:expected_update_due:waiting_on_job:2026-06-30T01:00:00Z"
        assert plan["skipped_started_candidates"] == []
