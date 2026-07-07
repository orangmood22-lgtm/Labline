# Labline Runtime Upgrade Plan

## 目的

这份文档用于交给开发 session，目标是把 Labline 从“skills + 分散状态文件 + 若干工具”升级为一个更稳定的项目运行时状态协议。

> 2026-06-26 修订说明：本文不是要把 Labline 重写成 LangGraph，也不是把所有项目文件搬进 `.labline/runtime/`。核心目标只有一个：通过框架约定的项目内 heartbeat/status 文件协议，降低 Leader 长时间在线等待和自行解释状态的压力。

核心问题不是 Labline 缺功能，而是当前状态分散在多个系统里，Leader 需要靠定时查看、读日志、读状态文件来维持全局判断。这会导致：

- Leader 必须长时间在线，容易出现“leader anxiety”。
- 交互式 Codex、`codex exec resume`、外部 heartbeat、未来 ChatOps 入口可能同时操作同一个任务。
- Watchdog、experiment queue、agent status、各 workflow 私有 state 各自有状态，但没有统一 Leader 默认读取视图。
- 自动流程虽然存在状态文件，但缺少机器级的 lease、escalation、heartbeat 协议来约束控制权。

升级方向：先实现一个轻量的 `Project Runtime State Root` 与 `Project Heartbeat Protocol`，把现有文件协议硬化成统一的 task/event/lease/escalation/summarization 模型。LangGraph、Temporal、cron、Feishu、Codex exec、OpenCode 等都应该作为可替换触发器或 adapter，而不是成为项目格式本身。

## 当前架构判断

Labline 已经具备几个重要基础：

- 三边架构：Leader / Executor / Reviewer。
- Agent status stream：`.labline/status/agents/*.json`。
- Watchdog：服务器侧持续健康检查，输出 task status、alerts、summary。
- Experiment queue：管理 GPU job、screen/tmux、OOM retry、queue state。
- 外部 Feishu/Lark bridge：默认由 `lark-channel-bridge` 作为 transport，Labline 不再把 legacy `.labline/feishu-control/` 作为新 runtime 的目标状态面。
- Recovery state contract：机器可恢复的 JSON sidecar。
- Markdown-first research artifacts：计划、实验、论文、ledger、人类可读记录。

主要缺口：

- 状态源太多，没有统一 `lane status`。
- 没有全局控制权 lease，容易出现多入口同时控制。
- Watchdog 还偏“被读取的监控文件”，没有充分事件化为 escalation。
- Leader 仍然承担过多状态解释职责。
- `codex exec`、交互式 Codex、外部 scheduler、未来 ChatOps 之间缺少明确边界。
- 旧的根目录 `PIPELINE_STATE.json` 是 Leader skill 的历史阶段恢复约定，不应继续作为新项目协议。

## 目标架构

建议目标分层：

```text
Labline Skills
  - Leader / Coder / Deployer / Writer / Reviewer
  - Research, experiment, paper, rebuttal skills

Project Runtime State Root
  - agents
  - jobs
  - queues
  - watchdog observations
  - pipeline machine state
  - tasks
  - events
  - leases
  - heartbeats
  - escalations
  - summaries

Adapters
  - AgentStatusAdapter
  - WatchdogAdapter
  - ExperimentQueueAdapter
  - PipelineStateAdapter
  - CodexExecWorker
  - OpenCodeWorker
  - ShellWorker
  - ClearML / Slurm / Modal / Vast adapters, optional

Optional Orchestrators
  - cron / systemd timer / APScheduler
  - LangGraph
  - Temporal
  - Prefect

Human Interfaces
  - Codex App / Codex CLI
  - Feishu / Lark ChatOps
  - status dashboard, optional
```

原则：

- Labline 项目格式仍然是 human-readable project structure + JSON sidecar。
- Runtime state 必须可被普通文件系统恢复，不依赖某个特定 orchestrator。
- Runtime 整理不能破坏人对项目的可读性：`project.yaml`、`AGENTS.md`、`CLAUDE.md`、`MANIFEST.md`、`findings.md`、`idea-stage/`、`refine-logs/`、`review-stage/`、`paper/` 等 human/shared surface 保持原位。
- `.labline/runtime/` 只放维护和控制状态，不放 Codex/Claude 入口文件、安装 manifest、`.gitignore`、研究产物、trace archive、外部 bridge 私有状态。
- LangGraph 可以接入，但只作为 optional backend。
- 长训练不由 Codex 进程托管，而由 tmux/screen/slurm/queue/ClearML 等 durable job handle 托管。
- Leader 不 sleep 等待训练；heartbeat 默认不唤醒 Leader，只在 escalation、due decision、terminal result 或用户显式状态请求时 resume Leader。

## Project Surface 边界

新 runtime 设计必须同时满足四类读者/用途：

