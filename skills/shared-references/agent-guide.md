# ARIS Agent Guide

> **给 AI agent 看的工具手册。** 人类用户请看 [QUICK_START.md](../../QUICK_START.md) 和 [docs/OPERATIONS_GUIDE.md](../../docs/OPERATIONS_GUIDE.md)。

本文件通过 symlink 安装到每个项目的 `.claude/skills/shared-references/agent-guide.md`。
**Executor Agent 启动后必须首先 Read 本文件。**

---

## 强制约束（每次 session 必须遵守）

### 1. 默认模式

- **caveman 模式默认开启** — 精简回复，保留技术准确度。唯一例外：写论文/文档时关闭
- **TDD** — Python/实验代码必须先写测试再实现。用 `/tdd` skill，不要手动 TDD
- **grill-before-design** — 新设计/架构决策落地前必须 `/grill-me` 或 `/grill-with-docs`

### 2. 禁止 tail 轮询

**严禁** `Bash(tail -f ...)` 或重复 `Bash(tail ...)` 轮询实验进度。

| 场景 | 正确做法 |
|------|---------|
| 远程长时间实验 | `screen -dmS` 启动 → `/monitor-experiment` 收集 |
| 本地长时间实验 | `Bash(run_in_background: true)` → 等 task-notification |
| 检查是否跑完 | 单次 `ssh server "tail -20 log.txt"` 或 `screen -ls` |

### 3. Executor 阻塞协议

详见 `executor-blocked-protocol.md`（同目录）。

- 遇阻塞 → 尝试绕过 1 → 尝试绕过 2 → 两次都失败写 `BLOCKED_REPORT.md`
- 累计 ≥3 个不同阻塞全失败 → 整个任务停止
- **Leader 绝不替代执行**

### 4. Agent Status Stream

详见 `agent-status-stream.md`（同目录）。

- Agent 启动、进入长任务、遇阻塞、完成时更新自己的 Agent Status File
- 长训练、下载、队列、远程部署必须写 job handle（tmux/screen/watchdog/queue/log/result path）
- 不手写 JSON；优先用 `.aris/tools/agent_status.py`
- Leader 只读状态摘要，不把状态流当任务队列或 agent 聊天室

### 5. 角色边界

- **Leader** 只读/判/派。不写代码、不跑命令、不画图
- **Executor** → 三种专用角色：Coder / Deployer / Writer
- **Reviewer** 只看原始文件，不看 Executor 转述

### 6. Executor 角色分层

Leader 派发任务时使用专用角色：

| 角色 | 职责 | Caller |
|------|------|--------|
| **Coder** | 写代码、测试、重构 | executor |
| **Deployer** | SSH 同步、启动训练、监控实验 | executor |
| **Writer** | 写论文、文档、Rebuttal | executor |

### 7. 模型分层

| 角色 | 模型 | Agent 参数 |
|------|------|-----------|
| Leader | Opus | 用户当前模型 |
| Coder / Deployer / Writer | Sonnet | `model: "sonnet"` |
| Reviewer | GPT-5.5 | `mcp__codex__codex` |

---

## Skill 分层

每个 skill 有明确的调用者（`caller`）。**不要越层调用。**

### 编排层（caller: leader）

Leader 或用户直接调用。Executor **不应**自行调用这些 skill。

| Skill | 用途 |
|-------|------|
| `/leader` | 三边架构总编排 |
| `/research-pipeline` | 全自动研究 pipeline |
| `/init-research` | 创建新科研项目 |
| `/meta-optimize` | 分析使用日志优化框架 |
| `/dse-loop` | 设计空间搜索编排 |
| `/idea-discovery` | Workflow 1: 想法发现 pipeline |
| `/idea-discovery-robot` | Workflow 1 机器人方向 |
| `/research-refine` | 方向→方法精炼 |
| `/research-refine-pipeline` | 精炼+实验计划一条龙 |
| `/experiment-plan` | 制定实验计划 |
| `/result-to-claim` | 结果→claim 判定 |
| `/experiment-audit` | 实验诚实度审计 |
| `/auto-review-loop` | 自动审稿迭代（Codex） |
| `/auto-review-loop-llm` | 自动审稿迭代（LLM API） |
| `/auto-review-loop-minimax` | 自动审稿迭代（MiniMax） |
| `/paper-writing` | Workflow 3: 完整论文 pipeline |
| `/auto-paper-improvement-loop` | 论文自动改进循环 |
| `/rebuttal` | Workflow 4: 审稿回复 |
| `/resubmit-pipeline` | Workflow 5: 改投 |
| `/patent-pipeline` | 完整专利 pipeline |
| `/paper-talk` | 完整演讲 pipeline |
| `/kill-argument` | 对抗性审查 |
| `/paper-claim-audit` | 数值 claim 审计 |
| `/citation-audit` | 引用完整性审计 |
| `/framework-update` | 更新框架 |

