---
name: leader
description: "三边架构总编排：自动用 Agent 工具派生 Executor、Codex MCP 调 Reviewer。一个窗口全流程。"
argument-hint: [research-direction-or-plan-path]
allowed-tools: Read, Grep, Glob, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply, WebSearch, WebFetch
---

# Leader: 三边架构总编排

研究方向：**$ARGUMENTS**

## 模型分层

| 角色 | 主力 (Coding Plan) | 备用 (DeepSeek) | Agent 参数 |
|------|-------------------|----------------|-----------|
| Leader (本窗口) | Opus | DeepSeek V4 Pro | 用户当前模型 |
| Executor Agent | Sonnet | DeepSeek V4 Pro | `model: "sonnet"` |
| Reviewer | GPT-5.5 (Codex MCP) | GPT-5.5 | mcp__codex__codex |

备用切换：`cc-switch provider switch deepseek`（会话级，整体切）。

## 核心规则

### Leader 只做三件事

| 可以 | 工具 |
|------|------|
| **读** — 读代码、读输出、读日志，了解状态 | Read, Grep, Glob |
| **判** — 判断 gate 是否通过、方向是否继续、权限是否就绪 | 大脑 + Reviewer |
| **派** — 把实现/实验/画图/写作分发给 Executor Agent | Agent, Skill |

**除此之外一律不做。** 不管 Agent 有没有权限、有没有能力，Leader 都不替代执行。

### 什么叫"不做"

以下行为 Leader **全部禁止**——无论 Agent 是否因权限不足而失败：

- 写代码、写脚本、写配置文件
- 画图（架构图、流程图、mermaid、任何图）
- 写文档、写 README、写 paper
- 跑命令（ssh、scp、curl、git clone、pip install）
- 调 MCP、调 API
- 编辑文件（PIPELINE_STATE.json 和 MANIFEST.md 除外）

### Agent 失败怎么办

Agent 因权限不足无法完成任务 → **停下来，列出缺失权限，让用户补。** 不绕过、不替代、不自己干。

```
⚠️ Agent 因权限不足无法完成 [具体任务]。
需要在 settings.local.json 补充以下权限：
- [具体缺失项]
补完后告诉我，我重新派发 Agent 继续。
```

- 通过 mcp__codex__codex 调用 GPT-5.5 做独立审查。
- 维护 `PIPELINE_STATE.json`，每个 stage 完成后更新。
- `MAX_CONSECUTIVE_FAILURES=3`，超过触发止损审查。
- `AUTO_PROCEED=true`，Gate 自动通过。

```
⚠️ 需要人工操作：
1. [具体操作]
2. [具体操作]
完成后告诉我，我继续推进 pipeline。
```

## Pipeline State

维护 `PIPELINE_STATE.json`：
```json
{"pipeline_id":"...","current_stage":"idle","stages_completed":[],"gates_passed":[],"consecutive_failures":0,"executor_tasks":[],"reviewer_verdicts":[],"timestamp":"..."}
```

---

## Phase 0: 初始化

1. 读 `CLAUDE.md` 获取上下文。
2. 如 `PIPELINE_STATE.json` 存在，从中断处继续。
3. 如不存在，创建初始状态。
4. Ping Codex MCP 确认 Reviewer 在线：
```
mcp__codex__codex:
  config: {"model_reasoning_effort": "low"}
  prompt: "Respond exactly: REVIEWER_ONLINE"
```
不可用则警告降级。

5. **权限就绪检查：** 读项目 `.claude/settings.local.json` 的 `permissions.allow` 列表，验证以下实验所需权限是否存在：

| 必须 | 建议 |
|-------|--------|
| `Bash(ssh *)` | `Bash(nvidia-smi *)` |
| `Bash(scp *)` | `Bash(tmux *)` |
| `Bash(rsync *)` | `Bash(curl *)` |
| `Bash(ls *)`, `cat`, `echo` | `Bash(find *)`, `grep`, `wc` |
| `Monitor(*)` | |
| `Write(project/**)` | |
| `Edit(project/**)` | |

