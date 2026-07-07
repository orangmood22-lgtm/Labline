# Runtime Heartbeat / Feishu Projection 实施计划

> 创建时间: 2026-06-29
> 状态: dev-only implementation plan
> 适用对象: Labline framework 维护者、Dev Leader、实现 runtime/bridge 的开发 agent
> 上游设计: `to-developer/discussions/20260626-LABLINE_RUNTIME_UPGRADE_PLAN.md`、`CONTEXT.md`

本文把 Runtime Task、Project Heartbeat Protocol、Feishu/Lark Remote Observation、BTW Side Channel 和 Runtime Control Intent 收敛成可执行的实现步骤。讨论文档负责解释为什么这样设计；本文只回答按什么顺序做、每步交付什么、怎么验收。

## 0. 实施原则

1. 先做项目内 runtime 文件协议，再做 Feishu 投影。
2. 先做只读状态和事件，再做控制 intent 和 resume。
3. 先支持现有 agent status、watchdog、experiment queue，再引入新 orchestrator。
4. Feishu/Lark 只作为 Runtime Interaction Entry 和 Remote Status Projection，不写入项目真相，不持有 heartbeat。
5. 所有会执行的工作统一为 Runtime Task；短任务和长任务差异只由 capability profile 表达。
6. BTW 连续问答属于 bridge-owned BTW Thread，不是 Runtime Task，也不改变项目状态。
7. 每个 phase 都必须有可自动跑的最小测试；没有测试的行为不能进入下一阶段作为依赖。

## 1. 最小总体目标

第一轮完成后，Labline 应满足：

- `lane runtime init` 能在项目内创建 `.labline/runtime/` root。
- `lane status --json` / `lane status --brief` 能从 agent、job、queue、watchdog、pipeline 状态聚合当前项目状态。
- Runtime Task 有统一 schema、capability profile、事件和派生摘要。
- heartbeat 可以定时读状态、识别 due/escalation/terminal，但正常平台期不会唤醒 Leader。
- control intent 通过 lease 串行化，避免本地 TUI、Feishu、scheduler 同时改同一任务。
- lark-channel-bridge 可以只读订阅 runtime 状态，按 `/follow`、节流、terminal fresh reply 规则更新飞书。
- 普通飞书插话默认先路由：observation / BTW / normal project interaction / control intent。
- 项目 `.labline/runtime/` 不保存 chat id、open id、Feishu token、私有 archive 内容。

## 2. 架构切片

| 切片 | 主要路径 | 职责 |
|---|---|---|
| Runtime Core | `tools/labline_runtime.py`, `tools/lane` | 初始化 runtime root、atomic JSON/JSONL、schema validation、event append |
| Status Aggregator | `tools/labline_runtime.py` 或独立模块 | 读取 component-owned state，写 `tasks/` 和 `summaries/` |
| Runtime Task Layer | `.labline/runtime/tasks/`, `.labline/runtime/events/` | task schema、capability profile、parent/child task、terminal verdict |
| Lease / Intent | `.labline/runtime/leases/`, `.labline/runtime/escalations/`, events | 控制权、pending intent、risk-level confirmation、scope lock |
| Heartbeat Runner | `lane heartbeat`, `.labline/runtime/heartbeats/` | due check、platform event、escalation、可选 resume gate |
| Component Adapters | `tools/agent_status.py`, `tools/watchdog.py`, `tools/experiment_queue/*` | 将旧/现有状态接入 runtime，不改变组件源数据所有权 |
| Remote Observation Contract | bridge-owned archive/subscription/delivery state | `/follow`、投影节流、dedupe、terminal fresh reply |
| Remote Routing | bridge-side router + runtime diagnostic events | BTW Thread、Normal Project Interaction、Runtime Control Intent |

## 3. Phase 0: Contract 和测试脚手架

目标：先冻结最小 schema 和测试入口，避免后续实现把边界写散。

交付：

- 新增 runtime schema fixture：
  - `tests/fixtures/runtime/task_minimal.json`
  - `tests/fixtures/runtime/task_supervised.json`
  - `tests/fixtures/runtime/event_remote_routed.json`
  - `tests/fixtures/runtime/control_intent_submitted.json`
- 新增 runtime 测试文件：
  - `tests/test_labline_runtime_core.py`
  - `tests/test_labline_runtime_status.py`
  - `tests/test_labline_runtime_heartbeat.py`
- 明确 `.labline/runtime/` 子目录和写入责任，和讨论文档保持一致。
- 明确旧路径兼容策略：
  - `.labline/status/agents/*.json` 是迁移/兼容输入。
  - 根目录 `PIPELINE_STATE.json` 只作为旧项目迁移输入。
  - legacy `.labline/feishu-control/` 不进入新协议。

