# 三边架构关键问题探索报告

> 基于 ARIS 全部核心 SKILL.md、shared-references 协议、tools 脚本的深度源码阅读。
> 为后续 Leader(Opus4.6) + Executor(DeepSeekV4Pro) + Reviewer(GPT5.5) 三边架构改造提供决策依据。

---

## 一、探索范围

本次深度阅读了以下所有文件：

**流水线编排层（5 个）**：
- `research-pipeline` — 总编排
- `idea-discovery` — W1 选题编排
- `experiment-bridge` — W1.5 实现桥接
- `auto-review-loop` — W2 审查循环
- `paper-writing` — W3 论文编排

**子 Skill 层（12 个）**：
- `research-lit`, `idea-creator`, `novelty-check`, `research-review`
- `research-refine`, `research-refine-pipeline`, `experiment-plan`
- `run-experiment`, `monitor-experiment`, `experiment-audit`
- `result-to-claim`, `paper-plan`, `paper-write`, `paper-compile`
- `auto-paper-improvement-loop`

**共享协议层（10 个）**：
- `reviewer-independence.md`, `experiment-integrity.md`
- `effort-contract.md`, `assurance-contract.md`
- `integration-contract.md`, `review-tracing.md`
- `reviewer-routing.md`, `output-versioning.md`
- `output-manifest.md`, `writing-principles.md`

**工具层**：`tools/` 下所有 `.sh` 和 `.py` 脚本

---

## 二、关键问题 1：Leader / Executor / Reviewer 的职责边界怎么划？

### 2.1 ARIS 原设计的角色模型

原 ARIS 只有两个角色：

| 角色 | 模型 | 职责范围 |
|---|---|---|
| **Executor** (Claude) | 当前 session | 编排 + 决策 + 写代码 + 跑实验 + 写论文 + 汇总 |
| **Reviewer** (GPT) | Codex MCP | 打分 + 挑毛病（只在特定节点出场）|

**核心问题：Executor 身兼编排者和执行者。** 它既决定"下一步做什么"，又亲手做那件事，还自己判断做得好不好。这导致了你在 FPA-IOD 项目中遇到的所有痛点。

### 2.2 三边架构的职责划分建议

根据源码分析，建议如下划分：

#### Leader（Opus 4.6 via Claude Code）—— 统筹决策层

**从原 ARIS 中剥离出来的职责：**

| 职责 | 原来在 ARIS 中谁做 | 为什么要剥离给 Leader |
|---|---|---|
| 选择下一个 Stage | `research-pipeline` 内联逻辑 | Executor 在实现中遇到困难时会自行"简化"跳过，需要独立决策者 |
| Gate 决策（选 idea、是否继续） | `research-pipeline` 的 Gate 1 | 同上 |
| 止损判断（连续失败时 Pivot） | **不存在**（原 ARIS 的最大盲区） | 你的 Phase 3 四种修复全败无人叫停 |
| 文件契约校验 | **不存在** | 上游产出格式偏差导致下游静默失败 |
| Delta Assertion | **不存在** | compare.py 三组结果完全相同无人报警 |
| 全局进度追踪 | `MANIFEST.md`（被动日志） | 需要主动的进度监控和异常检测 |

**Leader 的核心原则：**
- **不写代码**，不跑实验，不写论文
- **只读文件**，做判断，分发任务
- **维护全局状态** `PIPELINE_STATE.json`（当前 Stage、已完成 Gate、累计失败次数）
- **强制执行文件契约**：每次 Executor 交付产出后，Leader 先做 schema 校验再决定下一步

#### Executor（DeepSeek V4 Pro via Claude Code）—— 纯执行层

**从原 ARIS 中保留的职责：**

| 职责 | 对应原 ARIS Skill |
|---|---|
| 文献调研 | `/research-lit` |
| 头脑风暴 | `/idea-creator` |
| 方法精炼 | `/research-refine` |
| 写实验代码 | `/experiment-bridge` Stage 2 |
| 部署和跑实验 | `/run-experiment` |
| 收集实验结果 | `/monitor-experiment` |
| 写论文 | `/paper-write` |
| 编译 PDF | `/paper-compile` |

