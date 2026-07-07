# Labline 全框架测试矩阵

> 创建时间: 2026-07-03
> 状态: dev-only 测试地图草案
> 适用对象: Labline framework 维护者、Dev Leader、Debugger、Real-Machine Tester、后续 cheap worker
> 定位: 从框架开发者视角列出 Labline 需要长期覆盖的测试面；不替代具体测试代码、realtest 日志或 release gate。

## 0. 目的

Labline 已经不是单个 CLI 或一组 skill，而是由项目初始化、Skill Graph、Runtime Task、Feishu/Lark 远程入口、部署、实验队列、文档治理和发布流程组成的框架。测试不能只看某个单元测试是否通过，而要覆盖这些系统之间的契约。

这份文档回答三个问题：

- 哪些模块必须测。
- 每类能力应该用什么层级测。
- 新功能要达到什么体验，才算和普通消息交互一样舒服。

本文是 dev-only 测试地图，后续真实验证结果应写入 `to-developer/logs/` 或 realtest 记录，再蒸馏到开发日志。用户项目，例如 `/aris/projects/visdrone-repro`，只能作为框架调试 canary，不属于框架仓库资产。

## 1. 测试层级

| 层级 | 名称 | 目标 | 典型入口 | 何时必须跑 |
|---|---|---|---|---|
| T0 | 静态一致性 | 文档、DAG、catalog、镜像、schema、引用不漂移 | `python tools/update_developer_docs.py --check-only`、catalog/DAG 生成器、secret scan | 改 docs、skills、templates、release/promote 相关文件 |
| T1 | 单元和契约测试 | 锁住工具函数、schema、CLI 子命令、文件协议 | `python -m pytest tests/test_*.py -q` | 改 `tools/`、`tests/`、runtime 协议、bridge helper |
| T2 | 本地 CLI smoke | 用临时项目跑真实命令，确认入口可用 | `lane project init`、`lane runtime init`、`lane status`、`lane debug runtime-smoke` | 改安装器、模板、runtime、status、heartbeat |
| T3 | 真实项目 canary | 在一个独立项目上验证框架不会污染项目内容 | `lane debug runtime-smoke --project PATH`、`lane debug longtask-smoke --project PATH` | 改 runtime、project update、doctor、debug smoke |
| T4 | Bridge fake integration | 不连真实飞书，用 fake archive/subscription 验证路由和投影语义 | `tests/test_labline_remote_observation.py` 等 | 改 Remote Observation、BTW、control intent、projection |
| T5 | Feishu/Lark 实机 UI | 真实 bot、真实 p2p/group、真实卡片/状态/中断体验 | `lane feishu doctor/start/status/restart/logs`、手机端手测记录 | 改 bridge、卡片、run UI、`/stop`、OAuth、lark-cli 交互 |
| T6 | 部署和 GPU 实机 | 容器、GPU、端口、proxy、共享资产、framework copy 正常 | deploy compose、3090 realtest、GPU doctor | 改 `deploy/`、GPU doctor、entrypoint、operations docs |
| T7 | 故障注入 | 断网、断 bridge、任务异常、lease 冲突、OOM、卡片投递失败后能恢复 | 手工脚本 + realtest 日志 | 改 supervisor、heartbeat、queue、bridge delivery、restart |
| T8 | Release gate | 确认用户可见能力、文档、changelog、promote 边界一致 | `tests/test_runtime_release_gate.py`、release tools | 准备 tag、promote、稳定发布 |

最低要求：

- 普通文档或 skill 小改：T0 + 受影响 T1。
- Runtime 或 Feishu 改动：T0 + runtime/bridge 相关 T1/T4 + 至少一个 T2。
- 远程交互体验改动：T0 + T4 + T5。
- 发布候选：T0 到 T8 中与 release scope 相关的全部 gate，并留下日志。

## 2. 模块覆盖总表

