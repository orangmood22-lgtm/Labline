from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FEISHU_CONTROL = REPO_ROOT / "tools" / "feishu_control.py"
ARIS_FEISHU_SESSION = REPO_ROOT / "tools" / "aris_feishu_session.py"


def run_control(args):
    return subprocess.run(
        [sys.executable, str(FEISHU_CONTROL), *args],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def run_session(args, check=True):
    return subprocess.run(
        [sys.executable, str(ARIS_FEISHU_SESSION), *args],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_once_dry_run_processes_inbox_and_writes_outbox():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "$status"])

        result = run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--dry-run",
                "--no-send-feishu",
            ]
        )

        assert "processed 1 message" in result.stdout
        responses = read_jsonl(root / "outbox" / "leader-1.jsonl")
        assert responses[-1]["text"] == "DRY RUN: $status"

        second = run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--dry-run",
                "--no-send-feishu",
            ]
        )
        assert "processed 0 messages" in second.stdout


def test_once_invokes_codex_bin_and_records_response():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fake_codex = root / "fake-codex"
        fake_codex.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
            "out.write_text('codex answered', encoding='utf-8')\n",
            encoding="utf-8",
        )
        fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "hello"])

        run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--codex-bin",
                str(fake_codex),
                "--no-send-feishu",
            ]
        )

        responses = read_jsonl(root / "outbox" / "leader-1.jsonl")
        assert responses[-1]["text"] == "codex answered"


def test_resume_last_builds_codex_exec_resume_command():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        capture = root / "argv.json"
        fake_codex = root / "fake-codex"
        fake_codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            f"pathlib.Path({str(capture)!r}).write_text(json.dumps(sys.argv), encoding='utf-8')\n"
            "out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
            "out.write_text('resumed answer', encoding='utf-8')\n",
            encoding="utf-8",
        )
        fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "continue"])

        run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--codex-bin",
                str(fake_codex),
                "--resume-last",
                "--no-send-feishu",
            ]
        )

        argv = json.loads(capture.read_text(encoding="utf-8"))
        assert argv[1:4] == ["exec", "resume", "--last"]


def test_yolo_mode_passes_bypass_flag_to_codex_exec():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        capture = root / "argv.json"
        fake_codex = root / "fake-codex"
        fake_codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            f"pathlib.Path({str(capture)!r}).write_text(json.dumps(sys.argv), encoding='utf-8')\n"
            "out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
            "out.write_text('yolo answer', encoding='utf-8')\n",
            encoding="utf-8",
        )
        fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "continue"])

        run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--codex-bin",
                str(fake_codex),
                "--yolo",
                "--no-send-feishu",
            ]
        )

        argv = json.loads(capture.read_text(encoding="utf-8"))
        assert "--dangerously-bypass-approvals-and-sandbox" in argv


def test_mark_seen_skips_existing_inbox_messages():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "old one"])
        run_control(["--state-root", str(root), "handle-message", "--text", "old two"])

        result = run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--dry-run",
                "--mark-seen",
                "--no-send-feishu",
            ]
        )

        assert "marked 2 messages seen" in result.stdout
        assert not (root / "outbox" / "leader-1.jsonl").exists()


def test_empty_codex_output_records_diagnostic_instead_of_blank_card():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fake_codex = root / "fake-codex"
        fake_codex.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
            "out.write_text('', encoding='utf-8')\n",
            encoding="utf-8",
        )
        fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "hello"])

        run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--codex-bin",
                str(fake_codex),
                "--no-send-feishu",
            ]
        )

        responses = read_jsonl(root / "outbox" / "leader-1.jsonl")
        assert "Codex produced no final message" in responses[-1]["text"]


