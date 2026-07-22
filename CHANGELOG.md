# Changelog

All notable changes to the Labline framework.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- `lane project migrate-aris` can dry-run and apply migration of legacy ARIS project state, old framework symlinks, and `project.yaml` framework metadata.
- Auto-wakeup now creates `expected_update_due` candidates for waiting or recovery tasks when their declared check time arrives.

### Changed
- Feishu/Lark integration docs now explain `--home`, `--profile`, `--workspace`, tmux operation, and multi-user/multi-project usage.
- Deployment docs and compose examples now standardize on HTTP/HTTPS proxy variables without `ALL_PROXY/all_proxy`, default Labline researcher containers to host networking, and route API provider setup through `cc-switch-cli` instead of prefilled API keys.

### Fixed
- `lane feishu` now reports a clear install hint when `lark-channel-bridge` is missing, and status-style bridge commands no longer pass workspace-only arguments.
- Repeated `wakeup_already_started` checks are log-only by default instead of sending a visible Feishu message every poll cycle.

---

## [v0.3.3] - 2026-06-16

### Fixed
- Feishu-controlled sessions now send status cards and final replies back to the actual message sender instead of relying on a fixed configured recipient.
- Feishu session state writes are now atomic, reducing transient failures when the bridge and runner access session state concurrently.

---

## [v0.3.2] - 2026-06-16

### Changed
- Leader readiness checks are now Codex-first and no longer require Claude Code `settings.local.json` permission allowlists by default.

---

## [v0.3.1] - 2026-06-16

### Fixed
- `lane framework --version` is now read-only and no longer tries to create framework rollback history.
- Framework-level CLI state now defaults to the user's `~/.labline` directory unless `LABLINE_WORKSPACE` is explicitly set.
- Docker deployments now persist Labline state under each container user's home directory instead of requiring `/lane/.labline`.

---

## [v0.3.0] - 2026-06-16

### Added
- Labline beginner CLI under `tools/lane` with `project` and `framework` namespaces.
- `lane project init PATH --direction "..."` for current-directory initialization, path-based project creation, and attaching Labline to existing projects without overwriting user files.
- `lane project doctor`, `lane project update`, `lane project detach`, and project/framework version inspection commands.
- User workspace Project Registry for syncing registered projects after framework updates.
- Non-destructive `lane framework check-update` with cached daily notification support for shell/tmux sessions.
- Per-user Docker workspace topology: each researcher gets an isolated framework copy, projects directory, and Labline state directory while sharing datasets, pretrained models, and download cache.
- `cc-switch-cli` is preinstalled in container images for provider management.
- Detailed user/admin operation guide split in `docs/OPERATIONS_GUIDE.md`.
- Feishu control bridge and managed Codex runner for opt-in remote session input, live tmux takeover, status-card updates, `/interrupt`, and side-channel `/btw` questions.
- Feishu integration documentation, ADRs, and a `feishu-session` skill describing setup, safety boundaries, and operation.
- 文档依赖 DAG：`docs/DOC_DAG.yaml`、`docs/DOC_DAG.mmd` 和 `tools/generate_doc_dag.py`，用于新增/修改文档时做影响分析。
- 中文 `tools/` 全量索引文档 `docs/TOOLS_INDEX.md`，汇总安装、发布、Feishu、实验、检索、审计、生成器和维护脚本。
- Stable-readable Chinese promote specification in `docs/PROMOTE_FLOW.md` and root `AGENTS.md` guidance for Codex/developers.

### Changed
- Labline documentation is now Codex-first while preserving Claude Code compatibility.
- `README.md`, `QUICK_START.md`, deployment docs, and project templates now use `lane project ...` / `lane framework ...` commands.
- Tripartite architecture docs now describe one Codex leader session, local delegated agents, Executor sub-roles Coder/Deployer/Writer, and local independent Reviewer.
- Framework updates are explicit user actions; container startup and shell/tmux entry only check and notify.
- Promote 文档纳入已有 release、tag、install、smart update 工具，避免 Codex 手写临时发布流程。
- Feishu status cards now update in place with minimal state and elapsed time instead of sending repeated acknowledgement cards.

### Fixed
- Deployment guides no longer assume hard-coded `/data`, `/opt/lane-framework`, or shared framework named-volume layouts.
- Container entrypoint no longer performs silent `git pull` on framework startup.
- Stable-facing docs no longer directly depend on dev-only `to-developer/` paths.
- Feishu bridge now supports card patch updates and disables noisy queue acknowledgements by default.
- Stable framework no longer tracks dev-only `to-developer/` materials; release checks rely on `CHANGELOG.md` for stable readiness.

### Removed
- Legacy short CLI commands `lane init`, `lane update`, `lane doctor`, and `lane detach` are intentionally unsupported.