**Executor 的核心原则：**
- **只做 Leader 分配的具体任务**，不自行决定做什么
- **每次任务是干净的 session**——不携带前序 Stage 的上下文（解决上下文污染）
- **交付明确的产出文件**，由 Leader 校验后才算完成
- **不做自审**——代码写完提交给 Reviewer，不自己判断质量

#### Reviewer（GPT 5.5 via Codex）—— 纯审查层

**从原 ARIS 中保留并扩展的职责：**

| 职责 | 原 ARIS 中的触发时机 | 三边架构中的触发时机 |
|---|---|---|
| idea 审查 | `/research-review`（idea 阶段末尾） | **保留**，无变化 |
| 代码审查 | `/experiment-bridge` Phase 2.5（可关闭） | **强制**，每次 Executor 写完代码后立即触发 |
| 实验完整性审查 | `/experiment-audit`（advisory） | **强制**，且审查清单扩展（增加 split 正确性、数据通路连通性） |
| 迭代审查 | `/auto-review-loop`（实验后循环） | **保留**，但增加"方向性审查"维度 |
| 论文审查 | `/auto-paper-improvement-loop` | **保留**，无变化 |
| **Delta Assertion 审查** | **不存在** | **新增**：实验结果到手后，先检查"实验组 vs 对照组是否有差异" |
| **方向性审查** | **不存在** | **新增**：连续 N 次失败后，Reviewer 评估"这个方向本身对不对" |

**Reviewer 的核心原则：**
- 遵守 `reviewer-independence.md` 协议——只看原始文件，不看 Executor 的总结
- 遵守 `experiment-integrity.md` 协议——Executor 不能审自己的代码
- **审查清单可扩展**——Leader 可以根据项目特点动态添加审查项

---

## 三、关键问题 2：文件契约需要升级到什么程度？

### 3.1 ARIS 原设计的文件契约现状

ARIS 的文件契约是**纯 prose 级别的君子协定**：

```
AGENT_GUIDE.md 的 Artifact Contracts 表：
  IDEA_REPORT.md  ← idea-discovery 产出
  EXPERIMENT_PLAN.md ← experiment-plan 产出
  ... 等等
```

`integration-contract.md` 提出了 6 项要求（activation predicate、canonical helper、concrete artifact、visible checklist、backfill、verifier），但这 6 项在大多数 Skill 之间**尚未落地**。文件中自己也承认：

> "Two bugs in the same week, same pathology... one skill 'called' another via prose without a canonical helper, a concrete artifact, or a verifier."

### 3.2 三边架构下文件契约的升级方向

**分级策略——不是所有文件都需要同等严格的校验：**

#### Tier 1: Gate 文件（跨 Stage 交接件）—— 强制 JSON Schema 校验

这些文件是 Stage 之间的"接力棒"，错误会级联放大：

| 文件 | 从 → 到 | 需要校验什么 |
|---|---|---|
| `idea-stage/IDEA_REPORT.md` | idea-discovery → experiment-bridge | 必须包含 ranked ideas，每个 idea 有 hypothesis、pilot result、novelty status |
| `refine-logs/EXPERIMENT_PLAN.md` | experiment-plan → experiment-bridge | 必须包含 run order、每个 block 的 claim、success criterion |
| `EXPERIMENT_LOG.md` | run-experiment → auto-review-loop | 必须包含实验名、指标、baseline 对比、delta |
| `NARRATIVE_REPORT.md` | auto-review-loop → paper-writing | 必须包含 claims、evidence mapping |

**建议做法：** 为每个 Gate 文件定义一个对应的 `_SCHEMA.json`（或在 Leader 中硬编码），Leader 在收到 Executor 产出后做校验。不通过 = 退回重做。

#### Tier 2: 状态文件 —— 标准 JSON 格式已有

`REVIEW_STATE.json`、`REFINE_STATE.json` 等已经有了标准格式，三边架构下 Leader 直接管理这些文件即可。

