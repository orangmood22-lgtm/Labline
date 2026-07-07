# Labline Development Log

开发者侧按模块记录的 Labline 框架开发日志。模块边界见 `to-developer/20260615-FRAMEWORK_MODULES.md`；用户可见部分在发布前再蒸馏到 `CHANGELOG.md`。

## [Unreleased]

### skills
- Added the user-facing `runtime-task-protocol` skill and shared reference, introduced explicit `planner` and `reviewer` role skills, and wired Leader/Planner/Coder/Deployer/Writer/Reviewer plus their Codex mirrors to formal `runtime-task-protocol` DAG edges so every dispatched role sees status, terminal, and resolution-event obligations.
- Tightened the actual Leader dispatch prompts: Reviewer review templates now carry `agent_id`, `agent_status.py`, terminal status, and verdict artifact requirements; embedded Coder/Deployer/Writer prompts in both main and Codex Leader skills explicitly read `runtime-task-protocol.md`.
- Updated `leader`, `paper-talk`, and their Codex mirrors to use `.labline/runtime/pipelines/*.json` for new-project machine phase state; root or workflow-local `PIPELINE_STATE.json` files are now legacy migration input only.
- Added dev-only Developer Skill forks under `to-developer/skills/dev-*`, including `dev-worker`, `dev-caveman`, `dev-tdd`, `dev-diagnose`, `dev-review`, `dev-grill-docs`, `dev-handoff`, and `dev-zoom-out`.
- Removed `worker` from the user project role graph and Codex skill mirror; cheap worker remains a dev-only runtime/helper concept instead of a Coder/Deployer/Writer peer.
- Added `skills/feishu-session/` for operating the Feishu-controlled Codex session bridge and runner.
- Added Agent Status Stream protocol and wired Leader/Coder/Deployer/Writer role instructions to project-local status snapshots.
- Updated reviewer-independence guidance so Reviewer status may carry transport/input-scope metadata without carrying review reasoning or executor summaries.
- 固化用户侧默认 Runtime Binding：Leader=`gpt-5.5`，Planner/Reviewer/Writer=`gpt-5.4`，Coder/Deployer=`gpt-5.4-mini`；开发侧 Worker 默认 `gpt-5.4-mini`，且不进入用户 role graph。
- 新增 `shared-references/role-contracts.md` 及 Codex mirror，固定 Leader/Planner/Coder/Deployer/Writer/Reviewer 的职责、默认模型绑定和 handoff 规则，避免 provider/model 覆盖改变用户侧 role graph。
- Normalized skill DAG governance so formal edges come only from frontmatter `invokes`.
- Added `platform`, `status`, and dependency metadata to key Codex/Claude dual-client skills.
- Added Codex mirrors for the newly added skill set.
- Enhanced `skills-codex-claude-review` overlays with reviewer bias guard, edit whitelist, reviewer memory, debate protocol, and broader venue support.

