# ARIS GPU 服务器部署新手指南

> 面向第一次部署 ARIS 的同学。
>
> 目标：在任意一台 Linux GPU 服务器上启动 `aris-gpu` Docker 容器，让容器能访问 GPU、ARIS framework、实验项目、共享数据集，并能运行 Codex CLI / Claude Code。
>
> 本文不是 3090x2 专用文档。3090x2 只作为一个示例；真实部署时请替换成你的服务器用户名、路径、项目名、代理端口。

## 1. 先确定你的部署变量

后续命令会用这些变量。先按你的服务器实际情况填好。

| 变量 | 含义 | 示例 |
|------|------|------|
| `SERVER` | SSH alias 或服务器地址 | `[你的服务器SSH别名]` |
| `HOST_USER` | 服务器上的 Linux 用户名 | `alice`、`dell`、`researcher` |
| `ARIS_ROOT` | 可选：你自己定义的 ARIS 总目录 | `[你的ARIS总目录]` |
| `FRAMEWORK_PATH` | 宿主机上的 ARIS framework 目录 | `[你的framework位置]` |
| `DEV_FRAMEWORK_PATH` | 可选开发版 framework 目录 | `[你的dev framework位置]` |
| `PROJECTS_ROOT` | 宿主机上的项目根目录 | `[你的项目工作区]` |
| `DATASETS_PATH` | 宿主机上的共享数据集目录 | `[你的数据集目录]` |
| `PRETRAINED_PATH` | 宿主机上的预训练模型缓存目录 | `[你的预训练模型目录]` |
| `SSH_PATH` | 宿主机上的 SSH key 目录 | `[你的SSH目录]` |
| `CONTAINER_NAME` | Docker 容器名 | `aris-gpu` |
| `CONTAINER_USER` | 容器内默认用户名 | `researcher`、`alice` |
| `USER_UID` | 容器用户 UID，通常与宿主机用户一致 | `1000` |
| `USER_GID` | 容器用户 GID，通常与宿主机用户一致 | `1000` |
| `HTTP_PROXY_URL` | 可选代理地址 | 空值、`http://127.0.0.1:7897` |
| `HTTPS_PROXY_URL` | 可选代理地址 | 空值、`http://127.0.0.1:7897` |

示例取值：

```bash
SERVER=[你的服务器SSH别名]
HOST_USER=[你的服务器用户名]
ARIS_ROOT=[你的ARIS总目录]
FRAMEWORK_PATH=[你的framework位置]
DEV_FRAMEWORK_PATH=[你的dev framework位置]
PROJECTS_ROOT=[你的项目工作区]
DATASETS_PATH=[你的数据集目录]
PRETRAINED_PATH=[你的预训练模型目录]
SSH_PATH=[你的SSH目录]
CONTAINER_NAME=aris-gpu
CONTAINER_USER=researcher
USER_UID=1000
USER_GID=1000
HTTP_PROXY_URL=
HTTPS_PROXY_URL=
```

建议把这些变量保存到一个临时文件，例如 `~/aris-deploy.env`：

```bash
cat > ~/aris-deploy.env <<'EOF'
SERVER=[你的服务器SSH别名]
HOST_USER=[你的服务器用户名]
ARIS_ROOT=[你的ARIS总目录]
FRAMEWORK_PATH=[你的framework位置]
DEV_FRAMEWORK_PATH=[你的dev framework位置]
PROJECTS_ROOT=[你的项目工作区]
DATASETS_PATH=[你的数据集目录]
PRETRAINED_PATH=[你的预训练模型目录]
SSH_PATH=[你的SSH目录]
CONTAINER_NAME=aris-gpu
CONTAINER_USER=alice
USER_UID=1001
USER_GID=1001
HTTP_PROXY_URL=
HTTPS_PROXY_URL=
EOF
source ~/aris-deploy.env
```

本文里有些命令在本机执行，有些命令在服务器执行。进入服务器后也要设置同一组变量，可以把这个文件复制到服务器再 `source`：

```bash
scp ~/aris-deploy.env "$SERVER:~/aris-deploy.env"
ssh "$SERVER"
source ~/aris-deploy.env
```

## 2. 理解宿主机路径和容器路径

