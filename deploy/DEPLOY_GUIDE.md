# Labline 部署指南

> 面向组长/管理员。从零开始在一台服务器上部署 Labline 多人研究环境。

## 前置要求

| 项目 | 最低配置 |
|------|---------|
| 服务器 | Ubuntu 20.04+ |
| Docker | 24.0+ (`docker compose` 子命令可用) |
| 网络 | 能访问 GitHub（拉框架）和 PyPI（装依赖） |
| 磁盘 | 足够空间放数据集 + 项目 |

## 网络代理基线

部署时至少有三层网络环境：宿主机 shell、Git、容器运行时。不要只配一处代理；很多工具只读小写 `http_proxy/https_proxy`，也有工具只读大写 `HTTP_PROXY/HTTPS_PROXY`。

Labline 默认**不配置 `ALL_PROXY/all_proxy`**。原因是 Node/Lark SDK 对 `ALL_PROXY` 的处理和 `curl` 不完全一致，飞书 bridge 可能出现 `socket hang up`。统一只用 HTTP/HTTPS 代理变量。

如果服务器需要代理才能访问 GitHub/PyPI/飞书，先在宿主机 shell 设置大小写两套变量：

```bash
export HTTP_PROXY=http://127.0.0.1:[你的代理端口]
export HTTPS_PROXY=http://127.0.0.1:[你的代理端口]
export NO_PROXY=127.0.0.1,localhost,::1
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export no_proxy="$NO_PROXY"
unset ALL_PROXY all_proxy
export NODE_USE_ENV_PROXY=1

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
unset HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy ALL_PROXY all_proxy NODE_USE_ENV_PROXY
git config --global --unset http.proxy || true
git config --global --unset https.proxy || true
```

如果使用 Clash/V2Ray，确认代理监听地址对当前环境可达：

| 场景 | 推荐代理地址 |
|------|--------------|
| 宿主机本机命令 | `http://127.0.0.1:7897` |
| Labline 默认 host network 容器 | `http://127.0.0.1:7897` |
| Docker Desktop | `http://host.docker.internal:7897` |
| 远程服务器上的 Clash | 监听 `0.0.0.0:7897`，并用防火墙限制来源 |

容器启动时会根据 `.env` 自动写入 `~/.proxy_env`，并默认在新 shell 中启用。容器内可以手动切换：

```bash
proxy-on     # 新 shell 默认 source ~/.proxy_env
proxy-off    # 新 shell 不再自动启用代理
source ~/.proxy_env
```

## 快速开始（5 分钟）

默认推荐在 GPU 服务器上使用 `docker-compose.gpu.yaml`；没有 GPU 或只做 SSH 跳板/文档工作的机器使用 `docker-compose.yaml`。两套 compose 都使用同一套代理、host network、cc-switch 和 Labline state 契约。

多人部署模型是**一人一个长期容器**：

| 资源 | 隔离/共享方式 |
|------|---------------|
| 用户运行环境 | 每人一个容器，例如 `labline-zhangsan`、`labline-lisi` |
| framework | 每人一份宿主机目录，挂到 `/labline/framework` |
| 项目目录 | 每人一份宿主机目录，挂到 `/labline/projects` |
| 数据集 | 共享宿主机目录，挂到 `/labline/shared/datasets` |
| 预训练模型/下载缓存 | 共享宿主机目录，挂到 `/labline/shared/pretrained` 和 `/labline/shared/downloads` |
| SSH key、git 身份、个人 API 覆盖 | 每个容器单独配置 |

也就是说，组里不是所有人挤进同一个容器；管理员每加一个用户，就在 `.env` 和 `docker-compose.yaml` 中增加一组 researcher 配置。每个用户有自己的 framework copy，可以独立更新和回退；数据集、预训练模型、下载缓存是组内共享资源。

拓扑如下：

