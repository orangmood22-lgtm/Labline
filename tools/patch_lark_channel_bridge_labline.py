#!/usr/bin/env python3
"""Patch an installed lark-channel-bridge bundle with Labline commands.

This is a small integration shim for deployed bridge packages when the
upstream package has not yet learned Labline remote-observation commands.
It patches the built `dist/cli.js` in-place, with a backup when `--apply`
is used.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


BEGIN = "// LABLINE_REMOTE_OBSERVATION_SHIM_BEGIN"
END = "// LABLINE_REMOTE_OBSERVATION_SHIM_END"
CHANNEL_EMPTY_BOT_ID_ENV = "LARK_CHANNEL_ALLOW_EMPTY_BOT_ID"


SHIM = r'''
// LABLINE_REMOTE_OBSERVATION_SHIM_BEGIN
var LABLINE_DEFAULT_FRAMEWORK = "__LABLINE_FRAMEWORK__";
function lablineFrameworkRoot() {
  return process.env.LABLINE_FRAMEWORK || LABLINE_DEFAULT_FRAMEWORK;
}
function lablineObservationTool() {
  return process.env.LABLINE_REMOTE_OBSERVATION_TOOL || `${lablineFrameworkRoot()}/tools/labline_remote_observation.py`;
}
function lablineLaneTool() {
  return process.env.LABLINE_LANE_TOOL || `${lablineFrameworkRoot()}/tools/lane`;
}
function lablineCodexBin() {
  return process.env.LABLINE_BTW_CODEX_BIN || process.env.CODEX_BIN || "codex";
}
function lablinePython() {
  return process.env.LABLINE_PYTHON || process.env.PYTHON || "python3";
}
function lablineAgentProxyEnvOverrides() {
  const env = {};
  const mappings = [
    ["LABLINE_AGENT_HTTP_PROXY", "http_proxy", "HTTP_PROXY"],
    ["LABLINE_AGENT_HTTPS_PROXY", "https_proxy", "HTTPS_PROXY"],
    ["LABLINE_AGENT_ALL_PROXY", "all_proxy", "ALL_PROXY"],
    ["LABLINE_AGENT_NO_PROXY", "no_proxy", "NO_PROXY"]
  ];
  for (const [source, lower, upper] of mappings) {
    const value = process.env[source];
    if (value && value.trim()) {
      env[lower] = value;
      env[upper] = value;
    }
  }
  return env;
}
function lablineBtwTimeoutMs() {
  const parsed = Number.parseInt(process.env.LABLINE_BTW_TIMEOUT_MS || "180000", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 180000;
}
function lablineForkTimeoutMs() {
  const parsed = Number.parseInt(process.env.LABLINE_FORK_TIMEOUT_MS || "15000", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 15000;
}
function lablineBtwMaxAnswerChars() {
  const parsed = Number.parseInt(process.env.LABLINE_BTW_MAX_ANSWER_CHARS || "6000", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 6000;
}
function lablineProject(ctx) {
  return effectiveWorkspaceCwd(ctx);
}
function lablineProfile(ctx) {
  return ctx.controls?.profile || "default";
}
function lablineRunJson(argv, cwd) {
  const result = spawnProcessSync(lablinePython(), [lablineObservationTool(), ...argv], {
    cwd: cwd || process.cwd(),
    encoding: "utf8",
    timeout: 1e4,
    maxBuffer: 4 * 1024 * 1024
  });
  if (result.error) {
    return { ok: false, error: result.error.message };
  }
  if (result.status !== 0) {
    const detail = `${result.stderr || result.stdout || ""}`.trim() || `exit ${result.status}`;
    return { ok: false, error: detail };
  }
  try {
    return { ok: true, value: JSON.parse(`${result.stdout || "{}"}`) };
  } catch (err) {
    return { ok: false, error: `invalid JSON from remote observation: ${err instanceof Error ? err.message : String(err)}` };
  }
}
function lablineProjectionIntervalMs() {
  const parsed = Number.parseInt(process.env.LABLINE_PROJECTION_POLL_INTERVAL_MS || "60000", 10);
  return Number.isFinite(parsed) && parsed >= 10000 ? parsed : 60000;
}
function lablineProjectionMaxPlans() {
  const parsed = Number.parseInt(process.env.LABLINE_PROJECTION_MAX_PLANS || "20", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 20;
}
function lablineProjectionDisabled() {
  const raw = process.env.LABLINE_PROJECTION_POLL_DISABLED || process.env.LABLINE_REMOTE_OBSERVATION_POLL_DISABLED || "";
  return /^(1|true|yes)$/i.test(raw);
}
function lablineProjectionIncludeCrossProfile() {
  const raw = process.env.LABLINE_PROJECTION_INCLUDE_CROSS_PROFILE || "";
  return /^(1|true|yes)$/i.test(raw);
}
function lablineAutoWakeupEnabled() {
  const raw = process.env.LABLINE_AUTO_WAKEUP_ENABLED || "";
  return /^(1|true|yes)$/i.test(raw);
}
function lablineAutoWakeupIncludeCrossProfile() {
  const raw = process.env.LABLINE_AUTO_WAKEUP_INCLUDE_CROSS_PROFILE || "";
  return /^(1|true|yes)$/i.test(raw);
}
function lablineAutoWakeupIntervalMs() {
  const parsed = Number.parseInt(process.env.LABLINE_AUTO_WAKEUP_INTERVAL_MS || "60000", 10);
  return Number.isFinite(parsed) && parsed >= 10000 ? parsed : 60000;
}
function lablineAutoWakeupBackend() {
  const value = process.env.LABLINE_AUTO_WAKEUP_BACKEND || "native-codex";
  return value === "prompt-only" || value === "native-codex" ? value : "native-codex";
}
function lablineAutoWakeupOwner(controls) {
  const profile = controls?.profile || "default";
  return process.env.LABLINE_AUTO_WAKEUP_OWNER || `labline-bridge-wakeup:${profile}`;
}
function lablineAutoWakeupCodexTimeoutSeconds() {
  const parsed = Number.parseInt(process.env.LABLINE_AUTO_WAKEUP_CODEX_TIMEOUT_SECONDS || "600", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 600;
}
function lablineAutoWakeupMaxOutputChars() {
  const parsed = Number.parseInt(process.env.LABLINE_AUTO_WAKEUP_MAX_OUTPUT_CHARS || "6000", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 6000;
}
function lablineAutoWakeupNoticeThrottleMs() {
  const parsed = Number.parseInt(process.env.LABLINE_AUTO_WAKEUP_NOTICE_THROTTLE_MS || "300000", 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 300000;
}
var lablineAutoWakeupNoticeLastSent = /* @__PURE__ */ new Map();
function lablineCaptureText(current, chunk) {
  const max = 4 * 1024 * 1024;
  if (current.length >= max) return current;
  const text = Buffer.isBuffer(chunk) ? chunk.toString("utf8") : String(chunk);
  return (current + text).slice(0, max);
}
function lablineRunLaneJson(argv, cwd, timeoutMs = 1e4) {
  const result = spawnProcessSync(lablinePython(), [lablineLaneTool(), ...argv], {
    cwd: cwd || process.cwd(),
    encoding: "utf8",
    timeout: timeoutMs,
    maxBuffer: 4 * 1024 * 1024
  });
  if (result.error) return { ok: false, error: result.error.message };
  if (result.status !== 0) {
    const detail = `${result.stderr || result.stdout || ""}`.trim() || `exit ${result.status}`;
    return { ok: false, error: detail };
  }
  try {
    return { ok: true, value: JSON.parse(`${result.stdout || "{}"}`) };
  } catch (err) {
    return { ok: false, error: `invalid JSON from lane: ${err instanceof Error ? err.message : String(err)}` };
  }
}
function lablineAutoWakeupProject(controls) {
  return controls?.profileConfig?.workspaces?.default || process.cwd();
}
function lablineBuildWakeupArgs(project, controls) {
  const args = [
    "workflow",
    "wakeup",
    "--project",
    project,
    "--json",
    "--backend",
    lablineAutoWakeupBackend(),
    "--owner",
    lablineAutoWakeupOwner(controls),
    "--codex-timeout",
    String(lablineAutoWakeupCodexTimeoutSeconds())
  ];
  const codexBin = process.env.LABLINE_AUTO_WAKEUP_CODEX_BIN || process.env.LABLINE_BTW_CODEX_BIN || process.env.CODEX_BIN || "";
  if (codexBin) args.push("--codex-bin", codexBin);
  const codexProfile = process.env.LABLINE_AUTO_WAKEUP_CODEX_PROFILE || "";
  if (codexProfile) args.push("--codex-profile", codexProfile);
  return args;
}
function lablineAutoWakeupChatTargets(project, controls, taskId) {
  const argv = [
    "delivery-targets",
    "--profile",
    controls.profile,
    "--project",
    project,
    "--limit",
    "20"
  ];
  if (lablineAutoWakeupIncludeCrossProfile()) argv.push("--include-cross-profile");
  if (taskId) argv.push("--task-id", taskId);
  const result = lablineRunJson(argv, project);
  let targets = [];
  if (!result.ok) {
    log.warn("labline-wakeup", "delivery-targets-failed", { profile: controls.profile, project, error: result.error });
  } else if (Array.isArray(result.value?.targets)) {
    targets = result.value.targets;
  }
  const envChats = (process.env.LABLINE_AUTO_WAKEUP_CHAT_ID || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const seen = new Set(targets.map((target) => String(target.chat_id || "")));
  for (const chatId of envChats) {
    if (!seen.has(chatId)) {
      targets.push({ chat_id: chatId, subscription_id: "env", target_type: "env", target_id: "env" });
      seen.add(chatId);
    }
  }
  return targets;
}
function lablineReadWakeupArtifact(project, ref) {
  if (!ref || typeof ref !== "string") return "";
  if (ref.startsWith("/") || ref.split("/").includes("..")) return "";
  try {
    return readFileSync(`${String(project).replace(/\/+$/, "")}/${ref.replace(/^\/+/, "")}`, "utf8").trim();
  } catch {
    return "";
  }
}
function lablineWakeupActionLabel(action) {
  const raw = String(action || "");
  const labels = {
    completed: "已完成",
    failed: "失败",
    started: "已启动",
    skipped: "已跳过",
    skip: "已跳过",
    blocked: "已阻塞",
    needs_confirmation: "需要确认"
  };
  return labels[raw] ? `${labels[raw]}（\`${escapeCode(raw)}\`）` : `\`${escapeCode(raw || "unknown")}\``;
}
function lablineWakeupResultMessage(project, result, code, signal, stderrText) {
  const candidate = result?.candidate && typeof result.candidate === "object" ? result.candidate : {};
  const codex = result?.codex && typeof result.codex === "object" ? result.codex : {};
  const taskId = candidate.task_id ? String(candidate.task_id) : "";
  const title = candidate.title ? String(candidate.title) : "";
  const wakeupId = result?.wakeup_id ? String(result.wakeup_id) : "";
  const action = result?.action ? String(result.action) : code === 0 ? "completed" : "failed";
  const reason = result?.reason ? String(result.reason) : "";
  let body = lablineReadWakeupArtifact(project, codex.output_ref || "");
  if (!body) body = lablineReadWakeupArtifact(project, codex.stdout_ref || "");
  if (!body && stderrText) {
    body = [
      "Leader 自动唤醒没有产出可读正文；stderr:",
      "```text",
      String(stderrText).trim().slice(0, 2000),
      "```"
    ].join("\n");
  }
  if (!body) {
    if (action === "started") {
      body = "Leader 自动唤醒已启动；后续以 runtime 状态、完成/失败通知或 `/status` 为准。";
    } else if (action === "skip" && reason === "wakeup_already_started") {
      body = "Leader 自动唤醒检查发现该候选已经触发过，本轮没有重复启动。";
    } else if (action === "skip" && reason === "lease_unavailable") {
      body = "Leader 自动唤醒检查发现 leader_session lease 正被占用，本轮没有启动新的 Leader turn。";
    } else if (action === "needs_confirmation") {
      body = "Leader 自动唤醒检查发现高风险控制意图，需要用户确认，未自动执行。";
    } else if (action === "skip") {
      body = "Leader 自动唤醒检查已运行，本轮没有启动新的 Leader turn。";
    } else {
      body = "Leader 自动唤醒已结束，但没有产出可读正文。";
    }
  }
  const header = [
    action === "completed" || action === "failed" ? "Labline Leader 自动唤醒结果" : "Labline Leader 自动唤醒检查",
    "",
    taskId ? `任务：\`${escapeCode(taskId)}\`` : "",
    title ? `标题：${escapeMd(title)}` : "",
    wakeupId ? `唤醒：\`${escapeCode(wakeupId)}\`` : "",
    `结果：${lablineWakeupActionLabel(action)}`,
    reason ? `原因：\`${escapeCode(reason)}\`` : "",
    signal ? `信号：\`${escapeCode(String(signal))}\`` : ""
  ].filter(Boolean).join("\n");
  const maxChars = lablineAutoWakeupMaxOutputChars();
  const budget = Math.max(500, maxChars - header.length - 80);
  if (body.length > budget) body = `${body.slice(0, budget)}\n\n[Leader 输出已截断，完整内容见项目 .labline/runtime/wakeups/]`;
  return `${header}\n\n${body}`;
}
function lablineWakeupResultCard(message, result) {
  const action = String(result?.action || "");
  const state = {
    blocks: [{ kind: "text", content: message, streaming: false }],
    reasoning: { content: "", active: false },
    footer: "streaming",
    terminal: "done"
  };
  if (typeof renderCard === "function") {
    return renderCard(state);
  }
  return shell(`Labline 自动唤醒${action === "failed" ? "失败" : "结果"}`, [
    divMd(message)
  ]);
}
async function lablineDeliverAutoWakeupResult(channel, project, controls, result, code, signal, stderrText) {
  const action = String(result?.action || "");
  const reason = String(result?.reason || "");
  if (!result || (action === "skip" && reason === "healthy_or_no_escalation")) {
    log.info("labline-wakeup", "delivery-skipped", { project, action: result?.action, reason: result?.reason });
    return;
  }
  if (!["completed", "failed", "started", "skip", "needs_confirmation"].includes(action)) {
    log.info("labline-wakeup", "delivery-skipped", { project, action: result?.action, reason: result?.reason });
    return;
  }
  const candidate = result.candidate && typeof result.candidate === "object" ? result.candidate : {};
  const taskId = candidate.task_id ? String(candidate.task_id) : "";
  const targets = lablineAutoWakeupChatTargets(project, controls, taskId);
  if (targets.length === 0) {
    log.warn("labline-wakeup", "delivery-no-target", { profile: controls.profile, project, taskId });
    return;
  }
  const message = lablineWakeupResultMessage(project, result, code, signal, stderrText);
  for (const target of targets) {
    const chatId = String(target.chat_id || "");
    if (!chatId) continue;
    try {
      await channel.send(chatId, { card: lablineWakeupResultCard(message, result) });
      log.info("labline-wakeup", "delivery-sent", { profile: controls.profile, project, chatId, taskId, action: result.action });
    } catch (err) {
      const cardError = err instanceof Error ? err.message : String(err);
      try {
        await channel.send(chatId, { markdown: message });
        log.info("labline-wakeup", "delivery-fallback-sent", { profile: controls.profile, project, chatId, taskId, action: result.action, cardError });
      } catch (fallbackErr) {
        log.warn("labline-wakeup", "delivery-failed", {
          profile: controls.profile,
          project,
          chatId,
          taskId,
          error: fallbackErr instanceof Error ? fallbackErr.message : String(fallbackErr),
          cardError
        });
      }
    }
  }
}
function lablineAutoWakeupNoticeKey(project, result) {
  const candidate = result?.candidate && typeof result.candidate === "object" ? result.candidate : {};
  const intent = result?.intent && typeof result.intent === "object" ? result.intent : {};
  return [
    project,
    result?.action || "",
    result?.reason || "",
    result?.wakeup_key || "",
    result?.wakeup_id || "",
    candidate.task_id || "",
    candidate.status || "",
    intent.intent_id || ""
  ].join("|");
}
async function lablineMaybeDeliverAutoWakeupNotice(channel, project, controls, result, code, signal, stderrText) {
  if (!result || (result.action === "skip" && result.reason === "healthy_or_no_escalation")) return;
  const key = lablineAutoWakeupNoticeKey(project, result);
  const throttleMs = lablineAutoWakeupNoticeThrottleMs();
  const now = Date.now();
  const last = lablineAutoWakeupNoticeLastSent.get(key) || 0;
  if (throttleMs > 0 && last && now - last < throttleMs) {
    log.info("labline-wakeup", "notice-throttled", { project, action: result.action, reason: result.reason, throttleMs });
    return;
  }
  lablineAutoWakeupNoticeLastSent.set(key, now);
  await lablineDeliverAutoWakeupResult(channel, project, controls, result, code, signal, stderrText);
}
function lablineParseWakeupJson(stdout) {
  const text = String(stdout || "").trim();
  if (!text) return { ok: false, error: "empty wakeup stdout" };
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}
function lablineSpawnAutoWakeup(project, controls, channel) {
  const args = lablineBuildWakeupArgs(project, controls);
  let stdout = "";
  let stderr = "";
  const child = spawnProcess(lablinePython(), [lablineLaneTool(), ...args], {
    cwd: project || process.cwd(),
    env: process.env,
    detached: true,
    stdio: ["ignore", "pipe", "pipe"]
  });
  child.stdout?.on("data", (chunk) => {
    stdout = lablineCaptureText(stdout, chunk);
  });
  child.stderr?.on("data", (chunk) => {
    stderr = lablineCaptureText(stderr, chunk);
  });
  child.on("error", (err) => {
    log.warn("labline-wakeup", "spawn-failed", { project, error: err instanceof Error ? err.message : String(err) });
  });
  child.on("exit", (code, signal) => {
    log.info("labline-wakeup", "process-exit", { project, code, signal });
    const parsed = lablineParseWakeupJson(stdout);
    if (!parsed.ok) {
      log.warn("labline-wakeup", "result-parse-failed", { project, error: parsed.error, stderr: stderr.slice(0, 500) });
      return;
    }
    void lablineMaybeDeliverAutoWakeupNotice(channel, project, controls, parsed.value, code, signal, stderr)
      .catch((err) => log.warn("labline-wakeup", "delivery-threw", { project, error: err instanceof Error ? err.message : String(err) }));
  });
  child.unref();
  log.info("labline-wakeup", "spawned", { project, pid: child.pid, backend: lablineAutoWakeupBackend() });
  return child;
}
function lablineStartAutoWakeupLoop({ channel, controls }) {
  if (!lablineAutoWakeupEnabled()) {
    log.info("labline-wakeup", "disabled", { profile: controls.profile });
    return { stop() {} };
  }
  const intervalMs = lablineAutoWakeupIntervalMs();
  let stopped = false;
  let running = false;
  let childActive = false;
  const tick = async () => {
    if (stopped || running || childActive) return;
    running = true;
    try {
      const project = lablineAutoWakeupProject(controls);
      const plan = lablineRunLaneJson([
        "workflow",
        "wakeup-plan",
        "--project",
        project,
        "--json",
        "--owner",
        lablineAutoWakeupOwner(controls)
      ], project);
      if (!plan.ok) {
        log.warn("labline-wakeup", "plan-failed", { profile: controls.profile, project, error: plan.error });
        return;
      }
      const value = plan.value || {};
      if (value.action !== "acquire_lease" || value.next_action !== "start_leader_turn") {
        if (value.action === "needs_confirmation") {
          log.warn("labline-wakeup", "needs-confirmation", { profile: controls.profile, project, reason: value.reason });
        }
        await lablineMaybeDeliverAutoWakeupNotice(channel, project, controls, value, 0, null, "");
        return;
      }
      try {
        const child = lablineSpawnAutoWakeup(project, controls, channel);
        childActive = true;
        child.on("exit", () => {
          childActive = false;
        });
        child.on("error", () => {
          childActive = false;
        });
      } catch (err) {
        childActive = false;
        log.warn("labline-wakeup", "spawn-threw", { project, error: err instanceof Error ? err.message : String(err) });
      }
    } finally {
      running = false;
    }
  };
  const timer = setInterval(() => void tick().catch((err) => log.warn("labline-wakeup", "tick-failed", { error: String(err) })), intervalMs);
  void tick().catch((err) => log.warn("labline-wakeup", "tick-failed", { error: String(err) }));
  log.info("labline-wakeup", "started", { profile: controls.profile, intervalMs, backend: lablineAutoWakeupBackend() });
  return {
    stop() {
      stopped = true;
      clearInterval(timer);
    }
  };
}
function lablineStreamFlushTimeoutMs() {
  const parsed = Number.parseInt(process.env.LABLINE_STREAM_FLUSH_TIMEOUT_MS || "15000", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 15000;
}
function lablineStreamTerminalGraceMs() {
  const parsed = Number.parseInt(process.env.LABLINE_STREAM_TERMINAL_GRACE_MS || "15000", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 15000;
}
function lablinePostDoneExitGraceMs() {
  const parsed = Number.parseInt(process.env.LABLINE_POST_DONE_EXIT_GRACE_MS || "30000", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 30000;
}
function lablineDefaultRunIdleTimeoutMinutes() {
  const raw = process.env.LABLINE_DEFAULT_RUN_IDLE_TIMEOUT_MINUTES;
  if (raw === void 0 || raw === "") return 15;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 0) return 15;
  return Math.min(Math.floor(parsed), 120);
}
function lablineRunningTickerMs() {
  const parsed = Number.parseInt(process.env.LABLINE_RUNNING_TICKER_MS || "1000", 10);
  return Number.isFinite(parsed) && parsed >= 1000 ? parsed : 1000;
}
function lablineStateWithRunStartedAt(state, startedAt) {
  if (!state || state.terminal !== "running" || state.runStartedAt) return state;
  return { ...state, runStartedAt: startedAt || Date.now() };
}
function lablineFormatElapsed(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}
function lablineRunningElapsedText(state) {
  if (!state?.runStartedAt) return "";
  return `（${lablineFormatElapsed(Date.now() - state.runStartedAt)}）`;
}
function lablineRegisterInterruptNotifier(handle, notify) {
  if (!handle || typeof notify !== "function") return () => {};
  if (!handle.interruptNotifiers) handle.interruptNotifiers = new Set();
  handle.interruptNotifiers.add(notify);
  return () => handle.interruptNotifiers?.delete(notify);
}
function lablineMarkdownTerminalFallbackMode() {
  const raw = (process.env.LABLINE_MARKDOWN_TERMINAL_FALLBACK_ENABLED || "").trim();
  if (!raw) return "verify";
  if (/^(0|false|no|off|disabled)$/i.test(raw)) return "off";
  if (/^(verify|auto)$/i.test(raw)) return "verify";
  if (/^(1|true|yes|on|always)$/i.test(raw)) return "always";
  return "verify";
}
function lablineMarkdownTerminalFallbackEnabled() {
  return lablineMarkdownTerminalFallbackMode() !== "off";
}
function lablineMarkdownTerminalVerifyTimeoutMs() {
  const parsed = Number.parseInt(process.env.LABLINE_MARKDOWN_TERMINAL_VERIFY_TIMEOUT_MS || "5000", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 5000;
}
function lablineContainsRunningFooterText(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value || "");
  return [
    "🧠 正在思考",
    "🧰 正在调用工具",
    "✍️ 正在输出"
  ].some((marker) => text.includes(marker));
}
async function lablineFetchRawMessageWithTimeout(channel, messageId, timeoutMs) {
  if (!channel || typeof channel.fetchRawMessage !== "function") {
    return { ok: false, reason: "unavailable" };
  }
  let timer;
  const timeout = new Promise((resolve) => {
    timer = setTimeout(() => resolve({ ok: false, reason: "timeout" }), timeoutMs);
  });
  try {
    const fetched = channel.fetchRawMessage(messageId, { cardContentType: "user_card_content" })
      .then((items) => ({ ok: true, items }), (err) => ({
        ok: false,
        reason: "error",
        error: err instanceof Error ? err.message : String(err)
      }));
    return await Promise.race([fetched, timeout]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}
async function lablineMarkdownTerminalNeedsFallback({ channel, messageId, scope, label }) {
  const mode = lablineMarkdownTerminalFallbackMode();
  if (mode === "off") return { needed: false, reason: "disabled" };
  if (mode === "always") return { needed: true, reason: "forced" };
  if (!messageId) {
    log.warn("stream", "markdown-terminal-verify-missing-message", { scope, label });
    return { needed: false, reason: "missing-message-id" };
  }
  const timeoutMs = lablineMarkdownTerminalVerifyTimeoutMs();
  const result = await lablineFetchRawMessageWithTimeout(channel, messageId, timeoutMs);
  if (!result.ok) {
    log.warn("stream", "markdown-terminal-verify-failed", {
      scope,
      label,
      messageId,
      timeoutMs,
      reason: result.reason,
      ...result.error ? { error: result.error } : {}
    });
    return { needed: true, reason: result.reason || "verify-failed" };
  }
  const stale = lablineContainsRunningFooterText(result.items);
  log.info("stream", "markdown-terminal-verified", {
    scope,
    label,
    messageId,
    stale,
    items: Array.isArray(result.items) ? result.items.length : void 0
  });
  if (!stale) return { needed: false, reason: "verified-fresh" };
  log.warn("stream", "markdown-terminal-stale", { scope, label, messageId });
  return { needed: true, reason: "verified-stale" };
}
async function lablineFlushAgentState(flush, state, scope) {
  const flushDone = Promise.resolve().then(() => flush(state));
  const timeoutMs = lablineStreamFlushTimeoutMs();
  const timeout = new Promise((resolve) => setTimeout(() => resolve({ timedOut: true }), timeoutMs));
  const result = await Promise.race([
    flushDone.then(() => ({ timedOut: false }), (err) => ({ timedOut: false, err })),
    timeout
  ]);
  if (!result.timedOut) {
    if (result.err) throw result.err;
    return;
  }
  log.warn("stream", "flush-timeout", { scope, timeoutMs, footer: state?.footer, terminal: state?.terminal });
  void flushDone.catch((err) => log.warn("stream", "flush-late-failed", { scope, error: err instanceof Error ? err.message : String(err) }));
}
async function lablineSetMarkdownContentWithTimeout(ctrl, body, scope, label, terminal) {
  const updateDone = Promise.resolve().then(async () => {
    await ctrl.setContent(body);
    const impl = ctrl.impl || ctrl;
    if (terminal && typeof impl.completeTerminal === "function") {
      await impl.completeTerminal();
      log.info("stream", "markdown-terminal-completed", { scope, label });
      return;
    }
    if (impl.throttle && typeof impl.throttle.flushNow === "function") {
      await impl.throttle.flushNow();
    }
    if (impl.queue && typeof impl.queue.drain === "function") {
      await impl.queue.drain();
    }
  });
  const timeoutMs = lablineStreamFlushTimeoutMs();
  const timeout = new Promise((resolve) => setTimeout(() => resolve({ ok: false, reason: "timeout" }), timeoutMs));
  const result = await Promise.race([
    updateDone.then(() => ({ ok: true }), (err) => ({ ok: false, reason: "error", err })),
    timeout
  ]);
  if (result.ok) return result;
  const error = result.err instanceof Error ? result.err.message : result.err ? String(result.err) : void 0;
  log.warn("stream", result.reason === "timeout" ? "markdown-update-timeout" : "markdown-update-failed", {
    scope,
    label,
    terminal,
    timeoutMs,
    ...error ? { error } : {}
  });
  if (result.reason === "timeout") {
    void updateDone.catch((err) => log.warn("stream", "markdown-update-late-failed", {
      scope,
      label,
      error: err instanceof Error ? err.message : String(err)
    }));
  }
  return result;
}
async function lablineSendMarkdownTerminalFallback({ channel, chatId, sendOpts, scope, state, messageId, label }) {
  if (!state || state.terminal === "running") return;
  const body = renderText(state);
  if (!body.trim()) return;
  const decision = await lablineMarkdownTerminalNeedsFallback({ channel, messageId, scope, label: label || "terminal" });
  if (!decision.needed) {
    log.info("stream", "markdown-terminal-fallback-skipped", {
      scope,
      label: label || "terminal",
      messageId,
      reason: decision.reason
    });
    return;
  }
  try {
    const result = await channel.send(chatId, { markdown: body }, sendOpts);
    log.info("outbound", "sent", {
      type: "markdown-terminal-fallback",
      scope,
      mode: "markdown",
      chars: body.length,
      messageId: result?.messageId,
      sourceMessageId: messageId,
      reason: decision.reason,
      replyTo: sendOpts?.replyTo,
      replyInThread: sendOpts?.replyInThread === true
    });
  } catch (err) {
    log.warn("outbound", "markdown-terminal-fallback-failed", {
      scope,
      err: err instanceof Error ? err.message : String(err)
    });
  }
}
function lablineCardContinuationMaxAgeMs() {
  const parsed = Number.parseInt(process.env.LABLINE_CARD_CONTINUATION_MAX_AGE_MS || "1200000", 10);
  return Number.isFinite(parsed) && parsed >= 60000 ? parsed : 1200000;
}
function lablineCardContinuationIdleMs() {
  const parsed = Number.parseInt(process.env.LABLINE_CARD_CONTINUATION_IDLE_MS || "60000", 10);
  return Number.isFinite(parsed) && parsed >= 15000 ? parsed : 60000;
}
function lablineCardContinuationMaxCards() {
  const parsed = Number.parseInt(process.env.LABLINE_CARD_CONTINUATION_MAX_CARDS || "8", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 8;
}
function lablineContinuationReasonText(reason) {
  if (reason === "max-age") return "上一张卡片达到更新时长上限";
  if (reason === "idle-probe") return "上一张卡片长时间没有确认更新";
  if (reason === "stream-ended") return "上一张卡片更新流已经结束";
  if (reason === "fallback") return "上一张卡片没有按时完成最终更新";
  if (reason === "timeout") return "上一张卡片更新超时";
  if (reason === "error") return "上一张卡片更新失败";
  return "上一张卡片可能已停止接收更新";
}
function lablineDecorateContinuationCard(card, generation, reason) {
  const body = card && typeof card.body === "object" ? card.body : {};
  const elements = Array.isArray(body.elements) ? body.elements : [];
  const config = card && typeof card.config === "object" ? card.config : {};
  const summary = config.summary && typeof config.summary === "object" ? config.summary : {};
  const note = {
    tag: "markdown",
    content: `_已切换到续接卡片 #${generation}；${lablineContinuationReasonText(reason)}。_`,
    text_size: "notation"
  };
  return {
    ...card,
    config: {
      ...config,
      summary: {
        ...summary,
        content: `续接更新${summary.content ? ` · ${summary.content}` : ""}`
      }
    },
    body: {
      ...body,
      elements: [note, ...elements]
    }
  };
}
async function lablineUpdateCardWithTimeout(ctrl, card, scope, label) {
  const updateDone = Promise.resolve().then(async () => {
    await ctrl.update(card);
    const impl = ctrl.impl || ctrl;
    if (typeof impl.patch === "function") {
      await impl.patch();
    } else if (impl.queue && typeof impl.queue.drain === "function") {
      await impl.queue.drain();
    }
  });
  const timeoutMs = lablineStreamFlushTimeoutMs();
  const timeout = new Promise((resolve) => setTimeout(() => resolve({ ok: false, reason: "timeout" }), timeoutMs));
  const result = await Promise.race([
    updateDone.then(() => ({ ok: true }), (err) => ({ ok: false, reason: "error", err })),
    timeout
  ]);
  if (result.ok) return result;
  const error = result.err instanceof Error ? result.err.message : result.err ? String(result.err) : void 0;
  log.warn("stream", result.reason === "timeout" ? "card-update-timeout" : "card-update-failed", {
    scope,
    label,
    timeoutMs,
    ...error ? { error } : {}
  });
  if (result.reason === "timeout") {
    void updateDone.catch((err) => log.warn("stream", "card-update-late-failed", {
      scope,
      label,
      error: err instanceof Error ? err.message : String(err)
    }));
  }
  return result;
}
function lablineCreateCardContinuationStream({ channel, chatId, sendOpts, scope, render }) {
  const runStartedAt = Date.now();
  let latestState = lablineStateWithRunStartedAt(initialState, runStartedAt);
  let activeCtrl;
  let activeStartedAt = 0;
  let generation = 0;
  let starting = false;
  let closed = false;
  let ageTimer;
  let idleTimer;
  let tickerTimer;
  let closeContinuation;
  const closedPromise = new Promise((resolve) => {
    closeContinuation = resolve;
  });
  const maxAgeMs = lablineCardContinuationMaxAgeMs();
  const idleMs = lablineCardContinuationIdleMs();
  const maxCards = lablineCardContinuationMaxCards();
  const cardFor = (state, reason) => {
    const timedState = lablineStateWithRunStartedAt(state || initialState, runStartedAt);
    return generation > 0
      ? lablineDecorateContinuationCard(render(timedState), generation, reason)
      : render(timedState);
  };
  const clearAgeTimer = () => {
    if (ageTimer) clearTimeout(ageTimer);
    ageTimer = void 0;
  };
  const clearIdleTimer = () => {
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = void 0;
  };
  const clearTickerTimer = () => {
    if (tickerTimer) clearInterval(tickerTimer);
    tickerTimer = void 0;
  };
  const armTicker = () => {
    clearTickerTimer();
    const tickerMs = lablineRunningTickerMs();
    if (closed || tickerMs <= 0 || !activeCtrl) return;
    tickerTimer = setInterval(() => {
      void (async () => {
        if (closed || !activeCtrl || latestState?.terminal !== "running") {
          clearTickerTimer();
          return;
        }
        const result = await lablineUpdateCardWithTimeout(activeCtrl, cardFor(latestState, "ticker"), scope, `generation-${generation}-ticker`);
        if (!result.ok) {
          await startContinuation(latestState, result.reason || "ticker");
        }
      })();
    }, tickerMs);
  };
  const armIdleProbe = () => {
    clearIdleTimer();
    if (closed || idleMs <= 0 || !activeCtrl) return;
    idleTimer = setTimeout(() => {
      void (async () => {
        if (closed || !activeCtrl || latestState?.terminal !== "running") return;
        const result = await lablineUpdateCardWithTimeout(activeCtrl, cardFor(latestState, "idle-probe"), scope, `generation-${generation}-idle-probe`);
        if (!result.ok) {
          await startContinuation(latestState, result.reason || "idle-probe");
          return;
        }
        armIdleProbe();
      })();
    }, idleMs);
  };
  const armAgeTimer = () => {
    clearAgeTimer();
    if (closed || maxAgeMs <= 0) return;
    ageTimer = setTimeout(() => {
      void startContinuation(latestState, "max-age");
    }, maxAgeMs);
  };
  const startContinuation = async (state, reason) => {
    latestState = lablineStateWithRunStartedAt(state, runStartedAt);
    if (closed || starting || generation >= maxCards) return false;
    starting = true;
    activeCtrl = void 0;
    clearAgeTimer();
    clearIdleTimer();
    clearTickerTimer();
    generation += 1;
    const thisGeneration = generation;
    const timeoutMs = lablineStreamFlushTimeoutMs();
    log.warn("stream", "card-continuation-start", { scope, generation: thisGeneration, reason, maxAgeMs, idleMs });
    const clearStartingTimer = setTimeout(() => {
      if (starting && generation === thisGeneration) {
        starting = false;
        log.warn("stream", "card-continuation-producer-timeout", { scope, generation: thisGeneration, timeoutMs });
      }
    }, timeoutMs);
    try {
      const streamDone = channel.stream(
        chatId,
        {
          card: {
            initial: lablineDecorateContinuationCard(render(latestState), thisGeneration, reason),
            producer: async (ctrl) => {
              if (generation !== thisGeneration || closed) return;
              activeCtrl = ctrl;
              activeStartedAt = Date.now();
              starting = false;
              clearTimeout(clearStartingTimer);
              armAgeTimer();
              armIdleProbe();
              armTicker();
              await lablineUpdateCardWithTimeout(
                ctrl,
                lablineDecorateContinuationCard(render(latestState), thisGeneration, reason),
                scope,
                `continuation-${thisGeneration}-initial`
              );
              await closedPromise;
            }
          }
        },
        sendOpts
      );
      void streamDone.then(
        () => log.info("stream", "card-continuation-finished", { scope, generation: thisGeneration }),
        (err) => {
          if (generation === thisGeneration) starting = false;
          log.warn("stream", "card-continuation-failed", {
            scope,
            generation: thisGeneration,
            error: err instanceof Error ? err.message : String(err)
          });
          void startContinuation(latestState, "stream-ended");
        }
      );
      return true;
    } catch (err) {
      starting = false;
      clearTimeout(clearStartingTimer);
      log.warn("stream", "card-continuation-send-failed", {
        scope,
        generation: thisGeneration,
        error: err instanceof Error ? err.message : String(err)
      });
      return false;
    }
  };
  return {
    setPrimary(ctrl) {
      if (closed || generation > 0) return;
      activeCtrl = ctrl;
      activeStartedAt = Date.now();
      armAgeTimer();
      armIdleProbe();
      armTicker();
    },
    initial() {
      return cardFor(latestState, "initial");
    },
    async update(state) {
      latestState = lablineStateWithRunStartedAt(state, runStartedAt);
      if (closed || !activeCtrl) return;
      if (maxAgeMs > 0 && Date.now() - activeStartedAt >= maxAgeMs) {
        await startContinuation(latestState, "max-age");
        return;
      }
      const result = await lablineUpdateCardWithTimeout(activeCtrl, cardFor(latestState, "continued"), scope, `generation-${generation}`);
      if (!result.ok) {
        await startContinuation(latestState, result.reason || "error");
        return;
      }
      armIdleProbe();
    },
    async fallback(state) {
      latestState = lablineStateWithRunStartedAt(state, runStartedAt);
      const started = await startContinuation(latestState, "fallback");
      if (started) return;
      if (activeCtrl) {
        const result = await lablineUpdateCardWithTimeout(activeCtrl, cardFor(latestState, "fallback"), scope, `generation-${generation}-fallback`);
        if (result.ok) return;
      }
      try {
        await channel.send(
          chatId,
          { card: lablineDecorateContinuationCard(render(latestState), generation + 1, "fallback") },
          sendOpts
        );
      } catch (err) {
        log.warn("stream", "card-continuation-static-fallback-failed", {
          scope,
          error: err instanceof Error ? err.message : String(err)
        });
      }
    },
    close() {
      if (closed) return;
      closed = true;
      clearAgeTimer();
      clearIdleTimer();
      clearTickerTimer();
      if (closeContinuation) closeContinuation();
    }
  };
}
function lablineProjectionAttention(plan) {
  const hint = plan && typeof plan.attention_hint === "object" ? plan.attention_hint : void 0;
  if (plan?.reason !== "stale_projection" && hint?.kind !== "stale_projection") return "";
  const task = hint?.task_id ? `\n任务：\`${escapeCode(hint.task_id)}\`` : "";
  const action = hint?.current_action ? `\n卡片阶段：${escapeMd(String(hint.current_action))}` : "";
  const staleAfter = hint?.stale_after ? `\n过期判断时间: \`${escapeCode(hint.stale_after)}\`` : "";
  const message = hint?.message ? escapeMd(String(hint.message)) : "飞书卡片状态可能已经过期；任务可能仍在本地运行。";
  return [
    `提示：长任务卡片状态可能已经过期${task}${action}${staleAfter}`,
    message
  ].join("\n");
}
const LABLINE_STATUS_LABELS = {
  running: "运行中",
  starting: "启动中",
  waiting_on_job: "等待外部任务",
  blocked: "已阻塞",
  need_decision: "等待决策",
  failed: "失败",
  anomaly: "异常",
  stale: "状态过期",
  recovering: "恢复中",
  recently_completed: "最近完成",
  completed: "已完成",
  cancelled: "已取消",
  terminal: "已到终态",
  done: "已完成",
  new: "新建",
  unknown: "未知"
};
const LABLINE_REASON_LABELS = {
  anomaly: "检测到异常",
  blocked: "任务阻塞",
  need_decision: "等待决策",
  failed: "任务失败",
  terminal: "任务到达终态",
  escalation: "需要升级处理",
  stale_projection: "飞书显示可能过期",
  explicit_status: "主动查询状态",
  progress: "普通进度更新",
  already_delivered: "相同状态已推送",
  delivery_retry_throttled: "投递重试被限流",
  throttled_no_significant_change: "无显著变化，已限流",
  no_significant_change: "无显著变化"
};
const LABLINE_TEXT_REWRITES = [
  ["agent executor did not progress past starting before next_expected_update", "agent executor 启动后没有在 next_expected_update 前继续推进；通常表示子 agent 句柄丢失或执行器没有真正跑起来"],
  ["Creating runtime status and reading required Coder/TDD/diagnose context before code changes", "正在创建 runtime 状态并读取 Coder/TDD/diagnose 必需上下文，尚未进入代码修改"],
  ["reading required context before test edits", "正在读取必要上下文，尚未开始测试修改"],
  ["Fix RemDet YOLOv5 runtime ignore propagation for R002 gate", "修复 RemDet YOLOv5 在 R002 gate 的 ignored regions 运行时传播"],
  ["Extend RemDet ignore propagation patch helper with TDD tests", "为 RemDet ignored regions 传播补丁 helper 增加 TDD 测试"],
  ["Target detector route does not consume R001 ignore_adapter/top-level ignore_regions; per gate, R003 must not start", "目标 detector 路径没有消费 R001 的 ignore_adapter/top-level ignore_regions；按 gate 规则不能启动 R003"],
  ["Compiled MMCV works, but official RemDet YOLOv5 train collate/model preprocessor drops ignored regions before model input; pseudo_collate preserves them but is incompatible with YOLOv5DetDataPreprocessor", "编译版 MMCV 可用，但官方 RemDet YOLOv5 训练的 collate/model preprocessor 在进入模型前丢掉 ignored regions；pseudo_collate 能保留它们，但与 YOLOv5DetDataPreprocessor 不兼容"],
  ["Full RemDet dataloader/training requires compiled MMCV ops; mmcv-lite import fails with ModuleNotFoundError: mmcv._ext", "完整 RemDet dataloader/training 需要编译版 MMCV ops；mmcv-lite 导入失败：ModuleNotFoundError: mmcv._ext"],
  ["R001 complete; R002 ignore adapter consumption blocked; R003 not started", "R001 已完成；R002 的 ignore adapter 消费链路阻塞；R003 未启动"],
  ["Stopped before R003 because R002 full runtime ignore propagation gate failed", "因 R002 完整运行时 ignored regions 传播 gate 失败，已在 R003 前停止"],
  ["R001 regenerated; R002 source-level smoke passed; R003 not started because full RemDet runtime lacks compiled mmcv._ext", "R001 已重新生成；R002 源码级 smoke 通过；因完整 RemDet runtime 缺少编译版 mmcv._ext，R003 未启动"],
  ["restricted Phase 3 R000 and R001-R003 limited sanity", "受限 Phase 3：R000 与 R001-R003 有限 sanity"],
  ["Phase 3 RemDet compiled MMCV runtime gate then R003 naive sanity if unblocked", "Phase 3：RemDet 编译版 MMCV runtime gate；若解除阻塞再跑 R003 naive sanity"],
  ["Restricted Phase 3: rerun R001/R002 only", "受限 Phase 3：只重跑 R001/R002"]
];
const LABLINE_COUNT_KEYS = ["running", "blocked", "need_decision", "failed", "recently_completed", "anomaly"];
function lablineReadableText(value) {
  let text = String(value || "");
  for (const [from, to] of LABLINE_TEXT_REWRITES) {
    text = text.split(from).join(to);
  }
  return text;
}
function lablineEnumLabel(value, labels) {
  const raw = String(value || "").trim();
  if (!raw) return "未知";
  const label = labels[raw] || raw;
  return label === raw ? `\`${escapeCode(raw)}\`` : `${label}（\`${escapeCode(raw)}\`）`;
}
function lablineStatusLabel(value) {
  return lablineEnumLabel(value, LABLINE_STATUS_LABELS);
}
function lablineReasonLabel(value) {
  return lablineEnumLabel(value, LABLINE_REASON_LABELS);
}
function lablineStatusCountParts(counts) {
  return LABLINE_COUNT_KEYS
    .filter((key) => counts[key] !== void 0)
    .map((key) => `${LABLINE_STATUS_LABELS[key] || key}=${counts[key]}`);
}
function lablineProjectionTarget(plan) {
  if (plan.target_type === "task") {
    const id = plan.target_id ? ` \`${escapeCode(plan.target_id)}\`` : "";
    return `任务${id}`;
  }
  return "项目整体";
}
function lablineProjectionMessage(plan) {
  const project = String(plan.project_root || "");
  const target = lablineProjectionTarget(plan);
  const reason = plan.reason ? `\n原因：${lablineReasonLabel(plan.reason)}` : "";
  const attention = lablineProjectionAttention(plan);
  const summary = project ? lablineStatusSummary(project) : "当前 Labline 状态读取失败：projection plan 缺少 project_root。";
  const lines = ["Labline 自动状态更新", ""];
  if (attention) lines.push(attention, "");
  lines.push(`对象：${target}${reason}`, "", summary);
  return lines.join("\n");
}
function lablineProjectionCard(message) {
  return shell("Labline 自动状态更新", [
    divMd(message)
  ]);
}
function lablineMessageId(result) {
  return String(result?.messageId || result?.message_id || "");
}
function lablineCanUpdateProjectionCard(channel, plan) {
  const mode = String(plan.previous_delivery_mode || "");
  return Boolean(plan.previous_message_id) && (!mode || mode === "card" || mode === "card_update") && typeof channel.updateCard === "function";
}
async function lablineSendProjectionStatusCard(channel, plan) {
  const message = lablineProjectionMessage(plan);
  try {
    const sent = await channel.send(plan.chat_id, { card: lablineProjectionCard(message) });
    return { messageId: lablineMessageId(sent), mode: "card" };
  } catch (err) {
    const cardError = err instanceof Error ? err.message : String(err);
    const sent = await channel.send(plan.chat_id, { markdown: message });
    return { messageId: lablineMessageId(sent), mode: "markdown", cardError };
  }
}
async function lablinePatchProjectionStatusCard(channel, plan) {
  const messageId = String(plan.previous_message_id || "");
  if (!lablineCanUpdateProjectionCard(channel, plan)) {
    return { updated: false, reason: messageId ? "previous-message-not-card" : "missing-message-id" };
  }
  await channel.updateCard(messageId, lablineProjectionCard(lablineProjectionMessage(plan)));
  return { updated: true, messageId, mode: "card_update" };
}
function lablineRecordProjectionDelivery(plan, status, error, messageId, deliveryMode) {
  const argv = [
    "delivery-record",
    "--delivery-key",
    String(plan.delivery_key || ""),
    "--subscription-id",
    String(plan.subscription_id || ""),
    "--projection-id",
    String(plan.projection_id || ""),
    "--status",
    status,
    "--state-signature",
    String(plan.state_signature || "")
  ];
  if (plan.reason) argv.push("--reason", String(plan.reason).slice(0, 120));
  if (error) argv.push("--error", String(error).slice(0, 500));
  if (messageId) argv.push("--message-id", String(messageId).slice(0, 200));
  if (deliveryMode) argv.push("--delivery-mode", String(deliveryMode).slice(0, 80));
  return lablineRunJson(argv, plan.project_root || process.cwd());
}
async function lablineDeliverProjectionPlan(channel, plan) {
  if (plan.action === "patch") {
    let messageId = "";
    let deliveryMode = "";
    try {
      const patched = await lablinePatchProjectionStatusCard(channel, plan);
      if (patched.updated) {
        messageId = patched.messageId;
        deliveryMode = patched.mode;
        log.info("labline-projection", "patch-updated", { subscriptionId: plan.subscription_id, messageId });
      } else {
        const sent = await lablineSendProjectionStatusCard(channel, plan);
        messageId = sent.messageId;
        deliveryMode = sent.mode;
        log.info("labline-projection", "patch-sent", { subscriptionId: plan.subscription_id, reason: patched.reason, mode: sent.mode });
      }
      const recorded = lablineRecordProjectionDelivery(plan, "delivered", void 0, messageId, deliveryMode);
      if (!recorded.ok) {
        log.warn("labline-projection", "patch-record-failed", { subscriptionId: plan.subscription_id, error: recorded.error });
      } else {
        log.info("labline-projection", "patch-recorded", { subscriptionId: plan.subscription_id, reason: plan.reason });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const recorded = lablineRecordProjectionDelivery(plan, "failed", message, messageId, deliveryMode);
      if (!recorded.ok) {
        log.warn("labline-projection", "patch-failure-record-failed", { subscriptionId: plan.subscription_id, error: recorded.error });
      }
      log.warn("labline-projection", "patch-failed", { subscriptionId: plan.subscription_id, error: message });
    }
    return;
  }
  if (plan.action !== "fresh_reply") return;
  try {
    const sent = await lablineSendProjectionStatusCard(channel, plan);
    const recorded = lablineRecordProjectionDelivery(plan, "delivered", sent.cardError, sent.messageId, sent.mode);
    if (!recorded.ok) {
      log.warn("labline-projection", "delivery-record-failed", { subscriptionId: plan.subscription_id, error: recorded.error });
    } else {
      log.info("labline-projection", "fresh-reply-sent", { subscriptionId: plan.subscription_id, reason: plan.reason, mode: sent.mode });
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const recorded = lablineRecordProjectionDelivery(plan, "failed", message);
    if (!recorded.ok) {
      log.warn("labline-projection", "delivery-failure-record-failed", { subscriptionId: plan.subscription_id, error: recorded.error });
    }
    log.warn("labline-projection", "fresh-reply-failed", { subscriptionId: plan.subscription_id, error: message });
  }
}
function lablineStartProjectionLoop({ channel, controls }) {
  if (lablineProjectionDisabled()) {
    log.info("labline-projection", "disabled", { profile: controls.profile });
    return { stop() {} };
  }
  const intervalMs = lablineProjectionIntervalMs();
  let stopped = false;
  let running = false;
  const tick = async () => {
    if (stopped || running) return;
    running = true;
    try {
      const cwd = controls.profileConfig?.workspaces?.default || process.cwd();
      const pollArgs = [
        "projection-poll",
        "--profile",
        controls.profile,
        "--project",
        cwd,
        "--limit",
        String(lablineProjectionMaxPlans())
      ];
      if (lablineProjectionIncludeCrossProfile()) pollArgs.push("--include-cross-profile");
      const polled = lablineRunJson(pollArgs, cwd);
      if (!polled.ok) {
        log.warn("labline-projection", "poll-failed", { profile: controls.profile, error: polled.error });
        return;
      }
      const plans = Array.isArray(polled.value?.plans) ? polled.value.plans : [];
      if (plans.length > 0) {
        log.info("labline-projection", "plans", { profile: controls.profile, count: plans.length });
      }
      for (const plan of plans) {
        await lablineDeliverProjectionPlan(channel, plan);
      }
      const errors = Array.isArray(polled.value?.errors) ? polled.value.errors : [];
      if (errors.length > 0) {
        log.warn("labline-projection", "poll-errors", { profile: controls.profile, count: errors.length });
      }
    } finally {
      running = false;
    }
  };
  const timer = setInterval(() => void tick().catch((err) => log.warn("labline-projection", "tick-failed", { error: String(err) })), intervalMs);
  void tick().catch((err) => log.warn("labline-projection", "tick-failed", { error: String(err) }));
  log.info("labline-projection", "started", { profile: controls.profile, intervalMs });
  return {
    stop() {
      stopped = true;
      clearInterval(timer);
    }
  };
}
function lablineStatusJson(project) {
  const result = spawnProcessSync(lablinePython(), [lablineLaneTool(), "status", "--project", project, "--json"], {
    cwd: project || process.cwd(),
    encoding: "utf8",
    timeout: 1e4,
    maxBuffer: 8 * 1024 * 1024
  });
  if (result.error || result.status !== 0) {
    return JSON.stringify({ error: `${result.error?.message || result.stderr || result.stdout || "status unavailable"}`.trim() });
  }
  return `${result.stdout || "{}"}`.trim() || "{}";
}
function lablineStatusCounts(project) {
  const result = spawnProcessSync(lablinePython(), [lablineLaneTool(), "status", "--project", project, "--json"], {
    cwd: project || process.cwd(),
    encoding: "utf8",
    timeout: 1e4,
    maxBuffer: 8 * 1024 * 1024
  });
  if (result.error || result.status !== 0) return "";
  try {
    const payload = JSON.parse(`${result.stdout || "{}"}`);
    const counts = payload.counts || {};
    const parts = lablineStatusCountParts(counts);
    return parts.length ? `\n状态：${parts.join("，")}` : "";
  } catch {
    return "";
  }
}
function lablineStatusSummary(project) {
  let payload;
  try {
    payload = JSON.parse(lablineStatusJson(project));
  } catch (err) {
    return `当前 Labline 状态读取失败：${escapeMd(err instanceof Error ? err.message : String(err))}`;
  }
  if (payload.error) {
    return `当前 Labline 状态读取失败：${escapeMd(String(payload.error))}`;
  }
  const counts = payload.counts || {};
  const countParts = lablineStatusCountParts(counts);
  const tasks = Array.isArray(payload.tasks) ? payload.tasks : [];
  const interesting = tasks.filter((task) => {
    const status = String(task.status || "");
    return ["running", "waiting_on_job", "need_decision", "blocked", "failed", "stale", "anomaly", "recovering"].includes(status);
  }).slice(0, 5);
  const lines = ["当前 Labline 状态：", countParts.length ? `状态：${countParts.join("，")}` : "状态：空"];
  if (interesting.length === 0) {
    lines.push("没有正在运行、阻塞、失败、异常或等待决策的 runtime task。");
  } else {
    lines.push("相关任务：");
    for (const task of interesting) {
      const id = task.task_id || task.id || "task";
      const parts = [`- \`${escapeCode(id)}\`：状态=${lablineStatusLabel(task.status || "unknown")}`];
      if (task.title) parts.push(`任务=${escapeMd(lablineReadableText(task.title))}`);
      if (task.current_action) parts.push(`当前=${escapeMd(lablineReadableText(task.current_action))}`);
      if (task.blocker) parts.push(`阻塞=${escapeMd(lablineReadableText(task.blocker))}`);
      lines.push(parts.join("；"));
    }
  }
  return lines.join("\n");
}
async function lablineRequireProject(ctx) {
  const project = lablineProject(ctx);
  if (!project) {
    await reply(ctx, "当前 chat 没有 cwd，先用 `/cd <项目路径>` 绑定项目。");
    return "";
  }
  return project;
}
function lablineArchive(ctx, project, text) {
  return lablineRunJson([
    "archive-message",
    "--profile",
    lablineProfile(ctx),
    "--workspace",
    project,
    "--chat-id",
    ctx.msg.chatId,
    "--sender-open-id",
    ctx.msg.senderId,
    "--message-id",
    ctx.msg.messageId,
    "--text",
    text
  ], project);
}
function lablineRouteMessage(ctx, project, archiveRef, text) {
  return lablineRunJson([
    "route-message",
    "--project",
    project,
    "--profile",
    lablineProfile(ctx),
    "--workspace",
    project,
    "--archive-ref",
    archiveRef,
    "--text",
    text,
    "--chat-id",
    ctx.msg.chatId,
    "--sender-open-id",
    ctx.msg.senderId
  ], project);
}
function lablineCodexAppServerOptions(ctx) {
  const codex = ctx.controls?.profileConfig?.codex || {};
  const binary = codex.binaryPath || ctx.agent?.binary || lablineCodexBin();
  return {
    binary,
    profileStateDir: commandProfilePaths(ctx).profileDir,
    ...codex.codexHome ? { codexHome: codex.codexHome } : {},
    ...codex.inheritCodexHome !== void 0 ? { inheritCodexHome: codex.inheritCodexHome } : {}
  };
}
function lablineRecordValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : void 0;
}
function lablineStringValue(value) {
  return typeof value === "string" ? value : void 0;
}
function lablineCodexAppServerCall(ctx, method, params) {
  return new Promise((resolve, reject) => {
    const child = spawnCodexAppServer(lablineCodexAppServerOptions(ctx));
    const requestId = 2;
    const stderrChunks = [];
    let stdoutBuffer = "";
    let settled = false;
    const timer = setTimeout(() => {
      fail(new Error(`codex app-server ${method} timed out after ${lablineForkTimeoutMs()}ms`));
    }, lablineForkTimeoutMs());
    const cleanup = (kill) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      child.stdout.removeAllListeners("data");
      child.stderr.removeAllListeners("data");
      child.removeAllListeners("error");
      child.removeAllListeners("exit");
      if (kill && child.exitCode === null && child.signalCode === null) child.kill("SIGTERM");
    };
    const fail = (err) => {
      if (settled) return;
      cleanup(true);
      reject(err);
    };
    const succeed = (value) => {
      if (settled) return;
      cleanup(true);
      resolve(value);
    };
    const handleLine = (line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      let msg;
      try {
        msg = JSON.parse(trimmed);
      } catch {
        return;
      }
      if (msg?.id !== requestId) return;
      if (msg.error) {
        const error = lablineRecordValue(msg.error);
        fail(new Error(lablineStringValue(error?.message) || `codex app-server rejected ${method}`));
        return;
      }
      succeed(msg.result);
    };
    child.once("error", fail);
    child.once("exit", (code) => {
      if (settled) return;
      const stderr = Buffer.concat(stderrChunks).toString("utf8").trim();
      fail(new Error(`codex app-server exited before ${method} response: ${code ?? "signal"}${stderr ? `: ${stderr}` : ""}`));
    });
    child.stderr.on("data", (chunk) => {
      stderrChunks.push(Buffer.from(chunk));
    });
    child.stdout.on("data", (chunk) => {
      stdoutBuffer += chunk.toString("utf8");
      let nl = stdoutBuffer.indexOf("\n");
      while (nl !== -1) {
        const line = stdoutBuffer.slice(0, nl);
        stdoutBuffer = stdoutBuffer.slice(nl + 1);
        handleLine(line);
        nl = stdoutBuffer.indexOf("\n");
      }
    });
    const initialize = {
      method: "initialize",
      id: 1,
      params: {
        clientInfo: {
          name: "lark-channel-bridge-labline",
          title: "Labline Lark Bridge",
          version: "0.1.0"
        },
        capabilities: null
      }
    };
    const request = { method, id: requestId, params };
    try {
      child.stdin.write(`${JSON.stringify(initialize)}\n${JSON.stringify(request)}\n`, "utf8", (err) => {
        if (err) fail(err);
      });
    } catch (err) {
      fail(err);
    }
  });
}
async function lablineForkCodexThread(ctx, sourceThreadId, name) {
  const forked = lablineRecordValue(await lablineCodexAppServerCall(ctx, "thread/fork", { threadId: sourceThreadId }));
  const thread = lablineRecordValue(forked?.thread);
  const threadId = lablineStringValue(thread?.id);
  if (!threadId) {
    throw new Error("codex app-server thread/fork returned no thread id");
  }
  if (name) {
    await lablineRenameCodexThread(ctx, threadId, name);
  }
  return {
    threadId,
    sessionId: lablineStringValue(thread?.sessionId),
    forkedFromId: lablineStringValue(thread?.forkedFromId)
  };
}
async function lablineRenameCodexThread(ctx, threadId, name) {
  await lablineCodexAppServerCall(ctx, "thread/name/set", { threadId, name });
}
function lablineBtwAnswerRef(ctx, project, threadId) {
  const profile = String(lablineProfile(ctx)).replace(/[^A-Za-z0-9_.-]+/g, "-") || "default";
  const workspace = String(project || "workspace").replace(/[^A-Za-z0-9_.-]+/g, "-").slice(-48) || "workspace";
  const thread = String(threadId || "project").replace(/[^A-Za-z0-9_.-]+/g, "-");
  const nonce = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  return `bridge://${profile}/${workspace}/btw-answer/${thread}/${nonce}`;
}
function lablineBuildBtwPrompt(question, project, routed) {
  const statusJson = lablineStatusJson(project);
  return [
    "你是 Labline/Codex 的 BTW side-channel。",
    "请用中文直接回答用户的只读旁路问题。",
    "硬性要求：不要修改文件；不要启动、停止、重跑或推进任务；不要改变当前主会话目标；如果信息不足，明确说明你只能基于当前可见状态回答。",
    "回答要短，优先给结论和可验证状态。",
    "",
    `项目路径：${project}`,
    `用户问题：${question}`,
    "",
    "路由信息 JSON：",
    "```json",
    JSON.stringify(routed || {}, null, 2),
    "```",
    "",
    "当前 Labline runtime status JSON：",
    "```json",
    statusJson,
    "```"
  ].join("\n");
}
function lablineRunBtwAnswer(question, ctx, project, routed) {
  const tmpBase = `${process.env.TMPDIR || "/tmp"}`.replace(/\/+$/, "") || "/tmp";
  const tmpDir = `${tmpBase}/labline-btw-${process.pid}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const outputFile = `${tmpDir}/answer.txt`;
  try {
    mkdirSync(tmpDir, { recursive: true });
    const argv = ["exec", "--ephemeral", "--sandbox", "read-only", "-C", project, "-o", outputFile];
    const codexProfile = process.env.LABLINE_BTW_CODEX_PROFILE || "";
    if (codexProfile) argv.push("-p", codexProfile);
    argv.push(lablineBuildBtwPrompt(question, project, routed));
    const result = spawnProcessSync(lablineCodexBin(), argv, {
      cwd: project || process.cwd(),
      encoding: "utf8",
      timeout: lablineBtwTimeoutMs(),
      maxBuffer: 4 * 1024 * 1024
    });
    if (result.error) {
      return { ok: false, error: result.error.message };
    }
    if (result.status !== 0) {
      const detail = `${result.stderr || result.stdout || ""}`.trim() || `exit ${result.status}`;
      return { ok: false, error: detail };
    }
    let answer = "";
    try {
      answer = readFileSync(outputFile, "utf8").trim();
    } catch {
      answer = `${result.stdout || ""}`.trim();
    }
    if (!answer) {
      return { ok: false, error: "BTW produced no final answer" };
    }
    const maxChars = lablineBtwMaxAnswerChars();
    if (answer.length > maxChars) {
      answer = `${answer.slice(0, maxChars)}\n\n[BTW answer truncated]`;
    }
    return { ok: true, answer, answerRef: lablineBtwAnswerRef(ctx, project, routed?.btw_thread_id) };
  } finally {
    try {
      rmSync(tmpDir, { recursive: true, force: true });
    } catch {
    }
  }
}
function lablineBtwScope(ctx) {
  return `${ctx.scope}:labline-btw`;
}
async function lablineRunManagedBtwAnswer(question, ctx, project, routed) {
  if (!ctx.runExecutor) {
    return { ok: false, error: "bridge run executor unavailable" };
  }
  const scope = lablineBtwScope(ctx);
  ctx.workspaces.setCwd(scope, project);
  const threadId = ctx.msg.threadId;
  const sendOpts = commandReplyOptions(ctx);
  const access = ctx.msg.chatType === "p2p"
    ? canUseDm(ctx.controls.profileConfig, ctx.controls, ctx.msg.senderId)
    : canUseGroup(ctx.controls.profileConfig, ctx.controls, ctx.msg.chatId, ctx.msg.senderId);
  const capability = ctx.controls.profileConfig.agentKind === "codex" ? codexCapability(ctx.controls.profileConfig) : claudeCapability(ctx.controls.profileConfig);
  const flow = await startRunFlow({
    scopeId: scope,
    scope: {
      source: "im",
      chatId: ctx.msg.chatId,
      actorId: ctx.msg.senderId,
      ...ctx.chatMode === "topic" && threadId ? { threadId } : {}
    },
    prompt: lablineBuildBtwPrompt(question, project, routed),
    attachments: [],
    access,
    capability,
    profileConfig: ctx.controls.profileConfig,
    sessions: ctx.sessions,
    sessionCatalog: void 0,
    workspaces: ctx.workspaces,
    executor: ctx.runExecutor,
    now: Date.now(),
    stopGraceMs: getAgentStopGraceMs(ctx.controls.cfg),
    observability: {
      profile: ctx.controls.profile,
      agent: capability.agentId,
      source: "im",
      stage: "labline-btw"
    }
  });
  if (!flow.ok) {
    return { ok: false, error: flow.rejectReason.userVisible };
  }
  const { execution } = flow;
  const handle = execution.handle;
  const eventStream = execution.subscribe();
  const scopeOverride = ctx.sessions.getIdleTimeoutMinutes(scope);
  const idleTimeoutMs = scopeOverride !== void 0
    ? scopeOverride > 0 ? scopeOverride * 6e4 : void 0
    : getRunIdleTimeoutMs(ctx.controls.cfg);
  const replyMode = getMessageReplyMode(ctx.controls.cfg);
  const filterForPrefs = (state) => {
    if (getShowToolCalls(ctx.controls.cfg)) return state;
    return { ...state, blocks: state.blocks.filter((b) => b.kind !== "tool") };
  };
  const recordSession = (evt) => {
    if (evt.type === "system" && evt.model) {
      log.info("session", "btw-model", { actual: evt.model });
    }
  };
  const reactionPromise = replyMode === "card" ? void 0 : addWorkingReaction(ctx.channel, ctx.msg.messageId);
  let finalState = initialState;
  try {
    if (replyMode === "card") {
      let latestState = initialState;
      let producerStarted = false;
      const cardStream = lablineCreateCardContinuationStream({
        channel: ctx.channel,
        chatId: ctx.msg.chatId,
        sendOpts,
        scope,
        render: (state) => renderCard(filterForPrefs(state))
      });
      const renderDone = processAgentStream(
        handle,
        eventStream,
        scope,
        idleTimeoutMs,
        recordSession,
        async (state) => {
          latestState = state;
          await cardStream.update(state);
        }
      );
      const unregisterInterruptNotifier = lablineRegisterInterruptNotifier(handle, async () => {
        latestState = markInterrupted(latestState);
        await cardStream.fallback(latestState);
      });
      const streamDone = ctx.channel.stream(
        ctx.msg.chatId,
        {
          card: {
            initial: cardStream.initial(),
            producer: async (ctrl) => {
              producerStarted = true;
              cardStream.setPrimary(ctrl);
              await cardStream.update(latestState);
              try {
                await renderDone;
              } finally {
                unregisterInterruptNotifier?.();
                cardStream.close();
              }
            }
          }
        },
        sendOpts
      );
      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        latestState: () => latestState,
        fallback: async (state) => {
          await cardStream.fallback(state);
        }
      });
      unregisterInterruptNotifier?.();
      cardStream.close();
      finalState = await renderDone;
    } else if (replyMode === "markdown") {
      let latestState = initialState;
      let producerStarted = false;
      let markdownCtrl;
      let markdownMessageId;
      const renderDone = processAgentStream(
        handle,
        eventStream,
        scope,
        idleTimeoutMs,
        recordSession,
        async (state) => {
          latestState = state;
          if (markdownCtrl) {
            await lablineSetMarkdownContentWithTimeout(
              markdownCtrl,
              renderText(filterForPrefs(state)),
              scope,
              state.terminal !== "running" ? "terminal" : "update",
              state.terminal !== "running"
            );
          }
        }
      );
      const streamDone = ctx.channel.stream(
        ctx.msg.chatId,
        {
          markdown: async (ctrl) => {
            producerStarted = true;
            markdownCtrl = ctrl;
            markdownMessageId = ctrl.messageId;
            log.info("stream", "markdown-started", { scope, messageId: markdownMessageId });
            await lablineSetMarkdownContentWithTimeout(
              ctrl,
              renderText(filterForPrefs(latestState)),
              scope,
              "initial",
              latestState.terminal !== "running"
            );
            await renderDone;
          }
        },
        sendOpts
      );
      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        latestState: () => latestState,
        fallback: async () => {
        }
      });
      await lablineSendMarkdownTerminalFallback({
        channel: ctx.channel,
        chatId: ctx.msg.chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState),
        messageId: markdownMessageId,
        label: "run-terminal"
      });
      finalState = await renderDone;
    } else {
      finalState = await processAgentStream(
        handle,
        eventStream,
        scope,
        idleTimeoutMs,
        recordSession,
        async () => {
        }
      );
      await sendFinalReply({
        channel: ctx.channel,
        chatId: ctx.msg.chatId,
        scope,
        state: filterForPrefs(finalState),
        replyMode,
        sendOpts,
        cardRenderOptions: {}
      });
    }
    const answer = renderText(filterForPrefs(finalState)).trim();
    return { ok: true, answer: answer || "BTW produced no final message." };
  } catch (err) {
    log.fail("stream", err, { scope, step: "labline-btw" });
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  } finally {
    scheduleWorkingReactionCleanup(ctx.channel, ctx.msg.messageId, reactionPromise);
  }
}
async function lablineAnswerRoutedBtw(question, ctx, project, routed, archived) {
  const thread = routed.btw_thread_id ? `\nbtw_thread: \`${escapeCode(routed.btw_thread_id)}\`` : "";
  const task = routed.task_id ? `\ntask: \`${escapeCode(routed.task_id)}\`` : "";
  const counts = lablineStatusCounts(project);
  log.info("command", "labline-btw", { scope: lablineBtwScope(ctx), route: routed.route, thread: routed.btw_thread_id });
  const answered = await lablineRunManagedBtwAnswer(question, ctx, project, routed);
  if (!answered.ok) {
    await reply(ctx, `BTW 回答失败: ${escapeMd(answered.error)}${thread}${task}${counts}`);
    return;
  }
  const answerRef = lablineBtwAnswerRef(ctx, project, routed.btw_thread_id);
  const recorded = lablineRunJson([
    "btw-answer",
    "--project",
    project,
    "--btw-thread-id",
    routed.btw_thread_id,
    "--archive-ref",
    archived.archive_ref,
    "--answer-ref",
    answerRef,
    "--text",
    answered.answer
  ], project);
  if (!recorded.ok) {
    await reply(ctx, `BTW 事件记录失败: ${escapeMd(recorded.error)}`);
  }
}
async function handleLablineFollow(args, ctx) {
  const project = await lablineRequireProject(ctx);
  if (!project) return;
  const taskId = args.trim().split(/\s+/).filter(Boolean)[0] || "";
  const archived = lablineArchive(ctx, project, ctx.msg.content);
  if (!archived.ok) {
    await reply(ctx, `Remote Observation archive failed: ${escapeMd(archived.error)}`);
    return;
  }
  const argv = [
    "follow",
    "--profile",
    lablineProfile(ctx),
    "--workspace",
    project,
    "--project",
    project,
    "--chat-id",
    ctx.msg.chatId,
    "--archive-ref",
    archived.value.archive_ref
  ];
  if (taskId) argv.push("--task-id", taskId);
  const followed = lablineRunJson(argv, project);
  if (!followed.ok) {
    await reply(ctx, `Remote Observation follow failed: ${escapeMd(followed.error)}`);
    return;
  }
  const target = followed.value.target_type === "task" ? `任务 \`${escapeCode(followed.value.target_id)}\`` : "项目整体";
  await reply(ctx, `已关注 ${target}。\n订阅：\`${escapeCode(followed.value.subscription_id)}\``);
}
async function handleLablineUnfollow(args, ctx) {
  const token = args.trim().split(/\s+/).filter(Boolean)[0] || "";
  const project = lablineProject(ctx);
  const argv = ["unfollow"];
  if (token.startsWith("sub_")) {
    argv.push("--subscription-id", token);
  } else {
    if (!project) {
      await reply(ctx, "当前 chat 没有 cwd，取消默认关注需要先 `/cd <项目路径>`；或者传 `sub_...`。");
      return;
    }
    argv.push("--profile", lablineProfile(ctx), "--workspace", project, "--project", project, "--chat-id", ctx.msg.chatId);
    if (token) argv.push("--task-id", token);
  }
  const result = lablineRunJson(argv, project || process.cwd());
  if (!result.ok) {
    await reply(ctx, `Remote Observation unfollow failed: ${escapeMd(result.error)}`);
    return;
  }
  const status = result.value.status === "missing" ? "未找到关注记录" : "已取消关注";
  await reply(ctx, `${status}: \`${escapeCode(result.value.subscription_id)}\``);
}
async function handleLablineBtw(args, ctx) {
  const project = await lablineRequireProject(ctx);
  if (!project) return;
  const question = args.trim();
  if (!question) {
    await reply(ctx, "用法：`/btw <只读问题>`");
    return;
  }
  const archived = lablineArchive(ctx, project, ctx.msg.content);
  if (!archived.ok) {
    await reply(ctx, `Remote Observation archive failed: ${escapeMd(archived.error)}`);
    return;
  }
  const routed = lablineRouteMessage(ctx, project, archived.value.archive_ref, ctx.msg.content);
  if (!routed.ok) {
    await reply(ctx, `Remote Observation route failed: ${escapeMd(routed.error)}`);
    return;
  }
  const thread = routed.value.btw_thread_id ? `\nbtw_thread: \`${escapeCode(routed.value.btw_thread_id)}\`` : "";
  const task = routed.value.task_id ? `\ntask: \`${escapeCode(routed.value.task_id)}\`` : "";
  const counts = lablineStatusCounts(project);
  if (routed.value.route !== "btw") {
    await reply(ctx, `已路由，不打断当前主会话。\nroute: \`${escapeCode(routed.value.route)}\`${thread}${task}${counts}`);
    return;
  }
  await lablineAnswerRoutedBtw(question, ctx, project, routed.value, archived.value);
}
async function handleLablineFork(args, ctx) {
  const name = args.trim();
  if (ctx.controls?.profileConfig?.agentKind !== "codex") {
    await reply(ctx, "`/fork` 只支持 Codex profile；Claude profile 请用 `/new` 或 `/resume`。");
    return;
  }
  if (ctx.activeRuns.get(ctx.scope)) {
    await reply(ctx, "当前会话还有任务在运行。请等它完成，或先用 `/stop` 停止后再 `/fork`。");
    return;
  }
  const identity = ctx.sessionCatalogIdentity;
  if (!ctx.sessionCatalog || !identity || identity.agentId !== "codex") {
    await reply(ctx, "当前 chat 没有可 fork 的 Codex thread；请先完成一次普通消息，或用 `/resume` 选择历史会话。");
    return;
  }
  const entry = ctx.sessionCatalog.activeFor(identity);
  const sourceThreadId = entry?.threadId;
  if (!sourceThreadId) {
    await reply(ctx, "当前 chat 没有可 fork 的 Codex thread；请先完成一次普通消息，或用 `/resume` 选择历史会话。");
    return;
  }
  try {
    const forked = await lablineForkCodexThread(ctx, sourceThreadId, name);
    ctx.sessionCatalog.upsertActive({
      scopeId: identity.scopeId,
      agentId: "codex",
      cwdRealpath: identity.cwdRealpath,
      policyFingerprint: identity.policyFingerprint,
      threadId: forked.threadId,
      now: Date.now()
    });
    const nameLine = name ? `\nname: \`${escapeCode(name)}\`` : "";
    const sessionLine = forked.sessionId ? `\nsession: \`${escapeCode(forked.sessionId)}\`` : "";
    await reply(ctx, `已 fork 当前 Codex thread，下一条消息会进入新 thread。\nfrom: \`${escapeCode(sourceThreadId)}\`\nthread: \`${escapeCode(forked.threadId)}\`${sessionLine}${nameLine}`);
  } catch (err) {
    await reply(ctx, `fork 失败: ${escapeMd(err instanceof Error ? err.message : String(err))}`);
  }
}
async function handleLablineRename(args, ctx) {
  const name = args.trim();
  if (!name) {
    await reply(ctx, "用法：`/rename <名称>`");
    return;
  }
  if (ctx.controls?.profileConfig?.agentKind !== "codex") {
    await reply(ctx, "`/rename` 只支持 Codex profile；Claude profile 请在对应客户端里改名。");
    return;
  }
  if (ctx.activeRuns.get(ctx.scope)) {
    await reply(ctx, "当前会话还有任务在运行。请等它完成，或先用 `/stop` 停止后再 `/rename <名称>`。");
    return;
  }
  const identity = ctx.sessionCatalogIdentity;
  if (!ctx.sessionCatalog || !identity || identity.agentId !== "codex") {
    await reply(ctx, "当前 chat 没有可重命名的 Codex thread；请先完成一次普通消息，或用 `/resume` 选择历史会话。");
    return;
  }
  const entry = ctx.sessionCatalog.activeFor(identity);
  const threadId = entry?.threadId;
  if (!threadId) {
    await reply(ctx, "当前 chat 没有可重命名的 Codex thread；请先完成一次普通消息，或用 `/resume` 选择历史会话。");
    return;
  }
  try {
    await lablineRenameCodexThread(ctx, threadId, name);
    await reply(ctx, `已重命名当前 Codex thread。\nthread: \`${escapeCode(threadId)}\`\nname: \`${escapeCode(name)}\``);
  } catch (err) {
    await reply(ctx, `rename 失败: ${escapeMd(err instanceof Error ? err.message : String(err))}`);
  }
}
// LABLINE_REMOTE_OBSERVATION_SHIM_END
'''


def bridge_cli_from_bin(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved.name == "cli.js":
        return resolved
    if resolved.name == "lark-channel-bridge.mjs":
        candidate = resolved.parent.parent / "dist" / "cli.js"
        if candidate.exists():
            return candidate
    if resolved.is_dir():
        candidate = resolved / "dist" / "cli.js"
        if candidate.exists():
            return candidate
    return resolved


def resolve_bridge_cli(value: str | None) -> Path:
    if value:
        return bridge_cli_from_bin(Path(value))
    found = shutil.which("lark-channel-bridge")
    if not found:
        raise SystemExit("lark-channel-bridge not found; pass --bridge-cli")
    return bridge_cli_from_bin(Path(found))


def strip_existing_shim(text: str) -> str:
    start = text.find(BEGIN)
    if start < 0:
        return text
    end = text.find(END, start)
    if end < 0:
        raise SystemExit("found Labline shim begin marker without end marker")
    end += len(END)
    if end < len(text) and text[end] == "\n":
        end += 1
    return text[:start].rstrip() + "\n" + text[end:]


def insert_once(text: str, anchor: str, insertion: str, already: str) -> str:
    if already in text:
        return text
    if anchor not in text:
        raise SystemExit(f"bridge bundle anchor not found: {anchor!r}")
    return text.replace(anchor, anchor + insertion, 1)


def insert_after_any_anchor(text: str, anchors: list[str], insertion: str, already: str) -> str:
    if already in text:
        return text
    for anchor in anchors:
        if anchor in text:
            return text.replace(anchor, anchor + insertion, 1)
    raise SystemExit(f"bridge bundle anchor not found: one of {anchors!r}")


def patch_stop_handler(text: str) -> str:
    if "labline-btw" in text and "ctx.activeRuns.interrupt(`${scope}:labline-btw`)" in text:
        return text
    anchor = (
        "  const ok = ctx.activeRuns.interrupt(scope);\n"
        '  log.info("command", "stop", {\n'
    )
    replacement = (
        "  let ok = ctx.activeRuns.interrupt(scope);\n"
        "  if (!targetScope) ok = ctx.activeRuns.interrupt(`${scope}:labline-btw`) || ok;\n"
        '  log.info("command", "stop", {\n'
    )
    if anchor not in text:
        raise SystemExit("bridge bundle anchor not found: handleStop interrupt line")
    return text.replace(anchor, replacement, 1)


def patch_codex_item_updated(text: str) -> str:
    """Teach older bridge bundles about newer Codex JSONL events."""
    if "var CodexJsonlTranslator = class" not in text:
        return text

    if 'case "event_msg":' not in text:
        anchor = (
            '      case "turn.started":\n'
            "        return [];\n"
            '      case "item.started":\n'
        )
        insertion = (
            '      case "turn.started":\n'
            "        return [];\n"
            '      case "event_msg":\n'
            "        return this.translateEventMsg(raw);\n"
            '      case "response_item":\n'
            "        return this.translateResponseItem(raw);\n"
            '      case "item.started":\n'
        )
        if anchor not in text:
            anchor = '      case "item.started":\n'
            insertion = (
                '      case "event_msg":\n'
                "        return this.translateEventMsg(raw);\n"
                '      case "response_item":\n'
                "        return this.translateResponseItem(raw);\n"
                '      case "item.started":\n'
            )
        if anchor not in text:
            raise SystemExit("bridge bundle anchor not found: Codex item.started switch case")
        text = text.replace(anchor, insertion, 1)

    if 'case "item.updated":' not in text:
        anchor = (
            '      case "item.completed":\n'
            "        return this.translateItemCompleted(raw);\n"
            '      case "agent_message":\n'
        )
        insertion = (
            '      case "item.completed":\n'
            "        return this.translateItemCompleted(raw);\n"
            '      case "item.updated":\n'
            "        return this.translateItemUpdated(raw);\n"
            '      case "agent_message":\n'
        )
        if anchor not in text:
            raise SystemExit("bridge bundle anchor not found: Codex item.completed switch case")
        text = text.replace(anchor, insertion, 1)

    if "updatedTextByItemId = /* @__PURE__ */ new Map();" not in text:
        anchor = "  startedItems = /* @__PURE__ */ new Set();\n"
        insertion = anchor + "  updatedTextByItemId = /* @__PURE__ */ new Map();\n"
        if anchor not in text:
            raise SystemExit("bridge bundle anchor not found: Codex startedItems field")
        text = text.replace(anchor, insertion, 1)

    if 'lastAgentMessageText = "";' not in text:
        anchor = "  updatedTextByItemId = /* @__PURE__ */ new Map();\n"
        if anchor not in text:
            anchor = "  startedItems = /* @__PURE__ */ new Set();\n"
        insertion = anchor + '  lastAgentMessageText = "";\n'
        if anchor not in text:
            raise SystemExit("bridge bundle anchor not found: Codex agent message state field")
        text = text.replace(anchor, insertion, 1)

    original_agent_message_completed = '''    if (item.type === "agent_message") {
      const message = stringValue(item.text ?? item.message);
      return message ? [{ type: "text", delta: message }] : [];
    }'''
    patched_agent_message_completed = '''    if (item.type === "agent_message") {
      const message = stringValue(item.text ?? item.message);
      if (!message) return [];
      const id = stringValue(item.id);
      if (id && this.updatedTextByItemId.has(id)) {
        const previous = this.updatedTextByItemId.get(id) ?? "";
        this.updatedTextByItemId.delete(id);
        return message.length > previous.length ? this.translateAgentDelta(message.slice(previous.length)) : [];
      }
      return this.translateAgentText(message);
    }'''
    legacy_agent_message_completed = '''    if (item.type === "agent_message") {
      const message = stringValue(item.text ?? item.message);
      if (!message) return [];
      const id = stringValue(item.id);
      if (id && this.updatedTextByItemId.has(id)) {
        const previous = this.updatedTextByItemId.get(id) ?? "";
        this.updatedTextByItemId.delete(id);
        return message.length > previous.length ? [{ type: "text", delta: message.slice(previous.length) }] : [];
      }
      return [{ type: "text", delta: message }];
    }'''
    if patched_agent_message_completed not in text:
        if legacy_agent_message_completed in text:
            text = text.replace(legacy_agent_message_completed, patched_agent_message_completed, 1)
        elif original_agent_message_completed in text:
            text = text.replace(original_agent_message_completed, patched_agent_message_completed, 1)
        else:
            raise SystemExit("bridge bundle anchor not found: Codex agent_message completion")

    if "  translateItemUpdated(raw) {" not in text:
        anchor = "  translateAgentMessage(raw) {\n"
        method = '''  translateItemUpdated(raw) {
    const item = recordValue(raw.item);
    if (!item) return [];
    if (item.type === "agent_message") {
      const id = stringValue(item.id);
      const delta = stringValue(item.delta ?? item.text_delta ?? raw.delta ?? raw.text_delta);
      if (delta) {
        if (id) this.updatedTextByItemId.set(id, (this.updatedTextByItemId.get(id) ?? "") + delta);
        return this.translateAgentDelta(delta);
      }
      const message = stringValue(item.text ?? item.message ?? raw.text ?? raw.message);
      if (!id || !message) return [];
      const previous = this.updatedTextByItemId.get(id) ?? "";
      if (message.length <= previous.length) return [];
      this.updatedTextByItemId.set(id, message);
      return this.translateAgentDelta(message.slice(previous.length));
    }
    if (item.type !== "command_execution") return [];
    const id = stringValue(item.id);
    if (!id) {
      this.drift.anomalies++;
      return [];
    }
    const output = stringValue(item.output ?? item.aggregated_output ?? item.stdout ?? raw.output ?? raw.aggregated_output ?? raw.stdout ?? item.delta ?? raw.delta);
    if (output === void 0) return [];
    const events = [];
    if (!this.startedItems.has(id)) {
      this.startedItems.add(id);
      events.push({
        type: "tool_use",
        id,
        name: "command_execution",
        input: {
          command: stringValue(item.command) ?? ""
        }
      });
    }
    events.push({ type: "tool_update", id, output });
    return events;
  }
'''
        if anchor not in text:
            raise SystemExit("bridge bundle anchor not found: Codex translateAgentMessage")
        text = text.replace(anchor, method + anchor, 1)
    else:
        text = text.replace(
            '        return [{ type: "text", delta }];',
            "        return this.translateAgentDelta(delta);",
            1,
        )
        text = text.replace(
            '      return [{ type: "text", delta: message.slice(previous.length) }];',
            "      return this.translateAgentDelta(message.slice(previous.length));",
            1,
        )

    original_translate_agent_message = '''  translateAgentMessage(raw) {
    const message = stringValue(raw.message ?? raw.text);
    if (!message) return [];
    return [{ type: "text", delta: message }];
  }'''
    patched_translate_agent_message = '''  translateAgentMessage(raw) {
    const message = stringValue(raw.message ?? raw.text);
    return this.translateAgentText(message);
  }'''
    if patched_translate_agent_message not in text:
        if original_translate_agent_message not in text:
            raise SystemExit("bridge bundle anchor not found: Codex translateAgentMessage body")
        text = text.replace(original_translate_agent_message, patched_translate_agent_message, 1)

    if "  translateAgentDelta(delta) {" not in text:
        anchor = "  translateAgentMessage(raw) {\n"
        helper = '''  translateAgentDelta(delta) {
    if (!delta) return [];
    this.lastAgentMessageText += delta;
    return [{ type: "text", delta }];
  }
  translateAgentText(message) {
    if (!message) return [];
    const previous = this.lastAgentMessageText;
    if (previous && message === previous) return [];
    if (previous && message.startsWith(previous)) {
      const delta = message.slice(previous.length);
      this.lastAgentMessageText = message;
      return delta ? [{ type: "text", delta }] : [];
    }
    this.lastAgentMessageText = message;
    return [{ type: "text", delta: message }];
  }
  translateEventMsg(raw) {
    const payload = recordValue(raw.payload);
    if (!payload || typeof payload.type !== "string") {
      this.drift.anomalies++;
      return [];
    }
    switch (payload.type) {
      case "task_started": {
        const threadId = stringValue(payload.turn_id ?? payload.turnId);
        if (!threadId) {
          this.drift.anomalies++;
          return [];
        }
        if (this.threadId) return [];
        this.threadId = threadId;
        return [{ type: "system", threadId }];
      }
      case "agent_message": {
        const message = stringValue(payload.message ?? payload.text);
        const events = this.translateAgentText(message);
        if (payload.phase === "final_answer") {
          this.terminal = true;
          events.push({
            type: "done",
            threadId: this.threadId ?? stringValue(payload.turn_id ?? payload.turnId),
            terminationReason: "normal"
          });
        }
        return events;
      }
      case "task_complete": {
        const events = [];
        const message = stringValue(payload.last_agent_message ?? payload.lastAgentMessage);
        events.push(...this.translateAgentText(message));
        this.terminal = true;
        events.push({
          type: "done",
          threadId: this.threadId ?? stringValue(payload.turn_id ?? payload.turnId),
          terminationReason: "normal"
        });
        return events;
      }
      case "token_count": {
        const info = recordValue(payload.info);
        const usage = recordValue(info?.total_token_usage ?? payload.total_token_usage ?? payload.usage);
        if (!usage) return [];
        return [{
          type: "usage",
          inputTokens: numberValue(usage.input_tokens ?? usage.inputTokens),
          outputTokens: numberValue(usage.output_tokens ?? usage.outputTokens),
          cachedInputTokens: numberValue(usage.cached_input_tokens ?? usage.cachedInputTokens),
          reasoningOutputTokens: numberValue(usage.reasoning_output_tokens ?? usage.reasoningOutputTokens)
        }];
      }
      default:
        return [];
    }
  }
  translateResponseItem(raw) {
    const payload = recordValue(raw.payload ?? raw.item);
    if (!payload || payload.type !== "message" || payload.role !== "assistant") return [];
    const content = Array.isArray(payload.content) ? payload.content : [];
    const message = content.map((part) => {
      const record = recordValue(part);
      if (!record) return "";
      if (record.type !== "output_text" && record.type !== "text") return "";
      return stringValue(record.text) ?? "";
    }).join("");
    const events = this.translateAgentText(message);
    if (payload.phase === "final_answer") {
      const metadata = recordValue(payload.internal_chat_message_metadata_passthrough);
      this.terminal = true;
      events.push({
        type: "done",
        threadId: this.threadId ?? stringValue(metadata?.turn_id ?? payload.turn_id ?? payload.turnId),
        terminationReason: "normal"
      });
    }
    return events;
  }
'''
        if anchor not in text:
            raise SystemExit("bridge bundle anchor not found: Codex translateAgentMessage")
        text = text.replace(anchor, helper + anchor, 1)

    legacy_event_msg_final_answer = '''      case "agent_message": {
        const message = stringValue(payload.message ?? payload.text);
        return this.translateAgentText(message);
      }'''
    patched_event_msg_final_answer = '''      case "agent_message": {
        const message = stringValue(payload.message ?? payload.text);
        const events = this.translateAgentText(message);
        if (payload.phase === "final_answer") {
          this.terminal = true;
          events.push({
            type: "done",
            threadId: this.threadId ?? stringValue(payload.turn_id ?? payload.turnId),
            terminationReason: "normal"
          });
        }
        return events;
      }'''
    if patched_event_msg_final_answer not in text:
        if legacy_event_msg_final_answer not in text:
            raise SystemExit("bridge bundle anchor not found: Codex event_msg agent_message body")
        text = text.replace(legacy_event_msg_final_answer, patched_event_msg_final_answer, 1)

    legacy_response_item_final_answer = '''  translateResponseItem(raw) {
    const payload = recordValue(raw.payload ?? raw.item);
    if (!payload || payload.type !== "message" || payload.role !== "assistant") return [];
    const content = Array.isArray(payload.content) ? payload.content : [];
    const message = content.map((part) => {
      const record = recordValue(part);
      if (!record) return "";
      if (record.type !== "output_text" && record.type !== "text") return "";
      return stringValue(record.text) ?? "";
    }).join("");
    return this.translateAgentText(message);
  }'''
    patched_response_item_final_answer = '''  translateResponseItem(raw) {
    const payload = recordValue(raw.payload ?? raw.item);
    if (!payload || payload.type !== "message" || payload.role !== "assistant") return [];
    const content = Array.isArray(payload.content) ? payload.content : [];
    const message = content.map((part) => {
      const record = recordValue(part);
      if (!record) return "";
      if (record.type !== "output_text" && record.type !== "text") return "";
      return stringValue(record.text) ?? "";
    }).join("");
    const events = this.translateAgentText(message);
    if (payload.phase === "final_answer") {
      const metadata = recordValue(payload.internal_chat_message_metadata_passthrough);
      this.terminal = true;
      events.push({
        type: "done",
        threadId: this.threadId ?? stringValue(metadata?.turn_id ?? payload.turn_id ?? payload.turnId),
        terminationReason: "normal"
      });
    }
    return events;
  }'''
    if patched_response_item_final_answer not in text:
        if legacy_response_item_final_answer not in text:
            raise SystemExit("bridge bundle anchor not found: Codex translateResponseItem body")
        text = text.replace(legacy_response_item_final_answer, patched_response_item_final_answer, 1)

    if 'case "tool_update":' not in text:
        anchor = '''    case "tool_result": {
      const blocks = state.blocks.map((b) => {'''
        insertion = '''    case "tool_update": {
      const blocks = state.blocks.map((b) => {
        if (b.kind !== "tool" || b.tool.id !== evt.id) return b;
        return {
          ...b,
          tool: {
            ...b.tool,
            output: evt.output
          }
        };
      });
      return { ...state, blocks };
    }
    case "tool_result": {
      const blocks = state.blocks.map((b) => {'''
        if anchor not in text:
            raise SystemExit("bridge bundle anchor not found: run-state tool_result reducer")
        text = text.replace(anchor, insertion, 1)

    return text


def patch_stream_resilience(text: str) -> str:
    """Avoid letting card/markdown update hangs block run completion."""
    handle_anchor = "    const handle = { run, interrupted: false };\n"
    handle_replacement = "    const handle = { run, interrupted: false, interruptNotifiers: new Set() };\n"
    if handle_anchor in text and handle_replacement not in text:
        text = text.replace(handle_anchor, handle_replacement, 1)

    interrupt_anchor = '''    h.interrupted = true;
    this.handles.delete(chatId);
    void h.run.stop().catch(() => {
    });
    return true;'''
    interrupt_replacement = '''    h.interrupted = true;
    this.handles.delete(chatId);
    for (const notify of h.interruptNotifiers || []) {
      try {
        notify();
      } catch (err) {
        log.warn("run", "interrupt-notifier-failed", { scope: chatId, err: err instanceof Error ? err.message : String(err) });
      }
    }
    void h.run.stop().catch(() => {
    });
    return true;'''
    if interrupt_anchor in text and interrupt_replacement not in text:
        text = text.replace(interrupt_anchor, interrupt_replacement, 1)

    start = text.find("async function processAgentStream(")
    end = text.find("async function awaitRenderAwareStream", start)
    if start >= 0 and end > start:
        segment = text[start:end]
        if "state = lablineStateWithRunStartedAt(initialState, runStart2);" not in segment:
            segment = segment.replace(
                "  let state = initialState;",
                "  let state = lablineStateWithRunStartedAt(initialState, runStart2);",
                1,
            )
        if "lablineFlushAgentState(flush, state, scope)" not in segment:
            segment = segment.replace(
                "await flush(state);",
                "await lablineFlushAgentState(flush, state, scope);",
            )
        text = text[:start] + segment + text[end:]

    terminal_grace_const_anchor = "var STREAM_TERMINAL_GRACE_MS = 3e3;"
    terminal_grace_const_replacement = "var STREAM_TERMINAL_GRACE_MS = lablineStreamTerminalGraceMs();"
    if terminal_grace_const_anchor in text and terminal_grace_const_replacement not in text:
        text = text.replace(terminal_grace_const_anchor, terminal_grace_const_replacement, 1)

    post_done_grace_anchor = "var DEFAULT_POST_DONE_EXIT_GRACE_MS = 2e3;"
    post_done_grace_replacement = "var DEFAULT_POST_DONE_EXIT_GRACE_MS = lablinePostDoneExitGraceMs();"
    if post_done_grace_anchor in text and post_done_grace_replacement not in text:
        text = text.replace(post_done_grace_anchor, post_done_grace_replacement, 1)

    terminal_grace_anchor = '''    void streamResult.then((result) => {
      if (!result.ok) {
        log.fail("stream", result.err, { mode: input.mode, step: "stream-terminal-late" });
      }
    });
    return;'''
    terminal_grace_replacement = '''    void streamResult.then((result) => {
      if (!result.ok) {
        log.fail("stream", result.err, { mode: input.mode, step: "stream-terminal-late" });
      }
    });
    if (input.mode !== "markdown" || lablineMarkdownTerminalFallbackEnabled()) {
      await runFallbackReply(input.mode, first.state, input.fallback);
    }
    return;'''
    if terminal_grace_anchor in text and terminal_grace_replacement not in text:
        text = text.replace(terminal_grace_anchor, terminal_grace_replacement, 1)
    legacy_terminal_grace_replacement = '''    void streamResult.then((result) => {
      if (!result.ok) {
        log.fail("stream", result.err, { mode: input.mode, step: "stream-terminal-late" });
      }
    });
    await runFallbackReply(input.mode, first.state, input.fallback);
    return;'''
    if legacy_terminal_grace_replacement in text and terminal_grace_replacement not in text:
        text = text.replace(legacy_terminal_grace_replacement, terminal_grace_replacement, 1)

    stream_error_anchor = '''      log.fail("stream", first.err, { mode: input.mode, step: "stream" });
      const rendered = await renderResult;
      if (!rendered.ok) throw rendered.err;
      await runFallbackReply(input.mode, rendered.state, input.fallback);
      return;'''
    stream_error_replacement = '''      log.fail("stream", first.err, { mode: input.mode, step: "stream" });
      const latest = typeof input.latestState === "function" ? input.latestState() : void 0;
      if (latest) {
        if (input.mode === "markdown" && !lablineMarkdownTerminalFallbackEnabled()) {
          void renderResult.then((result) => {
            if (!result.ok) {
              log.fail("stream", result.err, { mode: input.mode, step: "render-after-stream-failed" });
            }
          });
          return;
        }
        await runFallbackReply(input.mode, latest, input.fallback);
        void renderResult.then((result) => {
          if (!result.ok) {
            log.fail("stream", result.err, { mode: input.mode, step: "render-after-stream-failed" });
          }
        });
        return;
      }
      const rendered = await renderResult;
      if (!rendered.ok) throw rendered.err;
      await runFallbackReply(input.mode, rendered.state, input.fallback);
      return;'''
    if stream_error_anchor in text and stream_error_replacement not in text:
        text = text.replace(stream_error_anchor, stream_error_replacement, 1)
    legacy_stream_error_replacement = '''      log.fail("stream", first.err, { mode: input.mode, step: "stream" });
      const latest = typeof input.latestState === "function" ? input.latestState() : void 0;
      if (latest) {
        await runFallbackReply(input.mode, latest, input.fallback);
        void renderResult.then((result) => {
          if (!result.ok) {
            log.fail("stream", result.err, { mode: input.mode, step: "render-after-stream-failed" });
          }
        });
        return;
      }
      const rendered = await renderResult;
      if (!rendered.ok) throw rendered.err;
      await runFallbackReply(input.mode, rendered.state, input.fallback);
      return;'''
    if legacy_stream_error_replacement in text and stream_error_replacement not in text:
        text = text.replace(legacy_stream_error_replacement, stream_error_replacement, 1)

    footer_status_anchor = r'''function footerStatus(status) {
  const text = status === "thinking" ? "\u{1F9E0} \u6B63\u5728\u601D\u8003" : status === "tool_running" ? "\u{1F9F0} \u6B63\u5728\u8C03\u7528\u5DE5\u5177" : "\u270D\uFE0F \u6B63\u5728\u8F93\u51FA";
  return noteMd(text);
}'''
    footer_status_replacement = r'''function footerStatus(status, state) {
  const text = status === "thinking" ? "\u{1F9E0} \u6B63\u5728\u601D\u8003" : status === "tool_running" ? "\u{1F9F0} \u6B63\u5728\u8C03\u7528\u5DE5\u5177" : "\u270D\uFE0F \u6B63\u5728\u8F93\u51FA";
  return noteMd(`${text}${lablineRunningElapsedText(state)}`);
}'''
    if footer_status_anchor in text and footer_status_replacement not in text:
        text = text.replace(footer_status_anchor, footer_status_replacement, 1)
        text = text.replace("if (state.footer) elements.push(footerStatus(state.footer));", "if (state.footer) elements.push(footerStatus(state.footer, state));", 1)

    summary_anchor = r'''  if (state.footer === "tool_running") return "\u6B63\u5728\u8C03\u7528\u5DE5\u5177";
  if (state.footer === "streaming") return "\u6B63\u5728\u8F93\u51FA";
  return "\u601D\u8003\u4E2D";'''
    summary_replacement = '''  const elapsed = lablineRunningElapsedText(state);
  if (state.footer === "tool_running") return `正在调用工具${elapsed}`;
  if (state.footer === "streaming") return `正在输出${elapsed}`;
  return `思考中${elapsed}`;'''
    if summary_anchor in text and summary_replacement not in text:
        text = text.replace(summary_anchor, summary_replacement, 1)

    footer_line_anchor = r'''function footerLine(status) {
  if (status === "thinking") return "_\u{1F9E0} \u6B63\u5728\u601D\u8003\u2026_";
  if (status === "tool_running") return "_\u{1F9F0} \u6B63\u5728\u8C03\u7528\u5DE5\u5177\u2026_";
  return "_\u270D\uFE0F \u6B63\u5728\u8F93\u51FA\u2026_";
}'''
    footer_line_replacement = r'''function footerLine(status, state) {
  const elapsed = lablineRunningElapsedText(state);
  if (status === "thinking") return `_\u{1F9E0} \u6B63\u5728\u601D\u8003${elapsed}\u2026_`;
  if (status === "tool_running") return `_\u{1F9F0} \u6B63\u5728\u8C03\u7528\u5DE5\u5177${elapsed}\u2026_`;
  return `_\u270D\uFE0F \u6B63\u5728\u8F93\u51FA${elapsed}\u2026_`;
}'''
    if footer_line_anchor in text and footer_line_replacement not in text:
        text = text.replace(footer_line_anchor, footer_line_replacement, 1)
        text = text.replace("parts.push(footerLine(state.footer));", "parts.push(footerLine(state.footer, state));", 1)

    markdown_flush_anchor = '''        async (state) => {
          latestState = state;
          if (markdownCtrl) {
            await markdownCtrl.setContent(renderText(filterForPrefs(state)));
          }
        }'''
    markdown_flush_replacement = '''        async (state) => {
          latestState = state;
          if (markdownCtrl) {
            await lablineSetMarkdownContentWithTimeout(
              markdownCtrl,
              renderText(filterForPrefs(state)),
              scope,
              state.terminal !== "running" ? "terminal" : "update",
              state.terminal !== "running"
            );
          }
        }'''
    if markdown_flush_anchor in text and markdown_flush_replacement not in text:
        text = text.replace(markdown_flush_anchor, markdown_flush_replacement, 1)

    if "let markdownMessageId;" not in text:
        for markdown_ctrl_decl_anchor in (
            '''      let producerStarted = false;
      let markdownCtrl;''',
            '''    let producerStarted = false;
    let markdownCtrl;''',
        ):
            indent = markdown_ctrl_decl_anchor.split("let markdownCtrl;")[0].split("\n")[-1]
            markdown_ctrl_decl_replacement = f'''{markdown_ctrl_decl_anchor}
{indent}let markdownMessageId;'''
            if markdown_ctrl_decl_anchor in text:
                text = text.replace(markdown_ctrl_decl_anchor, markdown_ctrl_decl_replacement, 1)
                break

    markdown_producer_anchor = '''            await ctrl.setContent(renderText(filterForPrefs(latestState)));
            await renderDone;'''
    markdown_producer_replacement = '''            await lablineSetMarkdownContentWithTimeout(
              ctrl,
              renderText(filterForPrefs(latestState)),
              scope,
              "initial",
              latestState.terminal !== "running"
            );
            await renderDone;'''
    if markdown_producer_anchor in text and markdown_producer_replacement not in text:
        text = text.replace(markdown_producer_anchor, markdown_producer_replacement, 1)

    if "markdownMessageId = ctrl.messageId;" not in text:
        for markdown_producer_message_anchor in (
            '''            producerStarted = true;
            markdownCtrl = ctrl;
            await lablineSetMarkdownContentWithTimeout(''',
            '''          producerStarted = true;
          markdownCtrl = ctrl;
            await lablineSetMarkdownContentWithTimeout(''',
        ):
            indent = markdown_producer_message_anchor.split("producerStarted = true;")[0]
            markdown_producer_message_replacement = markdown_producer_message_anchor.replace(
                "            await lablineSetMarkdownContentWithTimeout(",
                f'''{indent}markdownMessageId = ctrl.messageId;
{indent}log.info("stream", "markdown-started", {{ scope, messageId: markdownMessageId }});
{indent}await lablineSetMarkdownContentWithTimeout(''',
            )
            if markdown_producer_message_anchor in text:
                text = text.replace(markdown_producer_message_anchor, markdown_producer_message_replacement, 1)
                break

    markdown_stream_anchor = '''      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        fallback: async (state) => {
          const body = renderText(filterForPrefs(state));
          if (body.trim()) {
            await channel.send(chatId, { markdown: body }, sendOpts);
          }
        }
      });'''
    markdown_stream_replacement = '''      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        latestState: () => latestState,
        fallback: async () => {
        }
      });
      await lablineSendMarkdownTerminalFallback({
        channel,
        chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState),
        messageId: markdownMessageId,
        label: "run-terminal"
      });'''
    if markdown_stream_anchor in text and markdown_stream_replacement not in text:
        text = text.replace(markdown_stream_anchor, markdown_stream_replacement, 1)
    legacy_markdown_stream_replacement = '''      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        latestState: () => latestState,
        fallback: async (state) => {
          const body = renderText(filterForPrefs(state));
          if (body.trim()) {
            await channel.send(chatId, { markdown: body }, sendOpts);
          }
        }
      });
      await lablineSendMarkdownTerminalFallback({
        channel,
        chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState),
        messageId: markdownMessageId,
        label: "run-terminal"
      });'''
    if legacy_markdown_stream_replacement in text and markdown_stream_replacement not in text:
        text = text.replace(legacy_markdown_stream_replacement, markdown_stream_replacement, 1)

    legacy_markdown_terminal_fallback_without_message = '''      await lablineSendMarkdownTerminalFallback({
        channel,
        chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState)
      });'''
    current_markdown_terminal_fallback = '''      await lablineSendMarkdownTerminalFallback({
        channel,
        chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState),
        messageId: markdownMessageId,
        label: "run-terminal"
      });'''
    if legacy_markdown_terminal_fallback_without_message in text:
        text = text.replace(
            legacy_markdown_terminal_fallback_without_message,
            current_markdown_terminal_fallback,
        )

    legacy_markdown_ctx_terminal_fallback_without_message = '''      await lablineSendMarkdownTerminalFallback({
        channel: ctx.channel,
        chatId: ctx.msg.chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState)
      });'''
    current_markdown_ctx_terminal_fallback = '''      await lablineSendMarkdownTerminalFallback({
        channel: ctx.channel,
        chatId: ctx.msg.chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState),
        messageId: markdownMessageId,
        label: "run-terminal"
      });'''
    if legacy_markdown_ctx_terminal_fallback_without_message in text:
        text = text.replace(
            legacy_markdown_ctx_terminal_fallback_without_message,
            current_markdown_ctx_terminal_fallback,
        )

    legacy_markdown_ctx_fallback = '''        fallback: async (state) => {
          const body = renderText(filterForPrefs(state));
          if (body.trim()) {
            await ctx.channel.send(ctx.msg.chatId, { markdown: body }, sendOpts);
          }
        }'''
    markdown_empty_fallback = '''        fallback: async () => {
        }'''
    if legacy_markdown_ctx_fallback in text:
        text = text.replace(legacy_markdown_ctx_fallback, markdown_empty_fallback)

    legacy_markdown_channel_fallback = '''        fallback: async (state) => {
          const body = renderText(filterForPrefs(state));
          if (body.trim()) {
            await channel.send(chatId, { markdown: body }, sendOpts);
          }
        }'''
    if legacy_markdown_channel_fallback in text:
        text = text.replace(legacy_markdown_channel_fallback, markdown_empty_fallback)

    final_reply_anchor = '''        await input.channel.stream(
          input.chatId,
          {
            markdown: async (ctrl) => {
              await ctrl.setContent(body);
            }
          },
          input.sendOpts
        );'''
    final_reply_replacement = '''        await input.channel.stream(
          input.chatId,
          {
            markdown: async (ctrl) => {
              await lablineSetMarkdownContentWithTimeout(
                ctrl,
                body,
                input.scope,
                "final-reply",
                true
              );
            }
          },
          input.sendOpts
        );'''
    if final_reply_anchor in text and final_reply_replacement not in text:
        text = text.replace(final_reply_anchor, final_reply_replacement, 1)
    return text


def patch_card_continuation(text: str) -> str:
    """Let ordinary card runs move updates to a fresh card when the old one stalls."""
    setup_anchor = '''    if (replyMode === "card") {
      let latestState = initialState;
      let producerStarted = false;
      let cardCtrl;
      const renderDone = processAgentStream('''
    if "const cardStream = lablineCreateCardContinuationStream({" in text or setup_anchor in text:
        text = text.replace("initial: renderCard(initialState, cardRenderOptions),", "initial: cardStream.initial(),")
        text = text.replace("initial: renderCard(initialState),", "initial: cardStream.initial(),")

    if "const cardStream = lablineCreateCardContinuationStream({" in text:
        existing_interrupt_anchor = '''      const streamDone = channel.stream('''
        existing_interrupt_replacement = '''      const unregisterInterruptNotifier = lablineRegisterInterruptNotifier(handle, async () => {
        latestState = markInterrupted(latestState);
        await cardStream.fallback(latestState);
      });
      const streamDone = channel.stream('''
        if existing_interrupt_anchor in text and existing_interrupt_replacement not in text and "const unregisterInterruptNotifier = lablineRegisterInterruptNotifier(handle" not in text:
            text = text.replace(existing_interrupt_anchor, existing_interrupt_replacement, 1)

        existing_close_anchor = '''      cardStream.close();'''
        existing_close_replacement = '''      unregisterInterruptNotifier?.();
      cardStream.close();'''
        if "unregisterInterruptNotifier?.();" not in text and existing_close_anchor in text:
            text = text.replace(existing_close_anchor, existing_close_replacement, 1)

        existing_anchor = '''      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        fallback: async (state) => {
          await cardStream.fallback(state);
        }
      });'''
        existing_replacement = '''      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        latestState: () => latestState,
        fallback: async (state) => {
          await cardStream.fallback(state);
        }
      });'''
        if existing_anchor in text and existing_replacement not in text:
            text = text.replace(existing_anchor, existing_replacement, 1)
        return text

    setup_replacement = '''    if (replyMode === "card") {
      let latestState = initialState;
      let producerStarted = false;
      const cardStream = lablineCreateCardContinuationStream({
        channel,
        chatId,
        sendOpts,
        scope,
        render: (state) => renderCard(filterForPrefs(state), cardRenderOptions)
      });
      const renderDone = processAgentStream('''
    if setup_anchor not in text:
        return text
    text = text.replace(setup_anchor, setup_replacement, 1)

    flush_anchor = '''        async (state) => {
          latestState = state;
          if (cardCtrl) {
            await cardCtrl.update(renderCard(filterForPrefs(state), cardRenderOptions));
          }
        }'''
    flush_replacement = '''        async (state) => {
          latestState = state;
          await cardStream.update(state);
        }'''
    if flush_anchor not in text:
        raise SystemExit("bridge bundle anchor not found: ordinary card flush callback")
    text = text.replace(flush_anchor, flush_replacement, 1)

    stop_anchor = '''      const streamDone = channel.stream('''
    stop_replacement = '''      const unregisterInterruptNotifier = lablineRegisterInterruptNotifier(handle, async () => {
        latestState = markInterrupted(latestState);
        await cardStream.fallback(latestState);
      });
      const streamDone = channel.stream('''
    if stop_anchor not in text:
        raise SystemExit("bridge bundle anchor not found: ordinary card stream start")
    text = text.replace(stop_anchor, stop_replacement, 1)

    producer_anchor = '''            producer: async (ctrl) => {
              producerStarted = true;
              cardCtrl = ctrl;
              await ctrl.update(renderCard(filterForPrefs(latestState), cardRenderOptions));
              await renderDone;
            }'''
    producer_replacement = '''            producer: async (ctrl) => {
              producerStarted = true;
              cardStream.setPrimary(ctrl);
              await cardStream.update(latestState);
              try {
                await renderDone;
              } finally {
                unregisterInterruptNotifier?.();
                cardStream.close();
              }
            }'''
    if producer_anchor not in text:
        raise SystemExit("bridge bundle anchor not found: ordinary card producer")
    text = text.replace(producer_anchor, producer_replacement, 1)

    fallback_anchor = '''      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        fallback: async (state) => {
          await channel.send(
            chatId,
            { card: renderCard(filterForPrefs(state), cardRenderOptions) },
            sendOpts
          );
        }
      });'''
    fallback_replacement = '''      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        latestState: () => latestState,
        fallback: async (state) => {
          await cardStream.fallback(state);
        }
      });
      unregisterInterruptNotifier?.();
      cardStream.close();'''
    if fallback_anchor not in text:
        raise SystemExit("bridge bundle anchor not found: ordinary card fallback")
    return text.replace(fallback_anchor, fallback_replacement, 1)


def patch_post_done_exit_grace(text: str) -> str:
    """Give agent subprocesses enough time to exit after emitting done."""
    duplicate_helper = '''function lablinePostDoneExitGraceMs() {
  const parsed = Number.parseInt(process.env.LABLINE_POST_DONE_EXIT_GRACE_MS || "30000", 10);
  return Number.isFinite(parsed) && parsed >= 2000 ? parsed : 30000;
}
'''
    if duplicate_helper in text:
        text = text.replace(duplicate_helper, "", 1)
    legacy = "var DEFAULT_POST_DONE_EXIT_GRACE_MS = 2e3;"
    patched = "var DEFAULT_POST_DONE_EXIT_GRACE_MS = lablinePostDoneExitGraceMs();"
    if patched in text:
        return text
    if legacy in text:
        return text.replace(legacy, patched, 1)
    return text


def patch_default_run_idle_timeout(text: str) -> str:
    """Default Codex no-output watchdog for profiles that have not configured one."""
    legacy = '''function getRunIdleTimeoutMs(cfg) {
  const raw = cfg.preferences?.runIdleTimeoutMinutes;
  if (typeof raw !== "number" || !Number.isFinite(raw) || raw <= 0) return void 0;
  const clamped = Math.min(Math.max(Math.floor(raw), 1), 120);
  return clamped * 6e4;
}'''
    patched = '''function getRunIdleTimeoutMs(cfg) {
  const raw = cfg.preferences?.runIdleTimeoutMinutes;
  if (typeof raw !== "number" || !Number.isFinite(raw)) {
    const defaultMinutes = lablineDefaultRunIdleTimeoutMinutes();
    return defaultMinutes > 0 ? defaultMinutes * 6e4 : void 0;
  }
  if (raw <= 0) return void 0;
  const clamped = Math.min(Math.max(Math.floor(raw), 1), 120);
  return clamped * 6e4;
}'''
    if patched in text:
        return text
    if legacy in text:
        return text.replace(legacy, patched, 1)
    return text


def patch_agent_proxy_env(text: str) -> str:
    """Allow the bridge to run no-proxy while Codex child processes use a proxy."""
    patched = (
        "    const envOverrides = buildLarkChannelEnv(this.larkChannel);\n"
        "    Object.assign(envOverrides, lablineAgentProxyEnvOverrides());\n"
    )
    if patched in text:
        return text
    legacy = "    const envOverrides = buildLarkChannelEnv(this.larkChannel);\n"
    if legacy not in text:
        return text
    return text.replace(legacy, patched, 1)


def patch_text(text: str, framework: Path) -> str:
    text = strip_existing_shim(text)
    text = patch_codex_item_updated(text)
    text = patch_card_continuation(text)
    text = patch_stream_resilience(text)
    text = patch_post_done_exit_grace(text)
    text = patch_default_run_idle_timeout(text)
    text = patch_agent_proxy_env(text)
    text = patch_stop_handler(text)
    legacy_wakeup_loop = "  const lablineAutoWakeupLoop = lablineStartAutoWakeupLoop({ controls });\n"
    current_wakeup_loop = "  const lablineAutoWakeupLoop = lablineStartAutoWakeupLoop({ channel, controls });\n"
    text = text.replace(legacy_wakeup_loop, current_wakeup_loop)
    while text.count(current_wakeup_loop) > 1:
        first = text.find(current_wakeup_loop)
        second = text.find(current_wakeup_loop, first + len(current_wakeup_loop))
        text = text[:second] + text[second + len(current_wakeup_loop):]
    text = insert_once(
        text,
        '  "/status": handleStatus,\n',
        '  "/follow": handleLablineFollow,\n  "/unfollow": handleLablineUnfollow,\n  "/btw": handleLablineBtw,\n',
        '"/btw": handleLablineBtw',
    )
    text = insert_once(
        text,
        '  "/status": handleStatus,\n',
        '  "/fork": handleLablineFork,\n',
        '"/fork":',
    )
    text = insert_once(
        text,
        '  "/fork": handleLablineFork,\n',
        '  "/rename": handleLablineRename,\n',
        '"/rename":',
    )
    text = insert_after_any_anchor(
        text,
        [
            '        "- `/status` — 当前状态",\n',
            '        "- `/status` \\u2014 \\u5F53\\u524D\\u72B6\\u6001",\n',
        ],
        '        "- `/follow [task_id]` — 关注当前项目或指定任务的运行状态",\n'
        '        "- `/unfollow [subscription_id|task_id]` — 取消关注",\n'
        '        "- `/btw <问题>` — 记录只读旁路问题，不打断当前任务",\n',
        "`/btw <问题>`",
    )
    text = insert_after_any_anchor(
        text,
        [
            '        "- `/status` — 当前状态",\n',
            '        "- `/status` \\u2014 \\u5F53\\u524D\\u72B6\\u6001",\n',
        ],
        '        "- `/fork [名称]` — fork 当前 Codex thread，并可选重命名",\n',
        "`/fork [名称]`",
    )
    text = insert_after_any_anchor(
        text,
        [
            '        "- `/fork [名称]` — fork 当前 Codex thread，并可选重命名",\n',
        ],
        '        "- `/rename <名称>` — 重命名当前 Codex thread",\n',
        "`/rename <名称>`",
    )
    text = insert_once(
        text,
        "  const knownChatsRefresh = startKnownChatsRefreshTimer(channel, controls);\n",
        "  const lablineProjectionLoop = lablineStartProjectionLoop({ channel, controls });\n",
        "lablineStartProjectionLoop({ channel, controls })",
    )
    text = insert_once(
        text,
        "  const lablineProjectionLoop = lablineStartProjectionLoop({ channel, controls });\n",
        "  const lablineAutoWakeupLoop = lablineStartAutoWakeupLoop({ channel, controls });\n",
        "lablineStartAutoWakeupLoop({ channel, controls })",
    )
    text = insert_once(
        text,
        "      knownChatsRefresh.stop();\n",
        "      lablineProjectionLoop.stop();\n",
        "lablineProjectionLoop.stop();",
    )
    text = insert_once(
        text,
        "      lablineProjectionLoop.stop();\n",
        "      lablineAutoWakeupLoop.stop();\n",
        "lablineAutoWakeupLoop.stop();",
    )
    shim = SHIM.replace("__LABLINE_FRAMEWORK__", str(framework).replace("\\", "\\\\"))
    anchor = "async function handleNew(args, ctx) {"
    if anchor not in text:
        raise SystemExit(f"bridge bundle anchor not found: {anchor!r}")
    return text.replace(anchor, shim.strip() + "\n" + anchor, 1)


CHANNEL_FETCH_BOT_IDENTITY_ORIGINAL = '''\tasync fetchBotIdentity() {
\t\tlet lastError;
\t\ttry {
\t\t\tconst r = await this.rawClient.request({
\t\t\t\turl: "/open-apis/bot/v3/info",
\t\t\t\tmethod: "GET"
\t\t\t});
\t\t\tconst bot = r.bot;
\t\t\tif (bot?.open_id) return {
\t\t\t\topenId: bot.open_id,
\t\t\t\tname: bot.app_name ?? "bot"
\t\t\t};
\t\t\tlastError = /* @__PURE__ */ new Error(`bot/v3/info response missing open_id: ${JSON.stringify(r).slice(0, 200)}`);
\t\t} catch (e) {
\t\t\tlastError = e;
\t\t}
\t\tconst classified = classifyError(lastError);
\t\tthrow new LarkChannelError(classified.code === "unknown" ? "not_connected" : classified.code, "could not resolve bot identity via /open-apis/bot/v3/info — required for channel to function", { cause: lastError });
\t}'''


CHANNEL_FETCH_BOT_IDENTITY_PATCHED = '''\tasync fetchBotIdentity() {
\t\tlet lastError;
\t\ttry {
\t\t\tconst r = await this.rawClient.request({
\t\t\t\turl: "/open-apis/bot/v3/info",
\t\t\t\tmethod: "GET"
\t\t\t});
\t\t\tconst bot = r.bot ?? r.data?.bot ?? r.data ?? r;
\t\t\tconst openId = bot?.open_id ?? bot?.openId;
\t\t\tif (openId) return {
\t\t\t\topenId,
\t\t\t\tname: bot.app_name ?? bot.appName ?? "bot"
\t\t\t};
\t\t\tlastError = /* @__PURE__ */ new Error(`bot/v3/info response missing open_id: ${JSON.stringify(r).slice(0, 200)}`);
\t\t} catch (e) {
\t\t\tlastError = e;
\t\t}
\t\tconst allowEmptyBotId = /^(1|true|yes)$/i.test(process.env.LARK_CHANNEL_ALLOW_EMPTY_BOT_ID ?? "");
\t\tif (allowEmptyBotId) {
\t\t\tthis.logger.warn?.("channel: bot identity unresolved; continuing with empty bot open_id because LARK_CHANNEL_ALLOW_EMPTY_BOT_ID is set", lastError);
\t\t\treturn { openId: "", name: "bot" };
\t\t}
\t\tconst classified = classifyError(lastError);
\t\tthrow new LarkChannelError(classified.code === "unknown" ? "not_connected" : classified.code, "could not resolve bot identity via /open-apis/bot/v3/info — required for channel to function", { cause: lastError });
\t}'''


def patch_channel_text(text: str) -> str:
    if CHANNEL_EMPTY_BOT_ID_ENV in text:
        return text
    if CHANNEL_FETCH_BOT_IDENTITY_ORIGINAL not in text:
        raise SystemExit("channel bundle anchor not found: fetchBotIdentity")
    return text.replace(CHANNEL_FETCH_BOT_IDENTITY_ORIGINAL, CHANNEL_FETCH_BOT_IDENTITY_PATCHED, 1)


def bridge_package_root_from_cli(path: Path) -> Path | None:
    resolved = path.expanduser().resolve()
    if resolved.name == "cli.js" and resolved.parent.name == "dist":
        return resolved.parent.parent
    if resolved.name == "lark-channel-bridge.mjs":
        package_root = resolved.parent.parent
        if (package_root / "dist" / "cli.js").exists():
            return package_root
    if resolved.is_dir() and (resolved / "dist" / "cli.js").exists():
        return resolved
    return None


def channel_bundle_paths(bridge_cli: Path) -> list[Path]:
    package_root = bridge_package_root_from_cli(bridge_cli)
    if package_root is None:
        return []
    channel_dist = package_root / "node_modules" / "@larksuite" / "channel" / "dist"
    candidates = [channel_dist / "index.mjs", channel_dist / "index.cjs"]
    return [path for path in candidates if path.exists()]


def backup_path(path: Path, backup_dir: Path | None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = backup_dir or path.parent / ".labline-backups"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{path.name}.{stamp}.bak"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-cli", help="Path to dist/cli.js, package dir, or lark-channel-bridge.mjs")
    parser.add_argument("--framework", type=Path, default=Path("/data/Labline/framework"))
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = resolve_bridge_cli(args.bridge_cli)
    if not target.exists():
        raise SystemExit(f"bridge CLI bundle not found: {target}")
    before = target.read_text(encoding="utf-8")
    after = patch_text(before, args.framework.expanduser().resolve())
    channel_updates: list[tuple[Path, str, str, bool]] = []
    for channel_path in channel_bundle_paths(target):
        channel_before = channel_path.read_text(encoding="utf-8")
        channel_after = patch_channel_text(channel_before)
        channel_updates.append((channel_path, channel_before, channel_after, channel_before != channel_after))
    changed = before != after or any(item[3] for item in channel_updates)
    print(f"bridge_cli: {target}")
    print(f"framework: {args.framework.expanduser().resolve()}")
    if channel_updates:
        print("channel_bundles:")
        for channel_path, _channel_before, _channel_after, channel_changed in channel_updates:
            print(f"  - {channel_path}: changed={str(channel_changed).lower()}")
    else:
        print("channel_bundles: none")
    print(f"changed: {str(changed).lower()}")
    if not args.apply:
        print("mode: dry-run")
        return 0
    if changed:
        if before != after:
            backup = backup_path(target, args.backup_dir)
            shutil.copy2(target, backup)
            target.write_text(after, encoding="utf-8")
            print(f"backup: {backup}")
        for channel_path, channel_before, channel_after, channel_changed in channel_updates:
            if not channel_changed:
                continue
            backup = backup_path(channel_path, args.backup_dir)
            shutil.copy2(channel_path, backup)
            channel_path.write_text(channel_after, encoding="utf-8")
            print(f"backup: {backup}")
    print("mode: applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
