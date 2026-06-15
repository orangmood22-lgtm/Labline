# ARIS Development Log

开发者侧按模块记录的 ARIS 框架开发日志。模块边界见 `to-developer/FRAMEWORK_MODULES.md`；用户可见部分在发布前再蒸馏到 `CHANGELOG.md`。

## [Unreleased]

### skills
- Added `skills/feishu-session/` for operating the Feishu-controlled Codex session bridge and runner.
- Added Agent Status Stream protocol and wired Leader/Coder/Deployer/Writer role instructions to project-local status snapshots.
- Updated reviewer-independence guidance so Reviewer status may carry transport/input-scope metadata without carrying review reasoning or executor summaries.
- Normalized skill DAG governance so formal edges come only from frontmatter `invokes`.
- Added `platform`, `status`, and dependency metadata to key Codex/Claude dual-client skills.
- Added Codex mirrors for the newly added skill set.
- Enhanced `skills-codex-claude-review` overlays with reviewer bias guard, edit whitelist, reviewer memory, debate protocol, and broader venue support.

### tools
- 新增 `tools/update_developer_docs.py`，用于校验 dev-only 文档覆盖并重新生成 `to-developer/DOC_DAG.mmd`。
- Added `tools/feishu_control.py` for session registration, inbox routing, control leases, approvals, `/interrupt`, and `/btw`.
- Added `tools/aris_feishu_session.py` for managed `codex exec` sessions and live tmux injection with Feishu status-card updates.
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
- 整理 `docs/` 用户侧入口，将开发者 ADR、迁移记录、LangGraph 评估和文档依赖维护规则迁入 `to-developer/`。
- 新增 `to-developer/FRAMEWORK_MODULES.md`，明确开发者侧框架模块边界，并约束 `DEVELOPMENT_LOG.md` 的模块记录方式。
- 新增 dev-only 开发者文档 DAG：`to-developer/DOC_DAG.yaml` / `to-developer/DOC_DAG.mmd`，用于统一维护开发计划、日志、讨论记录和 stable handoff 目标之间的更新关系。
- Added Feishu integration docs and ADRs for opt-in remote control, live TUI takeover, and Feishu-priority control leases.
- Added ADR-0002 and `to-developer/plans/AGENT_STATUS_STREAM.md` for the status-stream architecture and rollout plan.
- Added local GPU validation report under `to-developer/logs/`.
- 新增 `to-developer/plans/LANGGRAPH_EVALUATION.md`。
- Added `docs/README.md` and `mcp-servers/README.md` indexes.
- Updated repository paths and removed obsolete ARIS-Code/Matt Pocock/image assets.
- Added `CONTEXT.md` language for framework version governance.
- Added `to-developer/plans/VERSION_MANAGEMENT.md`.

### deploy
- 更新部署文档和 `.env` 示例，补齐 Feishu bridge/session runner 部署、git proxy、大小写 proxy 环境变量一致性说明。
- 加固 `deploy/entrypoint.sh`，将大小写 proxy 变量和可选 git proxy 配置持久化到 `docker exec` 会话。
- Hardened GPU server deployment flow, including 3090x2 deployment assumptions and Docker guidance.

### mcp-servers
- Extended `mcp-servers/feishu-bridge/` with `/update`, `/control/*`, Feishu long-connection inbound routing, and configurable receive ID types.
- Documented MCP bridge inventory and provider requirements.
- Made Codex review bridge portable across local paths.

### tests
- 新增开发者文档 DAG 回归测试。
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
