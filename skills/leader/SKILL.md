---
name: leader
description: "三边架构总编排：自动用 Agent 工具派生 Executor、Codex MCP 调 Reviewer。一个窗口全流程。"
argument-hint: [research-direction-or-plan-path]
allowed-tools: Read, Grep, Glob, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply, WebSearch, WebFetch
caller: leader
platform: both
status: active
invokes:
  - experiment-plan
  - tdd
  - diagnose
  - run-experiment
  - monitor-experiment
  - sync
  - experiment-queue
  - training-check
  - paper-writing
examples:
  - "/leader 频域特征+原型学习做小样本增量目标检测"
  - "run full research pipeline for this idea"
  - "orchestrate paper writing and review"
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

### Agent 阻塞怎么办

遵循 `skills/shared-references/executor-blocked-protocol.md`。

**Executor 自行处理阻塞**（尝试2种绕过 → 全失败写 `BLOCKED_REPORT.md`）。
**Leader 收到报告后只做三步：** 读报告 → 转述用户 → 等确认后重新派发。

```
⚠️ Executor 报告阻塞（见 BLOCKED_REPORT.md）：
[转述报告中的"需要人工操作"部分]
完成后告诉我，我重新派发 Agent 继续。
```

**Leader 绝对不做：** 自己尝试绕过、自己执行命令、自己修配置。

- 通过 mcp__codex__codex 调用 GPT-5.5 做独立审查。
- 维护 `PIPELINE_STATE.json`，每个 stage 完成后更新。
- 读取 `.aris/status/agents/*.json` 或 `.aris/tools/agent_status.py summary` 获取运行中 agent 状态；Leader 不编辑 agent-owned status file。
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

## Agent Status Stream

所有派生 agent 遵循 `skills/shared-references/agent-status-stream.md`：

- Leader 派发任务时给出 `agent_id`
- Agent 启动、进入长任务、阻塞、完成时用 `.aris/tools/agent_status.py` 写自己的状态文件
- 长运行任务必须写 job handle（tmux/screen/watchdog/queue/log/result path）
- Leader 到达 `next_expected_update` 后可自动做只读检查
- Leader 不通过状态流重启任务、杀进程、部署代码、改配置或修改产物

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

5. **运行能力就绪检查（Codex-first）：** 不读取或要求 `.claude/settings.local.json`。Codex 的权限由当前会话 sandbox/approval 策略控制；Leader 只做非破坏性的可用性探测和配置检查。

| 必须确认 | 检查方式 |
|----------|----------|
| 项目文件可读 | `AGENTS.md` / `CLAUDE.md` / `project.yaml` 是否存在 |
| 本地工具可用 | `git`、`python`、`tmux`、`ssh`、`rsync`、`scp` 按任务需要检查 `command -v` |
| GPU 可见性 | 本地任务检查 `nvidia-smi`；远程任务让 Deployer 检查目标机 |
| 远程配置 | `project.yaml` / `CLAUDE.md` 中是否有目标服务器、数据路径、输出路径 |
| ARIS 状态目录 | 项目 `.aris/` 与框架级 `~/.aris/` 可写 |

缺失项 → **不自己修。** 输出“缺什么、为什么需要、用户可执行的最小命令”，等确认后继续。不要让 Codex 用户修改 Claude Code 权限文件。

```
⚠️ 运行环境缺少必要能力：
- tmux 未安装：长实验无法稳定托管。建议：sudo apt-get install tmux
- project.yaml 未配置 remote server：Deployer 不知道部署目标。
完成后告诉我，我继续。
```

Claude Code 兼容模式：只有当用户明确在 Claude Code 中运行 ARIS，才额外检查 `.claude/settings.local.json` 的 `permissions.allow`。这属于兼容层提示，不是 Codex 默认阻塞条件。

---

## Phase 1: 实验计划

读 `templates/EXPERIMENT_PLAN_TEMPLATE.md`，执行 `/experiment-plan "$ARGUMENTS"` 生成 `refine-logs/EXPERIMENT_PLAN.md`。

**送 Reviewer 审核计划：** 详见 `.claude/skills/shared-references/leader-review-prompts.md` §1。

FAIL → 修改重审（最多 2 轮）。PASS/WARN → Gate 1 通过。

---

## Phase 2: 代码实现

**分发 Coder 子任务：**
```
Agent:
  model: "sonnet"
  description: "Implement experiment code (Coder)"
  prompt: |
    你是 Coder，只负责写代码。
    agent_id: coder-${pipeline_id}-phase2

    ## 首先
    Read .claude/skills/shared-references/agent-guide.md 了解可用 skills 和约束。
    Read .claude/skills/coder/SKILL.md 了解 Coder 职责边界。
    Read .claude/skills/shared-references/agent-status-stream.md 了解状态汇报协议。

    ## 任务
    读 refine-logs/EXPERIMENT_PLAN.md 实现代码。

    ## 推荐 Skills
    本任务必用：/tdd（先写测试再实现）
    本任务可选：/diagnose（遇 bug 时）
    参考：.claude/skills/shared-references/executor-skill-routing.md

    ## 约束
    - caveman 模式开启
    - 用 .aris/tools/agent_status.py start/update/finish 写 agent_id=coder-${pipeline_id}-phase2 的状态
    - 遵循 executor-blocked-protocol：遇阻塞先自行尝试 2 种绕过，全失败写 BLOCKED_REPORT.md 后停止
    - 不走自审、偏离计划写 IMPLEMENTATION_DEVIATIONS.json、无偏离写 no-deviation 声明
    - 只写代码不部署。完成后列出所有文件路径
```

