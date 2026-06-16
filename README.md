# ARIS — Auto Research In Sleep

> 让 AI 在你睡觉时做科研。醒来发现论文已写好、实验已跑完、审稿意见已回复。

ARIS 是一套面向 Codex CLI 的自动化科研框架，并兼容 Claude Code。当前主线包含 **94 个用户可调用 skill**，覆盖文献调研、实验规划、代码实现、GPU 部署、论文写作、审稿回复、专利和项目同步。

## 核心特性

**三边架构** — Leader（规划与 gate）+ Coder / Deployer / Writer（执行子职责）+ Reviewer（独立审查），用角色隔离减少自我确认偏差。

**Codex-first 双客户端轨道** — Codex CLI 使用 `$skill-name` 作为默认入口；Claude Code 兼容模式使用 `/skill-name`。项目模板同时提供 `AGENTS.md` 和 `CLAUDE.md`。

**项目分离** — 框架目录只放 `skills/`、`tools/`、`templates/`、`mcp-servers/`；科研项目目录只放代码、数据、论文、结果。详见 [docs/FRAMEWORK_STRUCTURE.md](docs/FRAMEWORK_STRUCTURE.md)。

**轻量安装** — 安装器用 symlink 接入框架，多个项目共享一套框架，框架更新自动传播。

**可部署** — 支持本地、SSH GPU 服务器、Docker 多人环境、Vast.ai、Modal、Overleaf、飞书通知等工作流。

## 快速开始

```bash
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git [你的framework位置]
cd /path/to/your/project
bash [你的framework位置]/tools/aris project init . --direction "你的研究方向"
```

更多步骤见 [QUICK_START.md](QUICK_START.md)。服务器部署见 [deploy/DEPLOY_GUIDE.md](deploy/DEPLOY_GUIDE.md)。

## 项目结构

```text
aris-framework/
├── skills/              # 94 个用户 skill + Codex/Claude Code overlay
├── templates/           # 项目、实验、论文、专利、配置模板
├── tools/               # 安装、同步、检索、实验队列、审计工具
├── mcp-servers/         # Claude/Codex/Gemini/MiniMax/Feishu MCP 或桥接服务
├── deploy/              # Docker / GPU 服务器部署配置
├── docs/                # 操作、适配、架构、catalog、DAG 文档
├── tests/               # 回归测试
├── QUICK_START.md
└── README.md
```

## Skill 一览

完整 skill 目录由脚本生成：

- [docs/SKILL_CATALOG.md](docs/SKILL_CATALOG.md)
- [docs/SKILL_CATALOG_CN.md](docs/SKILL_CATALOG_CN.md)

常用入口：

| 场景 | Skill |
|------|-------|
| 总编排 | `$leader`, `$research-pipeline`, `$init-research` |
| 文献/想法 | `$research-lit`, `$idea-discovery`, `$novelty-check` |
| 实验 | `$experiment-plan`, `$experiment-bridge`, `$run-experiment`, `$experiment-queue` |
| 论文 | `$paper-writing`, `$paper-plan`, `$paper-write`, `$paper-figure`, `$paper-compile` |
| 审查 | `$review`, `$research-review`, `$experiment-audit`, `$paper-claim-audit`, `$citation-audit` |
| 同步/部署 | `$sync`, `$framework-update`, `$deployer`, `$vast-gpu`, `$serverless-modal` |
| 执行角色 | `$coder`, `$deployer`, `$writer` |
| 开发辅助 | `$tdd`, `$diagnose`, `$caveman`, `$handoff` |

## 功能目录索引

### 文档

| 路径 | 内容 |
|------|------|
| [docs/README.md](docs/README.md) | 用户文档索引 |
| [docs/FRAMEWORK_STRUCTURE.md](docs/FRAMEWORK_STRUCTURE.md) | 框架/项目边界 |
| [docs/OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md) | 日常操作手册 |
| [docs/TRIPARTITE_ARCHITECTURE_GUIDE.md](docs/TRIPARTITE_ARCHITECTURE_GUIDE.md) | 三边架构 |
| [docs/FEISHU_INTEGRATION.md](docs/FEISHU_INTEGRATION.md) | 飞书通知、双向消息、受控 Codex runner |
| [deploy/DEPLOY_GUIDE.md](deploy/DEPLOY_GUIDE.md) | Docker / 服务器部署 |
| [AGENT_GUIDE.md](AGENT_GUIDE.md) | AI Agent 阅读指南 |

### MCP / 桥接服务

