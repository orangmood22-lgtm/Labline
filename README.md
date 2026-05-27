# ARIS — Auto Research In Sleep

> 让 AI 在你睡觉时做科研。醒来发现论文已写好、实验已跑完、审稿意见已回复。

ARIS 是一套基于 AI 编程助手（Claude Code / Codex CLI）的自动化科研框架。82 个 skill 覆盖从文献调研到论文投稿的完整流程，三边架构确保研究质量，Docker 容器化支持多人协作。

## 核心特性

**三边架构** — Leader（规划）+ Executor（执行）+ Reviewer（审查），跨模型协作避免自我审查盲区

**82 个研究 Skill** — 文献检索、实验规划、代码实现、论文撰写、审稿回复、专利申请……一条命令触发完整 pipeline

**项目分离** — 框架（skills/tools/templates）与科研项目（code/data/results）独立管理，一套框架支撑多个研究方向

**多人部署** — Docker 容器化，每人独立环境，共享数据集和 GPU 资源

**多端支持** — Claude Code (Terminal/VSCode)、Codex CLI、Cursor、Trae、Claude Desktop

## 架构

```
┌─────────────────────────────────────────────────────┐
│                    ARIS Framework                     │
├──────────┬──────────────┬──────────┬────────────────┤
│ skills/  │ templates/   │ tools/   │ deploy/        │
│ 82 skills│ 项目模板     │ 安装/同步│ Docker 部署    │
└──────────┴──────────────┴──────────┴────────────────┘
        │ install_aris.sh (symlink)
        ▼
┌─────────────────────────────────────────────────────┐
│              Research Project (per user)              │
├──────────┬──────────┬──────────┬────────────────────┤
│ code/    │ paper/   │ data/    │ refine-logs/       │
│ 实验代码 │ 论文 TeX │ 数据集   │ 实验计划/日志     │
└──────────┴──────────┴──────────┴────────────────────┘
```

### 三边协作

| 角色 | 模型 | 职责 | 禁止 |
|------|------|------|------|
| **Leader** | Claude Opus | 规划、决策、止损、分发任务 | 不写代码、不跑实验 |
| **Executor** | Claude Opus | 代码实现、实验部署、论文撰写 | 不做自审 |
| **Reviewer** | GPT-5.5 (Codex) | 代码审查、实验审计、claim 判定 | 只看原始文件 |

## 快速开始

详见 [QUICK_START.md](QUICK_START.md)。

```bash
# 个人使用（已有 Claude Code）
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git
cd Auto-research-in-sleep
bash tools/install_aris.sh /path/to/your/project

# 多人部署（Docker）
cd deploy && cp .env.example .env && vim .env
docker compose up -d
```

## Skill 一览

78 个 skill，覆盖 11 个分类：

| 分类 | 数量 | 代表 skill |
|------|------|-----------|
| Pipeline/编排 | 5 | `/leader` `/init-research` `/research-pipeline` |
| 研究发现 | 8 | `/idea-discovery` `/novelty-check` `/research-lit` |
| 搜索/数据源 | 7 | `/arxiv` `/semantic-scholar` `/gemini-search` |
| 实验 | 10 | `/experiment-plan` `/run-experiment` `/experiment-audit` |
| 论文撰写 | 13 | `/paper-writing` `/rebuttal` `/auto-paper-improvement-loop` |
| 论文演示 | 4 | `/paper-slides` `/paper-poster` `/paper-talk` |
| 图表/可视化 | 8 | `/paper-figure` `/figure-spec` `/mermaid-diagram` |
| 审查/质量 | 6 | `/kill-argument` `/proof-checker` `/citation-audit` |
| 专利/公文 | 8 | `/patent-pipeline` `/grant-proposal` `/specification-writing` |
| 工具/同步 | 6 | `/sync` `/framework-update` `/overleaf-sync` |
| 计算资源 | 3 | `/vast-gpu` `/serverless-modal` `/system-profile` |

