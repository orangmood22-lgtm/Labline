# Agent Status Stream

Project-local status snapshots let Leader observe delegated agents without reading full transcripts.

## Location

Runtime status belongs to the research project, not the Labline framework repo:

```text
.labline/runtime/
  agents/<agent_id>.json
  events.jsonl          # optional diagnostics only
```

`.labline/status/agents/` is a legacy compatibility path. New agent snapshots must be written under `.labline/runtime/agents/`; readers may still ingest the legacy path during migration.

Do not commit `.labline/runtime/` or `.labline/status/`. Framework tests must use `--status-root` with a tmp dir or a temporary project root.

## Tool

Use `.labline/tools/agent_status.py` in installed projects; use `tools/agent_status.py` only inside the Labline framework repo. Do not hand-write JSON unless recovering from tool failure.

```bash
python3 .labline/tools/agent_status.py --project-root "$PWD" start \
  --agent-id deployer-20260613-001 \
  --role deployer \
  --task "run full experiments" \
  --current-action "starting remote sanity" \
  --next-expected-update "+10m" \
  --next-check-reason "remote sanity run"
```

Commands:

```text
start      create a status file
update     update current snapshot fields
finish     mark done, failed, or blocked
list       list known agents
summary    print compact Leader-readable status
validate   validate schema
```

## Snapshot Contract

Required fields:

```json
{
  "schema_version": 1,
  "agent_id": "deployer-20260613-001",
  "role": "deployer",
  "status": "waiting_on_job",
  "task": "run full experiments",
  "last_updated": "2026-06-13T21:00:00Z",
  "current_action": "training warmup, waiting for first eval",
  "next_expected_update": "2026-06-13T21:05:00Z",
  "next_check_reason": "first 20 minutes of formal training",
  "job_handles": [],
  "artifacts": [],
  "blocker": null
}
```

Status enum:

```text
starting | running | waiting_on_job | blocked | done | failed
```

`stale` is never written by agents. Leader or `agent_status.py summary` derives stale states at read time.

## Long Jobs

Long training, downloads, queue runs, or remote deployments must expose a durable job handle before the agent waits:

```bash
python3 .labline/tools/agent_status.py --project-root "$PWD" update \
  --agent-id deployer-20260613-001 \
  --status waiting_on_job \
  --current-action "training in tmux exp01" \
  --next-expected-update "+5m" \
  --next-check-reason "first 20 minutes of formal training" \
  --job-handle '{"type":"tmux","server":"3090x2","session":"exp01"}'
```

Expected update pacing:

| Situation | next expected update |
|-----------|----------------------|
| Short task | `+5m` |
| Remote sanity run | `+10m` |
| First 20 minutes of formal training | `+5m` |
| Stable training | `+30m` to `+60m` |
| Large batch queue | shortest queue ETA, capped at `+60m` |
| Download | `+15m` to `+30m` |
| Paper / writing agent | `+10m` to `+20m` |
| Failure retry or uncertain state | `+5m` to `+10m` |

## Remote Bridge And Push Discipline

When a Labline run is controlled through Feishu/Lark, the chat card is only a Remote Status Projection. It is not the runtime owner and must not be kept busy for long work.

- Treat any expected runtime over 3 minutes as a supervised long task: environment install, compile, download, training, deploy, batch evaluation, or long `wait_agent`.
- Before long work starts, write an Agent Status Snapshot or Runtime Task with `current_action`, durable `job_handles`, log/result paths, `next_expected_update`, and `next_check_reason`.
- After dispatch, the Leader may wait once for immediate failure, up to 120 seconds. If the task is still running, the Leader must end the current turn with the task id/status path/log path and let `/status`, `/follow`, heartbeat, or monitor surface later updates.
- Normal progress must be throttled or patched in place. Send a fresh visible reply only for `completed`, `failed`, `cancelled`, `blocked`, `need_decision`, `anomaly`, or heartbeat escalation.
- Healthy heartbeat checks write local runtime state only; they must not spam Feishu messages during a stable plateau.

## Read-Only Checks

When expected update time arrives, Leader may read status, queue state, watchdog summaries, logs, or monitor outputs. Leader must not restart jobs, kill sessions, redeploy code, change config, or mutate project artifacts through this status flow.

## Role Rules

- Leader reads snapshots and aggregates status; Leader does not edit agent-owned files.
- Coder writes implementation progress, test status, changed files, blockers, final artifacts; no quality self-assessment.
- Deployer writes deployment progress, server/session metadata, job handles, watchdog/queue pointers, result dirs, next update.
- Writer writes writing progress, current section, output paths, source result files, blockers; no invented experiment status.
- Reviewer writes metadata only: transport, input scope, trace path, status, verdict artifact path. Review reasoning stays in review artifacts/traces, not snapshot.

Reviewer transport enum:

```text
local_agent | background_agent | mcp_codex | mcp_gemini | cli_session | external_api
```