验收：

```bash
python -m pytest tests/test_labline_runtime_core.py -q
python tools/update_developer_docs.py --check-only
```

第一批测试可以先是红灯，作为 Phase 1 的 TDD 锚点。

## 4. Phase 1: Runtime Core 最小实现

目标：建立可恢复、可 append、可被其他工具调用的项目 runtime 文件层。

交付：

- 新增 `tools/labline_runtime.py`。
- 在 `tools/lane` 增加命令入口：
  - `lane runtime init`
  - `lane runtime event append --type <event_type> [--task-id <task_id>] [--json <payload>]`
  - `lane runtime task get <task_id>`
  - `lane runtime task list`
- 实现 atomic write：
  - JSON 写临时文件后 `rename`。
  - JSONL 只 append，不重写历史。
  - 所有事件含 `schema_version`、`event_id`、`event_type`、`created_at`、`source`。
- 创建目录：
  - `agents/`, `jobs/`, `queues/`, `watchdog/`, `pipelines/`, `tasks/`, `events/`, `leases/`, `heartbeats/`, `escalations/`, `summaries/`。
- Runtime root 初始化必须幂等。

验收：

- 空项目运行 `lane runtime init` 后目录完整。
- 重复运行不覆盖已有状态。
- `event append` 只追加 `events/runtime.jsonl`。
- 非法 JSON payload 明确失败，不写半截文件。

## 5. Phase 2: Status Aggregator 和 `lane status`

目标：让 Leader 和用户不用再手动读多个状态文件。

交付：

- 新增：
  - `lane status --json`
  - `lane status --brief`
  - `lane runtime summarize`
- Aggregator 读取：
  - `.labline/runtime/agents/*.json`
  - `.labline/status/agents/*.json`
  - `.labline/runtime/jobs/*.json`
  - `.labline/runtime/queues/*.json`
  - `.labline/runtime/watchdog/**/summary.json`
  - `.labline/runtime/pipelines/*.json`
  - root `PIPELINE_STATE.json` 只读迁移输入
- Aggregator 写派生视图：
  - `.labline/runtime/tasks/*.json`
  - `.labline/runtime/summaries/current.json`
  - `.labline/runtime/summaries/current.md`
- `current.md` 面向人类扫描，必须短，包含 running / blocked / need_decision / recently_completed。

验收：

- 只有旧 `.labline/status/agents/*.json` 时也能生成 summary。
- 多个 running task 时 `--brief` 给项目总览，不强行选择单任务。
- 新项目不会创建 root `PIPELINE_STATE.json`。
- 派生文件标记 `derived: true` 或等价字段，避免被误当源数据。

## 6. Phase 3: Runtime Task Lifecycle 和 Capability Profile

目标：统一短任务、agent turn、detached job、supervised job 的 task 表达。

交付：

- 实现 task schema validation：
  - `execution_mode`: `inline | agent_turn | detached_job`
  - `durability`: `ephemeral | resumable | supervised`
  - `observation`: `disabled | enabled`
  - `heartbeat`: `none | passive | escalation_gated`
  - `status`: `new | dispatching | handoff_verifying | running | waiting_on_job | stale | anomaly | need_decision | recovering | completed | failed | cancelled`
- 实现 task event helpers：
  - `task.created`
  - `task.started`
  - `task.updated`
  - `task.completed`
  - `task.failed`
  - `task.cancelled`
- 支持 parent/child task：
  - parent 聚合 child 状态。
  - `/follow` 默认观察 parent/project aggregate。
  - 显式 task follow 才观察 child 细节。
- capability consistency 检查：
  - `heartbeat != none` 必须有 `next_expected_update` 或明确 due policy。
  - `execution_mode=detached_job` 必须有至少一个 job handle 或 pending handoff。
  - `durability=ephemeral` 不应声明 supervised-only job handle。

验收：

- 短 inline task 可写事件和终态，但不需要 heartbeat。
- detached supervised task 必须通过 handoff barrier 才能进入 `waiting_on_job`。
- child terminal 默认只更新 parent aggregate；显式 follow child 时才要求 fresh reply。

## 7. Phase 4: Lease 和 Runtime Control Intent

目标：让本地 CLI、TUI、Feishu、scheduler、heartbeat 多入口能同时观察，但不能同时修改。

交付：

- 实现：
  - `lane runtime lease acquire <scope> --owner <owner> --ttl <seconds> --purpose <text>`
  - `lane runtime lease release <scope> --owner <owner>`
  - `lane runtime lease status [scope]`
- lease scope 至少支持：
  - `project_runtime`
  - `leader_session`
  - `task:<task_id>`
  - `heartbeat:<runner>`
