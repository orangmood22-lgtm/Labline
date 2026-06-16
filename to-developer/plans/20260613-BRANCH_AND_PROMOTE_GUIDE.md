# ARIS 分支开发与 Dev -> Stable 合并指南

> 目标：说明两类常见工作流。
>
> 1. 在 `aris-dev` 里开发实验性能力，成熟后 promote 到 stable。
> 2. 在 stable 仓库里开功能/修复分支，验证后合并回主线。

## 0. 当前仓库关系

本机路径：

```text
/root/Projects/aris/Auto-research-in-sleep/aris-dev
/root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
```

服务器 3090x2 路径：

```text
/workspace/Orangmood/ARIS/aris-dev
/workspace/Orangmood/ARIS/aris-framework
```

容器内路径：

```text
/aris/aris-dev       # dev framework
/aris/framework      # stable framework
/aris/projects       # research projects
```

定位：

- `aris-dev`：孵化区，放还没稳定的新 skill、新工具、新模板、新部署方案。
- `aris-orangmood-edition` / `/aris/framework`：stable 区，项目默认依赖这里。
- dev 里的内容不能自动进入 stable，必须经过 promote。
- stable 的修复/功能开发应该开分支，验证后合并回主线分支。

## 1. 什么时候用 dev，什么时候直接改 stable

用 `aris-dev`：

- 新 skill 还在试验。
- 新工具的接口还不确定。
- 新模板/部署方案需要先在真实项目里跑。
- 可能会失败、废弃、重做。

直接在 stable 开分支：

- 修复 stable 已有功能的 bug。
- 修改 installer、deploy、测试、文档这类 stable 已发布能力。
- 已经明确要进入 stable，只是需要隔离开发分支。
- 像 3090x2 部署修复这种“稳定能力硬化”，应走 stable 功能/修复分支。

## 2. dev -> stable promote 流程

### 2.1 在 dev 里开发

进入 dev：

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-dev
tools/git-dev status --short --branch
```

如果在 3090x2 容器里：

```bash
cd /aris/aris-dev
git status --short --branch
```

开发内容按目录放：

```text
skills/<skill-name>/
tools/<tool-name>
templates/<template-name>
deploy/<deploy-file>
docs/<doc-file>
tests/<test-file>
```

不要 promote：

```text
to-developer/
to-developer/discussions/settings*.json
to-developer/discussions/ssh.txt
.codex/
.agents/
.claude/
```

### 2.2 在 dev 里测试

如果是 promote 工具自身：

```bash
python3 tests/test_promote_to_stable.py
```

如果是新 skill 或工具，至少做一次真实项目验证。例如：

```bash
cd /aris/projects/YOUR_PROJECT
bash /aris/framework/tools/install_aris.sh . --dev --quiet --no-doc
```

确认项目能发现 dev 内容。

### 2.3 提交 dev 改动

本机 dev 因为 `.git` 被环境占位，需要用 wrapper：

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-dev
tools/git-dev status --short
tools/git-dev add skills/<skill-name> tests/<test-file>
tools/git-dev commit -m "feat: add <feature> dev candidate"
```

服务器 dev 是普通 Git：

```bash
cd /aris/aris-dev
git status --short
git add skills/<skill-name> tests/<test-file>
git commit -m "feat: add <feature> dev candidate"
```

### 2.4 promote 前 dry-run

在 dev 目录执行：

```bash
tools/promote_to_stable.sh \
  --component skills/<skill-name> \
  --stable /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition \
  --dry-run
```

容器内：

```bash
cd /aris/aris-dev
tools/promote_to_stable.sh \
  --component skills/<skill-name> \
  --stable /aris/framework \
  --dry-run
```

输出应类似：

```text
PROMOTE skills/<skill-name>
  from: ...
  to:   ...
```

### 2.5 真正 promote

本机：

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-dev
tools/promote_to_stable.sh \
  --component skills/<skill-name> \
  --stable /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
```

容器内：

```bash
cd /aris/aris-dev
tools/promote_to_stable.sh \
  --component skills/<skill-name> \
  --stable /aris/framework
```

注意：

- 默认拒绝覆盖 stable 已有内容。
- 如果目标已存在，说明这是修改已有 stable 功能，不应该用简单 promote；应在 stable 开分支修改。

### 2.6 在 stable 补测试和文档

进入 stable：

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
git status --short --branch
```

补充：

- `tests/` 里的回归测试
- `CHANGELOG.md`
- 对应 `docs/` / `deploy/` / README
- skill 的 `SKILL.md` metadata、examples、caller 等

运行相关测试：

```bash
python3 tests/<related-test>.py
```

如果改 installer，跑 installer 相关测试。

### 2.7 提交 stable

```bash
git status --short
git add <promoted-files> <tests> <docs>
git commit -m "feat: promote <feature> from dev"
```

### 2.8 清理 dev

promote 成功后，dev 不应长期保留同名实现，否则会造成 stable/dev 分叉。

