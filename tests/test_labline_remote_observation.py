from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REMOTE_OBSERVATION = REPO_ROOT / "tools" / "labline_remote_observation.py"
LANE_CLI = REPO_ROOT / "tools" / "lane"


def run_remote(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, str(REMOTE_OBSERVATION), *args],
        cwd=str(cwd or REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"remote observation failed: {result.stderr}\nstdout:\n{result.stdout}")
    return result


def run_lane(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["LABLINE_WORKSPACE"] = str(cwd.parent)
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


def all_runtime_text(project: Path) -> str:
    root = project / ".labline" / "runtime"
    if not root.exists():
        return ""
    chunks = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def test_archive_and_follow_are_bridge_owned_without_project_identity_leak():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(["runtime", "init"], cwd=project)

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
                    "oc_secret_chat",
                    "--sender-open-id",
                    "ou_secret_sender",
                    "--message-id",
                    "om_001",
                    "--text",
                    "现在怎么样了",
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )

        followed = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "follow",
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--project",
                    str(project),
                    "--chat-id",
                    "oc_secret_chat",
                    "--archive-ref",
                    archived["archive_ref"],
                    "--now",
                    "2026-06-30T00:00:01Z",
                ]
            ).stdout
        )

        assert archived["archive_ref"].startswith("bridge://labline-codex/")
        assert "oc_secret_chat" not in json.dumps(followed)
        assert "ou_secret_sender" not in json.dumps(followed)
        archive_text = "\n".join(path.read_text() for path in (state_root / "archive").glob("*.json"))
        subscription_text = "\n".join(path.read_text() for path in (state_root / "subscriptions").glob("*.json"))
        assert "oc_secret_chat" in archive_text
        assert "ou_secret_sender" in archive_text
        assert "oc_secret_chat" in subscription_text
        runtime_text = all_runtime_text(project)
        assert "oc_secret_chat" not in runtime_text
        assert "ou_secret_sender" not in runtime_text
        assert "现在怎么样了" not in runtime_text


def test_follow_uses_stable_subscription_and_delivery_key_for_dedupe():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
        project = Path(tmp) / "project"
        project.mkdir()
        common = [
            "--state-root",
            str(state_root),
            "follow",
            "--profile",
            "labline-codex",
            "--workspace",
            "workspace-001",
            "--project",
            str(project),
            "--chat-id",
            "oc_secret_chat",
            "--task-id",
            "task_001",
        ]

        first = json.loads(run_remote([*common, "--archive-ref", "bridge://p/w/archive/a1"]).stdout)
        second = json.loads(run_remote([*common, "--archive-ref", "bridge://p/w/archive/a2"]).stdout)

        assert first["subscription_id"] == second["subscription_id"]
        assert first["delivery_key"] == second["delivery_key"]
        subscriptions = list((state_root / "subscriptions").glob("*.json"))
        assert len(subscriptions) == 1
        stored = json.loads(subscriptions[0].read_text())
        assert stored["archive_ref"] == "bridge://p/w/archive/a2"


def test_delivery_targets_lists_active_project_or_task_follow_chats():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
        project = Path(tmp) / "project"
        other_project = Path(tmp) / "other-project"
        project.mkdir()
        other_project.mkdir()

        common = [
            "--state-root",
            str(state_root),
            "follow",
            "--profile",
            "labline-codex",
            "--workspace",
            "workspace-001",
            "--archive-ref",
            "bridge://p/w/archive/a1",
        ]
        run_remote([*common, "--project", str(project), "--chat-id", "oc_project"])
        run_remote([*common, "--project", str(project), "--chat-id", "oc_task", "--task-id", "task_001"])
        run_remote([*common, "--project", str(project), "--chat-id", "oc_other_task", "--task-id", "task_002"])
        run_remote([*common, "--project", str(other_project), "--chat-id", "oc_other_project"])
        run_remote(
            [
                "--state-root",
                str(state_root),
                "follow",
                "--profile",
                "other-profile",
                "--workspace",
                "workspace-001",
                "--project",
                str(project),
                "--chat-id",
                "oc_other_profile",
                "--archive-ref",
                "bridge://p/w/archive/a2",
            ]
        )

        targets = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "delivery-targets",
                    "--profile",
                    "labline-codex",
                    "--project",
                    str(project),
                    "--task-id",
                    "task_001",
                ]
            ).stdout
        )

        chat_ids = {target["chat_id"] for target in targets["targets"]}
        assert chat_ids == {"oc_project", "oc_task"}
        assert {target["profile"] for target in targets["targets"]} == {"labline-codex"}

        cross_profile_targets = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "delivery-targets",
                    "--profile",
                    "visdrone-repro",
                    "--project",
                    str(project),
                    "--task-id",
                    "task_001",
                    "--include-cross-profile",
                ]
            ).stdout
        )

        cross_profile_chat_ids = {target["chat_id"] for target in cross_profile_targets["targets"]}
        assert cross_profile_chat_ids == {"oc_project", "oc_task", "oc_other_profile"}
        assert cross_profile_targets["include_cross_profile"] is True


