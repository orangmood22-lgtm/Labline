# Labline 顶层设计与开发地图

> 创建时间: 2026-06-17  
> 状态: dev-only 顶层设计草案  
> 适用对象: Labline framework 维护者、Codex/Claude 开发 agent、reviewer、未来 cheap worker  
> 定位: 人和机器共用的全局参考，不替代各模块细节文档

## 0. 为什么需要这份文档

Labline 已经长出很多功能: project init、framework update、skill DAG、Codex/Claude 兼容、Agent Status Stream、Feishu session、experiment integrity、developer skills、cheap worker、realtest container、promote/release 等。

现在的问题不是没有功能，而是:

- 每个功能都有局部实现，但全局边界不够清楚。
- 人和 agent 容易把 user-facing、dev-only、runtime state、workflow engine、skill graph 混在一起。
- 很多计划散在 `to-developer/plans/`、ADR、`CONTEXT.md` 和 skill 文档里，开发时容易漏上下文。
- 后续接 cheap coding worker 后，如果没有顶层地图，worker 会局部修补但破坏整体结构。

因此本文定义 Labline 的顶层模块、模块接口、重要性、开发优先级和下一步计划。它是开发全局信息入口。

## 1. 一句话架构

Labline 是一个面向科研项目的 agentic research framework:

```text
用户 / 研究项目
  -> Labline CLI 初始化和更新项目
  -> Project Template 安装 Codex/Claude 可读上下文
  -> User Skill Graph 驱动 Leader/Coder/Deployer/Writer/Reviewer
  -> Project Runtime State 记录状态、实验透明度和可审 artifact
  -> 可选 Feishu / remote control / workflow runtime 辅助长任务

框架开发者
  -> Dev Skills / Dev Runtime / Dev Agent / 文档 DAG / promote gate
  -> 在 dev line 中开发、验证、记录
  -> 成熟后 promote 到 stable line
```

核心目标不是让所有 agent 自动乱跑，而是让科研工作 **可初始化、可委派、可观测、可审查、可复现、可回退**。

## 2. 分层模型

Labline 必须长期保持四层分离:

| 层 | 名称 | 主要对象 | 是否进入用户项目 | 是否进入 stable | 说明 |
|---|---|---|---|---|---|
| L0 | Framework Stable | `skills/`, `tools/`, `templates/`, `docs/`, `deploy/` | 间接安装 | 是 | 用户可 pin 的正式框架 |
| L1 | Research Project | `project.yaml`, `AGENTS.md`, `.agents/skills`, `.labline/status` | 是 | 否 | 每个科研项目自己的工作目录 |
| L2 | Framework Dev | `to-developer/`, dev skills, dev runtime, tests | 否 | 否 | 框架维护用，不给普通项目安装 |
| L3 | Runtime / External | Feishu bridge, MCP servers, tmux, GPU jobs, future workflow engine | 可选 | 部分 | 运行期集成和外部服务 |

不能混淆的边界:

- User Skill != Developer Skill。
- Role != Transport。
- Skill Graph != Workflow Runtime。
- Project Runtime State != Framework Repo State。
- Provider config != Agent backend。
- Feishu bridge != remote shell。
- Experiment Transparency Ledger != post-hoc review report。

## 3. 全局数据流

### 3.1 用户项目生命周期

```text
管理员部署 / 用户 clone framework
  -> lane project init PATH --direction "..."
  -> 写 project.yaml / AGENTS.md / CLAUDE.md / 标准目录
  -> 安装 User Skills symlink
  -> 注册 Project Registry
  -> 用户进入 Codex session
  -> Leader 按 skill graph 分发任务
  -> Coder/Deployer/Writer 执行
  -> Reviewer 独立审查
  -> Status / Ledger / artifacts 留痕
```

主要接口:

