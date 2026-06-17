# Executor Skill Routing

Leader 派发任务时，根据任务类型选择专用角色。Coder / Deployer / Writer 是用户项目的主执行角色。

| 任务 | 角色 | 常用 skills |
|------|------|-------------|
| 代码、测试、重构 | Coder | `/tdd`, `/diagnose`, `/experiment-bridge` |
| SSH 同步、启动训练、监控、收集结果 | Deployer | `/run-experiment`, `/monitor-experiment`, `/experiment-queue`, `/sync` |
| 论文、文档、rebuttal | Writer | `/paper-write`, `/paper-writing`, `/paper-plan`, `/paper-compile` |
