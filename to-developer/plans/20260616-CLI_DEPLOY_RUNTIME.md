# ARIS CLI 与部署运行时机制说明

> 创建时间: 2026-06-16
> 适用对象: ARIS framework 开发者、部署维护者、release reviewer
> 相关模块: `tools`, `deploy`, `templates`, `docs`, `tests`

本文档说明当前 ARIS CLI 与容器部署运行时的内部机制。用户侧命令和操作步骤以 `QUICK_START.md`、`docs/OPERATIONS_GUIDE.md`、`deploy/DEPLOY_GUIDE.md` 为准；本文只解释实现边界、状态文件、调用链和维护约束。

## 设计目标

ARIS 当前 CLI/部署层解决四个问题：

1. 新用户能用一条稳定入口创建或接入项目，不需要知道安装脚本细节。
2. 每个用户拥有自己的 framework copy，避免组内共享 framework 导致强制升级。
3. framework 更新能同步已登记项目，但必须显式由用户触发。
4. 容器和 tmux/shell 能提醒用户有新 framework，但不能静默更新。

核心原则：

- `aris project ...` 管项目。
- `aris framework ...` 管用户自己的 framework copy。
- 自动行为只允许检查和提示，不允许 pull/reset/改项目。
- 用户 workspace 状态不写进 framework repo。
- Codex 是默认入口，Claude Code 只作为兼容接入。

## 运行时拓扑

托管部署中，管理员指定一个 `ARIS_ROOT`，每个用户一个 workspace：

```text
[ARIS_ROOT]/
├── users/<user>/
│   ├── framework/   # 用户自己的 ARIS checkout
│   ├── projects/    # 用户项目工作区
│   └── .aris/       # 用户级 ARIS 非版本化状态
└── shared/
    ├── datasets/
    ├── pretrained/
    └── downloads/
```

容器内固定挂载为：

```text
/aris/framework
/aris/projects
/aris/.aris
/aris/shared/datasets
/aris/shared/pretrained
/aris/shared/downloads
```

开发者不要把 `/aris/...` 误认为宿主机路径；它是容器内 ABI。宿主机路径由 `.env` 中的 `USERn_FRAMEWORK_PATH`、`USERn_PROJECTS_PATH`、`USERn_STATE_PATH`、`DATASETS_PATH` 等决定。

## CLI 命令边界

当前公共入口是 `tools/aris`：

```text
aris project init PATH --direction "..."
aris project doctor [PATH]
aris project update [PATH]
aris project detach [PATH]
aris project --version

aris framework --version
aris framework check-update [--if-stale DURATION] [--notify] [--no-fetch]
aris framework update [--no-project-sync]
aris framework rollback [--no-project-sync]
```

旧短命令 `aris init`、`aris update`、`aris doctor`、`aris detach` 不支持。当前没有老用户，故没有兼容层；测试会锁住这一点。

## 路径发现机制

`tools/aris` 的 framework 解析顺序：

1. 显式参数 `--aris-repo`。
2. `ARIS_WORKSPACE/framework`，如果 `ARIS_WORKSPACE` 存在且该目录存在。
3. 当前 CLI 所在 repo，即 `tools/aris` 的上级目录。

workspace 解析顺序：

1. 环境变量 `ARIS_WORKSPACE`。
2. 如果 CLI 位于 `.../framework/tools/aris`，则 workspace 是 `.../framework` 的父目录。
3. 如果 `/aris/framework` 或 `/aris/projects` 存在，则 workspace 是 `/aris`。

需要 workspace 的命令包括 project registry、framework rollback history、update status。无法发现 workspace 时，命令应明确失败，避免把用户级状态写进 framework repo。

## 项目初始化机制

`aris project init PATH --direction "..."`

执行模型：

1. 创建或选择 `PATH`。
2. 创建标准项目目录。
3. 写 `.gitignore`，避免 outputs、模型权重、`.aris/`、`.agents/`、`.claude/` 入库。
4. 如果没有 `.git/`，执行 `git init`。
5. 调用底层安装器：
   - `tools/install_aris.sh` 写 Claude Code 兼容接入。
   - `tools/install_aris_codex.sh` 写 Codex 接入。
6. 从 templates 写入：
   - `project.yaml`
   - `AGENTS.md`
   - `CLAUDE.md`
7. 写项目级 manifest：
   - `<project>/.aris/manifest.json`