| Surface | 读者 | 示例 | 是否迁入 `.labline/runtime/` |
|---|---|---|---|
| Human-facing | 人类读结论、报告、风险 | `README.md`, `findings.md`, `EXPERIMENT_LOG.md`, `AUTO_REVIEW.md`, paper artifacts | 否 |
| Shared | 人和 AI 都读/维护 | `project.yaml`, `AGENTS.md`, `CLAUDE.md`, `MANIFEST.md`, `EXPERIMENT_PLAN.md`, `EXPERIMENT_TRACKER.md`, `CLAUDE.md ## Pipeline Status` | 否 |
| Agent-facing | AI 恢复和结构化读取 | `.labline/runtime/summaries/current.json`, `.labline/runtime/tasks/*.json`, workflow recovery JSON | 部分迁入 |
| Maintenance | 工具、runtime、安装器、trace | `.labline/runtime/`, `.labline/installed-skills*.txt`, `.labline/tools`, `.labline/traces/`, `.labline/meta/` | 只 runtime 控制状态迁入 |

根目录 `PIPELINE_STATE.json` 在新协议中废弃。新项目的机器阶段状态写到 `.labline/runtime/pipelines/`；人类可读阶段摘要写到 `CLAUDE.md ## Pipeline Status`、tracker 或 `summaries/current.md`。

### Pipeline state 来源和迁移结论

旧根目录 `PIPELINE_STATE.json` 的主要来源是 `leader` skill 的历史阶段恢复约定：Leader 在阶段完成时写它，后续 Leader session 再读取它继续推进。当前没有工具层 hook 或 watcher 把根目录 `PIPELINE_STATE.json` 当作自动运行协议读取。

因此新协议采用以下规则：

- `leader` skill 新项目写 `.labline/runtime/pipelines/leader.json`，不再创建根目录 `PIPELINE_STATE.json`。
- 如果旧项目已有根目录 `PIPELINE_STATE.json`，只在初始化或迁移时读取一次，后续写入 runtime pipeline state。
- 既有 workflow 私有状态只作为迁移输入；新建 workflow phase state 写入 `.labline/runtime/pipelines/<workflow>.json`。workflow 私有 staging、audit input、final report 等维护材料可以继续留在 workflow 私有目录。
- 人类可读的阶段状态必须继续写入 shared surface，例如 `CLAUDE.md ## Pipeline Status`、tracker 或 `summaries/current.md`，不能只藏在机器 JSON 中。

## 建议新增目录

在项目内新增：

```text
.labline/runtime/
  agents/
    <agent_id>.json
  jobs/
    <job_id>.json
  queues/
    <queue_id>.json
  watchdog/
    <watchdog_id>/
      status/
      summary.json
  pipelines/
    <pipeline_id>.json
  tasks/
    <task_id>.json
  events/
    runtime.jsonl
  leases/
    <owner>.lock
  heartbeats/
    <runner>.json
  escalations/
    <task_id>.json
  summaries/
    current.json
    current.md
```

### 子目录内容和写入责任

| 子目录 | 主要内容 | 写入者 | 主要读者 | 是否源数据 |
|---|---|---|---|---|
| `agents/` | 每个 agent 的当前状态快照，含 role、task、liveness、blocker、artifact pointers、next expected update | 对应 agent 自己 | Leader、status aggregator、heartbeat | 是 |
| `jobs/` | tmux/screen/slurm/ClearML/Modal/Vast/ssh 等 durable job handle、日志路径、结果路径、terminal verdict | 启动作业的 Deployer、queue controller 或 job supervisor | watchdog、heartbeat、Leader、status aggregator | 是 |
| `queues/` | experiment queue 或批量调度器的队列、波次、重试、OOM/stale 状态 | queue controller | Leader、heartbeat、status aggregator | 是 |
| `watchdog/` | watchdog 观测结果、健康摘要、异常信号、被监控 job 的状态镜像 | watchdog runner | heartbeat、status aggregator、Leader | 是，限观测层 |
| `pipelines/` | 机器可读 workflow phase state，例如 `leader.json`、workflow-specific phase state | pipeline controller 或 Leader | Leader、status aggregator、recovery logic | 是 |
| `tasks/` | Leader 默认读取的统一任务视图，归一化 agent/job/queue/watchdog/pipeline 信号 | runtime status aggregator | Leader、ChatOps、用户 status command、heartbeat | 否，派生视图 |
| `events/` | append-only runtime event log，例如 task.started、task.stalled、lease.stolen、heartbeat.skipped | runtime CLI/API 代表各组件追加 | 调试、审计、status aggregator | 是，事件源 |
| `leases/` | 控制权锁，含 owner、host、pid、TTL、purpose | runtime lease manager | 所有会修改状态或控制 session 的入口 | 是 |
| `heartbeats/` | heartbeat runner 自身状态、上次 probe、下次计划、最近 skipped/triggered 原因 | heartbeat runner | Leader、status command、debugger | 是，限 heartbeat 自身 |
| `escalations/` | 需要 Leader 或人类介入的异常、due decision、terminal result、stop request | watchdog、heartbeat、status aggregator 或 runtime API | Leader、ChatOps、用户 | 是 |
| `summaries/` | 聚合后的 `current.json` 和人类可读 `current.md` | runtime status aggregator | Leader、ChatOps、用户、handoff | 否，派生摘要 |