#### Tier 3: 工作文件（中间产物）—— 保持 Markdown，不加强制校验

`round-N-review.md`、`round-N-refinement.md` 等中间文件保持原样，不值得加 schema 校验。

### 3.3 新增：PIPELINE_STATE.json（Leader 的全局状态文件）

这是三边架构中最关键的新增文件，由 Leader 独占管理：

```json
{
  "pipeline_id": "fpa-iod-20260511",
  "current_stage": "experiment-bridge",
  "current_phase": "code-review",
  "stages_completed": ["idea-discovery", "research-refine"],
  "gates_passed": ["gate-1-idea-selection"],
  "consecutive_failures": 0,
  "max_consecutive_failures": 3,
  "pivot_count": 0,
  "executor_sessions": [
    {"stage": "idea-discovery", "status": "completed", "artifacts": ["idea-stage/IDEA_REPORT.md"]},
    {"stage": "research-refine", "status": "completed", "artifacts": ["refine-logs/FINAL_PROPOSAL.md"]}
  ],
  "reviewer_verdicts": [
    {"stage": "idea-review", "score": 7, "verdict": "proceed"}
  ],
  "delta_assertions": [],
  "timestamp": "2026-05-11T10:00:00Z"
}
```

---

## 四、关键问题 3：审查时机怎么安排？

### 4.1 ARIS 原设计的审查时机

```
idea-discovery ──── [Reviewer: research-review] ──── experiment-bridge
                                                        │
                                                   [Reviewer: Phase 2.5 代码审查, 可关闭]
                                                        │
                                                   run-experiment
                                                        │
                                                   [Reviewer: experiment-audit, advisory]
                                                        │
                                                   auto-review-loop ── [Reviewer: 每轮循环]
                                                        │
                                                   paper-writing ── [Reviewer: improvement loop]
```

**问题：** 从 experiment-bridge 写代码到 run-experiment 跑实验之间，审查可以被关闭（`CODE_REVIEW = false`）。即使开启，审查清单也有盲区（不查 train/val split，不查数据通路连通性）。

### 4.2 三边架构的审查时机建议

```
                              Leader 分发任务
                                   │
                            ┌──────┼──────┐
                            ▼      ▼      ▼
idea-discovery        experiment   paper
(Executor)            (Executor)   (Executor)
     │                     │           │
     ▼                     ▼           ▼
[R1: idea-review]    [R2: code-review]  [R5: paper-review]
     │                     │                │
     ▼                     ▼                ▼
  Gate 1              [R3: sanity-delta]   [R6: improvement-loop]
(Leader 决策)              │
     │                     ▼
     ▼             [R4: result-review]
  refine                   │
(Executor)                 ▼
     │               Gate 3: 止损判断
     ▼              (Leader 决策)
  Gate 2
(Leader 决策)
```

**六个审查点：**

| 审查点 | 触发条件 | Reviewer 做什么 | 不通过的后果 |
|---|---|---|---|
| **R1: idea-review** | idea-discovery 完成后 | 审查 idea 质量和 novelty | Leader 退回重做或 Pivot |
| **R2: code-review** | Executor 写完实验代码后 | 审查代码正确性 + **新增：train/val split 检查、数据通路连通性检查** | Leader 退回给 Executor 修改 |
| **R3: sanity-delta** | Sanity 实验跑完后 | **新增：检查实验组 vs 对照组的输出是否有差异** | Leader 触发代码诊断 |
| **R4: result-review** | 全部实验跑完后 | 审查实验完整性 + result-to-claim | Leader 决定进入写作还是 Pivot |
| **R5: paper-review** | 论文初稿完成后 | 审查论文质量 | Leader 安排修改 |
| **R6: improvement-loop** | 论文改进轮 | 迭代审查（保持 REVIEWER_BIAS_GUARD=true，每轮新 thread） | Leader 决定是否继续改进 |

### 4.3 新增审查清单项（针对 FPA-IOD 暴露的盲区）

