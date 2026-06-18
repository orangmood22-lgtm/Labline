# 多 Provider 本地 Coding Agent 框架 Spike

> 状态: spike 草案
> 日期: 2026-06-17
> 结论先行: 短期优先 spike OpenCode；Aider 作为最快 fallback；goose / Cline SDK / OpenHands SDK / OpenClaw 进入中长期架构评估；LangGraph 用于 Labline workflow engine，不用于第一阶段 cheap coding worker。

## 0. 背景

`lane dev rt run` 当前只能调用远端 OpenAI-compatible chat API，然后把回复写入 `to-developer/logs/dev-runtime/.../response.md`。它不能读写本地仓库、不能调用 shell、不能跑测试、不能保证 write scope、不能输出可审 diff。

这说明 `dev rt` 只能保留为 **Developer Runtime Profile Surface**:

- provider / model / API key 配置
- 低风险 LLM 草案调用
- 非写入 prompt / response 日志

它不应该继续演化成 coding agent。Labline 需要新增独立的 **Developer Agent Surface**:

```bash
lane dev agent provider set ...
lane dev agent run ...
lane dev agent status ...
lane dev agent diff ...
lane dev agent apply ...
```

目标是把 cheap worker 从“远端补丁建议器”升级为“本地可写、可测试、可审查的开发 agent backend”。

## 1. Labline 需求

### 1.1 短期需求: 便宜模型写代码干杂活

最小闭环:

1. Codex 主控写清需求、write scope、验收测试。
2. cheap worker 在临时 git worktree 中改文件。
3. worker 跑指定测试。
4. Labline 收集 stdout、stderr、diff、实际修改文件列表。
5. Labline 检查修改是否超出 scope。
6. Codex 主控 review 后决定是否 apply / merge。

硬性要求:

- 支持 DeepSeek / OpenAI-compatible / OpenRouter 等低成本 provider。
- 支持 headless / CLI 非交互运行。
- 能读写本地文件、运行命令、生成 diff。
- 能限制 write scope 或至少由 Labline 后置审计 scope。
- 能禁用自动 commit。
- 能将测试命令纳入循环。
- 运行在临时 worktree，不能直接污染主 checkout。
- 不输出 API key 到 stdout、metadata、日志。

### 1.2 中长期需求: Labline 多 agent / workflow engine

长期不是只要一个 coding backend，而是要分层:

```text
Labline workflow layer
  - Leader / Planner / Coder / Reviewer / Integrity / Human checkpoint
  - 状态机、checkpoint、实验真实性验证、队列、审查

Agent orchestration layer
  - session lifecycle
  - worktree isolation
  - plan approval
  - merge / PR follow-through
  - multi-agent routing

Coding agent backend
  - OpenCode / Aider / goose / Cline / OpenHands / Codex / Claude Code

Provider layer
  - DeepSeek / OpenRouter / OpenAI / Anthropic / Gemini / local models
```

LangGraph 对应 workflow layer；OpenClaw 更接近 orchestration / gateway layer；OpenCode/Aider/goose/Cline/OpenHands 对应 coding backend 或 agent runtime。

## 2. 调研来源

本轮只采用官方文档、官方仓库或项目主页作为主依据:

- OpenCode docs: https://opencode.ai/docs
- OpenCode CLI docs: https://opencode.ai/docs/cli/
- OpenCode agents docs: https://opencode.ai/docs/agents/
- OpenCode permissions docs: https://opencode.ai/docs/permissions/
- OpenCode MCP docs: https://opencode.ai/docs/mcp-servers/
- OpenCode SDK docs: https://opencode.ai/docs/sdk/
- Aider docs: https://aider.chat/docs/
- Aider scripting docs: https://aider.chat/docs/scripting.html
- Aider lint/test docs: https://aider.chat/docs/usage/lint-test.html
- Aider other LLMs docs: https://aider.chat/docs/llms/other.html
- goose docs: https://goose-docs.ai/
- goose GitHub: https://github.com/aaif-goose/goose
- Cline docs: https://docs.cline.bot/cline-overview
- Cline SDK docs: https://docs.cline.bot/sdk/overview
- OpenHands SDK docs: https://docs.openhands.dev/sdk
- OpenHands CLI / LLM docs: https://docs.openhands.dev/openhands/usage/cli/command-reference
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- LangChain human-in-the-loop docs: https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- OpenClaw agent runtime docs: https://docs.openclaw.ai/concepts/agent-runtimes
- openclaw-code-agent: https://github.com/goldmar/openclaw-code-agent