- CLI: `lane project init/update/doctor/detach`
- 项目配置: `project.yaml`
- agent 上下文: `AGENTS.md`, `CLAUDE.md`
- skill 链接: `.agents/skills/`, `.claude/skills/`
- 运行状态: `.labline/status/`, 后续 `.labline/ledger/` 或等价 transparency surface
- 注册表: `<workspace>/.labline/project-registry.json`

### 3.2 框架开发生命周期

```text
CONTEXT.md / context archive / ADR / PRD
  -> to-developer plan
  -> dev implementation
  -> tests / realtest / review
  -> development log
  -> promote decision
  -> stable docs / CHANGELOG / release tag
```

主要接口:

- 语义根: `CONTEXT.md`
- 开发文档 DAG: `to-developer/DOC_DAG.yaml`
- 模块日志: `to-developer/20260613-DEVELOPMENT_LOG.md`
- release/promote: `to-developer/plans/20260613-PROMOTE_FLOW.md`, `docs/PROMOTE_FLOW.md`
- stable 用户入口: `docs/README.md`, `docs/OPERATIONS_GUIDE.md`, `deploy/DEPLOY_GUIDE.md`

### 3.3 当前默认 Runtime Binding

默认模型是运行期绑定，不是职责定义。Role Contract 仍然由 skill / shared references 决定。

| Scope | Role | Default model | 说明 |
|---|---|---|---|
| user | Leader | `gpt-5.5` | 主会话，决策质量优先 |
| user | Planner | `gpt-5.4` | 计划草案和任务拆解 |
| user | Reviewer | `gpt-5.4` | 独立审查，读原始文件 |
| user | Writer | `gpt-5.4` | 论文、文档、rebuttal |
| user | Coder | `gpt-5.4-mini` | 代码实现、测试、修 bug |
| user | Deployer | `gpt-5.4-mini` | 部署、运行、监控、收集结果 |
| dev | Worker | `gpt-5.4-mini` | 开发侧低风险批量杂活；不进入用户 role graph |

短期不把便宜外部模型接入用户侧 role 默认绑定。DeepSeek/OpenAI-compatible 等 provider 先保留在 developer runtime / future developer agent surface 中做开发降本实验。

## 4. 模块总览

### 4.1 模块重要性分级

| 等级 | 模块 | 理由 |
|---|---|---|
| P0 | CLI / Project Init / Templates | 没有它，新用户无法进入框架 |
| P0 | User Skill Graph / Role Contracts | 没有它，agent 职责和调用关系会继续松散 |
| P0 | Docs Governance / CONTEXT / DAG | 没有它，框架开发会失去全局一致性 |
| P0 | Tests / Contract Checks | 没有它，频繁改动会持续回归 |
| P1 | Agent Status Stream | 解决长任务可观测性，是 workflow engine 前置条件 |
| P1 | Experiment Transparency / Integrity | 解决实验可信度，是科研框架核心价值 |
| P1 | Developer Agent Surface | 解决开发成本和长期维护吞吐 |
| P1 | Deploy Runtime | 解决多人服务器落地和版本回退 |
| P2 | Feishu Remote Session | 有用但不是核心路径，必须保持 opt-in |
| P2 | MCP Servers / External Bridges | 能力扩展层，不能反向绑死核心架构 |
| P2 | Realtest Container | 重要验证手段，但属于 dev-only 验证资产 |
| P3 | LangGraph Workflow Engine | 长期重要，但必须等静态协议和 backend 稳定 |
| P3 | OpenClaw / Cline SDK / OpenHands SDK | 长期 orchestration/runtime 候选，当前后置 |

### 4.2 模块责任与接口