### 执行层（caller: executor）

Executor 在任务中应主动使用。Leader 通过映射表推荐。

| Skill | 用途 | 何时用 |
|-------|------|--------|
| `/tdd` | 测试驱动开发 | **写 Python 代码必用** |
| `/diagnose` | 系统化 bug 诊断 | 遇到 bug 时 |
| `/experiment-bridge` | 实验计划→代码实现 | 收到实验计划后 |
| `/run-experiment` | 部署运行实验 | 代码写完要跑时 |
| `/monitor-experiment` | 监控实验收集结果 | 实验跑起来后 |
| `/experiment-queue` | 多 seed/config 批量实验 | 需要批量跑时 |
| `/training-check` | 训练过程检查（WandB） | 长时间训练中 |
| `/paper-write` | 逐章节写 LaTeX | 收到大纲后 |
| `/paper-plan` | 生成论文大纲 | 写论文前 |
| `/paper-compile` | 编译 LaTeX → PDF | 写完要编译时 |
| `/paper-figure` | 生成论文图表 | 有实验数据后 |
| `/figure-spec` | 生成架构图（SVG） | 需要示意图时 |
| `/paper-illustration` | AI 生成论文插图（Gemini） | 需要插图时 |
| `/paper-illustration-image2` | AI 生成论文插图（Codex） | 需要插图时 |
| `/mermaid-diagram` | 生成 Mermaid 图 | 需要流程图时 |
| `/paper-poster` | 生成会议海报 | 投稿后 |
| `/paper-slides` | 生成演讲幻灯片 | 投稿后 |
| `/slides-polish` | 幻灯片逐页打磨 | 幻灯片生成后 |
| `/formula-derivation` | 公式推导 | 理论部分 |
| `/proof-writer` | 写数学证明 | 理论部分 |
| `/proof-checker` | 验证数学证明 | 证明写完后 |
| `/analyze-results` | 分析实验结果 | 实验跑完后 |
| `/ablation-planner` | 消融实验设计 | 主实验通过后 |
| `/sync` | 代码同步/部署 | 需要同步时 |
| `/overleaf-sync` | Overleaf 同步 | 论文协作时 |
| `/claims-drafting` | 撰写专利权利要求 | 专利流程中 |
| `/specification-writing` | 撰写专利说明书 | 专利流程中 |
| `/embodiment-description` | 撰写实施例描述 | 专利流程中 |
| `/figure-description` | 专利附图描述 | 专利流程中 |
| `/invention-structuring` | 发明构建 | 专利流程中 |
| `/jurisdiction-format` | 专利格式转换 | 专利流程中 |
| `/patent-novelty-check` | 专利查新 | 专利流程中 |
| `/patent-review` | 专利审查 | 专利流程中 |
| `/grant-proposal` | 基金申请撰写 | 申请基金时 |
| `/writing-systems-papers` | 系统论文模板 | 投稿系统会议时 |

### 工具层（caller: any）

任何角色均可使用。原子操作，不含编排逻辑。

| Skill | 用途 |
|-------|------|
| `/caveman` | 精简输出模式 |
| `/zoom-out` | 看全局/高层视角 |
| `/handoff` | 会话交接文档 |
| `/grill-me` | 追问式方案论证 |
| `/grill-with-docs` | 追问+文档更新 |
| `/git-guardrails` | Git 安全检查 |
| `/review` | 代码审查 |
| `/write-a-skill` | 创建新 skill |
| `/to-issues` | 拆分为 issues |
| `/to-prd` | 生成 PRD |
| `/research-review` | 外部研究审查 |
| `/research-wiki` | 研究知识库 |
| `/feishu-notify` | 飞书通知 |
| `/qzcli` | 启智平台管理 |
| `/pixel-art` | 像素画生成 |

