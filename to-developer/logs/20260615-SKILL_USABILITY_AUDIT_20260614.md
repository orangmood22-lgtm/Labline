# ARIS Skill Usability Audit — 2026-06-14

## Purpose

Overnight practical audit of ARIS skill usability. The goal was not to execute every skill end-to-end, because many skills can mutate files, push Git state, call paid APIs, rent GPUs, deploy to servers, or send external messages. Instead, the audit checked whether each skill is practically usable from its current instructions, whether it has a safe smoke path, and what would block real project use.

## Method

Four parallel sub-agents audited skills by caller class:

- `leader`: `to-developer/logs/skill-usability-parts/20260615-leader.md`
- `executor`: `to-developer/logs/skill-usability-parts/20260615-executor.md`
- `reviewer`: `to-developer/logs/skill-usability-parts/20260615-reviewer.md`
- `any`: `to-developer/logs/skill-usability-parts/20260615-any.md`

Safety policy:

- No destructive actions.
- No network/API/SSH/cloud/GPU rental/deploy/push actions.
- No real experiment launch.
- Only static reading, parser checks, local tests, and safe command help/check modes.

Local mechanical checks run:

```text
python3 tools/generate_skill_dag.py --check-only
python3 tests/test_skill_dag_contract.py
python3 tests/test_skill_catalog.py
python3 tests/test_agent_status.py
python3 tests/test_release_tools.py
python3 tests/test_codex_skill_mirror.py
python3 tests/test_install_aris_tools_symlink.py
```

All checks passed.

## Summary

Top-level skills audited: 94.

| Rating | Count | Meaning |
|---|---:|---|
| usable | 14 | Practical now with local inputs and low operational risk. |
| usable-with-caution | 57 | Useful, but needs preflight, dry-run, external dependency check, or clearer role boundary. |
| blocked | 23 | Should not be used unattended until safety/runtime/dry-run gaps are fixed. |

Caller distribution:

| Caller | Count |
|---|---:|
| leader | 22 |
| executor | 37 |
| reviewer | 11 |
| any | 24 |

Metadata gap:

- 77 / 94 top-level skills omit explicit `platform`.
- 77 / 94 top-level skills omit explicit `status`.
- 53 / 94 mention risk-bearing actions or deps such as web, SSH, rsync, Git push, cloud GPU, paid services, or secrets.

One archived duplicate was also flagged but not counted in the 94: `skills/skills-codex/review/SKILL.md` duplicates top-level `review` and remains `needs-runtime-adaptation`.

## Highest-Risk Findings

### 1. `caller: leader` is overloaded

Many `caller: leader` skills are really top-level workflow orchestrators, but `/leader` defines a stricter role: read, judge, delegate. Several leader-caller skills directly write files, run commands, call MCP/API, compile papers, deploy experiments, or edit project artifacts.

Impact: Leader role boundary becomes confusing. A user may think Leader is safe while the skill performs executor-grade actions.

Fix:

- Split `caller: leader` into stricter `caller: leader` and broader `caller: orchestrator`, or update every pipeline skill to delegate concrete execution to Coder/Deployer/Writer/Reviewer.
- Remove direct `Bash(*)`, `Write`, and `Edit` from true Leader skills unless explicitly documented as a narrow exception.

### 2. Blocked skills lack safe dry-run paths

Blocked skills are mostly powerful and valuable, but too risky for unattended use:

- remote/GPU/cloud: `run-experiment`, `experiment-queue`, `training-check`, `vast-gpu`, `serverless-modal`
- sync/admin: `sync`, `framework-update`, `init-research`, `overleaf-sync`
- full pipelines: `research-pipeline`, `paper-writing`, `paper-talk`, `resubmit-pipeline`, `auto-review-loop*`
- external platforms: `qzcli`
- issue backend: `to-prd`, `to-issues`

Fix:

- Add mandatory `--dry-run` or `plan-only` mode to every high-risk skill.
- Dry-run must create no files, call no network/API, launch no job, push no Git state, delete nothing.
- Include expected output contract for dry-run so CI can test it.

### 3. Reviewer independence not uniformly preserved

Shared protocol says reviewers should read original files, not executor summaries. Several reviewer skills still pass curated briefings, summaries, recommendations, or changed-since-last-round text.

Highest-risk cases:

- `research-review`
- `patent-review`
- parts of `patent-novelty-check`
- multi-round proof/paper review when prior context leaks across runs

Fix:

