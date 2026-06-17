# Executor Skill Routing

> Leader 派发 Executor 任务时，根据任务类型从本表选择推荐 skills 写入 prompt。
> Executor 收到推荐后**必须使用**标记为"必用"的 skill。
> Executor 有三种主执行角色：Coder / Deployer / Writer，各有不同 skill 路由；Worker 是低风险辅助执行角色，只处理批量文档、引用清扫、测试草案和低风险 patch 草案。

## 角色→Skill 路由

### Coder（代码实现）

| 任务类型 | 必用 | 可选 | caveman |
|----------|------|------|---------|
| **写 Python/实验代码** | `/tdd` | `/diagnose`（出 bug 时） | ✅ 开启 |
| **诊断 bug/性能问题** | `/diagnose` | `/zoom-out`（需要全局视角时） | ✅ 开启 |
| **实现实验计划** | `/experiment-bridge`, `/tdd` | `/diagnose` | ✅ 开启 |

### Deployer（部署监控）

| 任务类型 | 必用 | 可选 | caveman |
|----------|------|------|---------|
| **部署运行实验** | `/run-experiment`, `/monitor-experiment` | `/experiment-queue`（批量时）, `/training-check`（WandB） | ✅ 开启 |
| **代码同步/部署** | `/sync` | `/overleaf-sync`（论文时） | ✅ 开启 |
| **分析实验结果** | `/analyze-results` | `/ablation-planner`（需要消融时） | ✅ 开启 |

### Writer（论文写作）

| 任务类型 | 必用 | 可选 | caveman |
|----------|------|------|---------|
| **写论文** | `/paper-write` | `/paper-compile`, `/formula-derivation` | ❌ 关闭 |
| **生成论文图表** | `/paper-figure` | `/figure-spec`, `/mermaid-diagram`, `/paper-illustration` | ✅ 开启 |
| **生成幻灯片/海报** | `/paper-slides` 或 `/paper-poster` | `/slides-polish` | ❌ 关闭 |
| **文献调研** | `/research-lit` | `/semantic-scholar`, `/arxiv`, `/novelty-check` | ✅ 开启 |
| **写数学证明** | `/proof-writer` | `/proof-checker`（验证时） | ❌ 关闭 |
| **专利撰写** | 按阶段选用 | 见下方专利子表 | ❌ 关闭 |
| **基金申请** | `/grant-proposal` | — | ❌ 关闭 |

### Worker（低风险辅助执行）

| 任务类型 | 必用 | 可选 | caveman |
|----------|------|------|---------|
| **批量文档整理** | `/caveman` | `/diagnose`（只限本地小问题定位） | ✅ 开启 |
| **引用/路径/链接清扫** | `/caveman` | `/zoom-out`（需要全局视角时） | ✅ 开启 |
| **测试草案/断言补全** | `/caveman` | `/tdd`（只写测试草案时） | ✅ 开启 |
| **低风险 patch 草案** | `/caveman` | `/diagnose`（遇局部 bug 时） | ✅ 开启 |

### 专利任务细分

| 子任务 | 必用 |
|--------|------|
| 发明构建 | `/invention-structuring` |
| 查新 | `/patent-novelty-check`, `/prior-art-search` |
| 权利要求 | `/claims-drafting` |
| 说明书 | `/specification-writing` |
| 实施例 | `/embodiment-description` |
| 附图 | `/figure-description` |
| 格式化 | `/jurisdiction-format` |
| 审查 | `/patent-review` |

## Leader 派发模板

Leader 派发专用角色时，prompt 应包含以下结构：

### Coder 派发

```
Agent:
  model: "sonnet"
  description: "[任务简述] (Coder)"
  prompt: |
    你是 Coder，只负责写代码。

    ## 首先
    Read .claude/skills/shared-references/agent-guide.md 了解可用 skills 和约束。
    Read .claude/skills/coder/SKILL.md 了解 Coder 职责边界。

    ## 你的任务
    [具体任务描述]

    ## 推荐 Skills
    本任务必用：/tdd（写代码）、/diagnose（遇 bug 时）
    本任务可选：[根据路由表]

    ## 约束
    - caveman 模式开启
    - 遵循 executor-blocked-protocol
    - 不做自审，写完交 Reviewer
    - 只写代码不部署。完成后列出所有产出文件路径
```

### Deployer 派发

```
Agent:
  model: "sonnet"
  description: "[任务简述] (Deployer)"
  prompt: |
    你是 Deployer，只负责部署和监控。

    ## 首先
    Read .claude/skills/shared-references/agent-guide.md 了解可用 skills 和约束。
    Read .claude/skills/deployer/SKILL.md 了解 Deployer 职责边界。

    ## 你的任务
    [具体任务描述]

    ## 推荐 Skills
    本任务必用：/run-experiment, /monitor-experiment
    本任务可选：[根据路由表]

    ## 约束
    - caveman 模式开启
    - 遵循 executor-blocked-protocol
    - 禁止 tail -f 轮询
    - 完成后列出所有产出文件路径
```

### Writer 派发

```
Agent:
  model: "sonnet"
  description: "[任务简述] (Writer)"
  prompt: |
    你是 Writer，只负责写作。

    ## 首先
    Read .claude/skills/shared-references/agent-guide.md 了解可用 skills 和约束。
    Read .claude/skills/writer/SKILL.md 了解 Writer 职责边界。

    ## 你的任务
    [具体任务描述]

    ## 推荐 Skills
    本任务必用：/paper-write
    本任务可选：[根据路由表]

    ## 约束
    - caveman 模式关闭（写作需要完整语言）
    - 不做自审，写完交 Reviewer
    - 数据一致：数字必须与实验结果文件一致
    - 完成后列出所有产出文件路径
```

### Worker 派发

```
spawn_agent:
  agent_type: worker
  model: gpt-5.4-mini
  message: |
    你是 Worker，只做低风险辅助执行。
    你不是一个人在代码库里，不要 revert 别人的改动。

    ## 首先
    Read .agents/skills/shared-references/agent-guide.md 了解可用 skills 和约束。
    Read .agents/skills/worker/SKILL.md 了解 Worker 职责边界。

    ## 你的任务
    [具体任务描述]

    ## 写入范围
    - [明确文件或目录]

    ## 推荐 Skills
    本任务必用：/caveman
    本任务可选：[根据路由表]

    ## 约束
    - 不碰密钥
    - 不做最终架构、实验 claim、release、promote、rollback 决策
    - 不自动 commit / push
    - 如需越界，停止并报告
    - 完成后列出所有产出文件路径和验证命令
```

## 更新本文件

新增任务类型时：
1. 在映射表中添加一行
2. 如果涉及新 skill，确认该 skill 的 `caller` frontmatter 包含 `executor`
3. 更新 `agent-guide.md` 的执行层表格（如果是新 skill）
