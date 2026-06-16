# Project: {project-name}

## 默认模式

- caveman 模式默认开启（精简回复，保留技术准确度）
- 代码修改遵循 TDD（仅限 Python/实验代码，文档/配置不要求）
- 新设计/架构决策落地前必须 `$grill-me` 或 `$grill-with-docs`
- 新用户首次使用建议跑 `$git-guardrails`

## Agent 约束

**完整约束和 skill 用法见 `.agents/skills/shared-references/agent-guide.md`。**

- 禁止 `tail -f` 或循环 `tail` 轮询实验 → 用 `$monitor-experiment` 或 background tasks
- Executor 遇阻塞遵循 `executor-blocked-protocol.md`：自救 2 次，失败写 `BLOCKED_REPORT.md`
- Agent 启动、进入长任务、阻塞、完成时遵循 `agent-status-stream.md` 更新自己的状态文件；`.aris/status/` 不提交
- Leader 不写代码/不跑命令，Coder 不 SSH，Deployer 不改代码，Writer 不跑实验，Reviewer 只看原始文件
- Skill 分层：编排层(leader) / 执行层(coder|deployer|writer) / 审查层(reviewer) / 工具层(any) / 检索层(any)，不要越层调用

## Pipeline Status

```yaml
stage: idle          # idle | idea-discovery | implementation | training | review | paper
idea: ""             # Current idea title (one line)
contract: ""         # Path to research_contract.md (e.g., idea-stage/docs/research_contract.md)
current_branch: ""   # Git branch for this idea
baseline: ""         # Baseline numbers for comparison
training_status: idle  # idle | running | complete | failed
language: en         # en | zh — controls skill output language (see shared-references/output-language.md)
active_tasks: []
next: ""             # Concrete next step
last_updated: ""     # YYYY-MM-DD HH:mm — auto-updated by skills on every output write
```

## Three-Party Architecture

| Role         | Profile                 | Responsibility                          |
| ------------ | ----------------------- | --------------------------------------- |
| **Leader**   | Codex 主会话            | 研究规划、gate 决策、止损判断、分发任务 |
| **Coder**    | `codex exec -p coder`   | 代码实现、测试、修 bug、重构           |
| **Deployer** | `codex exec -p deployer`| 同步、训练、监控、收集结果             |
| **Writer**   | `codex exec -p writer`  | 论文、文档、rebuttal                  |
| **Reviewer** | 独立 reviewer agent     | 独立代码审查、实验审计、claim 判定      |

## Project Constraints

- {constraint 1}
- {constraint 2}

## Project Overrides

项目本地定制统一登记在 `overrides/` 目录，并通过 `project.yaml#overrides` 追踪生命周期。禁止未经登记的 override。详见框架文档 `docs/PROJECT_OVERRIDES.md`。

## Non-Goals

- {non-goal 1}

## Compute Budget

- {budget details, e.g., "8x A100 for 24h via vast.ai"}
