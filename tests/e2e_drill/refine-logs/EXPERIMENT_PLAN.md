# Experiment Plan

> **Template for Workflow 1.5 (`/experiment-bridge`).** Fill in, save as `refine-logs/EXPERIMENT_PLAN.md`, then run `/experiment-bridge`.

**Problem**: Simple MLPs underperform on image classification; we hypothesize an attention-augmented classifier can do better.
**Method Thesis**: ToyClassifier adds a lightweight channel-attention module to a baseline MLP, improving CIFAR-10 accuracy by routing features through learned importance weights.
**Date**: 2026-05-14

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|----------------|----------------------------|---------------|
| C1: ToyClassifier outperforms BaselineMLP by ≥5% accuracy on CIFAR-10 test set | Validates that channel attention adds value over plain MLP | accuracy delta ≥5% on official test split, seed=42 | B1, B2 |

## Paper Storyline
- **Main paper must prove**: Channel attention meaningfully improves classification accuracy over a baseline MLP on CIFAR-10.
- **Appendix can support**: Per-class accuracy breakdown, attention weight visualizations.
- **Experiments intentionally cut**: No comparison with CNNs or ViTs (out of scope for this claim).

## Expectation Declaration
- **Preconditions for a meaningful run**: CIFAR-10 dataset available (torchvision auto-download), PyTorch installed, single GPU or CPU.
- **Evaluation intent**: Evaluate on the official CIFAR-10 **test** split (10,000 images). Ground truth = dataset-provided integer class labels (0-9).
- **Baseline availability assumptions**: BaselineMLP is implemented in-repo; no external reproduction needed.
- **Stop conditions**: If sanity run shows ToyClassifier accuracy == BaselineMLP accuracy (no delta), halt and debug before scaling.

## Execution Spec

### Block 1: Main Result
- **Claim tested**: C1
- **Why this block exists**: Directly tests whether channel attention yields measurable improvement over baseline MLP
- **Dataset / split / task**: CIFAR-10 / **test** split / 10-class classification
- **Compared systems**: ToyClassifier (with channel attention) vs BaselineMLP (plain MLP)
- **Metrics**: Primary: top-1 accuracy
- **Setup details**: Hidden dim=256, attention bottleneck=64, optimizer=Adam, lr=1e-3, epochs=10, seed=42
- **Success criterion**: ToyClassifier accuracy - BaselineMLP accuracy ≥ 5%
- **Failure interpretation**: Channel attention module does not provide sufficient benefit; may be bypassed or ineffective
- **Table / figure target**: Main table (Table 1)
- **Priority**: MUST-RUN

### Block 2: Ablation Study
- **Claim tested**: C1 (novelty isolation)
- **Why this block exists**: Confirms the attention module is the source of improvement by removing it
- **Dataset / split / task**: CIFAR-10 / **test** split / 10-class classification
- **Compared systems**: ToyClassifier (full) vs ToyClassifier-NoAttention (attention module removed)
- **Metrics**: Primary: top-1 accuracy
- **Setup details**: Same as Block 1 but with attention module disabled
- **Success criterion**: ToyClassifier - ToyClassifier-NoAttention ≥ 2%
- **Failure interpretation**: Attention module is not contributing; improvement comes from elsewhere
- **Table / figure target**: Ablation table (Table 2)
- **Priority**: MUST-RUN

## Data Flow Summary
- **Inputs**: CIFAR-10 dataset (torchvision), 50k train + 10k test, 32x32 RGB images, integer labels 0-9
- **Transformation path**: torchvision.datasets.CIFAR10 → DataLoader → flatten to 3072-d vector → MLP/ToyClassifier → softmax → predicted class
- **Outputs**: Per-model accuracy on eval split, saved as JSON
- **Ground truth source**: CIFAR-10 official test labels provided by torchvision (train=False)
- **Saved result files**: `results/main_result.json` (Block 1), `results/ablation_result.json` (Block 2)

## Delta Assertion
- **Control / baseline**: BaselineMLP output predictions and accuracy
- **Expected concrete difference**: ToyClassifier should produce different per-sample predictions and higher overall accuracy than BaselineMLP
- **How to detect "no real effect"**: If ToyClassifier accuracy == BaselineMLP accuracy (difference < 0.1%), or if per-sample predictions are identical, the attention module is likely bypassed/dead
- **Sanity trigger**: Run both models on a 100-sample subset; ToyClassifier predictions should differ from BaselineMLP on at least 5% of samples

## Evidence Mapping

| Claim | Supporting Blocks | Expected Result Files | Notes for Audit / Claim Gate |
|-------|-------------------|-----------------------|------------------------------|
| C1 | B1, B2 | results/main_result.json, results/ablation_result.json | Verify eval on test split; verify delta > 0; verify attention module is on forward path |

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
| M0: Sanity | Pipeline works and delta path is live | 1 quick run (100 samples) | Predictions differ between models? | ~1min | Dead attention path |
| M1: Main | Full evaluation | Block 1 | accuracy delta ≥ 5%? | ~5min | No improvement |
| M2: Ablation | Isolate attention contribution | Block 2 | ablation delta ≥ 2%? | ~5min | Attention not causal |

## Compute and Data Budget
- **Total estimated GPU-hours**: ~0.2h (toy experiment, CPU-feasible)
- **Hardware**: CPU or single GPU
- **Data preparation needs**: None (torchvision auto-download)
- **Human evaluation needs**: None
- **Biggest bottleneck**: None (toy scale)

## Risks and Mitigations
- **Risk**: Attention module silently bypassed → **Mitigation**: Delta assertion checks predictions differ
- **Risk**: Wrong eval split used → **Mitigation**: Explicit split check in audit

## Final Checklist
- [x] Main paper tables are covered
- [x] Novelty is isolated
- [x] Simplicity is defended
- [x] Frontier contribution is justified or explicitly not claimed
- [x] Must-run and nice-to-have runs are separated
- [x] Expected split / GT source is explicit
- [x] Delta assertion is testable before scale-up
- [x] Every claim maps to concrete result files
- [x] Audit / claim gate has enough traceability to verify the chain
- [x] Implementation deviation sidecar rules are understood before execution begins
- [x] Any future plan drift can be recorded without ambiguity about claim or artifact impact