| 模块 | 责任 | 输入 | 输出 | 主要接口 | 当前主要问题 | 下一步 |
|---|---|---|---|---|---|---|
| CLI / Project Lifecycle | 初始化、更新、诊断、detach 项目 | path, direction, framework path | project baseline, registry | `tools/lane`, installers | 命令已变多，dev/user 命名仍需稳住 | 锁定公共 CLI contract，补端到端 smoke |
| Templates | 生成项目上下文和目录 | framework metadata, direction | `AGENTS.md`, `CLAUDE.md`, `project.yaml` | `templates/*.tmpl` | 模板和 skill/role 变化容易不同步 | 增加模板 contract test 和 role graph 校验 |
| User Skill Graph | 用户侧 agent 能力与调用边 | `skills/*/SKILL.md` frontmatter | catalog, DAG, symlink surface | `docs/SKILL_DAG.yaml`, generated catalog | 正文 mention 和正式 invoke 曾经混乱 | 只认 frontmatter `invokes` 为正式边 |
| Role Contracts | Leader/Planner/Coder/Deployer/Writer/Reviewer 职责 | user task, project state | delegated tasks, artifacts, review | role skills, shared references | Planner/Integrity/Reviewer 边界仍需固化 | 写 role contract matrix，补 DAG edge |
| Project Runtime State | 项目运行期状态 | agent updates, job handles | status snapshots, traces | `.labline/status/`, `tools/agent_status.py` | 当前只是 status，尚未覆盖 ledger | status v1 稳定后接 ledger |
| Experiment Integrity | 实验透明度、数据切分、指标和 claim 审计 | plan, data split, code, raw results | ledger, audit report, checkpoints | `experiment-audit`, future ledger CLI | 定性仍容易被看成普通 skill | 固定为 workflow module + skills/tools 入口 |
| Dev Skills | 框架维护专用技能 | dev task | dev-only outputs | `to-developer/skills/dev-*`, `.agents/skills/dev-*` | 与用户 skill 同源但会分叉 | 保持 `dev-` 前缀和独立 installer |
| Dev Runtime | provider/profile/key 管理和 LLM 草案调用 | provider config, prompt | prompt/response logs | `lane dev rt ...` | 容易被误认为 coding agent | 文档定性为 profile/runtime surface |
| Dev Agent Surface | cheap model 本地改代码、跑测试、产 diff | task, scope, tests, provider | worktree diff, logs, metadata | future `lane dev agent ...` | 尚未实现真实 coding backend | 先 OpenCode smoke，Aider fallback |
| Deploy Runtime | 多用户容器、framework copy、共享数据集 | admin env, user workspace | container ABI, update check | `deploy/`, `DEPLOY_GUIDE.md` | deploy 文档和实际拓扑需持续同步 | 用 contract test 锁 ABI |
| Feishu Session | 远程消息、审批、状态卡 | Feishu events | Codex session input/output | `lane feishu ...`, external lark-channel-bridge, legacy bridge MCP/session runner | 之前脆弱，session/tmux 绑定易断 | 默认封装外部 bridge；旧 runner 只保留 fallback/audit |
| MCP Servers | review/LLM/Feishu/image 等桥 | external requests | tool results | `mcp-servers/*` | 依赖多、部署状态分散 | 每个 server 要有 inventory 和 smoke |
| Docs Governance | 文档覆盖、DAG、归档、开发日志 | docs/plans/ADR | generated DAG, check result | `tools/update_developer_docs.py` | 顶层地图缺失，本文件补位 | 新 dev doc 必须入 DAG |
| Promote / Release | dev 到 stable 的准入 | validated changes | stable docs/tag/changelog | release tools, promote docs | 工具还不完整 | 第一次正式 promote 前补 gate 工具 |
| Realtest | 独立容器实机测试 | branch, task | logs, smoke report | `to-developer/realtest/` | 资产 dev-only，容易误进 stable | 保持 dev-only，补日志索引 |

## 5. 关键模块设计

### 5.1 CLI / Project Lifecycle

定位: 用户进入 Labline 的 P0 主入口。

稳定公共命令:

```text
lane project init PATH --direction "..."
lane project doctor [PATH]
lane project update [PATH]
lane project detach [PATH]
lane project --version

lane framework --version
lane framework check-update
lane framework update
lane framework rollback
```

接口约束:

- `project init .` 表示在当前目录接入 Labline。
- `project init ./name` 表示创建或选择目录后初始化。
- `detach` 只移除 Labline 接入，不删除项目内容。
- `framework update` 只更新用户自己的 framework copy。
- 用户级状态写入 workspace `.labline/`，不能写入 framework repo。

开发计划:

| 阶段 | 任务 |
|---|---|
| now | 固定 CLI contract，保证 docs/quickstart/deploy 一致 |
| next | 增加真实空目录和已有项目接入 smoke |
| later | rollback 加 dirty worktree guard |

### 5.2 User Skill Graph / Role Contracts

定位: Labline 的执行协议层。它决定 agent 如何理解职责，而不是决定用哪个模型。

正式边定义:

- `frontmatter.invokes`: 机器可执行/可生成 DAG 的正式调用边。
- `Skill List Entry`: 机器可查询目录项，可影响可发现性，但不等同 invoke。
- `reference`: 给人或 agent 读的参考，应出现在固定 references 区域。
- 正文 mention: 默认不是拓扑边；必须被重写为 invoke/list/reference 中的一种。

角色边界:

| Role | 职责 | 不负责 |
|---|---|---|
| Leader | 和人交互、澄清需求、分发任务、收口决策 | 长时间直接执行所有细活 |
| Planner | 自动产出计划草案和依赖拆解 | 越过 Leader 直接执行危险动作 |
| Coder | 实现代码、局部测试、提交 artifacts | 自我最终 review |
| Deployer | 部署、远程实验、job handle、日志路径 | 声称实验结论 |
| Writer | 写论文/报告/文档草案 | 编造实验状态或 claim |
| Reviewer | 独立审查计划、代码、实验、claim、论文 | 使用 executor 摘要替代原始输入 |

开发计划:

- P0: 给核心 role skill 补统一 role contract matrix。
- P0: skill DAG 只保留 formal edges，弱引用单独列出。
- P1: Planner 从 Leader 中长出，但 Leader 仍是人机交互主控。
- P1: Reviewer 作为本地 agent/MCP/API transport 都必须遵守 independence contract。

当前已落地的共享入口:

- `skills/shared-references/role-contracts.md`
- `skills/skills-codex/shared-references/role-contracts.md`

### 5.3 Project Runtime State / Agent Status Stream

定位: 让 Leader 看到运行中 agent 和长任务状态，减少读 transcript 和重复 observation。

当前接口:

```text
.labline/status/
  agents/<agent_id>.json
  events.jsonl          # optional diagnostic
```

工具:

```text
tools/agent_status.py start/update/finish/list/summary/validate
```

约束:

- 每个 agent 只写自己的 status file。
- Leader 读 snapshots，不写 agent-owned 文件。
- `next_expected_update` 是观察节奏，不是硬超时。
- status 不替代 experiment ledger、review artifact、queue state。

开发计划:

- P1: 确认 templates 已忽略 `.labline/status/`。
- P1: Leader/Coder/Deployer/Writer/Reviewer 全部补 status 责任。
- P2: 只在诊断时使用 `events.jsonl`，不要让 Leader 默认读全日志。

### 5.4 Experiment Transparency / Integrity

定位: Labline 区别于普通 coding agent 的核心科研价值。它不是单个普通 skill，而是一组贯穿实验生命周期的 workflow module。

需要记录的 evidence:

- 数据集来源和版本。
- train/val/test split 生成方式、随机种子和文件。
- metric 定义和计算代码。
- 预训练模型、checkpoint、配置。
- 每个实验 block 的计划、偏差、失败、重跑原因。
- raw results、aggregated tables、claim 对应关系。
- 人工 checkpoint 决策。

接口形态:

```text
project/.labline/ledger/              # future, runtime state
refine-logs/ or experiment-ledger/  # human-readable artifacts
tools/experiment_*                 # future deterministic helpers
skills/experiment-audit            # review/audit entrance
skills/result-to-claim             # claim support judgement
```

重要定性:

- Experiment Integrity 是 workflow module。
- `experiment-audit` 是其中一个审计入口 skill。
- 透明度记录应当隐式贯穿项目流程，随时可查看。
- 后续 LangGraph 可把它做成状态节点，但第一版不依赖 LangGraph。

开发计划:

| 阶段 | 任务 |
|---|---|
| now | 写清 ledger schema 草案和 artifact 路径 |
| next | 在 experiment-plan / run-experiment / monitor / result-to-claim 中引用 ledger |
| later | 接 human checkpoint queue 和 LangGraph node |

### 5.5 Developer Skills / Developer Runtime / Developer Agent

定位: 框架开发侧的降本增效系统，不能进入用户 role graph。

三者区别:

| 名称 | 命令/路径 | 能力 | 边界 |
|---|---|---|---|
| Dev Skills | `to-developer/skills/dev-*` | 给 Codex 读的开发技能 | dev-only，不装到项目 |
| Dev Runtime | `lane dev rt ...` | provider/profile/key 管理，简单 LLM 草案调用 | 不读写本地代码 |
| Dev Agent | future `lane dev agent ...` | 本地 coding worker，worktree + diff + tests | 只在 dev checkout 用 |

Dev Agent 推荐路线:

1. OpenCode smoke。
2. Aider fallback。
3. 正式 `lane dev agent run/status/diff/log`。
4. backend abstraction。
5. OpenClaw/Cline SDK/OpenHands SDK/LangGraph 后置评估。

开发原则:

- Codex/Leader 写任务、scope、验收。
- cheap worker 在临时 worktree 改代码。
- Labline 做 scope audit、test rerun、secret scan。
- 主控 review 后才合并。

### 5.6 Deploy Runtime

定位: 让多人服务器部署可管理，同时允许每个用户独立控制 framework 版本。

容器内 ABI:

```text
/lane/framework
/lane/projects
/lane/.labline
/lane/shared/datasets
/lane/shared/pretrained
/lane/shared/downloads
```

部署原则:

- 一人一个容器或等价隔离 workspace。
- 每个用户有自己的 framework copy 和 projects。
- datasets/pretrained/downloads 可共享。
- framework 自动检查更新可以提示，但不静默更新。
- 用户可 rollback 自己的 framework copy。

开发计划:

- P1: 用 contract test 锁定 compose/env/entrypoint ABI。
- P1: 管理员 deploy guide 和用户 operations guide 保持分工。
- P2: 每周/每日提示策略继续以 user workspace 状态记录，不进 framework repo。

### 5.7 Feishu Remote Session

定位: 可选远程控制入口，不是 Labline 核心执行层。

当前语义:

- 默认接入路径是 `lane feishu ...`，它封装外部 `lark-channel-bridge` CLI。
- Labline 不 vendor、不 fork、不重写 `lark-channel-bridge`；只提供安装、启动、状态、日志和 doctor 的短命令入口。
- 默认 profile 是 `lane-codex`，默认 agent 是 `codex`，`run/start` 默认绑定当前目录为 workspace。
- Claude Code 兼容通过独立 profile 表达，例如 `lane feishu run --profile lane-claude --agent claude`。
- Feishu-Controlled Session 必须 opt-in。
- Feishu 输入进入 live Codex session。
- Remote Action Approval 是单次动作审批，不是全局授权。
- Control Lease 决定本地/远程谁拥有输入权。
- Phone Session Report 记录手机端工作事实，不能合并隐藏上下文。

当前问题:

- legacy session/tmux 绑定脆弱，只能作为 fallback。
- 消息收发失败时需要能快速定位到 bridge CLI、profile、agent、state home 和日志目录。
- 外部 bridge 版本、Node 版本、Codex/Claude 登录态仍需要实机 smoke。

开发计划:

- P1: 稳定 `lane feishu install|doctor|run|start|status|stop|restart|logs` CLI contract。
- P1: 用户文档和 `feishu-session` skill 默认使用 `lane feishu ...`，底层 `lark-channel-bridge ...` 仅作为实现说明。
- P2: 增加真实 PersonalAgent app 的 realtest smoke，记录日志到 `to-developer/realtest/`。
- P2: legacy Labline runner 继续保留 inbox/outbox、merge report、tmux live-TUI injection，不再作为默认路径扩展。

