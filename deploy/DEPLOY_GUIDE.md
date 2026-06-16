# ARIS 部署指南

> 面向组长/管理员。从零开始在一台服务器上部署 ARIS 多人研究环境。

## 前置要求

| 项目 | 最低配置 |
|------|---------|
| 服务器 | Ubuntu 20.04+ |
| Docker | 24.0+ (`docker compose` 子命令可用) |
| 网络 | 能访问 GitHub（拉框架）和 PyPI（装依赖） |
| 磁盘 | 足够空间放数据集 + 项目 |

## 网络代理基线

部署时至少有三层网络环境：宿主机 shell、Git、容器运行时。不要只配一处代理；很多工具只读小写 `http_proxy/https_proxy`，也有工具只读大写 `HTTP_PROXY/HTTPS_PROXY`。

如果服务器需要代理才能访问 GitHub/PyPI/飞书，先在宿主机 shell 设置大小写两套变量：

```bash
export HTTP_PROXY=http://127.0.0.1:[你的代理端口]
export HTTPS_PROXY=http://127.0.0.1:[你的代理端口]
export NO_PROXY=127.0.0.1,localhost,::1
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export no_proxy="$NO_PROXY"

curl -I https://github.com
python3 -m pip index versions pip >/dev/null
```

如果 `git clone` / `git pull` 仍然连不上 GitHub，再显式配置 git 代理：

```bash
git config --global http.proxy "$HTTP_PROXY"
git config --global https.proxy "$HTTPS_PROXY"
git config --global --get-regexp 'http.*proxy'
```

不需要代理时清理：

```bash
unset HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy
git config --global --unset http.proxy || true
git config --global --unset https.proxy || true
```

如果使用 Clash/V2Ray，确认代理监听地址对当前环境可达：

| 场景 | 推荐代理地址 |
|------|--------------|
| 宿主机本机命令 | `http://127.0.0.1:7897` |
| Docker bridge 容器访问宿主机代理 | `http://172.17.0.1:7897` 或宿主机内网 IP |
| Docker Desktop | `http://host.docker.internal:7897` |
| 远程服务器上的 Clash | 监听 `0.0.0.0:7897`，并用防火墙限制来源 |

## 快速开始（5 分钟）

默认部署模型是**一人一个长期容器**：

| 资源 | 隔离/共享方式 |
|------|---------------|
| 用户运行环境 | 每人一个容器，例如 `aris-zhangsan`、`aris-lisi` |
| framework | 每人一份宿主机目录，挂到 `/aris/framework` |
| 项目目录 | 每人一份宿主机目录，挂到 `/aris/projects` |
| 数据集 | 共享宿主机目录，挂到 `/aris/shared/datasets` |
| 预训练模型/下载缓存 | 共享宿主机目录，挂到 `/aris/shared/pretrained` 和 `/aris/shared/downloads` |
| SSH key、git 身份、个人 API 覆盖 | 每个容器单独配置 |

也就是说，组里不是所有人挤进同一个容器；管理员每加一个用户，就在 `.env` 和 `docker-compose.yaml` 中增加一组 researcher 配置。每个用户有自己的 framework copy，可以独立更新和回退；数据集、预训练模型、下载缓存是组内共享资源。

拓扑如下：

```text
Host Server
└── [你的ARIS总目录]/
    ├── users/
    │   ├── zhangsan/
    │   │   ├── framework/         # 挂到 aris-zhangsan:/aris/framework
    │   │   ├── projects/          # 挂到 aris-zhangsan:/aris/projects
    │   │   └── .aris/             # 挂到 aris-zhangsan:/aris/.aris
    │   └── lisi/
    │       ├── framework/         # 挂到 aris-lisi:/aris/framework
    │       ├── projects/          # 挂到 aris-lisi:/aris/projects
    │       └── .aris/             # 挂到 aris-lisi:/aris/.aris
    └── shared/
        ├── datasets/              # 挂到 /aris/shared/datasets，只读
        ├── pretrained/            # 挂到 /aris/shared/pretrained
        └── downloads/             # 挂到 /aris/shared/downloads
```

管理员只管宿主机和 compose；普通用户只进入自己的容器。

```bash
# 1. 管理员准备一份部署用 framework
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git [你的ARIS总目录]/admin/framework
cd [你的ARIS总目录]/admin/framework/deploy

# 2. 配置环境变量
cp .env.example .env
vim .env   # 填写 ARIS_ROOT、用户名、API key、共享数据路径

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

管理员先指定一个 `ARIS_ROOT`，所有用户 workspace 和共享资产都放在这个根目录下，方便备份、迁移和权限管理。

```bash
export ARIS_ROOT="[你的ARIS总目录]"

