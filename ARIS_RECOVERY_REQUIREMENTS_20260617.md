# ARIS 需求恢复文档 2026-06-17

本文件用于在 `/aris/aris-dev` 被误删后，重建近期未提交的需求、术语和实现计划。内容来自当前会话，不依赖已删除工作区。

## 总体目标

ARIS 要从一组 scripts/skills 升级为可部署、可追踪、可低成本协作的科研 agent 框架。短期不直接上完整 workflow engine，而是先实现 CLI、部署、角色边界、skill DAG、实验透明性、飞书接入、开发侧 cheap worker 的最小闭环。

基本原则：

- Leader/Codex 负责理解需求、拆任务、最终 review、测试、promote/release 决策。
- cheap worker 负责批量文档、引用扫描、测试草案、低风险 patch 草案。
- Reviewer 是独立角色，不等同于 MCP；可以由本地 agent、MCP、API 或其他 transport 实现。
- 用户/管理员文档分离；`to-developer/` 是 dev-only，不能进入 stable `main`。
- 实验真实性依赖全过程透明，而不是事后自证。
- 每次重要 grilling/context 结果按时间和主题归档，并可追溯到功能开发。

## 名词定义

### ARIS CLI

统一命令入口，隐藏底层脚本名。主要 scope：

- `aris project ...`：项目初始化、更新、检查、脱离 ARIS。
- `aris framework ...`：框架版本、更新、回滚、检查更新。
- `aris dev worker ...`：开发侧 cheap worker 配置、任务生成、模型执行。

### Runnable Project Baseline

目录成为 ARIS 项目的最低可运行状态。至少包括 `project.yaml`、`AGENTS.md`、`CLAUDE.md`、`.aris/manifest.json`、Codex/Claude skill 接入记录、标准项目目录和版本基线。

### Project Init / Attach

`aris project init PATH --direction ...` 的语义：

- `PATH=.`：在当前目录初始化或半路接入 ARIS。
- `PATH=./my-project`：目录不存在则创建，存在则接入。
- 必须支持已有非 ARIS 项目半路接入，不能覆盖用户文件或历史。

### Project Detach

移除 ARIS 管理痕迹但不删除项目内容。避免使用 `uninstall project` 这种过重表达。

### User Workspace

管理员给每个用户分配的工作区。每个用户拥有自己的 framework checkout 和 project 区域；数据集和预训练模型等大资源共享。

### User Framework Copy

用户工作区内的独立 framework checkout。用户可独立 pin、update、rollback，避免共享 framework 更新破坏项目可回退性。

### ARIS Role

稳定职责边界。核心角色：

- Leader：面向人类用户的主协调者，也承担 grilling 和部分 planning。
- Coder：代码实现。
- Deployer：部署、运行实验、远程资源。
- Writer：论文、报告、文档输出。
- Reviewer：独立审查。
- Planner：可选角色，用于自动生成计划草案；草案必须回到 Leader/用户确认。

Monitor 默认不是独立角色；监控更像 Deployer/工具职责，除非以后明确引入独立 contract。

### Role Transport

实现某个 role 的运行机制，例如当前 Codex 会话、spawned local agent、独立 CLI session、MCP-backed model、OpenAI-compatible API、国产模型。Transport 变化不能改变 role 职责。

### Role Transport Configuration

项目级或开发侧配置，记录 role 到 provider/transport/model/base_url/api_key_env 的绑定。默认在项目初始化时写入，运行中可配置。

### Logical Skill Graph

transport-independent 的 skill/role 关系图，描述职责和依赖，不描述由哪个模型运行。

### Runtime Binding View

当前环境里 role 绑定到哪个 transport/model/session 的视图。它可以变化，但不能改写 Logical Skill Graph。

### Skill Invocation Edge

明确的调用/委托/必需依赖边。必须由结构化 metadata 声明，例如 `invokes`，不能从普通 prose 或 mention 推断。

### Skill Reference Edge

