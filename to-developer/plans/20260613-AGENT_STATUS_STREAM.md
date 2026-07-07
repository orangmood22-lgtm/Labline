# Agent Status Stream Plan

This plan tracks the rollout of project-local agent status snapshots for ARIS. The goal is to let Leader observe running agents without reading full transcripts or polluting planning context.

## Accepted Decisions

- Use project-local filesystem state, not a framework-owned runtime store.
- Real runtime state lives under project `.aris/status/` and is not committed.
- Framework development and tests use isolated tmp status roots only.
- Each agent owns one status file; no shared mutable snapshot is written by multiple agents.
- Leader normally reads current snapshots, not full event history.
- Optional `events.jsonl` may exist for diagnostics, but it is not the normal Leader input.
- Long-running tasks must expose a durable job handle that can be checked independently of the launching agent.
- Expected update time is an observation pacing hint, not a hard failure deadline.
- Leader may automatically perform read-only status checks when expected update time arrives.
- Mutating recovery actions still require explicit user approval or normal skill safety gates.
- Reviewer is a role, not a Codex MCP synonym; status records the review transport.
- Reviewer status snapshots contain metadata only, not review reasoning or executor summaries.

## Status Directory

Default project layout:

```text
.aris/status/
  agents/
    <agent_id>.json
  events.jsonl          # optional diagnostic append log
```

Framework tests must avoid writing to the framework repository by using a tmp directory:

```bash
python3 tools/agent_status.py --status-root /tmp/aris-agent-status-test start ...
```

The eventual project templates should ignore runtime status:

```gitignore
.aris/status/
```

## Snapshot Schema v1

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

Derived read-time states:

```text
stale
agent_stale_task_alive
agent_stale_task_unknown
agent_stale_task_failed
```

These derived states are computed by Leader or `agent_status.py summary`; agents do not write them into their status file.

Optional fields:

```json
{
  "transport": "background_agent",
  "review_independence": "fresh_original_inputs",
  "input_scope": ["refine-logs/EXPERIMENT_PLAN.md"],
  "trace_path": ".aris/traces/experiment-audit/20260613_run01/"
}
```

Initial `transport` enum:

```text
local_agent | background_agent | mcp_codex | mcp_gemini | cli_session | external_api
```

## Expected Update Policy

Default pacing:

| Situation | next_expected_update |
|-----------|----------------------|
| Short task | now + 5 min |
| Remote sanity run | now + 10 min |
| First 20 minutes of formal training | now + 5 min |
| Stable training | now + 30-60 min |
| Large batch queue | shortest ETA from `queue_state.json`, capped at 60 min |
| Download | now + 15-30 min |
| Paper / writing agent | now + 10-20 min |
| Failure retry or uncertain state | now + 5-10 min |

When the expected update time arrives, Leader may do read-only checks only:

- read `.aris/status/agents/*.json`
- run `agent_status.py summary`
- inspect queue state
- read watchdog summaries
- read logs or monitor outputs

Leader must not use the status flow to restart jobs, kill sessions, redeploy code, change config, or mutate project artifacts.

## Role Responsibilities

### Leader

- Creates or requests agent ids when dispatching agents.
- Requires every delegated long-running or background task to write status.
- Reads snapshots and aggregates the current picture.
- Treats `stale` as a prompt to inspect job handles, not as immediate task failure.
- Does not edit agent-owned status files.

### Coder

- Writes implementation progress, tests being run, changed file paths, blockers, and final artifacts.
- Does not write quality self-assessment into status.
- Keeps code review decisions for Leader + Reviewer.

### Deployer

- Writes deployment progress, server/session metadata, job handles, watchdog/queue pointers, result directories, and next expected update.
- Must not foreground long training/download commands as the only progress source.
- For long tasks, starts or registers a durable job handle before waiting.

### Writer

- Writes writing progress, current section, output paths, source result files, and blockers.
- Does not invent experiment status or claim validation.
- Leaves paper quality judgement to Leader + Reviewer.

### Reviewer

- Writes only review metadata: transport, input scope, trace path, status, and verdict artifact path.
- Does not write review reasoning into the status snapshot.
- Must preserve reviewer independence: fresh original inputs, no executor summary as a substitute for source files.

## CLI Scope

`tools/agent_status.py` v1 commands:

```text
start      create a status file
update     update current snapshot fields
finish     mark done, failed, or blocked
list       list known agents
summary    print compact Leader-readable status
validate   validate schema and report stale derived states
```

Path options:

```text
--project-root PATH   write/read PATH/.aris/status
--status-root PATH    write/read PATH directly; for tests and debugging
```

The CLI must not SSH, start jobs, call watchdog, run monitor skills, deploy code, or mutate experiment artifacts.

## Rollout Plan

### Phase 1: Protocol and Tool

- Add `tools/agent_status.py`.
- Add tests for schema validation, status enum, relative times such as `+5m`, summary output, and stale derivation.
- Add `skills/shared-references/agent-status-stream.md`.
- Ensure tests use tmp status roots.

### Phase 2: Leader Integration

- Update `skills/leader/SKILL.md` dispatch prompts to assign agent ids and require status writes.
- Require Deployer background and long-running tasks to write job handles before waiting.
- Teach Leader to use `agent_status.py summary` before asking the user about running agents.

### Phase 3: Executor Roles

- Update `skills/coder/SKILL.md` with status responsibilities.
- Update `skills/deployer/SKILL.md` with job handle and expected update rules.
- Update `skills/writer/SKILL.md` with writing-progress status rules.
- Update `skills/shared-references/agent-guide.md` so all executor agents inherit the protocol.

### Phase 4: Reviewer Adaptation

- Update reviewer-aware shared references to record reviewer transport and trace paths.
- Keep review content in formal review artifacts and traces, not in status snapshots.
- Cover Codex MCP, Gemini MCP, spawned reviewer agent, CLI session, and external API transports.

### Phase 5: Templates and Docs

- Update `templates/AGENTS_MD_TEMPLATE.md` and `templates/CLAUDE_MD_TEMPLATE.md`.
- Update `docs/TRIPARTITE_ARCHITECTURE_GUIDE.md` to describe status snapshots without presenting them as a user-facing requirement.
- Update project `.gitignore` template or installer behavior to ignore `.aris/status/`.

### Phase 6: Optional Diagnostics

- Add optional append-only `events.jsonl` for debugging status changes.
- Keep Leader default path on compact snapshots.
- Use event logs only for diagnosis, post-mortem, or tool tests.

## Non-Goals

- No central scheduler in v1.
- No peer-to-peer agent chat.
- No replacement for `Pipeline Status`.
- No replacement for `MANIFEST.md`, review traces, watchdog, experiment queue, or formal result files.
- No LangGraph dependency in the first rollout.