```text
Host Server
└── [你的Labline总目录]/
    ├── users/
    │   ├── zhangsan/
    │   │   ├── framework/         # 挂到 labline-zhangsan:/labline/framework
    │   │   ├── projects/          # 挂到 labline-zhangsan:/labline/projects
    │   │   └── .labline/             # 挂到 labline-zhangsan:~/.labline
    │   └── lisi/
    │       ├── framework/         # 挂到 labline-lisi:/labline/framework
    │       ├── projects/          # 挂到 labline-lisi:/labline/projects
    │       └── .labline/             # 挂到 labline-lisi:~/.labline
    └── shared/
        ├── datasets/              # 挂到 /labline/shared/datasets，只读
        ├── pretrained/            # 挂到 /labline/shared/pretrained
        └── downloads/             # 挂到 /labline/shared/downloads
```

管理员只管宿主机和 compose；普通用户只进入自己的容器。

```bash
# 1. 管理员准备一份部署用 framework
git clone https://github.com/orangmood22-lgtm/Labline.git [你的Labline总目录]/admin/framework
cd [你的Labline总目录]/admin/framework/deploy

# 2A. 默认 GPU 单容器部署
cp .env.gpu.example .env
vim .env   # 填写 framework/projects/shared/ssh 路径和代理端口
docker compose -f docker-compose.gpu.yaml up -d
docker exec -it labline-gpu bash

# 2A-image. 使用预构建 GPU 镜像部署（目标服务器不现场 build）
# 先在 .env 填 LABLINE_GPU_IMAGE=你的registry/labline-gpu:tag
docker compose -f docker-compose.gpu.image.yaml pull
docker compose -f docker-compose.gpu.image.yaml up -d

# 2B. 多人普通 compose 部署
cp .env.example .env
vim .env   # 填写 LABLINE_ROOT、用户名、共享数据路径、代理端口
docker compose up -d
docker exec -it labline-zhangsan bash

# 2B-image. 使用预构建普通镜像部署
# 先在 .env 填 LABLINE_IMAGE=你的registry/labline:tag
docker compose -f docker-compose.image.yaml pull
docker compose -f docker-compose.image.yaml up -d
```

预构建镜像的构建、推送、离线 tar 包和回滚流程见 `deploy/IMAGE_PACKAGING.md`。

## 3090 单用户实机测试：GPU + 暴露端口

这一节给 3090 服务器上的单用户实测用。目标是启动一个 `labline-gpu` 容器，确认 GPU、Labline runtime smoke 和宿主机端口访问都正常。默认 GPU compose 使用 `network_mode: host`，所以**不需要也不能靠 `ports:` / `-p` 做端口映射**；容器内进程只要监听 `0.0.0.0:18080`，宿主机的 `18080` 就会暴露出来。

### 1. 在 3090 宿主机准备目录

```bash
export LABLINE_ROOT=/srv/labline-realtest
export FRAMEWORK_PATH="$LABLINE_ROOT/framework"
export DEV_FRAMEWORK_PATH="$LABLINE_ROOT/labline-dev"
export PROJECT_PATH="$LABLINE_ROOT/projects"
export DATASETS_PATH="$LABLINE_ROOT/shared/datasets"
export PRETRAINED_PATH="$LABLINE_ROOT/shared/pretrained"
export SSH_PATH="$HOME/.ssh"

mkdir -p "$LABLINE_ROOT" "$PROJECT_PATH" "$DATASETS_PATH" "$PRETRAINED_PATH"

# 如果还没有 framework checkout：
git clone https://github.com/orangmood22-lgtm/Labline.git "$FRAMEWORK_PATH"

# docker-compose.gpu.yaml 当前要求 DEV_FRAMEWORK_PATH 是存在的绝对路径。
# 没有 dev checkout 时，可以先复用同一份 framework；需要开发版时再换成真实 dev checkout。
ln -sfn "$FRAMEWORK_PATH" "$DEV_FRAMEWORK_PATH"
```

确认 GPU 和 Docker runtime：

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.8.0-devel-ubuntu22.04 nvidia-smi
docker compose version
```

### 2. 配置 GPU `.env`

```bash
cd "$FRAMEWORK_PATH/deploy"
cp .env.gpu.example .env
```

把 `.env` 至少改成下面这些值。代理端口按 3090 服务器实际情况改；如果服务器直连可用，把 `LABLINE_PROXY_ENABLED=0` 并清空 HTTP/HTTPS proxy。

```env
USERNAME=researcher
USER_UID=1000
USER_GID=1000