给人看的上下文/参考边。必须出现在固定结构化位置，供工具识别。Reference 不是 runtime dependency。

### Skill List Entry

把 skill 放入可查询列表、菜单、catalog、能力表的 discovery edge。影响发现和选择，不是调用边。

### Unclassified Skill Mention

skill 文档里未分类的 skill/role/tool 名称出现。架构相关文档不应保留未分类 mention；要转成 invocation/reference/list entry 或其他明确语义。

### Skill Governance

治理 skill 类型、caller、invocation/reference/list edge、DAG、拓扑和边界的机制。防止隐式依赖和 loose `caller: any`。

### Reviewer Role

独立审查者。Reviewer 可由本地 agent、MCP、API 等 transport 实现。关键 contract 是独立性，不是具体工具。

### Design Grilling

在项目开始、人介入、新需求、审查、role/skill/transport 变化等 Human Governance Gate 处进行的结构化追问和术语澄清。`grill-with-docs` 是标准 workflow skill，但不负责 skill dependency 分类。

### Global Context Sweep

`grill-with-docs` 在开始或结束时做的全局上下文扫描，防止只围绕一个点收敛，遗漏其他待办需求。

### Grilling Context Archive

每次重要 `CONTEXT.md` / grilling 产物按日期和主题归档，作为功能开发的原始需求来源。

### Feature Decision Lineage

功能升级/开发必须能追溯到最初 context/grilling 记录、ADR、plan、实现、测试和 review。

### Agent Status Stream

本地文件系统状态通信机制。每个 delegated agent 写自己的 status snapshot，Leader 读取聚合。它不是任务队列，也不是 agent 聊天室。

### Agent Status Snapshot

单个 agent 当前状态：role、task、liveness、current action、blocker、artifact pointer、next expected update。

### Expected Update Time

下次合理期待 agent/job 给出信号的时间。不是硬 deadline。

### Status Freshness Contract

状态文件在 `next_expected_update` 后允许一个小宽限期。过期后 Leader 先做 read-only status check，再看 job handle/logs。

### Long-Running Job Handle

tmux/screen/session/queue/log/result dir 等可独立检查的长任务句柄。长任务真实性不能只依赖 agent transcript。

### Experiment Transparency Ledger

实验全过程透明账本，记录数据切分、metric 公式、代码版本、配置、trick、deviation、run artifact、人工 checkpoint。

### Experiment Integrity Workflow

持续可查看的实验真实性 workflow，不是普通一次性 skill。它应隐式伴随实验流程运行，产出独立节点/账本/日志，可随时人工查看，后续可升级到 LangGraph/workflow engine。

### Checkpoint Queue

实验完整性 workflow 中待人工确认的固定 checkpoint 列表。它不是任意打断机制的替代，而是第一阶段 HITL 的最小实现。

### Cheap Worker

低成本开发/执行 worker。默认可以是 `gpt-5.4-mini`，也可接 DeepSeek/Qwen/MiniMax 等 OpenAI-compatible provider。Cheap worker 不做最终决策，不 promote，不 rollback，不处理 secret。

### OpenAI-Compatible Provider

通过 `base_url + api_key_env + model` 配置的 chat completions provider。API key 只从环境变量读，日志只记录 env 名，不记录值。

### DeepSeek V4 Flash Worker

开发侧 cheap worker 的 named provider：

- provider: `deepseek-v4-flash`
- transport: `openai_compatible`
- model: `deepseek-v4-flash`
- base_url: `https://api.deepseek.com/v1`
- api_key_env: `DEEPSEEK_API_KEY`

## 已敲定需求清单

### 1. 新手 CLI 与项目初始化

- 空文件夹里不要求用户知道 `/init-research`。
- 统一入口是 `aris project init PATH --direction ...`。
- 支持当前目录初始化、指定路径初始化、已有项目半路接入。
- 初始化时安装 Codex skills，并兼容 Claude Code。
- 文档示例统一以 Codex 为主，Claude Code 为兼容入口。
- `project update/doctor/detach` 默认当前目录。
- `project --version` 显示项目绑定 framework path/version/commit。