部署后会同时存在两套路径：

| 内容 | 宿主机路径 | 容器内固定路径 |
|------|------------|----------------|
| Framework | `$FRAMEWORK_PATH` | `/aris/framework` |
| Dev framework | `$DEV_FRAMEWORK_PATH` | `/aris/aris-dev` |
| 项目根目录 | `$PROJECTS_ROOT` | `/aris/projects` |
| 共享数据集 | `$DATASETS_PATH` | `/aris/shared/datasets` |
| 预训练模型缓存 | `$PRETRAINED_PATH` | `/aris/shared/pretrained` |
| SSH key | `$SSH_PATH` | `/run/secrets/ssh` |

关键规则：

- 容器内访问 framework 永远用 `/aris/framework`。
- 容器内访问 dev framework 永远用 `/aris/aris-dev`。
- 容器内访问项目永远用 `/aris/projects/<project>`。
- 容器内访问共享数据集永远用 `/aris/shared/datasets/...`。
- 项目里的 `.agents/skills/*` 应该指向 `/aris/framework/skills/...`。
- Claude Code 兼容模式的 `.claude/skills/*` 也应该指向 `/aris/framework/skills/...`。
- 项目里的数据集 symlink 应该指向 `/aris/shared/datasets/...`。
- 不要在容器要用的 symlink 里写宿主机路径；容器内统一使用 `/aris/...`。
- API key 只放服务器本地的 `deploy/.env`，不要提交到 Git。

## 3. 前置条件

### 3.1 能 SSH 到服务器

在本机执行：

```bash
ssh "$SERVER"
```

如果失败，先检查：

- `SERVER` 是否配置在 `~/.ssh/config`。
- SSH key、端口、用户名是否正确。
- VPN、Clash TUN、校园网代理是否拦截了服务器内网域名。

### 3.2 服务器上有 Docker 和 GPU runtime

在服务器执行：

```bash
docker version
docker compose version
nvidia-smi
```

再检查 Docker 容器能不能看到 GPU：

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-devel-ubuntu22.04 nvidia-smi
```

如果这里看不到 GPU，先修 NVIDIA Container Toolkit。ARIS 容器本身无法绕过这个问题。

### 3.3 网络能下载依赖

构建镜像时需要访问：

- Ubuntu apt 源
- NodeSource
- npm registry
- PyPI / PyTorch wheel 源
- GitHub

不是每台服务器都有代理。分两种情况：

无代理，保持空值：

```bash
HTTP_PROXY_URL=
HTTPS_PROXY_URL=
```

有代理，填写服务器本机可访问的代理地址：

```bash
HTTP_PROXY_URL=http://127.0.0.1:7897
HTTPS_PROXY_URL=http://127.0.0.1:7897
export HTTP_PROXY="$HTTP_PROXY_URL"
export HTTPS_PROXY="$HTTPS_PROXY_URL"
export http_proxy="$HTTP_PROXY_URL"
export https_proxy="$HTTPS_PROXY_URL"
```

如果你填写了代理，先确认端口可连：

```bash
python3 - <<'PY'
import os, socket, urllib.parse
url = os.environ.get("HTTP_PROXY_URL", "")
if not url:
    print("no proxy configured")
    raise SystemExit(0)
u = urllib.parse.urlparse(url)
s = socket.socket()
s.settimeout(2)
try:
    s.connect((u.hostname, u.port))
    print("proxy open", url)
except Exception as e:
    print("proxy closed", url, repr(e))
finally:
    s.close()