FRAMEWORK_PATH=/srv/labline-realtest/framework
DEV_FRAMEWORK_PATH=/srv/labline-realtest/labline-dev
PROJECT_PATH=/srv/labline-realtest/projects
DATASETS_PATH=/srv/labline-realtest/shared/datasets
PRETRAINED_PATH=/srv/labline-realtest/shared/pretrained
SSH_PATH=/home/researcher/.ssh

NVIDIA_VISIBLE_DEVICES=all
CUDA_VISIBLE_DEVICES=

LABLINE_PROXY_ENABLED=1
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
NO_PROXY=127.0.0.1,localhost
http_proxy=http://127.0.0.1:7897
https_proxy=http://127.0.0.1:7897
no_proxy=127.0.0.1,localhost
GIT_HTTP_PROXY=
GIT_HTTPS_PROXY=
```

不要把 OpenAI、Anthropic、Feishu app secret 写进 `.env`。模型 provider 进容器后用 `cc-switch-cli` 配。

### 3. 启动容器

```bash
cd "$FRAMEWORK_PATH/deploy"
docker compose -f docker-compose.gpu.yaml up -d --build
docker compose -f docker-compose.gpu.yaml ps
docker exec -it labline-gpu bash
```

容器内快速确认：

```bash
nvidia-smi
python3 - <<'PY'
import torch
print("cuda_available=", torch.cuda.is_available())
print("gpu_count=", torch.cuda.device_count())
PY
lane framework --version
```

### 4. 创建测试项目并跑 Labline debug smoke

容器内执行：

```bash
cd /labline/projects
lane project init ./runtime-port-smoke --direction "3090 runtime exposed port smoke" --no-commit

lane debug runtime-smoke \
  --project /labline/projects/runtime-port-smoke \
  --in-place \
  --yes
```

等价单行命令：

```bash
lane debug runtime-smoke --project /labline/projects/runtime-port-smoke --in-place --yes
```

通过标准：

- `status: pass`
- 报告路径打印到 `debug-report.md` / `debug-report.json`
- 项目内出现 `.labline/runtime/`
- 根目录没有新的 `PIPELINE_STATE.json`

### 5. 暴露 18080 端口做浏览器实测

容器内启动一个最小 HTTP 服务：

```bash
cd /labline/projects/runtime-port-smoke
tmux new-session -d -s port-smoke 'python3 -m http.server 18080 --bind 0.0.0.0'
```

宿主机检查监听：

```bash
ss -lntp | grep 18080
curl -I http://127.0.0.1:18080
```

从你的本机浏览器访问：

```text
http://[服务器IP]:18080
```

如果访问不到，先分层排查：

```bash
# 3090 宿主机
curl -I http://127.0.0.1:18080
ss -lntp | grep 18080

# 如果宿主机可访问、本机不可访问，检查防火墙/安全组。
sudo ufw status
# 只允许你的办公网或本机出口 IP 更安全；不要无脑长期开放给全网。
sudo ufw allow from [你的本机出口IP或网段] to any port 18080 proto tcp
```

因为 compose 使用 `network_mode: host`，端口冲突也发生在宿主机层面。如果 `18080` 被占用，换一个未使用的高位端口，并同步替换上面的命令。

### 6. 清理实测环境

```bash
# 容器内
tmux kill-session -t port-smoke || true

# 宿主机
cd "$FRAMEWORK_PATH/deploy"
docker compose -f docker-compose.gpu.yaml down
```

如果要保留容器供后续实测，不要执行 `down`；只停止端口 smoke 的 tmux session 即可。

## 详细步骤

### Step 1: 安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录使 docker 组生效
```

### Step 2: 准备目录结构

管理员先指定一个 `LABLINE_ROOT`，所有用户 workspace 和共享资产都放在这个根目录下，方便备份、迁移和权限管理。

```bash
export LABLINE_ROOT="[你的Labline总目录]"

mkdir -p "$LABLINE_ROOT"/admin
mkdir -p "$LABLINE_ROOT"/users/{zhangsan,lisi}/{framework,projects,.labline}
mkdir -p "$LABLINE_ROOT"/shared/{datasets,pretrained,downloads}
# 如果用户还没有 SSH 目录，就为每个用户建好
mkdir -p /home/zhangsan/.ssh /home/lisi/.ssh
```