写入规则：

- 组件只直接写自己拥有的源目录：agent 写 `agents/`，queue 写 `queues/`，watchdog 写 `watchdog/`，heartbeat 写 `heartbeats/`。
- `tasks/` 和 `summaries/` 由 Runtime Status Aggregator 写入；普通组件通过源状态和 events 间接影响它们。
- `events/` 只能 append，不允许重写历史事件。需要修正时追加 correction event。
- `leases/` 只能由 lease manager/runtime CLI 写入，不能由任意组件手写覆盖。
- `escalations/` 可以由组件或 aggregator 通过 runtime API 创建，但 resolution 必须记录 owner 和时间。

补充说明：

- `agents/*.json`：agent-owned 状态快照，替代旧 `.labline/status/agents/*.json` 的新项目位置。
- `jobs/*.json`：tmux/screen/slurm/ClearML/Modal/Vast/ssh 等 durable job handle。
- `queues/*.json`：experiment queue 或其他批量调度器的状态。
- `watchdog/*`：watchdog 观测结果，不放任务叙事本体。
- `pipelines/*.json`：机器可读 workflow phase state，替代新项目中的根目录 `PIPELINE_STATE.json`。
- `tasks/*.json`：Leader 默认读取的统一任务视图，建议由 runtime aggregator 写入，组件不直接覆盖。
- `events/*.jsonl`：append-only runtime event log。
- `leases/*.lock`：控制权锁，防止多个入口同时操作。
- `heartbeats/*.json`：外部 scheduler / local runner / bridge-triggered probe 的活跃状态。
- `escalations/*.json`：需要人类或 Leader 介入的异常。
- `summaries/current.*`：给 Leader / ChatOps / 用户看的聚合视图。

不纳入新 runtime 协议：

- legacy `.labline/feishu-control/`：由旧 Labline runner 产生，默认已被外部 `lark-channel-bridge` 替代，后续可以删除，不作为新协议兼容目标。
- `AGENTS.md`、`CLAUDE.md`、`project.yaml`、`.gitignore`、`.agents/`、`.claude/`：项目入口和 client/install surface，保持原位。
- `.labline/installed-skills*.txt`、`.labline/manifest.json`、`.labline/tools`：安装元数据，保持在 `.labline/` 非 runtime 区域。
- `.labline/traces/`、`.labline/meta/`：审计 trace 和 meta 优化输入，不作为 runtime 控制状态。
- `MANIFEST.md`、`findings.md`、实验/审查/论文 artifact：人类项目结构，保持原位，runtime 只引用路径。
- `.agents/`、`.claude/`、`.codex/`、client settings 和根目录 agent 入口文件：属于客户端/入口 surface，不迁入 runtime。
- `.gitignore`、`.git/`、Git hooks、release tag 记录：属于版本控制或仓库治理 surface，不迁入 runtime。

## Runtime Task Schema 草案

```json
{
  "schema_version": "0.1",
  "task_id": "exp_auair_anchor5_long300",
  "kind": "experiment",
  "execution_mode": "detached_job",
  "durability": "supervised",
  "observation": "enabled",
  "heartbeat": "escalation_gated",
  "status": "running",
  "owner": "deployer",
  "created_at": "2026-06-26T00:00:00Z",
  "updated_at": "2026-06-26T01:00:00Z",
  "next_expected_update": "2026-06-26T03:00:00Z",
  "next_check_reason": "long training heartbeat",
  "job_handles": [
    {
      "type": "tmux",
      "host": "gpu-server-1",
      "session": "auair_anchor5_task0_long300",
      "log": "refine-logs/auair_anchor5_task0_long300.log",
      "output_dir": "RGR-IOD/work_dirs/..."
    }
  ],
  "artifacts": [
    {
      "type": "checkpoint",
      "path": "work_dirs/.../best_coco_bbox_mAP_50_epoch_12.pth"
    }
  ],
  "metrics": {
    "best_epoch": 12,
    "bbox_mAP_50": 0.371,
    "latest_epoch": 21
  },
  "blocker": null,
  "escalation": null,
  "source_refs": [
    ".labline/runtime/agents/deployer-auair.json",
    ".labline/runtime/jobs/auair_anchor5_task0_long300.json",
    ".labline/runtime/watchdog/local/status/auair_anchor5_task0_long300.json"
  ],
  "last_ingested_at": "2026-06-26T01:00:00Z"
}
```