| 模块 | 风险 | 必测能力 | 现有锚点 | 缺口 |
|---|---|---|---|---|
| CLI / Project Lifecycle | 用户进不来、项目被污染、detach/update 破坏项目 | 新目录初始化、已有目录接入、update、doctor、detach、registry、dirty worktree | `tests/test_lane_cli.py`、install/update 相关 tests | 需要完整 project lifecycle e2e，覆盖 init -> use -> update -> detach -> re-init |
| Templates | 项目上下文和 skill/role 漂移 | `AGENTS.md`、`CLAUDE.md`、`project.yaml`、`.gitignore`、runtime 忽略规则 | install/template 相关 tests | 需要模板 golden diff 和 role contract 对齐检查 |
| User Skill Graph | agent 乱调用、用户 skill 和 Codex mirror 不一致 | frontmatter `invokes`、catalog、DAG、Codex/Claude mirror、shared references | `tests/test_skill_dag_contract.py`、`tests/test_skill_catalog.py`、`tests/test_codex_skill_mirror.py` | 需要更强的 body mention 分类和 role graph e2e |
| Role Contracts | Leader/Coder/Deployer/Writer/Reviewer 职责混乱 | 分发边界、Reviewer 独立性、status 责任、artifact 指针 | role shared references、skill tests | 需要 role contract matrix 的自动 lint |
| Dev Skills | dev-only 能力泄漏到用户项目 | `dev-*` 前缀、dev installer、dev catalog/DAG、用户 catalog 不出现 dev skill | `tests/test_dev_skill_installer.py`、`tests/test_dev_skill_surface.py` | 需要 dev skill fork lineage 检查 |
| Dev Runtime / Dev Agent Surface | provider config 泄密、cheap worker 越权改代码 | provider 配置不含 key、role binding、prompt log、scope audit、diff/test evidence | `tests/test_dev_runtime_cli.py`、`tests/test_worker_harness_contract.py` | dev agent backend 还需要真实 coding worker smoke |
| Runtime Core | 状态文件损坏、事件不可恢复 | `.labline/runtime/` init、atomic write、JSONL append、schema validation | `tests/test_labline_runtime_core.py` | 需要并发写和文件损坏恢复测试 |
| Runtime Task / Capability Profile | 短任务/长任务状态不一致 | task lifecycle、capability consistency、parent/child、terminal verdict | runtime core tests | 需要多子任务 aggregate 和 stale resume case |
| Status Aggregator / `lane status` | 用户看不到真实状态或误读派生状态 | agents/jobs/queues/watchdog/pipelines 汇总、`current.md`、`--brief` | runtime/status tests、`lane debug runtime-smoke` | 需要跨旧项目和新项目的迁移 fixture |
| Lease / Control Intent | 多入口同时控制任务 | TTL、抢占、release owner、high-risk confirmation、read-only no lease | runtime core tests | 需要本地 TUI + Feishu 同时控制的 realtest |
| Heartbeat | 长任务刷屏、漏报终态、误唤醒 Leader | passive healthy、escalation、terminal fresh reply gate、dry-run | runtime heartbeat tests、longtask smoke | 需要长时间平台期 no-spam 实机测试 |
| Remote Observation / Projection | 飞书显示和执行真相混淆 | follow/unfollow、delivery key、throttle、terminal fresh reply、identity leak 防护 | `tests/test_labline_remote_observation.py` | 需要真实 Lark 卡片 patch/final reply 验收 |
| Remote Routing / BTW | “现在如何了”打断 TUI，或 stop 被当作普通问题 | observation、BTW、normal interaction、control intent、引用卡片/task id 路由 | remote observation tests | 需要中文自然语言歧义路由集 |
| Feishu Bridge / lark-channel | 本地 bot 断连、profile 错乱、授权错绑 | install/doctor/start/status/restart/logs、p2p/group、OAuth、callback token | `tests/test_lane_feishu_bridge_cli.py`、`tests/test_lark_channel_bridge_labline_patch.py` | 需要定期真实 bot realtest 和断连恢复手册 |
| Run UI / Chat UX | 新功能体验差，不像普通消息 | working reaction、正在思考、卡片刷新、markdown fallback、fresh final reply、`/stop`、BTW side reply | bridge fake tests、当前手工调试 | 需要完整 UI parity checklist 和截图/消息证据 |
| Agent Status Stream | Leader 看不到子 agent 状态 | per-agent snapshot、events diagnostic、legacy read | `tests/test_agent_status.py` | 需要各 role skill 的实际写入 smoke |
| Experiment Queue / Watchdog | GPU 浪费、OOM/stale 不升级 | queue state、wave、retry、watchdog summary、runtime mirror、escalation | `tests/test_queue_manager_state.py`、`tests/test_watchdog.py` | 需要真实 GPU job 小任务故障注入 |
| Experiment Integrity | 结果不可审、claim 无证据 | dataset/split/metric/config/raw result/deviation/checkpoint/claim | `tests/e2e_drill/`、audit/claim skills | 需要 ledger schema + workflow e2e |
| MCP / External Integrations | server 路径、stdio、provider 失败 | codex-review、image2、llm-chat、minimax、exa/deepxiv 等 smoke | MCP/provider tests | 需要 MCP inventory + per-server doctor |
| Deploy | 容器和文档不一致 | compose、entrypoint、proxy、GPU、ports、shared assets、rollback | `tests/test_gpu_deploy_contract.py`、realtest container tests | 需要真实 3090 container 周期性验证 |
| Docs Governance | 新 dev 文档漏 DAG，stable/dev 边界污染 | `DOC_DAG.yaml`、generated mmd、stable doc DAG、developer docs coverage | `tools/update_developer_docs.py`、`tests/test_developer_doc_dag.py` | 需要 release 前 docs coverage 汇总 |
| Promote / Release | dev-only 资产进入 stable，tag 不可信 | promote candidate 类型、changelog、release tag dry-run/apply、stable gate | `tests/test_release_tools.py`、`tests/test_runtime_release_gate.py` | 需要一次完整 rc rehearsal |
| Compatibility / Migration | 老项目升级断裂 | legacy `.aris`、root `PIPELINE_STATE.json` 只读迁移、旧 status 读取 | compatibility tests、runtime status tests | 需要老项目 fixture 库 |

