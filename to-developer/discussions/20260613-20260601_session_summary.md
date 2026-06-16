# 2026-06-01 工作总结 & 待办

## 今日完成

### 1. 3090x2 服务器部署（进行中）

- ✅ 诊断代理问题（Clash Verge 端口 7897，需 `proxyon`）
- ✅ 构建 `aris-gpu` Docker 镜像（CUDA 12.8 + PyTorch）
- ✅ 容器内手动 clone 框架（git clone 被 `|| true` 掩盖错误）
- ⏳ Skills 安装（79/91，缺 12 个 mattpocock skills）
- ⏳ git push 未成功（TLS 握手失败，需等网络恢复）

### 2. 框架 Bug 修复

- ✅ 12 个 skill symlink 指向外部路径（mattpocock-skills），导致 `install_aris.sh` 拒绝安装
- ✅ 提交 `0b67767`: replace external symlinks with real skill directories
- ⏳ 此 commit 未 push 到远程

### 3. exp0603 项目创建

- ✅ 目录结构、CLAUDE.md（3090x2 服务器信息）、Idea 文档
- ✅ ARIS skills 安装（91 个）
- ✅ 同步到 3090x2 服务器
- ⏳ 容器内需重建 skills symlink + 数据集 symlink

---

## 待办清单

### 🔴 必做（阻塞性）

1. **git push** — commit `0b67767` 未推送，网络恢复后执行
   ```bash
   cd /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
   git push
   ```

2. **容器内修复 exp0603 skills**
   ```bash
   # 容器内
   cd /aris/projects/exp0603
   rm -rf .claude/skills .aris/installed-skills.txt .aris/tools
   bash /aris/framework/tools/install_aris.sh . --aris-repo /aris/framework --quiet
   ```

3. **容器内修复 exp0516 skills**（同上）
   ```bash
   cd /aris/projects/exp0516
   rm -rf .claude/skills .aris/installed-skills.txt .aris/tools
   bash /aris/framework/tools/install_aris.sh . --aris-repo /aris/framework --quiet
   ```

4. **数据集同步到 3090x2 共享目录**（宿主机）
   ```bash
   # 本机 WSL
   rsync -avz --progress \
     /root/Projects/aris/Auto-research-in-sleep/exp0516/VOC2007.tar.gz \
     /root/Projects/aris/Auto-research-in-sleep/exp0516/VOCdevkit_full.tar.gz \
     3090x2-original:/workspace/shared/datasets/

   # 宿主机上解压
   cd /workspace/shared/datasets
   tar xzf VOC2007.tar.gz
   tar xzf VOCdevkit_full.tar.gz
   ```

5. **exp0603 数据集 symlink**（容器内，指向宿主机共享目录）
   ```bash
   # 容器内
   cd /aris/projects/exp0603/data
   ln -s /workspace/shared/datasets/VOCdevkit VOCdevkit
   ```

### 🟡 框架优化（已完成）

| # | 方向 | 状态 | 描述 |
|---|------|------|------|
| 1 | Executor 拆分 | ✅ 已完成 | Coder/Deployer/Writer 三个专用 SKILL.md + 更新 Leader 派发 prompt |
| 2 | 上下文记忆本地化 | ⏳ 待做 | Agent 启动自动读状态文件，长流程不丢上下文 |
| 3 | blocked-protocol 完善 | ⏳ 待做 | 绕过策略表 + 累计阈值机制标准化 |

### 🟢 导师任务

1. **论文** — 从 C 会投起，用 `/leader "频域特征+原型学习做小样本增量目标检测"` 在 exp0603 跑完整 pipeline
2. **专利** — 测试 `/patent-pipeline` skill 生成专利交底书
3. **框架优化** — 同上 🟡 列表

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `/tmp/aris-handoff-20260601.md` | 上次 handoff 文档 |
| `deploy/DEPLOY_GPU_3090x2.md` | 3090x2 部署指南 |
| `tools/install_aris.sh` | Skill 安装脚本 |
| `exp0603/CLAUDE.md` | 新项目配置（3090x2 服务器） |
| `exp0516/discussions/20260527_progress_extended.md` | 框架优化方向参考 |

---

## 容器启动速查

```bash
# 每次服务器重启后
ssh 3090x2-original
proxyon
docker start aris-gpu
docker exec -it aris-gpu bash

# 容器内更新框架（push 成功后）
cd /aris/framework && sudo -E git pull
cd /aris/projects/exp0603
bash /aris/framework/tools/install_aris.sh . --aris-repo /aris/framework --quiet

# 启动 Leader pipeline
cd /aris/projects/exp0603
claude
/leader "频域特征+原型学习做小样本增量目标检测"
```