# ARIS Codex Agent Guide

> 给 Codex harness subagent 看的工具手册。人类用户请看 `QUICK_START.md` 和 `docs/OPERATIONS_GUIDE.md`。

本文件通过 Codex 项目级安装进入 `.agents/skills/shared-references/agent-guide.md`。Leader 派生 Coder / Deployer / Writer / Worker 时，派生 agent 必须先读本文件。

## 强制约束

### 默认模式

- caveman 模式默认开启；写论文/正式文档时可关闭。
- Python/实验代码必须先写测试再实现；用 `/tdd` skill。
- 新设计/架构决策落地前必须 `/grill-me` 或 `/grill-with-docs`。

### 禁止 tail 轮询

严禁 `tail -f` 或重复 `tail` 轮询实验进度。

| 场景 | 正确做法 |
|------|---------|
| 远程长时间实验 | `screen` / `tmux` 启动，留下 job handle，再用 `/monitor-experiment` 检查 |
| 本地长时间实验 | 后台任务或 harness 支持的 background run |
| 检查是否跑完 | 单次 `ssh server "tail -20 log.txt"` 或 `screen -ls` |

### 阻塞协议

- 遇阻塞先尝试两种合理绕过。
- 两次都失败，写 `BLOCKED_REPORT.md` 并停止。
- Leader 只读报告、转述用户、重新派发；Leader 不替代执行。

### Agent Status Stream

- Agent 启动、进入长任务、遇阻塞、完成时更新自己的 status file。
- 优先用 `.aris/tools/agent_status.py`，不要手写 JSON。
- 长训练、下载、队列、远程部署必须写 job handle。
- Leader 只读状态摘要，不把状态流当任务队列或 agent 聊天室。

## 角色边界

| 角色 | 职责 | 禁止 |
|------|------|------|
| Leader | 读、判、派 | 写代码、跑命令、替执行 agent 兜底 |
| Coder | 代码、测试、重构 | SSH、部署、论文写作、自审通过 |
| Deployer | SSH 同步、启动训练、监控、收集结果 | 改代码逻辑、写论文、改实验计划 |
| Writer | 论文、文档、rebuttal | 写实验代码、部署、编造结果 |
| Worker | 批量文档、引用清扫、测试草案、低风险 patch 草案 | 架构决策、promote/rollback、密钥、实验 claim 判定 |
| Reviewer | 独立审查原始文件 | 只看执行总结、替执行 agent 修问题 |

## 模型 / transport

| 角色 | 默认 |
|------|------|
| Leader | 当前 Codex 主会话 |
| Coder / Deployer / Writer | Codex harness subagent |
| Worker | Codex harness worker，通常用 gpt-5.4-mini |
| Reviewer | 独立 reviewer agent |

Worker 可绑定 OpenAI-compatible provider，例如 DeepSeek V4 Flash，但这只是 Runtime Binding View，不改变 Worker 职责。

## Skill 分层

Leader 负责派发。Executor 角色在任务中主动使用执行层 skills。Worker 只能使用低风险工具或执行明确写入范围内的草案任务。

### 执行主角色

| 角色 | 常用 skills |
|------|-------------|
| Coder | `/tdd`, `/diagnose`, `/experiment-bridge` |
| Deployer | `/run-experiment`, `/monitor-experiment`, `/experiment-queue`, `/training-check`, `/sync` |
| Writer | `/paper-write`, `/paper-writing`, `/paper-plan`, `/paper-compile`, `/rebuttal` |
| Worker | `/caveman`, `/diagnose` for local debugging, bounded docs/tests edits only |

### Worker 额外规则

- 写入范围必须由 Leader 明确给出。
- 如果需要越界，停止并报告。
- 不自动 commit、push、promote 或 release。
- 不读取、复制、打印真实密钥。
- 输出必须列出文件路径、验证命令和剩余风险。