当前 `experiment-audit` 的审查清单缺失以下项目，建议新增：

```markdown
### G. Train/Val/Test Split Correctness
For each evaluation script:
1. Which data split is used for evaluation? (train / val / test)
2. Is it the INTENDED evaluation split?
3. Is there any data leakage (training data appearing in evaluation)?
FAIL if: Evaluation runs on training data without explicit proxy labeling.

### H. Core Modification Effect Verification (Delta Assertion)
For experiment groups vs control group:
1. Are the outputs numerically different?
2. If outputs are identical, does the proposed modification actually affect the forward pass?
3. Trace the data flow: input → modification → output. Is the modification on the critical path?
FAIL if: Experiment group outputs are identical to control group.

### I. Dimension / Shape Compatibility
For each module integration point:
1. Does the output shape of module A match the expected input shape of module B?
2. Are there any silent broadcasts or reshapes that mask incompatibility?
WARN if: Shape mismatches exist but are auto-broadcast.
FAIL if: Shape mismatch would cause runtime error.
```

---

## 五、关键问题 4：止损机制怎么实现？

### 5.1 ARIS 原设计的止损现状

ARIS 的唯一止损机制是 `auto-review-loop` 的 `MAX_ROUNDS = 4`——轮次上限。但这是"量"的限制，不是"质"的判断。它不问"方向对不对"，只限制"最多试几次"。

`result-to-claim` 有路由逻辑：
- `no` → 记录 postmortem，考虑 Pivot
- `partial` → 补充实验
- `yes` → 继续

但 `result-to-claim` 只在实验完成后触发一次，不在中间迭代时触发。

### 5.2 三边架构的止损机制设计

**由 Leader 维护止损状态，基于以下触发条件：**

#### Trigger 1: 连续失败计数器

```
PIPELINE_STATE.json:
  "consecutive_failures": N

规则：
  if N >= 3:
    Leader 强制暂停流水线
    Leader 触发 Reviewer 做"方向性审查"（不是代码审查，是方向审查）
    Reviewer 判断：CONTINUE / PIVOT / ABORT

    CONTINUE = 方向没问题，是实现问题，重置计数器
    PIVOT = 方向有问题，回退到 idea-discovery，排除当前方向
    ABORT = 基本面有根本问题，终止流水线，输出诊断报告
```

**这直接解决了你 Phase 3 四种修复全败无人叫停的问题。**

#### Trigger 2: 时间 / 成本预算

```
PIPELINE_STATE.json:
  "gpu_hours_used": X
  "gpu_hours_budget": Y
  "wall_clock_hours": Z
  "wall_clock_budget": W

规则：
  if gpu_hours_used > 0.8 * gpu_hours_budget:
    Leader 发出预算警告
    Leader 评估剩余工作量 vs 剩余预算
    如果不够 → 降级 effort 或 提前进入 paper-writing（用现有结果写）
```

#### Trigger 3: Delta Assertion 失败

```
规则：
  if 实验组 == 对照组（数值完全相同或差异 < epsilon）:
    Leader 立即暂停
    Leader 分发诊断任务给 Executor：
      "请检查核心改动是否真正注入了模型的 forward pass"
    Executor 交回诊断报告
    Leader 决定：修代码 / 重新设计实验 / Pivot
```

**这直接解决了你的 compare.py 三组结果完全相同但无人报警的问题。**

#### Trigger 4: 评估基础设施检查（新增 Stage 0）

```
在任何实验跑之前，Leader 分发一个"评估管线诊断"任务给 Executor：
  1. eval 代码用的是哪个 split？（train / val / test）
  2. GT 来源是什么？
  3. AP 计算方法是什么？
  4. 快速 dry-run：用 5 个样本跑一遍 eval，确认流程通顺

Executor 交回诊断报告
Leader 交给 Reviewer 确认
通过后才允许正式跑实验
```

**这直接解决了你 eval 用训练集跑了 4 个 Phase 才被发现的问题。**

---

## 六、关键问题 5：上下文隔离怎么落地？

