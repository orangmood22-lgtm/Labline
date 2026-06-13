# ADR-0002: Agent Status Stream

**状态：** 已采纳  
**日期：** 2026-06-13  
**决策者：** orangmood + AI

## 上下文

ARIS 的 `leader` 可以派生 Coder、Deployer、Writer、Reviewer 等执行或审查角色，但当前主要依赖最终产物、`PIPELINE_STATE.json`、`MANIFEST.md`、`BLOCKED_REPORT.md` 和远程 watchdog 来恢复状态。这个模型对阶段完成后的恢复足够，但对运行中的 agent 可观测性不足：Leader 看不到 agent 当前在做什么、是否还活着、是否卡在前台 SSH / broken pipe、以及下一次合理检查时间，因此容易反复询问或过度轮询。

## 决策

ARIS 采用项目本地文件系统上的 **Agent Status Stream**：每个 agent 写自己的当前状态文件，Leader 默认只读压缩后的 **Agent Status Snapshot**，必要时再读取可选事件流或正式 trace。真实运行态属于研究项目的本地非版本化状态，默认位于项目内 `.aris/status/`，不提交到 Git；ARIS 框架仓库只提供工具、协议和测试，开发测试必须使用独立 tmp 目录。

状态通道第一版使用 per-agent snapshot，而不是全局共享可写 JSON、数据库、队列或 LangGraph runtime。长运行任务必须写入可独立检查的 job handle，例如 tmux/screen 会话、watchdog task、queue state、日志路径或结果目录。Leader 到达 expected update time 后可以自动做只读状态检查，但不得自动重启任务、部署代码、修改配置或变更项目产物。

Reviewer 是跨平台的审查角色，不等同于 Codex MCP。状态文件需要记录 reviewer transport（例如 `mcp_codex`、`mcp_gemini`、`background_agent`、`cli_session`、`external_api`），但 Reviewer 状态只能写元信息、输入范围、trace path 和 verdict artifact path，不能把审查推理或 Executor/Writer 转述塞进 snapshot，以免破坏 reviewer independence。

## 考虑的替代方案

1. **只维护 `PIPELINE_STATE.json`**：适合阶段恢复，不适合多个 agent 并发运行时的细粒度可观测性。
2. **单个全局 status JSON**：Leader 读取方便，但多个 agent 并发写入容易冲突，且容易变成隐式调度面。
3. **直接读完整事件流或 agent transcript**：信息最完整，但会污染 Leader 上下文，增加焦虑式轮询。
4. **数据库、消息队列或 LangGraph runtime**：更强的一致性和编排能力，但会增加依赖和迁移成本；当前 ARIS 仍优先稳定静态 skill/DAG/schema/event logging。
5. **让 agent 前台挂住 SSH / training 命令**：实现简单，但 broken pipe 或长任务前台阻塞会让 agent 无法更新状态。

## 后果

- 新增 `tools/agent_status.py` 作为本地状态文件读写工具；它不负责 SSH、watchdog、monitor 或部署。
- 新增 `skills/shared-references/agent-status-stream.md` 作为所有角色共享协议。
- `leader`、`coder`、`deployer`、`writer` 和 reviewer-aware skills 需要逐步写入或消费 Agent Status Snapshot。
- `.aris/status/` 是项目运行态，不进入 Git；框架测试通过 `--status-root` 或 tmp 目录隔离。
- `stale` 不是 agent 写入的状态，而是 Leader 根据 `last_updated`、`next_expected_update` 和 job handle 在读取时推导。
