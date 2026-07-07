# Agent Status Stream

每个派生 agent 写自己的当前状态快照，Leader 只读汇总。状态流不是任务队列，也不是 agent 聊天室。

## 默认路径

```text
.labline/runtime/agents/<agent_id>.json
```

旧项目里的 `.labline/status/agents/` 只作为兼容读取路径。新状态必须写到 `.labline/runtime/agents/`。

优先使用项目内工具写状态：

```bash
.labline/tools/agent_status.py start --agent-id coder-001 --role coder --task "implement evaluator"
.labline/tools/agent_status.py update --agent-id coder-001 --status running --current-action "checking tests"
.labline/tools/agent_status.py finish --agent-id coder-001 --status done --current-action "completed"
```

长任务必须写 durable job handle，例如 tmux/screen/session/queue/log/result dir。

Leader 可在 `next_expected_update` 后做只读检查，但不得通过状态流自动重启任务、杀进程、部署代码、改配置或改项目产物。

## 飞书 / Lark 远控规则

飞书卡片只是 Remote Status Projection，不是运行时 owner。预计超过 3 分钟的安装、编译、下载、训练、部署、批量评估或长时间 `wait_agent` 都是长任务。

- 长任务启动前必须写 Agent Status Snapshot 或 Runtime Task：`current_action`、durable `job_handles`、日志/结果路径、`next_expected_update`、`next_check_reason`。
- Leader 最多短等一次即时失败，最长 120 秒；任务仍在跑时必须结束当前 turn，告诉用户 task id、状态路径、日志路径和后续用 `/status`/`/follow` 查询。
- 普通进度只 patch/节流；只有 `completed`、`failed`、`cancelled`、`blocked`、`need_decision`、`anomaly` 或 heartbeat escalation 才发新的可见回复。
- 健康 heartbeat 只写本地 runtime state，不刷屏。