def test_projection_plan_throttles_progress_but_fresh_replies_on_terminal():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
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
                "run experiment",
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
        followed = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "follow",
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--project",
                    str(project),
                    "--chat-id",
                    "oc_secret_chat",
                    "--task-id",
                    "task_001",
                    "--archive-ref",
                    "bridge://p/w/archive/a1",
                ]
            ).stdout
        )
        first_plan = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )
        assert first_plan["action"] == "patch"

        run_remote(
            [
                "--state-root",
                str(state_root),
                "delivery-record",
                "--delivery-key",
                first_plan["delivery_key"],
                "--subscription-id",
                followed["subscription_id"],
                "--projection-id",
                first_plan["projection_id"],
                "--status",
                "delivered",
                "--state-signature",
                first_plan["state_signature"],
                "--throttle-seconds",
                "600",
                "--now",
                "2026-06-30T00:00:00Z",
            ]
        )
        throttled = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:01:00Z",
                ]
            ).stdout
        )
        assert throttled["action"] == "skip"
        assert throttled["reason"] == "throttled_no_significant_change"

        run_lane(["runtime", "task", "complete", "task_001"], cwd=project)
        terminal = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:02:00Z",
                ]
            ).stdout
        )

        assert terminal["action"] == "fresh_reply"
        assert terminal["reason"] == "terminal"
        assert "oc_secret_chat" not in all_runtime_text(project)


def test_projection_plan_carries_previous_message_id_for_visible_patch_update():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
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
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "running",
                "--current-action",
                "queued",
            ],
            cwd=project,
        )
        followed = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "follow",
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--project",
                    str(project),
                    "--chat-id",
                    "oc_secret_chat",
                    "--task-id",
                    "task_001",
                    "--archive-ref",
                    "bridge://p/w/archive/a1",
                ]
            ).stdout
        )
        first_plan = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )
        assert first_plan["action"] == "patch"
        assert "previous_message_id" not in first_plan

        run_remote(
            [
                "--state-root",
                str(state_root),
                "delivery-record",
                "--delivery-key",
                first_plan["delivery_key"],
                "--subscription-id",
                followed["subscription_id"],
                "--projection-id",
                first_plan["projection_id"],
                "--status",
                "delivered",
                "--state-signature",
                first_plan["state_signature"],
                "--message-id",
                "om_status_card",
                "--delivery-mode",
                "card",
                "--now",
                "2026-06-30T00:00:00Z",
            ]
        )
        run_lane(
            [
                "runtime",
                "task",
                "update",
                "task_001",
                "--status",
                "running",
                "--current-action",
                "running detector gate",
            ],
            cwd=project,
        )

        second_plan = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:01:00Z",
                ]
            ).stdout
        )

        assert second_plan["action"] == "patch"
        assert second_plan["previous_message_id"] == "om_status_card"
        assert second_plan["previous_delivery_mode"] == "card"
        stored = json.loads((state_root / "deliveries" / f"{first_plan['delivery_key']}.json").read_text())
        assert stored["message_id"] == "om_status_card"
        assert stored["delivery_mode"] == "card"


