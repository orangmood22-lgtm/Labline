---
name: framework-update
description: "一键更新 ARIS 框架：git pull + 重建 symlinks。用户不需要懂 git。"
argument-hint: "[--force] [--dry-run]"
allowed-tools: Bash(*), Read
---

# /framework-update — 更新 ARIS 框架

## 流程

### Step 1: 定位框架

```bash
# 优先读 project.yaml
FRAMEWORK_DIR=$(python3 -c "
import yaml
with open('project.yaml') as f:
    print(yaml.safe_load(f).get('framework',{}).get('path',''))
" 2>/dev/null)

# 回退: 找 .aris/tools symlink 指向
if [ -z "$FRAMEWORK_DIR" ] || [ ! -d "$FRAMEWORK_DIR" ]; then
    FRAMEWORK_DIR=$(readlink -f .aris/tools/.. 2>/dev/null)
fi

# 再回退: 容器默认路径
if [ -z "$FRAMEWORK_DIR" ]; then
    FRAMEWORK_DIR="/aris/framework"
fi
```

检查: `$FRAMEWORK_DIR/.git` 存在。不存在 → 报错。

### Step 2: Git pull

```bash
cd $FRAMEWORK_DIR

# 保存当前版本
OLD_HEAD=$(git rev-parse HEAD)

# Pull
git fetch origin
git pull --ff-only origin $(git branch --show-current)

NEW_HEAD=$(git rev-parse HEAD)
```

如果 `--ff-only` 失败（有本地修改）:
- `--force` → `git reset --hard origin/$(branch)`
- 否则 → 报错 "框架有本地修改，用 --force 覆盖或手动解决"

### Step 3: 显示更新内容

```bash
if [ "$OLD_HEAD" != "$NEW_HEAD" ]; then
    echo "📦 框架已更新:"
    git log --oneline ${OLD_HEAD}..${NEW_HEAD}

    # 显示新增/删除 skills
    CHANGED_SKILLS=$(git diff --name-only ${OLD_HEAD}..${NEW_HEAD} -- skills/ | sed 's|skills/\([^/]*\)/.*|\1|' | sort -u)
    echo ""
    echo "🔧 变更的 skills:"
    echo "$CHANGED_SKILLS"
else
    echo "✅ 框架已是最新版本。"
fi
```

### Step 4: 重建 symlinks

如果有更新，对当前项目重新跑 install:

```bash
cd $PROJECT_DIR
bash $FRAMEWORK_DIR/tools/install_aris.sh $PROJECT_DIR --aris-repo $FRAMEWORK_DIR --reconcile
```

如果 Codex 安装器也存在:
```bash
bash $FRAMEWORK_DIR/tools/install_aris_codex.sh $PROJECT_DIR --aris-repo $FRAMEWORK_DIR 2>/dev/null || true
```

### Step 4.5: 重新生成 Skill Catalog

```bash
python3 $FRAMEWORK_DIR/tools/generate_skill_catalog.py
```

### Step 5: 输出摘要

```
✅ ARIS 框架已更新

  版本: abc1234 → def5678
  新增 skills: paper-illustration-image2, kill-argument
  更新 skills: leader, sync, init-research
  删除 skills: (none)

  当前项目 symlinks 已刷新。
```

如果 `--dry-run`:
```
🔍 Dry run — 不会实际修改

  当前版本: abc1234
  远程最新: def5678
  待更新 commits: 5
  变更 skills: leader, sync
```
