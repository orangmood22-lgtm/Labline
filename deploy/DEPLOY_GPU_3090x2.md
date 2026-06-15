# ARIS GPU 部署指南 — 3090x2 服务器

> 目标：在 `3090x2-original` 上用 Docker 部署 ARIS 框架（GPU 版），运行 exp0516 实验。

## 前置条件

| 项目           | 要求              | 当前状态     |
| -------------- | ----------------- | ------------ |
| GPU            | NVIDIA 3090 x2    | ✅            |
| Driver         | 580+              | ✅ 580.159.03 |
| Docker         | 24.0+             | ✅ 29.2.1     |
| nvidia runtime | docker 能看到 GPU | ✅            |
| 代理           | clash 运行中      | 需手动开启   |
| 磁盘           | >20GB 可用        | ✅ 860GB      |

## Step 0: SSH 进服务器 + 开代理

```bash
ssh 3090x2-original
proxyon
```

验证代理工作：
```bash
curl -s --max-time 5 https://registry-1.docker.io/v2/ && echo "OK"
```

## Step 1: 准备构建目录

文件已经通过 rsync 传过去了，确认一下：

```bash
ls /workspace/Orangmood/ARIS/aris-framework/deploy/
# 应该看到：Dockerfile.gpu  docker-compose.gpu.yaml  .env.gpu.example  entrypoint.sh
```

如果没有，从本机重传：
```bash
# 在本机 WSL 执行：
rsync -avz deploy/ 3090x2-original:/workspace/Orangmood/ARIS/aris-framework/deploy/
rsync -avz templates/api-config.yaml.tmpl 3090x2-original:/workspace/Orangmood/ARIS/aris-framework/templates/
```

## Step 2: 配置 .env

```bash
cd /workspace/Orangmood/ARIS/aris-framework
cp deploy/.env.gpu.example deploy/.env
```

编辑 `deploy/.env`，填入你的 API key：

```bash
vim deploy/.env
```

需要改的字段：
```ini
# 必填（至少填一个才能用 Claude Code）
ANTHROPIC_API_KEY=sk-ant-xxx（或中转站 key）
ANTHROPIC_BASE_URL=https://your-proxy.com/v1（留空=官方）

# 可选（Codex Reviewer 用）
OPENAI_API_KEY=sk-xxx

# 3090x2 上 clash 当前跑在 7897 端口
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
http_proxy=http://127.0.0.1:7897
https_proxy=http://127.0.0.1:7897
# 只有 git pull/clone 仍失败时再填
GIT_HTTP_PROXY=http://127.0.0.1:7897
GIT_HTTPS_PROXY=http://127.0.0.1:7897

# 3090x2 host paths
FRAMEWORK_PATH=/workspace/Orangmood/ARIS/aris-framework
DEV_FRAMEWORK_PATH=/workspace/Orangmood/ARIS/aris-dev
PROJECT_PATH=/workspace/Orangmood/ARIS
DATASETS_PATH=/workspace/shared/datasets
```

其他字段默认值已经对了（USERNAME=orangmood, UID=1000, PROJECT_PATH=/workspace/Orangmood/ARIS）。

## Step 3: Build Docker 镜像

```bash
cd /workspace/Orangmood/ARIS/aris-framework

docker build -f deploy/Dockerfile.gpu -t aris-gpu \
  --build-arg BUILD_HTTP_PROXY=http://127.0.0.1:7897 \
  --build-arg BUILD_HTTPS_PROXY=http://127.0.0.1:7897 \
  --network host \
  .
```

> ⏱️ 首次构建约 15-30 分钟（拉 CUDA 镜像 + 装 PyTorch）。
> 
> 如果报错 `failed to resolve source metadata`：
> ```bash
> docker builder prune -af
> # 重新跑上面的 build 命令
> ```

构建成功最后会打印：
```
PyTorch X.X.X, CUDA available: True
```

## Step 4: 启动容器

```bash
docker run -d \
  --name aris-gpu \
  --hostname aris-gpu \
  --add-host aris-gpu:127.0.1.1 \
  --restart unless-stopped \
  --gpus all \
  --network host \
  -v /workspace/Orangmood/ARIS/aris-framework:/aris/framework \
  -v /workspace/Orangmood/ARIS/aris-dev:/aris/aris-dev \
  -v /workspace/Orangmood/ARIS:/aris/projects \
  -v /workspace/shared/datasets:/aris/shared/datasets:ro \
  -v /workspace/Orangmood/pretrained:/aris/shared/pretrained \
  -v /home/dell/.ssh:/run/secrets/ssh:ro \
  -e ANTHROPIC_API_KEY="$(grep ANTHROPIC_API_KEY deploy/.env | cut -d= -f2)" \
  -e ANTHROPIC_BASE_URL="$(grep ANTHROPIC_BASE_URL deploy/.env | cut -d= -f2)" \
  -e OPENAI_API_KEY="$(grep OPENAI_API_KEY deploy/.env | cut -d= -f2)" \
  -e HTTP_PROXY=http://127.0.0.1:7897 \
  -e HTTPS_PROXY=http://127.0.0.1:7897 \
  aris-gpu sleep infinity
```