def test_projection_plan_fresh_replies_on_blocked_task_without_waiting_for_throttle():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
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
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "running",
            ],
            cwd=project,
        )
        followed = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "follow",
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--project",
                    str(project),
                    "--chat-id",
                    "oc_secret_chat",
                    "--task-id",
                    "task_blocked",
                    "--archive-ref",
                    "bridge://p/w/archive/a1",
                ]
            ).stdout
        )
        first_plan = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )
        run_remote(
            [
                "--state-root",
                str(state_root),
                "delivery-record",
                "--delivery-key",
                first_plan["delivery_key"],
                "--subscription-id",
                followed["subscription_id"],
                "--projection-id",
                first_plan["projection_id"],
                "--status",
                "delivered",
                "--state-signature",
                first_plan["state_signature"],
                "--throttle-seconds",
                "600",
                "--now",
                "2026-06-30T00:00:00Z",
            ]
        )

        run_lane(
            [
                "runtime",
                "task",
                "update",
                "task_blocked",
                "--status",
                "blocked",
                "--current-action",
                "blocked on detector runtime",
                "--blocker",
                "ignore flags dropped before model input",
            ],
            cwd=project,
        )
        blocked = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:01:00Z",
                ]
            ).stdout
        )

        assert blocked["action"] == "fresh_reply"
        assert blocked["reason"] == "blocked"


def test_projection_plan_fresh_replies_when_active_card_state_goes_stale():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_stuck",
                "--kind",
                "experiment",
                "--title",
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "running",
                "--current-action",
                "正在调用工具",
                "--next-expected-update",
                "2026-06-30T00:05:00Z",
            ],
            cwd=project,
        )
        followed = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "follow",
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--project",
                    str(project),
                    "--chat-id",
                    "oc_secret_chat",
                    "--task-id",
                    "task_stuck",
                    "--archive-ref",
                    "bridge://p/w/archive/a1",
                ]
            ).stdout
        )
        first_plan = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )
        assert first_plan["action"] == "patch"
        run_remote(
            [
                "--state-root",
                str(state_root),
                "delivery-record",
                "--delivery-key",
                first_plan["delivery_key"],
                "--subscription-id",
                followed["subscription_id"],
                "--projection-id",
                first_plan["projection_id"],
                "--status",
                "delivered",
                "--state-signature",
                first_plan["state_signature"],
                "--throttle-seconds",
                "600",
                "--now",
                "2026-06-30T00:00:00Z",
            ]
        )

        before_grace = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:06:00Z",
                ]
            ).stdout
        )
        assert before_grace["action"] == "skip"

        stale = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:11:00Z",
                ]
            ).stdout
        )
        assert stale["action"] == "fresh_reply"
        assert stale["reason"] == "stale_projection"
        assert stale["attention_hint"]["kind"] == "stale_projection"
        assert stale["attention_hint"]["task_id"] == "task_stuck"

        run_remote(
            [
                "--state-root",
                str(state_root),
                "delivery-record",
                "--delivery-key",
                stale["delivery_key"],
                "--subscription-id",
                followed["subscription_id"],
                "--projection-id",
                stale["projection_id"],
                "--status",
                "delivered",
                "--state-signature",
                stale["state_signature"],
                "--reason",
                stale["reason"],
                "--now",
                "2026-06-30T00:11:00Z",
            ]
        )
        repeated = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:12:00Z",
                ]
            ).stdout
        )
        assert repeated["action"] == "skip"
        assert repeated["reason"] == "already_delivered"


def test_projection_poll_fresh_replies_once_for_same_urgent_state():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
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
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "blocked",
                "--current-action",
                "blocked on detector runtime",
                "--blocker",
                "ignore flags dropped before model input",
            ],
            cwd=project,
        )
        followed = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "follow",
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--project",
                    str(project),
                    "--chat-id",
                    "oc_secret_chat",
                    "--task-id",
                    "task_blocked",
                    "--archive-ref",
                    "bridge://p/w/archive/a1",
                ]
            ).stdout
        )

        first_poll = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-poll",
                    "--profile",
                    "labline-codex",
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )
        assert len(first_poll["plans"]) == 1
        plan = first_poll["plans"][0]
        assert plan["action"] == "fresh_reply"
        assert plan["reason"] == "blocked"
        assert plan["chat_id"] == "oc_secret_chat"
        assert plan["project_root"] == str(project)

        run_remote(
            [
                "--state-root",
                str(state_root),
                "delivery-record",
                "--delivery-key",
                plan["delivery_key"],
                "--subscription-id",
                followed["subscription_id"],
                "--projection-id",
                plan["projection_id"],
                "--status",
                "delivered",
                "--state-signature",
                plan["state_signature"],
                "--now",
                "2026-06-30T00:00:00Z",
            ]
        )
        repeated_plan = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:01:00Z",
                ]
            ).stdout
        )
        assert repeated_plan["action"] == "skip"
        assert repeated_plan["reason"] == "already_delivered"

        second_poll = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-poll",
                    "--profile",
                    "labline-codex",
                    "--now",
                    "2026-06-30T00:01:00Z",
                ]
            ).stdout
        )
        assert second_poll["plans"] == []