### 6.1 ARIS 原设计的上下文管理

ARIS 的上下文管理几乎全靠单 session 内部的"COMPACT 模式"：

| 机制 | 覆盖范围 | 局限性 |
|---|---|---|
| `COMPACT = true` | auto-review-loop 读 `findings.md` 代替全量日志 | 只压缩审查循环，不压缩 idea-discovery 或实现阶段 |
| `REVIEW_STATE.json` | auto-review-loop 断点恢复 | 只覆盖审查循环，其他阶段无恢复机制 |
| `REFINE_STATE.json` | research-refine 断点恢复 | 只覆盖精炼阶段 |

**根本问题：** 所有 Stage 在同一个 session 里串行执行，前面阶段的上下文（文献调研、brainstorm、失败的修复尝试）会持续占据上下文窗口。

### 6.2 三边架构的上下文隔离方案

**核心思路：每个 Executor 任务是一个独立的 session，通过文件交接而非上下文传递。**

#### 方案 A：Agent 子任务模式（推荐，最小改造）

```
Leader (Opus 4.6, 主 session, 长驻)
  │
  ├─ 分发任务 → Agent(Executor-1, DeepSeek V4 Pro, 子 session)
  │     └─ 输入：EXPERIMENT_PLAN.md + 任务描述
  │     └─ 输出：实验代码文件 + IMPLEMENTATION_REPORT.md
  │     └─ session 结束，上下文释放
  │
  ├─ 收到产出 → 校验 → 分发审查 → Codex MCP (GPT 5.5)
  │     └─ 输入：代码文件路径 + 审查清单
  │     └─ 输出：CODE_REVIEW.json
  │
  ├─ 审查通过 → 分发任务 → Agent(Executor-2, DeepSeek V4 Pro, 新子 session)
  │     └─ 输入：代码文件 + 部署指令
  │     └─ 输出：EXPERIMENT_LOG.md
  │     └─ session 结束，上下文释放
  │
  ... 以此类推
```

**优点：**
- 每个 Executor 子 session 只有当前任务的上下文，不会被前序 Stage 污染
- Leader 的主 session 保持精简（只有任务分发和决策信息，不包含代码和实验细节）
- 天然支持 Claude Code 的 Agent 工具——Agent 子任务可以在 background 运行

**技术实现：**
- Leader 使用 Claude Code 的 `Agent` 工具分发任务
- Executor 子任务通过 `subagent_type` 或模型参数指定 DeepSeek V4 Pro
- 交接完全通过磁盘文件（符合 ARIS 原有的 Artifact Contract 模式）
- Reviewer 通过 Codex MCP 调用（与 ARIS 原设计兼容）

#### 方案 B：Worktree 隔离模式（更强隔离，改造较大）

```
Leader (主 worktree)
  │
  ├─ 创建 worktree → Executor 在隔离 worktree 中工作
  │     └─ 代码变更不影响主分支
  │     └─ 完成后 merge 回主分支
  │
  ├─ Reviewer 审查 worktree 中的变更
  │
  ... 以此类推
```

**优点：** 代码级别的隔离，适合多人协作或多方向并行探索。
**缺点：** 改造成本高，需要管理 git worktree 生命周期。

**建议：先用方案 A（Agent 子任务模式），如果遇到代码冲突问题再升级到方案 B。**

### 6.3 Leader 的上下文管理策略

Leader 自身也需要上下文管理。由于它是长驻 session，随着流水线推进它的上下文也会增长。建议：

1. **Leader 不读文件内容，只读文件存在性和 schema 校验结果** —— 大幅减少上下文消耗
2. **Leader 的决策依据全部来自结构化的 JSON 文件**（`PIPELINE_STATE.json`、`CODE_REVIEW.json`、`REVIEW_STATE.json`）
3. **Leader 在每个 Stage 切换时做一次上下文总结** —— 把前一个 Stage 的关键结论压缩为 3-5 行，丢弃细节

---

## 七、关键问题 6：模型选型适配分析

### 7.1 你的选型

