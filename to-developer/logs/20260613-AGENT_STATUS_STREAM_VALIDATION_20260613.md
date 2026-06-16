# Agent Status Stream Validation — 2026-06-13

## Purpose

Validate the first Agent Status Stream implementation before promoting it to the stable ARIS line. The target behavior is: Leader can observe delegated agents through project-local per-agent status snapshots without reading full transcripts, mutating runtime jobs, or committing project runtime state.

## Scope

Validated components:

- `tools/agent_status.py`
- `skills/shared-references/agent-status-stream.md`
- Leader/Coder/Deployer/Writer role instructions
- Reviewer independence notes for status metadata
- `.aris/status/` ignore rule
- Local GPU smoke on `aris-gpu` with 2 x RTX 3090

Not validated:

- Real remote SSH deployment
- Full ARIS research pipeline
- Watchdog integration
- Experiment queue integration

## Test-Driven Implementation

Behavior tests were added in `tests/test_agent_status.py` using tmp status roots only. Covered behaviors:

- `start` creates a schema v1 per-agent snapshot.
- `update` rewrites current status, artifacts, and job handles.
- `finish` records terminal status and blocker metadata.
- `summary` derives stale state without mutating the snapshot.
- `validate` reports schema and enum errors.
- `list` reports known agents.
- `--project-root` writes project-local runtime state under `.aris/status/`.
- Reviewer transport metadata is stored without review reasoning.

## Local GPU Smoke

Environment:

```text
host: aris-gpu
python: /usr/bin/python3
tmux: /usr/bin/tmux
gpu: 2 x NVIDIA GeForce RTX 3090
torch: 2.11.0+cu128, cuda=True, count=2
```

Smoke project:

```text
/tmp/aris-local-gpu-smoke.d5WjhY
```

Smoke flow:

1. Created a tmp project.
2. Started `deployer-local-gpu-001` status snapshot.
3. Launched a short tmux job that sampled `nvidia-smi`.
4. Updated the deployer snapshot to `waiting_on_job` with a tmux job handle.
5. Forced a stale read-time check with `--now 2026-06-13T21:06:00Z`.
6. Verified summary derived `agent_stale_task_alive`.
7. Waited for the tmux job to finish.
8. Finished the agent as `done`.
9. Ran `validate`.

Observed status output:

```text
deployer-local-gpu-001 deployer agent_stale_task_alive local GPU smoke running in tmux aris_status_smoke_155553
deployer-local-gpu-001 deployer done local GPU smoke complete
```

GPU log excerpt:

```text
0, NVIDIA GeForce RTX 3090, 894 MiB, 24576 MiB, 26 %
1, NVIDIA GeForce RTX 3090, 152 MiB, 24576 MiB, 41 %
```

## Checks Run

```text
python3 tests/test_agent_status.py
python3 -m py_compile tools/agent_status.py tests/test_agent_status.py
python3 tools/generate_skill_dag.py --check-only
python3 tests/test_skill_dag_contract.py
python3 tests/test_skill_catalog.py
python3 tests/test_install_aris_tools_symlink.py
python3 tests/test_codex_install_update.py
python3 tests/test_codex_skill_mirror.py
```

All checks passed.

## Findings

- Per-agent snapshot model works for Leader observability without writing repo-local runtime state.
- `agent_stale_task_alive` correctly distinguishes stale agent updates from alive long-running jobs when a job handle exists.
- Reviewer status needs transport/input-scope metadata, but review reasoning must stay in formal review artifacts/traces.
- Installed projects should call `.aris/tools/agent_status.py`; framework tests call `tools/agent_status.py`.
- Release tooling should not assume `python3.8` is present; `tag_release.sh` now uses `${PYTHON:-python3}`.

## Release Recommendation

Promote as a minor release (`v0.2.0`) because this adds a user-visible framework capability: project-local agent status snapshots and role-level status reporting protocol.