8. 将项目路径登记到用户 workspace registry。
9. 如果项目没有历史 commit 且用户未传 `--no-commit`，创建初始 commit。

半路接入已有项目时，已有文件和 git 历史必须保留。`copy_text()` 对已存在的目标文件不覆盖，这是保护已有项目的关键行为。

## Project Registry

位置：

```text
<workspace>/.aris/project-registry.json
```

schema:

```json
{
  "schema_version": 1,
  "projects": [
    "/aris/projects/demo"
  ]
}
```

职责：

- `project init` 注册项目。
- `project update` 注册或刷新项目接入。
- `project detach` 从 registry 移除项目。
- `framework update` / `framework rollback` 默认遍历 registry，同步重建每个项目的 skill links。

registry 是用户 workspace 状态，不属于 framework repo，也不属于任何单个项目 repo。不要把 registry 写进 `project.yaml`，否则会把用户本地路径带入项目版本库。

## Project Detach

`aris project detach [PATH]` 语义是“移除 ARIS 接入但保留项目内容”。

当前 detach 会：

- 调用安装器的 `--uninstall` 删除已记录的 skill links。
- 删除 `.aris/manifest.json`、安装 manifest。
- 从 workspace registry 移除该项目。

detach 不应删除：

- 项目源码。
- 数据。
- 论文。
- git 历史。
- 用户自己写的非 ARIS 文件。

不要恢复 `uninstall` 作为公共词；它容易让新用户以为会删除项目。

## Framework Update

`aris framework update`

执行模型：

1. 记录当前 framework commit 到：

```text
<workspace>/.aris/framework-history/previous
```

2. 在用户自己的 framework copy 中执行：

```bash
git pull --ff-only
```

3. 默认同步 registry 中所有仍存在的项目：

```text
install_clients(project, framework)
```

4. 输出同步项目数量和缺失项目数量。

`--no-project-sync` 只更新 framework，不重建项目接入。

当前 update 允许本地-only 测试 repo 没有 upstream tracking；这是为了测试便利，不代表用户文档应推荐无 remote 的 framework。

## Framework Rollback

`aris framework rollback`

执行模型：

1. 读取 `<workspace>/.aris/framework-history/previous`。
2. 对 framework repo 执行：

```bash
git reset --hard <previous>
```

3. 默认同步 registry 中项目。

风险：

- 当前 rollback 会丢弃 framework repo 未提交改动。
- 这对普通用户通常可接受，因为用户不应在 framework copy 里开发。
- 对 framework 开发者有风险，后续应加 dirty worktree guard。

推荐后续改动：

- rollback 前检查 `git status --porcelain`。
- 如果有本地修改，默认拒绝，并提示手动 stash/commit。
- 提供显式 `--force` 时才允许 reset。

## Framework Update Check

`aris framework check-update`

这是非破坏性检查，只做 fetch/比较，不改变 framework 工作树，不同步项目。

状态判断：

| 条件 | status |
|---|---|
| 本地 commit 等于 upstream commit | `up-to-date` |
| 本地 commit 是 merge-base，upstream 更远 | `update available` |
| upstream commit 是 merge-base，本地更远 | `local ahead` |
| 两边都不是 merge-base | `diverged` |
| 无 upstream | `unknown` |
| fetch 失败 | `check failed` |

状态文件：

```text
<workspace>/.aris/framework-update-status.json
```

关键字段：

```json
{
  "schema_version": 1,
  "last_checked_at": "2026-06-16T00:00:00Z",
  "last_notified_at": "2026-06-16T00:00:00Z",
  "framework": "/aris/framework",
  "local_commit": "...",
  "upstream": "origin/main",
  "upstream_commit": "...",
  "status": "update available",
  "error": ""
}
```

`--if-stale 1d`：

- 如果 `last_checked_at` 距当前时间小于 1 天，复用缓存状态。
- 如果已过期，才执行 git fetch 和比较。

`--notify`：

- 只在 `status == update available` 时输出提醒。
- 如果 `last_notified_at` 距当前时间小于 1 天，不再提醒。
- 当前提醒文本只告诉用户运行 `aris framework update` 和 rollback 命令，不自动执行。

这个节流策略实现“每个用户每天最多提醒一次”。

## 容器 EntryPoint Hook

`deploy/entrypoint.sh` 负责把 CLI 检查接入容器交互环境。

启动时行为：