## Step 5: 进容器

```bash
docker exec -it aris-gpu bash
```

## Step 6: 容器内验证

```bash
# GPU
nvidia-smi
python3 -c "import torch; print(f'GPUs: {torch.cuda.device_count()}, CUDA: {torch.cuda.is_available()}')"

# ARIS 框架
ls /aris/framework/skills/ | head -5
ls -ld /aris/aris-dev
bash /aris/framework/deploy/aris_gpu_doctor.sh --project exp0516 --project exp0603

# Claude Code
claude --version

# 项目文件和数据集
ls /aris/projects/exp0516/
ls -ld /aris/shared/datasets/VOCdevkit
```

## Step 7: 容器内安装 Skills 到 exp0516

exp0516 的 symlinks 指向本机路径，需重建：

```bash
cd /aris/projects/exp0516
bash /aris/framework/tools/install_aris.sh . --aris-repo /aris/framework --replace-link
```

验证：
```bash
ls -la .claude/skills/ | head -5
# 应该指向 /aris/framework/skills/...
```

## Step 8: 传数据集（从本机 WSL 执行）

```bash
# 回到本机 WSL
rsync -avz --progress \
  /root/Projects/aris/Auto-research-in-sleep/exp0516/VOC2007.tar.gz \
  /root/Projects/aris/Auto-research-in-sleep/exp0516/VOCdevkit_full.tar.gz \
  3090x2-original:/workspace/Orangmood/ARIS/exp0516/
```

约 5GB，取决于网速。

## Step 9: 容器内解压数据集

```bash
cd /aris/projects/exp0516
tar xzf VOC2007.tar.gz
tar xzf VOCdevkit_full.tar.gz
```

## Step 10: 开始使用

```bash
# 进入项目目录
cd /aris/projects/exp0516

# 启动 Claude Code
claude

# 或直接跑实验
python3 code/train.py
```

---

## 日常使用

### 启动（每次服务器重启后）

```bash
ssh 3090x2-original
proxyon
docker start aris-gpu
docker exec -it aris-gpu bash
```

### 停止

```bash
docker stop aris-gpu
```

### 重建（框架更新后）

```bash
docker stop aris-gpu && docker rm aris-gpu
cd /workspace/Orangmood/ARIS/aris-framework
git pull
docker build -f deploy/Dockerfile.gpu -t aris-gpu \
  --build-arg BUILD_HTTP_PROXY=http://127.0.0.1:7897 \
  --build-arg BUILD_HTTPS_PROXY=http://127.0.0.1:7897 \
  --network host .
# 然后重复 Step 4-7
```

### 容器内更新框架（不重建镜像）

```bash
# 容器内执行
cd /aris/framework && sudo git pull
cd /aris/projects/exp0516
bash /aris/framework/tools/install_aris.sh . --aris-repo /aris/framework --reconcile
```

---

## 故障排查

| 问题                          | 解决                                                                    |
| ----------------------------- | ----------------------------------------------------------------------- |
| `docker build` apt 报错       | 使用 `BUILD_HTTP_PROXY/BUILD_HTTPS_PROXY=http://127.0.0.1:7897`，Dockerfile 会覆盖 CUDA base image 里的旧代理 |
| `git pull` / `git clone` 失败 | 同时设置大小写 proxy；仍失败再设置 `git config --global http.proxy/https.proxy` |
| GPU 容器内看不到              | 检查 `--gpus all`，宿主机跑 `nvidia-smi` 确认驱动正常                   |
| Claude Code 报 401/403        | 检查 `ANTHROPIC_API_KEY` 是否正确传入，容器内 `echo $ANTHROPIC_API_KEY` |
| PyTorch 报 CUDA not available | 驱动版本和 CUDA 镜像版本不兼容，降级 Dockerfile 中的 CUDA 版本          |
| `install_aris.sh` 报错        | 确认 `/aris/framework/skills/` 存在且非空                               |
| 容器内网络不通                | `--network host` 应该继承宿主机网络，检查 clash 是否在跑                |