def test_tmux_pane_mode_injects_message_without_running_codex_exec():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        calls = root / "tmux-calls.jsonl"
        fake_tmux = root / "fake-tmux"
        fake_tmux.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            f"calls = pathlib.Path({str(calls)!r})\n"
            "stdin = sys.stdin.read()\n"
            "with calls.open('a', encoding='utf-8') as fh:\n"
            "    fh.write(json.dumps({'argv': sys.argv[1:], 'stdin': stdin}) + '\\n')\n",
            encoding="utf-8",
        )
        fake_tmux.chmod(fake_tmux.stat().st_mode | stat.S_IXUSR)

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "live takeover"])

        run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--tmux-bin",
                str(fake_tmux),
                "--tmux-pane",
                "dev:1.0",
                "--tmux-submit-delay-seconds",
                "0",
                "--no-watch-codex-response",
                "--no-send-feishu",
            ]
        )

        tmux_calls = read_jsonl(calls)
        assert tmux_calls[0] == {"argv": ["load-buffer", "-"], "stdin": "live takeover"}
        assert tmux_calls[1] == {"argv": ["paste-buffer", "-d", "-t", "dev:1.0"], "stdin": ""}
        assert tmux_calls[2] == {"argv": ["send-keys", "-t", "dev:1.0", "Enter"], "stdin": ""}
        responses = read_jsonl(root / "outbox" / "leader-1.jsonl")
        assert "Injected into live Codex TUI pane `dev:1.0`" in responses[-1]["text"]


def test_tmux_pane_mode_can_send_final_answer_from_codex_transcript():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        transcript = root / "rollout.jsonl"
        transcript.write_text('{"type":"event_msg","payload":{"type":"task_complete","last_agent_message":"old"}}\n', encoding="utf-8")
        fake_tmux = root / "fake-tmux"
        fake_tmux.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            f"transcript = pathlib.Path({str(transcript)!r})\n"
            "if sys.argv[1:2] == ['send-keys']:\n"
            "    event = {'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'final from live tui'}}\n"
            "    with transcript.open('a', encoding='utf-8') as fh:\n"
            "        fh.write(json.dumps(event) + '\\n')\n"
            "else:\n"
            "    sys.stdin.read()\n",
            encoding="utf-8",
        )
        fake_tmux.chmod(fake_tmux.stat().st_mode | stat.S_IXUSR)

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "live takeover"])

        run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--tmux-bin",
                str(fake_tmux),
                "--tmux-pane",
                "dev:1.0",
                "--tmux-submit-delay-seconds",
                "0",
                "--codex-transcript",
                str(transcript),
                "--codex-response-timeout-seconds",
                "1",
                "--codex-response-poll-seconds",
                "0.01",
                "--no-send-feishu",
            ]
        )

        responses = read_jsonl(root / "outbox" / "leader-1.jsonl")
        assert responses[-1]["text"] == "final from live tui"


def test_wait_for_codex_task_complete_sends_heartbeat_status_cards():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        send_feishu = True
        feishu_status_updates = True
        feishu_status_mode = "send"
        feishu_format = "card"
        http_timeout_seconds = 10
        codex_response_timeout_seconds = 0.05
        codex_response_poll_seconds = 0.01
        feishu_status_interval_seconds = 0.01
        session_id = "leader-1"

    with tempfile.TemporaryDirectory() as tmp:
        transcript = Path(tmp) / "rollout.jsonl"
        transcript.write_text("", encoding="utf-8")

        with patch.object(aris_feishu_session, "post_json", return_value={"ok": True}) as post_json:
            result, elapsed = aris_feishu_session.wait_for_codex_task_complete(Args(), transcript, transcript.stat().st_size)

    assert result is None
    assert elapsed >= 0
    status_payloads = [call.args[1] for call in post_json.call_args_list]
    assert any(payload["title"] == "ARIS 状态" and "`leader-1` · 已收到信息 · 0s" in payload["body"] for payload in status_payloads)


def test_send_status_updates_existing_status_card():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        send_feishu = True
        feishu_status_updates = True
        feishu_status_mode = "update"
        feishu_format = "card"
        http_timeout_seconds = 10

    args = Args()
    with patch.object(
        aris_feishu_session,
        "post_json",
        side_effect=[{"ok": True, "message_id": "om_status"}, {"ok": True, "message_id": "om_status"}],
    ) as post_json:
        aris_feishu_session.send_status(args, "`leader-phone` · 已收到信息 · 0s")
        aris_feishu_session.send_status(args, "`leader-phone` · 处理中 · 30s")

    assert post_json.call_args_list[0].args[0] == "http://bridge/send"
    assert post_json.call_args_list[1].args[0] == "http://bridge/update"
    assert post_json.call_args_list[1].args[1]["message_id"] == "om_status"
    assert post_json.call_args_list[1].args[1]["body"] == "`leader-phone` · 处理中 · 30s"


