# LangGraph Evaluation for ARIS

本文说明 LangGraph 对 ARIS 的价值、边界和推荐引入时机。结论：现在不把 LangGraph 加成 ARIS 核心依赖；先继续完善 ARIS 原有的静态 skill 文档、DAG、schema、事件日志和 Codex/Claude Code 双客户端兼容。LangGraph 适合作为后续可选的长流程编排后端。

信息来源：LangChain 官方文档的 LangGraph overview、persistence、interrupts 页面：

- <https://docs.langchain.com/oss/python/langgraph/overview>
- <https://docs.langchain.com/oss/python/langgraph/persistence>
- <https://docs.langchain.com/oss/python/langgraph/interrupts>

## LangGraph 能做什么

LangGraph 是一个把 agent 工作流显式建成图的运行时。对 ARIS 有价值的点主要是运行期编排，而不是替代 `SKILL.md` 文档系统。

| 能力 | 对 ARIS 的意义 |
|------|----------------|
| 显式状态图 | 把 `leader -> executor -> reviewer -> fix -> audit` 这类流程从自然语言约定变成可执行状态机 |
| checkpoint / persistence | 长任务中断后恢复，例如夜间实验、论文自动修复、多轮 review |
| interrupt / human-in-the-loop | 在 `git push`、远程部署、删除文件、接受 reviewer 结论前暂停并等人确认 |
| 条件分支 | 根据实验结果、review 分数、编译失败类型进入不同节点 |
| 可观测性接口 | 后续可以统一记录每个 agent 的 token、工具调用、状态转移、失败原因 |
| 子图 | 把 paper writing、resubmit、auto-review-loop 拆成可复用 workflow 模块 |

## LangGraph 不能解决什么

LangGraph 不是 ARIS 现在问题的直接替代品。

| 不适合替代的部分 | 原因 |
|------------------|------|
| `SKILL.md` 本身 | skill 是给 Codex/Claude Code 读的操作协议，必须保持静态、可审计、可安装 |
| `docs/SKILL_DAG.yaml` 生成器 | DAG 是治理和影响分析资产，不等于运行时 workflow |
| Codex/Claude Code 兼容层 | LangGraph 不会自动解决 `$skill`、`/skill`、`AGENTS.md`、`CLAUDE.md`、hook 能力差异 |
| 简单工具脚本 | 安装、目录同步、catalog 生成、BibTeX 验证这类 deterministic 工具不需要 agent graph |
| 所有 skill 的统一 runtime | 很多 skill 是文档化流程或人工协作协议，强行变成 runtime 会增加维护成本 |

## 好在哪里

LangGraph 的主要价值是让长流程变得可恢复、可观测、可插入人工确认。

对 ARIS 来说，最值得关注的是：

- 恢复能力：多小时任务不用靠聊天上下文续命，可以从 checkpoint 继续。
- 明确边界：每个节点只处理一类状态转换，减少 leader skill 里自然语言分支过多的问题。
- 审批门：危险命令、远程部署、重投稿、覆盖论文文件等动作可以统一走 interrupt。
- 统计口径：token、命令调用、agent 调用次数、失败节点可以挂在状态转移日志上。
- 多客户端一致性：Codex 和 Claude Code 前端不同，但后端 workflow 可以复用同一套状态机。

## 对当前 ARIS 的风险

现在直接引入 LangGraph 会带来几个成本：

- 新依赖会改变安装前提，服务器部署和离线环境会更复杂。
- skill 还在做 Codex/Claude Code 双兼容，过早引入 runtime 会让问题叠加。
- 当前 DAG 仍在正规化，先把 `invokes`、`produces`、`consumes`、`platform`、`status` 这些静态元数据稳定下来更重要。
- 很多新增 skill 还只是 Codex mirror 可见性补齐，不适合马上绑定到一个执行框架。
- 如果没有统一事件日志，LangGraph 的 observability 价值发挥不出来。

## 推荐路线

### 阶段 1：继续原框架

现在应继续原来的 ARIS 开发方式：

- 所有 skill frontmatter 增加或修正 `platform: both`、`status`、`invokes`、`produces`、`consumes`。
- `tools/generate_skill_dag.py` 只把 frontmatter `invokes` 作为正式 DAG 边；正文 `/skill`、`$skill` 只当弱引用。
- Codex mirror 不再标成 Claude-only；只能标为 `needs-adaptation`、`needs-runtime-adaptation`、`needs-safety-confirmation` 等可收敛状态。
- 先建立统一事件日志格式，至少包含 skill、agent、model/provider、token、tool call、artifact、failure。
- 对 `sync`、`framework-update`、`git-guardrails` 等危险动作先用文档约束和测试守住。

### 阶段 2：做最小 LangGraph 原型

等静态治理稳定后，只选一个 workflow 原型化，不要一次迁移全部 skill。首选：

| 候选 workflow | 适配价值 |
|---------------|----------|
| `leader` | 最接近状态机，但范围最大，适合作为第二个原型 |
| `grill-with-docs` | 有明确问答、决策、文档更新节点，适合小范围验证 |
| `auto-review-loop` | 多轮 review/fix/checkpoint 很适合 LangGraph |
| `paper-talk` | 生成、编译、逐页 polish、审计、导出是清晰 pipeline |
| `resubmit-pipeline` | 多审批门、硬约束多，适合 interrupt |

建议第一个原型选 `grill-with-docs` 或 `auto-review-loop`，不要直接从 `leader` 开始。

### 阶段 3：可选后端，而不是强制依赖

如果原型有效，LangGraph 应作为可选后端：

```text
SKILL.md 静态协议
  -> ARIS DAG / schema / docs
  -> 可选 workflow runtime
       - native Codex / Claude Code conversation
       - LangGraph backend
```

这样用户没有 LangGraph 也能继续使用 ARIS；需要长任务恢复、统计、人工审批的人再启用 runtime。

## 适配设计草案

如果后续引入，建议用一个小的 ARIS workflow schema 映射到 LangGraph：

```yaml
workflow: auto-review-loop
platform: both
state:
  project_dir: path
  round: int
  review_report: path
  patch_summary: path
  verdict: enum
nodes:
  - run_review
  - classify_findings
  - implement_fixes
  - run_tests
  - human_approval
  - finalize
interrupts:
  - git_push
  - destructive_edit
  - accept_negative_result
events:
  - node_started
  - tool_called
  - artifact_written
  - node_failed
  - node_completed
```

这个 schema 不应该替换 `SKILL.md`，而是由 `SKILL.md` 引用或生成。

## 当前决策

当前决策是：不引入 LangGraph 核心依赖；继续原生 ARIS 框架开发。短期工作重点是 DAG 正规化、Codex/Claude Code 双兼容 metadata、skill mirror 适配、事件日志设计和安全动作确认。

LangGraph 的重新评估条件：

- `docs/SKILL_DAG.yaml` 和 frontmatter schema 稳定。
- 至少 10 个关键 skill 明确 `platform/status/invokes/produces/consumes`。
- Codex/Claude Code 双客户端安装和调用路径稳定。
- 已有统一事件日志，可以记录 token、工具调用、agent 调用次数。
- 有一个明确长流程痛点，例如 auto-review-loop 中断恢复或 paper-talk 多阶段审批。