### tools
- Updated skill catalog translation/category generation for the new Planner/Reviewer/runtime-task-protocol user-skill surface.
- Added Runtime Task resolution folding for auto-wakeup/status: `task.superseded`, `task.resolved`, `task.resolved_by`, and terminal `leader.decision` events now mark replaced old tasks as non-active terminal resolutions in summaries, suppress stale escalation-file wakeup candidates for resolved task ids, and instruct auto-wakeup Leader turns to write machine-readable resolution events when a later task/artifact replaces an older blocker.
- Fixed Remote Observation projection patch delivery so progress `patch` plans now update the previous Feishu status card when a recorded `message_id` is available, or send and record a new status card when no update target exists; `delivery-record` now carries bridge-owned `message_id` / `delivery_mode`.
- Added opt-in bridge Remote Observation cross-profile polling for the current workspace/project via `LABLINE_PROJECTION_INCLUDE_CROSS_PROFILE`, while keeping default delivery same-profile to avoid cross-bot Feishu send failures.
- Fixed bridge auto-wakeup visibility so non-healthy `skip` / `needs_confirmation` / `started` outcomes are delivered to active same-profile `/follow` chats or explicit `LABLINE_AUTO_WAKEUP_CHAT_ID` targets with per-result notice throttling, making `wakeup_already_started` and lease conflicts visible instead of log-only; cross-profile targets require `LABLINE_AUTO_WAKEUP_INCLUDE_CROSS_PROFILE=1`.
- Added split proxy handling for Feishu-controlled Codex runs: bridge profiles may still start with `--no-proxy` for Feishu SDK calls while `LABLINE_AGENT_HTTP_PROXY` / `LABLINE_AGENT_HTTPS_PROXY` / `LABLINE_AGENT_NO_PROXY` are injected only into Codex agent subprocesses and `native-codex` auto-wakeup.
- Fixed the Labline `lark-channel-bridge` markdown terminal fallback double-send regression: ordinary IM markdown runs now pass the streaming `messageId` into terminal verification, already-partially-patched bundles are upgraded, and `missing-message-id` in verify mode records an audit skip instead of sending an extra static fallback message.
- Added verified markdown-stream terminal fallback to the Labline `lark-channel-bridge` shim: after terminal markdown flush, the bridge fetches the original streaming message, detects stale running footers such as "正在调用工具/正在输出/正在思考", and sends an auditable static final markdown mirror with `sourceMessageId`/reason logging when the visible card is stale or cannot be verified.
- Fixed markdown-stream terminal finalization in the Labline `lark-channel-bridge` shim by calling the underlying Feishu markdown stream `completeTerminal()` on terminal state, falling back to throttle flush / update queue drain only when the upstream controller lacks that API.
- Made bridge post-done subprocess cleanup grace configurable via `LABLINE_POST_DONE_EXIT_GRACE_MS` and widened the default to 30s so Codex runs that have already emitted `done` are not stopped during normal post-run shutdown before visible stream finalization settles.
- Added a Labline default run idle watchdog for `lark-channel-bridge` profiles without an explicit timeout: `LABLINE_DEFAULT_RUN_IDLE_TIMEOUT_MINUTES` defaults to 15 minutes, can be set to `0` to preserve fully unbounded runs, and leaves explicit `/timeout off` / profile `runIdleTimeoutMinutes: 0` behavior unchanged. This gives Codex transport stalls a visible `idle_timeout` terminal state instead of leaving Feishu cards indefinitely on "正在输出".
- Added elapsed-time ticks to ordinary running Feishu cards (`正在思考/正在调用工具/正在输出`) and wired `/stop` to an interrupt notifier that immediately patches the visible card to `已中断`, instead of waiting for the Codex event stream to produce a terminal event. The initial card frame, continuation/fallback renders, and bridge-managed `/btw` side-run cards all use the same timed state so users do not see a static first card before the next update.
- Added explicit `--force` retry support to `lane workflow wakeup-plan` and `lane workflow wakeup`. Forced wakeups bypass only persisted `wakeup_key` dedupe, preserve high-risk intent and `leader_session` lease gates, and record a `wakeup.retry_requested` audit event before writing a second same-key `wakeup.started`.
- Changed bridge auto-wakeup result delivery to use the same CardKit-style run card surface as ordinary agent replies, with markdown fallback on card delivery failure, and localized wakeup result fields (`任务/标题/唤醒/结果/信号`) for consistency with Remote Observation projections.
- Localized Labline bridge Remote Observation projection messages to Chinese-first wording for target/reason/status/task summaries, including common executor-loss and RemDet R002 blocker phrases, so automatic Feishu status updates are readable without interpreting raw English fields.
- Added explicit `native-codex` auto-wakeup backend for `lane workflow wakeup --backend native-codex`. It runs a foreground `codex exec` Leader turn from the sanitized wakeup prompt, records output/stdout/stderr artifact refs, writes `wakeup.completed` or `wakeup.failed`, and releases the `leader_session` lease after the Codex process exits.
- Defaulted the `native-codex` wakeup backend to `codex exec -s danger-full-access`, with `--codex-sandbox` / `LABLINE_AUTO_WAKEUP_CODEX_SANDBOX` overrides, so bridge-triggered Leader turns do not fail on hosts where `bwrap` cannot create unprivileged namespaces.
- Added executor-loss detection for agent status snapshots: a `starting` agent with no job handle past `next_expected_update` is derived as runtime `anomaly` with escalation-gated heartbeat, so lost sub-agent handles no longer look like healthy running work.
- Fixed `wakeup-plan` candidate selection so already-started wakeup keys are skipped per candidate; a stale older candidate no longer prevents later blocked/anomaly candidates from waking Leader.
- Excluded terminal task results from `wakeup-plan` candidates so completed/failed/cancelled states are handled by Remote Observation delivery instead of repeatedly starting Leader turns.
- Added native auto-wakeup apply v0 with `lane workflow wakeup --project PATH --json`. It acquires the `leader_session` lease, writes a `wakeup.started` event, creates a sanitized Leader handoff prompt under `.labline/runtime/wakeups/`, and dedupes repeated wakeup attempts by persisted `wakeup_key`; the v0 backend is prompt-only and does not launch another agent process by default.
- Added native auto-wakeup dry-run planning with `lane workflow wakeup-plan --project PATH --json`. It reads Runtime Tasks, escalation files, active leases, and pending high-risk control intents; emits `skip`, `needs_confirmation`, or `acquire_lease -> start_leader_turn` plans without writing runtime state or starting an agent.
- Tightened `wakeup-plan` dedupe so a candidate whose `wakeup_key` already has a persisted `wakeup.started` event returns `skip/wakeup_already_started` at plan time, avoiding repeated bridge-spawned no-op wakeup processes.
- Added Chinese-output constraints to auto-wakeup Leader prompts so Feishu-delivered wakeup conclusions explain decisions and required actions in Chinese instead of forwarding English-only monitor-style text.
- Added an opt-in bridge auto-wakeup trigger to the Labline `lark-channel-bridge` shim. With `LABLINE_AUTO_WAKEUP_ENABLED=1`, the bridge periodically runs `lane workflow wakeup-plan` for the profile workspace and starts `lane workflow wakeup --backend native-codex` only when the plan reaches `acquire_lease -> start_leader_turn`; lease, dedupe, prompt, and completion/failure records remain owned by `.labline/runtime/`.
- Added bridge-side delivery for auto-wakeup Leader results: after `native-codex` wakeup exits, the shim reads the wakeup JSON/artifact output and sends a concise result message to active `/follow` chats for the same profile/project, with `LABLINE_AUTO_WAKEUP_CHAT_ID` as an explicit fixed-chat fallback.
- Added `stale_projection` Remote Observation fresh replies for long-task Feishu cards that remain on the same active state past `next_expected_update` grace or stuck display phases such as "正在调用工具/正在输出"; delivery records now store projection `reason` so stale hints fire once per unchanged state signature without spamming.
- Added ordinary Feishu run-card resilience to the Labline `lark-channel-bridge` shim: card/markdown flushes now have a timeout so a stuck Feishu update cannot block Codex event consumption, and terminal stream grace expiry sends a fallback final reply instead of leaving the original card stuck on "正在调用工具/正在输出".
- Added ordinary Feishu run-card continuation to the Labline `lark-channel-bridge` shim: streaming card updates now move to a fresh continuation card when the current card update times out, fails, or reaches the configured card-age threshold, without requiring users to preselect `/follow`.
- Tightened ordinary Feishu run-card continuation so `ctrl.update()` is followed by a real patch/drain wait, stream failures can fallback from the latest known state without waiting for agent completion, and running cards get a periodic health probe (`LABLINE_CARD_CONTINUATION_IDLE_MS`) before the maximum-age fallback.
- Added a bridge-profile Remote Observation projection poller to the Labline `lark-channel-bridge` shim. It scans active `/follow` subscriptions, sends `fresh_reply` status updates through the current bridge channel, records delivery state, and stops cleanly on bridge disconnect.
- Extended `tools/labline_remote_observation.py` with `projection-poll` for bridge-side delivery loops, and deduped urgent `blocked`/terminal projections by state signature after successful delivery to avoid repeated fresh replies.
- Added a Labline `lark-channel-bridge` `/rename <name>` shim for Codex profiles. It calls Codex app-server `thread/name/set` for the current active thread and rejects non-Codex, unnamed, missing-thread, or currently running scopes.
- Added a Labline `lark-channel-bridge` `/fork [name]` shim for Codex profiles. It calls Codex app-server `thread/fork`, optionally calls `thread/name/set`, updates the bridge session catalog to the new thread, and rejects non-Codex or currently running scopes instead of cloning chat summaries.
- Extended `tools/patch_lark_channel_bridge_labline.py` to patch older `lark-channel-bridge` Codex JSONL translators for `item.updated` events, including incremental agent-message de-duplication and running tool-output updates so Feishu projection does not silently drop Codex progress events.
- Extended `tools/patch_lark_channel_bridge_labline.py` to patch installed `@larksuite/channel` bundles with an env-gated empty bot identity fallback (`LARK_CHANNEL_ALLOW_EMPTY_BOT_ID`) for debug profiles where `/open-apis/bot/v3/info` is unavailable, while keeping normal bridge startup strict by default.
- Added `tools/patch_lark_channel_bridge_labline.py` to reapply Labline Remote Observation command shims (`/follow`, `/unfollow`, `/btw`) to an installed `lark-channel-bridge` bundle when upstream has not yet exposed those commands.
- Extended the `/btw` bridge shim from route-only receipt to read-only side-channel answering: after routing and thread recording, it runs a bridge-managed read-only side-channel answer through the normal run UI (working reaction / streaming card or markdown / active run state), records sanitized `btw.answered` metadata, and lets plain `/stop` interrupt the current BTW side run without injecting into the main TUI.
- Added dev-only `to-developer/scripts/sync_dev_framework_remote.sh` for explicit dry-run/apply rsync of the current dev checkout to a remote framework directory, with optional bridge shim reapplication.
- Added local long-task debug smoke mode: `lane debug longtask-smoke --project PATH` copies a real project by default, starts a real local detached Python job, registers it as a supervised Runtime Task, verifies running heartbeat health, completes the task after the job exits, and checks terminal heartbeat escalation with JSON/Markdown reports.
- Added local user-side debug smoke mode: `lane debug runtime-smoke --project PATH` copies a real project into an isolated local worktree by default, runs project update/doctor, runtime task/status/heartbeat checks, fake Feishu Remote Observation routing, runtime leak checks, and writes JSON/Markdown debug reports; `--in-place --yes` is required to mutate the target project directly.
- Added Remote Interaction Routing v0 to `tools/labline_remote_observation.py`: `route-message` classifies archived remote messages into observation, BTW, control intent, or normal project interaction; writes sanitized `remote_message.routed`, `btw.question_received`, `btw.answered`, and `control_intent.submitted` runtime events; keeps BTW thread records bridge-owned and avoids TUI injection for read-only/status questions.
- Added bridge-owned Remote Observation / Feishu Projection contract helper `tools/labline_remote_observation.py` with remote message archive refs, stable follow subscription ids, stable projection delivery keys, delivery state recording, projection throttling decisions, and terminal/escalation fresh-reply decisions without writing chat/open ids or delivery failures into project runtime.
- Added Phase 6 runtime adapters: `agent_status.py` now defaults project-root writes to `.labline/runtime/agents` while retaining legacy `.labline/status/agents` read compatibility; watchdog can opt-in mirror task summaries/anomalies into `.labline/runtime/watchdog`, runtime events, and escalations; experiment queue can opt-in mirror `queue_state.json` into `.labline/runtime/queues`.
- Added Escalation-Gated Heartbeat v0 with `lane heartbeat`, `--dry-run`, explicit `--task` checks, passive healthy checks, escalation file emission for terminal/anomaly/decision states, and task-scoped lease gating before escalation control.
- Added lease/control-intent v0 with `lane runtime lease acquire/release/status` and `lane runtime intent submit`, including TTL leases, expired lease stealing events, owner-checked release, and bridge-safe control intent events that use archive refs instead of chat identities.
- Added Runtime Task lifecycle v0 with `lane runtime task create/update/complete/fail/cancel`, capability profile consistency checks, explicit task aggregation in `lane status`, and task lifecycle events.
- Added Runtime Status Aggregator v0 with `lane status --json/--brief` and `lane runtime summarize`, deriving project task and summary views from runtime/legacy agent status plus runtime job, queue, watchdog, and pipeline source files.
- Added Runtime Core v0 with `tools/labline_runtime.py` and `lane runtime init/event/task` commands for project-local `.labline/runtime/` initialization and append-only runtime events.
- Drafted the Project Runtime State Root and Project Heartbeat Protocol direction: unified Runtime Tasks with capability profiles instead of separate ordinary/long task lifecycles, component-owned runtime state under `.labline/runtime/`, Runtime Status Aggregator-derived `tasks` and `summaries`, read-only Runtime Observation Entries, bridge-profile-scoped Remote Observation Subscriptions for TUI-originated task push, lease-protected Runtime Control Intents, Multi-Endpoint Control, and escalation-gated heartbeat.
- Renamed the framework from ARIS to Labline, with `lane` as the public CLI, `~/.labline` / `.labline` as runtime state, and `LABLINE_*` as the environment prefix. Legacy `.aris/manifest.json` remains migration input only.
- Added `lane dev rt/runtime ...` as the Developer Runtime Surface for provider registration, role binding, prompt generation, and OpenAI-compatible cheap worker runs; removed `lane dev worker ...` from the canonical CLI.
- Added `lane dev rt load .env` for one-file Developer Runtime provider/agent injection, storing provider config separately from local API-key material.
- Added `lane dev rt config --json` for script-readable Developer Runtime config inspection without exposing API key values.
- Added `lane dev skills ...` and `tools/install_labline_dev_skills.sh` for Codex-only dev skill installation into the dev checkout `.agents/skills/dev-*` surface.
- Added `lane dev user-surface ...` so user-facing catalog/DAG generation is explicit and separate from dev skill installation.
- Added `tools/generate_dev_skill_catalog.py` and `tools/generate_dev_skill_dag.py` for dev-only skill catalog and DAG generation.
- Added optional `tools/generate_skill_dag.py --fail-on-inferred` gate so weak body mentions can be reported and eventually blocked without changing default DAG generation behavior.
- 新增 `tools/update_developer_docs.py`，用于校验 dev-only 文档覆盖并重新生成 `to-developer/DOC_DAG.mmd`。
- `tools/update_developer_docs.py` 忽略 `to-developer/logs/dev-runtime/` 与 `to-developer/logs/dev-workflow/`，避免把本机运行态日志误当作必须进入开发者文档 DAG 的规范材料。
- Added `tools/feishu_control.py` for session registration, inbox routing, control leases, approvals, `/interrupt`, and `/btw`.
- Added `tools/labline_feishu_session.py` for managed `codex exec` sessions and live tmux injection with Feishu status-card updates.
- Added `tools/agent_status.py` for schema-v1 per-agent status snapshots with `start`, `update`, `finish`, `list`, `summary`, and `validate`.
- Made release tag tooling use `${PYTHON:-python3}` instead of assuming `python3.8`.
- Added guarded release tooling under `tools/release/`.
- Made `mcp-servers/codex-review/bridge.py` resolve its sibling `server.py` by default instead of using a hard-coded developer path.
- Added Python 3.8 compatibility fixes to selected tools and tests.
- Updated catalog generation/translation coverage for newer role and DAG-check skills.

