# Labline Development Log

开发者侧按模块记录的 Labline 框架开发日志。模块边界见 `to-developer/20260615-FRAMEWORK_MODULES.md`；用户可见部分在发布前再蒸馏到 `CHANGELOG.md`。

## [Unreleased]

### skills
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
