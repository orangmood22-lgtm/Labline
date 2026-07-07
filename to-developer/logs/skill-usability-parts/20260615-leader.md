# Leader-Caller Skill Usability Audit

Scope: `caller: leader` skills in `docs/SKILL_DAG.yaml`, cross-checked with `docs/SKILL_CATALOG.md` and each `skills/*/SKILL.md`.

## Top Blockers

- Leader role contract conflict: `/leader` says leader only read / judge / delegate, but most `caller: leader` skills grant `Bash(*)`, `Write`, `Edit`, web/API/MCP, and instruct direct file writes or command runs.
- Broad tool grants: many skills use `allowed-tools: Bash(*)` despite narrow workflows. Usability suffers because safe vs unsafe actions are buried in prose.
- Network/API assumptions: search, web fetch, Codex MCP, MiniMax, Gemini, arXiv, DBLP/CrossRef, Overleaf, W&B, Codex app-server appear as normal paths, often without clean no-network fallback.
- Cloud/GPU/SSH leakage: research pipelines and review loops directly include `/run-experiment`, `/experiment-queue`, SSH/screen/tmux/GPU work. Bad fit for leader boundary.
- Silent skip vs gate ambiguity: several skills say audits may skip, later say mandatory gates. Good intent, but operators can misread when artifact absence blocks.
- Missing implementation hooks: some workflows specify helper fns (`check_whitelist_compliance`), params, or MCP tools not guaranteed by skill catalog/tooling.
- Dangerous defaults: `AUTO_PROCEED=true` in expensive research flows; direct `git push`, `git reset --hard`, `git fetch`, Overleaf push paths in leader-caller skills.

## Per-Skill Ratings