### 2. Framework 更新、回滚、检查更新

- `aris framework --version`
- `aris framework update`
- `aris framework rollback`
- `aris framework check-update`
- 状态文件放在 `~/.aris` 或 `ARIS_WORKSPACE/.aris`，不能写到 `/aris/.aris`。
- 每个用户每天最多提醒一次更新。
- 用户启动 tmux 或常用入口时可检查更新。
- framework 更新默认自动 sync 已注册项目。
- detach 项目从 registry 移除。

### 3. 部署拓扑与文档

- `deploy/DEPLOY_GUIDE.md` 面向管理员。
- `docs/OPERATIONS_GUIDE.md` 面向使用者，并分用户/管理员两大板块或清晰目录。
- 管理员指定每个用户的 workspace。
- 每个用户一份 framework + projects，便于版本控制和回退。
- 数据集和预训练模型共享。
- 文档中 framework 路径统一写 `[你的framework位置]`。
- `/data` 等固定路径改成自由目录/管理员指定目录。
- 一人一个容器大致成立，数据/预训练只读共享。

### 4. Dev-only 实机测试容器

- 测试 deploy 资产放 `to-developer/realtest/`，不放 stable `deploy/`。
- 包含 `docker-compose.test.yaml`、`.env.test.example`、`test-runner.sh`、dated 说明文档。
- 用于新功能实机 smoke/integration 测试。
- 日志写回 host 指定目录。
- 不默认支持嵌套 Docker；需要 Docker socket / DinD 时单独显式扩展。

### 5. Feishu/Lark 接入

- 当前 `feishu-session` 太弱。
- 方向是接入 `https://github.com/zarazhangrui/lark-coding-agent-bridge` 作为模块。
- 旧 in-repo Feishu runner 作为 fallback。
- bridge 只做消息/状态/审批 transport，不拥有 workflow 决策，不直接执行 shell。
- 远程消息不能吞；要能回传、可追踪、可恢复。

### 6. Skill DAG 和调用层级

- skill DAG、调用层级、职责边界要系统化。
- “出现在其他 skill 文档”必须定性为 invocation、reference、list entry、unclassified mention 或其他结构化语义。
- reference 固定出现在机器可识别位置。
- list entry 作为 discovery edge 接入 DAG，但不等于 runtime dependency。
- reviewer 作为本地 agent 替代 MCP 后也必须进入 skill 体系。
- Coder/Deployer/Writer 可以有独立 transport，便于接便宜模型。

### 7. Leader / Planner / Executor 职责

- 三边架构文档要修正：没有“三个 Codex session”的既定说法。
- Executor 应拆成 Coder、Deployer、Writer 三个子职责。
- Leader 是和人交互主体，也承担 grilling 和部分 planning。
- Planner 可作为可选角色长出来，负责自动 plan 草案。
- Planner 的草案必须回到 Leader/用户确认，不能自动变成执行计划。

### 8. 文件系统状态通信

- 需要规定状态文件通信规则。
- 每个 agent 写自己的 status file。
- Leader 读 status snapshot，减少重复 observation 和 token 消耗。
- 状态有 `next_expected_update` 和宽限期。
- stale 后优先 read-only check，再看 job handle/log。

### 9. Experiment Integrity Workflow

- 实验真实性依赖过程透明。
- 指标公式、数据切分、trick、代码操作、模型内容、artifact 全部可追踪。
- 测试集可单独拉出，本地独立计算指标，必要时现场跑。
- 同一模型跨数据集性能重要。
- 做成隐式、随时可查看的 workflow。
- 有独立节点/账本/日志系统。
- 与 skill 体系的关系：workflow 不是普通 tool skill；实验相关 skill 必须写 ledger/checkpoint。
- 后续可升级 LangGraph，但第一阶段不依赖 workflow engine。

### 10. grill-with-docs 和 context 归档

