# ARIS 三边架构使用指南

> 本文档面向想用 ARIS 跑完整研究流程的用户。假设你已经有一个研究方向，想让多个 AI 模型分工协作完成从选题到出论文的全流程。

---

## 一、什么是三边架构

传统的 AI 辅助科研是**一个模型干所有事**：它既规划研究方向、又写代码跑实验、还审查自己的结果、最后给自己打分写论文。

这就像一个学生自己出题、自己答题、自己批卷——很难发现自己的错误。

ARIS 的三边架构把这件事拆成三个独立角色：

```
┌──────────────┐
│   Leader     │  规划、决策、止损
│  (Claude)    │  "我们下一步做什么？该不该继续？"
└──────┬───────┘
       │ 分发任务
       ▼
┌──────────────┐         ┌──────────────┐
│  Executor    │ ──────→ │  Reviewer    │
│  (Claude)    │  交代码  │  (GPT-5.5)  │
│  写代码跑实验 │ ←────── │  独立审查    │
└──────────────┘  审查报告 └──────────────┘
```

| 角色 | 干什么 | 不干什么 |
|------|--------|----------|
| **Leader** | 制定实验计划、gate 决策、止损判断 | 不写代码、不跑实验 |
| **Executor** | 写代码、部署实验、收集结果、写论文 | 不审查自己的代码/结果 |
| **Reviewer** | 代码审查、实验审计、claim 判定 | 不看 Executor 的总结，只看原始文件 |

**为什么 Reviewer 必须是另一个模型家族？**

因为同一个模型审查自己写的代码，容易有系统性盲区。就像同一个老师出题改题，不如交叉阅卷。GPT-5.5 和 Claude 是不同模型家族，审查独立性更强。

---

## 二、准备工作

### 2.1 需要安装的工具

```bash
# Claude Code（Leader + Executor 用）
npm install -g @anthropic-ai/claude-code

# Codex CLI（Reviewer 用）
npm install -g @openai/codex
```

### 2.2 需要的 API Key

| 角色 | 模型 | API 来源 |
|------|------|----------|
| Leader + Executor | Claude Opus 4.6 | Anthropic 官方或中转站 |
| Reviewer | GPT-5.5 | OpenAI 官方或中转站 |

### 2.3 配置 Claude Code

编辑 `~/.claude/settings.json`：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "<你的 Anthropic API key>",
    "ANTHROPIC_BASE_URL": "<API 地址，官方就填 https://api.anthropic.com>"
  }
}
```

### 2.4 配置 Codex CLI

编辑 `~/.codex/config.toml`：

```toml
model_provider = "<你的 provider 名>"
model = "gpt-5.5"

[model_providers.<你的 provider 名>]
name = "<你的 provider 名>"
base_url = "<API 地址>"
wire_api = "responses"
requires_openai_auth = true
```

API key 放在 `~/.codex/auth.json` 中。

---

## 三、创建实验项目

### 3.1 初始化项目目录

```bash
# 创建一个新的实验项目目录（不要在 ARIS 仓库里跑实验）
mkdir -p ~/my-research-project
cd ~/my-research-project
git init
mkdir -p idea-stage refine-logs paper discussions
```

### 3.2 安装 ARIS Skill

ARIS 的所有能力都以 skill 的形式存在。需要把它们安装到你的项目里：

```bash
# 假设 ARIS 仓库在 ~/aris-orangmood-edition
ARIS_REPO=~/aris-orangmood-edition

# 安装 Claude Code 用的 skill（给 Leader 和 Executor）
bash $ARIS_REPO/tools/install_aris.sh . --aris-repo $ARIS_REPO --quiet

# 安装 Codex CLI 用的 skill（给 Reviewer）
bash $ARIS_REPO/tools/install_aris_codex.sh . --aris-repo $ARIS_REPO --quiet
```

安装完成后，你的项目目录下会多出：

```
.claude/skills/     ← 75 个 Claude Code skill（symlink 到 ARIS 仓库）
.agents/skills/     ← 69 个 Codex CLI skill（symlink 到 ARIS 仓库）
.aris/              ← 安装清单
```

### 3.3 写 CLAUDE.md

在项目根目录创建 `CLAUDE.md`，这是 AI 进入项目后读到的第一个文件：

```markdown
# 你的项目名