PY
```

如果直连网络能用，不要为了“看起来完整”硬填代理。

如果 `curl` 能通但 `git clone` / `git pull` 仍失败，给 git 单独设置代理：

```bash
git config --global http.proxy "$HTTP_PROXY_URL"
git config --global https.proxy "$HTTPS_PROXY_URL"
git config --global --get-regexp 'http.*proxy'
```

切回直连时清理：

```bash
git config --global --unset http.proxy || true
git config --global --unset https.proxy || true
```

### 3.4 磁盘空间足够

ARIS GPU 镜像大约 18-20GB，数据集和实验输出可能更大。

```bash
df -h "$ARIS_ROOT" "$DATASETS_PATH" 2>/dev/null || df -h
docker system df
```

空间不足时，先人工确认旧容器/旧镜像是否还能删除：

```bash
docker ps -a
docker images
```

## 4. 准备服务器目录

在服务器上执行：

```bash
mkdir -p "$FRAMEWORK_PATH" "$DEV_FRAMEWORK_PATH" "$PROJECTS_ROOT" "$DATASETS_PATH" "$PRETRAINED_PATH"
```

确认项目目录存在。把 `exp0516`、`exp0603` 换成你的项目名：

```bash
ls -ld "$PROJECTS_ROOT/exp0516" "$PROJECTS_ROOT/exp0603"
```

确认数据集存在。以 VOC 为例：

```bash
ls -ld "$DATASETS_PATH/VOCdevkit"
```

如果需要从本机上传数据：

```bash
rsync -avz --progress /path/to/VOCdevkit_full.tar.gz "$SERVER:$DATASETS_PATH/"
ssh "$SERVER" "cd '$DATASETS_PATH' && tar xzf VOCdevkit_full.tar.gz"
```

## 5. 同步 ARIS framework 文件

在本机 ARIS stable framework 仓库执行：

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
```

同步部署文件。注意排除服务器本地 `.env`：

```bash
rsync -avz --exclude .env deploy/ "$SERVER:$FRAMEWORK_PATH/deploy/"
```

同步安装器、skills、templates：

```bash
ssh "$SERVER" "mkdir -p '$FRAMEWORK_PATH/tools' '$FRAMEWORK_PATH/skills' '$FRAMEWORK_PATH/templates'"
scp tools/install_aris.sh "$SERVER:$FRAMEWORK_PATH/tools/install_aris.sh"
rsync -avz skills/ "$SERVER:$FRAMEWORK_PATH/skills/"
rsync -avz templates/ "$SERVER:$FRAMEWORK_PATH/templates/"
```

如果你也要在服务器上开发 ARIS dev framework，同步本地 `aris-dev`：

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
  "$SERVER:$DEV_FRAMEWORK_PATH/"
```

说明：

- `deploy/.env` 应该只在服务器本地创建。
- 如果服务器上已经是完整 Git checkout，也可以用 `git pull`，但仍要确认没有覆盖本地 `.env`。
- 最低限度需要有：`deploy/`、`tools/install_aris.sh`、`skills/`、`templates/`。

## 6. 配置服务器本地 `.env`

在服务器执行：

```bash
cd "$FRAMEWORK_PATH"
cp deploy/.env.gpu.example deploy/.env
vim deploy/.env
```

按你的服务器改这些字段：

```ini
USERNAME=researcher
USER_UID=1000
USER_GID=1000

ANTHROPIC_API_KEY=
ANTHROPIC_BASE_URL=
OPENAI_API_KEY=

HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=127.0.0.1,localhost
http_proxy=
https_proxy=
no_proxy=127.0.0.1,localhost
GIT_HTTP_PROXY=
GIT_HTTPS_PROXY=

FRAMEWORK_PATH=[你的framework位置]
DEV_FRAMEWORK_PATH=[你的dev framework位置]
PROJECT_PATH=[你的项目工作区]
DATASETS_PATH=[你的数据集目录]
PRETRAINED_PATH=[你的预训练模型目录]
SSH_PATH=[你的SSH目录]
```

如果服务器需要代理：

```ini
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
http_proxy=http://127.0.0.1:7897
https_proxy=http://127.0.0.1:7897
# 只有 git 仍连不上外网时再填
GIT_HTTP_PROXY=http://127.0.0.1:7897
GIT_HTTPS_PROXY=http://127.0.0.1:7897
```

如果服务器不需要代理：

```ini
HTTP_PROXY=
HTTPS_PROXY=
```

API key 说明：

- `OPENAI_API_KEY` 给 Codex CLI 用。
- `ANTHROPIC_API_KEY` 给 Claude Code 兼容模式用。
- `ANTHROPIC_BASE_URL` 只在你使用中转站时填写。
- 不要把 `deploy/.env` 提交到 Git。
- 不要在截图、日志、文档里展示 key。

## 7. 构建 GPU 镜像

建议用 `tmux`，避免 SSH 断开导致构建中止：

```bash
ssh "$SERVER"
tmux new -s aris_gpu_build
```

进入 tmux 后：

```bash
cd "$FRAMEWORK_PATH"
```

有代理时：

```bash
docker build --progress=plain \
  -f deploy/Dockerfile.gpu \
  -t aris-gpu \
  --build-arg USERNAME="$CONTAINER_USER" \
  --build-arg UID="$USER_UID" \
  --build-arg GID="$USER_GID" \
  --build-arg BUILD_HTTP_PROXY="$HTTP_PROXY_URL" \
  --build-arg BUILD_HTTPS_PROXY="$HTTPS_PROXY_URL" \
  --network host \
  .
