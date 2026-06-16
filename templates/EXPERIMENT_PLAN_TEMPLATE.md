# Experiment Plan

> **Template for Workflow 1.5 (`$experiment-bridge`).** Fill in, save as `refine-logs/EXPERIMENT_PLAN.md`, then run `$experiment-bridge`.

**Problem**: [What problem does your method solve?]
**Method Thesis**: [One-sentence description of your approach]
**Date**: [YYYY-MM-DD]

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|----------------|----------------------------|---------------|
| C1: [Main claim] | [Why] | [Evidence needed] | B1, B2 |
| C2: [Supporting claim] | [Why] | [Evidence needed] | B3 |

## Paper Storyline
- **Main paper must prove**: [What absolutely needs to land in the main narrative]
- **Appendix can support**: [Helpful but non-blocking evidence]
- **Experiments intentionally cut**: [What you are *not* planning to run and why]

## Expectation Declaration
- **Preconditions for a meaningful run**: [Required datasets, checkpoints, hardware, labels, official eval availability]
- **Evaluation intent**: [What split should be used, what counts as the authoritative target / GT]
- **Baseline availability assumptions**: [Which baselines must reproduce or be available to make the comparison valid]
- **Stop conditions**: [What would make you halt before scaling up]

## Execution Spec

### Block 1: Main Result
- **Claim tested**: C1
- **Why this block exists**: [Why this block changes a reviewer belief]
- **Dataset / split / task**: [e.g., ImageNet val]
- **Compared systems**: [Your method vs. Baseline A vs. Baseline B]
- **Metrics**: [Primary: accuracy/PPL. Secondary: throughput]
- **Setup details**: [Backbone, optimizer, lr, epochs, seeds]
- **Success criterion**: [e.g., "> 2% accuracy over baseline"]
- **Failure interpretation**: [If negative, what does it mean?]
- **Table / figure target**: [Main table / appendix / qualitative figure]
- **Priority**: MUST-RUN

### Block 2: Ablation Study
- **Claim tested**: C1 (novelty isolation)
- **Why this block exists**: [Which component or mechanism it isolates]
- **Dataset / split / task**: [Same or different setting]
- **Compared systems**: [Full method, -component A, -component B]
- **Metrics**: [Which metrics matter here]
- **Setup details**: [Config deltas from the main block]
- **Success criterion**: [Each component contributes > 0.5%]
- **Failure interpretation**: [What a null result implies]
- **Table / figure target**: [Ablation table / appendix]
- **Priority**: MUST-RUN

### Block 3: [Additional Experiment]
- **Claim tested**: [Claim ID]
- **Why this block exists**: [Purpose]
- **Dataset / split / task**: [...]
- **Compared systems**: [...]
- **Metrics**: [...]
- **Setup details**: [...]
- **Success criterion**: [...]
- **Failure interpretation**: [...]
- **Table / figure target**: [...]
- **Priority**: NICE-TO-HAVE

## Data Flow Summary
- **Inputs**: [Dataset / labels / prompts / checkpoints consumed]
- **Transformation path**: [Data loader → preprocessing → model path → post-processing]
- **Outputs**: [Predictions, metrics, artifact files]
- **Ground truth source**: [Exact source of authoritative labels / targets]
- **Saved result files**: [JSON / CSV / logs expected from each block]

## Delta Assertion
- **Control / baseline**: [What result or variant the new method must differ from]
- **Expected concrete difference**: [What output / metric / intermediate behavior should change]
- **How to detect “no real effect”**: [Numerical equality, identical outputs, dead path, unchanged activations, etc.]
- **Sanity trigger**: [What quick run should reveal the difference before full-scale execution]

## Evidence Mapping

| Claim | Supporting Blocks | Expected Result Files | Notes for Audit / Claim Gate |
|-------|-------------------|-----------------------|------------------------------|
| C1 | B1, B2 | results/main.json, results/ablation.json | [What downstream audit should verify] |
| C2 | B3 | results/block3.json | [Caveats or dependencies] |

## Implementation Deviation Protocol
- **Canonical sidecar path**: `refine-logs/IMPLEMENTATION_DEVIATIONS.json`
- **When to write it**: whenever implementation or execution diverges from this plan, or when bridge explicitly verifies that no deviations exist at the checked scope
- **Minimum per-deviation fields**:
  - `plan_reference`
  - `deviation_type`
  - `planned_value`
  - `actual_value`
  - `reason`
  - `claim_impact`
  - `artifact_impact`
  - `status`
  - `owner`
  - `timestamp`
- **Allowed `claim_impact` values**: `none` | `narrow_scope` | `weakens_evidence` | `breaks_claim_test`
- **Allowed `status` values**: `planned` | `accepted` | `unresolved`
- **No-drift receipt rule**: if no deviations exist, still emit an explicit sidecar stating the checked scope matched plan so audit / claim stages do not have to infer silence as success

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|-----------|------|------|---------------|------|------|
| M0: Sanity | Pipeline works and delta path is live | 1 quick run | Loss decreases and expected delta appears? | ~0.5h | [Main risk] |
| M1: Baselines | Reproduce baselines | Block 3 | Numbers match? | ~4h | [Risk] |
| M2: Main | Full method | Block 1 | Meets criterion? | ~8h | [Risk] |
| M3: Ablation | Components | Block 2 | Each matters? | ~6h | [Risk] |

## Compute and Data Budget
- **Total estimated GPU-hours**: ~18h
- **Hardware**: [e.g., 4x RTX 3090]
- **Data preparation needs**: [Any preprocessing, downloads, annotation, cleanup]
- **Human evaluation needs**: [If any]
- **Biggest bottleneck**: [e.g., baseline reproduction]

## Risks and Mitigations
- **Risk**: [What could go wrong] → **Mitigation**: [How to handle it]

## Final Checklist
- [ ] Main paper tables are covered
- [ ] Novelty is isolated
- [ ] Simplicity is defended
- [ ] Frontier contribution is justified or explicitly not claimed
- [ ] Must-run and nice-to-have runs are separated
- [ ] Expected split / GT source is explicit
- [ ] Delta assertion is testable before scale-up
- [ ] Every claim maps to concrete result files
- [ ] Audit / claim gate has enough traceability to verify the chain
- [ ] Implementation deviation sidecar rules are understood before execution begins
- [ ] Any future plan drift can be recorded without ambiguity about claim or artifact impact
