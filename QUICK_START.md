# ARIS 快速开始

> 5 分钟从零到第一个研究项目。

## 前置条件

- Codex CLI 已安装（`codex` 命令可用）
- OpenAI API Key 或 OpenAI-compatible provider（用于 Codex 本地 agent）
- （可选）Claude Code + Anthropic API Key；ARIS 保持兼容，但不是默认入口

## 方式一：个人本地使用

### 1. 安装框架

框架安装目录和科研项目目录是分离的。框架放在一个固定位置，项目可以放在任意工作区。

```bash
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git [你的framework位置]
```

如果想把 ARIS 当普通 CLI 用，建议把命令链接到 `PATH`：

```bash
mkdir -p ~/.local/bin
ln -sf [你的framework位置]/tools/aris ~/.local/bin/aris
export PATH="$HOME/.local/bin:$PATH"
```

之后文档里的 `aris ...` 等价于 `bash [你的framework位置]/tools/aris ...`。

### 2. 创建科研项目

```bash
mkdir -p ~/projects/my-research && cd ~/projects/my-research
aris project init . --direction "你的研究方向"
```

安装完成后出现：
- `project.yaml` — 项目元数据和框架版本入口
- `AGENTS.md` — Codex 项目上下文
- `CLAUDE.md` — Claude Code 兼容上下文
- `.agents/skills/` — Codex skills symlinks → 框架 skills
- `.claude/skills/` — Claude Code 兼容 skills symlinks
- `.aris/manifest.json` — CLI 初始化记录
- `code/`、`data/`、`refine-logs/`、`outputs/` 等标准目录

也可以从父目录直接新建项目：

```bash
cd ~/projects
aris project init ./my-research --direction "你的研究方向"
```

已有项目也用同一个命令半路接入 ARIS；现有代码、数据、论文、git 历史会保留：

```bash
cd /path/to/existing-project
aris project init . --direction "你的研究方向"
```

### 3. 检查初始化

```bash
aris project doctor
```

### 4. 启动 Codex

```bash
cd ~/projects/my-research
codex
```

进入后用 `$skill-name` 调用 ARIS skills。Claude Code 用 `/skill-name`。

### 5. 开始研究

```
$leader "你的研究方向"
$experiment-plan                  # 只做实验计划
```

### 多项目管理

框架只需一份，项目随便放，不要求和框架在同一个父目录：

```
[你的framework位置]/           # 框架安装目录

~/projects/                    # 项目工作区 A
├── exp-detection/
└── exp-segmentation/

[你的项目工作区]/               # 项目工作区 B
└── paper-rebuttal/
```

- 框架 `aris framework update` → 更新 framework 并默认同步已登记项目
- 新增 skill → 项目内运行 `aris project update`
- 移除 ARIS 接入但保留项目文件 → `aris project detach`

---

## 方式二：Docker 多人部署

适合实验室/研究组，每人独立容器。

完整说明见 [deploy/DEPLOY_GUIDE.md](deploy/DEPLOY_GUIDE.md)。


---

## 常用命令速查

| 命令 | 作用 |
|------|------|
| `aris project init . --direction "方向"` | 当前目录初始化项目 |
| `aris project init PATH --direction "方向"` | 创建/接入指定目录 |
| `aris project doctor` | 检查项目初始化状态 |
| `aris project update` | 重建项目 ARIS 接入 |
| `aris project detach` | 移除 ARIS 接入，保留项目文件 |
| `aris framework --version` | 查看 framework 版本 |
| `aris framework check-update` | 检查 framework 是否有更新，不改变本地版本 |
| `aris framework update` | 更新 framework 并同步登记项目 |
| `aris framework rollback` | 回退上一次 framework 更新 |
| `$leader "研究方向"` | 启动三边 pipeline |
| `$research-pipeline "方向"` | 全自动研究（单窗口） |
| `$sync push` | 保存并推送代码 |
| `$sync deploy --server NAME` | 部署到 GPU 服务器 |
| `$sync status` | 查看同步状态 |
| `$framework-update` | 更新框架到最新版 |
| `$experiment-plan` | 制定实验计划 |
| `$paper-writing` | 启动论文撰写 |
| `$research-wiki init` | 初始化研究知识库 |

## 项目结构（创建后）

```
my-research/
├── project.yaml         # 项目配置（服务器、git remote、同步规则）
├── AGENTS.md            # Codex 项目上下文（自动生成）
├── CLAUDE.md            # Claude Code 兼容上下文（自动生成）
├── code/                # 实验代码
├── data/                # 数据集
├── paper/               # 论文 TeX
├── refine-logs/         # 实验计划、bridge 日志
├── idea-stage/          # 想法探索
├── discussions/         # 进度报告
├── figures/             # 图表
├── outputs/             # 实验输出（gitignore）
├── .agents/skills/      # Codex → 框架 skills（symlink）
└── .claude/skills/      # Claude Code 兼容 symlink
```

## 配置 GPU 服务器

编辑 `project.yaml`：

```yaml
servers:
  - name: "4090x4"
    host: "4090x4-ai-original-22"    # SSH 别名
    path: "[服务器上的项目位置]/my-research"
    conda_env: "aris"
    gpus: [0, 2]
```

然后：
```
$sync deploy --server 4090x4
```

## 配置 Git Remote

首次 `$sync push` 时会提示选择：
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
- 框架更新 → 在项目内运行 `$framework-update`