```

无代理时：

```bash
docker build --progress=plain \
  -f deploy/Dockerfile.gpu \
  -t aris-gpu \
  --build-arg USERNAME="$CONTAINER_USER" \
  --build-arg UID="$USER_UID" \
  --build-arg GID="$USER_GID" \
  --network host \
  .
```

构建完成后检查：

```bash
docker images | grep aris-gpu
```

期望看到 `aris-gpu` 镜像，大小通常约 18-20GB。

如果想后台构建并写日志，可以用：

```bash
cd "$FRAMEWORK_PATH"
tmux new-session -d -s aris_gpu_build \
  "bash -lc 'docker build --progress=plain -f deploy/Dockerfile.gpu -t aris-gpu --build-arg USERNAME=$CONTAINER_USER --build-arg UID=$USER_UID --build-arg GID=$USER_GID --network host . > deploy/build_aris_gpu.log 2>&1; echo EXIT:$? > deploy/build_aris_gpu.status'"
```

如果后台构建需要代理，再加上 `--build-arg BUILD_HTTP_PROXY=... --build-arg BUILD_HTTPS_PROXY=...`。

查看后台构建状态：

```bash
tmux ls | grep aris_gpu_build || true
cat "$FRAMEWORK_PATH/deploy/build_aris_gpu.status" 2>/dev/null || true
docker images | grep aris-gpu || true
```

## 8. 启动容器

在服务器执行：

```bash
cd "$FRAMEWORK_PATH"
mkdir -p "$PRETRAINED_PATH"
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
```

有代理时：

```bash
docker run -d \
  --name "$CONTAINER_NAME" \
  --hostname "$CONTAINER_NAME" \
  --add-host "$CONTAINER_NAME:127.0.1.1" \
  --restart unless-stopped \
  --gpus all \
  --network host \
  -v "$FRAMEWORK_PATH:/aris/framework" \
  -v "$DEV_FRAMEWORK_PATH:/aris/aris-dev" \
  -v "$PROJECTS_ROOT:/aris/projects" \
  -v "$DATASETS_PATH:/aris/shared/datasets:ro" \
  -v "$PRETRAINED_PATH:/aris/shared/pretrained" \
  -v "$SSH_PATH:/run/secrets/ssh:ro" \
  -e ANTHROPIC_API_KEY="$(awk -F= '$1=="ANTHROPIC_API_KEY"{print substr($0,index($0,"=")+1)}' deploy/.env)" \
  -e ANTHROPIC_BASE_URL="$(awk -F= '$1=="ANTHROPIC_BASE_URL"{print substr($0,index($0,"=")+1)}' deploy/.env)" \
  -e OPENAI_API_KEY="$(awk -F= '$1=="OPENAI_API_KEY"{print substr($0,index($0,"=")+1)}' deploy/.env)" \
  -e HTTP_PROXY="$HTTP_PROXY_URL" \
  -e HTTPS_PROXY="$HTTPS_PROXY_URL" \
  -e NO_PROXY=127.0.0.1,localhost \
  aris-gpu sleep infinity
