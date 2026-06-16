# ARIS 核心流水线架构解析

> 基于源码阅读的梳理，用于后续痛点诊断与三边架构改造讨论。

---

## 一、总体架构：一条串行大链条

ARIS 的全流程（`/research-pipeline`）本质上是一条**线性串行链条**，由一个顶层编排 Skill 依次调用子 Skill，每个子 Skill 又可能内嵌更深层的子调用：

```
/research-pipeline（总编排）
│
├─ Stage 1: /idea-discovery（W1 - 选题）
│   ├─ /research-lit              → 文献调研
│   ├─ /idea-creator              → 头脑风暴出 ideas
│   ├─ /novelty-check             → 查新
│   ├─ /research-review           → GPT 交叉审查
│   └─ /research-refine-pipeline  → 方法精炼 + 实验规划
│       ├─ /research-refine           → 与 GPT 对抗精炼方法
│       └─ /experiment-plan           → 生成实验路线图
│
├─ Gate 1: 选 idea（AUTO_PROCEED=true 时自动选 #1）
│
├─ Stage 2: 实现（Pipeline 自身内联逻辑，不是独立 Skill）
│   └─ 根据 EXPERIMENT_PLAN.md 写代码
│
├─ Stage 3: /run-experiment 或 /experiment-queue（部署跑实验）
│
├─ Stage 4: /auto-review-loop（W2 - 迭代审查改进，最多 4 轮）
│   └─ 每轮: GPT-5.4 审 → Claude 改 → 跑实验 → 再审
│
├─ Stage 5: 生成 NARRATIVE_REPORT.md（写作交接件）
│
└─ Stage 6（可选）: /paper-writing（W3 - 写论文）
    ├─ /paper-plan                    → 大纲
    ├─ /paper-figure                  → 数据图表
    ├─ /figure-spec 或 /paper-illustration → 架构图 / 示意图
    ├─ /paper-write                   → 逐节写 LaTeX
    ├─ /paper-compile                 → 编译 PDF
    └─ /auto-paper-improvement-loop   → 再审再改 ×2 轮
```

---

## 二、状态流转机制：纯文件契约（Artifact Contracts）

Skill 之间**没有内存级别的状态传递**，完全依赖磁盘上的 Markdown / JSON 文件做"接力棒"：

### 2.1 文件流转链条

```
idea-stage/IDEA_REPORT.md              ← /idea-discovery 产出
         ↓
refine-logs/FINAL_PROPOSAL.md          ← /research-refine-pipeline 产出
refine-logs/EXPERIMENT_PLAN.md         ← /experiment-plan 产出
refine-logs/EXPERIMENT_TRACKER.md
         ↓
（Stage 2 读这些文件，写出实验代码）
         ↓
EXPERIMENT_LOG.md                      ← /run-experiment 收集结果后产出
         ↓
review-stage/AUTO_REVIEW.md            ← /auto-review-loop 累积审查日志
review-stage/REVIEW_STATE.json         ← 循环状态持久化（轮次、threadId、分数）
         ↓
NARRATIVE_REPORT.md                    ← Stage 5 汇总产出
         ↓
paper/PAPER_PLAN.md                    ← /paper-plan 产出
paper/main.tex                         ← /paper-write 产出
paper/main.pdf                         ← /paper-compile 产出
```

### 2.2 完整 Artifact 契约表

| Artifact 文件 | 由谁创建 | 由谁消费 |
|---|---|---|
| `IDEA_REPORT.md` | idea-discovery | experiment-bridge |
| `EXPERIMENT_PLAN.md` | experiment-plan | experiment-bridge |
| `EXPERIMENT_LOG.md` | experiment-bridge | auto-review-loop, result-to-claim |
| `NARRATIVE_REPORT.md` | auto-review-loop | paper-writing |
| `paper/main.tex` | paper-write | paper-compile |
| `paper/main.pdf` | paper-compile | auto-paper-improvement-loop |
| `EXPERIMENT_AUDIT.md / .json` | experiment-audit | result-to-claim |
| `PAPER_CLAIM_AUDIT.md / .json` | paper-claim-audit | paper-writing Phase 5.5 gate |
| `CITATION_AUDIT.md / .json` | citation-audit | paper-writing Phase 5.8 gate |
| `research-wiki/` | research-wiki | idea-creator, research-lit, result-to-claim |
| `.aris/meta/events.jsonl` | hooks (被动) | meta-optimize |

---

## 三、跨模型协作协议

ARIS 的核心设计哲学是"**交叉模型对抗**"（Cross-Model Adversarial Collaboration）：

| 角色 | 模型 | 职责 |
|---|---|---|
| **Executor**（执行者） | Claude（当前 session） | 写代码、跑实验、写论文、做决策 |
| **Reviewer**（审查者） | GPT-5.4 via Codex MCP | 打分、挑毛病、提修改要求 |

### 3.1 跨模型规则

