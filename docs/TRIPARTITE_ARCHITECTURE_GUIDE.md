# ARIS 三边架构使用指南

> Codex-first 版本。ARIS 当前默认是在一个 Codex 主会话中由 Leader 编排本地 agents：Leader 负责读、判、派；Executor 不是单一角色，而是拆成 Coder / Deployer / Writer 三个执行子职责；Reviewer 是本地独立审查 agent。Claude Code 只作为兼容客户端。

---

## 一、什么是三边架构

传统的 AI 辅助科研容易变成一个模型同时规划、实现、跑实验、审查结果，最后给自己打分。ARIS 把流程拆成三个互相制衡的角色：

```
                 ┌──────────────────┐
                 │      Leader      │
                 │  读 / 判 / 派     │
                 └────────┬─────────┘
                          │ 派发本地 agents
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
   ┌──────────┐    ┌──────────┐     ┌──────────┐
   │  Coder   │    │ Deployer │     │  Writer  │
   │ 写代码测试 │    │ 部署跑实验 │     │ 写论文文档 │
   └────┬─────┘    └────┬─────┘     └────┬─────┘
        └───────────────┼────────────────┘
                        ▼
                 ┌──────────┐
                 │ Reviewer │
                 │ 独立审查  │
                 └──────────┘
```

| 层级 | 角色 | 职责 | 禁止 |
|------|------|------|------|
| 编排 | **Leader** | 制定计划、读状态、判断 gate、派发任务、止损 | 写代码、跑命令、部署、写论文、替执行 agent 兜底 |
| 执行 | **Coder** | 写代码、测试、修 bug、重构 | SSH、部署、跑远程实验、写论文、自审通过 |
| 执行 | **Deployer** | 同步代码、启动训练、监控实验、收集结果 | 改代码逻辑、写论文、改实验计划 |
| 执行 | **Writer** | 写论文、文档、rebuttal、专利材料 | 写实验代码、部署、编造结果 |
| 审查 | **Reviewer** | 审代码、审实验、审 claim、审论文 | 只看 Executor 总结、替 Executor 修问题 |

Reviewer 的独立性来自独立 agent 上下文和原始文件审查。当前默认不依赖 Codex MCP；MCP reviewer bridge 只是高级扩展。

---

## 二、准备工作

### 2.1 安装 Codex CLI

```bash
npm install -g @openai/codex
```

配置 `~/.codex/auth.json` 和 `~/.codex/config.toml`：

```toml
model_provider = "my_proxy"
model = "gpt-5.5"

[model_providers.my_proxy]
base_url = "https://my-proxy.example.com/v1"
wire_api = "responses"
```

### 2.2 初始化项目

推荐直接用 `aris init`，不要手工拼安装器：

```bash
mkdir -p ~/projects/my-research
cd ~/projects/my-research
aris init --direction "你的研究方向"
aris doctor
```

初始化后会有：

```
my-research/
├── project.yaml
├── AGENTS.md              # Codex 项目上下文
├── CLAUDE.md              # Claude Code 兼容上下文
├── .agents/skills/        # Codex skills
├── .claude/skills/        # Claude Code 兼容 skills
├── .aris/
├── code/
├── data/
├── outputs/
└── refine-logs/
```

---

## 三、启动方式

### 默认：一个 Codex 主会话

用户只需要打开一个 Codex 会话：

```bash
cd ~/projects/my-research
codex
```

然后运行：

```text
$leader "你的研究方向"
```

Leader 在这个主会话里读项目上下文、维护状态、派发本地 agents。不要手动开三个 `codex exec -p ...` 终端；当前最小可用 CLI 设计不是三终端常驻模型。

### Leader 如何派发执行

Leader 根据任务类型派发不同执行子角色：

