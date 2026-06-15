# ARIS Docs Index

此目录存放框架文档。新用户优先读根目录 [README.md](../README.md)、[QUICK_START.md](../QUICK_START.md)，再按问题进入下面文档。

## Core

| 文档 | 用途 |
|------|------|
| [FRAMEWORK_STRUCTURE.md](FRAMEWORK_STRUCTURE.md) | 框架目录和科研项目目录如何分离 |
| [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) | 常规使用、API 配置、workflow 操作 |
| [TRIPARTITE_ARCHITECTURE_GUIDE.md](TRIPARTITE_ARCHITECTURE_GUIDE.md) | Leader / Executor / Reviewer 三边协作 |
| [codex-migration.md](codex-migration.md) | Claude Code 到 Codex CLI 的迁移状态 |
| [DOC_DEPENDENCIES.md](DOC_DEPENDENCIES.md) | 改文档时需要同步更新哪些文件 |
| [LANGGRAPH_EVALUATION.md](LANGGRAPH_EVALUATION.md) | LangGraph 对 ARIS 的价值、边界和引入时机 |
| [FEISHU_INTEGRATION.md](FEISHU_INTEGRATION.md) | 飞书通知、长连接收消息、受控 Codex runner 接入 |

## Skill Catalog

| 文档 | 用途 |
|------|------|
| [SKILL_CATALOG.md](SKILL_CATALOG.md) | 自动生成的 skill 目录 |
| [SKILL_CATALOG_CN.md](SKILL_CATALOG_CN.md) | 自动生成的中文 skill 目录 |
| [SKILL_DAG.yaml](SKILL_DAG.yaml) | skill 依赖图源数据 |
| [SKILL_DAG.mmd](SKILL_DAG.mmd) | Mermaid 依赖图 |
| [skill-dag.html](skill-dag.html) | 浏览器版依赖图 |

## Project Files / Recovery

| 文档 | 用途 |
|------|------|
| [PROJECT_FILES_GUIDE.md](PROJECT_FILES_GUIDE.md) | 项目文件布局 |
| [PROJECT_FILES_GUIDE_CN.md](PROJECT_FILES_GUIDE_CN.md) | 项目文件布局中文版 |
| [SESSION_RECOVERY_GUIDE.md](SESSION_RECOVERY_GUIDE.md) | 会话恢复协议 |
| [SESSION_RECOVERY_GUIDE_CN.md](SESSION_RECOVERY_GUIDE_CN.md) | 会话恢复协议中文版 |
| [WATCHDOG_GUIDE.md](WATCHDOG_GUIDE.md) | watchdog 使用 |
| [WATCHDOG_GUIDE_CN.md](WATCHDOG_GUIDE_CN.md) | watchdog 中文版 |
| [NARRATIVE_REPORT_EXAMPLE.md](NARRATIVE_REPORT_EXAMPLE.md) | 论文叙事报告示例 |

## Reviewer / API Bridges

| 文档 | 用途 |
|------|------|
| [CODEX_CLAUDE_REVIEW_GUIDE.md](CODEX_CLAUDE_REVIEW_GUIDE.md) | Codex 调 Claude reviewer |
| [CODEX_CLAUDE_REVIEW_GUIDE_CN.md](CODEX_CLAUDE_REVIEW_GUIDE_CN.md) | 中文版 |
| [CODEX_GEMINI_REVIEW_GUIDE.md](CODEX_GEMINI_REVIEW_GUIDE.md) | Codex 调 Gemini reviewer |
| [CODEX_GEMINI_REVIEW_GUIDE_CN.md](CODEX_GEMINI_REVIEW_GUIDE_CN.md) | 中文版 |
| [MINIMAX_MCP_GUIDE.md](MINIMAX_MCP_GUIDE.md) | MiniMax MCP 配置 |
| [MiniMax-GLM-Configuration.md](MiniMax-GLM-Configuration.md) | MiniMax + GLM 配置 |
| [LLM_API_MIX_MATCH_GUIDE.md](LLM_API_MIX_MATCH_GUIDE.md) | 多 provider 混用 |
| [MODELSCOPE_GUIDE.md](MODELSCOPE_GUIDE.md) | ModelScope 方案 |
| [ALI_CODING_PLAN_GUIDE.md](ALI_CODING_PLAN_GUIDE.md) | 阿里 Coding Plan 方案 |
| [FEISHU_INTEGRATION.md](FEISHU_INTEGRATION.md) | Feishu/Lark 双向集成 |

## Client Adapters

| 文档 | 用途 |
|------|------|
| [CURSOR_ADAPTATION.md](CURSOR_ADAPTATION.md) | Cursor 适配 |
| [TRAE_ARIS_RUNBOOK_CN.md](TRAE_ARIS_RUNBOOK_CN.md) | Trae 中文 runbook |
| [TRAE_ARIS_RUNBOOK_EN.md](TRAE_ARIS_RUNBOOK_EN.md) | Trae English runbook |
| [ANTIGRAVITY_ADAPTATION.md](ANTIGRAVITY_ADAPTATION.md) | Antigravity 适配 |
| [ANTIGRAVITY_ADAPTATION_CN.md](ANTIGRAVITY_ADAPTATION_CN.md) | Antigravity 中文适配 |
| [OPENCLAW_ADAPTATION.md](OPENCLAW_ADAPTATION.md) | OpenClaw 适配 |

## ADR

| 文档 | 用途 |
|------|------|
| [adr/0001-model-tiering-strategy.md](adr/0001-model-tiering-strategy.md) | 模型分层策略 ADR |
| [adr/0002-agent-status-stream.md](adr/0002-agent-status-stream.md) | Agent Status Stream ADR |
| [adr/0003-feishu-control-uses-opt-in-codex-sessions.md](adr/0003-feishu-control-uses-opt-in-codex-sessions.md) | 飞书控制只接入 opt-in Codex Session |
| [adr/0004-feishu-control-lease-prioritizes-remote-input.md](adr/0004-feishu-control-lease-prioritizes-remote-input.md) | 飞书 Control Lease 优先级 |

## Assets

| 文件 | 用途 |
|------|------|
| [aris_logo.svg](aris_logo.svg) | ARIS logo |
