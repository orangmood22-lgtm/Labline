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
- Planner outputs drafts for Leader approval; it is not a hidden scheduler.
- Coder, Deployer, and Writer update Agent Status Stream for long or delegated work.
- Reviewer reads original inputs directly and records metadata separately from reasoning.
- Any role that hits a boundary writes a blocker or handoff instead of expanding its own scope.

## Model Override Rules

- A stronger model may be used for high-risk work without changing the role contract.
- A cheaper model may be used only when the task remains within the role's allowed scope and the output is reviewable.
- User-side cheap external providers are not default in the short term.
- Developer-side `dev-worker` is separate from user roles and defaults to `gpt-5.4-mini`.
