# Labline 用户文档索引

`docs/` 只放用户安装、配置、运行和使用 Labline 时需要看的文档。开发计划、ADR、迁移记录、评估材料和文档维护规则放在 `to-developer/`。

## 入门和日常使用

| 文档 | 用途 |
|------|------|
| [FRAMEWORK_STRUCTURE.md](FRAMEWORK_STRUCTURE.md) | 理解 framework / project / dev 边界 |
| [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) | 日常操作、API 配置、workflow 使用 |
| [TOOLS_INDEX.md](TOOLS_INDEX.md) | 常用 `lane` 命令和稳定工具入口 |
| [TRIPARTITE_ARCHITECTURE_GUIDE.md](TRIPARTITE_ARCHITECTURE_GUIDE.md) | Leader / Executor / Reviewer 三边协作 |
| [FEISHU_INTEGRATION.md](FEISHU_INTEGRATION.md) | 飞书/Lark 远控：默认 `lark-channel-bridge`，旧版 Labline runner fallback |

## 项目文件和恢复

| 文档 | 用途 |
|------|------|
| [PROJECT_FILES_GUIDE.md](PROJECT_FILES_GUIDE.md) | 项目文件布局 |
| [PROJECT_FILES_GUIDE_CN.md](PROJECT_FILES_GUIDE_CN.md) | 项目文件布局中文版 |
| [EXPERIMENT_TRANSPARENCY_LEDGER.md](EXPERIMENT_TRANSPARENCY_LEDGER.md) | 实验透明度 ledger 契约：数据、split、metric、run、artifact、claim、checkpoint 追踪 |
| [SESSION_RECOVERY_GUIDE.md](SESSION_RECOVERY_GUIDE.md) | 会话恢复协议 |
| [SESSION_RECOVERY_GUIDE_CN.md](SESSION_RECOVERY_GUIDE_CN.md) | 会话恢复协议中文版 |
| [WATCHDOG_GUIDE.md](WATCHDOG_GUIDE.md) | watchdog 使用 |
| [WATCHDOG_GUIDE_CN.md](WATCHDOG_GUIDE_CN.md) | watchdog 中文版 |
| [NARRATIVE_REPORT_EXAMPLE.md](NARRATIVE_REPORT_EXAMPLE.md) | 论文叙事报告示例 |

## Skill 目录

| 文档 | 用途 |
|------|------|
| [SKILL_CATALOG.md](SKILL_CATALOG.md) | 自动生成的 skill 目录 |
| [SKILL_CATALOG_CN.md](SKILL_CATALOG_CN.md) | 自动生成的中文 skill 目录 |
| [SKILL_DAG.yaml](SKILL_DAG.yaml) | 自动生成的 skill 依赖图源数据 |
| [SKILL_DAG.mmd](SKILL_DAG.mmd) | Mermaid skill 依赖图 |
| [skill-dag.html](skill-dag.html) | 浏览器版 skill 依赖图 |

## Reviewer / API 桥接

| 文档 | 用途 |
|------|------|
| [CODEX_CLAUDE_REVIEW_GUIDE.md](CODEX_CLAUDE_REVIEW_GUIDE.md) | Codex 调 Claude reviewer |
| [CODEX_CLAUDE_REVIEW_GUIDE_CN.md](CODEX_CLAUDE_REVIEW_GUIDE_CN.md) | Codex 调 Claude reviewer 中文版 |
| [CODEX_GEMINI_REVIEW_GUIDE.md](CODEX_GEMINI_REVIEW_GUIDE.md) | Codex 调 Gemini reviewer |
| [CODEX_GEMINI_REVIEW_GUIDE_CN.md](CODEX_GEMINI_REVIEW_GUIDE_CN.md) | Codex 调 Gemini reviewer 中文版 |
| [MINIMAX_MCP_GUIDE.md](MINIMAX_MCP_GUIDE.md) | MiniMax MCP 配置 |
| [MiniMax-GLM-Configuration.md](MiniMax-GLM-Configuration.md) | MiniMax + GLM 配置 |
| [LLM_API_MIX_MATCH_GUIDE.md](LLM_API_MIX_MATCH_GUIDE.md) | 多 provider 混用 |
| [MODELSCOPE_GUIDE.md](MODELSCOPE_GUIDE.md) | ModelScope 方案 |
| [ALI_CODING_PLAN_GUIDE.md](ALI_CODING_PLAN_GUIDE.md) | 阿里 Coding Plan 方案 |

## 客户端适配

| 文档 | 用途 |
|------|------|
| [CURSOR_ADAPTATION.md](CURSOR_ADAPTATION.md) | Cursor 适配 |
| [TRAE_LABLINE_RUNBOOK_CN.md](TRAE_LABLINE_RUNBOOK_CN.md) | Trae 中文 runbook |
| [TRAE_LABLINE_RUNBOOK_EN.md](TRAE_LABLINE_RUNBOOK_EN.md) | Trae English runbook |
| [ANTIGRAVITY_ADAPTATION.md](ANTIGRAVITY_ADAPTATION.md) | Antigravity 适配 |
| [ANTIGRAVITY_ADAPTATION_CN.md](ANTIGRAVITY_ADAPTATION_CN.md) | Antigravity 中文适配 |
| [OPENCLAW_ADAPTATION.md](OPENCLAW_ADAPTATION.md) | OpenClaw 适配 |

## 资源

| 文件 | 用途 |
|------|------|
| [labline_logo.svg](labline_logo.svg) | Labline logo |