### 检索层（caller: any）

获取外部信息，任何角色均可用。

| Skill | 数据源 |
|-------|--------|
| `/arxiv` | arXiv 论文 |
| `/alphaxiv` | AlphaXiv 摘要 |
| `/deepxiv` | DeepXiv 分层阅读 |
| `/semantic-scholar` | Semantic Scholar |
| `/openalex` | OpenAlex |
| `/exa-search` | Exa AI 搜索 |
| `/gemini-search` | Gemini 搜索 |
| `/research-lit` | 多源文献综述 |
| `/novelty-check` | 查新验证 |
| `/prior-art-search` | 现有技术检索 |
| `/idea-creator` | 想法生成 |
| `/comm-lit-review` | 通信领域文献 |

### 计算资源层（caller: executor）

| Skill | 平台 |
|-------|------|
| `/vast-gpu` | Vast.ai 租 GPU |
| `/serverless-modal` | Modal 无服务器 GPU |
| `/system-profile` | 性能分析 |

---

## Skill 调用语法

**Claude Code / Cursor / Trae:**
```
/skill-name "arguments" — key: value, key2: value2
```

**Codex CLI:**
```
/skill-name "arguments" — key: value
```

## 通用参数

```
— effort: lite | balanced | max | beast      # 工作强度（默认 balanced）
— human checkpoint: true | false             # 暂停等人审批（默认 false）
— AUTO_PROCEED: true | false                 # gate 自动通过（默认 true）
— difficulty: medium | hard | nightmare      # reviewer 对抗强度
— venue: ICLR | NeurIPS | ICML | ...        # 目标会议
— sources: web, zotero, deepxiv, ...        # 文献源
— gpu: local | remote | vast | modal         # GPU 后端
```

## Effort Levels

| Level | Token 倍率 | 变化 |
|-------|:------:|------|
| `lite` | 0.4x | 更少论文、想法、轮次 |
| `balanced` | 1x | 默认 |
| `max` | 2.5x | 更多论文、更深审查 |
| `beast` | 5-8x | 所有旋钮拉满 |

---

## Artifact 流转

Skills 通过纯文本文件通信：

| Artifact | 产出者 | 消费者 |
|----------|--------|--------|
| `EXPERIMENT_PLAN.md` | experiment-plan | experiment-bridge |
| `EXPERIMENT_LOG.md` | experiment-bridge | auto-review-loop, result-to-claim |
| `NARRATIVE_REPORT.md` | auto-review-loop | paper-writing |
| `paper/main.tex` | paper-write | paper-compile |
| `paper/main.pdf` | paper-compile | auto-paper-improvement-loop |
| `EXPERIMENT_AUDIT.md/.json` | experiment-audit | result-to-claim |
| `PAPER_CLAIM_AUDIT.md/.json` | paper-claim-audit | paper-writing gate |
| `CITATION_AUDIT.md/.json` | citation-audit | paper-writing gate |
| `IDEA_REPORT.md` | idea-discovery | experiment-bridge |
| `BLOCKED_REPORT.md` | executor (blocked) | leader → 用户 |
| `research-wiki/` | research-wiki | idea-creator, research-lit, result-to-claim |
| `PIPELINE_STATE.json` | leader | leader (断点续跑) |
| `MANIFEST.md` | 所有角色 | 所有角色 |

---

## Shared References 索引

开始工作前应了解的协议文档（同目录下）：

| 文件 | 内容 |
|------|------|
| `executor-blocked-protocol.md` | Executor 阻塞自救协议 |
| `reviewer-independence.md` | Reviewer 独立性规则 |
| `experiment-integrity.md` | 实验诚实度禁令 |
| `integration-contract.md` | 实验链统一词汇 |
| `effort-contract.md` | effort level 规格 |
| `writing-principles.md` | 写作标准 |
| `citation-discipline.md` | 引用规则 |
| `venue-checklists.md` | 会议格式要求 |
| `recovery-state-contract.md` | 断点续跑协议 |
| `executor-skill-routing.md` | Leader 派发 skill 映射表 |

---

## Source of Truth

- 每个 skill 的完整行为：读 `skills/<name>/SKILL.md`
- 系统级规则：读 `skills/shared-references/*.md`
- 本文件是路由索引，不是规格说明