| 角色 | 模型 | 平台 | 成本考量 |
|---|---|---|---|
| Leader | Opus 4.6 | Claude Code | 推理能力强，适合复杂决策；成本较高但使用量小（只做决策） |
| Executor | DeepSeek V4 Pro | Claude Code (外部模型) | 代码能力强，成本较低；使用量大（实际干活） |
| Reviewer | GPT 5.5 | Codex MCP | 独立模型家族，确保跨模型审查的独立性 |

### 7.2 适配分析

**Leader = Opus 4.6 ✅ 非常合适**
- 长链推理和规划能力强
- 作为决策者不需要大量输出 token，成本可控
- Claude Code 原生支持，不需要额外适配

**Executor = DeepSeek V4 Pro ⚠️ 需要验证**
- 代码能力强，性价比高
- **关键问题：** Claude Code 的 Agent 子任务目前是否支持指定外部模型（DeepSeek）？如果不支持，可能需要：
  - 方案 1：通过 MCP server 调用 DeepSeek API（类似 Codex MCP 调用 GPT）
  - 方案 2：使用 `llm-chat` MCP server 接入 DeepSeek
  - 方案 3：直接在 Claude Code 中用 Bash 调用 DeepSeek API
- **建议：** 先测试 Claude Code Agent 工具是否支持 DeepSeek 模型切换。如果不支持，考虑用 Opus 4.6 自己做 Executor（同模型不同 session，仍然有上下文隔离的好处），或通过 MCP 桥接。

**Reviewer = GPT 5.5 via Codex ✅ 完全兼容**
- ARIS 原设计就是用 Codex MCP 调用 GPT 系列
- GPT 5.5 是 GPT 5.4 的升级，接口完全兼容
- 只需要在 SKILL.md 中把 `REVIEWER_MODEL = gpt-5.4` 改为 `gpt-5.5`

### 7.3 跨模型家族审查的保证

| Leader ↔ Executor | Executor ↔ Reviewer | Leader ↔ Reviewer |
|---|---|---|
| Claude ↔ DeepSeek（不同家族 ✅） | DeepSeek ↔ GPT（不同家族 ✅） | Claude ↔ GPT（不同家族 ✅） |

三个角色分属三个模型家族，任意两两之间都是跨家族审查，完美满足 `reviewer-independence.md` 的要求。

---

## 八、关键问题 7：Trae vs CLI 能力差异导致的问题分析

### 8.1 你的描述

> "那次不可用的是通过 Trae 的对话框进行的让它自动调用 skill 的，感觉跟 CLI 的能力也有关系。"

### 8.2 ARIS 对不同 IDE 的兼容性分析

根据源码分析，ARIS Skill 的执行依赖以下能力：

| 能力 | Claude Code CLI | Trae IDE | 差异影响 |
|---|---|---|---|
| **Bash 执行** | 原生支持，持久工作目录 | 支持，但可能有沙箱限制 | 实验部署依赖 SSH 和 screen，Trae 可能受限 |
| **MCP Server** | 原生支持（Codex MCP） | 需要单独配置 | Reviewer 审查依赖 MCP，Trae 配置更复杂 |
| **Agent 子任务** | 原生支持 | Trae 可能不支持 Agent 工具 | 三边架构的核心依赖 |
| **Skill 调用** | `/skill-name` 原生支持 | 需要特定适配 | Trae 的 Skill 调用机制可能不同 |
| **长 session** | 支持，有 compaction 机制 | 可能有 session 长度限制 | 全流程 28h 在 Trae 中可能被截断 |
| **文件读写** | 无限制 | 可能有工作区限制 | 跨目录操作可能受限 |
| **环境变量** | 继承 shell 环境 | 可能需要单独配置 | API key、SSH config 等可能丢失 |

### 8.3 关键结论

**ARIS 是为 Claude Code CLI 设计的。** 在 Trae 中运行会遇到：