## 3. 端到端场景矩阵

| 场景 ID | 场景 | 覆盖模块 | 通过标准 | 证据 |
|---|---|---|---|---|
| E2E-01 | 新用户新目录初始化 | CLI、templates、skills、docs | 生成 runnable baseline，skill symlink 正常，doctor 通过 | 命令日志、生成文件列表、`project.yaml` 摘要 |
| E2E-02 | 现有项目接入和 detach | CLI、templates、registry、compat | 不删除项目内容，detach 后 framework managed surface 被移除 | before/after tree、registry diff |
| E2E-03 | framework update/reconcile | CLI、install、skills mirror | 更新 skill/tools symlink，不覆盖项目 override | update log、manifest、override 检查 |
| E2E-04 | Skill Graph 全量生成 | skills、docs、Codex mirror | catalog/DAG 稳定，正式边只来自 frontmatter | generated diff、pytest |
| E2E-05 | Dev Skill 安装面 | dev-skills、dev-user-surface | dev skill 只进 dev checkout，不进入用户项目 catalog | install log、catalog grep |
| E2E-06 | Runtime Core 最小项目 | runtime、status | `runtime init` 幂等，event append 正常，`lane status --brief` 可读 | `.labline/runtime` tree、summary |
| E2E-07 | 本地长任务 smoke | runtime task、heartbeat、lease、status | detached job 运行中健康，终态升级，source project 不被污染 | `lane debug longtask-smoke` report |
| E2E-08 | Watchdog/Queue 异常 | queue、watchdog、heartbeat | OOM/stale/dead 写 runtime event/escalation，status 可见 | queue state、watchdog summary、events |
| E2E-09 | Feishu p2p 普通任务 | bridge、run UI、Remote Session Inbox | 收到真实回复，有 working 状态，终态 fresh reply，可继续追问 | sanitized message ids、截图或文本摘录 |
| E2E-10 | Feishu group mention | bridge、routing、mentions | 只有真实 @ bot 才触发；不 @ 其他 bot；人类可见回复正常 | 群消息记录、routing log |
| E2E-11 | `/follow` 观察 TUI 发起任务 | remote observation、projection | 不注入 TUI，卡片按节流刷新，terminal 有新消息 | subscription record、delivery state、卡片截图 |
| E2E-12 | BTW side channel | routing、BTW、run UI | “现在如何了/顺便解释”不打断主任务，可连续只读问答 | `btw.*` events、主任务状态不变 |
| E2E-13 | `/stop` 和停止意图 | control intent、lease、run UI | plain `/stop` 可中断当前 BTW/managed run；“停掉任务”进入高风险 control intent | events、UI 回执、任务 verdict |
| E2E-14 | 卡片按钮回调 | lark-cli、callback signing、bridge session | 只有签名 token 的按钮回调到同一会话；无 token 只展示 | callback payload、bridge log |
| E2E-15 | 本地 bot 断连重启 | bridge、job service、logs | `status` 能定位 profile/agent/session；`restart` 后恢复消息收发，不丢 active projection | status before/after、logs |
| E2E-16 | OAuth 用户身份授权 | lark-cli、bridge profile | p2p device flow 成功，group 不发授权链接，strict/default-as 收敛后可重试 | auth log 摘要、禁止泄密检查 |
| E2E-17 | 真实项目 canary | project lifecycle、runtime、debug monitor | canary 项目可作为框架测试宿主，框架不把项目内容带回 repo | canary report、git diff 检查 |
| E2E-18 | 部署 3090 realtest | deploy、GPU、ops docs | compose 启动、端口可访问、GPU doctor 通过、debug smoke 通过 | server log、doctor output、cleanup log |
| E2E-19 | Release candidate rehearsal | docs、tests、promote、release | release gate 全绿，dev-only 不进 stable，CHANGELOG 只含用户可见项 | gate report、tag dry-run |