统一规则：

- 所有会执行的工作都进入 `Runtime Task` lifecycle，包含短任务、agent turn、远程部署、训练、论文生成等。
- 不再把“普通任务”和“长程任务”建成两套对象。差异通过能力字段表达：
  - `execution_mode`: `inline` / `agent_turn` / `detached_job`
  - `durability`: `ephemeral` / `resumable` / `supervised`
  - `observation`: `disabled` / `enabled`
  - `heartbeat`: `none` / `passive` / `escalation_gated`
- `/status`、`/tasks`、`/task <task_id>` 这类只读观察不是 Runtime Task。
- 只有 `durability=supervised` 的 Runtime Task 需要 Durable Task Supervisor；短任务也有 events、status 和 verdict，但不强制启动重型 supervisor。
- 历史文档中的 “long job/长程任务” 在新设计里只对应 `durability=supervised` 或 `execution_mode=detached_job` 的子集，不再是一套平行 lifecycle。

推荐状态枚举：

```text
new
dispatching
handoff_verifying
running
waiting_on_job
stale
anomaly
need_decision
recovering
completed
failed
cancelled
```

## Lease 机制

必须解决的问题：

- 交互式 Codex 正在操作时，外部 heartbeat 不应同时 `codex exec resume`。
- Feishu live injection 不应和 Codex CLI 人工输入同时发生。
- 多个 scheduler 不应同时修复同一个异常。

建议 lease 文件：

```json
{
  "schema_version": "0.1",
  "lease_id": "leader_session",
  "owner": "local-heartbeat",
  "pid": 12345,
  "host": "workstation",
  "acquired_at": "2026-06-26T00:00:00Z",
  "expires_at": "2026-06-26T00:10:00Z",
  "purpose": "resume leader session for escalation"
}
```

规则：

- 所有会修改 runtime 状态或控制 Codex session 的入口都必须先 acquire lease。
- 读状态不需要 lease。
- lease 必须有 TTL。
- 过期 lease 可以被抢占，但必须记录 event。
- 抢不到 lease 时，heartbeat 只能写入 skipped event，不能控制任务。
- heartbeat 写状态不等于唤醒 Leader；只有 escalation、due decision、terminal result 或用户显式 status request 才允许尝试 `codex exec resume`。

## Watchdog 升级方向

现有 watchdog 应升级为事件源，而不是只给 Leader 读 summary。

建议 watchdog 输出统一 event：

```text
task.healthy
task.no_change_but_healthy
task.stalled
task.dead
task.oom
task.error_log_detected
task.need_decision
task.recovered
```

原则：

- 正常情况只更新 task status 和 summary。
- 只有异常、过期、需要决策时写 `escalations/*.json`。
- Leader 不应每 1-2 小时主动读长日志。
- 日志深读只在 `anomaly` 或 `need_decision` 时触发。

## ChatOps 升级方向

Feishu/Lark 默认由外部 `lark-channel-bridge` 提供 transport。Labline runtime 不拥有 Feishu 会话，也不迁移 legacy `.labline/feishu-control/`。

ChatOps 默认不再作为“远程键盘”，而是作为 runtime status / approval / escalation 接口。

### 飞书作为未来交互入口

飞书可以成为用户最常用的远程交互入口，但它只能是 Runtime Interaction Entry，不是 workflow runtime、heartbeat owner、job supervisor 或项目状态源。

关键区分：

- **观察入口**：`/status`、`/tasks`、`/task <task_id>`、订阅进度卡片、查看 artifact pointers。只读 runtime state，不向 TUI 发消息，不 resume Leader，不抢 `leader_session` lease。
- **控制入口**：`/approve`、`/reject`、`/force-check`、`/interrupt`、`/resume`、`/launch`、`/pause-heartbeat`。必须转成 Runtime Control Intent，并按 scope 获取 lease 后才能执行。

目标交互模型：

- 飞书/Lark、local Codex CLI、shell、dashboard、scheduler 都读同一个 `.labline/runtime/`。
- 飞书默认展示 `summaries/current.md`、`tasks/*.json`、`escalations/*.json` 和必要 artifact pointers，不展示或维护自己的项目真相。
- TUI 里派发的 Runtime Task 要通过 runtime event/status 自动进入飞书观察订阅：TUI/Leader 写 `task.started`、capability profile、agent/job 状态和 `next_expected_update`，bridge 观察订阅读取这些状态并更新飞书卡片。
- 用户在飞书里发出的 `/approve`、`/reject`、`/force-check`、`/interrupt`、`/resume`、`/launch` 等命令先转成 Runtime Control Intent，再由 runtime CLI/API 检查 lease、写 event、触发对应动作。
- 飞书卡片和消息只是 projection。投递失败只影响 remote display，不改变 job/task 的真实 lifecycle verdict。
- live TUI injection 只保留为 emergency/manual 模式，不是默认交互路径。

