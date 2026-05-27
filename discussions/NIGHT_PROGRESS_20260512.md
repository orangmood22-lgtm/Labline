# 夜间进度日志

> 目标：边实现边探索，把三边架构 / Human-in-the-loop / Delta Assertion 从讨论文档推进到仓库内可执行机制。

## 2026-05-12 夜间执行计划

### P0（先做）
1. 落地模板文件：Data Flow Spec / Pseudocode Spec / Experiment Expectation Declaration
2. 实现 `tools/delta_assertion.py`，把“实验组 vs 对照组差异”和“预期 vs 实际偏差”都做成可执行检查
3. 改造关键 SKILL：`experiment-plan`、`experiment-bridge`、`experiment-audit`、`result-to-claim`
4. 记录 MANIFEST 和 git 变更，保证后续可追踪

### P1（随后探索）
1. 看 `monitor-experiment` / `research-pipeline` 是否需要最小改造来接入新工件
2. 评估是否需要补 `generate_stage_report.py` / checkpoint queue 原型
3. 整理一份阶段性汇报文档，方便你醒来后直接看

## 当前发现
- 现有 `experiment-audit` 只覆盖 A-F，没有 split correctness / implementation conformance / expectation-vs-actual。
- 现有 `experiment-bridge` 有 code review，但缺技术规格层（spec）和 Delta Assertion 阶段。
- 现有 `experiment-plan` 能写 claim-driven 计划，但还不会产出 expectation declaration 与实现规格模板。
- `result-to-claim` 能做 claim routing，但没有把 expectation anomaly 和 delta assertion 结果作为显式输入。
- 仓库根目录还没有 `MANIFEST.md`，已补建以便后续产出追踪。

## 风险
- 当前工作树已有多处未由本轮产生的改动，提交时必须精确挑选文件，避免误带。
- 多个技能文档较长，改动时要尽量做增量补丁，避免破坏现有流程描述。