## Research Direction
你的研究方向描述

## Pipeline Status
| Stage | Status | Artifact |
|-------|--------|----------|
| Idea Discovery | NOT STARTED | — |
| Experiment Plan | NOT STARTED | — |
| Experiment Bridge | NOT STARTED | — |
| Experiment Audit | NOT STARTED | — |
| Result-to-Claim | NOT STARTED | — |
| Paper Writing | NOT STARTED | — |

## Three-Party Architecture (Single-Window Auto-Orchestration)
| Role | Model | How | Responsibility |
|------|-------|-----|---------------|
| Leader | Claude Opus 4.6 | 主 session（你开的窗口） | 研究规划、gate 决策 |
| Executor | Claude Opus 4.6 | Agent 子任务（自动派生） | 代码实现、实验部署 |
| Reviewer | GPT-5.5 | Codex MCP（自动调用） | 独立审查 |

Quick Start: `claude` → `/leader "你的研究方向"`

## Compute Resources
- SSH: `ssh your-server`
- GPU: 描述你的 GPU 资源
- Env: 描述你的 conda/venv 环境
```

---

## 四、启动（只需一个窗口）

三边架构**不需要手动开三个窗口**。Leader 通过 Claude Code 的 `Agent` 工具自动派生 Executor 子任务，通过 Codex MCP 自动调用 Reviewer。你只需要开一个终端：

```bash
cd ~/my-research-project
claude
```

进入后运行：

```
/leader "你的研究方向"
```

Leader 会自动编排整个流程：

```
你开的这一个窗口 (Leader，长驻)
  │
  ├─ Agent(prompt="实现代码...")  → 自动派生 Executor 子 session
  │     └─ 独立上下文，跑完自动回收
  │     └─ 产出通过磁盘文件交回
  │
  ├─ mcp__codex__codex(prompt="审查代码...")  → 自动调用 GPT-5.5
  │     └─ 独立模型家族，保证审查独立性
  │     └─ 返回结构化 verdict
  │
  └─ Leader 读返回结果 → gate 决策 / 止损 / 下一阶段
```

### 为什么不用手动开三个窗口？

- **Executor 是子任务**：Claude Code 的 `Agent` 工具可以派生独立的子 session。每个 Executor 任务有自己的上下文，不会被前序任务污染，跑完自动释放。
- **Reviewer 是 API 调用**：Codex MCP 直接调 GPT-5.5，不需要一个长驻窗口。
- **Leader 是编排者**：它长驻在你的窗口里，维护 `PIPELINE_STATE.json`，做所有决策。

### （可选）手动三窗口模式

如果你更喜欢手动控制每一步，也可以开三个窗口分别操作：

```bash
# 终端 1 - Leader
claude
# 手动跑 /experiment-plan，手动决策

# 终端 2 - Executor
claude
# 手动跑 /experiment-bridge

# 终端 3 - Reviewer
codex
# 手动跑 /experiment-audit
```

但推荐用 `/leader` 一键模式，省心且流程更规范。

---

> **以下为旧版三窗口说明，已被上面的单窗口模式取代，保留仅供参考。**

### （旧）窗口 2：Executor

```bash
claude
```

Executor 负责执行。Leader 决定做什么之后，在这个窗口里实际写代码、跑实验。

### 窗口 3：Reviewer

```bash
codex
```

Reviewer 负责独立审查。代码写完、实验跑完后，在这个窗口里做审计。

> **注意**：三个窗口在同一个项目目录下工作，通过文件系统自动共享产出物。产出文件后应在 `MANIFEST.md` 登记。

---

## 五、全流程实验步骤

整个流程是一条链：

```
/experiment-plan → /experiment-bridge → /experiment-audit → /result-to-claim
     (Leader)         (Executor)          (Reviewer)          (Leader)