给每个用户准备初始 framework copy：

```bash
git clone https://github.com/orangmood22-lgtm/Labline.git "$LABLINE_ROOT/admin/framework"
git clone https://github.com/orangmood22-lgtm/Labline.git "$LABLINE_ROOT/users/zhangsan/framework"
git clone https://github.com/orangmood22-lgtm/Labline.git "$LABLINE_ROOT/users/lisi/framework"
```

如果这些目录归 root 或其他用户所有，按你的服务器权限模型调整 owner/group；不要直接照抄 `chmod 777`。

### Step 3: 配置 .env

```bash
cd [你的Labline总目录]/admin/framework/deploy
cp .env.example .env
```

必填项:

```env
# 用户（每人一个容器；按人数复制 researcher block）
USER1_NAME=zhangsan
USER1_UID=1001
USER1_SSH=/home/zhangsan/.ssh    # 宿主机上该用户的 SSH 目录
USER1_FRAMEWORK_PATH=[你的Labline总目录]/users/zhangsan/framework
USER1_PROJECTS_PATH=[你的Labline总目录]/users/zhangsan/projects
USER1_STATE_PATH=[你的Labline总目录]/users/zhangsan/.labline

USER2_NAME=lisi
USER2_UID=1002
USER2_SSH=/home/lisi/.ssh
USER2_FRAMEWORK_PATH=[你的Labline总目录]/users/lisi/framework
USER2_PROJECTS_PATH=[你的Labline总目录]/users/lisi/projects
USER2_STATE_PATH=[你的Labline总目录]/users/lisi/.labline

# 模型供应商/API key 不写在 .env 里。
# 每个用户进入自己的容器后用 cc-switch-cli 配置 Codex/Claude provider。

# 共享资源（宿主机路径）
LABLINE_ROOT=[你的Labline总目录]
DATASETS_PATH=[你的Labline总目录]/shared/datasets
PRETRAINED_PATH=[你的Labline总目录]/shared/pretrained
DOWNLOADS_PATH=[你的Labline总目录]/shared/downloads

# 代理（默认开启；端口按宿主机代理实际配置改）
LABLINE_PROXY_ENABLED=1
PROXY_PORT=7890
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
NO_PROXY=127.0.0.1,localhost,gitea
http_proxy=http://127.0.0.1:7890
https_proxy=http://127.0.0.1:7890
no_proxy=127.0.0.1,localhost,gitea
# 不要设置 ALL_PROXY/all_proxy。

# git 代理（可选；只有 git 仍连不上外网时再填）
GIT_HTTP_PROXY=
GIT_HTTPS_PROXY=

# framework 更新检查（默认只检查，不自动更新）
LABLINE_AUTO_CHECK_UPDATE=1
LABLINE_UPDATE_CHECK_INTERVAL=1d
LABLINE_UPDATE_CHECK_TIMEOUT=10s
```

### Step 4: 启动服务

```bash
docker compose up -d

# 查看状态
docker compose ps

# 预期输出:
# labline-gitea       running  0.0.0.0:3000->3000/tcp, 0.0.0.0:2222->22/tcp
# labline-zhangsan    running
# labline-lisi        running
```

首次启动前，每个用户的 `framework/` 目录必须已经是可用的 Labline checkout。管理员可以从 admin framework 克隆或同步一份初始版本给每个用户；之后用户在自己的容器内用 `lane framework check-update` / `lane framework update` / `lane framework rollback` 管理自己的 framework 版本。

容器启动、进入交互 shell、打开 tmux pane 时默认都会触发检查入口，但 `LABLINE_UPDATE_CHECK_INTERVAL=1d` 会让同一用户每天最多联网检查一次；`--notify` 的状态记录会让同一用户每天最多看到一次提醒。检查不会自动 `git pull`。如果实验期不想自动检查，在 `.env` 里设：

```env
LABLINE_AUTO_CHECK_UPDATE=0
```

### Step 5: 初始化 Gitea

