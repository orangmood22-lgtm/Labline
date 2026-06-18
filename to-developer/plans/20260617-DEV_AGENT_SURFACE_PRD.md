# Developer Agent Surface PRD

> 状态: PRD 草案  
> 创建时间: 2026-06-17  
> 适用范围: `to-developer/` dev-only；不进入 stable 用户侧文档  
> 依赖调研: `to-developer/plans/20260617-MULTI_PROVIDER_AGENT_FRAMEWORK_SPIKE.md`

## 0. 结论

短期最适合 Labline 的 cheap coding worker 后端是 **OpenCode**；**Aider** 作为最快 fallback。

原因很直接:

- OpenCode 已有 `opencode run` 非交互入口、`--format json` 事件输出、`--dir` 工作目录、`--model provider/model`、agent 配置、permission 配置、`serve` headless server、JS/TS SDK、MCP 和 ACP 支持。
- Aider 的脚本模式更成熟，`--message-file`、`--yes`、`--no-auto-commits`、`--test-cmd` 足够快速跑通“指定文件改代码 + 测试”的杂活闭环。
- LangGraph 适合 Labline 长期 workflow engine，但不是 coding backend；先上 LangGraph 不能解决 cheap worker 本地改代码。
- OpenClaw / openclaw-code-agent 更像 coding session orchestration / worktree follow-through 控制层，不是第一阶段“接便宜模型写代码”的最小答案。
- Cline SDK / OpenHands SDK 长期价值高，但第一阶段引入成本高于 OpenCode/Aider。

因此路线定为:

1. `lane dev rt` 保留为 provider/profile/key 管理和低风险 LLM 草案调用。
2. 新增 `lane dev agent ...`，专门负责本地 coding worker。
3. Phase 1 先实现 OpenCode smoke，不直接做大框架。
4. OpenCode 卡住时立刻用 Aider fallback 跑通最小可用闭环。
5. backend 稳定后，再评估 OpenClaw / Cline SDK / OpenHands SDK / LangGraph。

## 1. 背景问题

现有 `lane dev rt run` 只能调用 OpenAI-compatible API，然后把模型回复写入日志。它没有本地文件写入能力、没有 shell 工具、没有测试循环、没有 diff 和 scope 审计，也没有接入 Codex harness 的本地 agent 生命周期。

这导致 DeepSeek 这类便宜模型现在只能当“补丁建议器”，不能真正替代本地 agent 干杂活。

Labline 需要的不是把 `dev rt` 强行扩展成 agent，而是新增一个明确边界的 **Developer Agent Surface**。

## 2. 术语

- **Developer Runtime Surface**: `lane dev rt ...`。管理 provider、model、API key env、prompt/response 日志和简单 LLM 调用。
- **Developer Agent Surface**: `lane dev agent ...`。管理能读写本地 worktree、运行命令、产出 diff、跑测试、可审查的 coding worker。
- **Provider**: 模型服务来源，如 DeepSeek、OpenRouter、OpenAI-compatible endpoint。
- **Backend**: 真正执行 coding agent loop 的工具，如 OpenCode、Aider、goose、Cline SDK、OpenHands SDK。
- **Workflow Engine**: Labline 未来的状态机/人介入/实验真实性/多角色编排层，如 LangGraph。
- **Orchestration Layer**: 管 session lifecycle、worktree、plan approval、merge/PR follow-through 的控制层，如 OpenClaw / openclaw-code-agent。
- **Scope Audit**: Labline 外层检查实际 diff 是否只触及允许文件。

## 3. 目标

### 3.1 短期目标

让 Codex/leader 能把明确、低风险、可测试的开发任务交给便宜模型:

1. 主控写任务说明、允许文件、测试命令和验收标准。
2. cheap worker 在临时 git worktree 里改代码。
3. worker 或 Labline 运行测试。
4. Labline 收集 stdout、stderr、diff、测试日志和 metadata。
5. Labline 检查 scope 越权、API key 泄露和测试状态。
6. Codex 主控 review 后决定是否合并。

### 3.2 非目标

第一阶段不做:

- 不 fork Codex CLI。
- 不把 cheap worker 纳入用户侧 role graph。
- 不把 `dev rt run` 伪装成本地 agent。
- 不直接实现 LangGraph workflow engine。
- 不默认自动 merge 到当前 checkout。
- 不把 dev-only 文档、worker 配置或实验资产 promote 到 stable 用户侧。

## 4. 短期候选比较

| 候选 | 短期结论 | 主要优点 | 主要风险 |
|---|---|---|---|
| OpenCode | 主线 | 非交互 `run`、JSON event、agent/permission、SDK、MCP/ACP、多 provider | 需要实测 DeepSeek 配置、JSON 稳定性和权限粒度 |
| Aider | fallback | 脚本模式成熟、DeepSeek 接入简单、测试循环现成、最容易一两天跑通 | 权限/scope 主要靠 Labline 后置审计；长期 agent lifecycle 弱 |
| goose | P1 smoke | MCP、providers、permissions、sandbox、general agent 价值高 | 短期 headless coding task 和日志格式需实测 |
| Cline SDK | 中长期重点 | 可嵌入 harness、checkpoint、MCP、subagents、provider gateway | TypeScript/Node 22+ 集成成本高 |
| OpenHands SDK | 中长期重型候选 | Python SDK、Docker/Kubernetes workspace、coding-agent 专用 | 运行时重，第一阶段成本高 |
| OpenClaw | 后置编排层 | session lifecycle、plan approval、worktree isolation、merge/PR follow-through | 依赖底层 harness，不能直接解决 cheap backend |
| LangGraph | 后置 workflow engine | durable execution、persistence、human-in-the-loop、状态机 | 不是 coding backend |