Coder 完成后，**送 Reviewer 审查代码：** 详见 `.claude/skills/shared-references/leader-review-prompts.md` §2。

FAIL → 分发修复任务（Coder，最多 2 轮）。PASS/WARN → Gate 2 通过。

---

## Phase 3: 部署运行

**3.1 Sanity（必须先过）：**
```
Agent:
  model: "sonnet"
  description: "Deploy sanity experiment (Deployer)"
  prompt: |
    你是 Deployer，只负责部署和监控。
    agent_id: deployer-${pipeline_id}-sanity

    ## 首先
    Read .claude/skills/shared-references/agent-guide.md 了解可用 skills 和约束。
    Read .claude/skills/deployer/SKILL.md 了解 Deployer 职责边界。
    Read .claude/skills/shared-references/agent-status-stream.md 了解状态汇报协议。

    ## 任务
    读 CLAUDE.md 获取服务器信息。将代码同步到服务器，运行 sanity 实验。
    检查：训练正常跑、eval 正常跑、delta assertion 成立（实验组≠对照组）。
    结果写 refine-logs/SANITY_RESULTS.md。delta assertion 失败立即报告。

    ## 推荐 Skills
    本任务必用：/run-experiment, /monitor-experiment
    本任务可选：/sync deploy, /diagnose（出问题时）

    ## 约束
    - caveman 模式开启
    - 用 .aris/tools/agent_status.py start/update/finish 写 agent_id=deployer-${pipeline_id}-sanity 的状态
    - 启动远程训练后必须写 job handle 和 next_expected_update
    - 遵循 executor-blocked-protocol
    - 禁止 tail -f 轮询，用 Monitor 或 run_in_background
```

Sanity delta assertion 失败 → 诊断任务（Coder 修代码 + Deployer 重跑），累加 consecutive_failures。超过阈值 → Phase X。

**3.2 全规模：**
```
Agent:
  model: "sonnet"
  description: "Deploy full experiments (Deployer)"
  run_in_background: true
  prompt: |
    你是 Deployer，只负责部署和监控。
    agent_id: deployer-${pipeline_id}-full

    ## 首先
    Read .claude/skills/shared-references/agent-guide.md 了解可用 skills 和约束。
    Read .claude/skills/deployer/SKILL.md 了解 Deployer 职责边界。
    Read .claude/skills/shared-references/agent-status-stream.md 了解状态汇报协议。

    ## 任务
    读 EXPERIMENT_PLAN.md，按 run order 部署所有 MUST-RUN block。
    监控运行，收集结果到 refine-logs/EXPERIMENT_RESULTS/。
    更新 EXPERIMENT_TRACKER.md。完成后列出所有结果文件路径。

    ## 推荐 Skills
    本任务必用：/run-experiment, /monitor-experiment
    本任务可选：/experiment-queue（批量时）, /training-check（WandB）, /diagnose

    ## 约束
    - caveman 模式开启
    - 用 .aris/tools/agent_status.py start/update/finish 写 agent_id=deployer-${pipeline_id}-full 的状态
    - 每个长运行任务必须写 job handle 和 next_expected_update；正式训练前 20 分钟每 +5m 更新/检查一次，稳定后 +30m 到 +60m
    - 遵循 executor-blocked-protocol
    - 禁止 tail 轮询
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

用 Writer 角色生成论文 → Reviewer 审查 → 迭代修改（最多 4 轮）。

```
Agent:
  model: "sonnet"
  description: "Write paper (Writer)"
  prompt: |
    你是 Writer，只负责写作。
    agent_id: writer-${pipeline_id}-paper

    ##首先
    Read .claude/skills/shared-references/agent-guide.md 了解可用 skills 和约束。
    Read .claude/skills/writer/SKILL.md 了解 Writer 职责边界。
    Read .claude/skills/shared-references/agent-status-stream.md 了解状态汇报协议。

    ## 任务
    读实验结果（refine-logs/EXPERIMENT_RESULTS/）和实验计划（refine-logs/EXPERIMENT_PLAN.md）。
    用 /paper-writing 或直接写论文。

    ## 约束
    - 用 .aris/tools/agent_status.py start/update/finish 写 agent_id=writer-${pipeline_id}-paper 的状态
    - 学术严谨：claim 必须有实验结果支撑，不夸大
    - 数据一致：论文中的数字必须与实验结果文件一致
```

---

## Phase X: 止损

**Trigger: consecutive_failures ≥ 3**

送 Reviewer 做方向性审查（详见 prompts §5）→ CONTINUE / PIVOT / ABORT。

**Trigger: Delta Assertion 失败**

分发诊断任务给 Coder → 修代码 / 重设计 / Pivot。

---

## 每阶段完成更新

1. `PIPELINE_STATE.json` — 当前状态
2. `MANIFEST.md` — 新工件登记
3. `CLAUDE.md` Pipeline Status 表