---

## [v0.2.0] - 2026-06-13

### Added
- Agent Status Stream: project-local per-agent status snapshots under `.labline/status/` so Leader can observe running Coder, Deployer, Writer, and Reviewer roles without reading full transcripts.
- `tools/agent_status.py` CLI with `start`, `update`, `finish`, `list`, `summary`, and `validate` commands.
- Shared Agent Status Stream protocol and role guidance for long-running job handles, expected update timing, read-only status checks, and reviewer transport metadata.
- Maintainer validation report for local GPU smoke testing on the 3090x2 development container.

### Changed
- Leader, Coder, Deployer, Writer, templates, and reviewer-independence guidance now reference the Agent Status Stream protocol.
- Release tag tooling now uses `${PYTHON:-python3}` instead of assuming `python3.8` is installed.

### Fixed
- `.labline/status/` is ignored as project-local runtime state and should not be committed.

---

## [v0.1.0] - 2026-06-13

### Added
- Codex and Claude Code dual-client framework baseline with 94 user-facing skills.
- Dev/stable branch structure with `main` as stable and `dev` as integration.
- Skill DAG normalization with frontmatter `invokes` as formal edges and body mentions as inferred references.
- Codex skill mirrors for newly added skills.
- LangGraph evaluation document for future optional orchestration backend decisions.
- Portable MCP server index and Codex review bridge path handling.
- Development log and guarded release tooling plan for Labline version management.
- Framework version recording in `install_labline.sh` (`record_framework_version`)
- `project.yaml` template fields: `framework.version`, `framework.commit`, `overrides` registry
- `docs/FRAMEWORK_STRUCTURE.md` — framework/project/dev boundary contract
- Four top-level buckets: `examples/`, `compat/`, `incubating/`, `legacy/`
- Regression tests for framework version recording (`tests/test_install_labline_version_record.py`)
- `--dev` flag in `install_labline.sh` to use lane-dev/ repo instead of stable
- `--Codex` platform switching tests (`tests/test_install_labline_codex_flag.py`)
- Manifest safety tests (`tests/test_install_labline_manifest_safety.py`)
- `--reconcile` synchronization tests (`tests/test_install_labline_reconcile.py`)

### Changed
- README and documentation index now describe the current Labline framework layout and dual-client usage.
- Documentation paths were updated from the upstream Claude-only project to the current Labline repository.
- Templates and installer path discovery were generalized to avoid hard-coded user/server paths.
- `install_labline.sh`: refactored dead `$DRY_RUN` branch in uninstall cleanup
- `templates/CLAUDE_MD_TEMPLATE.md` and `AGENTS_MD_TEMPLATE.md`: added Project Overrides section
- `README.md`: referenced framework structure docs
- `QUICK_START.md`: added framework version recording step

### Fixed
- GPU server deployment hardening for the 3090x2 deployment path.
- Python 3.8 compatibility in selected tools/tests.
- Codex review bridge no longer hard-codes a developer-local server path.

### Removed
- Obsolete Labline-Code README variants and old README image assets.

---

## [2026-06-10]

### Added
- `examples/`, `compat/`, `incubating/`, `legacy/` directories with READMEs
- Version pin and overrides registry in project template

---

## [2026-06-08]

### Added
- Codex migration artifacts (`.agents/skills/`, `AGENTS.md`)
- `test_install_labline_tools_symlink.py` regression tests (#174)

### Fixed
- Symlink handling edge cases in `install_labline.sh`

---

## [2026-06-07]

### Added
- `examples` field added to all 94 SKILL.md files
- SKILL_DAG integration — HTML visualization + impact analysis + workflow
- Cytoscape.js DAG visualization with Apple-style redesign
- D3.js DAG as alternative renderer

---

## [2026-06-06]

### Added
- Executor role split — Coder/Deployer/Writer
- Bilingual UI support

---

## [2026-06-05]

### Fixed
- Cytoscape DAG — add dagre dependency, fix init

### Changed
- Replaced external symlinks with real skill directories

---

## [2026-06-04]

### Added
- Skill layering: agent-guide, caller fields, DAG

---

## [2026-06-03]

### Added
- Agent constraints added to all docs
- GPU deployment guide for 3090x2 server

---

## [2026-06-02]

### Added
- `executor-blocked-protocol.md`
- GPU Dockerfile
- Leader SKILL.md update

### Changed
- Generalized OPERATIONS_GUIDE — removed hardcoded server names and SSH config

---

## [2026-06-01]

### Added
- Labline framework v1 — docs, deployment, skill catalog, mattpocock skills
- `/paper-talk` + `/slides-polish` skills

---

## [Earlier]

See `git log --oneline` for full history prior to 2026-06-01.