## 3. 候选分层

### 3.1 Coding Backend

这些能直接承担“改代码、跑命令、产 diff”的候选:

- OpenCode
- Aider
- goose
- Cline CLI / SDK
- OpenHands SDK / CLI
- mini-swe-agent / SWE-agent

### 3.2 Orchestration / Gateway

这些更像 session / worktree / routing / approval 控制层:

- OpenClaw
- openclaw-code-agent
- LangGraph, if we build workflow ourselves

### 3.3 不建议作为第一选择

- open-codex: 维护活跃度和项目成熟度不足，不适合作为 Labline 新基座。
- fork OpenAI Codex CLI: 可行但不是第一步。Codex CLI 开源，但改 provider protocol、agent lifecycle、tool approvals 成本高，且容易追不上 upstream。

## 4. 候选评估

### 4.1 OpenCode

官方定位:

- 开源 coding agent，支持 terminal、desktop、IDE。
- 支持任意 provider，通过 Models.dev 覆盖 75+ providers。
- 支持 multi-session。
- CLI 有 `opencode run` 非交互命令。
- CLI 有 `opencode serve` headless server。
- CLI 有 `opencode acp`，支持 Agent Client Protocol。
- 支持 agent 配置，agent 可配置 system prompt、model、tool access。
- 支持 permission config，按 bash/edit/read 等工具设置 allow/ask/deny，且 edit 可按路径限制。
- 支持 MCP servers。
- 提供 JS/TS SDK，可启动 server 和 client，适合后续封装。

对 Labline 的价值:

- 最贴近短期目标。`opencode run --model provider/model --agent ... --file ... --format json --dir ...` 可以直接成为 `lane dev agent run` backend。
- permission 模型能表达 Labline write scope 的一部分，例如只允许编辑指定路径。
- `serve` + SDK 适合后续做长期常驻 worker pool。
- ACP 支持使它可以被 OpenClaw / editor / future Labline gateway 调度。
- MCP 支持让 Labline 后续把 research-wiki、experiment-integrity、status stream 暴露成工具。

风险:

- 需要实测 `opencode run` 在 `--format json` 下是否能稳定输出可解析事件。
- 需要实测 permission 的 path 规则是否足以限制写入，或者仍需 Labline 后置 `git diff --name-only` 审计。
- 需要实测 DeepSeek/OpenAI-compatible provider 的配置方式和模型名。
- 需要决定是否允许 `--dangerously-skip-permissions`。默认不允许；如果必须用，也只能在临时 worktree 中使用。

短期评级: **P0 / 首选**。

### 4.2 Aider

官方定位:

- terminal AI pair programmer。
- 命令行可指定要编辑的文件。
- 支持 `--message` / `--message-file` 脚本模式，执行一条任务后退出。
- 支持 `--yes` 自动确认、`--no-auto-commits` 禁止自动 commit、`--dry-run`。
- 支持 `--test-cmd` 和 `--auto-test`，测试失败后可尝试修复。
- 使用 LiteLLM 连接大量模型，支持 DeepSeek、OpenAI-compatible、OpenRouter 等。

对 Labline 的价值:

- 最快跑通。一个可行命令大概是:

```bash
aider \
  --model deepseek/deepseek-chat \
  --message-file /tmp/task.md \
  --yes \
  --no-auto-commits \
  --test-cmd "python -m pytest tests/test_developer_doc_dag.py -q" \
  tools/update_developer_docs.py tests/test_developer_doc_dag.py
```

