#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FEISHU_CONTROL = REPO_ROOT / "tools" / "feishu_control.py"


def state_root(args: argparse.Namespace) -> Path:
    if args.state_root:
        return Path(args.state_root)
    return Path(args.project_root) / ".aris" / "feishu-control"


def inbox_file(root: Path, session_id: str) -> Path:
    return root / "inbox" / f"{session_id}.jsonl"


def outbox_file(root: Path, session_id: str) -> Path:
    return root / "outbox" / f"{session_id}.jsonl"


def runner_file(root: Path, session_id: str) -> Path:
    return root / "runners" / f"{session_id}.json"


def report_file(root: Path, session_id: str) -> Path:
    return root / "reports" / f"{session_id}.md"


def response_dir(root: Path, session_id: str) -> Path:
    return root / "responses" / session_id


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def session_sender(root: Path, session_id: str) -> str:
    sessions_path = root / "sessions.json"
    if not sessions_path.exists():
        return ""
    try:
        data = json.loads(sessions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    session = data.get("sessions", {}).get(session_id, {})
    sender = session.get("last_sender_open_id", "")
    return sender if isinstance(sender, str) else ""


def message_sender(args: argparse.Namespace, message: dict | None = None) -> str:
    if message:
        sender = message.get("sender_open_id", "")
        if isinstance(sender, str) and sender:
            return sender
    sender = getattr(args, "_feishu_current_sender_open_id", "")
    return sender if isinstance(sender, str) else ""


def with_recipient(payload: dict, recipient: str) -> dict:
    if recipient:
        return {**payload, "user_id": recipient}
    return payload


def read_runner(root: Path, session_id: str) -> dict:
    path = runner_file(root, session_id)
    if not path.exists():
        return {"processed_count": 0}
    return json.loads(path.read_text(encoding="utf-8"))


def write_runner(root: Path, session_id: str, data: dict) -> None:
    path = runner_file(root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_control(args: argparse.Namespace, control_args: list[str]) -> dict:
    command = [sys.executable, str(FEISHU_CONTROL), "--state-root", str(state_root(args)), *control_args]
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(completed.stdout)


def register_session(args: argparse.Namespace) -> None:
    run_control(
        args,
        [
            "register",
            "--session-id",
            args.session_id,
            "--role",
            args.role,
            "--project-root",
            args.project_root,
        ],
    )
    run_control(args, ["use", "--session-id", args.session_id])


def codex_command(args: argparse.Namespace, prompt: str, output_file: Path) -> list[str]:
    yolo_flag = ["--dangerously-bypass-approvals-and-sandbox"] if args.yolo else []
    if args.resume_last:
        return [args.codex_bin, "exec", "resume", "--last", *yolo_flag, "-o", str(output_file), prompt]
    if args.codex_session_id:
        return [args.codex_bin, "exec", "resume", *yolo_flag, "-o", str(output_file), args.codex_session_id, prompt]
    command = [args.codex_bin, "exec", "-C", args.project_root]
    if getattr(args, "profile", None):
        command.extend(["-p", args.profile])
    command.extend(yolo_flag)
    command.extend(["-o", str(output_file), prompt])
    return command


def run_codex_for_message(args: argparse.Namespace, root: Path, message: dict, index: int) -> str:
    text = message.get("text", "")
    if args.dry_run:
        return f"DRY RUN: {text}"

    out_dir = response_dir(root, args.session_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file = out_dir / f"{index:06d}.txt"
    command = codex_command(args, text, output_file)
    cwd = args.project_root if Path(args.project_root).exists() else str(REPO_ROOT)
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout_seconds,
    )
    if completed.returncode != 0:
        return f"Codex command failed ({completed.returncode}):\n{completed.stderr.strip() or completed.stdout.strip()}"
    if output_file.exists():
        response = output_file.read_text(encoding="utf-8").strip()
        if response:
            return response
    stdout = completed.stdout.strip()
    if stdout:
        return stdout
    return "Codex produced no final message. This can happen when `codex exec resume --last` attaches to a live TUI session; use fresh exec mode or a specific inactive `--codex-session-id`."


def is_btw_message(message: dict) -> bool:
    text = message.get("text", "").strip()
    return text == "/btw" or text.startswith("/btw ")


def btw_question(message: dict) -> str:
    text = message.get("text", "").strip()
    return text.removeprefix("/btw").strip()


def read_transcript_context(path: Path | None, max_chars: int) -> str:
    if not path or not path.exists() or max_chars <= 0:
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def build_btw_prompt(question: str, transcript_context: str) -> str:
    return (
        "你是 ARIS/Codex 的 BTW side-channel。\n"
        "回答用户问题，但不要修改文件、不要执行项目操作、不要影响主 Codex CLI thread。\n"
        "你只能基于下面当前 thread transcript 摘要/尾部和用户问题回答。\n\n"
        f"用户 BTW 问题：\n{question}\n\n"
        "当前 thread transcript 尾部：\n"
        "```jsonl\n"
        f"{transcript_context}\n"
        "```\n"
    )


def run_btw_for_message(args: argparse.Namespace, root: Path, message: dict, index: int) -> str:
    question = btw_question(message)
    if not question:
        return "BTW 为空。用法：`/btw <问题>`"
    if args.dry_run:
        return f"DRY RUN BTW: {question}"

    transcript = latest_codex_transcript(args)
    context = read_transcript_context(transcript, getattr(args, "btw_context_chars", 20000))
    prompt = build_btw_prompt(question, context)
    out_dir = response_dir(root, args.session_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file = out_dir / f"{index:06d}.btw.txt"

    command = [args.codex_bin, "exec", "-C", args.project_root]
    if args.profile:
        command.extend(["-p", args.profile])
    command.extend(["-o", str(output_file), prompt])
    cwd = args.project_root if Path(args.project_root).exists() else str(REPO_ROOT)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = time.monotonic()
    deadline = started + getattr(args, "btw_timeout_seconds", 300)
    next_status = started + getattr(args, "feishu_status_interval_seconds", 15)
    while process.poll() is None:
        now = time.monotonic()
        if now >= deadline:
            process.kill()
            stdout, stderr = process.communicate()
            send_status(args, btw_timeout_status_text(args), color="red", channel="btw")
            return f"BTW timed out:\n{stderr.strip() or stdout.strip()}"
        if args.feishu_status_interval_seconds > 0 and now >= next_status:
            elapsed = int(now - started)
            send_status(args, btw_processing_status_text(args, elapsed), color="yellow", channel="btw")
            next_status = now + args.feishu_status_interval_seconds
        time.sleep(min(getattr(args, "codex_response_poll_seconds", 0.5), 1.0))
    stdout, stderr = process.communicate()
    completed = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if completed.returncode != 0:
        return f"BTW failed ({completed.returncode}):\n{completed.stderr.strip() or completed.stdout.strip()}"
    if output_file.exists():
        response = output_file.read_text(encoding="utf-8").strip()
        if response:
            return response
    stdout = completed.stdout.strip()
    return stdout or "BTW produced no final message."


def inject_message_to_tmux(args: argparse.Namespace, message: dict) -> str:
    text = message.get("text", "")
    if args.dry_run:
        return f"DRY RUN: would inject into tmux pane {args.tmux_pane}: {text}"
    load = subprocess.run(
        [args.tmux_bin, "load-buffer", "-"],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    if load.returncode != 0:
        return f"tmux load-buffer failed ({load.returncode}): {load.stderr.strip() or load.stdout.strip()}"
    paste = subprocess.run(
        [args.tmux_bin, "paste-buffer", "-d", "-t", args.tmux_pane],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    if paste.returncode != 0:
        return f"tmux paste-buffer failed ({paste.returncode}): {paste.stderr.strip() or paste.stdout.strip()}"
    if args.tmux_submit_delay_seconds > 0:
        time.sleep(args.tmux_submit_delay_seconds)
    enter = subprocess.run(
        [args.tmux_bin, "send-keys", "-t", args.tmux_pane, args.tmux_submit_key],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    if enter.returncode != 0:
        return f"tmux send-keys failed ({enter.returncode}): {enter.stderr.strip() or enter.stdout.strip()}"
    return f"Injected into live Codex TUI pane `{args.tmux_pane}`. The answer will appear in the local CLI thread."


def send_tmux_key(args: argparse.Namespace, key: str) -> None:
    completed = subprocess.run(
        [args.tmux_bin, "send-keys", "-t", args.tmux_pane, key],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"tmux send-keys failed ({completed.returncode}): {completed.stderr.strip() or completed.stdout.strip()}")


def latest_codex_transcript(args: argparse.Namespace) -> Path | None:
    if args.codex_transcript:
        return Path(args.codex_transcript).expanduser()
    sessions_root = Path(args.codex_home).expanduser() / "sessions"
    if not sessions_root.exists():
        return None
    candidates = [path for path in sessions_root.rglob("*.jsonl") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def transcript_offset(path: Path | None) -> int:
    if not path or not path.exists():
        return 0
    return path.stat().st_size


def extract_task_complete_message(event: dict) -> str | None:
    if event.get("type") != "event_msg":
        return None
    payload = event.get("payload") or {}
    if payload.get("type") != "task_complete":
        return None
    message = payload.get("last_agent_message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return None


def scan_live_control_messages(args: argparse.Namespace, root: Path | None, runner: dict | None, start_index: int) -> str | None:
    if root is None or runner is None:
        return None
    messages = read_jsonl(inbox_file(root, args.session_id))
    scan_start = max(start_index, int(runner.get("live_control_scan_count", start_index)))
    for index, message in enumerate(messages[scan_start:], start=scan_start):
        text = message.get("text", "").strip()
        runner["live_control_scan_count"] = index + 1
        previous_sender = getattr(args, "_feishu_current_sender_open_id", "")
        setattr(args, "_feishu_current_sender_open_id", message_sender(args, message) or previous_sender)
        if text == "/interrupt" or text.startswith("/interrupt "):
            send_status(args, interrupting_status_text(args), color="red")
            send_tmux_key(args, args.tmux_interrupt_key)
            runner["processed_count"] = max(int(runner.get("processed_count", 0)), index + 1)
            write_runner(root, args.session_id, runner)
            send_status(args, interrupted_status_text(args), color="red")
            setattr(args, "_feishu_current_sender_open_id", previous_sender)
            return "interrupt"
        if text == "/btw" or text.startswith("/btw "):
            send_status(args, btw_received_status_text(args), color="blue", channel="btw")
            answer = run_btw_for_message(args, root, message, index)
            send_response(args, answer, message)
            send_status(args, btw_completed_status_text(args), color="green", channel="btw")
            runner["processed_count"] = max(int(runner.get("processed_count", 0)), index + 1)
            write_runner(root, args.session_id, runner)
        setattr(args, "_feishu_current_sender_open_id", previous_sender)
    if scan_start < len(messages):
        write_runner(root, args.session_id, runner)
    return None


def flush_pending_btw(args: argparse.Namespace) -> None:
    setattr(args, "_pending_btw", [])


def wait_for_codex_task_complete(
    args: argparse.Namespace,
    transcript: Path,
    offset: int,
    root: Path | None = None,
    runner: dict | None = None,
    control_start_index: int = 0,
) -> tuple[str | None, int]:
    started = time.monotonic()
    deadline = started + args.codex_response_timeout_seconds
    next_status = started + args.feishu_status_interval_seconds
    current_offset = offset
    while time.monotonic() < deadline:
        now = time.monotonic()
        control = scan_live_control_messages(args, root, runner, control_start_index)
        if control == "interrupt":
            return "已中断", int(now - started)
        if args.feishu_status_interval_seconds > 0 and now >= next_status:
            elapsed = int(now - started)
            send_status(
                args,
                processing_status_text(args, elapsed),
                color="yellow",
            )
            next_status = now + args.feishu_status_interval_seconds
        if not transcript.exists():
            time.sleep(args.codex_response_poll_seconds)
            continue
        with transcript.open("r", encoding="utf-8") as fh:
            fh.seek(current_offset)
            chunk = fh.read()
            current_offset = fh.tell()
        for line in chunk.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = extract_task_complete_message(event)
            if message:
                return message, int(time.monotonic() - started)
        time.sleep(args.codex_response_poll_seconds)
    return None, int(time.monotonic() - started)


def run_live_tui_for_message(args: argparse.Namespace, root: Path, runner: dict, message: dict, index: int) -> str:
    setattr(args, "_feishu_status_message_id_main", "")
    transcript = latest_codex_transcript(args)
    offset = transcript_offset(transcript)
    injected = inject_message_to_tmux(args, message)
    if not args.watch_codex_response or injected.startswith("tmux "):
        return injected
    if not transcript:
        return f"{injected}\n\nCodex transcript was not found, so Feishu cannot mirror the final answer."
    send_status(
        args,
        processing_status_text(args, 0),
        color="blue",
    )
    response, elapsed = wait_for_codex_task_complete(args, transcript, offset, root, runner, index + 1)
    if response:
        if response == "已中断":
            return response
        send_status(args, completed_status_text(args, elapsed), color="green")
        flush_pending_btw(args)
        return response
    send_status(args, timeout_status_text(args), color="red")
    return f"{injected}\n\nTimed out waiting for Codex final answer in `{transcript}`."


def post_json(url: str, payload: dict, timeout: int = 10) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}


def send_response(args: argparse.Namespace, text: str, message: dict | None = None) -> None:
    if args.bridge_url:
        post_json(
            f"{args.bridge_url.rstrip('/')}/control/respond",
            {"session_id": args.session_id, "text": text},
            timeout=args.http_timeout_seconds,
        )
        if args.send_feishu:
            if args.feishu_format == "card":
                payload = {"title": "ARIS", "body": text, "color": "blue"}
            else:
                payload = {"type": "text", "content": text}
            payload = with_recipient(payload, message_sender(args, message))
            post_json(
                f"{args.bridge_url.rstrip('/')}/send",
                payload,
                timeout=args.http_timeout_seconds,
            )
        return
    run_control(args, ["respond", "--session-id", args.session_id, "--text", text])


def send_status(args: argparse.Namespace, text: str, color: str = "yellow", channel: str = "main") -> None:
    if not args.bridge_url or not args.send_feishu or not args.feishu_status_updates:
        return
    if args.feishu_format == "card":
        payload = {"title": "ARIS 状态", "body": text, "color": color}
    else:
        payload = {"type": "text", "content": text}
    payload = with_recipient(payload, message_sender(args))
    if getattr(args, "feishu_status_mode", "update") == "update" and args.feishu_format == "card":
        status_attr = f"_feishu_status_message_id_{channel}"
        message_id = getattr(args, status_attr, "")
        if message_id:
            update_payload = {**payload, "message_id": message_id}
            result = post_json(
                f"{args.bridge_url.rstrip('/')}/update",
                update_payload,
                timeout=args.http_timeout_seconds,
            )
            if result.get("ok"):
                return
            print(f"status card update failed: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr, flush=True)
            return
    result = post_json(
        f"{args.bridge_url.rstrip('/')}/send",
        payload,
        timeout=args.http_timeout_seconds,
    )
    if result.get("message_id"):
        status_attr = f"_feishu_status_message_id_{channel}"
        setattr(args, status_attr, result["message_id"])


def processing_status_text(args: argparse.Namespace, elapsed_seconds: int) -> str:
    if elapsed_seconds <= 0:
        stage = "已收到信息"
    elif elapsed_seconds < 30:
        stage = "思考中"
    else:
        stage = "处理中"
    return status_line(args, stage, elapsed_seconds, "")


def timeout_status_text(args: argparse.Namespace) -> str:
    return status_line(args, "超时，未收到最终回复", None, "")


def completed_status_text(args: argparse.Namespace, elapsed_seconds: int) -> str:
    return status_line(args, "已完成", elapsed_seconds, "")


def interrupted_status_text(args: argparse.Namespace) -> str:
    return status_line(args, "已中断", None, "")


def interrupting_status_text(args: argparse.Namespace) -> str:
    return status_line(args, "正在中断", None, "")


def btw_received_status_text(args: argparse.Namespace) -> str:
    return status_line(args, "已收到 BTW", 0, "")


def btw_completed_status_text(args: argparse.Namespace) -> str:
    return status_line(args, "BTW 已完成", None, "")


def btw_processing_status_text(args: argparse.Namespace, elapsed_seconds: int) -> str:
    return status_line(args, "BTW 思考中", elapsed_seconds, "")


def btw_timeout_status_text(args: argparse.Namespace) -> str:
    return status_line(args, "BTW 超时", None, "")


def status_line(args: argparse.Namespace, stage: str, elapsed_seconds: int | None, warm_hint: str) -> str:
    parts = [f"`{getattr(args, 'session_id', 'unknown')}`", stage]
    if elapsed_seconds is not None:
        parts.append(f"{elapsed_seconds}s")
    if getattr(args, "feishu_status_style", "warm") == "warm" and warm_hint:
        parts.append(warm_hint)
    return " · ".join(parts)


def git_text(project_root: str, git_args: list[str]) -> str:
    root = Path(project_root)
    if not root.exists():
        return f"project root not found: {project_root}"
    completed = subprocess.run(
        ["git", *git_args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if completed.returncode != 0:
        return completed.stderr.strip() or completed.stdout.strip() or f"git {' '.join(git_args)} failed"
    return completed.stdout.strip() or "(empty)"


def fenced(text: str) -> str:
    return f"```text\n{text}\n```"


def build_phone_session_report(args: argparse.Namespace, root: Path) -> str:
    inbox = read_jsonl(inbox_file(root, args.session_id))
    outbox = read_jsonl(outbox_file(root, args.session_id))
    runner = read_runner(root, args.session_id)
    processed_count = int(runner.get("processed_count", 0))

    lines = [
        f"# Phone Session Report: {args.session_id}",
        "",
        "This report is an auditable handoff from a Feishu-controlled Codex session back to the local Codex thread.",
        "",
        "## Session State",
        "",
        f"- Project root: `{args.project_root}`",
        f"- State root: `{root}`",
        f"- Inbox messages: {len(inbox)}",
        f"- Outbox responses: {len(outbox)}",
        f"- Runner processed count: {processed_count}",
        "",
        "## Transcript",
        "",
    ]

    turn_count = max(len(inbox), len(outbox))
    if turn_count == 0:
        lines.append("(no messages recorded)")
        lines.append("")
    for index in range(turn_count):
        message = inbox[index] if index < len(inbox) else {}
        response = outbox[index] if index < len(outbox) else {}
        user_text = message.get("text", "")
        response_text = response.get("text", "")
        lines.extend(
            [
                f"### Turn {index + 1}",
                "",
                f"- User time: `{message.get('received_at', 'unknown')}`",
                f"- Response time: `{response.get('created_at', 'unknown')}`",
                "",
                "User:",
                "",
                fenced(user_text or "(empty)"),
                "",
                "Codex:",
                "",
                fenced(response_text or "(empty)"),
                "",
            ]
        )

    lines.extend(
        [
            "## Worktree Snapshot",
            "",
            "### `git status --short`",
            "",
            fenced(git_text(args.project_root, ["status", "--short"])),
            "",
            "### `git diff --stat`",
            "",
            fenced(git_text(args.project_root, ["diff", "--stat"])),
            "",
            "## Local Merge Contract",
            "",
            "- Treat this file as the source of truth for what happened on the phone session.",
            "- Merge facts, decisions, file changes, and open questions into the current local thread.",
            "- Do not assume hidden model context transferred from the phone runner.",
            "- Inspect the worktree before continuing implementation.",
            "",
        ]
    )
    return "\n".join(lines)


def write_phone_session_report(args: argparse.Namespace) -> Path:
    root = state_root(args)
    path = Path(args.report_path) if args.report_path else report_file(root, args.session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_phone_session_report(args, root), encoding="utf-8")
    return path


def build_merge_prompt(args: argparse.Namespace, report_path: Path) -> str:
    return (
        "请把 Feishu 手机 session 的可审计状态合并回当前本地 Codex thread。\n\n"
        f"1. 先读取 `{report_path}`。\n"
        f"2. 再在 `{args.project_root}` 检查 `git status --short` 和必要的 `git diff`。\n"
        "3. 只合并可验证事实：用户指令、Codex 回复、文件改动、命令结果、决策、未解决问题。\n"
        "4. 不要假设手机 runner 的隐藏上下文已经转移。\n"
        "5. 合并后用中文给出当前状态和下一步。"
    )


def process_once(args: argparse.Namespace) -> int:
    root = state_root(args)
    register_session(args)
    runner = read_runner(root, args.session_id)
    messages = read_jsonl(inbox_file(root, args.session_id))
    if args.mark_seen:
        runner["processed_count"] = len(messages)
        write_runner(root, args.session_id, runner)
        plural = "message" if len(messages) == 1 else "messages"
        print(f"marked {len(messages)} {plural} seen")
        return 0
    start = int(runner.get("processed_count", 0))
    processed = 0

    for index, message in enumerate(messages[start:], start=start):
        setattr(args, "_feishu_current_sender_open_id", message_sender(args, message) or session_sender(root, args.session_id))
        if is_btw_message(message):
            setattr(args, "_feishu_status_message_id_btw", "")
            send_status(args, btw_received_status_text(args), color="blue", channel="btw")
            response = run_btw_for_message(args, root, message, index)
            send_status(args, btw_completed_status_text(args), color="green", channel="btw")
        elif args.tmux_pane:
            setattr(args, "_feishu_status_message_id_main", "")
            response = run_live_tui_for_message(args, root, runner, message, index)
        else:
            response = run_codex_for_message(args, root, message, index)
        send_response(args, response, message)
        processed += 1
        runner["processed_count"] = max(int(runner.get("processed_count", 0)), index + 1)
        write_runner(root, args.session_id, runner)
        setattr(args, "_feishu_current_sender_open_id", "")

    plural = "message" if processed == 1 else "messages"
    print(f"processed {processed} {plural}")
    return processed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an opt-in Codex session from Feishu inbox messages.")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--state-root")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--role", default="leader")
    parser.add_argument("--profile")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--codex-session-id")
    parser.add_argument("--resume-last", action="store_true")
    parser.add_argument("--tmux-bin", default="tmux")
    parser.add_argument("--tmux-pane", help="Inject Feishu messages into an existing live Codex TUI tmux pane, for example dev:1.0.")
    parser.add_argument("--tmux-submit-key", default="Enter", help="tmux key used to submit after paste-buffer in live TUI mode.")
    parser.add_argument("--tmux-interrupt-key", default="C-c", help="tmux key used for /interrupt in live TUI mode.")
    parser.add_argument("--tmux-submit-delay-seconds", type=float, default=0.5, help="Delay between paste-buffer and submit key in live TUI mode.")
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"), help="Codex home directory used to locate live TUI transcripts.")
    parser.add_argument("--codex-transcript", help="Explicit Codex transcript JSONL to watch in live TUI mode.")
    parser.add_argument("--watch-codex-response", action=argparse.BooleanOptionalAction, default=True, help="In live TUI mode, wait for Codex task_complete and send the final answer back to Feishu.")
    parser.add_argument("--codex-response-timeout-seconds", type=float, default=900.0)
    parser.add_argument("--codex-response-poll-seconds", type=float, default=0.5)
    parser.add_argument("--btw-context-chars", type=int, default=20000)
    parser.add_argument("--btw-timeout-seconds", type=float, default=300.0)
    parser.add_argument("--feishu-status-updates", action=argparse.BooleanOptionalAction, default=True, help="Send live processing status cards to Feishu while waiting for Codex.")
    parser.add_argument("--feishu-status-mode", choices=("update", "send"), default="update", help="Update one status card or send a new status message each time.")
    parser.add_argument("--feishu-status-style", choices=("warm", "plain"), default="warm")
    parser.add_argument("--feishu-status-interval-seconds", type=float, default=15.0)
    parser.add_argument("--bridge-url", default="")
    parser.add_argument("--feishu-format", choices=("card", "text"), default="card")
    parser.add_argument("--send-feishu", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mark-seen", action="store_true", help="Mark current inbox messages processed without running Codex.")
    parser.add_argument("--write-report", action="store_true", help="Write a Phone Session Report and exit.")
    parser.add_argument("--merge-prompt", action="store_true", help="Write a Phone Session Report, print a local merge prompt, and exit.")
    parser.add_argument("--report-path", help="Override Phone Session Report output path.")
    parser.add_argument("--yolo", action="store_true", help="Pass Codex --dangerously-bypass-approvals-and-sandbox.")
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--http-timeout-seconds", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.resume_last and args.codex_session_id:
        raise SystemExit("--resume-last and --codex-session-id are mutually exclusive")
    if args.tmux_pane and (args.resume_last or args.codex_session_id):
        raise SystemExit("--tmux-pane cannot be combined with --resume-last or --codex-session-id")
    if args.write_report or args.merge_prompt:
        path = write_phone_session_report(args)
        print(path)
        if args.merge_prompt:
            print()
            print(build_merge_prompt(args, path))
        return 0
    while True:
        process_once(args)
        if args.once:
            return 0
        time.sleep(args.poll_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
