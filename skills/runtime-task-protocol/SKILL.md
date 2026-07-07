---
name: runtime-task-protocol
description: Runtime Task protocol contract for dispatched Labline roles. Use when acting as or dispatching Leader, Planner, Coder, Deployer, Writer, or Reviewer so status snapshots, terminal decisions, and superseded/resolved task events are written consistently.
argument-hint: "[role/task-id/status-scenario]"
caller: any
platform: both
status: active
examples:
  - "/runtime-task-protocol coder-r003"
  - "apply runtime protocol to this delegated task"
  - "how should I mark this old task superseded"
---

# Runtime Task Protocol

Use this skill as a contract, not as a work-producing workflow.

## Required Reference

Read `../shared-references/runtime-task-protocol.md` before dispatching or acting as a delegated Labline role.

## Required Behavior

- If you dispatch a role, include an `agent_id`, status/update expectations, artifact expectations, and the requirement to follow `runtime-task-protocol.md`.
- If you are a dispatched role, write your own status snapshot at start, meaningful progress, blockers, and terminal state.
- If you launch or wait on long work, write a durable job handle and `next_expected_update` before waiting.
- If a task is replaced, do not leave the old task stale. Write or request `task.superseded`, `task.resolved`, or `task.resolved_by`.
- If Leader decides an old task must not resume, write a terminal `leader.decision` with an explicit terminal `status`.

## Non-Negotiable

Prose summaries do not satisfy runtime protocol. The framework only wakes, suppresses, or folds tasks from status snapshots and runtime events.
