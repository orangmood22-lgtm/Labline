# ARIS 快速开始

> 5 分钟从零到第一个研究项目。

## 前置条件

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 已安装（`claude` 命令可用）
- Anthropic API Key（官方 / 中转站均可）
- （可选）[Codex CLI](https://github.com/openai/codex) — 用于 Reviewer 角色

## 方式一：个人使用

### 1. 克隆框架（只需一次）

```bash
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git ~/aris-framework
```

### 2. 创建科研项目

```bash
mkdir -p ~/projects/my-research && cd ~/projects/my-research
git init
bash ~/aris-framework/tools/install_aris.sh . --aris-repo ~/aris-framework
```

安装完成后出现：
- `.claude/skills/` — 90+ symlinks → 框架 skills
- `.aris/installed-skills.txt` — manifest
- `CLAUDE.md` — AI 上下文模板（**需编辑**）

### 3. 编辑 CLAUDE.md

```bash
vim CLAUDE.md
```

填入：研究方向、服务器 SSH 别名/路径/GPU、项目约束等。这是 Agent 每次 session 的上下文来源。

### 4. 记录框架版本

安装完成后，建议记录当前框架版本：

```bash
cd ~/aris-framework
git log -1 --format="%H" > .aris/framework-commit.txt
git describe --tags --always > .aris/framework-version.txt 2>/dev/null || echo "no-tag"
```

### 5. 启动 Claude Code

```bash
cd ~/projects/my-research
claude
```

进入后所有 `/` 命令可用。可选运行 `/init-research` 补充生成 project.yaml 和标准目录结构。

### 5. 开始研究

```
/leader "你的研究方向"          # 三边架构全自动
/research-pipeline "你的研究方向"  # 单窗口全流程
/experiment-plan                  # 只做实验计划
```

### 多项目管理

框架只需一份，项目随便放：

```
~/
├── aris-framework/            # 框架（git clone 一次）
└── projects/
    ├── exp-detection/         # 科研项目 1
    ├── exp-segmentation/      # 科研项目 2
    └── paper-rebuttal/        # 科研项目 3
```

- 框架 `git pull` → 所有项目 skill 内容自动更新（symlink）
- 新增 skill → 项目内重跑 `install_aris.sh --reconcile`
- 已有代码目录加装 → 同样 `install_aris.sh .`，不动已有文件

---

## 方式二：Docker 多人部署

适合实验室/研究组，每人独立容器。

### 1. 克隆框架

如果服务器需要代理才能访问 GitHub，先同时设置大小写 proxy；如果 `git clone` 仍失败，再设置 git proxy。完整说明见 [deploy/DEPLOY_GUIDE.md](deploy/DEPLOY_GUIDE.md)。

```bash
# 如需代理，先取消下面四行注释并改成你的代理端口：
# export HTTP_PROXY=http://127.0.0.1:7897
# export HTTPS_PROXY=http://127.0.0.1:7897
# export http_proxy="$HTTP_PROXY"
# export https_proxy="$HTTPS_PROXY"
# 可选：git config --global http.proxy "$HTTP_PROXY"
# 可选：git config --global https.proxy "$HTTPS_PROXY"
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git /opt/aris-framework
cd /opt/aris-framework/deploy
```

### 2. 配置环境

```bash
cp .env.example .env
vim .env
```

必填项：
```env
USER1_NAME=zhangsan
USER1_UID=1001
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx          # Codex Reviewer 用
# 如需代理，同时填写 HTTP_PROXY/HTTPS_PROXY 和 http_proxy/https_proxy
```

### 3. 启动

```bash
docker compose up -d
```

### 4. 进入容器

```bash
docker exec -it aris-zhangsan bash
```

### 5. 创建第一个项目

```bash
# 容器内，Claude Code 已预装
claude

# 输入：
/init-research frequency-detection --direction "基于频域特征的增量目标检测"
```

---

## 常用命令速查

| 命令 | 作用 |
|------|------|
| `/init-research NAME --direction "方向"` | 创建新项目 |
| `/leader "研究方向"` | 启动三边 pipeline |
| `/research-pipeline "方向"` | 全自动研究（单窗口） |
| `/sync push` | 保存并推送代码 |
| `/sync deploy --server NAME` | 部署到 GPU 服务器 |
| `/sync status` | 查看同步状态 |
| `/framework-update` | 更新框架到最新版 |
| `/experiment-plan` | 制定实验计划 |
| `/paper-writing` | 启动论文撰写 |
| `/research-wiki init` | 初始化研究知识库 |

## Agent 约束（重要）

以下规则写入每个项目的 `CLAUDE.md`，Agent 每次 session 自动遵守：

| 规则 | 说明 |
|------|------|
| **禁止 tail 轮询** | 不用 `tail -f` 或循环 `tail` 监控实验。用 `/monitor-experiment` 或 `run_in_background` |
| **Executor 阻塞协议** | Agent 遇阻塞自行尝试 2 种绕过，全失败写 `BLOCKED_REPORT.md`，不卡死不越权 |
| **模型分层** | Leader=Opus, Executor=Sonnet(省70%), Reviewer=GPT-5.5 |

详见 `docs/OPERATIONS_GUIDE.md` → 三边架构使用 → Agent 约束。

## 项目结构（创建后）

```
my-research/
├── project.yaml         # 项目配置（服务器、git remote、同步规则）
├── CLAUDE.md            # AI 上下文（自动生成）
├── code/                # 实验代码
├── data/                # 数据集
├── paper/               # 论文 TeX
├── refine-logs/         # 实验计划、bridge 日志
├── idea-stage/          # 想法探索
├── discussions/         # 进度报告
├── figures/             # 图表
├── outputs/             # 实验输出（gitignore）
└── .claude/skills/      # → 框架 skills（symlink）
```

## 配置 GPU 服务器

编辑 `project.yaml`：

```yaml
servers:
  - name: "4090x4"
    host: "4090x4-ai-original-22"    # SSH 别名
    path: "/data/user/aris/my-research"
    conda_env: "aris"
    gpus: [0, 2]
```

然后：
```
/sync deploy --server 4090x4
```

## 配置 Git Remote

首次 `/sync push` 时会提示选择：
1. 推送到 Gitea（自建 git，Docker 部署自带）
2. 推送到 GitHub
3. 仅本地保存

或手动编辑 `project.yaml`：
```yaml
git:
  remote: "http://gitea:3000/zhangsan/my-research.git"
  branch: "main"
  auto_commit: true
```

## 下一步

- 详细操作 → [docs/OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md)
- Docker 部署细节 → [deploy/DEPLOY_GUIDE.md](deploy/DEPLOY_GUIDE.md)
- 三边架构原理 → [docs/TRIPARTITE_ARCHITECTURE_GUIDE.md](docs/TRIPARTITE_ARCHITECTURE_GUIDE.md)
- 框架更新 → 在项目内运行 `/framework-update`
