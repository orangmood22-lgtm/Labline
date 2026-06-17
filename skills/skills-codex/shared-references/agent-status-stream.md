# Agent Status Stream

每个派生 agent 写自己的当前状态快照，Leader 只读汇总。状态流不是任务队列，也不是 agent 聊天室。

## 默认路径

```text
.aris/status/agents/<agent_id>.json
```

优先使用项目内工具写状态：

```bash
.aris/tools/agent_status.py start --agent-id coder-001 --role coder --task "implement evaluator"
.aris/tools/agent_status.py update --agent-id coder-001 --status running --current-action "checking tests"
.aris/tools/agent_status.py finish --agent-id coder-001 --status done --current-action "completed"
```

长任务必须写 durable job handle，例如 tmux/screen/session/queue/log/result dir。

Leader 可在 `next_expected_update` 后做只读检查，但不得通过状态流自动重启任务、杀进程、部署代码、改配置或改项目产物。
