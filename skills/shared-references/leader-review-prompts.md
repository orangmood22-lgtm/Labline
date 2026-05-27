# Leader Review Prompts — 供 Leader skill 引用的 Codex MCP 审查模板

> 本文件内包含 Leader 分发 Reviewer 任务时使用的完整 prompt 模板。
> Leader skill 本身只写流程，具体 prompt 在此按需读取。

---

## §1 Phase 1: 实验计划审核

```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    EXPERIMENT PLAN REVIEW

    审核以下实验计划的科学严谨性：

    1. claims 是否清晰可测？
    2. 评估类型（real_gt / synthetic_proxy / etc.）是否声明？
    3. split、GT 来源、baseline 是否明确？
    4. delta assertion 是否具体、可证伪？
    5. scope 是否诚实声明（不过度夸大）？
    6. evidence mapping 是否完整（每个 claim 对应到结果文件）？

    计划内容：
    [paste full EXPERIMENT_PLAN.md]

    返回：
    - verdict: PASS / WARN / FAIL
    - issues: 具体问题列表
    - suggestions: 改进建议
```

---

## §2 Phase 2: 代码审查

```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    CODE REVIEW FOR EXPERIMENT IMPLEMENTATION

    You are a senior code reviewer. Review the following for correctness.

    Experiment Plan:
    [paste key sections from EXPERIMENT_PLAN.md: Expectation Declaration, Execution Spec, Data Flow, Delta Assertion, Evidence Mapping]

    Code Files:
    [list each file path and its content]

    Check:
    1. Does the code correctly implement the planned method?
    2. All hyperparameters from plan in argparse?
    3. Logic bugs (wrong loss, incorrect split, missing eval)?
    4. Metrics computed correctly?
    5. Delta assertion reachable (not dead path)?
    6. Data flow matches plan?
    7. Results saved in parseable JSON/CSV?

    For each issue: specify CRITICAL / MAJOR / MINOR and exact fix.
    Return verdict: PASS / WARN / FAIL.
```

---

## §3 Phase 4: 实验审计

```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    EXPERIMENT AUDIT

    You are an independent experiment auditor. You must read ALL files directly — do NOT trust any Executor summary.

    Files to read:
    - refine-logs/EXPERIMENT_PLAN.md (the plan)
    - refine-logs/IMPLEMENTATION_DEVIATIONS.json (drift record)
    - [all code files — list paths and read each]
    - [all result files — list paths and read each]

    Audit Checklist (A-J):
    A. Ground Truth Provenance — GT from dataset or model-generated?
    B. Score Normalization — suspicious normalization?
    C. Result File Existence — claimed results actually exist?
    D. Dead Code Detection — metric functions actually called?
    E. Scope Assessment — scope matches claim language?
    F. Evaluation Type Classification — real_gt / synthetic_proxy / etc.
    G. Split Correctness — eval uses intended split?
    H. Implementation Conformance — code matches plan? Deviations complete?
    I. Delta Assertion — core modification actually produced difference?
    J. Evidence Mapping — each claim traces to concrete evidence?

    For each check: Status (PASS/WARN/FAIL), Evidence (file:line), Details.
    Overall verdict: PASS / WARN / FAIL.
```

---

## §4 Phase 5: Claim 判定

```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    RESULT-TO-CLAIM EVALUATION

    Judge whether experimental results support the intended claims.

    Planning contract:
    - Claim map: [from EXPERIMENT_PLAN.md]
    - Expectation declaration: [split / GT / baseline]
    - Execution spec: [variants / metrics / seeds]
    - Delta assertion: [expected difference]
    - Evidence mapping: [result files → claims]
    - Implementation deviations: [from IMPLEMENTATION_DEVIATIONS.json]
    - Audit verdict: [from EXPERIMENT_AUDIT.json]

    Results: [from result files]

    Evaluate:
    1. claim_supported: yes | partial | no
    2. confidence: high | medium | low
    3. delta_assertion_status: satisfied | weak | failed | unavailable
    4. implementation_deviation_impact: none | narrow_scope | weakens_evidence | breaks_claim_test | unknown
    5. evidence_mapping_status: aligned | partial | broken
    6. suggested_claim_revision: (if needed)
    7. missing_evidence: (if any)

    Be honest. Do not inflate claims.
    A single positive result on one dataset does not support a general claim.
```

---

## §5 Phase X: 方向性止损审查

```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    DIRECTION REVIEW (STOP-LOSS)

    The research pipeline has failed [N] consecutive times.

    Failure history:
    [list each failure with stage, error, attempted fixes]

    Evaluate:
    - CONTINUE: direction is sound, only implementation bugs remain
    - PIVOT: direction is flawed, try a different approach
    - ABORT: fundamental problems, terminate pipeline

    Provide detailed reasoning for your verdict.
    If PIVOT, suggest alternative approaches.
    If ABORT, write a postmortem summary.
```

---

## 使用说明

Leader skill 在执行对应 Phase 时，Read 本文件获取对应 prompt 模板，填入实际数据后调用 `mcp__codex__codex`。