```

### 步骤 1：制定实验计划（Leader 窗口）

```
/experiment-plan "你的研究方向描述"
```

Leader 会生成 `refine-logs/EXPERIMENT_PLAN.md`，包含：

- **Claim Map**：这个实验想证明什么
- **Expectation Declaration**：用什么 split、GT 来源、baseline 假设
- **Execution Spec**：每个实验 block 的具体配置（variants / metrics / seeds）
- **Delta Assertion**：实验组 vs 对照组应有什么差异
- **Evidence Mapping**：哪个结果文件支撑哪个 claim

**Leader 检查计划合理后，告诉 Executor 开始执行。**

### 步骤 2：实现和部署实验（Executor 窗口）

```
/experiment-bridge "refine-logs/EXPERIMENT_PLAN.md"
```

Executor 会：

1. 读取计划，理解要实现什么
2. 写代码实现实验
3. 代码写完后，由 Reviewer 做代码审查（自动调用 Codex）
4. 代码审查通过后，部署到 GPU 服务器运行
5. 先跑 sanity 实验验证管线通不通
6. sanity 通过后跑全规模实验
7. 收集结果

**如果实现过程中偏离了计划**，Executor 必须写 `refine-logs/IMPLEMENTATION_DEVIATIONS.json` 记录偏差。

### 步骤 3：审计实验（Reviewer 窗口）

```
/experiment-audit
```

Reviewer 会独立检查（不看 Executor 的总结，直接读代码和结果文件）：

- **Ground Truth Provenance**：GT 是不是真的来自数据集
- **Score Normalization**：分数有没有被做奇怪归一化
- **Result File Existence**：结果文件是不是真的存在
- **Dead Code Detection**：指标函数是不是根本没被调用
- **Split Correctness**：eval 用的是不是正确的 split
- **Implementation Conformance**：实际代码有没有偏离计划
- **Delta Assertion**：关键改动是不是真的生效了
- **Evidence Mapping**：claim 能不能追溯到具体证据

产出 `EXPERIMENT_AUDIT.md` 和 `EXPERIMENT_AUDIT.json`。

### 步骤 4：判定 Claim（Leader 窗口）

```
/result-to-claim
```

Leader 读取实验计划、实验结果、审计报告、偏差记录，综合判断：

- claim_supported：yes / partial / no
- confidence：high / medium / low
- delta_assertion_status：satisfied / weak / failed
- implementation_deviation_impact：none / narrow_scope / breaks_claim_test

**根据判定结果决定：**
- `yes` → 进入论文写作
- `partial` → 设计补充实验
- `no` → Pivot 到新方向

---

## 六、核心规则

### 6.1 Reviewer 独立性

Reviewer 必须直接读原始文件（代码、结果、配置），不能只看 Executor 写的总结。详见 `skills/shared-references/reviewer-independence.md`。

### 6.2 实验诚实度

禁止以下行为，详见 `skills/shared-references/experiment-integrity.md`：

- ❌ 用模型输出当 ground truth
- ❌ 用自己的分数做分母来归一化到 0.99
- ❌ 声称结果来自不存在的文件
- ❌ 把 2 个场景的 pilot 叫做"comprehensive evaluation"

### 6.3 计划偏移必须记录

如果实际实现偏离了计划，必须写 `IMPLEMENTATION_DEVIATIONS.json`：

```json
[
  {
    "plan_reference": "Block B1, Execution Spec",
    "deviation_type": "metric_change",
    "planned_value": "mAP@0.5",
    "actual_value": "mAP@[0.5:0.95]",
    "reason": "COCO 标准用 mAP@[0.5:0.95]",
    "claim_impact": "narrow_scope",
    "artifact_impact": "results/eval_*.json 格式变化",
    "status": "resolved",
    "owner": "executor",
    "timestamp": "2026-05-17T21:00:00Z"
  }
]
```

### 6.4 Delta Assertion

每个实验必须能回答：**"实验组和对照组的结果真的不一样吗？"**

如果实验组和对照组输出完全相同，说明核心改动根本没生效（可能是 dead code、bypass、shape mismatch 等），必须立即停下来排查，而不是继续烧 GPU。

---

## 七、文件交接规范

三个角色之间通过文件交接。每个阶段产出的关键文件：

| 阶段 | 产出文件 | 谁写 | 谁读 |
|------|----------|------|------|
| Plan | `refine-logs/EXPERIMENT_PLAN.md` | Leader | Executor, Reviewer |
| Bridge | 实验代码 + `IMPLEMENTATION_DEVIATIONS.json` | Executor | Reviewer |
| Audit | `EXPERIMENT_AUDIT.md` + `.json` | Reviewer | Leader |
| Claim | Claim verdict artifact | Leader | 全员 |

所有产出文件应在 `MANIFEST.md` 登记，格式：

```markdown
| Timestamp | Skill | File | Stage | Description |
|-----------|-------|------|-------|-------------|
| 2026-05-17 21:00 | /experiment-plan | refine-logs/EXPERIMENT_PLAN.md | implementation | FSCIOD experiment plan with 3 blocks |
```

---

## 八、目录结构一览

一个完整的 ARIS 实验项目长这样：

```
my-research-project/
├── CLAUDE.md                        ← 项目配置（AI 进来先读这个）
├── MANIFEST.md                      ← 工件追踪账本
├── .claude/skills/                  ← Claude Code skill（symlink）
├── .agents/skills/                  ← Codex CLI skill（symlink）
├── .aris/                           ← ARIS 安装清单
├── idea-stage/                      ← 选题阶段产出
│   ├── IDEA_REPORT.md
│   └── IDEA_CANDIDATES.md
├── refine-logs/                     ← 计划 + 实现阶段产出
│   ├── EXPERIMENT_PLAN.md
│   ├── EXPERIMENT_TRACKER.md
│   ├── IMPLEMENTATION_DEVIATIONS.json
│   └── FINAL_PROPOSAL.md
├── paper/                           ← 论文阶段产出
│   ├── main.tex
│   └── main.pdf
├── discussions/                     ← 进度报告、分析文档
└── reference paper/                 ← 参考文献
```

---

## 九、常见问题

### Q: 两个 Claude 窗口怎么区分 Leader 和 Executor？

进入窗口后，直接告诉它自己的角色。例如：

- Leader 窗口：`"你是 Leader，负责研究规划和决策。请先阅读 CLAUDE.md 了解项目背景。"`
- Executor 窗口：`"你是 Executor，负责代码实现和实验执行。等 Leader 分发任务后开始工作。"`

### Q: Reviewer 窗口能直接跑 `/experiment-audit` 吗？

可以。Codex CLI 的 skill 已经安装在 `.agents/skills/` 下。直接在 Codex 窗口里调用即可。

### Q: 如果只有一个模型（比如只有 Claude），还能用三边架构吗？

可以，但审查独立性会降低。建议至少 Reviewer 用不同的模型家族。如果实在只有一个模型，至少保证三个窗口的上下文完全隔离（不同 session），避免 Reviewer 被 Executor 的上下文污染。

### Q: 实验跑一半挂了怎么办？

ARIS 的恢复机制基于 `skills/shared-references/recovery-state-contract.md`：
- 工具层面（queue_manager, watchdog）有原子写入和状态持久化
- 链条层面有阶段检查点，可以从最近的 seam 续跑，不用从头来

### Q: 我想用 DeepSeek 当 Executor 可以吗？

可以。用 [claude-code-router](https://github.com/musistudio/claude-code-router) (ccr) 把 Executor 窗口路由到 DeepSeek：

```bash
# 安装 router
npm install -g @musistudio/claude-code-router

# 在 ~/.claude-code-router/config.json 里配置 DeepSeek provider
# 然后用 ccr code 启动 Executor 窗口
```

具体配置参见 ccr 文档。