## 5. 推荐架构

```text
Codex / Leader
  - 写任务、scope、验收、review
  - 不直接依赖 cheap provider 的输出可信度

lane dev agent
  - provider/backend config
  - temp git worktree
  - backend adapter: opencode | aider | goose | ...
  - scope audit
  - test rerun
  - logs / metadata / diff

Coding backend
  - OpenCode first
  - Aider fallback
  - later: goose / Cline SDK / OpenHands SDK

Provider
  - DeepSeek / OpenRouter / OpenAI-compatible / local models
```

关键原则:

- backend 可以不完美，但 Labline 外层必须可靠。
- 所有 worker 修改都先落临时 worktree。
- 任何 backend 都不能直接污染主 checkout。
- 测试命令由 Labline 最后再跑一遍。
- scope audit 是强制 gate，不依赖模型自觉。
- API key 只通过 env 注入，不写入日志。

## 6. 命令草案

### 6.1 Provider / backend 配置

```bash
lane dev agent provider set deepseek-opencode \
  --backend opencode \
  --model deepseek/deepseek-v4-flash \
  --api-key-env DEEPSEEK_API_KEY
```

fallback:

```bash
lane dev agent provider set deepseek-aider \
  --backend aider \
  --model deepseek/deepseek-chat \
  --api-key-env DEEPSEEK_API_KEY
```

### 6.2 运行任务

```bash
lane dev agent run dev-worker \
  --provider deepseek-opencode \
  --file tools/update_developer_docs.py \
  --file tests/test_developer_doc_dag.py \
  --test "python -m pytest tests/test_developer_doc_dag.py -q" \
  "实现 dev-runtime 日志排除，并补测试"
```

### 6.3 查看结果

```bash
lane dev agent status
lane dev agent diff <run-id>
lane dev agent log <run-id>
lane dev agent apply <run-id>
lane dev agent discard <run-id>
```

第一阶段可以先不实现 `apply`，只生成 patch 让主控 review。

## 7. Phase 计划

### Phase 0: 明确边界

交付:

- 文档明确 `dev rt` 不是 coding agent。
- `dev rt config --json` 可供未来 agent surface 读取 provider/profile。
- developer doc DAG 忽略 `to-developer/logs/dev-runtime/**` 运行日志。

验收:

- `python -m pytest tests/test_dev_runtime_cli.py tests/test_developer_doc_dag.py -q`
- `python tools/update_developer_docs.py --check-only`

### Phase 1: OpenCode smoke script

先写 dev-only smoke，不直接接正式 CLI。

交付:

- `tools/dev_agent_opencode_smoke.py` 或等价脚本。
- 创建临时 worktree。
- 写入临时 OpenCode config / agent prompt。
- 调 `opencode run --dir <worktree> --format json --model <model> ...`。
- 收集输出、diff、测试日志和 metadata。
- 检查 scope 和 secret。

统一 smoke task:

> 修改 `tools/update_developer_docs.py`，让 `to-developer/logs/dev-runtime/**` 不参与 developer doc DAG 覆盖校验；补测试到 `tests/test_developer_doc_dag.py`；运行 `python -m pytest tests/test_developer_doc_dag.py -q`。

验收:

- DeepSeek worker 能在临时 worktree 改文件。
- 测试通过。
- `git diff --name-only` 只包含 scope 文件。
- 日志不含 API key。
- 失败时主 checkout 不变。

### Phase 2: Aider fallback smoke

如果 OpenCode provider、权限或 JSON event 卡住，立刻跑 Aider。

交付:

- `tools/dev_agent_aider_smoke.py` 或同一 adapter 里的 `aider` backend。
- 使用 `--message-file --yes --no-auto-commits --test-cmd <cmd> <scope files...>`。
- 外层复用 worktree、scope audit、secret scan、test rerun。

验收:

- 同 Phase 1。
- Aider auto commit 必须关闭。

### Phase 3: 正式 `lane dev agent` 最小版

交付命令:

- `lane dev agent provider set/list/show`
- `lane dev agent run`
- `lane dev agent status`
- `lane dev agent diff`
- `lane dev agent log`

运行目录:

```text
to-developer/logs/dev-agent/<run-id>/
  task.md
  backend.json
  stdout.log
  stderr.log
  tests.log
  diff.patch
  metadata.json
```

metadata schema:

