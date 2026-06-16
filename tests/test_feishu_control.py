from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FEISHU_CONTROL = REPO_ROOT / "tools" / "feishu_control.py"


def run_control(args, check=True):
    return subprocess.run(
        [sys.executable, str(FEISHU_CONTROL), *args],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_register_list_and_switch_active_session():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "register", "--session-id", "executor-1", "--role", "executor", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "use", "--session-id", "executor-1"])

        result = run_control(["--state-root", str(root), "sessions", "--json"])
        data = json.loads(result.stdout)

        assert data["active_session_id"] == "executor-1"
        assert sorted(data["sessions"]) == ["executor-1", "leader-1"]
        assert data["sessions"]["leader-1"]["role"] == "leader"
        assert data["sessions"]["executor-1"]["project_root"] == "/repo/a"


def test_feishu_text_routes_to_active_or_addressed_session_inbox():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "register", "--session-id", "executor-1", "--role", "executor", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "use", "--session-id", "leader-1"])

        run_control(["--state-root", str(root), "handle-message", "--text", "$monitor-experiment 看一下", "--now", "2026-06-14T12:00:00Z"])
        run_control(["--state-root", str(root), "handle-message", "--text", "@executor-1 $tdd 继续", "--now", "2026-06-14T12:01:00Z"])

        leader_messages = read_jsonl(root / "inbox" / "leader-1.jsonl")
        executor_messages = read_jsonl(root / "inbox" / "executor-1.jsonl")

        assert leader_messages[-1]["text"] == "$monitor-experiment 看一下"
        assert leader_messages[-1]["source"] == "feishu"
        assert executor_messages[-1]["text"] == "$tdd 继续"
        assert executor_messages[-1]["source"] == "feishu"


def test_feishu_message_records_sender_for_session_and_inbox():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])

        run_control([
            "--state-root",
            str(root),
            "handle-message",
            "--text",
            "hi",
            "--sender-open-id",
            "ou_sender",
            "--now",
            "2026-06-14T12:00:00Z",
        ])

        state = json.loads((root / "sessions.json").read_text(encoding="utf-8"))
        messages = read_jsonl(root / "inbox" / "leader-1.jsonl")
        assert state["sessions"]["leader-1"]["last_sender_open_id"] == "ou_sender"
        assert messages[-1]["sender_open_id"] == "ou_sender"


def test_control_lease_blocks_local_input_until_release_or_expiry():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])

        run_control(["--state-root", str(root), "handle-message", "--text", "远程接管", "--now", "2026-06-14T12:00:00Z", "--lease-ttl-seconds", "60"])

        blocked = run_control(
            ["--state-root", str(root), "local-input", "--session-id", "leader-1", "--text", "本地输入", "--now", "2026-06-14T12:00:30Z"],
            check=False,
        )
        assert blocked.returncode == 2
        assert json.loads(blocked.stdout)["status"] == "blocked_by_feishu"

        run_control(["--state-root", str(root), "handle-message", "--text", "/release", "--now", "2026-06-14T12:00:40Z"])
        allowed = run_control(["--state-root", str(root), "local-input", "--session-id", "leader-1", "--text", "本地恢复", "--now", "2026-06-14T12:00:41Z"])
        assert json.loads(allowed.stdout)["status"] == "queued"

        run_control(["--state-root", str(root), "handle-message", "--text", "远程再次接管", "--now", "2026-06-14T12:01:00Z", "--lease-ttl-seconds", "10"])
        expired = run_control(["--state-root", str(root), "local-input", "--session-id", "leader-1", "--text", "超时后本地输入", "--now", "2026-06-14T12:01:11Z"])
        assert json.loads(expired.stdout)["status"] == "queued"


def test_remote_action_approval_is_single_action_code_and_expires():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(
            [
                "--state-root",
                str(root),
                "request-approval",
                "--session-id",
                "leader-1",
                "--action-id",
                "act-1",
                "--description",
                "git push origin dev",
                "--code",
                "A1B2C3",
                "--now",
                "2026-06-14T12:00:00Z",
                "--ttl-seconds",
                "60",
            ]
        )

        wrong = run_control(["--state-root", str(root), "handle-message", "--text", "/approve WRONG", "--now", "2026-06-14T12:00:10Z"], check=False)
        assert wrong.returncode == 3
        assert json.loads(wrong.stdout)["status"] == "unknown_approval_code"

        ok = run_control(["--state-root", str(root), "handle-message", "--text", "/approve A1B2C3", "--now", "2026-06-14T12:00:20Z"])
        assert json.loads(ok.stdout)["status"] == "approved"

        second = run_control(["--state-root", str(root), "handle-message", "--text", "/approve A1B2C3", "--now", "2026-06-14T12:00:21Z"], check=False)
        assert second.returncode == 3
        assert json.loads(second.stdout)["status"] == "approval_already_resolved"

        run_control(
            [
                "--state-root",
                str(root),
                "request-approval",
                "--session-id",
                "leader-1",
                "--action-id",
                "act-2",
                "--description",
                "rsync --delete",
                "--code",
                "D4E5F6",
                "--now",
                "2026-06-14T12:00:00Z",
                "--ttl-seconds",
                "5",
            ]
        )
        expired = run_control(["--state-root", str(root), "handle-message", "--text", "/approve D4E5F6", "--now", "2026-06-14T12:00:06Z"], check=False)
        assert expired.returncode == 3
        assert json.loads(expired.stdout)["status"] == "approval_expired"


def test_bridge_commands_do_not_execute_tools_or_shell():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])

        run_command = run_control(["--state-root", str(root), "handle-message", "--text", "/run ls"], check=False)
        tool_command = run_control(["--state-root", str(root), "handle-message", "--text", "/tool Bash"], check=False)
        skill_text = run_control(["--state-root", str(root), "handle-message", "--text", "$monitor-experiment 看一下"])

        assert run_command.returncode == 4
        assert json.loads(run_command.stdout)["status"] == "unsupported_command"
        assert tool_command.returncode == 4
        assert json.loads(tool_command.stdout)["status"] == "unsupported_command"
        assert json.loads(skill_text.stdout)["status"] == "queued"
        messages = read_jsonl(root / "inbox" / "leader-1.jsonl")
        assert messages[-1]["text"] == "$monitor-experiment 看一下"


def test_interrupt_and_btw_commands_are_queued_for_runner():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])

        interrupt = run_control(["--state-root", str(root), "handle-message", "--text", "/interrupt"])
        btw = run_control(["--state-root", str(root), "handle-message", "--text", "/btw 记得检查日志"])

        assert json.loads(interrupt.stdout)["status"] == "queued"
        assert json.loads(btw.stdout)["status"] == "queued"
        messages = read_jsonl(root / "inbox" / "leader-1.jsonl")
        assert messages[-2]["text"] == "/interrupt"
        assert messages[-1]["text"] == "/btw 记得检查日志"


def test_session_response_is_recorded_in_outbox():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])

        result = run_control(
            [
                "--state-root",
                str(root),
                "respond",
                "--session-id",
                "leader-1",
                "--text",
                "实验还在跑",
                "--now",
                "2026-06-14T12:00:00Z",
            ]
        )

        assert json.loads(result.stdout)["status"] == "queued"
        responses = read_jsonl(root / "outbox" / "leader-1.jsonl")
        assert responses[-1]["text"] == "实验还在跑"
        assert responses[-1]["delivery_status"] == "pending"