def test_status_line_can_use_plain_or_warm_style():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        session_id = "leader-1"
        feishu_status_style = "plain"

    assert aris_feishu_session.processing_status_text(Args(), 15) == "`leader-1` · 思考中 · 15s"

    Args.feishu_status_style = "warm"
    assert aris_feishu_session.processing_status_text(Args(), 15) == "`leader-1` · 思考中 · 15s"


def test_warm_status_without_hint_stays_minimal():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        session_id = "leader-1"
        feishu_status_style = "warm"

    assert aris_feishu_session.processing_status_text(Args(), 30) == "`leader-1` · 处理中 · 30s"
    assert aris_feishu_session.processing_status_text(Args(), 45) == "`leader-1` · 处理中 · 45s"


def test_send_status_does_not_send_new_card_when_update_fails():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        send_feishu = True
        feishu_status_updates = True
        feishu_status_mode = "update"
        feishu_format = "card"
        http_timeout_seconds = 10
        _feishu_status_message_id_main = "om_status"

    with patch.object(aris_feishu_session, "post_json", return_value={"error": "update failed"}) as post_json:
        aris_feishu_session.send_status(Args(), "`leader-phone` · 处理中 · 30s")

    assert len(post_json.call_args_list) == 1
    assert post_json.call_args_list[0].args[0] == "http://bridge/update"


def test_btw_status_uses_separate_card_from_main_status():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        send_feishu = True
        feishu_status_updates = True
        feishu_status_mode = "update"
        feishu_format = "card"
        http_timeout_seconds = 10
        _feishu_status_message_id_main = "om_main"

    args = Args()
    with patch.object(aris_feishu_session, "post_json", return_value={"ok": True, "message_id": "om_btw"}) as post_json:
        aris_feishu_session.send_status(args, "`leader-phone` · 已收到 BTW · 0s", channel="btw")

    assert post_json.call_args_list[0].args[0] == "http://bridge/send"
    assert args._feishu_status_message_id_main == "om_main"
    assert args._feishu_status_message_id_btw == "om_btw"


def test_run_live_tui_updates_status_to_completed_before_returning_answer():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        send_feishu = True
        feishu_status_updates = True
        feishu_status_mode = "update"
        feishu_format = "card"
        http_timeout_seconds = 10
        watch_codex_response = True
        session_id = "leader-phone"

    args = Args()
    with patch.object(aris_feishu_session, "latest_codex_transcript", return_value=Path("/tmp/rollout.jsonl")):
        with patch.object(aris_feishu_session, "transcript_offset", return_value=0):
            with patch.object(aris_feishu_session, "inject_message_to_tmux", return_value="Injected"):
                with patch.object(aris_feishu_session, "wait_for_codex_task_complete", return_value=("done", 42)):
                    with patch.object(aris_feishu_session, "send_status") as send_status:
                        result = aris_feishu_session.run_live_tui_for_message(args, Path("/tmp/state"), {"processed_count": 0}, {"text": "hello"}, 0)

    assert result == "done"
    assert send_status.call_args_list[-1].args[1] == "`leader-phone` · 已完成 · 42s"
    assert send_status.call_args_list[-1].kwargs["color"] == "green"


def test_run_live_tui_does_not_overwrite_interrupt_status_with_completed():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        send_feishu = True
        feishu_status_updates = True
        feishu_status_mode = "update"
        feishu_format = "card"
        http_timeout_seconds = 10
        watch_codex_response = True
        session_id = "leader-phone"

    args = Args()
    with patch.object(aris_feishu_session, "latest_codex_transcript", return_value=Path("/tmp/rollout.jsonl")):
        with patch.object(aris_feishu_session, "transcript_offset", return_value=0):
            with patch.object(aris_feishu_session, "inject_message_to_tmux", return_value="Injected"):
                with patch.object(aris_feishu_session, "wait_for_codex_task_complete", return_value=("已中断", 3)):
                    with patch.object(aris_feishu_session, "send_status") as send_status:
                        result = aris_feishu_session.run_live_tui_for_message(args, Path("/tmp/state"), {"processed_count": 0}, {"text": "hello"}, 0)

    assert result == "已中断"
    assert not any("已完成" in call.args[1] for call in send_status.call_args_list)


