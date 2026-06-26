# Labline 镜像打包与预构建部署

目标：把耗时、容易受网络影响的环境构建前移到一台可联网、可运行 Docker 的构建机。目标服务器只需要安装 Docker/NVIDIA Container Toolkit、拉取镜像、挂载目录，然后启动容器。

## 适用场景

- 多台服务器重复部署 Labline，不想每台机器现场 `docker build`。
- 目标服务器网络差，但能通过 registry 或离线 tar 包拿到镜像。
- 需要先验证一个“能用的容器环境”，再交给组内复用。

镜像只包含通用运行环境：系统包、Python/Node、Codex/Claude CLI、cc-switch、Python 科学栈、GPU 镜像中的 CUDA/PyTorch 栈。不要把 API key、SSH 私钥、项目数据、数据集打进镜像；这些一律在运行时通过 volume 或用户配置注入。

## 镜像类型

| 类型 | Dockerfile | Compose | 用途 |
|------|------------|---------|------|
| GPU 单用户 | `deploy/Dockerfile.gpu` | `deploy/docker-compose.gpu.image.yaml` | GPU 服务器上跑实验、PyTorch/CUDA、单用户长期容器 |
| 普通多人 | `deploy/Dockerfile` | `deploy/docker-compose.image.yaml` | 多人 SSH/文档/调度环境，实验仍可部署到外部 GPU |

现有 `docker-compose.gpu.yaml` 和 `docker-compose.yaml` 仍然保留现场 build 路径；新增的 `*.image.yaml` 只使用 `image:`，不会在目标服务器上 build。

## 构建并推送 GPU 镜像

在一台能联网、能跑 Docker 的构建机上执行：

```bash
cd /path/to/Labline

export IMAGE_REGISTRY=ghcr.io/your-org
export LABLINE_IMAGE_TAG=v0.1.0-cuda128
export LABLINE_GPU_IMAGE="$IMAGE_REGISTRY/labline-gpu:$LABLINE_IMAGE_TAG"

docker buildx build \
  --platform linux/amd64 \
  -f deploy/Dockerfile.gpu \
  -t "$LABLINE_GPU_IMAGE" \
  --build-arg LABLINE_BRANCH=main \
  --build-arg BUILD_HTTP_PROXY="${HTTP_PROXY:-}" \
  --build-arg BUILD_HTTPS_PROXY="${HTTPS_PROXY:-}" \
  --push \
  .
```

如果不用 registry，可以导出 tar 包：

```bash
docker build -f deploy/Dockerfile.gpu -t labline-gpu:v0.1.0-cuda128 .
docker save labline-gpu:v0.1.0-cuda128 | gzip > labline-gpu-v0.1.0-cuda128.tar.gz
```

目标服务器导入：

```bash
gunzip -c labline-gpu-v0.1.0-cuda128.tar.gz | docker load
```

## 构建并推送普通多人镜像

```bash
cd /path/to/Labline

export IMAGE_REGISTRY=ghcr.io/your-org
export LABLINE_IMAGE_TAG=v0.1.0
export LABLINE_IMAGE="$IMAGE_REGISTRY/labline:$LABLINE_IMAGE_TAG"

docker buildx build \
  --platform linux/amd64 \
  -f deploy/Dockerfile \
  -t "$LABLINE_IMAGE" \
  --build-arg LABLINE_BRANCH=main \
  --build-arg BUILD_HTTP_PROXY="${HTTP_PROXY:-}" \
  --build-arg BUILD_HTTPS_PROXY="${HTTPS_PROXY:-}" \
  --push \
  .
```

## 用预构建 GPU 镜像部署

目标 GPU 服务器上仍需满足：

- Docker 24+ 和 `docker compose` 可用。
- NVIDIA 驱动正常，宿主机 `nvidia-smi` 可用。
- NVIDIA Container Toolkit 可用，`docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi` 通过。

部署：

```bash
cd /path/to/Labline/deploy
cp .env.gpu.example .env
vim .env
```

至少设置：

```env
LABLINE_GPU_IMAGE=ghcr.io/your-org/labline-gpu:v0.1.0-cuda128
FRAMEWORK_PATH=/data/labline/users/you/framework
DEV_FRAMEWORK_PATH=/data/labline/admin/labline-dev
PROJECT_PATH=/data/labline/users/you/projects
DATASETS_PATH=/data/labline/shared/datasets
PRETRAINED_PATH=/data/labline/shared/pretrained
SSH_PATH=/home/you/.ssh
```

启动：

```bash
docker compose -f docker-compose.gpu.image.yaml pull
docker compose -f docker-compose.gpu.image.yaml up -d
docker exec -it labline-gpu bash
```

容器内验证：

```bash
nvidia-smi
python - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda", torch.cuda.is_available())
print("gpus", torch.cuda.device_count())
PY
lane project doctor /labline/framework
```

## 用预构建普通镜像部署多人环境

普通预构建镜像里的 Linux 用户是构建时固定的，默认是 `researcher`。使用 `docker-compose.image.yaml` 时，多用户隔离来自不同容器名和不同宿主机挂载目录；容器内用户名不随 `USER1_NAME` / `USER2_NAME` 改变。如果确实需要容器内 UID/GID/用户名与每个用户完全一致，继续使用现场 build 的 `docker-compose.yaml`，或为每个 UID 单独构建一份镜像。

```bash
cd /path/to/Labline/deploy
cp .env.example .env
vim .env
```

至少设置：

```env
LABLINE_IMAGE=ghcr.io/your-org/labline:v0.1.0
LABLINE_IMAGE_USERNAME=researcher
USER1_FRAMEWORK_PATH=/data/labline/users/zhangsan/framework
USER1_PROJECTS_PATH=/data/labline/users/zhangsan/projects
USER1_STATE_PATH=/data/labline/users/zhangsan/.labline
DATASETS_PATH=/data/labline/shared/datasets
PRETRAINED_PATH=/data/labline/shared/pretrained
DOWNLOADS_PATH=/data/labline/shared/downloads
```

启动：

```bash
docker compose -f docker-compose.image.yaml pull
docker compose -f docker-compose.image.yaml up -d
docker exec -it labline-zhangsan bash
```

## 版本与回滚

推荐镜像 tag 同时带上框架版本和运行栈信息：

```text
labline:v0.1.0
labline-gpu:v0.1.0-cuda128
labline-gpu:v0.1.0-cuda128-20260622
```

不要用裸 `latest` 作为生产部署默认值。升级时先改 `.env` 里的镜像 tag，再：

```bash
docker compose -f docker-compose.gpu.image.yaml pull
docker compose -f docker-compose.gpu.image.yaml up -d --force-recreate
```

回滚就是把 `.env` 中的镜像 tag 改回旧版本后重新 `pull/up`。

## 边界

预构建镜像能解决“构建慢、网络依赖多、每台机器重复安装”的问题，但不能替代宿主机权限：

- 目标服务器仍必须有可用 Docker daemon。
- GPU 目标服务器仍必须有宿主机 NVIDIA 驱动和 NVIDIA Container Toolkit。
- 如果 SSH 入口本身是无特权容器，且没有挂载宿主机 `/var/run/docker.sock`，预构建镜像也无法启动。