```

无代理时：

```bash
docker run -d \
  --name "$CONTAINER_NAME" \
  --hostname "$CONTAINER_NAME" \
  --add-host "$CONTAINER_NAME:127.0.1.1" \
  --restart unless-stopped \
  --gpus all \
  --network host \
  -v "$FRAMEWORK_PATH:/aris/framework" \
  -v "$DEV_FRAMEWORK_PATH:/aris/aris-dev" \
  -v "$PROJECTS_ROOT:/aris/projects" \
  -v "$DATASETS_PATH:/aris/shared/datasets:ro" \
  -v "$PRETRAINED_PATH:/aris/shared/pretrained" \
  -v "$SSH_PATH:/run/secrets/ssh:ro" \
  -e ANTHROPIC_API_KEY="$(awk -F= '$1=="ANTHROPIC_API_KEY"{print substr($0,index($0,"=")+1)}' deploy/.env)" \
  -e ANTHROPIC_BASE_URL="$(awk -F= '$1=="ANTHROPIC_BASE_URL"{print substr($0,index($0,"=")+1)}' deploy/.env)" \
  -e OPENAI_API_KEY="$(awk -F= '$1=="OPENAI_API_KEY"{print substr($0,index($0,"=")+1)}' deploy/.env)" \
  aris-gpu sleep infinity