1. 浏览器打开 `http://服务器IP:3000`
2. 首次访问会进安装页，数据库选 SQLite，其余默认
3. 注册管理员账号
4. 为每个用户创建账号（或开启注册让用户自己注册）
5. 在容器内配置 git:

```bash
# 进入容器
docker exec -it labline-zhangsan bash

# 配置 git 身份
git config --global user.name "zhangsan"
git config --global user.email "zhangsan@lab.edu"

# 配置 Gitea token（从 Gitea 网页 Settings → Applications 创建）
echo "export GITEA_TOKEN=your_token_here" >> ~/.bashrc
```

### Step 6: 用户日常使用

```bash
# 进入自己的容器，不要进入别人的容器
docker exec -it labline-zhangsan bash

# 在自己的 /labline/projects 下创建项目
cd /labline/projects
lane project init ./freq-detection --direction "基于频域特征的增量目标检测"

# 同步代码
$sync push                    # 保存到 Gitea
$sync deploy --server 4090x4  # 部署到 GPU 服务器

# 更新框架
lane framework check-update
lane framework update

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
服务器 A (小组1): labline-framework + Gitea + 容器x3
服务器 B (小组2): labline-framework + 容器x3 (Gitea 指向 A 的)
服务器 C (小组3): labline-framework + 容器x3 (Gitea 指向 A 的)
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

### 模型/API 配置（容器内用 cc-switch-cli）

Labline 镜像预装 `cc-switch-cli`。不要把 OpenAI/Anthropic API key 预填到 `deploy/.env` 或 compose environment 里；多人服务器上这很容易造成凭据混用。每个用户进入自己的容器后配置自己的 provider。

```bash
# 进入自己的容器
docker exec -it labline-zhangsan bash

# 在容器内添加 provider。命令以你安装的 cc-switch-cli 版本为准：
cc-switch provider add --name "codex-main"
cc-switch provider list
cc-switch provider switch 1 --app codex
cc-switch provider switch 1 --app claude
```

### 需要 VPN/海外 IP

如果用 Anthropic 官方 API 或 Claude Coding Plan:

```env
# .env 里配代理。Labline 容器默认 host network，127.0.0.1 是宿主机。
LABLINE_PROXY_ENABLED=1
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
NO_PROXY=127.0.0.1,localhost,gitea
http_proxy=http://127.0.0.1:7897
https_proxy=http://127.0.0.1:7897
no_proxy=127.0.0.1,localhost,gitea
```

宿主机跑 Clash/V2Ray/mihomo 监听 `127.0.0.1:7897` 即可。entrypoint 会自动写入 `~/.proxy_env` 和 `/etc/environment`，`docker exec` 的 PAM 会话也能读取。

容器内验证：

```bash
docker exec -it labline-zhangsan bash
env | grep -i proxy
curl -I https://github.com
git ls-remote https://github.com/orangmood22-lgtm/Labline.git HEAD
```

如果 `curl` 能通但 `git ls-remote` 失败，再设置 git 专用代理：

```env
GIT_HTTP_PROXY=http://127.0.0.1:7897
GIT_HTTPS_PROXY=http://127.0.0.1:7897
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
docker exec -it labline-zhangsan bash -lc '
git config --global --unset http.proxy || true
git config --global --unset https.proxy || true
'
```

## 飞书远程控制部署

Codex + Claude Code 的飞书/Lark 远程控制默认推荐使用外部桥接器 `lark-channel-bridge`。它只是消息传输适配器：飞书负责收发消息，真正执行仍发生在本机或容器里的 Codex/Claude Code session；它不是 Labline Leader，不接管 workflow，也不是远程 shell。

前置要求：

- Node.js >= 20.12
- 容器或宿主机内已安装并登录 Codex CLI / Claude Code
- 飞书/Lark PersonalAgent app；首次启动可按上游 QR 引导绑定

安装：

```bash
lane feishu install
lane feishu doctor
```

在用户项目目录启动 Codex profile：

```bash
lane feishu run \
  --home ~/.lark-channel-[用户] \
  --profile [用户]-[项目] \
  --workspace [你的project位置]