- 实现 intent event schema：
  - `control_intent.submitted`
  - `control_intent.applied`
  - `control_intent.skipped`
  - `control_intent.failed`
- 风险级别：
  - high: stop/cancel/delete/overwrite/switch objective/big rerun，必须二次确认。
  - medium: add ablation/change config/rerun child，先 pending，由 Leader/lease 处理。
  - low: follow/remind/status，直接更新 bridge-owned subscription 或记录低风险 intent。

验收：

- 未过期 lease 不能被无 owner 覆盖。
- 过期 lease 可抢占，但必须追加 `lease.stolen` 或等价事件。
- heartbeat 抢不到 lease 时只写 skipped，不执行 control。
- read-only status 不需要 lease。

## 8. Phase 5: Escalation-Gated Heartbeat

目标：把“定时等 Leader 看状态”改成“外部 probe 只在必要时升级”。

交付：

- 新增：
  - `lane heartbeat`
  - `lane heartbeat --dry-run`
  - `lane heartbeat --task <task_id>`
- Heartbeat 只检查：
  - `heartbeat=passive` 或 `heartbeat=escalation_gated`
  - 当前时间超过 `next_expected_update`
  - 或用户显式 `/status` / `/force-check`
- 平台期行为：
  - 读取 agent/job/queue/watchdog 状态。
  - 写 `heartbeat.checked` 或 `task.no_change_but_healthy`。
  - 更新 `.labline/runtime/heartbeats/<runner>.json`。
  - 不 resume Leader。
  - 不发 visible push，除非用户显式 status。
- 升级行为：
  - terminal result、need_decision、anomaly、stalled、dead、OOM、NaN 等写 `escalations/*.json`。
  - 需要唤醒 Leader 时先 acquire `leader_session` 或 `task:<task_id>` lease。
  - `codex exec resume` 只允许在 escalation/due decision/terminal/explicit status 的 gate 后执行。

验收：

- 正常训练 10 次 heartbeat 不产生 10 条飞书消息。
- terminal result 会写 escalation/terminal event，并允许 remote projection fresh reply。
- 抢不到 lease 时不会 resume。
- `--dry-run` 不写状态，输出将执行动作。

## 9. Phase 6: 现有组件 Adapter

目标：接入已有工具，不要求一次重写它们。

交付：

- `tools/agent_status.py`
  - 新项目默认写 `.labline/runtime/agents/*.json`。
  - 保留旧 `.labline/status/agents/*.json` 读取兼容。
- `tools/watchdog.py`
  - 正常健康写 observation/status。
  - 异常写 runtime event 和 escalation。
  - 不直接唤醒 Leader。
- `tools/experiment_queue/queue_manager.py`
  - 将 queue state mirror 到 `.labline/runtime/queues/<queue_id>.json` 或让 aggregator 直接读取 queue state。
  - OOM/stale/retry 写事件。
- `leader` / `paper-talk` 等 workflow skill
  - 新项目写 `.labline/runtime/pipelines/<workflow>.json`。
  - 人类可读阶段状态继续写 shared surface。

验收：

- 旧项目只升级工具也能被 `lane status` 读到。
- queue OOM retry 能进入 runtime summary。
- watchdog dead/stalled 能进入 escalation。
- skills 不再创建新 root `PIPELINE_STATE.json`。

## 10. Phase 7: Remote Observation / Feishu Projection Contract

目标：让飞书能看 TUI 发起的任务进度，但不成为任务 owner。

交付在 bridge 侧，项目内只定义 contract：

- bridge-owned state：
  - Remote Message Archive
  - Remote Observation Subscription
  - Projection Delivery State
  - BTW Thread records
- project-visible references：
  - `archive_ref`
  - `task_id`
  - `projection_id` 或 delivery key 摘要，不含 chat/open id
- `/follow`
  - 默认订阅 parent task/project aggregate。
  - `/follow <task_id>` 订阅 child/detail。
  - `/unfollow` 只改 bridge-owned subscription。
- 推送节流：
  - 普通进度 5-10 分钟 patch 一次或状态显著变化。
  - decision/escalation/terminal 立即推送。
  - heartbeat 平台期不 visible push。
- fresh reply：
  - parent terminal、decision、escalation、显式 child follow terminal 发新消息。
  - 默认 parent aggregate 下普通 child terminal 只 patch aggregate。
- dedupe：
  - 同 profile/workspace/subscription/projection 使用稳定 delivery key。
  - 多 bridge 进程同源重复启动不能重复 patch 同一投影。

验收：

- 项目 `.labline/runtime/` 中 grep 不到 chat id/open id/token。
- bridge 投递失败只更新 delivery state，不改变 task terminal verdict。
- 无 subscription 时任务正常运行；用户之后 `/status` 可拉取 summary。