### templates
- Added Agent Status Stream rules to Claude/Codex project templates.
- Reworked `templates/README.md` into a structured template index.
- Generalized `project.yaml.tmpl` server examples and framework metadata.
- Updated idea candidate template paths to the current project file layout.

### docs
- Documented Runtime Task Protocol as a hard Role Contract requirement in the Operations Guide, and regenerated the user skill DAG/catalog artifacts for the new role/protocol skills.
- Documented Remote Observation visible progress patching and auto-wakeup status notices in Feishu integration, operations, and tool-index docs.
- Documented Feishu/Codex split proxy operation for `lane feishu run --no-proxy` environments where Feishu must be direct but Codex API requires a local proxy.
- Documented forced auto-wakeup retry usage in Feishu integration and operations docs, clarifying that `--force` is a manual retry path for a previously started `wakeup_key` and does not bypass high-risk confirmation or `leader_session` leases.
- Documented `stale_projection` as a Feishu Remote Observation display-staleness hint, distinct from task failure, in the Feishu integration and operations guides.
- Documented ordinary Feishu message card continuation as a display-channel fallback, distinct from task restart and not limited to `/follow`.
- Documented ordinary Feishu card continuation triggers as stream/update failures, update timeouts, and running-card health probes, with maximum card age as a final fallback rather than the primary disconnect detector.
- Documented bridge auto-wakeup as an opt-in trigger for `lane workflow wakeup`, not as bridge ownership of workflow state; high-risk control intents still require confirmation.
- Added `to-developer/plans/20260704-WORKFLOW_RUNTIME_STATEGRAPH_SPIKE.md`, freezing the auto-wakeup state graph and the LangGraph/OpenClaw adapter boundary: Labline `.labline/runtime/` remains the state truth, Feishu stays transport/observation, LangGraph is optional workflow backend, and OpenClaw is an agent runtime/orchestration candidate.
- Updated the top-level design so Workflow Runtime Stategraph is the current bridge between heartbeat/projection/lease and later LangGraph/OpenClaw adapter spikes, rather than an immediate migration of Labline core.
- Documented the Feishu `/follow` delivery loop: active subscriptions are scanned by the bridge profile poller, only `fresh_reply` states produce new messages, successful state signatures are deduped, and project debug monitors are separate alert sources.
- Documented Feishu `/rename <名称>` as a Codex-native current-thread rename command that does not fork or rename the Feishu chat.
- Documented Feishu `/fork [名称]` as a Codex-native thread fork command rather than a Labline transcript-copy mechanism.
- Updated the developer top-level design and module guide with a capability-discovery rule: when building new features, check Codex CLI/app-server native interfaces first, then upstream bridges/SDKs/MCPs, then add Labline adapters or runtime protocols only where needed.
- Documented `lane debug longtask-smoke` in stable user docs as the local, Docker-free real long-task lifecycle smoke test entry.
- Updated `deploy/DEPLOY_GUIDE.md` with a copy-pasteable 3090 single-user GPU realtest path, including `docker-compose.gpu.yaml` setup, host-network port exposure semantics, `lane debug runtime-smoke`, browser access via `http://[服务器IP]:18080`, firewall checks, and cleanup.
- Documented `lane debug runtime-smoke` in stable user docs as the local, Docker-free runtime/Feishu projection smoke test entry.
- Updated stable user docs for Runtime Heartbeat / Feishu Projection v0: added `docs/TOOLS_INDEX.md`, documented `.labline/runtime/`, `lane runtime`, `lane status`, `lane heartbeat`, Remote Observation `/follow`, bridge-owned state boundaries, and root `PIPELINE_STATE.json` deprecation.
- Added runtime-upgrade dev discussion covering human/shared/agent/maintenance project surfaces, `.labline/runtime/` subdirectory ownership, Feishu as a future observation/control entry rather than runtime owner, non-interrupting progress follow and push subscriptions for TUI-originated tasks, multi-endpoint control rules, Feishu bridge vs legacy Feishu control boundary, and root `PIPELINE_STATE.json` deprecation.
- Added `to-developer/plans/20260629-RUNTIME_HEARTBEAT_IMPLEMENTATION_PLAN.md` to turn the runtime heartbeat / Feishu projection discussion into phased implementation slices with deliverables, acceptance checks, routing rules, and test matrix.
- Added `to-developer/DEV_SKILL_CATALOG.md`, `to-developer/DEV_SKILL_DAG.yaml`, `to-developer/DEV_SKILL_DAG.mmd`, and ADR-0005 to define Developer Skills, their fork lineage, and their separate install surface.
- Updated tripartite architecture, operations guide, project agent template, skill catalog, and skill DAG so user-facing roles stay limited to Leader, Coder, Deployer, Writer, and Reviewer; cheap worker/provider documentation stays under `to-developer/`.
- 整理 `docs/` 用户侧入口，将开发者 ADR、迁移记录、LangGraph 评估和文档依赖维护规则迁入 `to-developer/`。
- 新增 `to-developer/20260615-FRAMEWORK_MODULES.md`，明确开发者侧框架模块边界，并约束 `to-developer/20260613-DEVELOPMENT_LOG.md` 的模块记录方式。
- 新增 `to-developer/20260617-FRAMEWORK_TOP_LEVEL_DESIGN.md`，作为人和 agent 共用的全局开发地图，统一说明 Labline 顶层分层、模块接口、重要性分级、当前缺口和开发路线图，并加入 `AGENTS.md` 必读列表。
- 将 `to-developer/` 下的 `.md` / `.txt` 开发者文档统一改为 `YYYYMMDD-` 创建日期前缀，并同步 DAG、引用、release gate 和测试路径。
- 新增 `to-developer/plans/20260616-CLI_DEPLOY_RUNTIME.md`，面向开发者详细说明 Labline CLI、Project Registry、framework update/check/rollback、容器 shell hook 和部署拓扑的机制与测试契约。
- 新增 `to-developer/plans/20260616-CHEAP_WORKER_DEFAULT_DIVISION.md`，说明开发侧默认由 Codex/leader 收口、gpt-5.4-mini 或命名 cheap worker provider 负责批量文档、扫引用、测试草案与低风险 patch 草案，并要求所有 worker 输出可追踪。
- 新增 `to-developer/plans/20260617-MULTI_PROVIDER_AGENT_FRAMEWORK_SPIKE.md` 和 `to-developer/plans/20260617-DEV_AGENT_SURFACE_PRD.md`，将 cheap worker 从 `dev rt` 远端 LLM 调用器重新定性为 dev-only 本地 coding agent surface；短期优先 OpenCode，Aider 作为 fallback，LangGraph/OpenClaw/Cline SDK/OpenHands SDK 进入中长期路线。
- 新增 `to-developer/realtest/20260616-REALTEST_CONTAINER.md` 和 dev-only 实机测试容器资产，用于新功能在独立容器中做带日志的 smoke/integration 测试。
- 新增 dev-only 开发者文档 DAG：`to-developer/DOC_DAG.yaml` / `to-developer/DOC_DAG.mmd`，用于统一维护开发计划、日志、讨论记录和 stable handoff 目标之间的更新关系。
- 新增 `docs/EXPERIMENT_TRANSPARENCY_LEDGER.md`，将 Experiment Integrity 定性为贯穿 plan/execution/audit/claim 的 workflow module，并定义 dataset/split/metric/run/deviation/artifact/claim/checkpoint 最小 ledger record 类型；同步到 shared references 和 docs 索引。
- Added Feishu integration docs and ADRs for opt-in remote control, live TUI takeover, and Feishu-priority control leases.
- Added ADR-0002 and `to-developer/plans/20260613-AGENT_STATUS_STREAM.md` for the status-stream architecture and rollout plan.
- Added local GPU validation report under `to-developer/logs/`.
- 新增 `to-developer/plans/20260613-LANGGRAPH_EVALUATION.md`。
- Added `docs/README.md` and `mcp-servers/README.md` indexes.
- Updated repository paths and removed obsolete ARIS-Code/Matt Pocock/image assets.
- Added `CONTEXT.md` language for framework version governance.
- Added `to-developer/plans/20260613-VERSION_MANAGEMENT.md`.