### 5.8 Docs Governance / Promote / Release

定位: 防止框架快速演化后没人知道哪些东西该同步。

硬规则:

- `CONTEXT.md` 是 semantic root，只记术语和约定。
- 新增/删除/重命名 `to-developer/*.md` 或 `.txt` 必须更新 `to-developer/DOC_DAG.yaml`。
- 运行:

```bash
python tools/update_developer_docs.py
python tools/update_developer_docs.py --check-only
```

- `to-developer/` 不进入 stable。
- stable 用户可见变更才进 `CHANGELOG.md`。
- Developer Material 不触发 release。

开发计划:

- P0: 本文成为开发入口之一，纳入 DAG。
- P1: 第一次大型 promote 前补 `check_promote_ready`。
- P1: 把 feature decision lineage 和 context archive 用法写成固定流程。

## 6. 模块间接口矩阵

| From | To | 接口 | 数据/契约 |
|---|---|---|---|
| CLI | Templates | 文件生成 | `project.yaml`, `AGENTS.md`, `CLAUDE.md` |
| CLI | Project Registry | JSON state | `<workspace>/.labline/project-registry.json` |
| Framework Update | Project Installer | symlink rebuild | `.agents/skills`, `.claude/skills` |
| User Skill Graph | Docs Catalog | generated docs | `docs/SKILL_DAG.yaml`, catalogs |
| Leader | Role Skills | invoke contract | task, scope, expected artifacts |
| Agents | Status Stream | JSON snapshot | `.labline/status/agents/*.json` |
| Deployer | Long Jobs | durable handle | tmux/session/log/result path |
| Experiments | Integrity Ledger | evidence records | splits, metrics, configs, raw results |
| Reviewer | Review Artifacts | independent verdict | trace path, input scope, report |
| Dev Skills | Dev Docs | maintenance output | plans, ADR, logs, DAG updates |
| Dev Runtime | Provider Config | JSON/env | no API key in logs |
| Dev Agent | Git Worktree | diff/test logs | patch, stdout, stderr, metadata |
| Feishu Bridge | Codex Session | inbox/approval | session id, lease, message, response |
| Promote | Stable Docs | distilled docs | changelog, release notes, docs update |

## 7. 当前缺口清单

### P0 缺口

- Role graph 仍需要从“文档里提到”收敛成 formal DAG + role contract。
- Experiment Integrity 的 workflow module 定性还没完全落到 schema 和入口。
- 用户侧 docs、templates、skills 仍可能在快速改动中不同步。
- 顶层设计此前缺失，agent 容易局部优化。

### P1 缺口

- Agent Status Stream 已有协议和工具，但 role skill 接入需要继续查漏。
- Developer Agent Surface 尚未真正接 OpenCode/Aider。
- Deploy 文档、容器 ABI、update/rollback 行为需要更多实机验证。
- Promote gate 工具还没完整实现。

### P2 缺口

- Feishu bridge 不够可靠，需要模块化和健康检查。
- MCP server inventory 和 smoke 需要统一。
- Realtest container 的日志索引和复用流程需要强化。

### P3 缺口

- LangGraph 仍是后置 workflow runtime，不能提前成为核心依赖。
- OpenClaw/Cline/OpenHands 需要等 dev agent backend 稳定后再评估。

## 8. 开发优先级路线图

### Phase A: 稳住框架主干

目标: 新用户能进来，agent 不乱分工，docs 不漂移。

任务:

- 固定 CLI/project/template contract。
- 补 role contract matrix。
- 清理 skill mention，把 topology 边全部转成 `invokes` 或固定 reference。
- 确保 developer doc DAG 覆盖新增顶层文档。
- 继续完善 tests 作为行为锁。

