---
name: sync
description: "一键同步科研项目：封装 git add/commit/push/pull + 远程部署。用户不需要懂 git。"
argument-hint: "[push|pull|deploy|status] [--server NAME] [--message 'commit msg']"
allowed-tools: Bash(*), Read, Write, Edit
---

# /sync — 科研项目同步

读 `project.yaml` 获取 git remote 和 server 列表。

## 子命令

| 命令 | 作用 |
|------|------|
| `/sync` 或 `/sync push` | 保存并上传：git add → commit → push |
| `/sync pull` | 从 remote 拉最新代码 |
| `/sync deploy` | 把代码 rsync 到 GPU 服务器 |
| `/sync deploy --server NAME` | 指定某台服务器 |
| `/sync status` | 显示 git status + remote 状态 + 服务器同步状态 |

## 前置检查

1. 确认当前目录有 `project.yaml`。没有 → 报错 "不在 ARIS 项目目录内，先 /init-research"
2. 读 `project.yaml` 获取:
   - `git.remote` — push/pull 目标
   - `git.auto_commit` — 是否自动 commit
   - `servers[]` — 部署目标
   - `sync_exclude[]` — 排除列表

## `/sync push` 流程

```bash
cd {PROJECT_DIR}

# 1. 检查 dirty
STATUS=$(git status --porcelain)
if [ -z "$STATUS" ]; then
    echo "Nothing to sync. Already up to date."
    exit 0
fi

# 2. Auto commit
git add -A
MSG="${用户指定 --message 或自动生成}"
# 自动消息格式: "sync: YYYY-MM-DD HH:mm 简要描述改了什么"
# 通过 git diff --stat 生成描述
git commit -m "$MSG"

# 3. Push (如果 remote 配了)
if [ -n "$(git remote)" ]; then
    git push origin $(git branch --show-current)
    echo "✅ 已推送到 remote"
else
    echo "✅ 已本地提交（无 remote 配置）"
fi
```

### 自动生成 commit message

读 `git diff --cached --stat`，生成格式:

```
sync: 修改 models/detector.py, 新增 configs/exp3.yaml (2 files)
```

不需要详细描述，一行够了。

## `/sync pull` 流程

```bash
cd {PROJECT_DIR}

# 1. Stash local changes
STASHED=false
if [ -n "$(git status --porcelain)" ]; then
    git stash push -m "auto-stash before pull $(date +%H:%M)"
    STASHED=true
fi

# 2. Pull
git pull origin $(git branch --show-current) --rebase

# 3. Pop stash
if [ "$STASHED" = true ]; then
    git stash pop || echo "⚠️ Stash 冲突，需手动解决: git stash show -p"
fi

echo "✅ 已拉取最新代码"
```

## `/sync deploy` 流程

对 `project.yaml` 中每个 server（或 --server 指定的）:

```bash
SERVER_HOST={server.host}
SERVER_PATH={server.path}
EXCLUDES=$(从 project.yaml sync_exclude 生成 --exclude 参数)

# 1. 确保远程目录存在
ssh $SERVER_HOST "mkdir -p $SERVER_PATH"

# 2. Rsync
rsync -avz --delete \
    $EXCLUDES \
    --exclude='.git/' \
    ./ ${SERVER_HOST}:${SERVER_PATH}/

echo "✅ 已部署到 $SERVER_HOST:$SERVER_PATH"
```

## `/sync status` 流程

输出格式:

```
📂 项目: ntn-scheduling
🌿 分支: main
📝 本地状态: 3 files modified, 1 untracked

🔗 Remote: http://gitea:3000/zhangsan/ntn-scheduling.git
   本地 vs remote: 2 commits ahead, 0 behind

🖥️ 服务器:
   4090x4 (4090x4-ai-original-22:/data/.../ntn-scheduling)
     最后同步: 2026-05-26 14:00
     状态: 本地有更新未部署
```

## 首次配置 remote

如果用户跑 `/sync push` 但 `project.yaml` 里 `git.remote` 为空:

提示:
```
未配置 git remote。选择:
1. 推送到 Gitea (http://gitea:3000)
2. 推送到 GitHub
3. 仅本地保存（不推送）
```

如果选 1，自动:
```bash
# 用 Gitea API 创建 repo
curl -X POST "http://gitea:3000/api/v1/user/repos" \
    -H "Authorization: token ${GITEA_TOKEN}" \
    -d '{"name": "{PROJECT_NAME}", "private": true}'

git remote add origin http://gitea:3000/{USER}/{PROJECT_NAME}.git
git push -u origin main

# 更新 project.yaml
```

如果选 2，提示用户输入 GitHub repo URL。