完整目录（含用法示例）：[docs/SKILL_CATALOG.md](docs/SKILL_CATALOG.md) | [中文版](docs/SKILL_CATALOG_CN.md)

## 部署方式

### 方式一：个人安装（推荐入门）

前置：已安装 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 或 [Codex CLI](https://github.com/openai/codex)

```bash
# 克隆框架
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git ~/aris-framework

# 在你的科研项目中安装 skills
bash ~/aris-framework/tools/install_aris.sh /path/to/my-research
```

### 方式二：Docker 多人部署（推荐团队）

详见 [deploy/DEPLOY_GUIDE.md](deploy/DEPLOY_GUIDE.md)

```bash
cd deploy
cp .env.example .env   # 配置用户、API key、数据集路径
docker compose up -d   # 启动 Gitea + 用户容器
```

每人一个容器，共享：
- 框架代码（只读）
- 数据集（只读）
- 预训练模型（读写）

## 项目结构

```
aris-framework/
├── skills/              # 82 个 skill 定义（SKILL.md）
│   ├── leader/          # 三边架构 Leader
│   ├── experiment-plan/ # 实验规划
│   ├── paper-writing/   # 论文撰写
│   ├── sync/            # 代码同步
│   └── ...
├── templates/           # 项目模板
│   ├── project.yaml.tmpl
│   ├── CLAUDE_MD_TEMPLATE.md
│   └── EXPERIMENT_PLAN_TEMPLATE.md
├── tools/               # 安装器、同步脚本、辅助工具
│   ├── install_aris.sh
│   ├── sync.sh
│   └── watchdog.py
├── deploy/              # Docker 部署配置
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   └── DEPLOY_GUIDE.md
├── mcp-servers/         # MCP 服务器（Codex review）
├── docs/                # 详细文档
├── tests/               # 回归测试
├── QUICK_START.md       # 快速开始
└── README.md            # 本文件
```

## 客户端兼容

| 客户端 | 支持度 | 说明 |
|--------|--------|------|
| Claude Code (Terminal) | 完整 | 推荐，所有 skill 可用 |
| Claude Code (VSCode) | 完整 | Remote SSH 到容器 |
| Codex CLI | 完整 | 有独立 skill 镜像 (`skills-codex/`) |
| Cursor | 部分 | 见 `docs/CURSOR_ADAPTATION.md` |
| Trae | 部分 | 见 `docs/TRAE_ARIS_RUNBOOK_CN.md` |
| Claude Desktop | 有限 | 无法用 skills，仅 API 对话 |

## API 配置

支持多种 API 来源：

- Anthropic 官方（需海外 IP）
- Anthropic 中转站（国内可用）
- Claude Coding Plan（需 VPN）
- OpenAI / 中转站（Codex Reviewer 用）
- 免费方案：ModelScope（见 `docs/MODELSCOPE_GUIDE.md`）

详见 [docs/OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md#api-配置)

## 文档

| 文档 | 内容 |
|------|------|
| [QUICK_START.md](QUICK_START.md) | 5 分钟上手 |
| [docs/SKILL_CATALOG_CN.md](docs/SKILL_CATALOG_CN.md) | Skill 完整目录（中文） |
| [docs/SKILL_CATALOG.md](docs/SKILL_CATALOG.md) | Skill 完整目录（英文） |
| [docs/OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md) | 详细操作手册 |
| [deploy/DEPLOY_GUIDE.md](deploy/DEPLOY_GUIDE.md) | Docker 部署指南 |
| [docs/TRIPARTITE_ARCHITECTURE_GUIDE.md](docs/TRIPARTITE_ARCHITECTURE_GUIDE.md) | 三边架构详解 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |
| [AGENT_GUIDE.md](AGENT_GUIDE.md) | AI Agent 阅读指南 |

## 社区

- GitHub Issues: bug 报告、功能建议
- 每人 fork 自己的分支，必要时开会合并

## 致谢

基于 [wanshuiyin/Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) 上游项目。

## License

MIT