- 非常适合“指定少量文件、做低风险改动、跑测试”的杂活。
- Python scripting API 存在，但官方明确不是稳定 API；短期应调用 CLI，不嵌 SDK。

风险:

- Aider 默认会 auto commit，需要明确关闭。
- 它是 pair programmer，不是多 agent runtime；session / worktree / approval 需要 Labline 自己包。
- permission 粒度弱于 OpenCode。虽然命令行指定 files，但仍需 Labline 后置检查实际 diff。
- 对复杂仓库上下文和大型任务，可能不如真正 coding-agent runtime。

短期评级: **P0 fallback / 最快可用**。

### 4.3 goose

官方定位:

- 本机 open source AI agent，提供 desktop、CLI、API。
- 不只做代码，也做 research、writing、automation、data analysis。
- GitHub README 写明支持 15+ providers，MCP 70+ extensions。
- 官方首页强调 recipes、MCP apps、subagents、security、tool permission controls、sandbox mode、adversary reviewer。
- 支持 ACP server，可连接 Zed、JetBrains、VS Code，并可使用 Claude Code / Codex 等 ACP agents 作为 providers。

对 Labline 的价值:

- 长期架构很贴合 Labline: MCP、subagents、permissions、sandbox、recipes 都对应我们想要的 workflow engine。
- 适合做本地 agent runtime，而不只是 coding worker。
- 可能成为 Labline 中长期 Developer Agent Runtime 的重要候选。

风险:

- 它是 general-purpose agent，不是纯 coding worker；短期“给我改这两个文件并跑测试”的摩擦可能高于 OpenCode/Aider。
- 需要实测 CLI headless、日志格式、DeepSeek/OpenAI-compatible provider、workdir/sandbox 行为。
- 如果输出不是稳定事件流，Labline 包装成本会提高。

短期评级: **P1**。

中长期评级: **P0/P1**。

### 4.4 Cline CLI / Cline SDK

官方定位:

- Cline 是 editor 和 terminal coding agent，可读写文件、运行命令、使用 browser，并需要显式 approval。
- Cline SDK 是其 agent core，可用于构建 agentic apps，是 Cline IDE extensions 和 CLI 使用的同一 harness。
- SDK 有 plugin architecture，支持 checkpoints、web fetch、MCPs、cron jobs、subagents。
- SDK 暴露 `@cline/core`、`@cline/agents`、`@cline/llms` 等包；需要 Node.js 22+。
- 官方博客称 provider layer 支持 Anthropic、OpenAI、Google、Bedrock、Mistral、LiteLLM、OpenAI-compatible endpoints。

对 Labline 的价值:

- SDK 化程度强，适合中长期直接构建 Labline dev-agent runtime。
- Approval / checkpoint / subagent / MCP / provider gateway 与 Labline 长期需求一致。
- 比 Aider/OpenCode 更像“我们可以嵌入的 agent harness”。

风险:

- 新 SDK / CLI 仍需实测成熟度。
- Node 22+ 和 TypeScript integration 会增加 Labline 当前 Python/shell tooling 的复杂度。
- 短期可能比 OpenCode/Aider 更慢。

短期评级: **P1**。

中长期评级: **P0/P1**。

### 4.5 OpenHands SDK / CLI

官方定位:

- Software Agent SDK 是 Python 和 REST APIs，用于构建能写软件的 agents。
- SDK 可用于 one-off tasks、routine maintenance、major multi-agent tasks。
- Agents 可用 local machine workspace，也可用 Docker/Kubernetes ephemeral workspaces。
- OpenHands CLI/Cloud/Web UI 消费同一 SDK。
- OpenHands 使用 LiteLLM provider 生态。

对 Labline 的价值:

- Python SDK 很适合长期和 Labline 直接集成。
- Ephemeral workspace / Docker / Kubernetes 方向对 Labline 实机测试和容器隔离有长期价值。
- 适合将来做“真正 Labline agent backend”，而不只是 CLI wrapper。

风险:

- 比 OpenCode/Aider 重。
- 需要更多 runtime / container / dependency 管理。
- Headless 模式和 approve 模式需要审慎验证；部分资料提到 headless 可能默认强自动化，必须放在受控 worktree/container 中。