## 4. Feishu/Lark “普通消息一样舒服”验收清单

新功能接入 Feishu/Lark 时，不能只做到“能发消息”。必须和普通聊天任务的交互体验尽量一致。

| 能力 | 期望体验 | 必测项 | 失败判定 |
|---|---|---|---|
| 工作中反馈 | 用户发起任务后很快看到“正在处理”的明确反馈 | working reaction 或 active status segment 在数秒内出现；失败时有 fallback 文本 | 用户长时间无反馈，不知道 bot 是否收到 |
| 普通回复 | 普通短回答像正常消息一样直接可读 | markdown/text 正常换行，引用回复围绕 quoted message，p2p/group 都可用 | 只改旧卡片，没有新消息；或把 bridge XML 元数据吐给用户 |
| 卡片状态 | 长任务有状态卡，但不刷屏 | 卡片 patch 节流，阶段边界开新 segment，terminal fresh reply | 每次 heartbeat 发新卡；终态只改旧卡片导致用户没通知 |
| 回复表情/反应 | 支持用 reaction 或等价轻量反馈表示已收到/工作中/完成 | 发送、更新、清理或降级路径都有日志 | reaction 失败导致主流程失败 |
| 正在思考 | managed run 显示 active/running，而非沉默 | active run state 与 runtime task 状态一致 | run 已开始但 projection 仍显示 idle |
| 可刷新状态 | 用户问“现在如何了”走只读状态，不打断任务 | observation/BTW 路由，`lane status` 或 projection summary 被读取 | 状态问题被注入 TUI，改变主任务上下文 |
| 可中断 | `/stop` 或明确停止请求有清晰语义 | plain `/stop` 中断当前 bridge-managed side run；停止任务生成 control intent | stop 被当普通聊天回答，或直接无记录 kill 进程 |
| BTW 旁路 | 活跃任务中可问只读问题 | BTW thread 只读回答，不写项目状态，不注入 Leader | 旁路问答修改文件或推进任务 |
| 按钮回调 | 交互按钮安全回到同一会话 | `__bridge_cb` + `bridge_token` 由 lark-cli 签名；payload 清洗 | 手写 token、复用 token、点击后丢 session |
| 身份和隐私 | 项目 runtime 不保存 chat/open id/token | `.labline/runtime/` grep 不到身份字段；archive 在 bridge-owned state | chat id/open id/token 出现在项目文件或日志 |
| 掉线恢复 | 本地 bot/bridge 断连后可诊断和恢复 | doctor/status/logs 给出 profile、agent、pid、日志路径；restart 不破坏任务真相 | 用户只看到“连不上”，没有可执行诊断路径 |