### Phase B: 实验可信度主线

目标: Labline 的科研价值不只是自动写代码，而是让实验过程透明可审。

任务:

- 写 Experiment Transparency Ledger schema。
- 将 ledger 接入 experiment-plan / run-experiment / monitor / result-to-claim。
- 固定 human checkpoint / checkpoint queue 的最小协议。
- 给用户侧和开发侧都补完整使用文档。

### Phase C: 开发降本主线

目标: 便宜模型能真正承担低风险开发杂活。

任务:

- OpenCode smoke。
- Aider fallback。
- `lane dev agent` 最小 CLI。
- worktree isolation、scope audit、test rerun、secret scan。
- worker 产出必须由 Codex/leader review。

### Phase D: 部署和远程协作

目标: 多用户服务器能长期稳定使用。

任务:

- deploy/operations 文档和 ABI contract test。
- update check / rollback / registry 的实机验证。
- Feishu bridge 模块化替换或加固。
- realtest container 日志化。

### Phase E: Workflow Engine

目标: 长任务可恢复、可暂停、可审计。

前置条件:

- static skill graph 稳定。
- agent status 和 ledger 稳定。
- dev agent backend 稳定。
- 至少一个 workflow 有强痛点。

候选:

- `grill-with-docs`
- `auto-review-loop`
- `experiment integrity`
- `paper-talk`

## 9. 给 agent 的工作规则

任何 agent 修改 Labline 前，默认按这个顺序读:

1. `CONTEXT.md`
2. 本文档
3. `to-developer/20260615-FRAMEWORK_MODULES.md`
4. 相关 plan / ADR
5. 相关 tests

任何 agent 做功能开发前，必须回答:

- 这是 user-facing 还是 dev-only?
- 会不会进入 stable?
- 改的是 skill graph、runtime binding、provider config 还是 workflow engine?
- 运行状态写在哪里?
- 是否需要更新 `CONTEXT.md`?
- 是否需要更新 `to-developer/DOC_DAG.yaml`?
- 是否需要更新 stable docs 或 `CHANGELOG.md`?
- 有哪些 contract test 能锁住行为?

任何 cheap worker 输出都必须包含:

```text
scope:
changed_files:
tests_run:
risk:
needs_leader_review: yes
```

## 10. 文档关系

本文是顶层地图，下游细节见:

- `CONTEXT.md`: 术语和治理语义根。
- `docs/FRAMEWORK_STRUCTURE.md`: 面向用户/管理员的 framework/project/dev 三层结构。
- `to-developer/20260615-FRAMEWORK_MODULES.md`: 按目录归属的模块边界。
- `to-developer/plans/20260616-CLI_DEPLOY_RUNTIME.md`: CLI 和部署运行时机制。
- `to-developer/plans/20260613-AGENT_STATUS_STREAM.md`: status stream 协议。
- `to-developer/plans/20260617-DEV_AGENT_SURFACE_PRD.md`: cheap coding worker / dev agent 计划。
- `to-developer/plans/20260613-LANGGRAPH_EVALUATION.md`: LangGraph 引入时机。
- `to-developer/plans/20260613-PROMOTE_FLOW.md`: promote 流程。
- `to-developer/DOC_DAG.yaml`: 开发者文档依赖图源数据。

## 11. 当前决策摘要

- Labline 当前最重要的主干是 project lifecycle、skill/role graph、docs governance、tests。
- Experiment Integrity 是科研核心主线，不能降级成普通后置 review skill。
- Developer Agent Surface 是开发降本主线，短期 OpenCode + Aider，长期再看 OpenClaw/Cline/OpenHands/LangGraph。
- LangGraph 是后置 workflow runtime，不是当前核心依赖。
- Feishu 是可选远程协作入口，不是执行核心。
- `to-developer/` 是 dev-only，任何 dev-only 能力默认不进入 stable。
- 顶层设计、模块边界、DAG、开发日志必须一起维护，否则 agent 开发会继续局部失焦。