### TUI 任务推送到飞书

这个方向是对的，但同步对象应是“任务状态”，不是 TUI 对话历史。

推荐链路：

```text
TUI Leader 派发任务
  -> runtime CLI/API 写 task.started event
  -> agent/job/queue/watchdog 持续写 .labline/runtime/*
  -> Runtime Status Aggregator 更新 tasks/*.json 和 summaries/current.*
  -> Feishu bridge 的 Remote Observation Subscription 发现变更
  -> bridge patch / send 飞书状态卡
```

边界：

- TUI 不需要知道飞书 chat_id，也不直接调用飞书 API。
- 项目 `.labline/runtime/` 不保存飞书 chat 私有身份；chat/task 订阅关系由 bridge 的 Remote Message Archive 或 bridge profile 私有状态维护。
- 同一台机器可以有多个 bridge 进程。每个 bridge 只处理自己 `home/profile/workspace` 下的 Remote Observation Subscription，不做全机全项目广播。
- 如果不同用户或不同 chat 都订阅了同一个 project/task，各自都会收到自己 bridge/profile 下的投影更新；这是预期行为。
- 如果同一用户重复启动了同一个 profile/workspace 的 bridge，需要用 subscription/projection delivery key 去重，避免同一张卡被两个同源 bridge 同时 patch。
- `task.started`、`task.updated`、`task.completed`、`task.failed`、`escalation.created` 这类 runtime event 是推送触发源；是否主动推送由 `observation` capability 和 bridge-owned subscription 共同决定。
- 飞书端 `/follow` 默认订阅当前项目的父任务聚合摘要，只主动推送重要阶段、terminal result、decision 和 escalation；`/follow <task_id>` 才订阅单个子任务细节，`/unfollow` 取消订阅。
- Remote projection 必须节流：普通进度默认 5-10 分钟 patch 一次，或在状态显著变化时 patch；重要阶段变化、terminal result、decision、escalation 立即推送。
- heartbeat 正常平台期只更新 runtime state 和 events，不产生用户可见推送；用户显式 `/status` 时可以读取并展示最新平台期状态。
- 子任务详情订阅可以比父任务摘要更细，但仍必须节流；普通进度只 patch 现有卡片，不开新消息。
- 如果没有订阅，TUI 任务仍正常运行，只是不主动推送到飞书；用户之后发 `/status` 仍可拉取当前状态。
- 推送失败只更新 Projection Delivery State，不改变 task status；bridge 后续可重试或在用户下次 `/status` 时补发摘要。
- terminal result 需要按粒度 fresh reply：父任务完成/失败/取消、decision、escalation、以及显式 `/follow <task_id>` 的子任务终态必须发新消息；默认 `/follow` 项目摘要下的普通子任务终态只 patch 父任务聚合卡，不开新消息。大量并行 seeds/ablations 只在批次完成、异常或需要决策时 fresh reply。

### 多端交互处理

多端问题的核心不是“谁是入口”，而是“谁有控制权、谁写事实、如何审计”。规则如下：