- Reviewer prompts should pass file paths, objective, rubric, venue constraints, and raw context only.
- Executor summaries must not substitute for source files.
- Status snapshots may contain reviewer transport/input-scope/trace paths, not review reasoning.

### 4. Runtime portability remains incomplete

Many skills still assume Claude-style tool names:

- `Agent`
- `WebSearch`
- `WebFetch`
- `mcp__codex__codex`
- `mcp__codex__codex-reply`
- Claude hook or settings paths

Fix:

- Add platform frontmatter to all skills.
- Add explicit fallback or blocked state when a runtime tool is unavailable.
- Centralize tool mapping in shared references instead of embedding platform assumptions in every skill.

### 5. External dependency checks are uneven

External deps appear throughout the skill set:

- web/API search: arXiv, AlphaXiv, Exa, DeepXiv, Semantic Scholar, OpenAlex, Gemini, Feishu
- document toolchains: LaTeX, Mermaid, PPTX, LibreOffice, renderers
- remote/GPU: SSH, tmux/screen, W&B, Vast, Modal, qzcli
- Git/Overleaf bridges

Fix:

- Add a `Preflight` section to every external skill.
- Preflight should return `BLOCKED` or `NOT_AVAILABLE` artifacts, not silently skip.
- Use local fixtures for smoke tests where network is unavailable.

### 6. One broken local doc reference

Static relative-link check found:

```text
skills/write-a-skill/SKILL.md -> REFERENCE.md missing
```

Fix: add the referenced file, correct the link, or remove the reference.

## Rating Lists

### Usable

These are practical now with local inputs and low operational risk:

- `caveman`
- `coder`
- `diagnose`
- `embodiment-description`
- `figure-description`
- `formula-derivation`
- `grill-me`
- `handoff`
- `jurisdiction-format`
- `proof-writer`
- `skill-dag-check`
- `tdd`
- `writer`
- `zoom-out`

### Usable With Caution

These are valuable but need preflight, dry-run, runtime mapping, clearer evidence rules, or external dependency checks:

- `ablation-planner`
- `alphaxiv`
- `analyze-results`
- `arxiv`
- `auto-paper-improvement-loop`
- `citation-audit`
- `claims-drafting`
- `comm-lit-review`
- `deepxiv`
- `deployer`
- `exa-search`
- `experiment-audit`
- `experiment-bridge`
- `experiment-plan`
- `experiment-queue`
- `feishu-notify`
- `figure-spec`
- `gemini-search`
- `git-guardrails`
- `grant-proposal`
- `grill-with-docs`
- `idea-creator`
- `idea-discovery`
- `idea-discovery-robot`
- `invention-structuring`
- `kill-argument`
- `leader`
- `mermaid-diagram`
- `meta-optimize`
- `monitor-experiment`
- `novelty-check`
- `openalex`
- `paper-claim-audit`
- `paper-compile`
- `paper-figure`
- `paper-illustration-image2`
- `paper-plan`
- `paper-poster`
- `paper-slides`
- `paper-write`
- `patent-novelty-check`
- `patent-pipeline`
- `pixel-art`
- `prior-art-search`
- `proof-checker`
- `rebuttal`
- `research-lit`
- `research-refine`
- `research-refine-pipeline`
- `research-wiki`
- `result-to-claim`
- `semantic-scholar`
- `slides-polish`
- `specification-writing`
- `system-profile`
- `write-a-skill`
- `writing-systems-papers`

### Blocked

Do not run these unattended until the listed class of issue is fixed:

| Skill | Main blocker |
|---|---|
| `auto-review-loop` | Direct code/experiment loop, remote monitoring, reviewer transport assumptions. |
| `auto-review-loop-llm` | External LLM API, credentials, direct fix loop. |
| `auto-review-loop-minimax` | MiniMax API, credentials, direct fix loop. |
| `dse-loop` | Long-running program execution and config mutation. |
| `framework-update` | Git/network/framework mutation; safety gate required. |
| `init-research` | Project creation, Git init/commit/push, installer side effects. |
| `overleaf-sync` | Git bridge push/pull can overwrite local or remote state. |
| `paper-illustration` | External image generation/API by design. |
| `paper-talk` | Full build/export/audit pipeline with many tool deps. |
| `paper-writing` | Full paper generation/compile/audit pipeline with many writes. |
| `patent-review` | Reviewer independence risk and legal-doc auto-fix flow. |
| `qzcli` | External GPU platform job create/stop risk. |
| `research-pipeline` | End-to-end implementation/deploy/review/paper workflow, too broad. |
| `research-review` | Sends curated briefing instead of original-file-only review. |
| `resubmit-pipeline` | Copy/rsync/compile/Overleaf push and multi-stage artifact mutation. |
| `review` | `needs-runtime-adaptation`, missing issue tracker doc, Agent dependency. |
| `run-experiment` | SSH/rsync/GPU/cloud launch paths. |
| `serverless-modal` | Cloud billing/deploy/secrets. |
| `sync` | Git push/pull/rsync deploy by design. |
| `to-issues` | Issue backend missing. |
| `to-prd` | Issue backend missing. |
| `training-check` | Live monitoring/kill-action/W&B/SSH risks. |
| `vast-gpu` | GPU rental/billing/destroy/SSH. |

