# ARIS 详细操作手册

> 日常使用参考。覆盖所有 skill、工作流、配置、故障排查。

---

## 目录

1. [概念](#概念)
2. [项目生命周期](#项目生命周期)
3. [三边架构使用](#三边架构使用)
4. [Skill 详解](#skill-详解)
5. [代码同步](#代码同步)
6. [远程实验](#远程实验)
7. [论文工作流](#论文工作流)
8. [API 配置](#api-配置)
9. [框架管理](#框架管理)
10. [多人协作](#多人协作)
11. [故障排查](#故障排查)

---

## 概念

### 框架 vs 项目

|      | 框架 (Framework)                            | 科研项目 (Project)         |
| ---- | ------------------------------------------- | -------------------------- |
| 内容 | skills、tools、templates、deploy            | code、data、paper、results |
| 位置 | `/opt/aris-framework` 或 `~/aris-framework` | 任意位置，每个研究方向一个 |
| 更新 | `git pull` 或 `/framework-update`           | 用户自行管理               |
| 共享 | 所有项目共用一份                            | 每人/每方向独立            |

框架通过 symlink 安装到项目中（`.claude/skills/` → 框架 `skills/`）。

### project.yaml

每个科研项目的核心配置文件，由 `/init-research` 生成：

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
    path: "/data/zhangsan/aris/my-detection"
    conda_env: "aris"
    gpus: [0, 2]

framework:
  path: "/opt/aris-framework"
  repo: "https://github.com/your-org/aris-framework.git"

sync_exclude:
  - "outputs/"
  - "wandb/"
  - "*.pth"
  - "__pycache__/"
```

所有 skill 读这个文件获取配置。手动编辑即可，无需特殊工具。

---

## 项目生命周期

### 创建项目

#### Step 1: 建目录 + 安装 ARIS

`install_aris.sh` 是创建项目的**唯一入口**。先装框架，才有 `/` 命令可用。

```bash
# 新项目
mkdir -p ~/projects/my-research
cd ~/projects/my-research
git init
bash ~/aris-framework/tools/install_aris.sh . --aris-repo ~/aris-framework

# 已有项目加装 ARIS（不动已有文件）
cd /path/to/existing-project
bash ~/aris-framework/tools/install_aris.sh . --aris-repo ~/aris-framework
```

安装完成后项目结构：

```
my-research/
├── CLAUDE.md              ← AI 上下文（需编辑：填研究方向、服务器等）
├── .claude/skills/        ← 90+ symlinks → 框架 skills
├── .aris/
│   ├── installed-skills.txt  ← manifest（记录安装了哪些 skill）
│   └── tools              ← symlink → 框架 tools/
└── (你的代码/数据/论文)
```

#### Step 2: 编辑 CLAUDE.md

安装器生成的 CLAUDE.md 是模板，需要填写：

```bash
vim CLAUDE.md
```

必填项：
- 项目名和研究方向
- 服务器 SSH 别名、路径、conda 环境、可用 GPU

可选项：
- Pipeline Status（使用三边架构时）
- Experiment Chain Contract（使用实验 skill 时）

#### Step 3: 进入 Claude Code 开始工作

```bash
cd ~/projects/my-research
claude
```

进入后可用 `/init-research` 补充生成 `project.yaml`、标准目录结构等（可选，不是必须）：

```
/init-research my-project --direction "研究方向" --server gpu-server-1
```

#### 项目放哪？

框架不限制位置。推荐：

```
~/projects/                    # 或 /workspace/user/
├── aris-framework/            # 框架本体（git clone 一次）
├── exp-detection/             # 科研项目 1
├── exp-segmentation/          # 科研项目 2
└── paper-rebuttal/            # 科研项目 3
```

**关键点：**

- 框架只需一份，所有项目通过 symlink 共享
- 项目之间完全独立（各自 git repo、各自 CLAUDE.md）
- 框架 `git pull` 后，所有项目的 skill 内容自动更新（symlink）
- 新增 skill 需重跑 `install_aris.sh --reconcile` 补链接

### 日常开发

```
# 保存进度
/sync push --message "完成 backbone 实现"

# 部署到 GPU 服务器
/sync deploy --server gpu-server-1

# 拉取最新（多人协作时）
/sync pull

# 查看状态
/sync status
```

### 更新框架

```
/framework-update          # 正常更新（ff-only）
/framework-update --force  # 强制覆盖本地修改
/framework-update --dry-run  # 只看不动
```

---

## 三边架构使用

### 启动方式

打开三个终端窗口，都 `cd` 到同一个项目目录：

**窗口 1 — Leader（Claude Code）**
```bash
claude
# 输入：/leader "研究方向"
```

**窗口 2 — Executor（Claude Code）**
```bash
claude
# 等待 Leader 分发任务，按指示执行
```

**窗口 3 — Reviewer（Codex CLI）**
```bash
codex
# 等待代码审查/实验审计请求
```

### 角色职责

**Leader 只做三件事：读、判、派**
- 读：读取文件、实验结果、审查报告
- 判：决定下一步、是否止损、claim 是否成立
- 派：将任务写入文件，通知 Executor/Reviewer

**Leader 绝对不做：**
- 写代码、画图、跑命令
- 替 Executor 干活（即使 Executor 遇到权限问题）
- 遇到问题自己解决 → 应报告给人

**Executor 做：**
- 代码实现、实验部署、论文撰写
- 完成后产出文件，等待 Reviewer 审查

**Reviewer 做：**
- 独立审查代码/实验/claim
- 只看原始文件，不看 Executor 的总结

### Agent 约束

#### 禁止 tail 轮询

**严禁**用 `Bash(tail -f ...)` 或重复 `Bash(tail ...)` 轮询实验进度。代价：800+ 次无意义 API 调用。

正确做法：
- 远程实验 → `ssh server "screen -dmS exp bash -c 'cmd > log.txt 2>&1'"` 启动，用 `/monitor-experiment` 一次性收集
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

| 角色 | 模型 | 原因 |
|------|------|------|
| Leader | Opus | 决策质量优先 |
| Executor | Sonnet | 量大省 70% |
| Reviewer | GPT-5.5 | 跨模型独立性 |
- 输出审查报告（pass/fail + 具体问题）

### 文件协作

三个窗口在同一目录工作，通过文件通信：
- Leader 产出：`refine-logs/EXPERIMENT_PLAN.md`、`PIPELINE_STATE.json`
- Executor 产出：`code/`、`paper/`、实验结果
- Reviewer 产出：审查报告（JSON + Markdown）

产出后在 `MANIFEST.md` 登记。

---

## Skill 详解

### 研究发现类

#### `/idea-discovery`
AI 驱动的创新点发现。读取领域文献，找 gap，生成可验证的 idea。

```
/idea-discovery "增量目标检测" --sources all
```

输出：`idea-stage/IDEAS.md`

#### `/research-lit`
多源文献综述。支持 Semantic Scholar、Gemini、OpenAlex。

```
/research-lit "few-shot class-incremental learning" --sources all,gemini
```

#### `/novelty-check`
验证 idea 是否已有人做过。

```
/novelty-check "用频域特征做增量学习的原型对齐"
```

### 实验类

#### `/experiment-plan`
制定严格的实验计划，包含：
- Expectation Declaration（预期声明）
- Execution Spec（执行规格：variants / metrics / seeds）
- Data Flow Summary（数据流）
- Delta Assertion（对照差异断言）

```
/experiment-plan
```

输出：`refine-logs/EXPERIMENT_PLAN.md`

#### `/experiment-bridge`
将实验计划转化为可执行代码。

```
/experiment-bridge
```

读取 `EXPERIMENT_PLAN.md`，产出代码到 `code/`。

#### `/experiment-audit`
独立审计实验诚实度。检查：
- 是否有 fake GT
- 是否有 score normalization fraud
- 是否有 phantom results
- 评估类型是否与声明一致

```
/experiment-audit
```

#### `/run-experiment`
远程执行实验。读 `project.yaml` 的 servers 配置。

```
/run-experiment --server gpu-server-1 --script code/train.py
```

#### `/monitor-experiment`
监控正在运行的实验。

```
/monitor-experiment --server gpu-server-1
```

### 论文类

#### `/paper-writing`
完整论文撰写 pipeline（6+ phases）。

```
/paper-writing --effort balanced --assurance submission
```

effort 级别：`lite` / `balanced` / `max` / `beast`
assurance 级别：`draft` / `submission`（submission 强制跑审计）

#### `/auto-paper-improvement-loop`
自动迭代改进论文。每轮：AI 审稿 → 找问题 → 修改 → 再审。

```
/auto-paper-improvement-loop "paper/" --max-rounds 3
```

#### `/rebuttal`
审稿回复。读取审稿意见，生成结构化回复。

```
/rebuttal "paper/ + reviews" --venue ICML --character-limit 5000
```

输出：`PASTE_READY.txt`（直接粘贴）+ `REBUTTAL_DRAFT_rich.md`

#### `/paper-slides` / `/paper-poster` / `/paper-talk`
演示材料生成。

```
/paper-slides "paper/"      # Beamer + PPTX + speaker notes
/paper-poster "paper/"      # A0 poster
/paper-talk "paper/"        # 完整演讲 pipeline
```

### 质量保证类

#### `/proof-checker`
数学证明验证。

```
/proof-checker "paper/sections/theory.tex"
```

#### `/citation-audit`
引用完整性审计。检查悬空引用、未引用 bib 条目。

```
/citation-audit "paper/" --uncited
```

#### `/kill-argument`
对抗性审查：模拟最严厉的 area chair 写拒稿意见，再独立判定是否已在论文中回应。

```
/kill-argument "paper/"
```

---

## 代码同步

### `/sync push` — 保存并上传

```
/sync push                          # 自动生成 commit message
/sync push --message "实现 backbone"  # 指定 message
```

流程：`git add -A` → `git commit` → `git push`

如果没配 remote，只做本地 commit。

### `/sync pull` — 拉取最新

```
/sync pull
```

流程：自动 stash → `git pull --rebase` → pop stash

### `/sync deploy` — 部署到服务器

```
/sync deploy                    # 部署到所有配置的服务器
/sync deploy --server gpu-server-1   # 只部署到指定服务器
```

通过 rsync 同步，自动排除 `sync_exclude` 中的文件。

### `/sync status` — 查看状态

```
/sync status
```

显示：本地修改数、与 remote 的差异、各服务器同步状态。

### 独立脚本（不依赖 Claude Code）

```bash
bash tools/sync.sh push --message "msg"
bash tools/sync.sh pull
bash tools/sync.sh deploy --server gpu-server-1
bash tools/sync.sh status
```

---

## 远程实验

### 配置服务器

编辑 `project.yaml`：

```yaml
servers:
  - name: "gpu-server-1"
    host: "gpu-server-1"             # ~/.ssh/config 中的别名
    path: "/data/user/aris/project"
    conda_env: "aris"
    gpus: [0, 2]

  - name: "gpu-server-2"
    host: "gpu-server-2"
    path: "/workspace/user/aris/project"
    conda_env: "torch"
    gpus: [2]
```

### SSH 配置

确保 `~/.ssh/config` 有对应条目：

```
Host gpu-server-1
    HostName 192.168.1.200        # 替换为实际 IP
    User your_username             # 替换为实际用户名
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

### 工作流

```
# 1. 本地开发完成
/sync push

# 2. 部署到服务器
/sync deploy --server gpu-server-1

# 3. 远程执行
/run-experiment --server gpu-server-1 --script code/train.py

# 4. 监控
/monitor-experiment --server gpu-server-1

# 5. 结果拉回
# （结果文件通过 rsync 或手动 scp）
```

---

## 论文工作流

### 完整流程（三边架构）

```
1. /leader "研究方向"
   ├── Phase 1: /idea-discovery → 创新点
   ├── Phase 2: /experiment-plan → 实验计划
   ├── Phase 3: /experiment-bridge → 代码实现
   │            /run-experiment → 远程执行
   │            /experiment-audit → 诚实度审计
   ├── Phase 4: /result-to-claim → 结果→claim
   ├── Phase 5: /paper-writing → 论文撰写
   │            /auto-paper-improvement-loop → 迭代改进
   └── Phase 6: /citation-audit + /proof-checker → 最终审计
```

### 简化流程（单窗口）

```
/research-pipeline "研究方向"
```

一条命令走完全流程。适合快速验证。

### 投稿后

```
/rebuttal "paper/ + reviews" --venue ICML    # 回复审稿
/resubmit-pipeline --from ICML --to NeurIPS  # 改投
/paper-slides "paper/"                        # 做 PPT
```

---

## API 配置

### CC-Switch — API Provider 统一管理（推荐）

容器内已预装 [cc-switch-cli](https://github.com/SaladDay/cc-switch-cli)，统一管理 Claude Code / Codex / Gemini 等多个 CLI 的 API 配置。

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

# 切换（一键写入 Claude Code / Codex 配置文件）
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

#### 组管理员预配

在 `entrypoint.sh` 或容器启动后，可批量预配组统一 provider：

```bash
cc-switch provider add --name "组统一-中转站" \
    --base-url "$ANTHROPIC_BASE_URL" \
    --api-key "$ANTHROPIC_API_KEY" \
    --model "claude-sonnet-4-20250514"
cc-switch provider switch 1
```

用户想用自己的 key 时，`cc-switch provider add` 加一个再 switch 即可。

#### Win11 用户（GUI 版）

本地电脑装 [CC-Switch GUI](https://github.com/farion1231/cc-switch)（桌面版），管理本地的 Claude Code / Codex 配置。

> ⚠️ GUI 版不支持远程配置服务器。Win11 管 Win11，服务器 CLI 管服务器，各自独立。

### 模型分层策略

三边架构使用不同模型，平衡成本与质量：

| 角色 | 主力 (Coding Plan) | 备用 (DeepSeek) | 说明 |
|------|-------------------|----------------|------|
| Leader | Claude Opus | DeepSeek V4 Pro | 决策质量优先 |
| Executor Agent | Claude Sonnet | DeepSeek V4 Pro | 量大，用便宜模型 |
| Reviewer | GPT-5.5 (Codex MCP) | GPT-5.5 | 跨模型审查，不变 |

Leader 派 Agent 时自动指定 `model: "sonnet"`，无需手动配置。

#### 预配 Provider（cc-switch）

容器启动后建议配置三个 provider：

```bash
# 1. Coding Plan（买了 Plan 后用）
cc-switch provider add --name "plan" \
    --api-key "$ANTHROPIC_API_KEY" \
    --model "claude-sonnet-4-20250514"
# 不配 base_url = 走官方

# 2. 中转站（过渡期主力）
cc-switch provider add --name "中转站" \
    --base-url "https://your-proxy.com/v1" \
    --api-key "sk-proxy-xxx" \
    --model "claude-sonnet-4-20250514"

# 3. DeepSeek 备用（Anthropic 挂了切这个）
cc-switch provider add --name "deepseek" \
    --base-url "https://api.deepseek.com/anthropic" \
    --api-key "sk-deepseek-xxx" \
    --model "deepseek-v4-pro"
# 或走中转站转发：
# cc-switch provider add --name "deepseek-via-proxy" \
#     --base-url "https://your-proxy.com/v1" \
#     --api-key "sk-proxy-xxx" \
#     --model "deepseek-v4-pro"
```

切换：
```bash
cc-switch provider switch 1    # 切 Coding Plan
cc-switch provider switch 2    # 切中转站
cc-switch provider switch 3    # 切 DeepSeek 备用
```

> ⚠️ 切换是**会话级**的 — 整个 Claude Code 都切到该 provider。不支持 Agent 级别单独切。Anthropic 恢复后记得切回来。

### 组统一配置（.env / 环境变量）

```env
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_BASE_URL=                    # 留空=官方，填中转站 URL
OPENAI_API_KEY=sk-xxx                  # Codex Reviewer 用
```

### 个人覆盖（容器内）

#### Claude Code

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

#### Codex CLI

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

### 代理/VPN

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

### 免费方案

- ModelScope：见 `docs/MODELSCOPE_GUIDE.md`
- MiniMax + GLM：见 `docs/MiniMax-GLM-Configuration.md`

---

## 框架管理

### 更新框架

```
/framework-update
```

等价于：
```bash
cd /path/to/aris-framework
git pull --ff-only
cd /path/to/my-project
bash /path/to/aris-framework/tools/install_aris.sh . --aris-repo /path/to/aris-framework --reconcile
```

### 手动安装/重装 Skills

```bash
bash tools/install_aris.sh /path/to/project --aris-repo /path/to/framework
```

选项：
- `--reconcile`：对比已安装和上游，添加新 skill、删除已移除 skill
- `--adopt-existing`：接管已存在的同名目录
- `--replace-link`：覆盖已存在的 symlink

### Codex Skills 安装

```bash
bash tools/install_aris_codex.sh /path/to/project --aris-repo /path/to/framework
```

---

## 多人协作

### Git 工作流

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

### 科研项目协作

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

### Docker 多人环境

每人一个容器，共享资源：

```
┌─────────────────────────────────────────┐
│ Host Server                              │
├──────────┬──────────┬───────────────────┤
│ aris-    │ aris-    │ aris-gitea        │
│ zhangsan │ lisi     │ (git server)      │
├──────────┴──────────┴───────────────────┤
│ Shared Volumes:                          │
│  /data/shared/datasets (ro)             │
│  /data/shared/pretrained (rw)           │
│  /opt/aris-framework (ro)               │
└─────────────────────────────────────────┘
```

添加新用户：编辑 `.env` + `docker-compose.yaml`，`docker compose up -d`。

---

## 故障排查

### Claude Code 相关

| 问题                                | 解决                                              |
| ----------------------------------- | ------------------------------------------------- |
| Skill 不出现在 `/` 补全中           | 检查 `.claude/skills/` symlink 是否存在且指向正确 |
| `/framework-update` 报 "有本地修改" | 用 `--force` 或手动 `cd framework && git stash`   |
| API 403/401                         | 检查 key 是否过期，base_url 是否正确              |
| "context window exceeded"           | 正常，Claude Code 会自动压缩上下文继续            |

### Git/Sync 相关

| 问题                        | 解决                                     |
| --------------------------- | ---------------------------------------- |
| `/sync push` 报 "no remote" | 编辑 `project.yaml` 的 `git.remote` 字段 |
| push 被拒绝                 | `git pull --rebase` 后重试               |
| stash 冲突                  | `git stash show -p` 查看冲突，手动解决   |
| deploy rsync 超时           | 检查 SSH config，确认 `ssh HOST` 能连通  |

### Docker 相关

| 问题                     | 解决                                           |
| ------------------------ | ---------------------------------------------- |
| `docker compose up` 失败 | Docker 版本需 24.0+（`docker compose` 子命令） |
| Gitea 502                | 首次启动慢，等 30s 重试                        |
| 容器内 `git push` 失败   | 检查 GITEA_TOKEN 环境变量                      |
| SSH key 不可用           | 检查 volume mount，`ls ~/.ssh/`                |

### GPU 服务器相关

| 问题               | 解决                                                         |
| ------------------ | ------------------------------------------------------------ |
| CUDA not available | 检查 `CUDA_VISIBLE_DEVICES`、`LD_LIBRARY_PATH`               |
| PyTorch 版本不匹配 | 用 `--index-url https://download.pytorch.org/whl/cu118` 重装 |
| OOM (显存不足)     | 减小 batch size，或换卡                                      |
| rsync 不存在       | 用 `tar czf -                                                | ssh tar xzf -` 替代 |

### Codex/Reviewer 相关

| 问题              | 解决                                    |
| ----------------- | --------------------------------------- |
| MCP 连接失败      | 检查 `.mcp.json` 路径、Python 路径      |
| Codex 返回空      | 检查 `~/.codex/config.toml` 的 base_url |
| "model not found" | 确认 provider 支持指定模型              |

---

## 附录：完整 Skill 列表

→ 见 [docs/SKILL_CATALOG.md](SKILL_CATALOG.md)（英文）| [docs/SKILL_CATALOG_CN.md](SKILL_CATALOG_CN.md)（中文）

当前 skill 数量和分类以自动生成目录为准。运行 `python3 tools/generate_skill_catalog.py` 更新。