| 路径 | 功能 |
|------|------|
| [mcp-servers/README.md](mcp-servers/README.md) | MCP 服务索引 |
| `mcp-servers/claude-review/` | Claude reviewer bridge |
| `mcp-servers/codex-review/` | Codex/OpenAI-compatible reviewer bridge |
| `mcp-servers/gemini-review/` | Gemini reviewer bridge |
| `mcp-servers/llm-chat/` | 通用 OpenAI-compatible chat MCP |
| `mcp-servers/minimax-chat/` | MiniMax chat MCP |
| `mcp-servers/feishu-bridge/` | 飞书 HTTP 通知/回复桥 |
| [docs/FEISHU_INTEGRATION.md](docs/FEISHU_INTEGRATION.md) | 飞书双向接入文档 |
| `mcp-servers/codex-image2/` | Codex app-server 图像生成桥 |

### 模板

| 路径 | 功能 |
|------|------|
| [templates/README.md](templates/README.md) | 模板全量索引 |
| `templates/AGENTS_MD_TEMPLATE.md` | Codex 项目指令模板 |
| `templates/CLAUDE_MD_TEMPLATE.md` | Claude Code 项目状态模板 |
| `templates/project.yaml.tmpl` | ARIS 项目元数据模板 |
| `templates/api-config.yaml.tmpl` | API provider 配置模板 |
| `templates/EXPERIMENT_*` | 实验计划/日志/预期声明模板 |
| `templates/RESEARCH_*`, `templates/IDEA_*` | 研究简报、contract、idea 候选池 |
| `templates/PAPER_PLAN_TEMPLATE.md`, `templates/NARRATIVE_REPORT_TEMPLATE.md` | 论文写作输入 |
| `templates/PATENT_*`, `templates/INVENTION_BRIEF_TEMPLATE.md` | 专利 pipeline 输入 |

### 工具

| 路径 | 功能 |
|------|------|
| `tools/aris` | 新手 CLI：`project init/doctor/update/detach`，`framework check-update/update/rollback` |
| `tools/install_aris.sh`, `tools/install_aris.ps1` | 安装 Claude Code 兼容 skills 到项目 |
| `tools/install_aris_codex.sh` | Codex-only 安装器 |
| `tools/smart_update.sh`, `tools/smart_update_codex.sh`, `tools/smart_update.ps1` | 框架更新/重建 symlink |
| `tools/sync.sh` | git + 远程部署同步 |
| `tools/watchdog.py` | 实验 watchdog |
| `tools/aris_feishu_session.py` | 飞书 inbox 驱动的受控 Codex Session runner |
| `tools/experiment_queue/` | SSH 多 GPU 实验队列 |
| `tools/arxiv_fetch.py`, `tools/semantic_scholar_fetch.py`, `tools/openalex_fetch.py`, `tools/deepxiv_fetch.py`, `tools/exa_search.py` | 论文/网页检索 |
| `tools/research_wiki.py` | 研究知识库 |
| `tools/generate_skill_catalog.py`, `tools/translate_skill_catalog.py`, `tools/generate_skill_dag.py` | skill catalog / DAG 生成 |
| `tools/figure_renderer.py`, `tools/extract_paper_style.py`, `tools/paper_illustration_image2.py` | 图表/论文视觉辅助 |
| `tools/overleaf_setup.sh`, `tools/overleaf_audit.sh` | Overleaf 同步审计 |
| `tools/verify_paper_audits.sh`, `tools/verify_wiki_coverage.sh`, `tools/save_trace.sh` | 审计和 trace 辅助 |
| `tools/meta_opt/` | meta optimization hook 辅助 |

## 客户端兼容

| 客户端 | 支持度 | 说明 |
|--------|--------|------|
| Codex CLI | 默认 | 使用 `$skill-name`；读取 `AGENTS.md` 和 `.agents/skills/` |
| Claude Code | 兼容 | 使用 `/skill-name`；读取 `CLAUDE.md` 和 `.claude/skills/` |
| Cursor | 部分 | 见 [docs/CURSOR_ADAPTATION.md](docs/CURSOR_ADAPTATION.md) |
| Trae | 部分 | 见 [docs/TRAE_ARIS_RUNBOOK_CN.md](docs/TRAE_ARIS_RUNBOOK_CN.md) |
| Antigravity / OpenClaw / ModelScope | 部分 | 见 `docs/*ADAPTATION*` 与 [docs/MODELSCOPE_GUIDE.md](docs/MODELSCOPE_GUIDE.md) |

## 维护

新增/删除 skill 后运行：

```bash
python3 tools/generate_skill_catalog.py
python3 tools/translate_skill_catalog.py
```

Stable 用户文档索引见 [docs/README.md](docs/README.md)。开发者侧计划、讨论、DAG 和维护规则只保留在 dev checkout。

## 致谢

基于 [wanshuiyin/Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) 上游项目。

## License

MIT