- Executor 和 Reviewer **必须不同模型家族**（Claude vs GPT）
- 传给 Reviewer 的是**原始文件路径 / 原始内容**，不是 Executor 的总结摘要（防止 Executor 美化信息）
- Executor **不能评判自己写的 eval 代码**——实验完整性审查必须由 Reviewer 独立执行
- 共享参考文档在 `skills/shared-references/` 下：
  - `reviewer-independence.md` — 跨模型审查协议
  - `experiment-integrity.md` — 禁止的造假模式
  - `effort-contract.md` — effort 级别规范
  - `citation-discipline.md` — 引用规则
  - `writing-principles.md` — 写作标准

---

## 四、关键控制机制

### 4.1 Gate / Checkpoint（闸门）

流水线中的关键决策点：

| 参数 | 默认值 | 作用 |
|---|---|---|
| `AUTO_PROCEED` | `true` | `true` = 自动放行（选排名第一的 idea）；`false` = 等人类确认 |
| `HUMAN_CHECKPOINT` | `false` | `true` = 每轮审查后暂停等人类干预；`false` = 全自动跑完 |

### 4.2 Effort 分级

控制搜索深度、审查轮数、论文精度：

| 级别 | Token 倍率 | 说明 |
|---|---|---|
| `lite` | 0.4x | 更少论文、更少 idea、更少轮次 |
| `balanced` | 1x | 默认行为 |
| `max` | 2.5x | 更多论文、更深审查 |
| `beast` | 5-8x | 所有旋钮拉到最大 |

### 4.3 Reviewer Difficulty 分级

控制 Reviewer 的对抗强度：

| 级别 | 机制 | 说明 |
|---|---|---|
| `medium` | MCP 审查 | Claude 控制给 GPT 看什么上下文 |
| `hard` | MCP + Reviewer Memory | GPT 有跨轮"记忆"，可以追踪 Claude 是否回避问题 |
| `nightmare` | Codex Exec（GPT 直读 repo） | GPT 直接读代码库，Claude 无法过滤信息 |

### 4.4 State Recovery（状态恢复）

长时间运行的 auto-review-loop 可能触发上下文压缩（compaction），通过 `REVIEW_STATE.json` 持久化关键状态来实现恢复：

```json
{
  "round": 2,
  "threadId": "019cd392-...",
  "status": "in_progress",
  "difficulty": "medium",
  "last_score": 5.0,
  "last_verdict": "not ready",
  "pending_experiments": ["screen_name_1"],
  "timestamp": "2026-03-13T21:00:00"
}
```

- 24 小时内的 `in_progress` 状态 → 自动恢复
- 超过 24 小时 → 视为废弃，重新开始
- `completed` 状态 → 重新开始（上一轮已正常结束）

---

## 五、架构的结构性风险（初步观察）

以下是基于源码阅读识别出的结构性问题，待后续结合实际踩坑经验进一步验证：

### 5.1 单 Session 串行，无真正隔离

整条流水线在一个 Claude session 里串行执行。前面阶段积累的上下文（文献调研、idea 头脑风暴产生的大量 token）会持续占据上下文窗口，到了 auto-review-loop 或 paper-writing 阶段时，上下文空间已经被严重挤压，导致后期行为质量退化。

### 5.2 编排者与执行者是同一个 Claude

写代码的 Claude 和决定"下一步做什么"的 Claude 是同一个 session。当 Stage 2 写代码遇到困难时，它可能自行"简化"实验设计、偏离 `EXPERIMENT_PLAN.md` 的原始规划，而没有任何外部制约机制来检测这种偏离。

### 5.3 文件契约是君子协定

Artifact 之间的传递完全依赖 Markdown 的非结构化文本。没有 schema 校验、没有完整性检查。上游 Skill 产出的格式稍有偏差，下游 Skill 就可能读偏或直接忽略关键信息。

### 5.4 Reviewer 只在特定节点出场

GPT 审查只发生在以下节点：
- `/research-review`（idea 阶段审查）
- `/auto-review-loop`（实验后迭代审查）
- `/auto-paper-improvement-loop`（论文改进）
- `/experiment-bridge` Phase 2.5（代码审查，可关闭）

中间大量的实现、调试、决策环节（Stage 2 写代码、Stage 3 部署实验、Stage 5 汇总报告）完全是 Claude 自说自话，缺乏外部约束。

### 5.5 Recovery 机制仅覆盖 Review Loop

`REVIEW_STATE.json` 只为 auto-review-loop 提供断点恢复。如果 session 在 Stage 1（idea-discovery）或 Stage 2（实现）阶段崩溃，没有对等的恢复机制——需要从头重跑或手动拼接状态。

---

## 六、后续讨论方向

1. **痛点诊断**：结合实际运行经验，定位上述结构性风险中哪些真正导致了产出不可用
2. **三边架构设计**：Leader（统筹）+ Executor（纯干活）+ Reviewer（纯审查）的角色分离与文件流转机制
3. **改造路线图**：确定哪些原有设计保留、哪些废弃、新机制如何落地