可选方式：

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-dev
tools/git-dev rm -r skills/<skill-name>
tools/git-dev commit -m "chore: remove promoted <skill-name> from dev"
```

如果想保留历史材料，移到：

```text
legacy/
```

但不要让项目继续依赖 dev 里的旧副本。

## 3. stable 功能/修复分支流程

适合修复 stable 已有能力，例如：

- 部署 Dockerfile
- installer
- tests
- stable skill bug
- 文档修复

### 3.1 确认主线干净

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
git status --short --branch
```

如果有未提交改动，先判断：

- 是当前任务的改动：继续提交。
- 是别人的/无关改动：不要覆盖，不要 reset。

### 3.2 从主线开分支

当前 stable 主线是：

```text
orangmood-tripartite-night-20260512
```

开功能/修复分支：

```bash
git switch orangmood-tripartite-night-20260512
git switch -c codex-<topic>
```

例子：

```bash
git switch -c codex-gpu-deploy-fix
git switch -c codex-installer-reconcile-content
git switch -c codex-skill-dag-cleanup
```

### 3.3 TDD 开发

写一条行为测试：

```bash
python3 tests/<new-test>.py
```

确认 RED。

写最小实现。

跑测试到 GREEN：

```bash
python3 tests/<new-test>.py
```

必要时继续下一条行为测试。

### 3.4 提交分支

```bash
git status --short
git add <changed-files>
git commit -m "fix: <short description>"
```

提交前至少跑相关测试。

### 3.5 合并回主线

切回主线：

```bash
git switch orangmood-tripartite-night-20260512
```

如果主线没有新提交，优先 fast-forward：

```bash
git merge --ff-only codex-<topic>
```

如果不能 fast-forward，说明主线和分支都前进了。先看差异：

```bash
git log --oneline --graph --decorate --all -20
```

确认后再普通 merge：

```bash
git merge codex-<topic>
```

不要在不理解冲突时强行解决。

### 3.6 合并后验证

```bash
git status --short --branch
python3 tests/<related-test>.py
```

例子，GPU 部署相关：

```bash
python3 tests/test_gpu_deploy_contract.py
python3 tests/test_aris_gpu_doctor.py
```

### 3.7 推送

当前本地 stable 可能领先远端：

```bash
git status --short --branch
```

看到：

```text
[ahead N]
```

说明还没推送。

推送：

```bash
git push origin orangmood-tripartite-night-20260512
```

如果网络失败，不要反复改代码；先记录当前 commit：

```bash
git log --oneline --decorate -3
```

## 4. 3090x2 部署分支这次发生了什么

这次流程是 stable 分支开发，不是 dev promote。

分支：

```text
codex-3090x2-deploy-fix
```

修复内容：

- GPU Dockerfile 代理和 Python 安装问题
- `aris_gpu_doctor.sh`
- GPU deploy tests
- 通用 GPU 新手部署文档
- 3090x2 专用部署文档
- dev framework 挂载 `/aris/aris-dev`

已合并回：

```text
orangmood-tripartite-night-20260512
```

合并方式：

```bash
git switch orangmood-tripartite-night-20260512
git merge --ff-only codex-3090x2-deploy-fix
```

当前 stable 主线包含部署修复。

## 5. 常见错误

### 5.1 把开发过程材料 promote 到 stable

不要 promote：

```text
to-developer/
settings*.json
ssh.txt
临时日志
私有讨论
```

`tools/promote_to_stable.sh` 会拒绝 `to-developer/`。

### 5.2 dev 和 stable 同名功能长期共存

promote 后要清理 dev，否则以后不知道项目用的是哪个版本。

### 5.3 在 stable 主线直接乱改

小文档可以直接改，但功能/修复建议开分支。尤其是：

- installer
- deploy
- skill runtime
- templates
- tests

### 5.4 用 `git reset --hard` 清理现场

不要这么做，除非明确知道会丢弃什么。当前工作区可能有用户或其他 agent 的改动。

### 5.5 服务器和本机 dev 不同步

如果本机 dev 改了，服务器也要同步：

```bash
rsync -avz --delete \
  --exclude '.git/' \
  --exclude '.git-store/' \
  --exclude '.codex/' \
  --exclude '.agents/' \
  --exclude '.claude/' \
  --exclude 'to-developer/discussions/settings*.json' \
  --exclude 'to-developer/discussions/ssh.txt' \
  /root/Projects/aris/Auto-research-in-sleep/aris-dev/ \
  3090x2-original:/workspace/Orangmood/ARIS/aris-dev/
```

然后在服务器提交：

```bash
ssh 3090x2-original
cd /workspace/Orangmood/ARIS/aris-dev
git status --short --branch
git add <files>
git commit -m "<message>"
```

## 6. 最短命令速查

dev promote：

```bash
cd /aris/aris-dev
tools/promote_to_stable.sh --component skills/foo --stable /aris/framework --dry-run
tools/promote_to_stable.sh --component skills/foo --stable /aris/framework
```

stable 开分支：

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
git switch orangmood-tripartite-night-20260512
git switch -c codex-my-fix
```

stable 合并回主线：

```bash
git switch orangmood-tripartite-night-20260512
git merge --ff-only codex-my-fix
```

看当前状态：

```bash
git status --short --branch
git log --oneline --decorate -5
```
