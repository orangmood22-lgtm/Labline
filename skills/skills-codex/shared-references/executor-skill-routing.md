# Executor Skill Routing

Leader 派发任务时，根据任务类型选择专用角色。Coder / Deployer / Writer 是主执行角色，Worker 是低风险辅助执行角色。

| 任务 | 角色 | 常用 skills |
|------|------|-------------|
| 代码、测试、重构 | Coder | `/tdd`, `/diagnose`, `/experiment-bridge` |
| SSH 同步、启动训练、监控、收集结果 | Deployer | `/run-experiment`, `/monitor-experiment`, `/experiment-queue`, `/sync` |
| 论文、文档、rebuttal | Writer | `/paper-write`, `/paper-writing`, `/paper-plan`, `/paper-compile` |
| 批量文档、引用清扫、测试草案、低风险 patch 草案 | Worker | `/caveman`, bounded local edits only |

## Worker 派发模板

```text
spawn_agent:
  agent_type: worker
  model: gpt-5.4-mini
  message: |
    你是 Worker，只做低风险辅助执行。
    你不是一个人在代码库里，不要 revert 别人的改动。

    先读：
    - .agents/skills/shared-references/agent-guide.md
    - .agents/skills/worker/SKILL.md
    - .agents/skills/shared-references/agent-status-stream.md

    任务：
    [具体任务]

    写入范围：
    - [明确文件或目录]

    约束：
    - 不碰密钥，不做最终决策，不自动 commit/push/promote
    - 如需越界，停止并报告
```
