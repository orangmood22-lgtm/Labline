# Runtime Task Protocol

This contract is mandatory for Labline roles that are dispatched by Leader or that dispatch other roles. It complements `agent-status-stream.md`: status snapshots describe current liveness, while runtime events describe lifecycle decisions such as cancellation, replacement, and resolution.

## Applies To

| Role | Protocol responsibility |
|------|-------------------------|
| Leader | Dispatch roles with an `agent_id`, expected artifacts, stop condition, and runtime protocol reminder; record terminal decisions and replacement/resolution events for old tasks. |
| Planner | Record planning progress and final plan artifacts when dispatched as a separate agent; do not execute the plan. |
| Coder | Record implementation progress, changed files, tests, blockers, terminal artifacts, and deviations. |
| Deployer | Record deployment progress, durable job handles, logs, result paths, blockers, and terminal verdicts. |
| Writer | Record current section/document, output paths, cited result files, blockers, and terminal artifacts. |
| Reviewer | Record metadata only: transport, input scope, trace path, verdict artifact path, and terminal status. Review reasoning belongs in review artifacts, not status snapshots. |

## Status Snapshot

At start, update, and finish, dispatched agents must use `.labline/tools/agent_status.py` in installed projects. Use `tools/agent_status.py` only inside the Labline framework repository.

Minimum snapshot fields:

```json
{
  "agent_id": "coder-r003-config-20260706",
  "role": "coder",
  "status": "running",
  "task": "generate minimal R003 config",
  "current_action": "writing config and parser check",
  "next_expected_update": "2026-07-06T09:30:00Z",
  "next_check_reason": "config parse and artifact integrity check",
  "job_handles": [],
  "artifacts": [],
  "blocker": null
}
```

Agents must not write `stale` or `anomaly` themselves. Those are derived by runtime readers when expected updates are missed or required handles are absent.

## Runtime Task Record

Leader must create or update a Runtime Task record for every delegated role before accepting its outcome. The runtime schema and validator are the source of truth; role prompts and Skill DAG edges are only projections of this contract.

Minimum delegated-agent dispatch record:

```bash
python .labline/tools/lane runtime task create agent-coder-r003-config \
  --kind agent \
  --title "generate R003 config" \
  --owner Coder \
  --status dispatching \
  --next-expected-update 2026-07-06T09:30:00Z \
  --required-artifact refine-logs/R003/config.py
```

Runtime preflight rejects a non-terminal delegated agent task that has no `next_expected_update`. This makes the boot observation window explicit: if the task remains `starting` past that timestamp with no job handle, runtime readers classify it as an observability anomaly rather than a role verdict.

Role-specific terminal artifacts are declared on the task:

- Use `--required-artifact PATH` for every artifact that must exist before `completed` or `resolved`.
- Reviewer tasks must also set `--verdict-artifact PATH` before terminal success; review reasoning belongs in that artifact, not in status snapshots.
- Terminal success is accepted only after declared required artifacts and Reviewer verdict artifacts exist in the project.

## Observability Failure Retry Policy

An observability failure is a transport/executor failure, not a Coder/Reviewer/Deployer verdict. Treat these as observability failures:

- `observability_failure=true`
- `boot_no_progress`
- `handle returned not_found`
- `starting` past `next_expected_update` with no `job_handles`
- required verdict or result artifact missing after the owner should have finished

After an observability failure, a retry must change both Runtime Task identity and transport evidence. Leader must not keep retrying the same gate through the same naked `local_agent` / background-agent path. The next attempt must either:

- use a foreground independent transport such as `cli_session`, Codex exec, MCP reviewer bridge, or another review transport that writes agent status and verdict artifacts; or
- persist a JSON-object `job_handles` entry and observe an agent status start/update within the first 120 seconds.

If neither condition is met, record a terminal `leader.decision` with `status=failed` or `cancelled`, keep the gate `not_passed`, and repair/probe executor transport before another delegated retry. Reviewer gates must use a verdict such as `NO_VERDICT_EXECUTION_FAILURE` for this case; do not report scientific PASS/FAIL without a verdict artifact.

For a short Reviewer gate retry, prefer the built-in foreground transport so the handle, status file, and verdict gate are written by one runtime command:

```bash
python .labline/tools/lane workflow foreground-review task-reviewer-r003-retry2 \
  --agent-id reviewer-r003-retry2 \
  --prompt-file prompts/reviewer-r003-retry2.md \
  --verdict-artifact refine-logs/R003_REVIEW_RETRY2.md
```

This command records a `cli_session` job handle before running `codex exec`, writes `.labline/runtime/agents/<agent_id>.json`, stores transport stdout/stderr under `.labline/runtime/transports/`, and marks the Runtime Task completed only if the Codex process exits 0 and the verdict artifact exists. If the verdict is missing, it marks the task failed with `NO_VERDICT_EXECUTION_FAILURE`.

## Long Work

Any task expected to exceed 3 minutes must expose a durable handle before waiting:

- tmux/screen session
- local job id
- queue/watchdog state path
- log path
- result directory

For tmux-backed local work, prefer the built-in launcher so the handle, job record, and agent status are written by one runtime command:

```bash
python .labline/tools/lane workflow tmux-job task-deployer-r003-retry2 \
  --agent-id deployer-r003-retry2 \
  --session r003_retry2 \
  --command 'python tools/train.py configs/r003.py --work-dir outputs/r003' \
  --log refine-logs/R003_retry2.log \
  --required-artifact outputs/r003/epoch_2.pth
```

This command writes a `tmux` job handle, `.labline/runtime/jobs/<job_id>.json`, `.labline/runtime/jobs/<job_id>.exitcode`, `.labline/runtime/agents/<agent_id>.json`, and a `job.started` event. The launcher only needs to persist the durable handle; it may exit after that. It does not mark the task completed. Runtime wakeup checks the detached tmux session later: an inactive session with exit code 0 or no exit-code sentinel yet and all required artifacts becomes `detached_job_completed`; an inactive session with a non-zero exit code or missing required artifacts becomes `detached_job_exited`. Leader must inspect the session/log/result artifact and then record completed/failed/continue-waiting.

For immediate read-only inspection, use:

```bash
python .labline/tools/lane workflow job-status TASK_ID --json
```

This returns `job_observations` and the same `wakeup_candidate` shape used by auto-wakeup. It does not write runtime state or mark the task terminal.

The agent must set `status=waiting_on_job`, `next_expected_update`, and `next_check_reason`. The chat card is only a projection; it is not the task owner.

## Terminal States

When a role stops owning a task, it must write a terminal status:

```text
done | failed | blocked
```

Leader-side runtime aggregation normalizes terminal task events to:

```text
completed | failed | cancelled | superseded | resolved
```

Use `blocked` only when human or upstream action is required and the task is still a meaningful blocker. Use `failed` for a real failed attempt. Use `cancelled`, `superseded`, or `resolved` through runtime events when the old attempt should no longer be resumed.

Terminal success must pass the artifact gate:

```bash
python .labline/tools/lane runtime task complete agent-reviewer-r003 \
  --verdict-artifact refine-logs/R003/REVIEW.md
```

For Coder, Deployer, Writer, and Planner, declare mandatory result files with `--required-artifact` when creating or updating the task, then complete the task only after those paths exist.

## Resolution Events

When a later task, main session exception, or artifact replaces an older task, Leader or the authorized owner must append one of these runtime events:

```bash
python .labline/tools/lane runtime event append \
  --type task.superseded \
  --task-id agent:old-task-id \
  --json '{"resolved_by_task_id":"agent:new-task-id","reason":"new task produced the required artifact"}'
```

Valid resolution event types:

```text
task.superseded
task.resolved
task.resolved_by
```

Terminal `leader.decision` events with `status=cancelled|completed|failed|superseded|resolved` are also consumed by runtime summaries. Prefer explicit `task.superseded` / `task.resolved_by` when one task replaced another.

## Retry Identity

A retry is never the same Runtime Task. It receives a new Runtime Task identity. Leader must create a fresh task id and link it to the old attempt:

```bash
python .labline/tools/lane runtime task create agent-reviewer-r003-retry1 \
  --kind agent \
  --title "retry R003 review" \
  --owner Reviewer \
  --status dispatching \
  --next-expected-update 2026-07-06T09:45:00Z \
  --retry-of agent-reviewer-r003
```

After the retry is accepted, mark the old attempt with `task.superseded`, `task.resolved_by`, or a terminal `leader.decision`. Runtime validation rejects a retry whose `task_id` equals `retry_of`, including the common `agent:` prefix variant.

## Leader Dispatch Requirements

Every dispatched role prompt must include:

- `agent_id`
- role name
- scope and boundaries
- expected artifacts
- checks/tests to run or explicitly skip
- stop condition
- status snapshot requirement
- Runtime Task requirement, including `next_expected_update`
- `--required-artifact` paths and, for Reviewer, `--verdict-artifact`
- resolution requirement for handoff/replacement
- path to this protocol reference

If Leader dispatches a replacement task, Leader must mark the old task with `task.superseded` or `task.resolved_by` after the replacement is accepted.

## Hard Validation

Runtime readers intentionally treat missing protocol signals as risk:

- no status file -> not observable
- no `next_expected_update` on running agent -> stale after grace
- `starting` past expected update with no job handle -> anomaly
- delegated non-terminal Runtime Task with no `next_expected_update` -> rejected at creation/update
- terminal success with missing `--required-artifact` path -> rejected
- Reviewer terminal success with no `--verdict-artifact` or missing verdict file -> rejected
- retry task with the same id as `--retry-of` -> rejected
- old escalation with no resolution event -> wakeup candidate
- unresolved `failed` / `cancelled` terminal Runtime Task -> `terminal_result` wakeup candidate
- detached `tmux` job session inactive, exit code 0 or unknown, and required artifacts present -> `detached_job_completed` wakeup candidate
- detached `tmux` job session inactive and non-zero exit code or required artifacts missing -> `detached_job_exited` wakeup candidate
- task id referenced by another Runtime Task's `retry_of` -> not resumed by wakeup
- completed/resolved/superseded task id, or any task id with terminal `leader.decision` -> not resumed by wakeup

Do not suppress these by prose. Write the runtime status or event.