- **读状态并发**：任何入口都可以读 `summaries/`、`tasks/`、`events/`、`escalations/`，不需要 lease。
- **关注进度不打断**：如果用户在 tmux/TUI 里启动 Leader 并派发了任务，飞书端的进度查询必须走 Runtime Observation Entry：读取 `.labline/runtime/agents/`、`jobs/`、`tasks/`、`summaries/` 和 Remote Status Projection，而不是把“现在怎么样了”发送进 TUI。
- **多任务默认总览**：用户问“现在怎么样了”时，如果只有一个 running task，直接回答该 task；如果有多个 running task，默认返回项目总览，列出 running、blocked、need_decision、recently_completed 的任务摘要。只有消息引用任务卡、明确 task id/任务名，或当前 chat 订阅了具体 task 时，才优先回答单任务详情。
- **中途插话不打断**：任务运行中，飞书里的普通问题默认走 BTW Side Channel。bridge 可用最近 Remote Message Archive、Runtime Status Aggregator 摘要、Project Handoff Surface pointers 和只读文件片段回答；它不得修改项目文件、改变任务目标、推进 task、注入 TUI 或抢 `leader_session` lease。
- **BTW 可以连续对话**：围绕同一个 project 或 active task 的连续只读问答归入 bridge-owned BTW Thread。BTW Thread 可保留最近几轮问答、引用的 task、archive refs 和只读 project pointers；它不是 Runtime Task、Normal Project Interaction、Leader conversation 或 control session。建议 30-60 分钟无新消息、active task 终态、或用户明确开始新话题时关闭当前 BTW Thread。
- **远端消息先路由**：bridge 收到普通文本时必须先做 Remote Interaction Routing。显式命令优先；引用任务卡或包含 task id/任务名时绑定对应 task；运行中且语义是只读问题时走 BTW；无活跃任务或明确要求新工作时走 Normal Project Interaction；包含停止、重跑、改目标、改文件、审批等动作时走 Runtime Control Intent。
- **路由不确定时保守只读**：如果 bridge 无法判断普通文本是 BTW、Normal Project Interaction 还是控制动作，默认按 read-only BTW/observation 回答，不注入 Leader、不改 task、不创建新 task。回复里应说明“我按只读问题回答；如果你想改变正在跑的任务，请明确说停止/修改/重跑/新开任务”。
- **新工作不默认打断**：活跃任务运行中，用户发起新的 Normal Project Interaction 时，默认不打断当前任务。若新工作不共享冲突资源，可创建 sibling Runtime Task；若会占用同一 Leader、workspace、GPU、queue 或关键文件，先写成 `pending` interaction/task，并要求用户选择排队、并行或替换当前任务。会改变当前任务目标的消息不是新任务，而是 Runtime Control Intent。
- **BTW 只写诊断事实**：纯 BTW 问答完整内容写 bridge-owned Remote Message Archive，同时可向 `.labline/runtime/events` 追加最小诊断事件，例如 `btw.question_received`、`btw.answered`，只包含 archive ref、scope/task_id、read_only=true、changed_runtime_state=false、时间戳和路由理由。Runtime Status Aggregator 不得把 BTW 诊断事件解释为 task lifecycle、decision record 或 project truth。
- **插话升级为控制**：如果用户的问题实际要求改目标、追加需求、停止/继续/重跑、批准决策或修改文件，bridge 必须把它转成 Runtime Control Intent 或提示用户确认控制动作，不能伪装成只读 BTW 回答。
- **控制动作分级确认**：停止任务、取消队列、删除/覆盖结果、切换实验目标、大规模重跑等高风险动作必须二次确认；加 ablation、改配置、重跑单个子任务等中风险动作可先写成 `pending` Runtime Control Intent，等 Leader 或 lease 可用后处理；follow、跑完提醒等低风险动作可直接记录 intent 或更新 bridge-owned subscription。
- **写状态串行**：任何会修改 runtime state、恢复 Leader session、控制 heartbeat、启动/停止 task 的动作，都必须提交 Runtime Control Intent，并获取对应 lease。
- **按作用域加锁**：建议至少区分 `project_runtime`、`leader_session`、`task:<task_id>`、`heartbeat:<runner>` 这些 lease scope，避免一个无关动作锁住整个项目。
- **抢不到锁不强行执行**：Feishu 入口抢不到 lease 时返回“当前由本地/其他入口控制中”，并写 `intent.skipped` 或 `intent.pending` event；heartbeat 抢不到锁只做只读检查。
- **审批是 decision record**：飞书上的 approve/reject 只绑定一个 `decision_id` 或 `escalation_id`，不能变成 session-wide approve-all。
- **本地优先不等于本地唯一**：交互式 Codex 正在人工操作时，飞书可继续看状态和提交 pending intent，但不能直接插入输入；本地空闲或 lease 过期后，pending intent 才能被处理。
- **统一回显**：本地 CLI 发起的 task 也应该能被飞书看到；飞书发起的 control intent 也必须落到 runtime events，供本地 CLI 和后续 Leader session 看到。

建议命令：

```text
/status
/tasks
/task <task_id>
/btw <question>
/follow [task_id]
/unfollow [task_id]
/launch <workflow>
/approve <decision_id>
/reject <decision_id>
/interrupt <task_id>
/resume <task_id>
/force-check <task_id>
/pause-heartbeat
/resume-heartbeat
```

其中 `/status`、`/tasks`、`/task <task_id>` 默认是 observation command；`/btw <question>` 是只读 side question；没有命令前缀的普通文本由 Remote Interaction Routing 分类。只有用户明确使用控制命令，或 status/BTW 发现 terminal result / escalation 需要决策并且用户选择处理，才进入 control-intent 流程。
`/follow` 和 `/unfollow` 只修改 bridge-owned Remote Observation Subscription，不修改 project runtime truth，也不抢 `leader_session` lease。

建议 routing event：

```json
{
  "schema_version": "0.1",
  "event_type": "remote_message.routed",
  "source": {
    "entry": "feishu",
    "archive_ref": "bridge://profile/archive/msg_xxx"
  },
  "route": "observation",
  "btw_thread_id": "btw_20260626_001",
  "confidence": "high",
  "reason": "active_task_read_only_question",
  "target_task_id": "task_xxx",
  "changed_runtime_state": false,
  "requires_lease": false,
  "created_at": "2026-06-26T00:00:00Z"
}
```