| 任务 | 派发对象 | 典型 skill |
|------|----------|------------|
| 实现模型、训练脚本、评估脚本、测试 | **Coder** | `$coder`, `$tdd`, `$diagnose` |
| 同步服务器、启动训练、监控、拉结果 | **Deployer** | `$deployer`, `$sync`, `$run-experiment`, `$monitor-experiment`, `$experiment-queue` |
| 写论文、文档、rebuttal、报告 | **Writer** | `$writer`, `$paper-writing`, `$paper-write`, `$rebuttal` |
| 审查代码、实验、claim、论文 | **Reviewer** | 本地独立 reviewer agent，或 `$review` / `$experiment-audit` 等审查 skill |

Leader 自己只读、判断、派发，不直接承担 Coder / Deployer / Writer 的工作。

### 快速单窗口流水线

如果不需要逐阶段人工介入，可以直接：

```text
$research-pipeline "你的研究方向"
```

它仍应遵守同样的角色边界，只是自动推进更多步骤。

### Claude Code 兼容模式

如果继续使用 Claude Code：

```bash
claude
```

使用 `/skill-name` 调用同名 skill。兼容模式读取 `CLAUDE.md` 和 `.claude/skills/`。

---

## 四、全流程实验步骤

```
$experiment-plan → Coder → Reviewer → Deployer → Reviewer → $result-to-claim → Writer
     Leader        代码实现    代码审查     部署实验      实验审计       Leader 判定        写作
```

### 步骤 1：制定实验计划（Leader）

```text
$experiment-plan "你的研究方向描述"
```

产出 `refine-logs/EXPERIMENT_PLAN.md`，至少包含：

- Claim Map：实验想证明什么
- Expectation Declaration：split、GT 来源、baseline 假设
- Execution Spec：variants / metrics / seeds
- Delta Assertion：实验组 vs 对照组应有什么差异
- Evidence Mapping：哪个结果文件支撑哪个 claim

### 步骤 2：实现代码（Coder）

Leader 派 Coder 读取计划并实现：

```text
$coder "根据 refine-logs/EXPERIMENT_PLAN.md 实现实验代码和测试"
```

Coder 只负责代码和测试。若偏离计划，写 `refine-logs/IMPLEMENTATION_DEVIATIONS.json`；若无偏离，写 no-deviation 声明。

### 步骤 3：审查代码（Reviewer）

Reviewer 直接读代码、测试、计划和偏差记录，不看 Coder 自评。审查不通过则 Leader 重新派 Coder 修复。

### 步骤 4：部署运行（Deployer）

Leader 派 Deployer 同步代码、启动实验、监控、收集结果：

```text
$deployer "同步到配置的 GPU 服务器，先跑 sanity，再跑计划中的实验 blocks"
```

Deployer 只做部署和运行，不改代码逻辑。长任务必须留下 durable job handle，例如 screen/tmux 名、队列状态文件、日志路径、结果目录。

### 步骤 5：实验审计（Reviewer）

```text
$experiment-audit
```

Reviewer 直接读代码、配置、split、日志、结果文件，重点检查：

- Ground Truth Provenance
- Split Correctness
- Score Normalization
- Result File Existence
- Dead Code Detection
- Implementation Conformance
- Delta Assertion
- Evidence Mapping

### 步骤 6：判定 Claim（Leader）

```text
$result-to-claim
```

Leader 读取实验计划、结果、审计报告和偏差记录，判断：

- `claim_supported`: yes / partial / no
- `confidence`: high / medium / low
- `delta_assertion_status`: satisfied / weak / failed
- `implementation_deviation_impact`: none / narrow_scope / breaks_claim_test

### 步骤 7：写作（Writer）

如果结果支撑论文写作，Leader 派 Writer：

```text
$writer "根据实验计划、结果和 claim verdict 起草方法与实验章节"
```

Writer 只引用真实存在的实验结果文件，不编造数字；写完交给 Reviewer 审查。

---

## 五、核心规则

### Leader 不替执行 agent 干活

Leader 只能读、判、派。即使 Coder / Deployer / Writer 阻塞，Leader 也不直接写代码、SSH、改配置或写论文，而是转述阻塞报告，让用户介入或重新派发任务。