1. 写 API 配置。
2. 写 proxy 配置。
3. 拷贝 SSH key。
4. 建立 `~/.local/bin/aris -> /aris/framework/tools/aris`。
5. 写 `~/.aris/aris-shell-hook.sh`。
6. 将 hook source 追加到 `~/.bashrc`。
7. 启动时执行一次非阻塞更新提醒路径。

hook 内容核心是：

```bash
aris framework check-update \
  --aris-repo /aris/framework \
  --if-stale "${ARIS_UPDATE_CHECK_INTERVAL:-1d}" \
  --notify
```

触发节点：

- 容器启动。
- 用户进入交互 shell。
- 用户新开 tmux pane/window 后 shell 初始化。

注意：

- hook 入口可以频繁触发。
- CLI 的状态文件保证联网检查和提醒都按天节流。
- entrypoint 不允许 `git pull`。

相关环境变量：

```env
ARIS_AUTO_CHECK_UPDATE=1
ARIS_UPDATE_CHECK_INTERVAL=1d
ARIS_UPDATE_CHECK_TIMEOUT=10s
```

## 部署 Compose 契约

多人部署 compose 必须保持：

```text
USERn_FRAMEWORK_PATH -> /aris/framework
USERn_PROJECTS_PATH  -> /aris/projects
USERn_STATE_PATH     -> /aris/.aris
DATASETS_PATH        -> /aris/shared/datasets:ro
PRETRAINED_PATH      -> /aris/shared/pretrained
DOWNLOADS_PATH       -> /aris/shared/downloads
ARIS_WORKSPACE       -> /aris
```

不要恢复共享 framework named volume，例如：

```text
aris-framework:/aris/framework
```

不要恢复共享项目 volume，例如：

```text
user1-projects:/aris/projects
```

每个用户的 framework copy 是版本隔离边界；每个用户的 `.aris` 是 registry、rollback history、update status 的状态边界。

## 测试契约

关键测试：

- `tests/test_aris_cli.py`
  - project init / doctor / update / detach
  - 已有项目接入不破坏用户文件
  - registry 注册和移除
  - framework update / rollback
  - check-update 非破坏性
  - notify 每天最多一次
  - 旧短命令不支持

- `tests/test_gpu_deploy_contract.py`
  - compose per-user mount
  - env 示例包含 update check 变量
  - entrypoint 不含 `git pull --ff-only`
  - entrypoint 包含 `.bashrc` hook、`--if-stale`、`--notify`
  - cc-switch-cli 预装

修改 CLI 或 deploy 行为时至少运行：

```bash
python -m unittest tests.test_aris_cli tests.test_gpu_deploy_contract tests.test_aris_gpu_doctor
python -m py_compile tools/aris
```

修改开发者文档或 DAG 时还要运行：

```bash
python tools/update_developer_docs.py
python tools/update_developer_docs.py --check-only
python -m pytest tests/test_developer_doc_dag.py tests/test_release_tools.py
```

## 文档同步规则

改 CLI 行为时同步：

- `QUICK_START.md`
- `docs/OPERATIONS_GUIDE.md`
- `README.md`
- `CONTEXT.md`，仅当术语或概念变化
- `to-developer/20260613-DEVELOPMENT_LOG.md`

改部署拓扑或 entrypoint 时同步：

- `deploy/DEPLOY_GUIDE.md`
- `deploy/.env.example`
- `deploy/docker-compose.yaml`
- `docs/OPERATIONS_GUIDE.md` 管理员手册
- `tests/test_gpu_deploy_contract.py`

新增、删除、重命名 `to-developer/**/*.md` 或 `to-developer/**/*.txt` 时同步：

- `to-developer/DOC_DAG.yaml`
- `to-developer/DOC_DAG.mmd`

开发者文档文件名必须带创建日期前缀：

```text
YYYYMMDD-文件名.md
YYYYMMDD-文件名.txt
```

`to-developer/DOC_DAG.yaml` 和 `to-developer/DOC_DAG.mmd` 是工具固定入口，不加日期前缀。

## 已知后续工作

1. 为 `framework rollback` 增加 dirty worktree guard。
2. 考虑 `check-update --dismiss`，允许用户忽略某个 upstream commit。
3. 考虑 `project --version PATH` 支持，当前默认当前目录。
4. 为 `.bashrc` hook 增加幂等 marker 版本号，便于以后升级 hook 内容。
5. 为 `project-registry.json` 增加 project metadata，例如 name、last_seen、auto_sync。
6. 把 CLI 帮助文本补成中文或中英双语，降低新手排错成本。