def test_projection_poll_can_include_cross_profile_subscriptions_for_same_project():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
        project = Path(tmp) / "project"
        other_project = Path(tmp) / "other-project"
        project.mkdir()
        other_project.mkdir()
        run_lane(
            [
                "runtime",
                "task",
                "create",
                "task_001",
                "--kind",
                "experiment",
                "--title",
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
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
                "other_task",
                "--kind",
                "experiment",
                "--title",
                "other experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "running",
            ],
            cwd=other_project,
        )
        common = [
            "--state-root",
            str(state_root),
            "follow",
            "--workspace",
            "workspace-001",
            "--archive-ref",
            "bridge://p/w/archive/a1",
        ]
        followed = json.loads(
            run_remote(
                [
                    *common,
                    "--profile",
                    "labline-codex",
                    "--project",
                    str(project),
                    "--chat-id",
                    "oc_old_profile",
                ]
            ).stdout
        )
        run_remote(
            [
                *common,
                "--profile",
                "labline-codex",
                "--project",
                str(other_project),
                "--chat-id",
                "oc_other_project",
            ]
        )

        same_profile_only = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-poll",
                    "--profile",
                    "visdrone-repro",
                    "--project",
                    str(project),
                ]
            ).stdout
        )
        cross_profile = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-poll",
                    "--profile",
                    "visdrone-repro",
                    "--project",
                    str(project),
                    "--include-cross-profile",
                ]
            ).stdout
        )

        assert same_profile_only["plans"] == []
        assert len(cross_profile["plans"]) == 1
        plan = cross_profile["plans"][0]
        assert plan["subscription_id"] == followed["subscription_id"]
        assert plan["chat_id"] == "oc_old_profile"
        assert plan["project_root"] == str(project)
        assert cross_profile["include_cross_profile"] is True


def test_delivery_failure_updates_bridge_state_without_changing_task_verdict():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
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
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "ephemeral",
            ],
            cwd=project,
        )
        run_lane(["runtime", "task", "complete", "task_001"], cwd=project)
        task_path = project / ".labline" / "runtime" / "tasks" / "task_001.json"
        before_task = task_path.read_text(encoding="utf-8")
        followed = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "follow",
                    "--profile",
                    "labline-codex",
                    "--workspace",
                    "workspace-001",
                    "--project",
                    str(project),
                    "--chat-id",
                    "oc_secret_chat",
                    "--task-id",
                    "task_001",
                    "--archive-ref",
                    "bridge://p/w/archive/a1",
                ]
            ).stdout
        )
        plan = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "projection-plan",
                    "--project",
                    str(project),
                    "--subscription-id",
                    followed["subscription_id"],
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )

        run_remote(
            [
                "--state-root",
                str(state_root),
                "delivery-record",
                "--delivery-key",
                plan["delivery_key"],
                "--subscription-id",
                followed["subscription_id"],
                "--projection-id",
                plan["projection_id"],
                "--status",
                "failed",
                "--state-signature",
                plan["state_signature"],
                "--error",
                "network timeout",
                "--now",
                "2026-06-30T00:00:01Z",
            ]
        )

        delivery = json.loads((state_root / "deliveries" / f"{plan['delivery_key']}.json").read_text())
        assert delivery["status"] == "failed"
        assert delivery["error"] == "network timeout"
        assert task_path.read_text(encoding="utf-8") == before_task
        assert "network timeout" not in all_runtime_text(project)


def test_route_status_question_to_observation_without_tui_injection_or_identity_leak():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
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
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "running",
            ],
            cwd=project,
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
                    "bridge://p/w/archive/status1",
                    "--text",
                    "现在怎么样了",
                    "--sender-open-id",
                    "ou_secret_sender",
                    "--chat-id",
                    "oc_secret_chat",
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )

        assert routed["route"] == "observation"
        assert routed["action"] == "status_projection"
        assert routed["inject_tui"] is False
        runtime_text = all_runtime_text(project)
        assert "remote_message.routed" in runtime_text
        assert "现在怎么样了" not in runtime_text
        assert "ou_secret_sender" not in runtime_text
        assert "oc_secret_chat" not in runtime_text