### deploy
- 新增预构建镜像部署路径：`deploy/docker-compose.image.yaml` 和 `deploy/docker-compose.gpu.image.yaml` 只使用已构建镜像，目标服务器不再现场 build；`.env` 示例补充 `LABLINE_IMAGE`、`LABLINE_IMAGE_USERNAME`、`LABLINE_GPU_IMAGE` 与 `GITEA_URL`。
- 新增 `deploy/IMAGE_PACKAGING.md`，说明普通/GPU 镜像的构建、推送、离线 tar 包导入、预构建部署和版本回滚边界；`deploy/DEPLOY_GUIDE.md` 增加从现场 build 到预构建 image compose 的入口。
- 更新部署文档和 `.env` 示例，补齐 Feishu bridge/session runner 部署、git proxy、大小写 proxy 环境变量一致性说明。
- 加固 `deploy/entrypoint.sh`，将大小写 proxy 变量和可选 git proxy 配置持久化到 `docker exec` 会话。
- Hardened GPU server deployment flow, including 3090x2 deployment assumptions and Docker guidance.

### mcp-servers
- Extended `mcp-servers/feishu-bridge/` with `/update`, `/control/*`, Feishu long-connection inbound routing, and configurable receive ID types.
- Documented MCP bridge inventory and provider requirements.
- Made Codex review bridge portable across local paths.
- Fixed `mcp-servers/codex-image2/server.py` so binary stdio wrapping happens only in MCP server `main()` instead of at import time, keeping pytest/module imports from corrupting stdout capture.