| Skill | Rating | Practical blockers | Safe smoke-test | Role-boundary issue |
|---|---|---|---|---|
| `leader` | usable-with-caution | Strong role contract, but Phase 0 writes state and calls MCP despite "no edit/API"; permission model names Claude-only tools. | Read `PIPELINE_STATE` schema + validate required prompt refs exist. | Boundary is explicit but self-contradictory: leader says no MCP/edit, then does both. |
| `research-refine` | usable-with-caution | WebSearch/WebFetch + MCP core; writes many artifacts directly; high round count. | Given tiny local prompt, verify expected `refine-logs/*` filenames and stop before MCP. | Should be writer/planner executor plus reviewer, not direct leader writing. |
| `experiment-plan` | usable-with-caution | Writes plan/tracker directly; web allowed but not needed; no reviewer gate despite leader caller. | Feed existing `FINAL_PROPOSAL.md`; check template fields in output plan. | Planner execution work belongs executor; leader should delegate. |
| `research-refine-pipeline` | usable-with-caution | Thin wrapper, but inherits all direct writes/MCP/web from two child skills. | Check it only selects/refers to `research-refine` then `experiment-plan`. | Mostly orchestration, but still caller allowed `Write/Edit/Bash`. |
| `idea-discovery` | usable-with-caution | Broad web/API/search; pilots imply GPU; `AUTO_PROCEED=true`; calls many subskills. | Dry-run argument parse + ensure `idea-stage/` output contract complete. | Leader both orchestrates and runs discovery/pilot pipeline. |
| `idea-discovery-robot` | usable-with-caution | Robotics-specific and safer on hardware, but still web/MCP/direct writes; benchmark availability often external. | Local-only prompt -> verify robotics frame fields and no hardware action path. | Better boundaries than generic, but still planner/writer work in leader. |
| `research-pipeline` | blocked | Direct implementation, deployment, GPU, monitoring, review loop, optional paper writing; `AUTO_PROCEED=true`; huge blast radius. | Static lint: confirm it delegates implementation/deploy, not direct code/run. | Violates leader boundary hardest: implementation/deploy described as pipeline stages. |
| `auto-review-loop` | blocked | Implements code, runs experiments, remote monitoring, Feishu, curl/DBLP/CrossRef; nightmare mode runs `codex exec`. | Parse existing `review-stage/REVIEW_STATE.json`; no MCP/run. | Should be orchestrator + executor/reviewer split; current leader does execution. |
| `auto-review-loop-llm` | blocked | Requires `llm-chat` MCP or curl API; direct fixes/monitoring; generic credentials. | Env/MCP presence check only; verify fail-closed when absent. | API/review/execution all in leader-caller skill. |
| `auto-review-loop-minimax` | blocked | MiniMax MCP/curl API required; direct code/experiment loop; external provider coupling. | Check `MINIMAX_API_KEY` detection without calling API. | Same as LLM loop; reviewer backend should be reviewer role. |
| `auto-paper-improvement-loop` | usable-with-caution | Large direct LaTeX edits, compile commands, Codex calls; whitelist logic only prose; style-ref can fetch URLs. | Fixture paper with no compile: verify input discovery + whitelist parse only. | Editing/writing paper is executor/writer; leader should gate only. |
| `paper-writing` | blocked | Full paper generation, figures, compile, audits, image/API modes, external verifier; many direct writes. | Static output-contract check: expected `paper/`, `figures/`, audit filenames. | Workflow 3 should be writer/executor pipeline, not leader direct. |
| `paper-talk` | blocked | Builds slides/PPTX, runs LaTeX/LibreOffice, audits; many writes and tool deps. | Validate prerequisites list generation without invoking build. | Deck creation/polish is executor/writer; leader should coordinate only. |
| `rebuttal` | usable-with-caution | Safer than paper pipeline: text-only, no auto experiments by default; still writes drafts and calls MCP. | Local review-bundle fixture -> atomize concerns, no MCP stress test. | Drafting is writer; leader can own gates, not file edits. |
| `resubmit-pipeline` | blocked | Many shell ops (`mkdir`, `cp`, `rsync`, compile), Overleaf push path, audit loops; references helper not implemented inline. | Static dry-run: resolve new dir name and fail if exists; no copy/compile/push. | Mostly executor operations under leader caller. |
| `result-to-claim` | usable-with-caution | Good gate concept; still writes verdict/wiki files and may call W&B/Codex. | Read local result JSON + check verdict schema fields, no MCP. | Claim judgment fits leader/reviewer, but wiki edits are executor. |
| `kill-argument` | usable-with-caution | Detect-only mostly good; requires two Codex calls; writes reports/traces; theory applicability heuristic. | Local paper inventory + NOT_APPLICABLE heuristic only. | Reviewer action fits leader gate, but artifact writing should be delegated or allowed exception. |
| `dse-loop` | blocked | Explicitly runs programs up to 2h, edits configs, creates parsers, parallel jobs. | Parse parameter-space from a toy config; no run. | Pure executor loop mislabeled leader. |
| `framework-update` | blocked | Runs `git fetch/pull`, may `reset --hard --force`, rebuilds symlinks; network/destructive possible. | `--dry-run` only: locate framework and print planned commits, no fetch. | Maintenance/deploy op, not leader research role. |
| `init-research` | blocked | Creates dirs, git init/commit/push, installs skills, writes config. Status already `needs-adaptation`. | Validate slug/path collision and render planned tree only. | Project bootstrap executor/admin task, not leader. |
| `meta-optimize` | usable-with-caution | Useful maintenance workflow; writes proposed patches and may later edit skills; depends on logs + MCP. | Read `.aris/meta/events.jsonl` count; if <5, exit report-only. | Analysis fits leader; patch application must be separate executor/admin confirmation. |
| `patent-pipeline` | usable-with-caution | Strong checkpoints; legal high-stakes; web prior-art search; many generated legal docs; attorney caveat present. | Parse invention brief + jurisdiction/type, no web search. | Drafting/spec generation belongs executor; leader should checkpoint inventor decisions. |

## Role-Boundary Issues

- `caller: leader` overloaded: means "top-level workflow" in catalog, but `/leader` defines much stricter role. Rename field or split into `caller: orchestrator` vs true `leader`.
- Skills needing `Bash(*)`, `Write`, `Edit` should either be `caller: executor` or contain a clear "leader delegates this exact prompt to executor" block.
- Reviewer-only gates (`kill-argument`, `result-to-claim`) are closest to legitimate leader skills, but artifact writes need explicit exception or delegation.
- Maintenance/admin skills (`framework-update`, `init-research`, `meta-optimize apply`) need separate permission tier, not research leader.
- External calls should be declared as preflight requirements in frontmatter: `network`, `api`, `ssh`, `gpu`, `git-write`, `cloud-write`, `push`.

## Practical Fixes

1. Add frontmatter risk flags: `mutates_files`, `runs_commands`, `uses_network`, `uses_cloud`, `uses_gpu`, `uses_git_write`, `requires_api_key`.
2. For true leader skills, remove `Bash(*)`, `Write`, `Edit`; replace direct actions with executor delegation prompts.
3. For pipeline skills, set `caller: orchestrator` or `executor` unless they only read state, call reviewers, and dispatch agents.
4. Add `--dry-run` contract to every high-risk skill. Dry run must create no files, call no network/API, launch no job.
5. Make mandatory audit artifacts explicit: if gate says mandatory, `NOT_APPLICABLE` JSON must be emitted; no silent skip.
