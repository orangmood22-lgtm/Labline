#!/usr/bin/env python3
"""Tests for the Labline lark-channel-bridge bundle patcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PATCHER = REPO_ROOT / "tools" / "patch_lark_channel_bridge_labline.py"


def load_patcher():
    spec = importlib.util.spec_from_file_location("patch_lark_channel_bridge_labline", PATCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_bridge_bundle() -> str:
    return '''// fixture
function helpCard(agentName = "Agent") {
  return shell("help", [
    divMd(
      [
        "**命令列表**",
        "- `/status` — 当前状态",
        "- `/help` — 本帮助"
      ].join("\\n")
    )
  ]);
}
var handlers = {
  "/status": handleStatus,
  "/help": handleHelp
};
function effectiveWorkspaceCwd(ctx) {
  return ctx.workspaces.cwdFor(ctx.scope) ?? ctx.controls.profileConfig.workspaces.default;
}
function escapeMd(s) { return s; }
function escapeCode(s) { return s; }
async function reply(ctx, markdown2) {}
async function handleStop(args, ctx) {
  const targetScope = args.trim();
  const scope = targetScope || ctx.scope;
  const ok = ctx.activeRuns.interrupt(scope);
  log.info("command", "stop", {
    scope,
    targeted: Boolean(targetScope),
    interrupted: ok
  });
}
async function handleNew(args, ctx) {}
async function runBridge() {
  await channel.connect();
  const knownChatsRefresh = startKnownChatsRefreshTimer(channel, controls);
  return {
    disconnect: async () => {
      knownChatsRefresh.stop();
      keepalive.stop();
    }
  };
}
'''


def minimal_channel_bundle() -> str:
    return '''// fixture
class Channel {
\tasync fetchBotIdentity() {
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
\t}
}
'''


def minimal_codex_translator_bundle() -> str:
    return '''// fixture
var CodexJsonlTranslator = class {
  threadId;
  terminal = false;
  lastNonTerminalError;
  startedItems = /* @__PURE__ */ new Set();
  drift = {
    unknownEvents: 0,
    anomalies: 0
  };
  translate(raw) {
    switch (raw.type) {
      case "item.started":
        return this.translateItemStarted(raw);
      case "item.completed":
        return this.translateItemCompleted(raw);
      case "agent_message":
        return this.translateAgentMessage(raw);
      default:
        return [];
    }
  }
  translateItemStarted(raw) {
    return [];
  }
  translateItemCompleted(raw) {
    const item = recordValue(raw.item);
    if (!item) return [];
    if (item.type === "agent_message") {
      const message = stringValue(item.text ?? item.message);
      return message ? [{ type: "text", delta: message }] : [];
    }
    if (item.type !== "command_execution") return [];
    return [];
  }
  translateAgentMessage(raw) {
    const message = stringValue(raw.message ?? raw.text);
    if (!message) return [];
    return [{ type: "text", delta: message }];
  }
};
function reduce(state, evt) {
  switch (evt.type) {
    case "text": {
      return state;
    }
    case "tool_result": {
      const blocks = state.blocks.map((b) => {
        if (b.kind !== "tool" || b.tool.id !== evt.id) return b;
        return b;
      });
      return { ...state, blocks };
    }
    default:
      return state;
  }
}
function recordValue(value) {
  return typeof value === "object" && value !== null ? value : void 0;
}
function stringValue(value) {
  return typeof value === "string" ? value : void 0;
}
'''


def minimal_run_stream_bundle() -> str:
    return '''// fixture
async function processAgentStream(handle, events, scope, idleTimeoutMs, recordSession, flush) {
  let state = initialState;
  try {
    for await (const evt of events) {
      state = reduce(state, evt);
      await flush(state);
      if (state.terminal !== "running") break;
    }
  } finally {
  }
  if (state.terminal === "running") {
    state = finalizeIfRunning(state);
  }
  await flush(state);
  return state;
}
async function awaitRenderAwareStream(input) {
  const streamResult = input.streamDone.then(
    () => ({ kind: "stream", ok: true }),
    (err) => ({ kind: "stream", ok: false, err })
  );
  const renderResult = input.renderDone.then(
    (state) => ({ kind: "render", ok: true, state }),
    (err) => ({ kind: "render", ok: false, err })
  );
  const first = await Promise.race([streamResult, renderResult]);
  if (!first.ok) {
    if (first.kind === "stream") {
      log.fail("stream", first.err, { mode: input.mode, step: "stream" });
      const rendered = await renderResult;
      if (!rendered.ok) throw rendered.err;
      await runFallbackReply(input.mode, rendered.state, input.fallback);
      return;
    }
    throw first.err;
  }
  if (first.kind === "stream") return;
  const terminal = await Promise.race([
    streamResult,
    delay(STREAM_TERMINAL_GRACE_MS).then(() => void 0)
  ]);
  if (!terminal) {
    log.warn("stream", "terminal-grace-expired", {
      mode: input.mode,
      graceMs: STREAM_TERMINAL_GRACE_MS
    });
    void streamResult.then((result) => {
      if (!result.ok) {
        log.fail("stream", result.err, { mode: input.mode, step: "stream-terminal-late" });
      }
    });
    return;
  }
}
'''


def minimal_run_card_bundle() -> str:
    return '''// fixture
async function consumeRun() {
  try {
    if (replyMode === "card") {
      let latestState = initialState;
      let producerStarted = false;
      let cardCtrl;
      const renderDone = processAgentStream(
        handle,
        eventStream,
        scope,
        idleTimeoutMs,
        recordSession,
        async (state) => {
          latestState = state;
          if (cardCtrl) {
            await cardCtrl.update(renderCard(filterForPrefs(state), cardRenderOptions));
          }
        }
      );
      const streamDone = channel.stream(
        chatId,
        {
          card: {
            initial: renderCard(initialState, cardRenderOptions),
            producer: async (ctrl) => {
              producerStarted = true;
              cardCtrl = ctrl;
              await ctrl.update(renderCard(filterForPrefs(latestState), cardRenderOptions));
              await renderDone;
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
        fallback: async (state) => {
          await channel.send(
            chatId,
            { card: renderCard(filterForPrefs(state), cardRenderOptions) },
            sendOpts
          );
        }
      });
    }
  } finally {
  }
}
'''


def minimal_active_runs_bundle() -> str:
    return '''// fixture
var ActiveRuns = class {
  register(chatId, run) {
    if (this.handles.has(chatId)) {
      throw new Error(`run already active for scope: ${chatId}`);
    }
    this.reservations.delete(chatId);
    const handle = { run, interrupted: false };
    this.handles.set(chatId, handle);
    return handle;
  }
  interrupt(chatId) {
    const h = this.handles.get(chatId);
    if (!h) return false;
    this.reservations.delete(chatId);
    h.interrupted = true;
    this.handles.delete(chatId);
    void h.run.stop().catch(() => {
    });
    return true;
  }
};
'''


def minimal_run_markdown_bundle() -> str:
    return '''// fixture
async function processAgentStream(handle, events, scope, idleTimeoutMs, recordSession, flush) {
  let state = initialState;
  await flush(state);
  return state;
}
async function awaitRenderAwareStream(input) {
}
async function consumeRun() {
  if (replyMode === "markdown") {
    let latestState = initialState;
    let producerStarted = false;
    let markdownCtrl;
    const renderDone = processAgentStream(
      handle,
      eventStream,
      scope,
      idleTimeoutMs,
      recordSession,
        async (state) => {
          latestState = state;
          if (markdownCtrl) {
            await markdownCtrl.setContent(renderText(filterForPrefs(state)));
          }
        }
    );
    const streamDone = channel.stream(
      chatId,
      {
        markdown: async (ctrl) => {
          producerStarted = true;
          markdownCtrl = ctrl;
            await ctrl.setContent(renderText(filterForPrefs(latestState)));
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
        fallback: async (state) => {
          const body = renderText(filterForPrefs(state));
          if (body.trim()) {
            await channel.send(chatId, { markdown: body }, sendOpts);
          }
        }
      });
  }
}
'''


def minimal_send_final_reply_bundle() -> str:
    return '''// fixture
async function sendFinalReply(input) {
  const body = renderText(input.state);
  if (input.replyMode === "markdown") {
    if (body.trim()) {
      try {
        await input.channel.stream(
          input.chatId,
          {
            markdown: async (ctrl) => {
              await ctrl.setContent(body);
            }
          },
          input.sendOpts
        );
      } catch (err) {
      }
    }
  }
}
'''


def minimal_run_executor_bundle() -> str:
    return '''// fixture
var DEFAULT_POST_DONE_EXIT_GRACE_MS = 2e3;
var RunExecutor = class {
  constructor(deps) {
    this.postDoneExitGraceMs = deps.postDoneExitGraceMs ?? DEFAULT_POST_DONE_EXIT_GRACE_MS;
  }
};
'''


def minimal_run_idle_timeout_bundle() -> str:
    return '''// fixture
function getRunIdleTimeoutMs(cfg) {
  const raw = cfg.preferences?.runIdleTimeoutMinutes;
  if (typeof raw !== "number" || !Number.isFinite(raw) || raw <= 0) return void 0;
  const clamped = Math.min(Math.max(Math.floor(raw), 1), 120);
  return clamped * 6e4;
}
'''


def minimal_codex_adapter_bundle() -> str:
    return '''// fixture
var CodexAdapter = class {
  run(opts) {
    const envOverrides = buildLarkChannelEnv(this.larkChannel);
    if (this.codexHome) {
      envOverrides.CODEX_HOME = this.codexHome;
    }
    const child = spawnProcess(this.binary, args, {
      cwd: opts.cwd,
      env: mergeProcessEnv(process.env, envOverrides),
      stdio: ["pipe", "pipe", "pipe"]
    });
  }
};
'''


def test_patcher_injects_labline_command_handlers_and_help() -> None:
    patcher = load_patcher()
    patched = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev"))

    assert '"/follow": handleLablineFollow' in patched
    assert '"/unfollow": handleLablineUnfollow' in patched
    assert '"/btw": handleLablineBtw' in patched
    assert '"/fork": handleLablineFork' in patched
    assert '"/rename": handleLablineRename' in patched
    assert "`/follow [task_id]`" in patched
    assert "`/btw <问题>`" in patched
    assert "`/fork [名称]`" in patched
    assert "`/rename <名称>`" in patched
    assert 'var LABLINE_DEFAULT_FRAMEWORK = "/framework/dev";' in patched
    assert "function lablineObservationTool()" in patched
    assert "function lablineAgentProxyEnvOverrides()" in patched
    assert "LABLINE_AGENT_HTTP_PROXY" in patched
    assert "function lablineStartProjectionLoop(" in patched
    assert "function lablineStartAutoWakeupLoop(" in patched
    assert "LABLINE_AUTO_WAKEUP_ENABLED" in patched
    assert "LABLINE_AUTO_WAKEUP_CHAT_ID" in patched
    assert "LABLINE_AUTO_WAKEUP_INCLUDE_CROSS_PROFILE" in patched
    assert "lablineDeliverAutoWakeupResult(channel" in patched
    assert '"delivery-targets"' in patched
    assert '"--include-cross-profile"' in patched
    assert '"wakeup-plan"' in patched
    assert '"wakeup"' in patched
    assert "function lablineProjectionAttention(" in patched
    assert "function lablineFlushAgentState(" in patched
    assert "function lablineSetMarkdownContentWithTimeout(" in patched
    assert "function lablineSendMarkdownTerminalFallback(" in patched
    assert "function lablineMarkdownTerminalNeedsFallback(" in patched
    assert "function lablineFetchRawMessageWithTimeout(" in patched
    assert "markdown-terminal-verified" in patched
    assert "markdown-terminal-stale" in patched
    assert "LABLINE_MARKDOWN_TERMINAL_VERIFY_TIMEOUT_MS" in patched
    assert "LABLINE_MARKDOWN_TERMINAL_FALLBACK_ENABLED" in patched
    assert "function lablineDefaultRunIdleTimeoutMinutes(" in patched
    assert "LABLINE_DEFAULT_RUN_IDLE_TIMEOUT_MINUTES" in patched
    assert "lablineRunningElapsedText(" in patched
    assert "lablineRegisterInterruptNotifier(" in patched
    assert "function lablineCreateCardContinuationStream(" in patched
    assert "LABLINE_CARD_CONTINUATION_MAX_AGE_MS" in patched
    assert "LABLINE_CARD_CONTINUATION_IDLE_MS" in patched
    assert "const impl = ctrl.impl || ctrl;" in patched
    assert "impl.throttle && typeof impl.throttle.flushNow" in patched
    assert "impl.queue && typeof impl.queue.drain" in patched
    assert 'typeof impl.completeTerminal === "function"' in patched
    assert 'typeof impl.patch === "function"' in patched
    assert "续接卡片" in patched
    assert '"projection-poll"' in patched
    assert 'plan.action === "patch"' in patched
    assert '"patch-recorded"' in patched
    assert '"stale_projection"' in patched
    assert "长任务卡片状态可能已经过期" in patched
    assert '"--reason"' in patched
    assert "lablineStartProjectionLoop({ channel, controls })" in patched
    assert "lablineStartAutoWakeupLoop({ channel, controls })" in patched
    assert "lablineProjectionLoop.stop();" in patched
    assert "lablineAutoWakeupLoop.stop();" in patched
    assert "async function lablineForkCodexThread(" in patched
    assert "async function lablineRenameCodexThread(" in patched
    assert "async function handleLablineRename(" in patched
    assert '"thread/fork"' in patched
    assert '"thread/name/set"' in patched
    assert "else child.stdin.end();" not in patched
    assert "async function lablineRunManagedBtwAnswer(" in patched
    assert "startRunFlow({" in patched
    assert "sendFinalReply({" in patched
    assert '"btw-answer"' in patched
    assert "ctx.activeRuns.interrupt(`${scope}:labline-btw`)" in patched
    assert "await ctx.channel.send(ctx.msg.chatId, { markdown: body }, sendOpts);" not in patched


def test_projection_status_messages_are_chinese_first() -> None:
    patcher = load_patcher()
    patched = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev"))

    assert "对象：" in patched
    assert "项目整体" in patched
    assert "原因：" in patched
    assert "状态：" in patched
    assert "运行中" in patched
    assert "已阻塞" in patched
    assert "异常" in patched
    assert "阻塞=" in patched
    assert "agent executor 启动后没有在 next_expected_update 前继续推进" in patched
    assert "target: ${target}" not in patched
    assert "reason: `${escapeCode(plan.reason)}`" not in patched
    assert "status: ${countParts.join" not in patched
    assert "project aggregate" not in patched


def test_auto_wakeup_delivery_uses_card_with_markdown_fallback() -> None:
    patcher = load_patcher()
    patched = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev"))

    assert "function lablineWakeupResultCard(" in patched
    assert "function lablineMaybeDeliverAutoWakeupNotice(" in patched
    assert "return renderCard(state)" in patched
    assert "{ card: lablineWakeupResultCard(message, result) }" in patched
    assert "{ markdown: message }" in patched
    assert "delivery-fallback-sent" in patched
    assert "wakeup_already_started" in patched
    assert "Leader 自动唤醒检查" in patched
    assert "notice-throttled" in patched
    assert "await lablineMaybeDeliverAutoWakeupNotice(channel, project, controls, value, 0, null, \"\");" in patched
    assert "任务：\\`" in patched
    assert "标题：" in patched
    assert "唤醒：\\`" in patched
    assert "结果：" in patched
    assert "task: `" not in patched
    assert "title: ${escapeMd(title)}" not in patched
    assert "wakeup: `" not in patched
    assert "action: `" not in patched


def test_projection_patch_sends_or_updates_visible_status_card() -> None:
    patcher = load_patcher()
    patched = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev"))

    assert "function lablineProjectionCard(" in patched
    assert "async function lablineSendProjectionStatusCard(" in patched
    assert "async function lablinePatchProjectionStatusCard(" in patched
    assert "plan.previous_message_id" in patched
    assert "previous_delivery_mode" in patched
    assert "await channel.updateCard(messageId, lablineProjectionCard(lablineProjectionMessage(plan)));" in patched
    assert "await lablinePatchProjectionStatusCard(channel, plan);" in patched
    assert "patch-updated" in patched
    assert "patch-sent" in patched
    assert '"projection-poll"' in patched
    assert '"--project"' in patched
    assert "cwd," in patched
    assert "LABLINE_PROJECTION_INCLUDE_CROSS_PROFILE" in patched
    assert "if (lablineProjectionIncludeCrossProfile()) pollArgs.push(\"--include-cross-profile\");" in patched
    assert '"--include-cross-profile"' in patched
    assert '"--message-id"' in patched
    assert '"--delivery-mode"' in patched
    assert "patch-recorded" in patched
    assert "card_update" in patched


def test_stream_resilience_patcher_times_out_hanging_flush_and_fallbacks_on_terminal_grace() -> None:
    patcher = load_patcher()

    patched = patcher.patch_stream_resilience(minimal_run_stream_bundle())

    assert "await lablineFlushAgentState(flush, state, scope);" in patched
    assert "await flush(state);" not in patched
    assert 'if (input.mode !== "markdown" || lablineMarkdownTerminalFallbackEnabled())' in patched
    assert "await runFallbackReply(input.mode, first.state, input.fallback);" in patched
    assert "const latest = typeof input.latestState" in patched
    assert 'input.mode === "markdown" && !lablineMarkdownTerminalFallbackEnabled()' in patched
    assert 'step: "render-after-stream-failed"' in patched


def test_stream_resilience_patches_interrupt_notifier_handle() -> None:
    patcher = load_patcher()

    patched = patcher.patch_stream_resilience(minimal_active_runs_bundle())

    assert "const handle = { run, interrupted: false, interruptNotifiers: new Set() };" in patched
    assert "for (const notify of h.interruptNotifiers || [])" in patched
    assert "notify();" in patched


def test_stream_resilience_patches_running_elapsed_rendering() -> None:
    patcher = load_patcher()
    bundle = r'''// fixture
function renderCard(state, options = {}) {
  const elements = [];
  if (state.terminal === "running") {
    if (state.footer) elements.push(footerStatus(state.footer));
  }
}
function footerStatus(status) {
  const text = status === "thinking" ? "\u{1F9E0} \u6B63\u5728\u601D\u8003" : status === "tool_running" ? "\u{1F9F0} \u6B63\u5728\u8C03\u7528\u5DE5\u5177" : "\u270D\uFE0F \u6B63\u5728\u8F93\u51FA";
  return noteMd(text);
}
function summaryText(state) {
  if (state.footer === "tool_running") return "\u6B63\u5728\u8C03\u7528\u5DE5\u5177";
  if (state.footer === "streaming") return "\u6B63\u5728\u8F93\u51FA";
  return "\u601D\u8003\u4E2D";
}
function renderText(state) {
  const parts = [];
  if (state.terminal === "running" && state.footer) {
    parts.push(footerLine(state.footer));
  }
}
function footerLine(status) {
  if (status === "thinking") return "_\u{1F9E0} \u6B63\u5728\u601D\u8003\u2026_";
  if (status === "tool_running") return "_\u{1F9F0} \u6B63\u5728\u8C03\u7528\u5DE5\u5177\u2026_";
  return "_\u270D\uFE0F \u6B63\u5728\u8F93\u51FA\u2026_";
}
async function processAgentStream(handle, events, scope, idleTimeoutMs, recordSession, flush) {
  const runStart2 = Date.now();
  let state = initialState;
}
async function awaitRenderAwareStream(input) {
}
'''

    patched = patcher.patch_stream_resilience(bundle)

    assert "function footerStatus(status, state)" in patched
    assert "footerStatus(state.footer, state)" in patched
    assert "lablineRunningElapsedText(state)" in patched
    assert "正在调用工具${elapsed}" in patched
    assert "footerLine(state.footer, state)" in patched
    assert "lablineStateWithRunStartedAt(initialState, runStart2)" in patched


def test_stream_resilience_patcher_drains_markdown_terminal_updates() -> None:
    patcher = load_patcher()

    patched = patcher.patch_stream_resilience(minimal_run_markdown_bundle())

    assert "await lablineSetMarkdownContentWithTimeout(" in patched
    assert "state.terminal !== \"running\" ? \"terminal\" : \"update\"" in patched
    assert "state.terminal !== \"running\"" in patched
    assert "latestState.terminal !== \"running\"" in patched
    assert "latestState: () => latestState," in patched
    assert "await lablineSendMarkdownTerminalFallback({" in patched
    assert "state: filterForPrefs(latestState)" in patched
    assert "let markdownMessageId;" in patched
    assert "markdownMessageId = ctrl.messageId;" in patched
    assert '"markdown-started"' in patched
    assert "messageId: markdownMessageId" in patched
    assert 'label: "run-terminal"' in patched
    assert "await markdownCtrl.setContent(" not in patched
    assert "await ctrl.setContent(" not in patched
    assert "await channel.send(chatId, { markdown: body }, sendOpts);" not in patched


def test_shim_markdown_terminal_helper_calls_complete_terminal() -> None:
    patcher = load_patcher()

    patched = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev"))

    assert 'if (terminal && typeof impl.completeTerminal === "function") {' in patched
    assert "await impl.completeTerminal();" in patched
    assert "await impl.throttle.flushNow();" in patched
    assert "await impl.queue.drain();" in patched


def test_stream_resilience_patches_final_markdown_reply_terminal_helper() -> None:
    patcher = load_patcher()

    patched = patcher.patch_stream_resilience(minimal_send_final_reply_bundle())

    assert "await lablineSetMarkdownContentWithTimeout(" in patched
    assert '"final-reply"' in patched
    assert "input.scope" in patched
    assert "await ctrl.setContent(body);" not in patched


def test_shim_markdown_terminal_fallback_sends_auditable_static_mirror() -> None:
    patcher = load_patcher()

    patched = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev"))

    assert "const decision = await lablineMarkdownTerminalNeedsFallback({" in patched
    assert "sourceMessageId: messageId" in patched
    assert "reason: decision.reason" in patched
    assert '"markdown-terminal-fallback-skipped"' in patched
    assert '"markdown-terminal-verify-missing-message"' in patched
    assert 'return { needed: false, reason: "missing-message-id" };' in patched


def test_stream_resilience_patcher_upgrades_markdown_terminal_fallback_message_id() -> None:
    patcher = load_patcher()

    legacy = patcher.patch_stream_resilience(minimal_run_markdown_bundle()).replace(
        '''      await lablineSendMarkdownTerminalFallback({
        channel,
        chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState),
        messageId: markdownMessageId,
        label: "run-terminal"
      });''',
        '''      await lablineSendMarkdownTerminalFallback({
        channel,
        chatId,
        sendOpts,
        scope,
        state: filterForPrefs(latestState)
      });''',
    )

    patched = patcher.patch_stream_resilience(legacy)

    assert "messageId: markdownMessageId" in patched
    assert 'label: "run-terminal"' in patched


def test_patcher_makes_post_done_exit_grace_configurable() -> None:
    patcher = load_patcher()

    patched = patcher.patch_post_done_exit_grace(minimal_run_executor_bundle())

    assert "var DEFAULT_POST_DONE_EXIT_GRACE_MS = lablinePostDoneExitGraceMs();" in patched
    assert "var DEFAULT_POST_DONE_EXIT_GRACE_MS = 2e3;" not in patched
    assert "function lablinePostDoneExitGraceMs()" not in patched


def test_patcher_removes_duplicate_post_done_helper_from_legacy_patch() -> None:
    patcher = load_patcher()
    legacy = '''// fixture
function lablinePostDoneExitGraceMs() {
  const parsed = Number.parseInt(process.env.LABLINE_POST_DONE_EXIT_GRACE_MS || "30000", 10);
  return Number.isFinite(parsed) && parsed >= 2000 ? parsed : 30000;
}
var DEFAULT_POST_DONE_EXIT_GRACE_MS = lablinePostDoneExitGraceMs();
'''

    patched = patcher.patch_post_done_exit_grace(legacy)

    assert "var DEFAULT_POST_DONE_EXIT_GRACE_MS = lablinePostDoneExitGraceMs();" in patched
    assert "function lablinePostDoneExitGraceMs()" not in patched


def test_patcher_defaults_run_idle_timeout_when_profile_unset() -> None:
    patcher = load_patcher()

    patched = patcher.patch_default_run_idle_timeout(minimal_run_idle_timeout_bundle())

    assert "const defaultMinutes = lablineDefaultRunIdleTimeoutMinutes();" in patched
    assert "return defaultMinutes > 0 ? defaultMinutes * 6e4 : void 0;" in patched
    assert 'if (raw <= 0) return void 0;' in patched
    assert 'raw <= 0) return void 0' in patched


def test_patcher_injects_agent_proxy_env_into_codex_child_only() -> None:
    patcher = load_patcher()

    patched = patcher.patch_agent_proxy_env(minimal_codex_adapter_bundle())

    assert "Object.assign(envOverrides, lablineAgentProxyEnvOverrides());" in patched
    assert "env: mergeProcessEnv(process.env, envOverrides)" in patched


def test_card_continuation_patcher_wraps_ordinary_card_stream() -> None:
    patcher = load_patcher()

    patched = patcher.patch_card_continuation(minimal_run_card_bundle())

    assert "const cardStream = lablineCreateCardContinuationStream({" in patched
    assert "initial: cardStream.initial()," in patched
    assert "initial: renderCard(initialState" not in patched
    assert "cardStream.setPrimary(ctrl);" in patched
    assert "await cardStream.update(state);" in patched
    assert "await cardStream.update(latestState);" in patched
    assert "latestState: () => latestState," in patched
    assert "await cardStream.fallback(state);" in patched
    assert "cardStream.close();" in patched
    assert "let cardCtrl;" not in patched
    assert "cardCtrl = ctrl;" not in patched
    assert "lablineRegisterInterruptNotifier(handle, async () => {" in patched
    assert "latestState = markInterrupted(latestState);" in patched
    assert "await cardStream.fallback(latestState);" in patched
    assert "unregisterInterruptNotifier?.();" in patched


def test_card_continuation_patcher_is_idempotent() -> None:
    patcher = load_patcher()

    once = patcher.patch_card_continuation(minimal_run_card_bundle())
    twice = patcher.patch_card_continuation(once)

    assert once == twice
    assert twice.count("const cardStream = lablineCreateCardContinuationStream({") == 1
    assert twice.count("initial: cardStream.initial(),") == 1
    assert twice.count("cardStream.setPrimary(ctrl);") == 1
    assert twice.count("latestState: () => latestState,") == 1
    assert twice.count("await cardStream.fallback(state);") == 1
    assert twice.count("lablineRegisterInterruptNotifier(handle, async () => {") == 1


def test_card_continuation_patcher_upgrades_existing_initial_card() -> None:
    patcher = load_patcher()

    legacy = patcher.patch_card_continuation(minimal_run_card_bundle()).replace(
        "initial: cardStream.initial(),",
        "initial: renderCard(initialState, cardRenderOptions),",
    )
    legacy = legacy.replace("                unregisterInterruptNotifier?.();\n", "")

    patched = patcher.patch_card_continuation(legacy)

    assert "initial: cardStream.initial()," in patched
    assert "initial: renderCard(initialState" not in patched
    assert "unregisterInterruptNotifier?.();" in patched


def test_full_patch_btw_card_stream_has_initial_timer_and_stop_notifier() -> None:
    patcher = load_patcher()

    patched = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev"))

    assert "initial: cardStream.initial()," in patched
    assert "initial: renderCard(initialState)" not in patched
    assert "const unregisterInterruptNotifier = lablineRegisterInterruptNotifier(handle, async () => {" in patched
    assert "await cardStream.fallback(latestState);" in patched


def test_stream_resilience_patcher_is_idempotent() -> None:
    patcher = load_patcher()

    once = patcher.patch_stream_resilience(minimal_run_stream_bundle() + minimal_run_markdown_bundle())
    twice = patcher.patch_stream_resilience(once)

    assert once == twice
    assert twice.count("lablineFlushAgentState(flush, state, scope)") == 2
    assert twice.count("await runFallbackReply(input.mode, first.state, input.fallback);") == 1
    assert twice.count("await lablineSetMarkdownContentWithTimeout(") == 2
    assert twice.count("await lablineSendMarkdownTerminalFallback({") == 1


def test_stream_resilience_patcher_upgrades_legacy_markdown_fallback_patch() -> None:
    patcher = load_patcher()

    legacy = patcher.patch_stream_resilience(minimal_run_stream_bundle() + minimal_run_markdown_bundle())
    legacy = legacy.replace(
        '''    if (input.mode !== "markdown" || lablineMarkdownTerminalFallbackEnabled()) {
      await runFallbackReply(input.mode, first.state, input.fallback);
    }''',
        "    await runFallbackReply(input.mode, first.state, input.fallback);",
    )
    legacy = legacy.replace(
        '''        if (input.mode === "markdown" && !lablineMarkdownTerminalFallbackEnabled()) {
          void renderResult.then((result) => {
            if (!result.ok) {
              log.fail("stream", result.err, { mode: input.mode, step: "render-after-stream-failed" });
            }
          });
          return;
        }
''',
        "",
    )
    legacy = legacy.replace(
        '''        fallback: async () => {
        }''',
        '''        fallback: async (state) => {
          const body = renderText(filterForPrefs(state));
          if (body.trim()) {
            await channel.send(chatId, { markdown: body }, sendOpts);
          }
        }''',
    )

    patched = patcher.patch_stream_resilience(legacy)

    assert 'if (input.mode !== "markdown" || lablineMarkdownTerminalFallbackEnabled())' in patched
    assert 'input.mode === "markdown" && !lablineMarkdownTerminalFallbackEnabled()' in patched
    assert "await channel.send(chatId, { markdown: body }, sendOpts);" not in patched


def test_stream_resilience_patcher_removes_legacy_btw_markdown_fallback() -> None:
    patcher = load_patcher()
    legacy = '''// fixture
async function consumeRun() {
      await awaitRenderAwareStream({
        mode: replyMode,
        streamDone,
        renderDone,
        producerStarted: () => producerStarted,
        latestState: () => latestState,
        fallback: async (state) => {
          const body = renderText(filterForPrefs(state));
          if (body.trim()) {
            await ctx.channel.send(ctx.msg.chatId, { markdown: body }, sendOpts);
          }
        }
      });
}
'''

    patched = patcher.patch_stream_resilience(legacy)

    assert "fallback: async () => {" in patched
    assert "await ctx.channel.send(ctx.msg.chatId, { markdown: body }, sendOpts);" not in patched


def test_patcher_is_idempotent() -> None:
    patcher = load_patcher()
    once = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev"))
    twice = patcher.patch_text(once, Path("/framework/dev"))

    assert twice.count(patcher.BEGIN) == 1
    assert twice.count('"/btw": handleLablineBtw') == 1
    assert twice.count('"/fork": handleLablineFork') == 1
    assert twice.count('"/rename": handleLablineRename') == 1
    assert twice.count("const lablineProjectionLoop = lablineStartProjectionLoop({ channel, controls });") == 1
    assert twice.count("const lablineAutoWakeupLoop = lablineStartAutoWakeupLoop({ channel, controls });") == 1
    assert twice.count("lablineProjectionLoop.stop();") == 1
    assert twice.count("lablineAutoWakeupLoop.stop();") == 1
    assert twice.count("`/btw <问题>`") == 1
    assert twice.count("`/fork [名称]`") == 1
    assert twice.count("- `/rename <名称>`") == 1
    assert twice.count("ctx.activeRuns.interrupt(`${scope}:labline-btw`)") == 1
    assert once == twice


def test_patcher_migrates_legacy_auto_wakeup_loop_call() -> None:
    patcher = load_patcher()
    legacy = patcher.patch_text(minimal_bridge_bundle(), Path("/framework/dev")).replace(
        "  const lablineAutoWakeupLoop = lablineStartAutoWakeupLoop({ channel, controls });\n",
        "  const lablineAutoWakeupLoop = lablineStartAutoWakeupLoop({ controls });\n",
    )

    patched = patcher.patch_text(legacy, Path("/framework/dev"))

    assert "lablineStartAutoWakeupLoop({ controls })" not in patched
    assert patched.count("const lablineAutoWakeupLoop = lablineStartAutoWakeupLoop({ channel, controls });") == 1


def test_patcher_accepts_escaped_help_anchor_from_built_bundle() -> None:
    patcher = load_patcher()
    escaped = minimal_bridge_bundle().replace(
        '        "- `/status` — 当前状态",',
        '        "- `/status` \\u2014 \\u5F53\\u524D\\u72B6\\u6001",',
    )

    patched = patcher.patch_text(escaped, Path("/framework/dev"))

    assert "`/follow [task_id]`" in patched
    assert "`/btw <问题>`" in patched
    assert "`/fork [名称]`" in patched
    assert "`/rename <名称>`" in patched


def test_channel_patcher_adds_env_gated_empty_bot_identity_fallback() -> None:
    patcher = load_patcher()

    patched = patcher.patch_channel_text(minimal_channel_bundle())

    assert "LARK_CHANNEL_ALLOW_EMPTY_BOT_ID" in patched
    assert "r.bot ?? r.data?.bot ?? r.data ?? r" in patched
    assert "bot?.open_id ?? bot?.openId" in patched
    assert 'return { openId: "", name: "bot" };' in patched


def test_channel_patcher_is_idempotent() -> None:
    patcher = load_patcher()

    once = patcher.patch_channel_text(minimal_channel_bundle())
    twice = patcher.patch_channel_text(once)

    assert once == twice
    assert twice.count("LARK_CHANNEL_ALLOW_EMPTY_BOT_ID") == 2


def test_patcher_adds_codex_item_updated_support() -> None:
    patcher = load_patcher()

    patched = patcher.patch_codex_item_updated(minimal_codex_translator_bundle())

    assert 'case "event_msg":' in patched
    assert 'case "response_item":' in patched
    assert "translateEventMsg(raw)" in patched
    assert "translateResponseItem(raw)" in patched
    assert 'case "item.updated":' in patched
    assert "translateItemUpdated(raw)" in patched
    assert "updatedTextByItemId = /* @__PURE__ */ new Map();" in patched
    assert 'lastAgentMessageText = "";' in patched
    assert "translateAgentText(message)" in patched
    assert "last_agent_message" in patched
    assert 'payload.phase === "final_answer"' in patched
    assert "internal_chat_message_metadata_passthrough" in patched
    assert 'type: "tool_update"' in patched
    assert 'case "tool_update":' in patched
    assert "message.slice(previous.length)" in patched


def test_patcher_upgrades_legacy_codex_item_updated_patch() -> None:
    patcher = load_patcher()

    legacy = patcher.patch_codex_item_updated(minimal_codex_translator_bundle())
    legacy = legacy.replace('case "event_msg":\n        return this.translateEventMsg(raw);\n', "")
    legacy = legacy.replace('case "response_item":\n        return this.translateResponseItem(raw);\n', "")
    legacy = legacy.replace('  lastAgentMessageText = "";\n', "")
    start = legacy.index("  translateAgentDelta(delta) {")
    end = legacy.index("  translateAgentMessage(raw) {")
    legacy = legacy[:start] + legacy[end:]
    legacy = legacy.replace(
        "return message.length > previous.length ? this.translateAgentDelta(message.slice(previous.length)) : [];",
        'return message.length > previous.length ? [{ type: "text", delta: message.slice(previous.length) }] : [];',
    )
    legacy = legacy.replace(
        "return this.translateAgentText(message);",
        'return [{ type: "text", delta: message }];',
        1,
    )
    legacy = legacy.replace(
        "return this.translateAgentDelta(delta);",
        'return [{ type: "text", delta }];',
    )
    legacy = legacy.replace(
        "return this.translateAgentDelta(message.slice(previous.length));",
        'return [{ type: "text", delta: message.slice(previous.length) }];',
    )
    legacy = legacy.replace(
        '''  translateAgentMessage(raw) {
    const message = stringValue(raw.message ?? raw.text);
    return this.translateAgentText(message);
  }''',
        '''  translateAgentMessage(raw) {
    const message = stringValue(raw.message ?? raw.text);
    if (!message) return [];
    return [{ type: "text", delta: message }];
  }''',
    )

    patched = patcher.patch_codex_item_updated(legacy)

    assert 'case "event_msg":' in patched
    assert 'case "response_item":' in patched
    assert 'lastAgentMessageText = "";' in patched
    assert "translateAgentDelta(delta)" in patched
    assert "translateAgentText(message)" in patched
    assert "last_agent_message" in patched
    assert 'payload.phase === "final_answer"' in patched
    assert "internal_chat_message_metadata_passthrough" in patched
    assert '''  translateAgentMessage(raw) {
    const message = stringValue(raw.message ?? raw.text);
    if (!message) return [];
    return [{ type: "text", delta: message }];
  }''' not in patched


def test_codex_item_updated_patcher_is_idempotent() -> None:
    patcher = load_patcher()

    once = patcher.patch_codex_item_updated(minimal_codex_translator_bundle())
    twice = patcher.patch_codex_item_updated(once)

    assert once == twice
    assert twice.count('case "event_msg":') == 1
    assert twice.count('case "response_item":') == 1
    assert twice.count('case "item.updated":') == 1
    assert twice.count("  translateItemUpdated(raw) {") == 1
    assert twice.count("  translateEventMsg(raw) {") == 1
    assert twice.count("  translateResponseItem(raw) {") == 1
    assert twice.count('case "tool_update":') == 1