这些验收至少需要一份真实 Feishu/Lark p2p 记录。可以用截图、脱敏 message id、bridge log 摘要和 runtime events 作为证据，但不得把 token、open id、chat id 明文写进项目 runtime 或公开日志。

## 5. 故障注入清单

| 故障 | 预期行为 | 覆盖测试 |
|---|---|---|
| bridge 进程退出 | active Runtime Task 继续由项目 runtime/job handle 表示；重启后可重新发现或至少可诊断 | E2E-15 |
| Feishu 卡片 patch 失败 | 只更新 Projection Delivery State，不改变 task terminal verdict | T4/T5 |
| heartbeat 平台期连续触发 | 写健康检查事件或 heartbeat 状态，不可刷屏、不唤醒 Leader | E2E-07 |
| terminal result 到达 | 写 terminal/escalation，允许 fresh final reply | E2E-07/E2E-11 |
| lease 被占用 | control/heartbeat 跳过并写 skipped，不并发修改 | runtime lease tests |
| 用户发“停掉” | 转高风险 control intent，等待 Leader/确认路径 | E2E-13 |
| 用户发“现在怎么样” | 只读 observation/BTW，不注入主 TUI | E2E-12 |
| lark-cli 未绑定 bridge context | 停止操作并提示重启 bridge/doctor，不绕过 profile | Feishu realtest |
| group 里要求 OAuth | 不启动 auth login，提示去 p2p | OAuth realtest |
| job OOM/stale | queue/watchdog 写状态，heartbeat 升级，status summary 显示 | E2E-08 |
| source project dirty | debug smoke 默认 copy mode，不直接改源项目；in-place 需要显式 `--yes` | debug smoke tests |
| generated docs 过期 | check-only 失败，阻止完成 | T0 |

## 6. Release Gate 建议

### 每次 PR 或开发任务最小 gate

1. 跑受影响测试文件。
2. 跑 `python tools/update_developer_docs.py --check-only`，如果改了 `to-developer/`。
3. 如果改 skill 或 mirror，跑 skill DAG/catalog/mirror 测试。
4. 如果改 CLI/runtime，跑对应 `lane` smoke。
5. 输出 `changed_files`、`tests_run`、`known_gaps`。

### Runtime / Feishu 改动 gate

1. Runtime core/status/task/lease/heartbeat 相关 pytest。
2. Remote observation/routing fake integration tests。
3. `lane debug runtime-smoke --project <canary>`。
4. 至少一次 p2p realtest，覆盖普通消息、状态查询、终态回复、`/stop` 或 BTW。
5. grep 项目 runtime，确认没有 chat/open id/token。

### Minor release gate

1. T0 全部通过。
2. 全量或代表性 pytest 通过。
3. 新目录 project init smoke 通过。
4. 真实项目 canary runtime smoke 通过。
5. 若 release 包含 Feishu/remote UX，必须有 T5 证据。
6. 若 release 包含 deploy/GPU，必须有 T6 证据。
7. `CHANGELOG.md` 只写用户可见变化。
8. `to-developer/` 不进入 stable promote 输出。
9. release tag dry-run 通过。

