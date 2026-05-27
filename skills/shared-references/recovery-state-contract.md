# Recovery State Contract

Long-running ARIS workflows need a **small, explicit recovery contract** so transient failures and resumability are handled consistently instead of ad hoc. This document defines the minimum shared state shape, retry semantics, and stage-checkpoint expectations for recovery-sensitive tooling.

This contract is intentionally narrow:
- it does **not** replace markdown-first workflow artifacts
- it does **not** require a new orchestration framework
- it does provide a common receipt that tools and skills can inspect after interruption, retry, or restart

## When this contract applies

Use this contract whenever a workflow step is both:
1. **long-running or externally fragile** (remote job launch, API fetch, queue orchestration, watchdog monitoring), and
2. **load-bearing for downstream execution** (a crash or retry decision changes what runs next, what artifacts are trusted, or whether a stage can resume safely).

Typical examples:
- queue schedulers writing `queue_state.json`
- watchdog-style persistent monitors
- fetchers that retry transient API failures and need to surface retry state
- experiment-chain stage runners that may resume after crash / disconnect / rate limit

## Core principle

**Markdown remains the human-facing workflow record; JSON recovery state is the machine-facing continuity receipt.**

Do not migrate plans, audits, or claim narratives into JSON just because a process needs resumability. Instead:
- keep the canonical human artifact in markdown when that is already the repo pattern
- add a small JSON sidecar only for resumability, retry tracking, and stage continuity

## Required components

Every recovery-sensitive flow should provide all six:

### 1. Activation predicate — explicit and observable

The flow must have a clear external condition for when recovery state is expected.

- ✅ `queue_state.json` exists for an active experiment queue
- ✅ a fetch command is running with retry-enabled HTTP requests
- ❌ "if the run seems long enough"

### 2. Canonical state file — one machine-readable receipt

Each recovery-sensitive flow should have one canonical latest state file.
Examples:
- `refine-logs/RECOVERY_STATE.json`
- `queue_state.json`
- `watchdog/status/<task>.json`

If the file is overwritten on updates, version it using `shared-references/output-versioning.md`.

### 3. Minimal state schema — stable enough to inspect and resume

Recommended minimum fields:

```json
{
  "run_id": "exp-20260513-001",
  "stage": "sanity",
  "status": "running",
  "attempt": 2,
  "last_successful_step": "implementation_complete",
  "resume_cursor": "block:B1",
  "error_class": "transient_network",
  "backoff_until": "2026-05-13T12:00:00Z",
  "artifact_refs": [
    "refine-logs/EXPERIMENT_PLAN.md",
    "refine-logs/EXPERIMENT_TRACKER.md"
  ],
  "updated_at": "2026-05-13T11:58:20Z"
}
```

Field meanings:
- `run_id` — stable identifier for this run / recovery lineage
- `stage` — coarse workflow boundary currently active
- `status` — `pending` | `running` | `backoff` | `completed` | `failed`
- `attempt` — current retry or execution attempt count for the active stage
- `last_successful_step` — latest step definitely completed
- `resume_cursor` — fine-grained resume point, if needed
- `error_class` — normalized failure class for the latest blocking issue
- `backoff_until` — next eligible retry time for delayed retries
- `artifact_refs` — files already produced and still considered authoritative
- `updated_at` — last state write timestamp

Tools may extend this schema with local fields, but should not omit these without a strong reason.

### 4. Failure classification — bounded, not improvised

Normalize failures into a small shared vocabulary:

- `transient_network` — connection resets, temporary DNS / socket failures
- `retryable_http` — rate limit or retryable upstream/server response
- `retryable_parse` — malformed/empty retryable response where retry is explicitly allowed
- `validation_error` — bad input, bad config, schema mismatch, impossible arguments
- `environment_error` — missing binary, missing dataset, unavailable GPU, bad path
- `logic_error` — deterministic code bug or broken invariant
- `unknown` — temporary fallback when classification is not yet refined

This classification should appear in recovery state or equivalent logs when a retryable or terminal failure occurs.

### 5. Retry policy — explicit and capped

Recovery-sensitive tools must define which classes retry and which fail fast.

Recommended behavior:
- `transient_network` → bounded exponential backoff, resume from latest checkpoint
- `retryable_http` → bounded exponential backoff, stricter retry budget for rate-limits/quota pressure
- `retryable_parse` → retry only when the source/status class is explicitly marked retryable
- `validation_error` → fail fast, no retry loop
- `environment_error` → fail fast unless the tool has a concrete repair action
- `logic_error` → fail fast and surface actionable context

A retry policy should always specify:
- max attempts
- backoff schedule or formula
- what state/artifacts are written before sleeping or aborting

### 6. Stage checkpoints — resume at seams, not from scratch

Prefer coarse checkpoint boundaries already meaningful to the workflow. For the experiment chain, the natural seams are:
- plan validated
- implementation completed
- sanity completed
- audit completed
- claim verdict finalized

Resumption should restart from the current stage or finer resume cursor — **not** replay already-completed earlier stages unless authoritative artifacts are missing or invalid.

## Writing rules

- Write recovery state atomically.
- Prefer timestamped archive + latest-copy overwrite for load-bearing state files.
- Keep `artifact_refs` aligned with real files that downstream tools may trust.
- If a run is resumed after crash, update the same lineage (`run_id`) unless a user intentionally starts a fresh run.
- Silence is not success: if no retry/deviation/state receipt exists where one is required, downstream tools should treat recovery status as unknown rather than assumed-good.

## Relationship to experiment-chain artifacts

This recovery contract complements the experiment-chain contract:
- `EXPERIMENT_PLAN.md` defines intended execution
- implementation deviation sidecars explain plan drift
- recovery state explains **continuity across interruption / retry / restart**
- audits and claim gates may use recovery state as context, but should not replace their own integrity checks with it

## Recommended ARIS adoption points

Current best-fit adopters:
- `tools/semantic_scholar_fetch.py` — retry classification and backoff receipts when useful
- `tools/experiment_queue/queue_manager.py` — canonical scheduler resumability state
- `tools/watchdog.py` — persistent liveness/status receipts
- future experiment-chain runners that need stage-level resume guarantees

## Anti-patterns to refuse

- "We can just retry a few times" without recording attempt/backoff state
- "State is whatever the logs imply" when downstream logic needs a receipt
- Replaying the full workflow after a recoverable interruption despite valid upstream artifacts
- Treating missing recovery state as proof that nothing went wrong

## See Also

- `shared-references/integration-contract.md`
- `shared-references/output-versioning.md`
- `shared-references/output-manifest.md`
