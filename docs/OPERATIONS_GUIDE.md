# Labline 操作与运维手册

> 分为用户手册和管理员手册。用户手册讲项目创建、日常 workflow、框架更新；管理员手册讲多人容器、共享资产和部署维护。

---

## 目录

1. [用户手册](#用户手册)
   - [概念](#概念)
   - [项目生命周期](#项目生命周期)
     - [创建项目](#创建项目)
     - [日常开发](#日常开发)
     - [运行态状态与心跳](#运行态状态与心跳)
     - [本地 Debug Smoke](#本地-debug-smoke)
     - [更新框架](#更新框架)
   - [三边架构使用](#三边架构使用)
     - [启动方式](#启动方式)
     - [角色职责](#角色职责)
     - [Agent 约束](#agent-约束)
   - [Skill 详解](#skill-详解)
     - [完整 Skill 列表入口](#完整-skill-列表入口)
     - [研究发现类](#研究发现类)
     - [实验类](#实验类)
     - [论文类](#论文类)
     - [质量保证类](#质量保证类)
   - [代码同步](#代码同步)
   - [远程实验](#远程实验)
   - [论文工作流](#论文工作流)
   - [API 配置](#api-配置)
   - [框架管理](#框架管理)
   - [多人协作](#多人协作)
2. [管理员手册](#管理员手册)
   - [Docker 多人环境](#docker-多人环境)
   - [API Provider 预配](#api-provider-预配)
   - [Framework 更新检查策略](#framework-更新检查策略)
   - [故障排查](#故障排查)
     - [Codex 相关](#codex-相关)
     - [Git/Sync 相关](#gitsync-相关)
     - [Docker 相关](#docker-相关)
     - [GPU 服务器相关](#gpu-服务器相关)
     - [Claude Code 兼容相关](#claude-code-兼容相关)
3. [附录：完整 Skill 列表](#附录完整-skill-列表)

---

## 用户手册

### 概念

#### 框架 vs 项目

|      | 框架 (Framework)                            | 科研项目 (Project)         |
| ---- | ------------------------------------------- | -------------------------- |
| 内容 | skills、tools、templates、deploy            | code、data、paper、results |
| 位置 | 管理员分配；容器内通常是 `/lane/framework` | 容器内通常在 `/lane/projects` 下 |
| 更新 | `lane framework update` / `lane framework rollback` | 用户自行管理 |
| 共享 | 每个用户一份 framework copy，同一用户项目共享 | 每人/每方向独立 |

框架通过 symlink 安装到项目中：Codex 默认使用 `.agents/skills/`，Claude Code 兼容模式使用 `.claude/skills/`。

#### project.yaml

每个科研项目的核心配置文件，由 `lane project init` 生成：

```yaml
project:
  name: "my-detection"
  direction: "基于频域特征的增量目标检测"
  size: "full"
  author: "zhangsan"

git:
  auto_commit: true
  remote: "http://gitea:3000/zhangsan/my-detection.git"
  branch: "main"

servers:
  - name: "gpu-server-1"
    host: "gpu-server-1"              # ~/.ssh/config 中的别名
    path: "[服务器上的项目位置]/my-detection"
    conda_env: "lane"
    gpus: [0, 2]

framework:
  path: "[你的framework位置]"
  repo: "https://github.com/your-org/lane-framework.git"

sync_exclude:
  - "outputs/"
  - "wandb/"
  - "*.pth"
  - "__pycache__/"
```

所有 skill 读这个文件获取配置。手动编辑即可，无需特殊工具。

---

### 项目生命周期

#### 创建项目

#### Step 1: 用 `lane project init` 初始化项目

`lane project init PATH` 是新手创建项目的**首选入口**。它会调用底层安装器并生成项目骨架。`PATH` 必填，`.` 表示当前目录。

```bash
# 当前目录初始化/接入
mkdir -p ~/projects/my-research
cd ~/projects/my-research
lane project init . --direction "研究方向"

# 从父目录创建项目；目录不存在会自动创建
cd ~/projects
lane project init ./my-research --direction "研究方向"

# 已有项目半路接入 Labline
cd /path/to/existing-project
lane project init . --direction "研究方向"
```

安装完成后项目结构：

```
my-research/
├── project.yaml
├── AGENTS.md              ← Codex 上下文（需编辑：填研究方向、服务器等）
├── CLAUDE.md              ← Claude Code 兼容上下文
├── .agents/skills/        ← Codex skills symlinks
├── .claude/skills/        ← Claude Code 兼容 symlinks
├── .labline/
│   ├── manifest.json      ← CLI 初始化记录
│   ├── installed-skills.txt  ← manifest（记录安装了哪些 skill）
│   └── installed-skills-codex.txt
├── code/
├── data/
├── outputs/
└── (你的代码/数据/论文)
```

#### Step 2: 检查初始化结果

```bash
lane project doctor
```

如果需要手动补充研究方向、服务器、约束，可再编辑 `AGENTS.md`；Claude Code 兼容模式同步参考 `CLAUDE.md`。

#### Step 3: 进入 Codex 开始工作

```bash
cd ~/projects/my-research
codex
```

进入后直接用 `$leader`、`$experiment-plan` 等 skill。Claude Code 兼容模式使用 `/skill-name`。

#### 项目放哪？

普通用户只需要知道自己的项目通常放在 `/lane/projects` 或管理员指定的项目工作区。framework 位置由管理员分配；容器内通常是 `/lane/framework`。

```
/lane/framework/              # 你的 framework copy

/lane/projects/               # 你的项目工作区
├── exp-detection/
└── exp-segmentation/
```

**关键点：**

- 每个用户有自己的 framework copy；该用户的项目通过 symlink 共享这份 copy
- 项目之间完全独立（各自 git repo、各自 `AGENTS.md`）
- `lane framework update` 默认同步更新已登记项目
- 单个项目可手动运行 `lane project update`

#### 旧 ARIS 项目迁移

如果项目曾经接入过 ARIS，目录里可能保留 `.aris/` 状态、旧 `project.yaml framework.path`，以及指向旧 framework 的 `.agents/skills` / `.claude/skills` symlink。先 dry-run 看计划：

```bash
cd [你的project位置]
lane project migrate-aris
```

确认只会处理旧 ARIS 链接后执行：

```bash
lane project migrate-aris --apply
lane project doctor
```

这个命令会迁移 `.aris/manifest.json` 到 `.labline/manifest.json`，删除指向旧 ARIS framework 的 skill symlink，重写 `project.yaml` 的 `framework:` 块，并重新安装当前 Labline skills。它不会删除项目代码、数据或 Git 历史。

#### 日常开发

```
# 保存进度
$sync push --message "完成 backbone 实现"

# 部署到 GPU 服务器
$sync deploy --server gpu-server-1

# 拉取最新（多人协作时）
$sync pull

# 查看状态
$sync status
```

#### 更新框架

```
lane framework --version
lane framework update
lane framework rollback
```


---

### 三边架构使用

#### 启动方式

默认只需要一个 Codex 主会话。Leader 在本会话中编排并派生本地 agents；Executor 拆成 Coder / Deployer / Writer 三个主执行子职责；Reviewer 是本地独立审查 agent。Claude Code 只作为兼容客户端。

```bash
cd ~/projects/my-research
codex
```

进入后：

```text
$leader "研究方向"
```

不要手动开三个 `codex exec -p ...` 终端；当前最小可用 CLI 设计是单主会话 + Leader 派生 agents。

#### 角色职责

**Leader 只做三件事：读、判、派**
- 读：读取文件、实验结果、审查报告
- 判：决定下一步、是否止损、claim 是否成立
- 派：将任务写入文件，通知 Executor/Reviewer

**Leader 绝对不做：**
- 写代码、画图、跑命令
- 替 Executor 干活（即使 Executor 遇到权限问题）
- 遇到问题自己解决 → 应报告给人

**Executor 拆成三个主执行子职责：**
- Coder：写代码、测试、修 bug、重构；不 SSH、不部署、不写论文
- Deployer：同步服务器、启动训练、监控实验、收集结果；不改代码逻辑
- Writer：写论文、文档、rebuttal；不写实验代码、不跑实验、不编造结果

**Reviewer 做：**
- 独立审查代码/实验/claim
- 只看原始文件，不看 Executor 的总结

#### Agent 约束

#### 禁止 tail 轮询

**严禁**用 `Bash(tail -f ...)` 或重复 `Bash(tail ...)` 轮询实验进度。代价：800+ 次无意义 API 调用。

正确做法：
- 远程实验 → `ssh server "screen -dmS exp bash -c 'cmd > log.txt 2>&1'"` 启动，用 `$monitor-experiment` 一次性收集
- 本地实验 → `Bash(run_in_background: true)` 启动，等 task-notification 回调
- 检查是否跑完 → 单次 `ssh server "tail -20 log.txt"` 或 `screen -ls`，**不要循环**

#### Executor 阻塞协议

详见 `skills/shared-references/executor-blocked-protocol.md`。

Agent 遇到权限/网络/资源阻塞时：
1. 尝试绕过方案 1（换等价命令/工具）
2. 尝试绕过方案 2（降级执行/替代路径）
3. 两次都失败 → 写 `BLOCKED_REPORT.md`（含可复制粘贴的人工操作命令）
4. 累计 ≥3 个不同阻塞全失败 → 整个任务停止

**Leader 收到报告后：** 读报告 → 转述用户 → 等确认 → 重新派发。Leader 绝不自己执行。

#### 模型分层

| 角色 | 形态 | 默认模型 | 原因 |
|------|------|----------|------|
| Leader | Codex 主会话 | `gpt-5.5` | 决策质量优先，读/判/派 |
| Planner | 本地派生 agent / planning skill | `gpt-5.4` | 计划草案、依赖拆解 |
| Coder | 本地派生 agent / `$coder` | `gpt-5.4-mini` | 代码实现与测试 |
| Deployer | 本地派生 agent / `$deployer` | `gpt-5.4-mini` | 部署、运行、监控、收集结果 |
| Writer | 本地派生 agent / `$writer` | `gpt-5.4` | 论文、文档、rebuttal |
| Reviewer | 本地独立 reviewer agent | `gpt-5.4` | 原始文件审查，不自审 |

这些是默认 Runtime Binding，不改变 Role Contract。需要更高质量或更低成本时，可以按部署策略覆盖模型，但不能改变 Leader / Planner / Coder / Deployer / Writer / Reviewer 的职责边界。
- 输出审查报告（pass/fail + 具体问题）

#### Runtime Task Protocol

Leader / Planner / Coder / Deployer / Writer / Reviewer 都必须遵循 `skills/shared-references/runtime-task-protocol.md`。这不是普通建议，而是 `lane status`、heartbeat 和 auto-wakeup 能正确判断任务是否仍活跃的文件协议。

- 被派生 agent 启动、更新、完成时写自己的 agent status。
- 长任务必须先写 job handle、日志路径、结果路径和 `next_expected_update`。
- Leader 创建派生 Runtime Task 时必须带 `--next-expected-update`；缺失会在创建/更新时被拒绝。
- 需要作为成功条件的产物用 `--required-artifact PATH` 声明；`completed` / `resolved` 前路径必须存在。
- Reviewer 的终态成功必须带 `--verdict-artifact PATH`，且 verdict 文件必须存在；缺 verdict 不等价于 Reviewer fail，而是派生 Agent 可观测性失败。
- 重试必须创建新的 Runtime Task id，并用 `--retry-of OLD_TASK_ID` 链回旧尝试；不能复用同一个 task id。
- 旧任务被新任务、主会话例外或人工决策替代时，Leader 写 `task.superseded` / `task.resolved_by`。
- Leader 判定旧任务不能恢复时，写带终态 status 的 `leader.decision`。
- Leader 的嵌入式 Coder/Deployer/Writer prompt 和 Reviewer prompt 模板也必须显式带上 `agent_id`、status 写入要求和 verdict/result artifact 路径；只在 Skill DAG 上声明依赖不够。
- 缺 status、缺 expected update、缺 terminal artifact、缺 verdict artifact 或缺 resolution 会被框架硬校验为拒绝创建/终态、`stale`、`anomaly` 或 wakeup candidate。

#### 文件协作

各 agent 在同一项目目录通过文件通信：
- Leader 产出：`refine-logs/EXPERIMENT_PLAN.md`、`.labline/runtime/pipelines/leader.json`、`CLAUDE.md` Pipeline Status
- Coder 产出：`code/`、测试、偏差记录
- Deployer 产出：job handle、日志、`refine-logs/EXPERIMENT_RESULTS/`
- Writer 产出：`paper/`、报告、rebuttal
- Reviewer 产出：审查报告（JSON + Markdown）

产出后在 `MANIFEST.md` 登记。

---

### Skill 详解

#### 完整 Skill 列表入口

本节只放常用 skill 的快速入口和典型用法。完整列表见：

- [中文 Skill Catalog](SKILL_CATALOG_CN.md)
- [英文 Skill Catalog](SKILL_CATALOG.md)

#### 研究发现类

##### `$idea-discovery`
AI 驱动的创新点发现。读取领域文献，找 gap，生成可验证的 idea。

```
$idea-discovery "增量目标检测" --sources all
```

输出：`idea-stage/IDEAS.md`

##### `$research-lit`
多源文献综述。支持 Semantic Scholar、Gemini、OpenAlex。

```
$research-lit "few-shot class-incremental learning" --sources all,gemini
```

##### `$novelty-check`
验证 idea 是否已有人做过。

```
$novelty-check "用频域特征做增量学习的原型对齐"
```

#### 实验类

##### `$experiment-plan`
制定严格的实验计划，包含：
- Expectation Declaration（预期声明）
- Execution Spec（执行规格：variants / metrics / seeds）
- Data Flow Summary（数据流）
- Delta Assertion（对照差异断言）

```
$experiment-plan
```

输出：`refine-logs/EXPERIMENT_PLAN.md`

##### `$experiment-bridge`
将实验计划转化为可执行代码。

```
$experiment-bridge
```

读取 `EXPERIMENT_PLAN.md`，产出代码到 `code/`。

##### `$experiment-audit`
独立审计实验诚实度。检查：
- 是否有 fake GT
- 是否有 score normalization fraud
- 是否有 phantom results
- 评估类型是否与声明一致

```
$experiment-audit
```

##### `$run-experiment`
远程执行实验。读 `project.yaml` 的 servers 配置。

```
$run-experiment --server gpu-server-1 --script code/train.py
```

##### `$monitor-experiment`
监控正在运行的实验。

```
$monitor-experiment --server gpu-server-1
```

#### 论文类

##### `$paper-writing`
完整论文撰写 pipeline（6+ phases）。

```
$paper-writing --effort balanced --assurance submission
```

effort 级别：`lite` / `balanced` / `max` / `beast`
assurance 级别：`draft` / `submission`（submission 强制跑审计）

##### `$auto-paper-improvement-loop`
自动迭代改进论文。每轮：AI 审稿 → 找问题 → 修改 → 再审。

```
$auto-paper-improvement-loop "paper/" --max-rounds 3
```

##### `$rebuttal`
审稿回复。读取审稿意见，生成结构化回复。

```
$rebuttal "paper/ + reviews" --venue ICML --character-limit 5000
```

输出：`PASTE_READY.txt`（直接粘贴）+ `REBUTTAL_DRAFT_rich.md`

##### `$paper-slides` / `$paper-poster` / `$paper-talk`
演示材料生成。

```
$paper-slides "paper/"      # Beamer + PPTX + speaker notes
$paper-poster "paper/"      # A0 poster
$paper-talk "paper/"        # 完整演讲 pipeline
```

#### 质量保证类

##### `$proof-checker`
数学证明验证。

```
$proof-checker "paper/sections/theory.tex"
```

##### `$citation-audit`
引用完整性审计。检查悬空引用、未引用 bib 条目。

```
$citation-audit "paper/" --uncited
```

##### `$kill-argument`
对抗性审查：模拟最严厉的 area chair 写拒稿意见，再独立判定是否已在论文中回应。

```
$kill-argument "paper/"
```

---

### 代码同步

#### `$sync push` — 保存并上传

```
$sync push                          # 自动生成 commit message
$sync push --message "实现 backbone"  # 指定 message
```

流程：`git add -A` → `git commit` → `git push`

如果没配 remote，只做本地 commit。

#### `$sync pull` — 拉取最新

```
$sync pull
```

流程：自动 stash → `git pull --rebase` → pop stash

#### `$sync deploy` — 部署到服务器

```
$sync deploy                    # 部署到所有配置的服务器
$sync deploy --server gpu-server-1   # 只部署到指定服务器
```

通过 rsync 同步，自动排除 `sync_exclude` 中的文件。

#### `$sync status` — 查看状态

```
$sync status
```

显示：本地修改数、与 remote 的差异、各服务器同步状态。

#### 独立脚本（不依赖 Codex）

```bash
bash tools/sync.sh push --message "msg"
bash tools/sync.sh pull
bash tools/sync.sh deploy --server gpu-server-1
bash tools/sync.sh status
```

#### 运行态状态与心跳

Labline 新项目的机器可读运行态写在项目内 `.labline/runtime/`。这里保存 Runtime Task、事件、lease、heartbeat、watchdog/queue mirror、foreground transport 记录和派生摘要；根目录 `PIPELINE_STATE.json` 只作为旧项目迁移输入，新项目不再创建。

首次需要 runtime 状态时可以显式初始化：

```bash
lane runtime init
```

查看当前项目状态：

```bash
lane status --json
lane status --brief
```

`lane status --json` 面向脚本和 bridge；`lane status --brief` 面向人类快速扫描。两者都会从 `.labline/runtime/`、兼容的旧 agent status、queue、watchdog 和 pipeline state 聚合当前状态，并写入 `.labline/runtime/summaries/current.json` / `current.md`。

`lane status --json` 同时输出 `metrics.delegated_agent_observability`。其中 `observability_failure_rate = observability_failures / delegated_agent_tasks`，只统计 Leader 派生 agent 的可观测性失败，不代表实验失败率、Reviewer verdict 失败率或总体任务失败率。`lane workflow wakeup-plan` 会把同一指标透传为 `summary_metrics`，供 Leader 判断当前是否是 executor/transport 健康问题。

Runtime terminal gate 会在 `lane runtime task complete` / `resolved` 类成功终态上检查声明产物：`--required-artifact` 指向的路径必须存在；Reviewer 还必须提供已存在的 `--verdict-artifact`。如果只是缺状态或缺 verdict 文件，按 Delegated Agent Observability Failure 处理，由 Leader 决定是否新建 retry task；runtime 不会自动把旧 task 重试成同一个身份。

短时 Reviewer gate 可以用 foreground transport 明确留下可观测 handle：

```bash
lane workflow foreground-review task-reviewer-r003-retry2 \
  --agent-id reviewer-r003-retry2 \
  --prompt-file prompts/reviewer-r003.md \
  --verdict-artifact refine-logs/R003_REVIEW.md
```

该命令会在运行前写入 `cli_session` job handle 和 `.labline/runtime/agents/<agent_id>.json`，执行 `codex exec` 后只有在返回码为 0 且 verdict artifact 存在时才把 Runtime Task 标为 completed；否则标为 failed。`TASK_ID` 使用 `task-reviewer-...`，避免与派生 agent status task `agent:<agent_id>` 的文件名相撞。它用于短 gate、review 和可观测性 retry，不用于训练、部署、下载或其它长任务。

长训练、部署、下载或批量实验需要先暴露 durable handle，再等待产物。优先使用 tmux launcher：

```bash
lane workflow tmux-job task-deployer-r003-stage-a-teacher-train-retry2 \
  --agent-id deployer-r003-stage-a-teacher-train-retry2 \
  --session r003_stage_a_teacher_train_retry2 \
  --command 'python tools/train.py configs/r003_stage_a_teacher.py --work-dir refine-logs/EXPERIMENT_RESULTS/R003_stage_a_teacher/work_dirs/stage_a_teacher_sanity' \
  --log refine-logs/EXPERIMENT_RESULTS/R003_stage_a_teacher/stage_a_teacher_train_retry2.log \
  --required-artifact refine-logs/EXPERIMENT_RESULTS/R003_stage_a_teacher/work_dirs/stage_a_teacher_sanity/epoch_2.pth \
  --next-expected-update 2026-07-06T18:30:00Z
```

该命令会启动 tmux session，并写入 Runtime Task `job_handles`、`.labline/runtime/jobs/<job_id>.json`、`.labline/runtime/agents/<agent_id>.json`、`.labline/runtime/jobs/<job_id>.exitcode` 路径和 `job.started` 事件。启动者只负责留下 durable handle，可以在确认 handle 写入后退出；它不代表训练成功。成功仍以 exit code、log、session 状态和声明的 `--required-artifact` 为准。`lane workflow wakeup-plan` 会检查 detached tmux session：session 已退出、exit code 为 0 或暂不可得、且 required artifact 存在时产生 `detached_job_completed` candidate；session 已退出但 exit code 非 0 或 required artifact 缺失时产生 `detached_job_exited` candidate，交给 Leader 检查日志并记录终态。`TASK_ID` 使用 `task-deployer-...`，不要使用 `agent-deployer-...`，避免和派生 agent status task 撞名。

需要检查 due task 或长期任务时使用 heartbeat：

```bash
lane heartbeat
lane heartbeat --dry-run
lane heartbeat --task TASK_ID
```

默认 heartbeat 是 escalation-gated：正常平台期只写本地 runtime 事件和 heartbeat 状态，不向用户连续推送，也不唤醒 Leader；只有 terminal、blocked、need_decision、anomaly、stale 等需要处理的状态才写 heartbeat escalation，并通过 lease 避免多个入口同时控制同一任务。`lane workflow wakeup-plan` 不要求先运行 heartbeat：未被 `leader.decision` / `task.resolved` / `task.superseded` 处理过、且未被后续 `retry_of` 取代的 `failed` / `cancelled` 终态会直接成为 `terminal_result` wakeup candidate；detached tmux job 结束后也会按 required artifact 是否存在成为 `detached_job_completed` 或 `detached_job_exited` candidate。`ready_to_continue` 表示正常阶段边界已满足，不作为普通 heartbeat escalation；`lane workflow wakeup-plan` 会直接把它归类为 `phase_boundary_ready` wakeup candidate，交给 Leader 做下一步编排。

#### 本地 Debug Smoke

想从用户侧验证一个真实项目是否能跑新 runtime 链路，可以用本地 smoke 命令。默认会复制项目到 debug 工作目录执行，不改源项目，也不需要 Docker：

```bash
lane debug runtime-smoke --project /path/to/project
```

需要脚本读取时：

```bash
lane debug runtime-smoke --project /path/to/project --json
```

它会检查：

- `lane project update` / `lane project doctor`
- 根目录不生成新的 `PIPELINE_STATE.json`
- `lane runtime init`
- 创建临时 Runtime Task
- `lane status --json`
- `lane heartbeat --dry-run` 和真实 heartbeat
- fake Feishu Remote Observation 路由
- `.labline/runtime/` 中不泄漏 chat id、open id 或消息正文

报告写到 `$LABLINE_WORKSPACE/.labline/debug/runtime-smoke/.../debug-report.json` 和 `debug-report.md`。只有明确要原地写入当前项目 runtime 时才使用：

```bash
lane debug runtime-smoke --project . --in-place --yes
```

如果要验证真实长任务生命周期，而不只验证 runtime/Feishu projection 链路，可以运行本地长任务 smoke。它会启动一个短时本地 Python 进程，把它登记为 supervised detached Runtime Task，先确认运行中 heartbeat 是 healthy，再等待进程结束并确认 terminal heartbeat 产生 escalation：

```bash
lane debug longtask-smoke --project /path/to/project
```

需要机器可读报告时：

```bash
lane debug longtask-smoke --project /path/to/project --json
```

默认同样是 copy 模式，不改源项目。报告写到 `$LABLINE_WORKSPACE/.labline/debug/longtask-smoke/.../debug-report.json` 和 `debug-report.md`；工作副本里的 `outputs/labline-debug-longtask/` 会保留 `progress.json`、`result.json` 和 `job.log`。

---

### 远程实验

#### 配置服务器

编辑 `project.yaml`：

```yaml
servers:
  - name: "gpu-server-1"
    host: "gpu-server-1"             # ~/.ssh/config 中的别名
    path: "[服务器上的项目位置]/project"
    conda_env: "lane"
    gpus: [0, 2]

  - name: "gpu-server-2"
    host: "gpu-server-2"
    path: "[另一台服务器上的项目位置]/project"
    conda_env: "torch"
    gpus: [2]
```

#### SSH 配置

确保 `~/.ssh/config` 有对应条目：

```
Host gpu-server-1
    HostName 192.168.1.200        # 替换为实际 IP
    User your_username             # 替换为实际用户名
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

#### 工作流

```
# 1. 本地开发完成
$sync push

# 2. 部署到服务器
$sync deploy --server gpu-server-1

# 3. 远程执行
$run-experiment --server gpu-server-1 --script code/train.py

# 4. 监控
$monitor-experiment --server gpu-server-1

# 5. 结果拉回
# （结果文件通过 rsync 或手动 scp）
```

---

### 论文工作流

#### 完整流程（三边架构）

```
1. $leader "研究方向"
   ├── Phase 1: $idea-discovery → 创新点
   ├── Phase 2: $experiment-plan → 实验计划
   ├── Phase 3: $experiment-bridge → 代码实现
   │            $run-experiment → 远程执行
   │            $experiment-audit → 诚实度审计
   ├── Phase 4: $result-to-claim → 结果→claim
   ├── Phase 5: $paper-writing → 论文撰写
   │            $auto-paper-improvement-loop → 迭代改进
   └── Phase 6: $citation-audit + $proof-checker → 最终审计
```

#### 简化流程（单窗口）

```
$research-pipeline "研究方向"
```

一条命令走完全流程。适合快速验证。

#### 投稿后

```
$rebuttal "paper/ + reviews" --venue ICML    # 回复审稿
$resubmit-pipeline --from ICML --to NeurIPS  # 改投
$paper-slides "paper/"                        # 做 PPT
```

---

### API 配置

#### CC-Switch — API Provider 统一管理（推荐）

容器内可用 [cc-switch-cli](https://github.com/SaladDay/cc-switch-cli) 管理 Codex、Claude Code、Gemini 等多个 CLI 的 API 配置。Labline 默认入口是 Codex。

#### 基本用法

```bash
# 添加 provider
cc-switch provider add --name "中转站A" \
    --base-url "https://proxy.example.com/v1" \
    --api-key "sk-xxx" \
    --model "claude-sonnet-4-20250514"

# 添加第二个 provider
cc-switch provider add --name "官方" \
    --base-url "https://api.anthropic.com" \
    --api-key "sk-ant-xxx" \
    --model "claude-sonnet-4-20250514"

# 切换（一键写入 Codex / Claude Code 配置文件）
cc-switch provider switch 1        # 切到中转站A
cc-switch provider switch 2        # 切到官方

# 测速
cc-switch provider test            # 测试所有 provider 延迟

# 查看当前配置
cc-switch provider list
```

#### 指定目标 APP

```bash
cc-switch provider switch 1 --app claude    # 只改 Claude Code
cc-switch provider switch 2 --app codex     # 只改 Codex
```

#### Win11 用户（GUI 版）

本地电脑装 [CC-Switch GUI](https://github.com/farion1231/cc-switch)（桌面版），管理本地的 Codex / Claude Code 配置。

> ⚠️ GUI 版不支持远程配置服务器。Win11 管 Win11，服务器 CLI 管服务器，各自独立。

#### 模型分层策略

三边架构使用不同模型，平衡成本与质量：

| 角色 | 默认模型 | 说明 |
|------|----------|------|
| Leader | GPT-5.5 / Codex profile | 决策质量优先 |
| Planner | GPT-5.4 / Codex profile | 自动计划草案、任务拆解 |
| Coder | GPT-5.4-mini / Codex profile | 代码实现、测试、修 bug |
| Deployer | GPT-5.4-mini / Codex profile | 部署、运行、监控、收集结果 |
| Writer | GPT-5.4 / Codex profile | 论文、文档、rebuttal |
| Reviewer | GPT-5.4 / independent Codex profile | 本地独立审查，不依赖 MCP |

三边角色通过本地 Codex profile 和项目文件区分职责；Claude Code provider 只影响兼容模式。

#### 预配 Provider（cc-switch）

容器启动后建议先配置 Codex 可用的 OpenAI-compatible provider：

```bash
# Codex 主力 provider
cc-switch provider add --name "codex-main" \
    --base-url "https://your-proxy.com/v1" \
    --api-key "sk-proxy-xxx" \
    --model "gpt-5.5"

# DeepSeek / 其他 OpenAI-compatible 备用
cc-switch provider add --name "deepseek" \
    --base-url "https://api.deepseek.com/v1" \
    --api-key "sk-deepseek-xxx" \
    --model "deepseek-v4-pro"
```

切换：
```bash
cc-switch provider switch 1 --app codex
cc-switch provider switch 2 --app codex
```

> ⚠️ 切换是 CLI 配置级的。三边角色的职责由 Codex profile 和项目文件约束区分。

#### 个人覆盖（容器内）

##### Claude Code

```bash
cat > ~/.claude/settings.json <<'EOF'
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-my-key",
    "ANTHROPIC_BASE_URL": "https://my-proxy.com/anthropic"
  }
}
EOF
```

##### Codex CLI

```bash
# ~/.codex/auth.json
{"OPENAI_API_KEY": "sk-my-key"}

# ~/.codex/config.toml
model_provider = "my_proxy"
model = "gpt-5.5"
[model_providers.my_proxy]
base_url = "https://my-proxy.com/v1"
wire_api = "responses"
```

#### 代理/VPN

如果用 Anthropic 官方 API 或 Claude Coding Plan：

```env
HTTP_PROXY=http://host.docker.internal:7890
HTTPS_PROXY=http://host.docker.internal:7890
NO_PROXY=127.0.0.1,localhost
http_proxy=http://host.docker.internal:7890
https_proxy=http://host.docker.internal:7890
no_proxy=127.0.0.1,localhost
```

宿主机跑 Clash/V2Ray 监听 7890，`host.docker.internal` 自动解析到宿主机。

如果 `curl` 能联网但 `git clone` / `git pull` 失败，再配置 git 专用代理：

```bash
git config --global http.proxy "$HTTP_PROXY"
git config --global https.proxy "$HTTPS_PROXY"
```

#### 免费方案

- ModelScope：见 `docs/MODELSCOPE_GUIDE.md`
- MiniMax + GLM：见 `docs/MiniMax-GLM-Configuration.md`

---

### 飞书 / Lark 远程入口

Labline 默认通过外部 `lark-channel-bridge` 连接飞书/Lark 和本地 Codex/Claude Code。Labline 的稳定入口是短命令 `lane feishu ...`。

首次安装和检查：

```bash
lane feishu install
lane feishu doctor
```

默认安装到当前用户的 `~/.labline/node`，普通用户不需要 sudo。管理员确实要装到系统 npm 目录时再用：

```bash
lane feishu install --scope system
```

在项目目录前台启动 Codex 远程会话：

```bash
cd [你的project位置]
lane feishu run
```

确认扫码和收发消息正常后，改为后台服务：

```bash
cd [你的project位置]
lane feishu start
lane feishu status
lane feishu logs --tail 50
```

如果启动时报 `could not resolve bot identity` 或飞书开放平台 502，先试直连禁用代理：

```bash
lane feishu run --no-proxy
```

如果 `--no-proxy` 能连飞书，但 Codex 子进程卡在 `Network unreachable` / `request timed out`，保留 `--no-proxy`，同时只给 agent 子进程设置代理：

```bash
LABLINE_AGENT_HTTP_PROXY=http://127.0.0.1:[你的代理端口] \
LABLINE_AGENT_HTTPS_PROXY=http://127.0.0.1:[你的代理端口] \
LABLINE_AGENT_NO_PROXY=127.0.0.1,localhost,::1 \
lane feishu run --no-proxy
```

`LABLINE_AGENT_*_PROXY` 会注入普通 Codex bridge turn 和 `native-codex` auto-wakeup；不会让 Feishu SDK 走代理。

Claude Code 用独立 profile：

```bash
cd [你的project位置]
lane feishu run --profile lane-claude --agent claude
```

飞书入口只是 transport adapter，不是远程 shell，也不替代 Leader。实际代码修改、工具执行和权限判断仍发生在本地 Codex/Claude Code session 中。详细配置见 `docs/FEISHU_INTEGRATION.md`。

远控长任务不要占住当前飞书卡片。预计超过 3 分钟的安装、编译、下载、训练、部署、批量评估或长时间等待，必须先写 `.labline/runtime/` 状态和 durable job handle；Leader 最多短等 120 秒后收口，后续通过 `/status`、`/follow`、heartbeat 或 monitor 投影。普通 progress 由当前 workspace/project 的 `/follow` poller 节流更新同一张投影状态卡；换 bridge profile 后应在新 bot chat 里重新 `/follow`，只有确认新旧 profile 使用同一个可投递 bot/chat 权限时才开启 `LABLINE_PROJECTION_INCLUDE_CROSS_PROFILE=1`。completed、failed、cancelled、blocked、need_decision、anomaly、heartbeat escalation、phase_boundary_ready wakeup，以及卡片长时间停在“正在调用工具/正在输出”等旧阶段时的 `stale_projection` 提示，才需要新的可见推送；`stale_projection` 只表示飞书显示可能过期，不表示任务失败。

普通飞书消息的 streaming card 也有显示层兜底，不要求用户提前判断是否是长任务。bridge 会优先更新原卡片；如果 stream/update 报错、update 超时，或运行中健康探针发现上一张卡片已经不能确认更新，会自动发新的续接卡片并继续在新卡片上更新。若 profile 使用 markdown streaming，终态更新会等待 Feishu markdown card 的 throttle flush 和 update queue drain，并默认 fetch 校验原 streaming message 是否仍含“正在调用工具/正在输出/正在思考”；若校验失败或仍是旧运行态，会额外发送一条普通 markdown 终态镜像。续接卡片和终态镜像只是显示通道兜底，不表示本地 Codex 任务重启；如需完全关闭终态镜像，可设置 `LABLINE_MARKDOWN_TERMINAL_FALLBACK_ENABLED=off`。

需要自动唤醒 Leader 时，按 profile 显式设置 `LABLINE_AUTO_WAKEUP_ENABLED=1` 并重启 bridge。启用后 bridge 只做轻量触发：定时运行 `lane workflow wakeup-plan`，当 runtime escalation、未处理的 `failed` / `cancelled` terminal Runtime Task、detached tmux job 已退出且需要 Leader 检查 artifact/log，或 `phase_boundary_ready` candidate 可接手且 `leader_session` lease 可用时，启动 `lane workflow wakeup --backend native-codex`。去重、lease、prompt、完成/失败记录都写在 `.labline/runtime/`；高风险 control intent 仍需要人工确认，不会被自动执行。若确认同一 `wakeup_key` 的上一次唤醒没有真正接手，可以先用 `lane workflow wakeup-plan --force` 预览，再用 `lane workflow wakeup --force --backend native-codex` 重试；`--force` 只绕过去重，不绕过高风险确认和 `leader_session` lease。`native-codex` wakeup 默认用 `codex exec -s danger-full-access`，不依赖 `bwrap` sandbox；如需收紧可设置 `LABLINE_AUTO_WAKEUP_CODEX_SANDBOX=workspace-write|read-only` 或传 `--codex-sandbox`。bridge 会把 started、completed、failed、非健康 skip 和 `needs_confirmation` 发到当前 profile/project 的 active `/follow` chat；也可用 `LABLINE_AUTO_WAKEUP_CHAT_ID` 指定固定投递 chat。跨 profile 通知默认关闭，只有确认同一个 bot 可以投递目标 chat 时才开启 `LABLINE_AUTO_WAKEUP_INCLUDE_CROSS_PROFILE=1`。同一检查结果按 `LABLINE_AUTO_WAKEUP_NOTICE_THROTTLE_MS` 限流。用户可见的自动唤醒结论默认使用中文解释，英文只保留在必要的标识符、路径、状态值中。

多人共用同一台服务器、同一 Linux 账户时，至少用不同 `--home`、`--profile` 和 `--workspace` 隔离：

```bash
lane feishu start --home /root/.lark-channel-user-a --profile user-a-codex --workspace /lane/projects/user-a-project
lane feishu start --home /root/.lark-channel-user-b --profile user-b-codex --workspace /lane/projects/user-b-project
```

---

### 框架管理

#### 更新框架

只检查是否有新版本，不改变本地 framework：

```bash
lane framework check-update
```

输出含义：

| status | 含义 |
|--------|------|
| `up-to-date` | 当前 framework 已经是 upstream 最新 |
| `update available` | upstream 有新提交，可以运行 `lane framework update` |
| `local ahead` | 本地比 upstream 新，通常是本地开发或未推送 |
| `diverged` | 本地和 upstream 分叉，需要人工处理 |
| `unknown` | 当前 framework 没有配置 upstream |

容器启动、进入交互 shell、打开 tmux pane 时都会触发一次轻量检查入口；默认最多每天联网检查一次，且每个用户每天最多提醒一次。它只检查，不会自动更新。

```
lane framework update
```

默认行为：更新你自己的 framework copy，然后根据 Project Registry 自动同步已登记项目。若只想更新 framework，不同步项目：

```bash
lane framework update --no-project-sync
```

如果更新后遇到兼容性问题：

```bash
lane framework rollback
```

#### 项目接入更新

单个项目重建 Labline 接入：

```bash
lane project update
```

查看版本：

```bash
lane framework --version
lane project --version
```

---

### 多人协作

#### Git 工作流

每人 fork 框架仓库，独立开发：

```
upstream (your-org/lane-framework)
  ├── fork-zhangsan
  ├── fork-lisi
  └── fork-wangwu
```

定期同步上游：
```bash
git fetch upstream
git merge upstream/main
```

#### 科研项目协作

科研项目用 Gitea（Docker 部署自带）：

```
Gitea (http://gitea:3000)
  ├── zhangsan/frequency-detection
  ├── zhangsan/ntn-scheduling
  └── lisi/point-cloud-seg
```

每人管自己的项目。需要协作时：
1. 在 Gitea 上 fork 对方项目
2. 各自开发
3. 通过 Pull Request 合并

## 管理员手册

### Docker 多人环境

每人一个长期容器。每个容器有自己的 `/lane/framework` 和 `/lane/projects`；数据集、预训练模型、下载缓存共享：

```
┌─────────────────────────────────────────┐
│ Host Server                              │
├──────────┬──────────┬───────────────────┤
│ lane-    │ lane-    │ lane-gitea        │
│ zhangsan │ lisi     │ (git server)      │
├──────────┴──────────┴───────────────────┤
│ Shared Volumes:                          │
│  [你的数据集目录] -> /lane/shared/datasets (ro)     │
│  shared-pretrained -> /lane/shared/pretrained        │
│  shared-downloads -> /lane/shared/downloads          │
│ Per-user Volumes:                        │
│  zhangsan/framework -> lane-zhangsan:/lane/framework │
│  lisi/framework -> lane-lisi:/lane/framework         │
│  user1-projects -> lane-zhangsan:/lane/projects     │
│  user2-projects -> lane-lisi:/lane/projects         │
│  zhangsan/.labline -> lane-zhangsan:~/.labline             │
│  lisi/.labline -> lane-lisi:~/.labline                     │
└─────────────────────────────────────────┘
```

添加新用户：编辑 `.env` + `docker-compose.yaml`，`docker compose up -d`。

### API Provider 配置

不要把 API key 预填在 `deploy/.env` 里让所有用户容器继承。每个用户进入自己的容器后用 `cc-switch-cli` 配置 Codex/Claude provider；这样可以避免多人共用 key、误覆盖 provider 或把 key 写进部署文件。

```bash
cc-switch provider add --name "codex-main"
cc-switch provider list
cc-switch provider switch 1
```

### Framework 更新检查策略

管理员提供每个用户的初始 framework copy，但不在后台强制更新用户的 framework。容器启动、进入交互 shell、打开 tmux pane 时默认都会触发一次轻量检查入口：

```bash
lane framework check-update --lane-repo /lane/framework --if-stale 1d --notify
```

`--if-stale 1d` 让同一用户每天最多联网检查一次；`--notify` 让同一用户每天最多看到一次更新提醒。这只提示是否有 upstream 更新，不会 `git pull`。用户确认后自己运行：

```bash
lane framework update
```

如果实验期需要固定版本，可以在 `.env` 中关闭启动检查：

```env
LABLINE_AUTO_CHECK_UPDATE=0
```

检查间隔和超时也可以调：

```env
LABLINE_UPDATE_CHECK_INTERVAL=1d
LABLINE_UPDATE_CHECK_TIMEOUT=10s
```

---

### 故障排查

#### Codex 相关

| 问题                                | 解决                                              |
| ----------------------------------- | ------------------------------------------------- |
| Skill 不可用                         | 检查 `.agents/skills/` symlink 是否存在且指向正确 |
| `lane framework update` 报 "有本地修改" | 先提交/保存本地修改，或手动处理 framework git 状态 |
| `lane project update` 报旧 ARIS symlink conflict | 运行 `lane project migrate-aris`，确认后加 `--apply` |
| API 403/401                         | 检查 key 是否过期，base_url 是否正确              |
| Codex 返回空                         | 检查 `~/.codex/config.toml` 的 base_url            |

#### Git/Sync 相关

| 问题                        | 解决                                     |
| --------------------------- | ---------------------------------------- |
| `$sync push` 报 "no remote" | 编辑 `project.yaml` 的 `git.remote` 字段 |
| push 被拒绝                 | `git pull --rebase` 后重试               |
| stash 冲突                  | `git stash show -p` 查看冲突，手动解决   |
| deploy rsync 超时           | 检查 SSH config，确认 `ssh HOST` 能连通  |

#### Docker 相关

| 问题                     | 解决                                           |
| ------------------------ | ---------------------------------------------- |
| `docker compose up` 失败 | Docker 版本需 24.0+（`docker compose` 子命令） |
| Gitea 502                | 首次启动慢，等 30s 重试                        |
| 容器内 `git push` 失败   | 检查 GITEA_TOKEN 环境变量                      |
| SSH key 不可用           | 检查 volume mount，`ls ~/.ssh/`                |

#### GPU 服务器相关

| 问题               | 解决                                                         |
| ------------------ | ------------------------------------------------------------ |
| CUDA not available | 检查 `CUDA_VISIBLE_DEVICES`、`LD_LIBRARY_PATH`               |
| PyTorch 版本不匹配 | 用 `--index-url https://download.pytorch.org/whl/cu118` 重装 |
| OOM (显存不足)     | 减小 batch size，或换卡                                      |
| rsync 不存在       | 用 `tar czf -                                                | ssh tar xzf -` 替代 |

#### Claude Code 兼容相关

| 问题              | 解决                                    |
| ----------------- | --------------------------------------- |
| Skill 不出现在 `/` 补全中 | 检查 `.claude/skills/` symlink 是否存在且指向正确 |
| "context window exceeded" | 正常，Claude Code 会自动压缩上下文继续 |
| "model not found" | 确认 provider 支持指定模型 |

---

## 附录：完整 Skill 列表

→ 见 [docs/SKILL_CATALOG.md](SKILL_CATALOG.md)（英文）| [docs/SKILL_CATALOG_CN.md](SKILL_CATALOG_CN.md)（中文）

当前 skill 数量和分类以自动生成目录为准。运行 `python3 tools/generate_skill_catalog.py` 更新。