```

为什么最后是 `sleep infinity`：

- 镜像默认命令是 `bash`。
- detached 模式下 `bash` 没有交互输入会立刻退出。
- `sleep infinity` 让容器常驻，后续用 `docker exec` 进入。

检查容器：

```bash
docker ps --filter name="$CONTAINER_NAME"
```

## 9. 容器内验证

进入容器：

```bash
docker exec -it "$CONTAINER_NAME" bash
```

检查 GPU 和 PyTorch：

```bash
nvidia-smi
python3 - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda", torch.cuda.is_available())
print("gpus", torch.cuda.device_count())
PY
```

合格标准：

```text
cuda True
gpus >= 1
```

检查挂载：

```bash
ls -ld /aris/framework
ls -ld /aris/aris-dev
ls -ld /aris/projects
ls -ld /aris/shared/datasets
```

检查 CLI：

```bash
codex --version
claude --version
```

运行部署健康检查。把项目名换成你自己的：

```bash
bash /aris/framework/deploy/aris_gpu_doctor.sh --project exp0516 --project exp0603
```

期望：

```text
OK exp0516 skills
OK exp0516 dataset
OK exp0603 skills
OK exp0603 dataset
```

注意：当前 doctor 的数据集检查面向 VOC 项目，会检查 `data/VOCdevkit`。如果你的项目不用 VOC，可以只参考 skills 检查，或扩展 doctor。

验证 dev framework 可被 `--dev` 自动发现：

```bash
tmp=$(mktemp -d)
bash /aris/framework/tools/install_aris.sh "$tmp" --dev --quiet --no-doc
cat "$tmp/.aris/framework-version.txt" 2>/dev/null || true
rm -rf "$tmp"
```

如果 dev framework 还没有实际 skill 目录，可能看到 `warning: skipping unsafe upstream name: *`。这表示 `skills/` 目前只有占位文件，等你加入第一个 dev skill 后 warning 会消失。

## 10. 修复项目链接

### 10.1 修复 skills

如果 doctor 报：

```text
FAIL <project> skills: stale target outside framework
```

在容器内执行：

```bash
cd /aris/projects/YOUR_PROJECT
bash /aris/framework/tools/install_aris.sh . --aris-repo /aris/framework --quiet --no-doc
```

检查：

```bash
ls -la /aris/projects/YOUR_PROJECT/.agents/skills | head
# Claude Code 兼容模式：
ls -la /aris/projects/YOUR_PROJECT/.claude/skills | head
```

目标应该是：

```text
/aris/framework/skills/...
```

### 10.2 修复数据集 symlink

如果项目使用共享 VOC：

```bash
rm -f /aris/projects/YOUR_PROJECT/data/VOCdevkit
mkdir -p /aris/projects/YOUR_PROJECT/data
ln -s /aris/shared/datasets/VOCdevkit /aris/projects/YOUR_PROJECT/data/VOCdevkit
```

不要指向宿主机路径。容器内应使用：

```text
/aris/shared/datasets/VOCdevkit
```

## 11. 日常使用

启动：

```bash
ssh "$SERVER"
docker start "$CONTAINER_NAME"
docker exec -it "$CONTAINER_NAME" bash
```

停止：

```bash
docker stop "$CONTAINER_NAME"
```

看日志：

```bash
docker logs --tail 100 "$CONTAINER_NAME"
```

进入项目：

```bash
docker exec -it "$CONTAINER_NAME" bash
cd /aris/projects/YOUR_PROJECT
```

跑 doctor：

```bash
docker exec "$CONTAINER_NAME" bash -lc 'bash /aris/framework/deploy/aris_gpu_doctor.sh --project exp0516 --project exp0603'
```

查看 dev framework：

```bash
docker exec -it "$CONTAINER_NAME" bash
cd /aris/aris-dev
git status --short --branch
```

## 12. 常见问题与解决

### 12.1 SSH 在握手前断开

现象：

```text
Connection lost before handshake
Socket ended
```

常见原因：

- VPN 或 Clash TUN 把内网服务器流量送到了公网代理节点。
- fake-IP DNS 规则导致 SSH 走错路。

解决：

- 给服务器域名/IP 加 DIRECT 规则。
- 如果使用 Clash fake-IP，给内网域名加 fake-ip-filter。
- 修改规则后刷新 DNS 缓存。

### 12.2 Docker build 访问 `172.17.0.1:10808`

现象：

```text
Could not connect to 172.17.0.1:10808
E: Failed to fetch http://archive.ubuntu.com/...
```

原因：

- Docker daemon 或 CUDA base image 里残留旧代理。

解决：

- 使用当前版本的 `deploy/Dockerfile.gpu`。
- 有代理时显式传：

```bash
--build-arg BUILD_HTTP_PROXY=http://host:port
--build-arg BUILD_HTTPS_PROXY=http://host:port
```

- 无代理时不要传 build proxy args。

### 12.3 容器反复 Restarting

现象：

```bash
docker ps -a --filter name="$CONTAINER_NAME"
# Restarting (0)
```

原因：

- detached 模式启动默认 `bash`，它马上退出。

解决：

启动容器时最后使用：

```bash
aris-gpu sleep infinity
```

### 12.4 容器内没有 `/aris/framework`

原因：

- 启动容器时漏挂 framework。

解决：

启动命令必须包含：

```bash
-v "$FRAMEWORK_PATH:/aris/framework"
```

### 12.5 skills 指向旧路径

现象：

```text
FAIL PROJECT skills: stale target outside framework
```

解决：

```bash
cd /aris/projects/YOUR_PROJECT
bash /aris/framework/tools/install_aris.sh . --aris-repo /aris/framework --quiet --no-doc
```

### 12.6 数据集链接宿主机可用、容器内不可用

原因：

- symlink 指向宿主机路径。

解决：

```bash
rm -f /aris/projects/YOUR_PROJECT/data/VOCdevkit
ln -s /aris/shared/datasets/VOCdevkit /aris/projects/YOUR_PROJECT/data/VOCdevkit
```

### 12.7 `sudo: unable to resolve host`

原因：

- 容器 hostname 不在 `/etc/hosts`。

解决：

启动容器时加：

```bash
--hostname "$CONTAINER_NAME"
--add-host "$CONTAINER_NAME:127.0.1.1"
```

### 12.8 `docker exec` 提示容器正在 restarting

检查：

```bash
docker logs --tail 100 "$CONTAINER_NAME"
docker inspect "$CONTAINER_NAME" --format 'Exit={{.State.ExitCode}} Error={{.State.Error}} Restarting={{.State.Restarting}}'
```

如果 exit code 是 `0`，通常是默认 `bash` 退出，按 12.3 重新创建容器。

## 13. 验收清单

宿主机：

```bash
docker ps --filter name="$CONTAINER_NAME" --format "{{.Names}} {{.Status}} {{.Image}}"
docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | grep '^aris-gpu'
```

容器内：

```bash
docker exec "$CONTAINER_NAME" bash -lc '
python3 - <<PY
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "gpus", torch.cuda.device_count())
PY
claude --version
codex --version
'
```

项目检查：

```bash
docker exec "$CONTAINER_NAME" bash -lc 'bash /aris/framework/deploy/aris_gpu_doctor.sh --project exp0516 --project exp0603'
```

合格标准：

```text
容器是 Up
aris-gpu 镜像存在
torch cuda True
gpus >= 1
Claude Code 能打印版本
Codex CLI 能打印版本
项目 doctor 对 skills 和 datasets 返回 OK
```