短期评级: **P1/P2**。

中长期评级: **P1**。

### 4.6 OpenClaw / openclaw-code-agent

官方定位:

- OpenClaw 文档明确区分 provider、model、agent runtime、channel。
- Agent runtime 是执行 prepared model loop 的组件，provider 只是认证、发现模型和命名 model refs。
- OpenClaw 可以使用 embedded harness 或 CLI backend。
- `openclaw-code-agent` 管理 Claude Code、Codex、实验性 OpenCode 后台 coding sessions，并提供 plan approval、session lifecycle、wake routing、worktree isolation、merge/PR follow-through、goal loops、session output/status/cost 等。

对 Labline 的价值:

- 它不是短期 coding backend，而是很强的 orchestration layer。
- 它的概念模型非常接近 Labline 长期想要的:
  - plan -> review -> execute
  - delegated worktree isolation
  - session lifecycle
  - merge / PR follow-through
  - goal-task loops
  - routed summaries
  - session stats / cost
- `openclaw-code-agent` 已经把 OpenCode/Codex/Claude Code 等 harness 放到一个 control plane 下，这个方向与 Labline 的 `Leader -> worker backend` 目标高度一致。

风险:

- 它不是“把 DeepSeek 直接变成本地 coding agent”的底层答案；它仍依赖 Claude Code、Codex、OpenCode 等 harness。
- README 明确 OpenCode harness 还是 experimental。
- 对 Labline 来说引入 OpenClaw 可能比先接 OpenCode/Aider 更重。
- 如果我们先上 OpenClaw，可能先调通的是 orchestration，而不是最急需的 cheap coding worker。

短期评级: **不作为第一 backend；作为 OpenCode 后的 P1 orchestration spike**。

中长期评级: **P0/P1 orchestration layer**。

### 4.7 LangGraph / LangChain

官方定位:

- LangGraph 专注 agent orchestration 的底层能力: durable execution、streaming、human-in-the-loop 等。
- LangChain human-in-the-loop middleware 可在敏感 tool call 前 interrupt，等待人工决策。

对 Labline 的价值:

- LangGraph 很适合 Labline 长期 workflow engine:
  - Leader / Planner / Coder / Reviewer / Integrity / Human checkpoint
  - Checkpoint Queue
  - Experiment Integrity Verification
  - 状态持久化、恢复、人工介入
- 它不是 coding backend。每个 Coder node 仍需调用 OpenCode/Aider/goose/Cline/OpenHands/Codex/Claude Code。

风险:

- 先上 LangGraph 不能解决“便宜模型本地写代码”。
- 如果 backend 未定，workflow engine 会变成空壳。

短期评级: **暂缓**。

中长期评级: **P0 workflow engine**。

### 4.8 mini-swe-agent / SWE-agent

官方定位:

- SWE-agent 文档现在推荐 mini-swe-agent；更偏 issue-solving、benchmark、research harness。

对 Labline 的价值:

- 适合后续做统一 benchmark / eval backend。
- 可用于评估各 provider 在固定 issue 修复任务上的表现。

风险:

- 不适合第一阶段日常 framework maintenance worker。

评级: **P2**。

### 4.9 Continue

官方文档显示当前主仓库不再积极维护并 read-only。历史生态不错，但不适合作为 Labline 新 backend。

评级: **暂缓**。

## 5. 矩阵比较