routing event 只用于排错和审计，不保存消息正文、`chat_id`、`open_id` 或用户私有身份；这些属于 bridge-owned Remote Message Archive。`changed_runtime_state=false` 的 routing event 不参与 task lifecycle。若消息路由成控制动作，另写 `control_intent.submitted`。

建议 intent event：

```json
{
  "schema_version": "0.1",
  "event_type": "control_intent.submitted",
  "intent_id": "intent_20260626_001",
  "source": {
    "entry": "feishu",
    "archive_ref": "bridge://profile/archive/msg_xxx"
  },
  "action": "approve",
  "risk_level": "low",
  "confirmation_status": "not_required",
  "target": {
    "decision_id": "decision_exp_001"
  },
  "lease_scope": "leader_session",
  "status": "pending",
  "created_at": "2026-06-26T00:00:00Z"
}
```

intent 状态建议：

```text
submitted
pending
lease_acquired
applied
skipped
rejected
expired
failed
```

Live TUI injection 保留为 emergency/manual 模式，不作为默认路径。

## Codex CLI 使用边界

推荐模式：

- 交互式 Codex：用于设计、人工决策、复杂讨论。
- `codex exec`：用于一次性 worker turn。
- `codex exec resume <session_id>`：只用于 heartbeat/escalation 需要唤醒原 Leader session 时的一次性 turn，必须受 lease 保护。
- 长训练：作为 `execution_mode=detached_job` 的 Runtime Task，必须 detached 到 tmux/screen/slurm/queue/ClearML，不依赖 Codex 进程存活。
- heartbeat 可调用 short-lived monitor worker 做摘要，但 monitor worker 不拥有决策权；最终 decision 仍回到原 Leader session。

派发 `durability=supervised` 的 Runtime Task 时，worker 必须完成 handoff barrier：

```text
1. detached job 已启动
2. job handle 已写入 `.labline/runtime/jobs/`，并被 runtime aggregator 反映到 task json
3. tmux/screen/slurm/queue 状态可被外部检查
4. log/output_dir/checkpoint 路径存在或已登记
5. next_expected_update 已写入
6. watchdog/heartbeat 已注册
7. task.started / task.updated event 已追加到 `.labline/runtime/events/`
8. 如存在 Remote Observation Subscription，bridge 能通过 task_id 找到并更新对应投影
9. worker 自己退出
```

## CLI 草案

建议先做这些命令：

```bash
lane runtime init
lane status --json
lane status --brief
lane runtime event append --type task.started --task-id <id>
lane runtime task get <task_id>
lane runtime lease acquire <lease_id> --owner <owner> --ttl 600
lane runtime lease release <lease_id> --owner <owner>
lane heartbeat
lane escalate list
```

第一阶段可以先做 Python CLI，不急着做复杂服务。

## 分阶段实施计划

### Phase 0: Runtime root 与统一读取面

目标：建立 `.labline/runtime/` 目录、统一状态读取入口和 Leader 默认读取面，同时不破坏人类项目结构。

任务：

- 新增 `.labline/runtime/` 初始化逻辑。
- 实现 `lane status --json` / `lane status --brief`。
- 聚合以下状态源：
  - `.labline/status/agents/*.json` 或新路径 `.labline/runtime/agents/*.json`
  - watchdog summary/status
  - experiment queue `queue_state.json`
  - `.labline/runtime/pipelines/*.json`
  - 旧根目录 `PIPELINE_STATE.json` 仅作为迁移输入，不作为新项目协议
- 输出 `summaries/current.json` 和 `summaries/current.md`。
- `CLAUDE.md ## Pipeline Status` 保留为 shared human/AI summary，不迁入 runtime。

验收：

- 用户可以只看一个命令知道当前项目状态。
- Leader 不需要手动读多个状态文件。
- 新项目不创建根目录 `PIPELINE_STATE.json`。

### Phase 1: Lease 和 Heartbeat

目标：解决多入口并发控制问题。

任务：

- 实现 runtime lease acquire/release。
- 为 heartbeat、Codex exec resume、未来 ChatOps trigger 增加 lease 检查。
- 实现 `lane heartbeat`：
  - 只读状态。
  - 只检查 `heartbeat=passive` 或 `heartbeat=escalation_gated` 且已经 due 的 Runtime Task。
  - 不深读日志，除非 task due、terminal、anomaly 或 escalation 存在。
  - 抢不到 lease 时跳过控制动作。
  - 默认不 resume Leader，只有 escalation / due decision / terminal result / explicit status request 才唤醒。

验收：