mkdir -p "$ARIS_ROOT"/admin
mkdir -p "$ARIS_ROOT"/users/{zhangsan,lisi}/{framework,projects,.aris}
mkdir -p "$ARIS_ROOT"/shared/{datasets,pretrained,downloads}
# 如果用户还没有 SSH 目录，就为每个用户建好
mkdir -p /home/zhangsan/.ssh /home/lisi/.ssh
```

给每个用户准备初始 framework copy：

```bash
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git "$ARIS_ROOT/admin/framework"
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git "$ARIS_ROOT/users/zhangsan/framework"
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git "$ARIS_ROOT/users/lisi/framework"
```

如果这些目录归 root 或其他用户所有，按你的服务器权限模型调整 owner/group；不要直接照抄 `chmod 777`。

### Step 3: 配置 .env

```bash
cd [你的ARIS总目录]/admin/framework/deploy
cp .env.example .env
```

必填项:

```env
# 用户（每人一个容器；按人数复制 researcher block）
USER1_NAME=zhangsan
USER1_UID=1001
USER1_SSH=/home/zhangsan/.ssh    # 宿主机上该用户的 SSH 目录
USER1_FRAMEWORK_PATH=[你的ARIS总目录]/users/zhangsan/framework
USER1_PROJECTS_PATH=[你的ARIS总目录]/users/zhangsan/projects
USER1_STATE_PATH=[你的ARIS总目录]/users/zhangsan/.aris

USER2_NAME=lisi
USER2_UID=1002
USER2_SSH=/home/lisi/.ssh
USER2_FRAMEWORK_PATH=[你的ARIS总目录]/users/lisi/framework
USER2_PROJECTS_PATH=[你的ARIS总目录]/users/lisi/projects
USER2_STATE_PATH=[你的ARIS总目录]/users/lisi/.aris

# API（组统一，用户可在容器内覆盖）
ANTHROPIC_API_KEY=sk-ant-xxx     # 或中转站 key
ANTHROPIC_BASE_URL=              # 留空=官方, 填中转站 URL
OPENAI_API_KEY=sk-xxx            # Codex 用

# 共享资源（宿主机路径）
ARIS_ROOT=[你的ARIS总目录]
DATASETS_PATH=[你的ARIS总目录]/shared/datasets
PRETRAINED_PATH=[你的ARIS总目录]/shared/pretrained
DOWNLOADS_PATH=[你的ARIS总目录]/shared/downloads

# 代理（可选）
HTTP_PROXY=http://192.168.1.1:7890
HTTPS_PROXY=http://192.168.1.1:7890
NO_PROXY=127.0.0.1,localhost,gitea
http_proxy=http://192.168.1.1:7890
https_proxy=http://192.168.1.1:7890
no_proxy=127.0.0.1,localhost,gitea

# git 代理（可选；只有 git 仍连不上外网时再填）
GIT_HTTP_PROXY=
GIT_HTTPS_PROXY=

# framework 更新检查（默认只检查，不自动更新）
ARIS_AUTO_CHECK_UPDATE=1
ARIS_UPDATE_CHECK_INTERVAL=1d
ARIS_UPDATE_CHECK_TIMEOUT=10s
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

首次启动前，每个用户的 `framework/` 目录必须已经是可用的 ARIS checkout。管理员可以从 admin framework 克隆或同步一份初始版本给每个用户；之后用户在自己的容器内用 `aris framework check-update` / `aris framework update` / `aris framework rollback` 管理自己的 framework 版本。

容器启动、进入交互 shell、打开 tmux pane 时默认都会触发检查入口，但 `ARIS_UPDATE_CHECK_INTERVAL=1d` 会让同一用户每天最多联网检查一次；`--notify` 的状态记录会让同一用户每天最多看到一次提醒。检查不会自动 `git pull`。如果实验期不想自动检查，在 `.env` 里设：

```env
ARIS_AUTO_CHECK_UPDATE=0
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
# 进入自己的容器，不要进入别人的容器
docker exec -it aris-zhangsan bash

# 在自己的 /aris/projects 下创建项目
cd /aris/projects
aris project init ./freq-detection --direction "基于频域特征的增量目标检测"

# 同步代码
$sync push                    # 保存到 Gitea
$sync deploy --server 4090x4  # 部署到 GPU 服务器

# 更新框架
aris framework check-update
aris framework update

# 启动研究 pipeline
$leader "频域增量检测"
```

## 添加新用户

1. 编辑 `.env`，复制一个 researcher block
2. 在 `docker-compose.yaml` 中复制一个 researcher service block
3. 修改 service 名、`USER*_NAME`、`USER*_UID/GID`、`USER*_SSH`、`USER*_FRAMEWORK_PATH`、`USER*_PROJECTS_PATH`
4. `docker compose up -d` 启动新容器