| 候选 | 短期可用性 | 多 provider | Headless | 本地写代码 | 测试循环 | 权限/Scope | SDK/API | 长期架构价值 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| OpenCode | 高 | 高 | 高 | 高 | 中 | 高 | 高 | 高 | 首选短期 spike |
| Aider | 很高 | 高 | 高 | 高 | 高 | 中低 | 中 | 中 | 最快 fallback |
| goose | 中 | 高 | 待测 | 高 | 待测 | 高 | 中高 | 高 | 中长期重点 |
| Cline SDK | 中 | 高 | 待测 | 高 | 待测 | 高 | 很高 | 很高 | 中长期重点 |
| OpenHands SDK | 中低 | 高 | 中 | 高 | 待测 | 高 | 很高 | 高 | 较重，后置 |
| OpenClaw | 中 | 高 | 中 | 取决于 backend | 取决于 backend | 高 | 高 | 很高 | 编排层，不是首个 backend |
| LangGraph | 低 | 取决于集成 | 高 | 取决于 backend | 取决于 backend | 高 | 高 | 很高 | workflow engine，后置 |
| mini-swe-agent | 中低 | 中 | 高 | 高 | 高 | 中 | 中 | 中 | eval/benchmark 后置 |

## 6. 推荐短期路线

### 6.1 第一选择: OpenCode backend spike

理由:

- 官方 CLI 直接支持 `opencode run` 非交互。
- 支持 `--model provider/model`、`--agent`、`--file`、`--format json`、`--dir`。
- 支持 `opencode serve` 和 SDK，方便后续常驻 worker pool。
- 支持 permissions，可在 OpenCode 内部限制 bash/edit/read 等工具。
- 支持 MCP 和 ACP，和 Labline 后续工具生态兼容。
- 支持多 provider，是核心需求。

第一阶段不需要完全相信 OpenCode 的权限系统。Labline 仍应在外层强制:

- 临时 worktree
- `git diff --name-only` scope 审计
- 禁止自动 commit 到主分支
- 测试命令由 Labline 运行一次
- diff 由 Codex 主控 review

### 6.2 第二选择: Aider backend fallback

如果 OpenCode 的 provider 配置、JSON event、权限或 headless 行为卡住，就先落 Aider:

- `--message-file`
- `--yes`
- `--no-auto-commits`
- `--test-cmd`
- 指定文件列表

Aider 可在一两天内形成最小可用 worker，但中长期不要把 Labline 架构绑死在 Aider。

### 6.3 第三选择: goose smoke

goose 的长期价值高，但短期先只做 smoke:

- 能否 headless 跑一次 coding task
- 能否使用 DeepSeek/OpenAI-compatible
- 能否在指定 workdir 改文件
- 是否有稳定输出和权限控制

## 7. 推荐中长期路线

### 7.1 Phase 0: 立刻止损

- 保留 `lane dev rt` 为 provider/profile/key 管理。
- 明确文档: `dev rt run` 不是本地 coding agent。
- 所有 cheap coding work 改走 `lane dev agent`。

### 7.2 Phase 1: OpenCode 最小 backend

目标命令:

```bash
lane dev agent provider set deepseek-opencode \
  --backend opencode \
  --model deepseek/deepseek-v4-flash \
  --api-key-env DEEPSEEK_API_KEY

lane dev agent run dev-worker \
  --provider deepseek-opencode \
  --file tools/update_developer_docs.py \
  --file tests/test_developer_doc_dag.py \
  --test "python -m pytest tests/test_developer_doc_dag.py -q" \
  "实现 dev-runtime 日志排除，并补测试"
```

实现方式:

1. 创建 `git worktree add /tmp/lane-agent/<task> HEAD`。
2. 在 worktree 写入临时 `opencode.json`:
   - model
   - agent prompt
   - permission: edit 仅允许 scope 文件
   - bash 仅允许 test command / rg / sed / python pytest 等白名单
3. 调 `opencode run --dir <worktree> --agent dev-worker --format json ...`。
4. 收集 OpenCode 输出。
5. Labline 运行测试命令。
6. Labline 检查 `git diff --name-only` 是否超 scope。
7. 生成 `to-developer/logs/dev-agent/<task>/`:
   - task.md
   - backend.json
   - stdout.log
   - stderr.log
   - diff.patch
   - tests.log
   - metadata.json
8. Codex 主控 review 后手动 apply 或 merge。

验收:

- 能用 DeepSeek 改一个测试文件。
- 测试通过。
- scope 越权能被 Labline 拦住。
- API key 不进入日志。

### 7.3 Phase 2: Aider fallback backend

