# Labline 工具索引

本文只列用户和集成器可以依赖的稳定入口。开发者实验命令、ADR 和临时维护脚本放在 `to-developer/`。

## 项目 CLI

| 命令 | 用途 |
|------|------|
| `lane project init PATH --direction "..."` | 初始化或接入一个 Labline 项目 |
| `lane project doctor` | 检查当前项目的 Labline 基础文件 |
| `lane project update` | 刷新当前项目的 framework symlink 和安装记录 |
| `lane framework update` | 更新当前用户的 framework copy |

## Runtime CLI

| 命令 | 用途 |
|------|------|
| `lane runtime init` | 初始化项目内 `.labline/runtime/` 状态根 |
| `lane runtime task create ...` | 创建 Runtime Task |
| `lane runtime task update ...` | 更新 Runtime Task |
| `lane runtime task complete TASK_ID` | 标记 Runtime Task 完成 |
| `lane runtime task fail TASK_ID` | 标记 Runtime Task 失败 |
| `lane runtime task cancel TASK_ID` | 标记 Runtime Task 取消 |
| `lane runtime event append --type TYPE` | 追加 runtime 事件 |
| `lane runtime lease acquire SCOPE --owner OWNER --ttl SECONDS --purpose TEXT` | 获取控制 lease |
| `lane runtime lease release SCOPE --owner OWNER` | 释放控制 lease |
| `lane runtime intent submit ...` | 提交控制意图 |
| `lane runtime summarize` | 生成当前 runtime 摘要 |
| `lane workflow foreground-review TASK_ID --agent-id ID --prompt-file PATH --verdict-artifact PATH` | 用前台 `codex exec` 运行 Reviewer gate，并写入 `cli_session` handle、agent status 和 verdict artifact 门禁结果 |
| `lane workflow tmux-job TASK_ID --agent-id ID --session NAME --command CMD --log PATH` | 为长训练/部署启动 tmux job，并写入真实 job handle、agent status、job record 和日志路径 |

Runtime Task 写入命令支持以下稳定字段：`--next-expected-update` 声明下一次可观测时间，`--required-artifact PATH` 声明终态成功必须存在的产物，Reviewer 终态成功额外使用 `--verdict-artifact PATH`，重试任务使用新的 `TASK_ID` 并通过 `--retry-of OLD_TASK_ID` 链回旧尝试。缺少这些字段或路径时，runtime 校验器会拒绝对应创建、更新或终态成功。

`lane workflow foreground-review` 适合短时 Reviewer gate 或重试诊断：启动前会把 `cli_session` job handle 写入 Runtime Task 和 `.labline/runtime/agents/<agent_id>.json`，子 Codex 结束后只有在返回码为 0 且 `--verdict-artifact` 存在时才把 task 标为 completed；否则标为 failed，并把原因记录为执行失败或缺 verdict artifact。`TASK_ID` 应使用 `task-reviewer-...` 这类不会与派生 agent status task `agent:<agent_id>` 撞名的 id。

`lane workflow tmux-job` 适合长时间训练、部署和批量实验：命令会先检查 tmux session 未占用，启动 session 后写 `.labline/runtime/jobs/<job_id>.json`、Runtime Task `job_handles`、`.labline/runtime/agents/<agent_id>.json` 和 `job.started` 事件。它只证明进程已可观测托管，不自动声明实验成功；后续仍要由 Leader/heartbeat 根据 log、session 和 `--required-artifact` 判定完成、失败或继续等待。`TASK_ID` 同样应使用 `task-deployer-...` / `task-train-...` 这类不会与 `agent:<agent_id>` 派生状态撞名的 id。

## 状态和心跳

| 命令 | 用途 |
|------|------|
| `lane status --json` | 输出机器可读项目状态聚合 |
| `lane status --brief` | 输出人类可读项目状态摘要 |
| `lane heartbeat` | 检查 due task，正常平台期只写本地状态 |
| `lane heartbeat --dry-run` | 预览 heartbeat 动作，不写 runtime |
| `lane heartbeat --task TASK_ID` | 只检查指定 task |

## 本地 Debug / Smoke

| 命令 | 用途 |
|------|------|
| `lane debug runtime-smoke --project PATH` | 复制项目到本地临时工作目录，按 runtime/heartbeat/Feishu projection 清单做安全 smoke 测试 |
| `lane debug runtime-smoke --project PATH --json` | 输出机器可读 smoke 报告 |
| `lane debug runtime-smoke --project PATH --in-place --yes` | 在目标项目原地执行 smoke；会写 `.labline/runtime/`，只在明确需要时使用 |
| `lane debug longtask-smoke --project PATH` | 复制项目并启动真实本地长任务进程，验证 detached Runtime Task、running heartbeat 和 terminal escalation |
| `lane debug longtask-smoke --project PATH --json` | 输出机器可读长任务 smoke 报告 |

默认 copy 模式不会改源项目。报告写到 `$LABLINE_WORKSPACE/.labline/debug/runtime-smoke/<timestamp>-<project>/debug-report.{json,md}`，并包含每个检查项的 pass/fail、工作副本路径、bridge fake state 路径和失败原因。
长任务 smoke 报告写到 `$LABLINE_WORKSPACE/.labline/debug/longtask-smoke/<timestamp>-<project>/debug-report.{json,md}`；测试输出在工作副本的 `outputs/labline-debug-longtask/` 下。

## 飞书 / Lark

| 命令或工具 | 用途 |
|------|------|
| `lane feishu install` | 安装推荐的 `lark-channel-bridge` |
| `lane feishu run` | 前台运行 bridge，适合首次配置和 tmux 常驻 |
| `lane feishu start` | 使用 bridge 后台服务机制启动 |
| `lane feishu status` | 查看 bridge 运行状态 |
| `lane feishu logs --tail 50` | 查看 bridge 日志 |
| `tools/labline_remote_observation.py` | bridge / 集成器使用的 Remote Observation helper；普通用户通常不直接运行 |

`tools/labline_remote_observation.py` 的状态是 bridge-owned：它保存飞书 chat/open id、消息 archive、订阅和投递记录，包括可更新投影状态卡的 `message_id`。项目 `.labline/runtime/` 只保存 archive ref、task id、路由诊断和控制意图，不保存远程身份或消息正文。