1. **MCP Server 不可用** → Reviewer 审查无法执行 → 流水线退化为"Claude 自说自话"
2. **Agent 子任务不支持** → 无法实现上下文隔离 → 回退到单 session 串行
3. **Bash 能力受限** → SSH 部署、screen 管理等功能可能失效
4. **Skill 调用机制差异** → ARIS 的 `/skill-name` 语法在 Trae 中可能无法正确路由

**建议：三边架构改造完全基于 Claude Code CLI 进行。** Trae 兼容性作为后续工作。

---

## 九、ARIS 原有设计中值得保留的部分

并非所有东西都要重写。以下是经过源码分析后认为设计优秀、值得保留的部分：

| 保留项 | 理由 |
|---|---|
| **Artifact Contract 模式（文件级交接）** | 天然适配多 session 隔离，无需内存级状态传递 |
| **reviewer-independence.md 协议** | "只传文件路径不传总结"的原则非常正确 |
| **experiment-integrity.md 协议** | "写代码的不能审代码"的原则正确（只是执行不力） |
| **effort-contract.md 分级** | lite/balanced/max/beast 的分级设计合理 |
| **assurance-contract.md 审计体系** | Verdict 状态机（PASS/WARN/FAIL/NOT_APPLICABLE/BLOCKED/ERROR）设计精良 |
| **output-versioning.md 版本控制** | 时间戳文件 + 固定名最新副本的双写策略实用 |
| **integration-contract.md 的 6 项要求** | 概念正确（只是大多数 Skill 还没落地） |
| **REVIEWER_BIAS_GUARD = true** | 每轮新 thread 防止分数膨胀，有实证支持 |
| **State Recovery（REVIEW_STATE.json / REFINE_STATE.json）** | 断点恢复机制设计合理（需要扩展到更多 Stage） |

---

## 十、ARIS 原有设计中建议废弃的部分

| 废弃项 | 理由 | 替代方案 |
|---|---|---|
| **单 session 串行编排**（research-pipeline 内联） | 上下文污染的根源 | Leader 分发独立子任务 |
| **Executor 自审**（Stage 2 的 self-review 清单） | 写代码的审自己毫无意义 | 全部交给 Reviewer |
| **CODE_REVIEW = false 选项** | 允许关闭代码审查是危险的默认值 | 代码审查强制开启 |
| **AUTO_PROCEED = true 作为默认值** | 自动跳过 Gate 在全自动模式下容易出问题 | Leader 显式决策 |
| **experiment-audit 作为 advisory** | advisory 意味着可以忽略 | 升级为 mandatory（至少在代码审查阶段） |
| **nightmare 模式的 `codex exec`** | 依赖 Codex CLI 工具安装，在三边架构中 Reviewer 通过 MCP 更稳定 | 用 MCP + 扩展审查清单替代 |

---

## 十一、下一步行动建议

### 阶段 1：最小可行改造（1-2 天）

1. **创建 Leader Skill**：`skills/leader/SKILL.md`——核心编排逻辑，维护 `PIPELINE_STATE.json`
2. **扩展审查清单**：在 `experiment-audit` 中新增 G/H/I 三项（split 检查、Delta Assertion、维度兼容性）
3. **强制代码审查**：把 `experiment-bridge` 的 `CODE_REVIEW` 默认值改为 `true` 且不可关闭
4. **新增止损机制**：在 Leader 中实现连续失败计数器和 Pivot Gate

### 阶段 2：上下文隔离（2-3 天）

5. **验证 Executor 模型切换**：测试 Claude Code 的 Agent 工具是否支持 DeepSeek V4 Pro
6. **实现 Agent 子任务分发**：Leader 通过 Agent 工具分发独立任务给 Executor
7. **实现文件契约校验**：Leader 在收到 Executor 产出后做 schema 校验

### 阶段 3：端到端测试（1-2 天）

8. **用 FPA-IOD 项目做回归测试**：看三边架构能否在 Phase 4 之前发现 eval 用训练集的 bug
9. **用一个新项目做前向测试**：验证全流程可用性

---

*探索完成。等你回来后我们可以逐项讨论，确定哪些要做、哪些暂缓、优先级怎么排。*
