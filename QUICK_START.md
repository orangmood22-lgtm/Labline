# ARIS 快速开始

> 5 分钟从零到第一个研究项目。

## 前置条件

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 已安装（`claude` 命令可用）
- Anthropic API Key（官方 / 中转站均可）
- （可选）[Codex CLI](https://github.com/openai/codex) — 用于 Reviewer 角色

## 方式一：个人使用

### 1. 克隆框架

```bash
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git ~/aris-framework
```

### 2. 创建科研项目

```bash
mkdir ~/my-research && cd ~/my-research
git init
```

### 3. 安装 ARIS Skills

```bash
bash ~/aris-framework/tools/install_aris.sh ~/my-research --aris-repo ~/aris-framework
```

安装完成后，项目目录下出现 `.claude/skills/`（symlink 到框架 skill）。

### 4. 启动 Claude Code

```bash
cd ~/my-research
claude
```

### 5. 开始研究

```
# 在 Claude Code 中输入：
/init-research my-project --direction "你的研究方向"

# 或直接启动全自动 pipeline：
/research-pipeline "你的研究方向"
```

---

## 方式二：Docker 多人部署

适合实验室/研究组，每人独立容器。

### 1. 克隆框架

```bash
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