```json
{
  "schema_version": 1,
  "run_id": "20260617-...",
  "backend": "opencode",
  "provider": "deepseek-opencode",
  "model": "deepseek/deepseek-v4-flash",
  "worktree": "...",
  "scope": ["tools/update_developer_docs.py"],
  "tests": ["python -m pytest ..."],
  "status": "passed",
  "scope_violation": false,
  "secret_scan": "passed"
}
```

### Phase 4: backend abstraction

新增 backend contract:

```yaml
backend:
  id: opencode
  command: opencode
  capabilities:
    headless: true
    json_events: true
    file_scope_permissions: true
    bash_permissions: true
    mcp: true
    sdk: true
```

每个 adapter 必须实现:

- `prepare(run)`
- `execute(run)`
- `collect(run)`
- `audit(run)`
- `cleanup(run)`

### Phase 5: Orchestration spike

评估顺序:

1. OpenClaw + OpenCode: 是否能管理 OpenCode session、plan approval、worktree follow-through。
2. Cline SDK: 是否值得直接嵌入 Labline dev-agent runtime。
3. goose: 是否适合 MCP-native 本地 agent runtime。
4. OpenHands SDK: 是否用于容器化/远程 workspace 和大型任务。

目标不是替换 Phase 1/2，而是判断长期是否把 `lane dev agent` 的内部运行时从 CLI wrapper 升级成 agent orchestration service。

### Phase 6: LangGraph workflow engine

等 coding backend 稳定后再做。

节点草案:

- Leader: 人机交互、需求澄清、scope 制定。
- Planner: 自动计划草案。
- Coder: 调 `lane dev agent run`。
- Reviewer: 独立 review diff。
- Test: 统一测试和验证。
- Integrity: 实验真实性、数据切分、指标透明度、可复现日志。
- Human Checkpoint: 任意关键步骤暂停、修改、批准、拒绝。
- Merge: apply / discard / rerun / open PR。

LangGraph 管状态、checkpoint 和人介入；不直接承担代码编辑。

## 8. 实现约束

- 所有 dev-only 新文档必须进 `to-developer/DOC_DAG.yaml`。
- `to-developer/logs/dev-agent/**` 和 `to-developer/logs/dev-runtime/**` 是运行日志，不应要求 DAG 覆盖。
- worker 不允许自动 commit 到主 checkout。
- 默认不允许 `--dangerously-skip-permissions`。如 OpenCode smoke 必须使用，只能在临时 worktree 中使用，并记录为风险。
- provider API key 只通过 env 传入。
- 所有日志写入前必须做 secret redaction。
- worker 输出不能直接被当成最终答案；Codex/leader 必须 review。
- 用户侧 stable 文档不暴露 developer worker 内部实现。

## 9. 风险

### OpenCode 风险

- DeepSeek provider/model 名称可能需要根据 Models.dev 或 OpenCode provider 配置实测。
- JSON event 输出可能不适合长期稳定协议，需要保留 stdout/stderr 原文。
- permission path 规则可能不能完全覆盖实际 shell 写入，需要 Labline 外层 diff audit。

### Aider 风险

- 默认 auto commit 必须关闭。
- 文件 scope 不是强权限系统，必须后置审计。
- Python API 官方不保证兼容，短期只调用 CLI。

### 长期风险

- 过早引入 LangGraph 会让 workflow engine 变成空壳。
- 过早引入 OpenClaw 会先解决 orchestration，而不是 cheap backend。
- Fork Codex CLI 会形成长期维护负担，除非后续确认所有外部 backend 都不满足。

## 10. 调研依据

本 PRD 只依赖官方文档、官方仓库或项目主页:

- OpenCode CLI: https://opencode.ai/docs/cli/
- OpenCode Agents: https://opencode.ai/docs/agents/
- OpenCode Permissions: https://opencode.ai/docs/permissions/
- OpenCode SDK: https://opencode.ai/docs/sdk/
- OpenCode MCP: https://opencode.ai/docs/mcp-servers/
- Aider scripting: https://aider.chat/docs/scripting.html
- Aider lint/test: https://aider.chat/docs/usage/lint-test.html
- Aider DeepSeek: https://aider.chat/docs/llms/deepseek.html
- Aider other LLMs: https://aider.chat/docs/llms/other.html
- goose quickstart: https://goose-docs.ai/docs/quickstart/
- goose providers: https://goose-docs.ai/docs/getting-started/providers/
- Cline SDK: https://docs.cline.bot/sdk/overview
- Cline checkpoints: https://docs.cline.bot/core-workflows/checkpoints
- OpenHands SDK: https://docs.openhands.dev/sdk
- OpenHands CLI: https://docs.openhands.dev/openhands/usage/cli/command-reference
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- LangChain HITL: https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- OpenClaw runtimes: https://docs.openclaw.ai/concepts/agent-runtimes
- openclaw-code-agent: https://github.com/goldmar/openclaw-code-agent

## 11. 下一步

推荐立即执行:

1. 清理并提交当前 `dev rt config --json`、DAG 日志忽略和本 PRD。
2. 实现 OpenCode smoke script。
3. 用 DeepSeek provider 跑统一 smoke task。
4. 如果 OpenCode smoke 失败超过半天，转 Aider fallback。
5. smoke 成功后再做 `lane dev agent run` 正式 CLI。
