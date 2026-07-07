# Labline Role Contract Matrix

Role Contract defines responsibility. Runtime Binding defines which model/session/provider runs the role. Changing a model must not change role responsibility.

## Default Runtime Binding

| Role | Default model | Transport shape |
|------|---------------|-----------------|
| Leader | `gpt-5.5` | Current main Codex session |
| Planner | `gpt-5.4` | Local planning agent or planning skill |
| Coder | `gpt-5.4-mini` | Local executor agent |
| Deployer | `gpt-5.4-mini` | Local executor agent |
| Writer | `gpt-5.4` | Local executor agent |
| Reviewer | `gpt-5.4` | Independent reviewer agent or review transport |

## Contracts

| Role | Owns | May use | Must produce | Must not do |
|------|------|---------|--------------|-------------|
| Leader | Human interaction, requirement clarification, gates, task dispatch, final decision | Read, Grep, Glob, Agent, Skill, status summary | Task briefs, gate decisions, user-facing summaries, pipeline state | Write code, run experiments, deploy, write final paper content, replace executors |
| Planner | Plan drafts, dependency decomposition, risk map, checkpoint proposal | Read, Grep, Glob, planning skills | Plan draft, task split, assumptions, open questions | Execute the plan, bypass Leader, approve its own plan |
| Coder | Code, tests, bug fixes, refactors | Read, Write, Edit, Bash for local tests | Changed file list, tests, implementation notes, deviation record | SSH, deploy, write paper, self-approve quality |
| Deployer | Remote/local execution, job handles, monitoring, result collection | Bash, Monitor, SSH/scp/rsync/tmux/screen as configured | Job handles, logs, result paths, tracker updates | Change code logic, write paper, modify experiment plan |
| Writer | Paper, report, documentation, rebuttal, patent text | Read, Write, Edit, WebSearch/WebFetch when needed | Draft files, cited result paths, claim/evidence mapping | Write experiment code, run experiments, invent results |
| Reviewer | Independent review of plan/code/experiment/claims/paper | Read original files, review transport | Verdict artifact, finding list, input scope, trace path | Use executor summaries as substitute for source files, fix issues for executor |

## Handoff Rules

- Leader dispatches tasks with role, scope, expected artifacts, tests/checks, and stop conditions.
- Leader dispatches every delegated role with `runtime-task-protocol.md` requirements, including `agent_id`, Runtime Task id, status update cadence, `next_expected_update`, terminal status, required artifacts, and replacement/resolution rules.
- Planner outputs drafts for Leader approval; it is not a hidden scheduler.
- Coder, Deployer, and Writer update Agent Status Stream for long or delegated work.
- Reviewer reads original inputs directly and records metadata separately from reasoning.
- Any role that hits a boundary writes a blocker or handoff instead of expanding its own scope.

## Runtime Task Protocol

All user-side roles must follow `runtime-task-protocol.md` when they are dispatched as separate agents or when they dispatch/replace another task.

| Role | Runtime obligation |
|------|--------------------|
| Leader | Assign `agent_id`, Runtime Task id, scope, expected artifacts, checks, stop condition, and status cadence; declare mandatory artifacts with `--required-artifact`; write `task.superseded`, `task.resolved_by`, or terminal `leader.decision` when old work is replaced or must not resume. |
| Planner | Write planning status and final plan artifact refs when dispatched; declare required plan artifacts before terminal success; never execute the plan or approve its own plan. |
| Coder | Write implementation progress, changed files, tests, blockers, deviations, and terminal artifacts; required implementation artifacts must exist before terminal success. |
| Deployer | Write deployment progress, durable job handles, log/result paths, monitor cadence, blockers, and terminal verdicts; required logs/results must exist before terminal success. |
| Writer | Write current section/document, output paths, cited result files, blockers, and terminal artifacts; required draft/report artifacts must exist before terminal success. |
| Reviewer | Write metadata only: transport, input scope, trace path, `--verdict-artifact` path, and terminal status; keep reasoning in review artifacts. |

Missing status, expected-update, required artifact, verdict artifact, or resolution is a runtime protocol violation, not merely a documentation issue. `lane status`, heartbeat, and auto-wakeup may derive `stale`, `anomaly`, or active escalation from missing fields. Runtime task validation rejects terminal success when required artifacts or Reviewer verdict artifacts are absent, and rejects retries that reuse the same task identity instead of linking with `--retry-of`.

## Model Override Rules

- A stronger model may be used for high-risk work without changing the role contract.
- A cheaper model may be used only when the task remains within the role's allowed scope and the output is reviewable.
- User-side cheap external providers are not default in the short term.
- Developer-side `dev-worker` is separate from user roles and defaults to `gpt-5.4-mini`.
