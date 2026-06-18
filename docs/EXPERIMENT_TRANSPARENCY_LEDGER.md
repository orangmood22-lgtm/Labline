# Experiment Transparency Ledger

## Purpose

The Experiment Transparency Ledger is the canonical, project-local record of how an experiment moved from plan to run to audit to claim.

It is a documentation contract, not an execution engine contract. The ledger is meant to be readable and editable by any workflow runner, including plain filesystem-based workflows. It does not require LangGraph or any other orchestration framework.

## Module Boundary

Experiment Integrity is a workflow module, not a single skill.

The module spans the experiment lifecycle:

- `experiment-plan` defines the intended evaluation and claim ceiling.
- `experiment-bridge` records implementation-level deviations.
- `run-experiment` and related execution paths produce run evidence.
- `experiment-audit` checks honesty, scope, and traceability.
- `result-to-claim` translates evidence into claimable statements.

The ledger is the shared contract across those stages.

## Canonical Path

Use a project-local, repository-relative path. The default location is:

`refine-logs/EXPERIMENT_TRANSPARENCY_LEDGER.md`

Recommended adjacent paths:

- `refine-logs/EXPERIMENT_TRANSPARENCY_LEDGER.json` for machine-readable mirrors
- `refine-logs/IMPLEMENTATION_DEVIATIONS.json` for plan drift
- `refine-logs/EXPERIMENT_RESULTS/` for run outputs
- `refine-logs/checkpoints/` for resumable checkpoints

All entries should store paths relative to the project root. Do not require a LangGraph state store to interpret or update the ledger.

## Minimal Record Types

The ledger must be able to represent these record types at minimum:

1. `dataset`
2. `split`
3. `metric`
4. `run`
5. `deviation`
6. `artifact`
7. `claim`
8. `checkpoint`

## Skeleton Shape

This is the minimal schema skeleton. Implementations may add fields, but they should preserve these record classes and the trace links between them.

```text
dataset:
  dataset_id
  source_path
  version_or_snapshot
  license_or_access_note
  checksum_or_fingerprint

split:
  split_id
  dataset_id
  split_rule
  seed
  coverage_note

metric:
  metric_id
  name
  direction
  aggregation
  reported_value
  source_artifact_id

run:
  run_id
  entrypoint
  config_path
  code_ref
  started_at
  finished_at

deviation:
  deviation_id
  planned_reference
  actual_value
  reason
  claim_impact
  artifact_impact

artifact:
  artifact_id
  kind
  path
  checksum
  producer_run_id

claim:
  claim_id
  statement
  supporting_metric_ids
  supporting_artifact_ids
  scope_label

checkpoint:
  checkpoint_id
  phase
  resume_path
  status
  decision_note
```

## Contract Rules

- Every claim must point to the run, metric, and artifact records that support it.
- Every deviation must link back to the intended plan or metric it changes.
- Every checkpoint must be resumable from a project-local path.
- Every path stored in the ledger should be portable across machines and not depend on absolute local directories.