def test_live_wait_interrupts_tmux_when_interrupt_message_arrives():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        send_feishu = True
        feishu_status_updates = True
        feishu_status_mode = "update"
        feishu_format = "card"
        http_timeout_seconds = 10
        session_id = "leader-1"
        tmux_bin = "tmux"
        tmux_pane = "dev:1.0"
        tmux_interrupt_key = "C-c"
        codex_response_timeout_seconds = 0.05
        codex_response_poll_seconds = 0.01
        feishu_status_interval_seconds = 30

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inbox = root / "inbox" / "leader-1.jsonl"
        inbox.parent.mkdir(parents=True)
        inbox.write_text(
            json.dumps({"text": "main", "session_id": "leader-1"}) + "\n"
            + json.dumps({"text": "/interrupt", "session_id": "leader-1"}) + "\n",
            encoding="utf-8",
        )
        transcript = root / "rollout.jsonl"
        transcript.write_text("", encoding="utf-8")
        runner = {"processed_count": 0}

        with patch.object(aris_feishu_session, "send_tmux_key", return_value=None) as send_tmux_key:
            with patch.object(aris_feishu_session, "send_status") as send_status:
                result, elapsed = aris_feishu_session.wait_for_codex_task_complete(Args(), transcript, 0, root, runner, 1)

    assert result == "已中断"
    assert elapsed >= 0
    send_tmux_key.assert_called_once()
    assert runner["processed_count"] == 2
    assert send_status.call_args_list[0].args[1] == "`leader-1` · 正在中断"
    assert send_status.call_args_list[-1].args[1] == "`leader-1` · 已中断"


def test_live_wait_answers_btw_as_side_channel_without_injecting_main_thread():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        send_feishu = True
        feishu_status_updates = True
        feishu_status_mode = "update"
        feishu_format = "card"
        http_timeout_seconds = 10
        session_id = "leader-1"
        tmux_bin = "tmux"
        tmux_pane = "dev:1.0"
        tmux_interrupt_key = "C-c"
        tmux_submit_delay_seconds = 0
        tmux_submit_key = "Enter"
        dry_run = False
        codex_response_timeout_seconds = 1
        codex_response_poll_seconds = 0.01
        feishu_status_interval_seconds = 30

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inbox = root / "inbox" / "leader-1.jsonl"
        inbox.parent.mkdir(parents=True)
        inbox.write_text(
            json.dumps({"text": "main", "session_id": "leader-1"}) + "\n"
            + json.dumps({"text": "/btw 记得检查日志", "session_id": "leader-1", "sender_open_id": "ou_btw"}) + "\n",
            encoding="utf-8",
        )
        transcript = root / "rollout.jsonl"
        event = {"type": "event_msg", "payload": {"type": "task_complete", "last_agent_message": "done"}}
        transcript.write_text(json.dumps(event) + "\n", encoding="utf-8")
        runner = {"processed_count": 0}

        args = Args()
        with patch.object(aris_feishu_session, "send_status") as send_status:
            with patch.object(aris_feishu_session, "run_btw_for_message", return_value="side answer") as run_btw:
                with patch.object(aris_feishu_session, "send_response") as send_response:
                    with patch.object(aris_feishu_session, "inject_message_to_tmux") as inject:
                        inject.return_value = "Injected"
                        result, _ = aris_feishu_session.wait_for_codex_task_complete(args, transcript, 0, root, runner, 1)
                        aris_feishu_session.flush_pending_btw(args)

    assert result == "done"
    assert runner["processed_count"] == 2
    run_btw.assert_called_once()
    send_response.assert_called_once()
    assert send_response.call_args.args[1] == "side answer"
    assert send_response.call_args.args[2]["sender_open_id"] == "ou_btw"
    assert getattr(args, "_feishu_current_sender_open_id") == ""
    assert send_status.call_args_list[0].args[1] == "`leader-1` · 已收到 BTW · 0s"
    assert send_status.call_args_list[-1].args[1] == "`leader-1` · BTW 已完成"
    assert inject.call_count == 0


