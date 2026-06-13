---
name: init-research
description: "一键创建新科研项目。自动: mkdir → git init → install skills → CLAUDE.md → project.yaml → push to git remote。"
argument-hint: "项目名 [--size full|small] [--server SSH别名] [--remote GIT_URL] [--direction 研究方向]"
allowed-tools: Bash(*), Read, Write, Edit, Agent
caller: leader
platform: both
status: needs-adaptation
produces:
  - project.yaml
  - CLAUDE.md
  - AGENTS.md
examples:
  - "/init-research exp0604 --direction few-shot detection"
  - "创建新项目 freq-proto"
  - "init research project for robotics"
---

# /init-research — 创建新科研项目

## 解析参数

从 `$ARGUMENTS` 提取:

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 第一个词 | **必填** | 项目名（slug: 字母数字中划线） |
| `--size` | `full` | `full`=完整 pipeline, `small`=快速验证 |
| `--server` | 无 | SSH 别名，可多次指定 |
| `--remote` | 无 | Git remote URL（Gitea/GitHub） |
| `--direction` | 无 | 研究方向描述（中文OK） |

如果用户只给了一个词（如 `/init-research ntn-scheduling`），用 AskUserQuestion 问 `--direction`。其余可选。

## 定位路径

```
FRAMEWORK_DIR = 找到当前 ARIS 框架 repo 根目录（含 skills/ 和 tools/install_aris.sh 的目录）
PROJECTS_DIR  = FRAMEWORK_DIR 的上一级（和框架平级）
                如果在容器内 /aris/framework，则 PROJECTS_DIR=/aris/projects
PROJECT_DIR   = PROJECTS_DIR/{项目名}
```

检查: PROJECT_DIR 不能已存在。已存在 → 报错退出。

## Step 1: 创建目录结构

### size=full

```bash
mkdir -p {PROJECT_DIR}/{code,refine-logs,idea-stage,paper,discussions,figures,outputs,data}
```

### size=small

```bash
mkdir -p {PROJECT_DIR}/{code,data,outputs}
```

## Step 2: Git 初始化

```bash
cd {PROJECT_DIR}
git init
```

写 `.gitignore`:

```
# Outputs & models
outputs/
wandb/
*.pth
*.pt
*.onnx
*.tar.gz

# Data (too large for git)
datasets/
data/*.tar*
data/*.zip

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/

# Editor
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# ARIS local
.aris/
.claude/
.agents/
```

## Step 3: 安装 ARIS skills

```bash
bash {FRAMEWORK_DIR}/tools/install_aris.sh {PROJECT_DIR} --aris-repo {FRAMEWORK_DIR}
```

如果 `install_aris_codex.sh` 也存在，同时跑:
```bash
bash {FRAMEWORK_DIR}/tools/install_aris_codex.sh {PROJECT_DIR} --aris-repo {FRAMEWORK_DIR}
```

## Step 4: 生成 project.yaml

读 `{FRAMEWORK_DIR}/templates/project.yaml.tmpl`，替换占位符:

| 占位符 | 值 |
|--------|-----|
| `{PROJECT_NAME}` | 项目名 |
| `{RESEARCH_DIRECTION}` | --direction 值 |
| `{DATE}` | 当前日期 |
| `{USER}` | `whoami` |

servers 段: 如果 --server 指定了，填入。否则留空注释。
git.remote: 如果 --remote 指定了，填入。

保存到 `{PROJECT_DIR}/project.yaml`。

## Step 5: 生成 CLAUDE.md

### size=full

读 `{FRAMEWORK_DIR}/templates/CLAUDE_MD_TEMPLATE.md`，替换 `{project-name}` 等占位符。保存到 `{PROJECT_DIR}/CLAUDE.md`。

### size=small

生成精简版:

```markdown
# Project: {项目名}

## 目标

{研究方向}

## Quick Reference

- 代码: `code/`
- 数据: `data/`
- 输出: `outputs/`
```

## Step 6: 生成 .mcp.json

```json
{
  "mcpServers": {
    "codex": {
      "command": "python3",
      "args": ["{FRAMEWORK_DIR}/mcp-servers/codex-review/server.py"]
    }
  }
}
```

## Step 7: Git 首次提交

```bash
cd {PROJECT_DIR}
git add -A
git commit -m "init: {项目名} ({研究方向})"
```

如果 --remote 指定了:
```bash
git remote add origin {REMOTE_URL}
git push -u origin main
```

## Step 8: 输出摘要

```
✅ 项目已创建: {PROJECT_DIR}

  结构: {full|small}
  方向: {研究方向}
  Git:  {local only | remote URL}
  服务器: {列表 | 无}

下一步:
  cd {PROJECT_DIR}
  /leader "{研究方向}"     ← 启动三边 pipeline (full only)
```