## 11. Phase 8: Remote Interaction Routing / BTW / Normal Project Interaction

目标：解决用户中途发普通消息时，如何不打断正在跑的任务。

交付：

- 路由顺序：
  1. 显式命令。
  2. 引用任务卡、task id、任务名。
  3. 明确控制动作。
  4. 活跃任务中的只读问题 -> BTW。
  5. 无活跃任务或明确新工作 -> Normal Project Interaction。
  6. 不确定 -> read-only BTW/observation。
- Runtime diagnostic events：
  - `remote_message.routed`
  - `btw.question_received`
  - `btw.answered`
- BTW Thread：
  - bridge-owned。
  - 可连续对话。
  - 建议 30-60 分钟无新消息、active task 终态、或用户明确新话题时关闭。
  - 只保存 archive refs、scope、task_id、read_only、route reason。
- Normal Project Interaction：
  - 若与当前任务不冲突，可创建 sibling Runtime Task。
  - 若冲突 Leader/workspace/GPU/queue/关键文件，写 pending interaction/task 并让用户选排队/并行/替换。
  - 若改变当前任务目标，转 Runtime Control Intent。

验收：

- “现在怎么样了”不会注入 TUI。
- “顺便解释一下结果含义”默认 BTW，可连续追问。
- “停掉这个实验”不会作为 BTW 回答，必须进入 control intent。
- routing event 不保存消息正文或 Feishu 身份。

## 12. Phase 9: 文档、兼容和发布准备

目标：实现稳定后再把用户可见部分蒸馏到 stable docs。

交付：

- stable docs 更新候选：
  - `docs/OPERATIONS_GUIDE.md`
  - `docs/FEISHU_INTEGRATION.md`
  - `docs/TOOLS_INDEX.md`
  - `docs/PROJECT_FILES_GUIDE.md`
- dev docs 更新：
  - `to-developer/20260613-DEVELOPMENT_LOG.md`
  - 必要 ADR 或 validation log。
- release gate：
  - runtime CLI tests
  - lane CLI smoke
  - Feishu bridge contract tests with fake archive/subscription
  - project init smoke 确认新项目不写 root `PIPELINE_STATE.json`

验收：

- 用户文档只暴露稳定命令和行为，不暴露 dev-only debate。
- `to-developer/DOC_DAG.yaml` 覆盖新增 dev docs。
- 若进入 stable，`CHANGELOG.md` 只写用户可感知能力。

## 13. 测试矩阵

| 测试 | 覆盖 |
|---|---|
| `tests/test_labline_runtime_core.py` | init、atomic write、event append、schema validation |
| `tests/test_labline_runtime_status.py` | aggregator、旧 agent status、pipeline migration input、summary |
| `tests/test_labline_runtime_task.py` | capability profile、parent/child、terminal verdict |
| `tests/test_labline_runtime_lease.py` | TTL、steal、release owner、read-only no lease |
| `tests/test_labline_runtime_heartbeat.py` | due detection、platform no resume、escalation、dry-run |
| `tests/test_runtime_adapters.py` | agent_status、watchdog、queue adapters |
| `tests/test_feishu_runtime_projection.py` | subscription、delivery dedupe、throttling、terminal fresh reply |
| `tests/test_remote_interaction_routing.py` | observation/BTW/normal/control routing、diagnostic events |

## 14. 第一张实现票

第一张票只做 Phase 0 + Phase 1 的一半，避免一口吃下 bridge 和 heartbeat：

```text
实现 Labline Runtime Core v0：

1. 新增 tools/labline_runtime.py。
2. 实现 runtime root discovery 和 lane runtime init。
3. 实现 atomic JSON write / JSONL append helper。
4. 实现 lane runtime event append。
5. 补 tests/test_labline_runtime_core.py：
   - init creates expected dirs
   - init is idempotent
   - event append writes runtime.jsonl
   - invalid payload fails without partial write
6. 不实现 Feishu、heartbeat resume、watchdog adapter。
```

第一张票通过后，再做 `lane status`；`lane status` 通过后，再做 task/capability；最后才接 heartbeat 和 bridge projection。

## 15. 暂缓事项

- LangGraph / Temporal / Prefect 只作为后续 orchestrator backend，不进入第一轮实现。
- dashboard 可选；先不做 UI。
- live TUI injection 保留 emergency/manual，不作为默认 Feishu 交互。
- Durable Task Supervisor 的完整本地服务可在 Runtime Task schema 和 heartbeat 稳定后再实现。
- `codex exec resume` 自动唤醒必须等 lease、escalation 和 fake-session 测试都稳定后再打开。