目标:

- 如果 OpenCode 卡住，Aider 先撑起本地 cheap worker。
- 也保留 Aider 作为简单文档/测试 patch backend。

实现:

```bash
aider \
  --model <model> \
  --message-file <task.md> \
  --yes \
  --no-auto-commits \
  --test-cmd "<test command>" \
  <scope files...>
```

Labline 外层同样负责 worktree、scope audit、test rerun、diff。

### 7.4 Phase 3: Agent backend abstraction

定义统一接口:

```yaml
backend:
  id: opencode
  command: opencode
  supports:
    headless: true
    json_events: true
    permissions: true
    mcp: true
    sdk: true
```

运行记录统一:

```json
{
  "schema_version": 1,
  "backend": "opencode",
  "provider": "deepseek-opencode",
  "model": "deepseek/deepseek-v4-flash",
  "worktree": "...",
  "scope": ["..."],
  "tests": ["..."],
  "status": "passed|failed|scope_violation|backend_error",
  "diff": "diff.patch"
}
```

### 7.5 Phase 4: OpenClaw / goose / Cline SDK / OpenHands SDK architecture spike

目的:

- 如果 Labline 需要长期 agent fleet、session lifecycle、human approval、worktree follow-through，OpenClaw 和 Cline SDK 的价值会上升。
- 如果 Labline 需要 Python-native agent framework 和 container workspace，OpenHands SDK 值得再看。
- 如果 Labline 需要 MCP-native desktop/CLI/API agent，goose 值得保留。

建议顺序:

1. OpenClaw + OpenCode: 看它能否把 OpenCode sessions 管起来。
2. Cline SDK: 看能否用 SDK 嵌入 Labline dev-agent runtime。
3. goose: 看 MCP/permissions/sandbox 是否比 OpenCode 更适合作为 Labline runtime。
4. OpenHands SDK: 看 Docker/Kubernetes ephemeral workspace 是否值得引入。

### 7.6 Phase 5: LangGraph workflow engine

等 coding backend 稳定后再上 LangGraph:

- Leader node: 和人交互、需求澄清、scope 制定
- Planner node: 自动计划草案
- Coder node: 调 `lane dev agent run`
- Reviewer node: 独立 review diff
- Test node: 运行测试
- Integrity node: 实验真实性 / 数据切分 / 指标透明度
- Human checkpoint node: 任意关键步骤可介入
- Merge node: apply / reject / rerun

LangGraph 管状态机，不直接写代码。

## 8. 实验任务设计

统一 smoke task:

> 修改 `tools/update_developer_docs.py`，让 `to-developer/logs/dev-runtime/**` 不参与 developer doc DAG 覆盖校验；补测试到 `tests/test_developer_doc_dag.py`；运行 `python -m pytest tests/test_developer_doc_dag.py -q`。

统一 scope:

- `tools/update_developer_docs.py`
- `tests/test_developer_doc_dag.py`

统一验收:

- `python -m pytest tests/test_developer_doc_dag.py -q` 通过。
- `python tools/update_developer_docs.py --check-only` 通过。
- `git diff --name-only` 只包含 scope 文件。
- diff 不包含 API key。
- backend 日志和 Labline metadata 可读。

## 9. 当前决策

短期最适合:

1. **OpenCode**: 主线。
2. **Aider**: fallback。
3. **goose**: 备选 smoke。

中长期:

1. **LangGraph**: Labline workflow engine。
2. **OpenClaw / openclaw-code-agent**: coding session orchestration / worktree lifecycle / approval / merge follow-through。
3. **Cline SDK**: 可嵌入 agent runtime。
4. **OpenHands SDK**: Python-native heavy agent workspace / container path。

下一步:

1. 写 `to-developer/plans/20260617-DEV_AGENT_SURFACE_PRD.md`。
2. 实现 OpenCode smoke script，不接入正式 CLI。
3. 用 DeepSeek 跑统一 smoke task。
4. 记录 smoke report。
5. 如果通过，再实现 `lane dev agent provider/run/status/diff` 最小版。