```

服务器和容器里推荐放进 tmux：

```bash
tmux new-session -d -s feishu-[用户]-[项目] '
source ~/.proxy_env 2>/dev/null || true
cd [你的project位置]
lane feishu run --home ~/.lark-channel-[用户] --profile [用户]-[项目] --workspace [你的project位置]
'
```

Claude Code 使用独立 profile：

```bash
lane feishu run \
  --home ~/.lark-channel-[用户] \
  --profile [用户]-[项目]-claude \
  --agent claude \
  --workspace [你的project位置]
```

`lane feishu start` 会使用上游后台服务机制；桌面 Linux 可以用，服务器/root/Docker 环境如果缺 user systemd/dbus，就用 tmux + `lane feishu run`。

飞书/Lark 里常用命令：

| 命令 | 作用 |
|------|------|
| `/cd <path>` | 切换当前项目/workspace |
| `/ws` | 管理已保存 workspace |
| `/status` | 查看 profile、agent、工作目录、session 和运行状态 |

如果启动时没传 `--workspace`，或者要切到另一个 Labline 项目，在飞书里执行 `/cd [你的project位置]`。

### 旧版 Labline-managed runner

仓库内仍保留旧版 fallback 路径：

| 组件 | 路径 | 职责 |
|------|------|------|
| Feishu bridge | `mcp-servers/feishu-bridge/server.py` | HTTP 发送/更新卡片、长连接接收飞书消息、写入 session inbox |
| Feishu session runner | `tools/labline_feishu_session.py` | 消费 inbox，启动/恢复 Codex Session，把最终回复发回飞书 |

只有在你需要 Labline 管理的 inbox/outbox 文件、phone-session merge report、或 tmux live-TUI 注入时，才优先使用这条路径。

`.env` 里增加：

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_USER_ID=ou_xxx
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_ENABLE_WS=1
BRIDGE_PORT=5000
LABLINE_PROJECT_ROOT=[你的Labline总目录]/admin/framework
LABLINE_FEISHU_CONTROL_ROOT=
```

启动 bridge：

```bash
cd [你的Labline总目录]/admin/framework
python3 -m venv .venv-feishu
.venv-feishu/bin/pip install -r mcp-servers/feishu-bridge/requirements.txt
set -a; source deploy/.env; set +a
export FEISHU_ENABLE_WS=1
export LABLINE_PROJECT_ROOT=[你的Labline总目录]/admin/framework
.venv-feishu/bin/python mcp-servers/feishu-bridge/server.py
```

再启动受控 Codex session：

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root [你的Labline总目录]/admin/framework \
  --profile leader \
  --bridge-url http://127.0.0.1:5000 \
  --resume-last \
  --feishu-format card
```

部署注意：

- 默认优先使用 `lark-channel-bridge`；旧版 in-repo runner 是 fallback/Labline-managed runner。
- `BRIDGE_PORT` 默认是 `5000`；如果旧版 bridge 报 `Address already in use`，换端口并同步修改 `--bridge-url`。
- 飞书长连接需要服务器能访问飞书开放平台；如果连接不上，按上面的大小写 proxy 规则同时设置 `HTTP_PROXY/HTTPS_PROXY/http_proxy/https_proxy`。
- bridge 不执行 shell、tools、skills；真正执行发生在 opt-in 的本地 Codex/Claude session 或旧版 Codex session runner。
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
| Python/pip/Feishu SDK 不认代理 | 同时设置 `HTTP_PROXY/HTTPS_PROXY` 和 `http_proxy/https_proxy`，不要设置 `ALL_PROXY/all_proxy` |
| Feishu bridge `socket hang up` | `unset ALL_PROXY all_proxy`，确认 `~/.proxy_env` 只含 HTTP/HTTPS 代理 |
| 旧版 Feishu bridge 启动时报 `Address already in use` | 修改 `BRIDGE_PORT`，并同步修改 runner 的 `--bridge-url` |
| SSH 到 GPU 超时 | 检查 SSH key mount，`ls ~/.ssh/` |
| API 403/401 | 检查 key 是否过期，base_url 是否正确 |
| CUDA not available (GPU 服务器) | 检查 `LD_LIBRARY_PATH`，参考 exp0516 的 conda activate hook |
