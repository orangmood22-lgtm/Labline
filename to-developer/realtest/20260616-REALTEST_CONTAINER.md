# Labline 实机测试容器

本目录是 dev-only 测试资产，用于新功能在真实容器环境里的 smoke/integration 测试。它不属于 stable 管理员部署流程，也不应 promote 到 `main`。

## 目标

- 每个新功能有一个可重复的容器实测入口。
- framework checkout、临时项目目录、测试日志目录都由开发者显式指定。
- 测试日志写回主机目录，便于复查、贴给 reviewer、或纳入 release 证据。
- 默认 smoke 只验证 Labline CLI 基础链路：`framework --version`、`project init`、`project doctor`、`project update`。

## 文件

- `docker-compose.test.yaml`：专用测试容器编排。
- `.env.test.example`：测试环境变量模板。
- `test-runner.sh`：容器内统一 runner，负责创建时间戳日志目录并执行 smoke 或自定义命令。

## 使用

```bash
cp to-developer/realtest/.env.test.example to-developer/realtest/.env.test
```

编辑 `to-developer/realtest/.env.test`，至少填写：

```bash
TEST_FRAMEWORK_PATH=[你的framework位置]
TEST_PROJECTS_PATH=[你的实机测试项目临时目录]
TEST_LOGS_PATH=[你的实机测试日志目录]
```

运行默认 smoke：

```bash
docker compose --env-file to-developer/realtest/.env.test -f to-developer/realtest/docker-compose.test.yaml up --build labline-realtest
```

运行自定义命令：

```bash
LABLINE_REALTEST_COMMAND='python -m pytest tests/test_feishu_transport_docs.py -q' \
docker compose --env-file to-developer/realtest/.env.test -f to-developer/realtest/docker-compose.test.yaml up --build labline-realtest
```

日志写入 `TEST_LOGS_PATH`，并维护 `latest` 指向最近一次运行。

## 约束

- 不要把 `TEST_PROJECTS_PATH` 指到真实项目目录。
- 默认关闭自动更新检查：`LABLINE_AUTO_CHECK_UPDATE=0`，避免测试运行隐式修改 framework checkout。
- 数据集和预训练模型通过只读 mount 接入：`TEST_DATASETS_PATH`、`TEST_PRETRAINED_PATH`。
- 默认不支持容器内嵌套 Docker；需要 host docker socket 或 DinD 时，单独做显式扩展。