## 7. 当前优先级

### P0: 先补能防止用户卡住的测试

- Feishu/Lark 本地 bot 断连诊断和 restart realtest。
- Run UI parity：working reaction、正在思考、状态卡刷新、terminal fresh reply、`/stop`。
- “现在如何了” observation/BTW 路由，确保不打断主任务。
- `lane debug runtime-smoke` 和 `lane debug longtask-smoke` 在真实 canary 项目上的周期性验证。
- `to-developer/DOC_DAG.yaml` 覆盖所有新增 dev 文档。

### P1: 补全框架主干回归

- project lifecycle e2e：init/update/doctor/detach/re-init。
- skill graph/mirror/catalog 全量 gate。
- Runtime Task parent/child aggregate 和 stale resume。
- Watchdog/queue 故障注入。
- deployment 3090 path realtest。

### P2: 补全科研可信度和发布演练

- Experiment Integrity ledger schema 和 workflow e2e。
- 老项目 migration fixture。
- full release candidate rehearsal。
- MCP server inventory 和 per-server doctor。

## 8. 建议新增或强化的测试文件

| 建议文件 | 用途 |
|---|---|
| `tests/test_project_lifecycle_e2e.py` | 覆盖 init/update/doctor/detach/re-init 和 source project safety |
| `tests/test_template_contract.py` | 模板 golden diff、runtime ignore、role contract 引用 |
| `tests/test_role_contract_lint.py` | 检查 role skill 是否声明 status/artifact/reviewer 独立边界 |
| `tests/test_feishu_run_ui_parity.py` | fake 或可注入 renderer 层验证 working、card patch、fresh reply、stop |
| `tests/test_feishu_callback_signature.py` | 验证 callback button 必须使用 bridge-signed token |
| `tests/test_remote_routing_chinese_cases.py` | 中文自然语言 observation/BTW/control/normal 路由集 |
| `tests/test_runtime_concurrency.py` | atomic write、lease 竞争、并发 event append |
| `tests/test_runtime_migration_fixtures.py` | legacy `.labline/status`、root `PIPELINE_STATE.json`、`.aris` 迁移 |
| `tests/test_experiment_integrity_workflow.py` | plan/run/result/claim/checkpoint 证据链 |
| `tests/test_mcp_inventory.py` | MCP server inventory、路径、stdio/import safety、doctor |

## 9. 测试记录格式

每次 realtest 或大 gate 最少留下这些字段：

```text
date:
framework_commit:
branch:
workspace:
project:
scope:
commands_run:
tests_run:
manual_checks:
artifacts:
sanitized_remote_evidence:
pass:
known_gaps:
follow_up:
```

远程证据必须脱敏。可以记录：

- bridge profile 名称。
- agent 类型。
- 脱敏 message id 或 projection id。
- runtime task id。
- 日志路径。
- 卡片截图或文字摘要。

不得记录：

- app secret、user token、tenant token。
- 原始 open id、chat id。
- OAuth device code。
- 未脱敏的用户私聊全文。

## 10. 与现有文档关系

- `CONTEXT.md` 定义测试中必须使用的 Runtime Task、Remote Status Projection、BTW、Control Intent、Project Runtime State 等术语。
- `to-developer/20260617-FRAMEWORK_TOP_LEVEL_DESIGN.md` 定义模块优先级和顶层路线。
- `to-developer/20260615-FRAMEWORK_MODULES.md` 定义开发日志和模块归属。
- `to-developer/plans/20260629-RUNTIME_HEARTBEAT_IMPLEMENTATION_PLAN.md` 定义 runtime/heartbeat/Feishu projection 的分阶段实现和验收。
- `docs/FRAMEWORK_STRUCTURE.md` 定义 framework/project/dev 边界，测试时必须防止 dev-only 资产进入用户项目或 stable。
- `to-developer/logs/` 应保存后续验证日志，本文件只作为测试地图和覆盖要求。