- 同一个 leader session 不会被两个入口同时控制。
- heartbeat 可以安全定时运行。
- `heartbeat=escalation_gated` 的正常平台期不会定时唤醒 Leader。

### Phase 2: Watchdog Event 化

目标：从“定时读 summary”变成“异常触发唤醒”。

任务：

- Watchdog 写入 runtime events。
- Watchdog 在异常时生成 `escalations/*.json`。
- 正常平台期只记录 healthy/no_change，不唤醒 Leader。
- 定义 anomaly 到 decision 的映射。

验收：

- 长训练等 `heartbeat=escalation_gated` 任务的平台期不会反复打扰 Leader。
- tmux dead / OOM / NaN / stalled 会形成明确 escalation。

### Phase 3: Worker Adapter

目标：Codex/OpenCode/Claude Code/shell 都成为可替换 worker，但不让 worker 成为 runtime state owner。

任务：

- 定义 worker adapter 接口：
  - `dispatch(prompt, context, task_id)`
  - `resume(session_id, message)`
  - `interrupt(session_id)`
  - `status(session_id)`
- 先实现 CodexExecWorker。
- 后续接 OpenCodeWorker / ClaudeCodeWorker。
- monitor worker 可以准备证据摘要，但不能替代 Leader 做最终决策。

验收：

- 派任务不依赖交互式 TUI。
- 交互式 Codex 可以退出，外部 heartbeat 能恢复指定 session。

### Phase 4: Optional LangGraph Backend

目标：把 LangGraph 接成 orchestrator backend，而不是核心格式。

任务：

- LangGraph 节点只读写 Labline Runtime state。
- 每个节点必须是短生命周期、可重试、幂等。
- detached/supervised task 节点只负责 launch/check/recover，不持有训练进程。
- 保留 cron/APScheduler backend。

验收：

- 不安装 LangGraph 时，Labline 仍可运行。
- 安装 LangGraph 后，可以获得更清晰的状态转移和 human-in-the-loop。

### Phase 5: ChatOps 和 Dashboard

目标：用户可以通过 Feishu/Lark 或 dashboard 查看和干预，但 ChatOps 只是入口，不是 heartbeat owner 或 workflow runtime。

任务：

- `lark-channel-bridge` 或其他 bridge 命令改为调用 runtime CLI/API。
- 默认关闭 live TUI injection。
- 增加 `/status`、`/tasks`、`/approve`、`/force-check` 等命令。
- `/follow` 只创建或更新 bridge-owned Remote Observation Subscription；是否产生推送取决于 Runtime Task 的 `observation` capability。
- 可选：做一个简单 TUI / FastAPI / Streamlit dashboard。

验收：

- 手机端可以看状态、批准决策、触发检查。
- 不需要一直盯着 Codex leader 窗口。

## 开发 session 起始任务建议

建议给开发 session 的第一条任务：

```text
请在 Labline 中实现 Project Runtime State Root + Project Heartbeat Protocol 的最小版本：

1. 新增 .labline/runtime 目录约定。
2. 新增 Python CLI，优先放在 tools/labline_runtime.py 或合适位置。
3. 实现:
   - runtime init
   - status --json
   - status --brief
   - lease acquire/release
   - heartbeat dry-run
4. status 聚合现有:
   - .labline/status/agents/*.json
   - watchdog summary/status
   - experiment_queue queue_state.json
   - .labline/runtime/pipelines/*.json
   - root PIPELINE_STATE.json 只作为旧项目迁移输入
5. 所有写入必须 atomic。
6. 不要迁移 human/shared project files，不要移动 AGENTS.md / CLAUDE.md / project.yaml / MANIFEST.md / findings.md / idea-stage / refine-logs / review-stage / paper。
7. 不要纳入 legacy .labline/feishu-control；新协议默认外部 lark-channel-bridge。
8. 添加最小测试，覆盖:
   - runtime root 初始化
   - status 聚合
   - root PIPELINE_STATE.json 迁移输入但新项目不创建
   - stale agent 推导
   - lease TTL
   - heartbeat 抢不到 lease 时只读跳过
   - heartbeat 正常平台期不 resume Leader

目标不是重构整个 Labline，而是先提供一个统一、可恢复、可被外部 heartbeat 调用的 runtime state layer。
```

## 最终判断

Labline 的最佳升级路线不是“换成 LangGraph”，而是：

```text
先 Project Runtime State Root + Escalation-Gated Heartbeat
再 Worker Adapter
再 Optional Orchestrator
最后 ChatOps / Dashboard
```

这样可以保留 Labline 现在最强的部分：Markdown-first、Codex-first、科研流程技能、GPU 实验工具和 Feishu 入口，同时把最脆弱的部分，也就是 Leader 的在线焦虑和状态解释压力，转移给机器可验证的 runtime 协议。