## Safe Smoke-Test Standard

Every skill should have a smoke path matching its risk level:

| Risk class | Required smoke path |
|---|---|
| Pure local reasoning/writing | Tiny fixture input -> deterministic local artifact. |
| Local file mutation | Tmp project only; no writes outside tmp. |
| Build/compile/render | Dependency preflight + tiny fixture compile, no auto-fix outside tmp. |
| Web/API | Parser/preflight mode that performs no network call. |
| Reviewer/MCP | Prompt builder/trace skeleton mode when transport unavailable. |
| SSH/GPU/queue | Plan-only mode plus local fake log/queue fixture. |
| Cloud/rental/push/delete | Must stay blocked unless explicit user confirmation + dry-run receipt exists. |

## Frontmatter Metadata Needed

Recommended additions for all skills:

```yaml
platform: both | claude | codex
status: active | needs-adaptation | needs-runtime-adaptation | needs-safety-confirmation | blocked
mutates_files: true | false
runs_commands: true | false
uses_network: true | false
uses_ssh: true | false
uses_gpu: true | false
uses_cloud: true | false
uses_git_write: true | false
requires_api_key: true | false
safe_smoke: true | false
```

These fields should feed `docs/SKILL_DAG.yaml`, `docs/SKILL_CATALOG.md`, and future compatibility checks.

## Priority Fix Plan

### P0: Stop unsafe unattended execution

- Mark blocked skills explicitly in frontmatter if not already marked.
- Add dry-run/plan-only contract to `sync`, `run-experiment`, `training-check`, `vast-gpu`, `serverless-modal`, `qzcli`, `overleaf-sync`, `framework-update`, `init-research`.
- Ensure dry-run does not mutate files, call network, launch jobs, push, rent, delete, or deploy.

### P1: Repair role boundaries

- Reclassify top-level workflow skills as `orchestrator` or rewrite them so true Leader only reads, gates, and delegates.
- Move implementation/deployment/writing actions to Coder/Deployer/Writer prompts.
- Keep Reviewer as independent transport-agnostic role.

### P2: Add smoke tests

- Add one local smoke test per safe skill group.
- Add parser/preflight-only tests for external deps.
- Add blocked-state tests for missing reviewer/web/SSH/cloud tools.

### P3: Normalize runtime metadata

- Fill `platform` and `status` for all 94 top-level skills.
- Add risk flags.
- Regenerate DAG/catalog after metadata update.

### P4: Fix docs/drift

- Fix missing `skills/write-a-skill/REFERENCE.md` reference.
- Resolve `comm-lit-review` frontmatter name mismatch (`comm-lit-review-claude-single` vs folder/trigger).
- Deduplicate or namespace archived `skills-codex/review`.
- Align top-level skills and Codex mirror shared references.

## Suggested Next Work Items

1. Create a `safe_smoke` test harness that loads every `SKILL.md`, reads frontmatter, and validates required metadata.
2. Add dry-run standards to shared references.
3. Patch blocked operational skills first: `sync`, `run-experiment`, `training-check`, `vast-gpu`, `serverless-modal`, `qzcli`.
4. Patch reviewer independence issues in `research-review` and `patent-review`.
5. Add a local markdown fallback for `to-prd` and `to-issues`.

## Raw Part Reports

Detailed sub-agent reports:

- `to-developer/logs/skill-usability-parts/20260615-leader.md`
- `to-developer/logs/skill-usability-parts/20260615-executor.md`
- `to-developer/logs/skill-usability-parts/20260615-reviewer.md`
- `to-developer/logs/skill-usability-parts/20260615-any.md`
