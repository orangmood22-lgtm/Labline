# ARIS 部署指南

> 面向组长/管理员。从零开始在一台服务器上部署 ARIS 多人研究环境。

## 前置要求

| 项目 | 最低配置 |
|------|---------|
| 服务器 | Ubuntu 20.04+, 任意 GPU（2x 3090 够用） |
| Docker | 24.0+ (`docker compose` 子命令可用) |
| 网络 | 能访问 GitHub（拉框架）和 PyPI（装依赖） |
| 磁盘 | /data 分区 500GB+（数据集 + 项目） |

## 快速开始（5 分钟）

```bash
# 1. 克隆框架
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git /opt/aris-framework
cd /opt/aris-framework/deploy

# 2. 配置环境变量
cp .env.example .env
vim .env   # 填写用户名、API key、数据集路径

# 3. 启动
docker compose up -d

# 4. 进入容器
docker exec -it aris-zhangsan bash
```

## 详细步骤

### Step 1: 安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录使 docker 组生效
```

### Step 2: 准备目录结构

```bash
# 宿主机上
sudo mkdir -p /data/shared/{datasets,pretrained,downloads}
sudo mkdir -p /data/aris-users   # 各用户项目存储
sudo chmod 777 /data/shared /data/aris-users
```

### Step 3: 配置 .env

```bash
cd /opt/aris-framework/deploy
cp .env.example .env
```

必填项:

```env
# 用户（按人数复制 researcher block）
USER1_NAME=zhangsan
USER1_UID=1001
USER1_SSH=/home/zhangsan/.ssh    # 宿主机上该用户的 SSH 目录

USER2_NAME=lisi
USER2_UID=1002
USER2_SSH=/home/lisi/.ssh

# API（组统一，用户可在容器内覆盖）
ANTHROPIC_API_KEY=sk-ant-xxx     # 或中转站 key
ANTHROPIC_BASE_URL=              # 留空=官方, 填中转站 URL
OPENAI_API_KEY=sk-xxx            # Codex 用

# 数据集目录
DATASETS_PATH=/data/shared/datasets

# 代理（可选）
HTTP_PROXY=http://192.168.1.1:7890
```

### Step 4: 启动服务

```bash
docker compose up -d

# 查看状态
docker compose ps

# 预期输出:
# aris-gitea       running  0.0.0.0:3000->3000/tcp, 0.0.0.0:2222->22/tcp
# aris-zhangsan    running
# aris-lisi        running
```

### Step 5: 初始化 Gitea

1. 浏览器打开 `http://服务器IP:3000`
2. 首次访问会进安装页，数据库选 SQLite，其余默认
3. 注册管理员账号
4. 为每个用户创建账号（或开启注册让用户自己注册）
5. 在容器内配置 git:

```bash
# 进入容器
docker exec -it aris-zhangsan bash

# 配置 git 身份
git config --global user.name "zhangsan"
git config --global user.email "zhangsan@lab.edu"

# 配置 Gitea token（从 Gitea 网页 Settings → Applications 创建）
echo "export GITEA_TOKEN=your_token_here" >> ~/.bashrc
```

### Step 6: 用户日常使用

```bash
# 进入容器
docker exec -it aris-zhangsan bash

# 创建新项目
/init-research "频域增量检测" --direction "基于频域特征的增量目标检测"

# 同步代码
/sync push                    # 保存到 Gitea
/sync deploy --server 4090x4  # 部署到 GPU 服务器

# 更新框架
/framework-update

# 启动研究 pipeline
/leader "频域增量检测"
```

## 添加新用户

1. 编辑 `.env`，复制一个 researcher block
2. 在 `docker-compose.yaml` 中复制一个 researcher service block
3. `docker compose up -d` 重启

或者用快捷脚本:

```bash
# deploy/add-user.sh (TODO: 后续实现)
bash add-user.sh --name wangwu --uid 1003
```

## 多台服务器部署

每台小组服务器独立部署一套:

```
服务器 A (小组1): aris-framework + Gitea + 容器x3
服务器 B (小组2): aris-framework + 容器x3 (Gitea 指向 A 的)
服务器 C (小组3): aris-framework + 容器x3 (Gitea 指向 A 的)
```

Gitea 只需部署一份。其他服务器的容器 `GITEA_URL` 指向 Gitea 所在服务器:

```env
# 服务器 B/C 的 .env
GITEA_URL=http://192.168.1.100:3000
```

## SSH 到 GPU 集群

容器需要能 SSH 到共享 GPU 服务器。配置方式:

```bash
# 宿主机上准备 SSH key
ssh-keygen -t ed25519 -f /home/zhangsan/.ssh/id_ed25519 -N ""
ssh-copy-id -i /home/zhangsan/.ssh/id_ed25519.pub user@gpu-server

# key 通过 volume mount 进入容器 (已在 docker-compose 配好)
```

容器内配 SSH config:

```bash
cat >> ~/.ssh/config <<EOF
Host 4090x4
    HostName 192.168.1.200
    User ai_worker
    Port 22
    IdentityFile ~/.ssh/id_ed25519

Host 4090x8
    HostName 192.168.1.201
    User ai_worker
    Port 22
    IdentityFile ~/.ssh/id_ed25519
EOF
chmod 600 ~/.ssh/config
```

## API 配置

### 组统一 key（.env 里配）

所有用户容器继承。

### 个人覆盖（容器内配）

```bash
# 覆盖 Anthropic（比如用自己的中转站）
cat > ~/.claude/settings.json <<EOF
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-my-personal-key",
    "ANTHROPIC_BASE_URL": "https://my-proxy.com/anthropic"
  }
}
EOF

# 覆盖 OpenAI/Codex
cat > ~/.codex/auth.json <<EOF
{"OPENAI_API_KEY": "sk-my-personal-key"}
EOF
cat > ~/.codex/config.toml <<EOF
model_provider = "my_proxy"
model = "gpt-5.5"
[model_providers.my_proxy]
base_url = "https://my-proxy.com/v1"
wire_api = "responses"
EOF
```

### 需要 VPN/海外 IP

如果用 Anthropic 官方 API 或 Claude Coding Plan:

```env
# .env 里配代理
HTTP_PROXY=http://host.docker.internal:7890
HTTPS_PROXY=http://host.docker.internal:7890
```

`host.docker.internal` 会自动解析到宿主机。宿主机跑 Clash/V2Ray 监听 7890 即可。

## 客户端选择

| 客户端 | 怎么用 | 备注 |
|--------|--------|------|
| Claude Code (Terminal) | 容器内直接敲 `claude` | 推荐，完整功能 |
| Claude Code (VSCode) | VSCode Remote SSH 到容器 | 需额外配 |
| Codex CLI | 容器内 `codex` | OpenAI key 必须配 |
| Claude Desktop | 不走容器，本地 APP 连 API | 无法用 skills/tools |

## 故障排查

| 问题 | 解决 |
|------|------|
| `docker compose up` 失败 | 检查 Docker 版本 ≥ 24.0 |
| Gitea 502 | 等 30s 再试，首次启动慢 |
| 容器内 `git push` 失败 | 检查 GITEA_TOKEN，或 `git remote set-url origin http://token@gitea:3000/user/repo.git` |
| SSH 到 GPU 超时 | 检查 SSH key mount，`ls ~/.ssh/` |
| API 403/401 | 检查 key 是否过期，base_url 是否正确 |
| CUDA not available (GPU 服务器) | 检查 `LD_LIBRARY_PATH`，参考 exp0516 的 conda activate hook |