def test_route_read_only_side_question_to_continuous_btw_thread():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
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
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "running",
            ],
            cwd=project,
        )

        first = json.loads(
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
                    "bridge://p/w/archive/btw1",
                    "--text",
                    "顺便解释一下结果含义",
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )
        second = json.loads(
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
                    "bridge://p/w/archive/btw2",
                    "--text",
                    "为什么",
                    "--now",
                    "2026-06-30T00:01:00Z",
                ]
            ).stdout
        )

        assert first["route"] == "btw"
        assert first["read_only"] is True
        assert second["route"] == "btw"
        assert second["btw_thread_id"] == first["btw_thread_id"]
        thread = json.loads((state_root / "btw_threads" / f"{first['btw_thread_id']}.json").read_text())
        assert thread["archive_refs"] == ["bridge://p/w/archive/btw1", "bridge://p/w/archive/btw2"]
        thread_text = json.dumps(thread, ensure_ascii=False)
        assert "顺便解释一下结果含义" not in thread_text
        runtime_text = all_runtime_text(project)
        assert "btw.question_received" in runtime_text
        assert "顺便解释一下结果含义" not in runtime_text


def test_explicit_btw_command_overrides_status_question_routing():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(["runtime", "init"], cwd=project)

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
                    "bridge://p/w/archive/btw-status",
                    "--text",
                    "/btw 当前做到哪了",
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )

        assert routed["route"] == "btw"
        assert routed["route_reason"] == "explicit_btw_command"
        assert routed["read_only"] is True
        assert "btw_thread_id" in routed
        runtime_text = all_runtime_text(project)
        assert "btw.question_received" in runtime_text
        assert "当前做到哪了" not in runtime_text


def test_route_stop_request_to_control_intent_not_btw():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
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
                "run experiment",
                "--execution-mode",
                "agent_turn",
                "--durability",
                "resumable",
                "--status",
                "running",
            ],
            cwd=project,
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
                    "bridge://p/w/archive/stop1",
                    "--text",
                    "停掉这个实验",
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )

        assert routed["route"] == "control_intent"
        assert routed["action"] == "stop_task"
        assert routed["risk_level"] == "high"
        assert routed["read_only"] is False
        runtime_text = all_runtime_text(project)
        assert "control_intent.submitted" in runtime_text
        assert "btw.question_received" not in runtime_text
        assert "停掉这个实验" not in runtime_text


def test_route_new_work_to_normal_project_interaction_when_no_active_task():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
        project = Path(tmp) / "project"
        project.mkdir()
        run_lane(["runtime", "init"], cwd=project)

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
                    "bridge://p/w/archive/new1",
                    "--text",
                    "新开一个分析任务",
                    "--now",
                    "2026-06-30T00:00:00Z",
                ]
            ).stdout
        )

        assert routed["route"] == "normal_project_interaction"
        assert routed["action"] == "create_or_queue_task"
        assert routed["risk_level"] == "medium"
        assert routed["inject_tui"] is False
        runtime_text = all_runtime_text(project)
        assert "remote_message.routed" in runtime_text
        assert "btw.question_received" not in runtime_text
        assert "control_intent.submitted" not in runtime_text
        assert "新开一个分析任务" not in runtime_text


def test_btw_answer_records_sanitized_answer_event():
    with tempfile.TemporaryDirectory() as tmp:
        state_root = Path(tmp) / "bridge-state"
        project = Path(tmp) / "project"
        project.mkdir()
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
                    "bridge://p/w/archive/btw1",
                    "--text",
                    "顺便解释一下",
                ]
            ).stdout
        )

        answered = json.loads(
            run_remote(
                [
                    "--state-root",
                    str(state_root),
                    "btw-answer",
                    "--project",
                    str(project),
                    "--btw-thread-id",
                    routed["btw_thread_id"],
                    "--archive-ref",
                    "bridge://p/w/archive/answer1",
                    "--answer-ref",
                    "bridge://p/w/answers/answer1",
                    "--text",
                    "这里是解释正文",
                    "--now",
                    "2026-06-30T00:02:00Z",
                ]
            ).stdout
        )

        assert answered["status"] == "answered"
        thread = json.loads((state_root / "btw_threads" / f"{routed['btw_thread_id']}.json").read_text())
        assert thread["answer_refs"] == ["bridge://p/w/answers/answer1"]
        assert "这里是解释正文" not in json.dumps(thread, ensure_ascii=False)
        runtime_text = all_runtime_text(project)
        assert "btw.answered" in runtime_text
        assert "这里是解释正文" not in runtime_text