### Coder / Deployer / Writer 边界

- Coder 不 SSH、不部署、不写论文。
- Deployer 不改代码逻辑、不改实验计划、不写论文。
- Writer 不写实验代码、不跑实验、不编造结果。

### Reviewer 独立性

Reviewer 必须直接读原始文件，不能只看执行 agent 的总结。详见 `skills/shared-references/reviewer-independence.md`。

### 实验诚实度

禁止以下行为，详见 `skills/shared-references/experiment-integrity.md`：

- 用模型输出当 ground truth
- 用自己的分数做分母来归一化到 0.99
- 声称结果来自不存在的文件
- 把 2 个场景的 pilot 叫做 comprehensive evaluation

### 计划偏移必须记录

如果实际实现偏离了计划，必须写 `IMPLEMENTATION_DEVIATIONS.json`：

```json
[
  {
    "plan_reference": "Block B1, Execution Spec",
    "deviation_type": "metric_change",
    "planned_value": "mAP@0.5",
    "actual_value": "mAP@[0.5:0.95]",
    "reason": "COCO 标准用 mAP@[0.5:0.95]",
    "claim_impact": "narrow_scope",
    "artifact_impact": "results/eval_*.json 格式变化",
    "status": "resolved",
    "owner": "coder",
    "timestamp": "2026-05-17T21:00:00Z"
  }
]
```

### Delta Assertion

每个实验必须能回答：实验组和对照组的结果真的不一样吗？如果输出完全相同，说明核心改动可能没有生效，必须停下来排查。

---

## 六、文件交接规范

| 阶段 | 产出文件 | 谁写 | 谁读 |
|------|----------|------|------|
| Plan | `refine-logs/EXPERIMENT_PLAN.md` | Leader | Coder, Deployer, Reviewer |
| Code | 实验代码、测试、no-deviation 或 `IMPLEMENTATION_DEVIATIONS.json` | Coder | Reviewer, Deployer |
| Run | logs、job handles、`refine-logs/EXPERIMENT_RESULTS/`、`EXPERIMENT_TRACKER.md` | Deployer | Reviewer, Leader |
| Audit | `EXPERIMENT_AUDIT.md` + `.json` | Reviewer | Leader |
| Claim | claim verdict artifact | Leader | Writer, Reviewer |
| Paper | `paper/`、rebuttal、报告 | Writer | Reviewer, Leader |

所有产出文件应在 `MANIFEST.md` 登记：

```markdown
| Timestamp | Skill | File | Stage | Description |
|-----------|-------|------|-------|-------------|
| 2026-05-17 21:00 | $experiment-plan | refine-logs/EXPERIMENT_PLAN.md | implementation | FSCIOD experiment plan with 3 blocks |
```

---

## 七、常见问题

### Q: 需要手动开三个 Codex session 吗？

不需要。默认是一个 Codex 主会话，由 Leader 在本地派生 Coder / Deployer / Writer / Reviewer agents。

### Q: Reviewer 还是 MCP 吗？

不是默认路径。当前 Codex-first 版本把 Reviewer 视为本地独立 reviewer agent。MCP reviewer bridge 可作为高级扩展使用，但不是新手部署依赖。

### Q: 为什么 Executor 要拆成三个子职责？

因为写代码、部署实验、写论文的风险不同。拆成 Coder / Deployer / Writer 后，权限、产出、阻塞协议和审查点都更清楚，Leader 也更容易判断哪里出了问题。

### Q: 只有一个窗口能不能跑？

可以，默认就是一个主窗口。想要更细粒度人工介入时，不是手动开三个常驻 session，而是让 Leader 在固定检查点停下来给用户看计划、结果、审查和下一步。

### Q: 实验跑一半挂了怎么办？

ARIS 的恢复机制基于 `skills/shared-references/recovery-state-contract.md`：工具层有状态持久化，链条层有阶段检查点，可以从最近检查点续跑。