新增用户不会进入已有用户容器，也不会复用已有用户的 framework 或 projects 目录。

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
# .env 里配代理（Docker bridge 网络）
# 172.17.0.1 是 Docker 默认网桥 IP，所有容器都能访问
HTTP_PROXY=http://172.17.0.1:7897
HTTPS_PROXY=http://172.17.0.1:7897
NO_PROXY=127.0.0.1,localhost,gitea
http_proxy=http://172.17.0.1:7897
https_proxy=http://172.17.0.1:7897
no_proxy=127.0.0.1,localhost,gitea
```

宿主机跑 Clash/V2Ray 监听 `*:7897`（所有接口）即可。

> **注意**: 不要用 `--network host`，用默认 bridge 网络。entrypoint 会自动将大小写代理变量写入 `/etc/environment`，`docker exec` 的 PAM 会话也能正确读取。

容器内验证：

```bash
docker exec -it aris-zhangsan bash
env | grep -i proxy
curl -I https://github.com
git ls-remote https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git HEAD
```

如果 `curl` 能通但 `git ls-remote` 失败，再设置 git 专用代理：

```env
GIT_HTTP_PROXY=http://172.17.0.1:7897
GIT_HTTPS_PROXY=http://172.17.0.1:7897
```

然后重建或重启容器：

```bash
docker compose up -d --force-recreate
```

容器启动时会执行：

```bash
git config --global http.proxy "$GIT_HTTP_PROXY"
git config --global https.proxy "$GIT_HTTPS_PROXY"
```

如果之后切回直连，记得清理容器里的 git 代理：

```bash
docker exec -it aris-zhangsan bash -lc '
git config --global --unset http.proxy || true
git config --global --unset https.proxy || true
'
```

## 飞书远程控制部署

新增的飞书能力由两部分组成：

| 组件 | 路径 | 职责 |
|------|------|------|
| Feishu bridge | `mcp-servers/feishu-bridge/server.py` | HTTP 发送/更新卡片、长连接接收飞书消息、写入 session inbox |
| Feishu session runner | `tools/aris_feishu_session.py` | 消费 inbox，启动/恢复 Codex Session，把最终回复发回飞书 |

`.env` 里增加：

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_USER_ID=ou_xxx
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_ENABLE_WS=1
BRIDGE_PORT=5000
ARIS_PROJECT_ROOT=[你的ARIS总目录]/admin/framework
ARIS_FEISHU_CONTROL_ROOT=
```

启动 bridge：

```bash
cd [你的ARIS总目录]/admin/framework
python3 -m venv .venv-feishu
.venv-feishu/bin/pip install -r mcp-servers/feishu-bridge/requirements.txt
set -a; source deploy/.env; set +a
export FEISHU_ENABLE_WS=1
export ARIS_PROJECT_ROOT=[你的ARIS总目录]/admin/framework
.venv-feishu/bin/python mcp-servers/feishu-bridge/server.py
```

再启动受控 Codex session：

```bash
.venv-feishu/bin/python tools/aris_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root [你的ARIS总目录]/admin/framework \
  --profile leader \
  --bridge-url http://127.0.0.1:5000 \
  --resume-last \
  --feishu-format card
```

部署注意：

- `BRIDGE_PORT` 默认是 `5000`；如果报 `Address already in use`，换端口并同步修改 `--bridge-url`。
- 飞书长连接需要服务器能访问飞书开放平台；如果连接不上，按上面的大小写 proxy 规则同时设置 `HTTP_PROXY/HTTPS_PROXY/http_proxy/https_proxy`。
- bridge 不执行 shell、tools、skills；真正执行发生在 opt-in 的 Codex session runner。
- `--yolo` 只应在可信服务器和可信项目中使用。
- 详细飞书配置见 [docs/FEISHU_INTEGRATION.md](../docs/FEISHU_INTEGRATION.md)。

## 客户端选择

| 客户端 | 怎么用 | 备注 |
|--------|--------|------|
| Codex CLI | 容器内 `codex` | 默认入口，OpenAI key 必须配 |
| Claude Code (Terminal) | 容器内直接敲 `claude` | 兼容入口 |
| Claude Code (VSCode) | VSCode Remote SSH 到容器 | 需额外配 |
| Claude Desktop | 不走容器，本地 APP 连 API | 无法用 skills/tools |

## 故障排查

| 问题 | 解决 |
|------|------|
| `docker compose up` 失败 | 检查 Docker 版本 ≥ 24.0 |
| Gitea 502 | 等 30s 再试，首次启动慢 |
| 容器内 `git push` 失败 | 检查 GITEA_TOKEN，或 `git remote set-url origin http://token@gitea:3000/user/repo.git` |
| `git clone` / `git pull` 连不上 GitHub | 先设置大小写 proxy env；仍失败再设置 `git config --global http.proxy/https.proxy` |
| 容器里 `curl` 能联网但 git 不行 | 在 `.env` 填 `GIT_HTTP_PROXY` / `GIT_HTTPS_PROXY` 后 `docker compose up -d --force-recreate` |
| Python/pip/Feishu SDK 不认代理 | 同时设置 `HTTP_PROXY/HTTPS_PROXY` 和 `http_proxy/https_proxy` |
| Feishu bridge 启动时报 `Address already in use` | 修改 `BRIDGE_PORT`，并同步修改 runner 的 `--bridge-url` |
| SSH 到 GPU 超时 | 检查 SSH key mount，`ls ~/.ssh/` |
| API 403/401 | 检查 key 是否过期，base_url 是否正确 |
| CUDA not available (GPU 服务器) | 检查 `LD_LIBRARY_PATH`，参考 exp0516 的 conda activate hook |