def test_top_level_btw_message_runs_side_query_not_live_tmux():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fake_codex = root / "fake-codex"
        capture = root / "prompt.txt"
        fake_codex.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "out = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
            "out.write_text('btw answer', encoding='utf-8')\n"
            f"pathlib.Path({str(capture)!r}).write_text(sys.argv[-1], encoding='utf-8')\n",
            encoding="utf-8",
        )
        fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR)
        transcript = root / "rollout.jsonl"
        transcript.write_text('{"type":"event_msg","payload":{"type":"user_message","message":"current context"}}\n', encoding="utf-8")

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", "/repo/a"])
        run_control(["--state-root", str(root), "handle-message", "--text", "/btw 当前做到哪了"])

        result = run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                "/repo/a",
                "--once",
                "--tmux-bin",
                "false",
                "--tmux-pane",
                "dev:1.0",
                "--codex-bin",
                str(fake_codex),
                "--codex-transcript",
                str(transcript),
                "--no-send-feishu",
            ]
        )

        responses = read_jsonl(root / "outbox" / "leader-1.jsonl")
        prompt = capture.read_text(encoding="utf-8")
        assert responses[-1]["text"] == "btw answer"
        assert "当前做到哪了" in prompt
        assert "current context" in prompt
        assert result.stdout.strip() == "processed 1 message"


def test_legacy_flush_pending_btw_is_noop():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        pass

    args = Args()
    args._pending_btw = ["old"]
    with patch.object(aris_feishu_session, "inject_message_to_tmux") as inject:
        aris_feishu_session.flush_pending_btw(args)

    inject.assert_not_called()
    assert args._pending_btw == []


def test_write_report_creates_phone_session_report_from_inbox_and_outbox():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "repo"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=str(project), check=True, stdout=subprocess.PIPE)
        (project / "README.md").write_text("changed\n", encoding="utf-8")

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", str(project)])
        run_control(["--state-root", str(root), "handle-message", "--text", "phone asks"])
        run_control(["--state-root", str(root), "respond", "--session-id", "leader-1", "--text", "codex answers"])

        result = run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                str(project),
                "--write-report",
            ]
        )

        report_path = Path(result.stdout.strip())
        report = report_path.read_text(encoding="utf-8")
        assert report_path == root / "reports" / "leader-1.md"
        assert "# Phone Session Report: leader-1" in report
        assert "phone asks" in report
        assert "codex answers" in report
        assert "git status --short" in report
        assert "README.md" in report


def test_merge_prompt_writes_report_and_references_it():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "repo"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=str(project), check=True, stdout=subprocess.PIPE)

        run_control(["--state-root", str(root), "register", "--session-id", "leader-1", "--role", "leader", "--project-root", str(project)])

        result = run_session(
            [
                "--state-root",
                str(root),
                "--session-id",
                "leader-1",
                "--project-root",
                str(project),
                "--merge-prompt",
            ]
        )

        report_path = root / "reports" / "leader-1.md"
        assert report_path.exists()
        assert str(report_path) in result.stdout
        assert "不要假设手机 runner 的隐藏上下文已经转移" in result.stdout


def test_send_response_defaults_to_feishu_card_payload():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        session_id = "leader-1"
        send_feishu = True
        feishu_format = "card"
        http_timeout_seconds = 10
        state_root = None
        project_root = "/repo/a"
        _feishu_current_sender_open_id = ""

    with patch.object(aris_feishu_session, "post_json", return_value={"ok": True}) as post_json:
        aris_feishu_session.send_response(Args(), "**done**")

    assert post_json.call_args_list[0].args[0] == "http://bridge/control/respond"
    send_payload = post_json.call_args_list[1].args[1]
    assert send_payload["title"] == "ARIS"
    assert send_payload["body"] == "**done**"
    assert send_payload["color"] == "blue"
    assert "type" not in send_payload


def test_send_response_targets_current_feishu_sender_when_available():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        session_id = "leader-1"
        send_feishu = True
        feishu_format = "card"
        http_timeout_seconds = 10
        state_root = None
        project_root = "/repo/a"
        _feishu_current_sender_open_id = "ou_current"

    with patch.object(aris_feishu_session, "post_json", return_value={"ok": True}) as post_json:
        aris_feishu_session.send_response(Args(), "**done**")

    send_payload = post_json.call_args_list[1].args[1]
    assert send_payload["user_id"] == "ou_current"


def test_send_response_can_use_plain_text_payload():
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import aris_feishu_session

    class Args:
        bridge_url = "http://bridge"
        session_id = "leader-1"
        send_feishu = True
        feishu_format = "text"
        http_timeout_seconds = 10
        state_root = None
        project_root = "/repo/a"
        _feishu_current_sender_open_id = ""

    with patch.object(aris_feishu_session, "post_json", return_value={"ok": True}) as post_json:
        aris_feishu_session.send_response(Args(), "**done**")

    send_payload = post_json.call_args_list[1].args[1]
    assert send_payload == {"type": "text", "content": "**done**"}
