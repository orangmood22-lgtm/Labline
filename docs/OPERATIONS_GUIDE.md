# ARIS 操作与运维手册

> 分为用户手册和管理员手册。用户手册讲项目创建、日常 workflow、框架更新；管理员手册讲多人容器、共享资产和部署维护。

---

## 目录

1. [用户手册](#用户手册)
   - [概念](#概念)
   - [项目生命周期](#项目生命周期)
     - [创建项目](#创建项目)
     - [日常开发](#日常开发)
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
| 位置 | 管理员分配；容器内通常是 `/aris/framework` | 容器内通常在 `/aris/projects` 下 |
| 更新 | `aris framework update` / `aris framework rollback` | 用户自行管理 |
| 共享 | 每个用户一份 framework copy，同一用户项目共享 | 每人/每方向独立 |

框架通过 symlink 安装到项目中：Codex 默认使用 `.agents/skills/`，Claude Code 兼容模式使用 `.claude/skills/`。

#### project.yaml

每个科研项目的核心配置文件，由 `aris project init` 生成：

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
    conda_env: "aris"
    gpus: [0, 2]

framework:
  path: "[你的framework位置]"
  repo: "https://github.com/your-org/aris-framework.git"

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

#### Step 1: 用 `aris project init` 初始化项目

`aris project init PATH` 是新手创建项目的**首选入口**。它会调用底层安装器并生成项目骨架。`PATH` 必填，`.` 表示当前目录。

```bash
# 当前目录初始化/接入
mkdir -p ~/projects/my-research
cd ~/projects/my-research
aris project init . --direction "研究方向"

# 从父目录创建项目；目录不存在会自动创建
cd ~/projects
aris project init ./my-research --direction "研究方向"

# 已有项目半路接入 ARIS
cd /path/to/existing-project
aris project init . --direction "研究方向"
```

安装完成后项目结构：

```
my-research/
├── project.yaml
├── AGENTS.md              ← Codex 上下文（需编辑：填研究方向、服务器等）
├── CLAUDE.md              ← Claude Code 兼容上下文
├── .agents/skills/        ← Codex skills symlinks
├── .claude/skills/        ← Claude Code 兼容 symlinks
├── .aris/
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
aris project doctor
```

如果需要手动补充研究方向、服务器、约束，可再编辑 `AGENTS.md`；Claude Code 兼容模式同步参考 `CLAUDE.md`。

#### Step 3: 进入 Codex 开始工作

```bash
cd ~/projects/my-research
codex
```

进入后直接用 `$leader`、`$experiment-plan` 等 skill。Claude Code 兼容模式使用 `/skill-name`。

#### 项目放哪？

普通用户只需要知道自己的项目通常放在 `/aris/projects` 或管理员指定的项目工作区。framework 位置由管理员分配；容器内通常是 `/aris/framework`。

```
/aris/framework/              # 你的 framework copy

/aris/projects/               # 你的项目工作区
├── exp-detection/
└── exp-segmentation/
```

**关键点：**

- 每个用户有自己的 framework copy；该用户的项目通过 symlink 共享这份 copy
- 项目之间完全独立（各自 git repo、各自 `AGENTS.md`）
- `aris framework update` 默认同步更新已登记项目
- 单个项目可手动运行 `aris project update`

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
aris framework --version
aris framework update
aris framework rollback
```


---

### 三边架构使用

#### 启动方式

默认只需要一个 Codex 主会话。Leader 在本会话中编排并派生本地 agents；Executor 拆成 Coder / Deployer / Writer 三个执行子职责；Reviewer 是本地独立审查 agent。Claude Code 只作为兼容客户端。

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

**Executor 拆成三个子职责：**
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

| 角色 | 形态 | 原因 |
|------|------|------|
| Leader | Codex 主会话 | 决策质量优先，读/判/派 |
| Coder | 本地派生 agent / `$coder` | 代码实现与测试 |
| Deployer | 本地派生 agent / `$deployer` | 部署、运行、监控、收集结果 |
| Writer | 本地派生 agent / `$writer` | 论文、文档、rebuttal |
| Reviewer | 本地独立 reviewer agent | 原始文件审查，不自审 |
- 输出审查报告（pass/fail + 具体问题）

#### 文件协作

各 agent 在同一项目目录通过文件通信：
- Leader 产出：`refine-logs/EXPERIMENT_PLAN.md`、`PIPELINE_STATE.json`
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

---

### 远程实验

#### 配置服务器

编辑 `project.yaml`：

```yaml
servers:
  - name: "gpu-server-1"
    host: "gpu-server-1"             # ~/.ssh/config 中的别名
    path: "[服务器上的项目位置]/project"
    conda_env: "aris"
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

容器内可用 [cc-switch-cli](https://github.com/SaladDay/cc-switch-cli) 管理 Codex、Claude Code、Gemini 等多个 CLI 的 API 配置。ARIS 默认入口是 Codex。

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

| 角色 | 主力 | 说明 |
|------|------|------|
| Leader | GPT-5.5 / Codex profile | 决策质量优先 |
| Executor Agent | GPT-5.5 / Codex profile | 实现、部署、论文撰写 |
| Reviewer | GPT-5.5 / independent Codex profile | 本地独立审查，不依赖 MCP |

三边角色通过本地 Codex profile 区分职责；Claude Code provider 只影响兼容模式。

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

### 框架管理

#### 更新框架

只检查是否有新版本，不改变本地 framework：

```bash
aris framework check-update
```

输出含义：

| status | 含义 |
|--------|------|
| `up-to-date` | 当前 framework 已经是 upstream 最新 |
| `update available` | upstream 有新提交，可以运行 `aris framework update` |
| `local ahead` | 本地比 upstream 新，通常是本地开发或未推送 |
| `diverged` | 本地和 upstream 分叉，需要人工处理 |
| `unknown` | 当前 framework 没有配置 upstream |

容器启动、进入交互 shell、打开 tmux pane 时都会触发一次轻量检查入口；默认最多每天联网检查一次，且每个用户每天最多提醒一次。它只检查，不会自动更新。

```
aris framework update
```

默认行为：更新你自己的 framework copy，然后根据 Project Registry 自动同步已登记项目。若只想更新 framework，不同步项目：

```bash
aris framework update --no-project-sync
```

如果更新后遇到兼容性问题：

```bash
aris framework rollback
```

#### 项目接入更新

单个项目重建 ARIS 接入：

```bash
aris project update
```

查看版本：

```bash
aris framework --version
aris project --version
```

---

### 多人协作

#### Git 工作流

每人 fork 框架仓库，独立开发：

```
upstream (your-org/aris-framework)
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

每人一个长期容器。每个容器有自己的 `/aris/framework` 和 `/aris/projects`；数据集、预训练模型、下载缓存共享：

```
┌─────────────────────────────────────────┐
│ Host Server                              │
├──────────┬──────────┬───────────────────┤
│ aris-    │ aris-    │ aris-gitea        │
│ zhangsan │ lisi     │ (git server)      │
├──────────┴──────────┴───────────────────┤
│ Shared Volumes:                          │
│  [你的数据集目录] -> /aris/shared/datasets (ro)     │
│  shared-pretrained -> /aris/shared/pretrained        │
│  shared-downloads -> /aris/shared/downloads          │
│ Per-user Volumes:                        │
│  zhangsan/framework -> aris-zhangsan:/aris/framework │
│  lisi/framework -> aris-lisi:/aris/framework         │
│  user1-projects -> aris-zhangsan:/aris/projects     │
│  user2-projects -> aris-lisi:/aris/projects         │
│  zhangsan/.aris -> aris-zhangsan:/aris/.aris         │
│  lisi/.aris -> aris-lisi:/aris/.aris                 │
└─────────────────────────────────────────┘
```

添加新用户：编辑 `.env` + `docker-compose.yaml`，`docker compose up -d`。

### API Provider 预配

组统一 provider 放在 `.env`，所有用户容器会继承；用户仍可在容器内用 `cc-switch provider add` 添加自己的 key 覆盖。

```env
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_BASE_URL=                    # 留空=官方，填中转站 URL
OPENAI_API_KEY=sk-xxx                  # Codex 主入口和本地 Reviewer 用
```

容器启动后可批量预配：

```bash
cc-switch provider add --name "组统一-中转站" \
    --base-url "$ANTHROPIC_BASE_URL" \
    --api-key "$ANTHROPIC_API_KEY" \
    --model "claude-sonnet-4-20250514"
cc-switch provider switch 1
```

### Framework 更新检查策略

管理员提供每个用户的初始 framework copy，但不在后台强制更新用户的 framework。容器启动、进入交互 shell、打开 tmux pane 时默认都会触发一次轻量检查入口：

```bash
aris framework check-update --aris-repo /aris/framework --if-stale 1d --notify
```

`--if-stale 1d` 让同一用户每天最多联网检查一次；`--notify` 让同一用户每天最多看到一次更新提醒。这只提示是否有 upstream 更新，不会 `git pull`。用户确认后自己运行：

```bash
aris framework update
```

如果实验期需要固定版本，可以在 `.env` 中关闭启动检查：

```env
ARIS_AUTO_CHECK_UPDATE=0
```

检查间隔和超时也可以调：

```env
ARIS_UPDATE_CHECK_INTERVAL=1d
ARIS_UPDATE_CHECK_TIMEOUT=10s
```

---

### 故障排查

#### Codex 相关

| 问题                                | 解决                                              |
| ----------------------------------- | ------------------------------------------------- |
| Skill 不可用                         | 检查 `.agents/skills/` symlink 是否存在且指向正确 |
| `aris framework update` 报 "有本地修改" | 先提交/保存本地修改，或手动处理 framework git 状态 |
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