### tests
- Added User Skill DAG and Codex mirror contract tests requiring the runtime-task-protocol shared reference/skill and formal runtime-protocol edges for Leader, Planner, Coder, Deployer, Writer, and Reviewer.
- Extended Runtime Core tests to cover task-resolution folding: superseded old tasks and terminal Leader decisions no longer count as active critical status, and stale escalation files for resolved task ids are ignored by `wakeup-plan`.
- Extended Remote Observation and bridge patch tests to require visible progress-card patch delivery, bridge-owned projection `message_id` recording, current-project cross-profile projection polling, and auto-wakeup non-healthy skip/needs-confirmation notices.
- Extended bridge patch tests to require markdown-stream `completeTerminal()` usage, final markdown reply wrapping, configurable post-done cleanup grace, and idempotency, covering the case where a run completes internally but the visible Feishu streaming message remains on a running state.
- Extended Runtime Core tests to cover forced auto-wakeup retries: `wakeup-plan --force` returns an actionable plan for an already-started `wakeup_key`, and `wakeup --force` writes `wakeup.retry_requested` plus a second same-key `wakeup.started` while non-force dedupe remains unchanged.
- Extended bridge patch and Runtime Core tests to cover `LABLINE_AGENT_*_PROXY` injection into Codex bridge child processes and `native-codex` wakeup subprocesses.
- Added bridge patch coverage requiring auto-wakeup result delivery to prefer card payloads, keep markdown fallback, and avoid legacy English `task/title/wakeup/action` field labels.
- Extended bridge patch tests to require Chinese-first Remote Observation projection labels and to reject legacy `target:` / `reason:` / `status:` projection templates.
- Extended Remote Observation and bridge patch tests to cover once-only `stale_projection` fresh replies for active Feishu card states that exceed expected-update grace, plus bridge-side stale hint rendering and delivery reason recording.
- Extended bridge patch tests to cover ordinary run-stream resilience: hanging card flushes are timeout-wrapped and terminal stream grace expiry triggers a fallback final reply.
- Extended bridge patch tests to cover ordinary streaming-card continuation injection and idempotency.
- Extended bridge patch tests to require real card patch/drain waits, card continuation health-probe configuration, and latest-state fallback on early stream failure.
- Extended bridge patch tests to require auto-wakeup loop injection, environment gating, lifecycle cleanup, and `workflow wakeup-plan` / `workflow wakeup` command wiring.
- Extended Runtime Core tests to cover `lane workflow wakeup --backend native-codex` with a fake Codex CLI, including successful `wakeup.completed`, failing `wakeup.failed`, artifact recording, command prompt passing, and `leader_session` lease release.
- Extended Runtime Core tests to cover `lane workflow wakeup` apply behavior: `leader_session` lease acquisition, sanitized Leader prompt generation, `wakeup.started` event writes, duplicate `wakeup_key` suppression after restart, heartbeat-escalation compatibility, and `wakeup.skipped` records for lease conflicts.
- Extended Runtime Core tests to cover `lane workflow wakeup-plan` for blocked escalation candidates, active `leader_session` lease conflicts, healthy running tasks, and high-risk pending control intents without runtime writes.
- Extended Remote Observation and bridge patch tests to cover bridge-side `projection-poll`, once-only urgent fresh replies for the same state signature, poller injection, and disconnect cleanup.
- Extended `tests/test_lark_channel_bridge_labline_patch.py` to require `/rename` command injection, help text, handler wiring, and Codex `thread/name/set` usage in the bridge patcher.
- Extended `tests/test_lark_channel_bridge_labline_patch.py` to require `/fork` command injection, help text, Codex `thread/fork`, and optional `thread/name/set` wiring in the bridge patcher.
- Extended `tests/test_lark_channel_bridge_labline_patch.py` with Codex `item.updated` translator patch coverage and idempotency checks.
- Extended `tests/test_lark_channel_bridge_labline_patch.py` with channel bundle patch anchors for the `LARK_CHANNEL_ALLOW_EMPTY_BOT_ID` fallback and idempotency.
- Added `tests/test_developer_doc_dag.py` as a pytest anchor for dev-only documentation DAG validation, generated Mermaid freshness, and uncovered developer-document detection.
- Extended GPU deployment contract tests to require the 3090 exposed-port smoke path in `deploy/DEPLOY_GUIDE.md`.
- Extended `tests/test_lane_debug_runtime_smoke.py` to cover `lane debug longtask-smoke` copy mode, detached local job execution, running heartbeat health, terminal escalation, and source-project non-mutation.
- Added `tests/test_lane_debug_runtime_smoke.py` to cover copy-mode source-project safety and `--in-place --yes` gating for the local debug runtime smoke command.
- Added Phase 9 release gate smoke tests for new-project root `PIPELINE_STATE.json` avoidance, runtime CLI entrypoints, Feishu projection identity/text isolation, and stable user docs coverage.
- Extended Remote Observation tests to cover Phase 8 routing: status questions route to observation without TUI injection, side questions keep a continuous bridge-owned BTW thread, stop requests become high-risk control intents, new work routes to normal project interaction, and BTW answers emit sanitized runtime events.
- Added Remote Observation contract tests for bridge-owned archive/follow state, project runtime identity-leak prevention, stable delivery-key dedupe, progress throttling, terminal fresh replies, and delivery-failure isolation from task verdicts.
- Extended runtime adapter tests to cover agent status runtime-default writes plus legacy reads, watchdog anomaly mirroring into runtime event/escalation files, experiment queue runtime mirroring, and `lane status --brief` surfacing queue/watchdog source summaries.
- Extended Runtime Core tests to cover `lane heartbeat` healthy due checks, terminal escalation, lease-conflict skip behavior, and dry-run explicit task checks without runtime writes.
- Extended Runtime Core tests to cover lease acquisition, active lease conflict, expired lease stealing, owner-checked release, read-only status without lease, and bridge-safe `control_intent.submitted` events.
- Extended Runtime Core tests to cover explicit Runtime Task creation, terminal updates, capability consistency failures, heartbeat due-time validation, and explicit task inclusion in status summaries.
- Extended Runtime Core tests to cover `lane status` aggregation, derived `summaries/current.*`, legacy `.labline/status/agents` compatibility, and human-readable brief output.
- Added Runtime Core tests for runtime root initialization, idempotent directory creation, append-only event JSONL writes, and invalid event payload rejection.
- Added dev runtime CLI, dev skill installer, and dev skill surface tests covering `aris dev rt/runtime`, `aris dev skills`, dev-only catalog/DAG generation, and legacy `aris dev worker` rejection.
- Updated Worker harness contract tests to assert dev-only worker configuration remains available while user-facing skills, docs, and Leader dispatch do not expose Worker as a project role.
- 扩展 GPU 部署合约测试，覆盖 `.env` 示例、compose 环境变量、entrypoint proxy/git proxy 持久化。
- 新增开发者文档 DAG 回归测试。
- 新增实机测试容器 contract test，确保 dev-only realtest 资产保持独立路径、日志 mount 和默认 smoke 行为。
- Added Feishu bridge/control/session tests covering card update semantics, queue ack behavior, live TUI status updates, `/interrupt`, and `/btw`.
- Added Agent Status Stream CLI behavior tests and local GPU smoke validation.
- Updated release tooling tests to use the current Python executable in direct-run mode.
- Added skill DAG contract tests.
- Added Codex review bridge path resolution test.
- Added release tooling tests.
- Ran catalog, DAG, mirror, bridge, and py_compile checks during stabilization.

### compatibility / migration
- Set `main` as stable, `dev` as integration, and `upstream-base` as old baseline backup.
- Switched Git remote push path to HTTPS after GitHub SSH transport failed in this environment.
- Restored `to-developer/` developer material into the dev worktree and ignored private settings/SSH notes.

### breaking / requires user action
- Projects should pin formal release tags after `v0.1.0`; prerelease tags are for deliberate testing only.