- 项目开始、人介入、新需求、审东西时应触发或建议触发 `grill-with-docs`。
- `grill-with-docs` 不负责把所有依赖分类；skill governance 负责 DAG 分类。
- 每次 grilling 的 `CONTEXT.md` 应按时间/主题归档。
- 归档服务于 Feature Decision Lineage。

### 11. 开发者文档规则

- `to-developer/` 是 dev-only，不能进 stable `main`。
- 开发者文档默认中文。
- 所有开发者侧 `.md`/`.txt` 名称加创建时间前缀。
- 新增/删除/重命名 `to-developer/` 下 `.md`/`.txt` 后必须更新 `to-developer/DOC_DAG.yaml`。
- 更新后运行 `python tools/update_developer_docs.py` 和 `python tools/update_developer_docs.py --check-only`。

### 12. 开发侧 cheap worker

- Codex 主会话太贵，开发侧也要“贵模型管控、便宜模型干活”。
- 默认 cheap worker 可用 `gpt-5.4-mini`。
- 可接国产 OpenAI-compatible 模型，如 DeepSeek V4 Flash。
- Cheap worker 用于批量文档编辑、引用/路径扫描、测试草案、低风险 patch 草案、大量机械迁移。
- Codex/Leader 负责拆任务、文件范围、最终审查、测试、apply patch、promote/release。

设计命令：

```bash
aris dev worker config --init

aris dev worker provider set deepseek-v4-flash \
  --transport openai_compatible \
  --model deepseek-v4-flash \
  --base-url https://api.deepseek.com/v1 \
  --api-key-env DEEPSEEK_API_KEY

aris dev worker prompt "任务内容" \
  --provider deepseek-v4-flash \
  --file docs/xxx.md

aris dev worker run "任务内容" \
  --provider deepseek-v4-flash \
  --file docs/xxx.md
```

Runner 约束：

- 调用 `/chat/completions`。
- API key 只从 env 读取。
- stdout/log/request/metadata 只能记录 `api_key_env`，不能记录 key 值。
- 每次 run 写入 `to-developer/logs/dev-workers/<timestamp>-<slug>/`。
- 保存 `task.md`、`request.json`、`response.md`、`metadata.json`。
- 不自动 apply patch。
- 不 commit。
- 不 promote。
- `codex_subagent` transport 由当前 Codex session 的 subagent 工具执行，不由 CLI runner 执行。

## 建议恢复实现顺序

1. 从 `/aris/framework` 或 remote 恢复当前 stable 基线。
2. 另建 dev 工作副本，恢复 `to-developer/` 规则和 `DOC_DAG`。
3. 恢复 `CONTEXT.md` 术语。
4. 恢复 `tools/aris` 的 `project/framework/dev worker` 命令。
5. 恢复测试：`test_aris_cli.py`、developer DAG、realtest contract、Feishu transport docs。
6. 恢复 realtest dev-only 目录。
7. 恢复 Feishu/Lark bridge 方向文档。
8. 恢复 skill governance 结构化 edge 设计。
9. 恢复 Experiment Integrity Workflow 设计和 schema。
10. 再做 review、promote、release。

## 当前恢复状态

- `/aris/aris-dev` 当前为空，且目录 owner 为 root。
- `/aris/framework` 是完整 stable 仓库，当前 `main` 在 `v0.3.3`。
- `/aris/framework` 干净，可作为恢复基线。
- `origin/dev` 仍存在，但看起来只比 stable 多 changelog 记录，不包含最新未提交工作。
- `/home/researcher/.aris/dev-workers.json` 仍存在，保留了 DeepSeek provider 配置。
- `/aris/backups/framework-backup-20260613-143059.tar.gz` 是较早备份，可作为旧资料来源。

## 优先继续查找位置

- Codex/agent 日志目录。
- shell history。
- `/tmp` 下 agent 或 pytest 残留。
- 编辑器 local history。
- Docker/container volume snapshot。
- 服务器备份。
- GitHub remote 是否有更晚的 dev 推送。