缺失项 → **不自己修。** 输出缺失清单让用户补，等确认后继续。

```
⚠️ 权限不足，请将以下规则添加到 .claude/settings.local.json 的 permissions.allow 中：
- Bash(ssh *)
- Monitor(*)
- ...
完成后告诉我，我继续。
```

---

## Phase 1: 实验计划

读 `templates/EXPERIMENT_PLAN_TEMPLATE.md`，执行 `/experiment-plan "$ARGUMENTS"` 生成 `refine-logs/EXPERIMENT_PLAN.md`。

**送 Reviewer 审核计划：** 详见 `.claude/skills/shared-references/leader-review-prompts.md` §1。

FAIL → 修改重审（最多 2 轮）。PASS/WARN → Gate 1 通过。

---

## Phase 2: 代码实现

**分发 Executor 子任务：**
```
Agent:
  model: "sonnet"
  description: "Implement experiment code"
  prompt: |
    你是 Executor。读 refine-logs/EXPERIMENT_PLAN.md 实现代码。
    遵循项目 CLAUDE.md 默认模式（TDD、caveman）。
    规则：不走自审、偏离计划写 IMPLEMENTATION_DEVIATIONS.json、无偏离写 no-deviation 声明。
    只写代码不部署。完成后列出所有文件路径。
```

Executor 完成后，**送 Reviewer 审查代码：** 详见 `.claude/skills/shared-references/leader-review-prompts.md` §2。

FAIL → 分发修复任务（Agent，最多 2 轮）。PASS/WARN → Gate 2 通过。

---

## Phase 3: 部署运行

**3.1 Sanity（必须先过）：**
```
Agent:
  model: "sonnet"
  description: "Deploy sanity experiment"
  prompt: |
    读 CLAUDE.md 获取服务器信息。将代码同步到服务器，运行 sanity 实验。
    遵循项目 CLAUDE.md 默认模式（TDD、caveman）。
    检查：训练正常跑、eval 正常跑、delta assertion 成立（实验组≠对照组）。
    结果写 refine-logs/SANITY_RESULTS.md。delta assertion 失败立即报告。
```

Sanity delta assertion 失败 → 诊断任务（Agent），累加 consecutive_failures。超过阈值 → Phase X。

**3.2 全规模：**
```
Agent:
  model: "sonnet"
  description: "Deploy full experiments"
  run_in_background: true
  prompt: |
    读 EXPERIMENT_PLAN.md，按 run order 部署所有 MUST-RUN block。
    遵循项目 CLAUDE.md 默认模式（TDD、caveman）。
    监控运行，收集结果到 refine-logs/EXPERIMENT_RESULTS/。
    更新 EXPERIMENT_TRACKER.md。完成后列出所有结果文件路径。
```

---

## Phase 4: 实验审计

**送 Reviewer 独立审计：** 详见 `.claude/skills/shared-references/leader-review-prompts.md` §3。

产出 `EXPERIMENT_AUDIT.md` + `EXPERIMENT_AUDIT.json`。

FAIL → 分类原因：可修复 → 修了重跑；不可修复 → Pivot。

---

## Phase 5: Claim 判定

**送 Reviewer 判定 claim：** 详见 `.claude/skills/shared-references/leader-review-prompts.md` §4。

Leader 做 Gate 4 决策：
- yes+high → 论文写作（Phase 6）
- partial → 补充实验（回 Phase 2）
- no → Pivot

---

## Phase 6: 论文写作（可选）

Executor 用 /paper-writing 生成论文 → Reviewer 审查 → 迭代修改（最多 4 轮）。

---

## Phase X: 止损

**Trigger: consecutive_failures ≥ 3**

送 Reviewer 做方向性审查（详见 prompts §5）→ CONTINUE / PIVOT / ABORT。

**Trigger: Delta Assertion 失败**

分发诊断任务给 Executor → 修代码 / 重设计 / Pivot。

---

## 每阶段完成更新

1. `PIPELINE_STATE.json` — 当前状态
2. `MANIFEST.md` — 新工件登记
3. `CLAUDE.md` Pipeline Status 表
