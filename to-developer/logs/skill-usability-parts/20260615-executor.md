# Executor Skill Usability Audit

Scope: top-level `skills/*/SKILL.md` with `caller: executor`, plus role skills `coder`, `deployer`, `writer`. Archive copies under `skills/skills-*` ignored. No network/SSH/cloud/GPU/API actions run.

## Top Blockers

- Status stream mostly absent. Only `coder`, `deployer`, `writer` explicitly use `agent-status-stream.md` / `agent_status.py`.
- Many executor skills still say `Bash(*)`, `WebSearch`, `WebFetch`, `mcp__codex__codex`, cloud CLIs, SSH, push, destroy. Missing dry-run/no-op path.
- Remote/cloud skills mix plan, deploy, monitor, cleanup in one doc. Hard to smoke-test safely.
- Several skills reference external services or current pricing/CFP/API behavior but lack offline fallback.
- Role boundaries conflict: `writer` allows web; `deployer` allows Agent; concrete skills call MCP/reviewer despite executor layer.
- Some skills depend on helpers (`tools/*`, `.aris/tools/*`, mermaid/latex/pptx/renderers) but preflight varies.

## Per-Skill Ratings

| Skill | Rating | Practical blockers | Safe smoke-test | Status-stream gap |
|---|---|---|---|---|
| `ablation-planner` | usable-with-caution | MCP/W&B assumed; may drift into running ablations. | Fixture `EXPERIMENT_LOG.md` + `CLAIM_VERDICT.json`; produce plan only. | Add start/update/finish; artifacts = ablation plan. |
| `claims-drafting` | usable-with-caution | Legal output, web/MCP examiner, many required patent inputs. | Tiny fake `patent/INVENTION_DISCLOSURE.md`; draft 1 claim set offline. | Add Writer-style status; artifact `patent/CLAIMS.md`. |
| `coder` | usable | Clear boundary, status integrated. Minor issue: risk detector sees SSH in ban text only. | Temp repo: add failing pytest then implementation. | OK. |
| `deployer` | usable-with-caution | SSH/rsync/env install/training core; not safe without explicit remote consent. | Parse dummy `CLAUDE.md`; emit planned commands only. | OK, but add dry-run status example. |
| `diagnose` | usable | Good local loop; can tempt destructive minimization if not constrained. | Failing unit test fixture; produce hypothesis log only. | Add status updates for reproduce/instrument/fix phases. |
| `embodiment-description` | usable | Needs patent inputs/figures; no external hard dependency. | Minimal claims + numeral index; write detailed description stub. | Add Writer status. |
| `experiment-bridge` | usable-with-caution | Too broad: implement + review + deploy + collect; MCP/modal/W&B/run-experiment hooks. | Tiny local plan; generate manifest/deviation files, skip deploy. | Must write coder/deployer substatus or own phase status. |
| `experiment-queue` | usable-with-caution | SSH/screen/GPU queue core; helper availability/path complex. | Validate manifest against local tmp dir; do not launch jobs. | Add queue run job handle + next update pacing. |
| `figure-description` | usable | Local patent writing. Missing figure absence behavior could be clearer. | Dummy SVG/PNG + invention brief; produce numeral index. | Add Writer status. |
| `figure-spec` | usable-with-caution | Needs renderer helper; optional MCP review; SVG/PDF toolchain. | `tools/figure_renderer.py schema` + validate tiny spec. | Add artifact refs for spec/svg/pdf/review trace. |
| `formula-derivation` | usable | Local reasoning/writing; no major external dependency. | Tiny lemma input; write `DERIVATION_PACKAGE.md`. | Add Writer status. |
| `grant-proposal` | usable-with-caution | Web/MCP/style extraction; grant facts can be stale; budget/CV placeholders. | Offline mini proposal from local brief; no web. | Add Writer status; record source files and blockers. |
| `invention-structuring` | usable-with-caution | MCP novelty review optional; needs prior art quality. | Local invention paragraph -> `INVENTION_DISCLOSURE.md`. | Add Writer status. |
| `jurisdiction-format` | usable | Formatting-only if inputs exist. | Minimal patent dir -> output summary in tmp project. | Add Writer status. |
| `mermaid-diagram` | usable-with-caution | Mermaid CLI/browser deps; mandatory render may fail. | Syntax-only render of tiny flowchart to temp `figures/`. | Add artifact refs for `.mmd/.md/.png`; status on render fail. |
| `monitor-experiment` | usable-with-caution | SSH/W&B/Modal/Vast read paths; Feishu optional; may inspect live services. | Local fake logs/results dirs; summarize only. | Add Deployer status update/finish; job_handles read-only. |
| `overleaf-sync` | blocked | Git bridge push/pull; can overwrite remote/local; no strong dry-run gate. | `status` against fake repo only; never pull/push. | Add start/update/finish; artifact audit report. |
| `paper-compile` | usable-with-caution | LaTeX env, auto-fix edits, possible stale file cleanup. | Compile tiny temp paper; no auto-fix outside temp. | Add Writer status; artifact PDF/log. |
| `paper-figure` | usable-with-caution | Plot env/data assumptions; possible Modal mention; MCP review. | Read tiny CSV; generate one local PNG + include file. | Add Writer/Coder status depending plot code edits. |
| `paper-illustration` | blocked | External image generation/API by design; no offline no-op path. | Prompt-only dry run: write spec JSON, no generation. | Add status with external job/artifact handles. |
| `paper-illustration-image2` | usable-with-caution | Local bridge/helper/env needed; external image generation behind bridge. | `preflight` helper only; create prompt/spec no image call. | Add job handle for bridge run + output artifacts. |
| `paper-plan` | usable-with-caution | Web/MCP optional; many input variants; venue rules may be stale. | Local `NARRATIVE_REPORT.md` -> `PAPER_PLAN.md`. | Add Writer status. |
| `paper-poster` | usable-with-caution | Large LaTeX/PPTX pipeline; auto visual review; destructive temp/checkpoint complexity. | Validate existing paper path; generate content plan only. | Add Writer status; phase + checkpoint artifact refs. |
| `paper-slides` | usable-with-caution | LaTeX/PPTX deps, Feishu optional, style helper. | Generate outline only from tiny paper; no compile. | Add Writer status; slide phase artifacts. |
| `paper-write` | usable-with-caution | Citation web lookup, LaTeX deps, auto cleanup risk. | Tiny `PAPER_PLAN.md`; draft one section offline. | Add Writer status; section artifact refs and source result refs. |
| `proof-writer` | usable | Local theorem/proof package. | Tiny proposition -> `PROOF_PACKAGE.md`. | Add Writer status. |
| `run-experiment` | blocked | SSH/rsync/Vast/Modal/W&B/git push/destroy; no safe dry-run required. | Plan-only command generation from fake `CLAUDE.md`. | Add Deployer status; job handle before launch. |
| `serverless-modal` | blocked | Cloud billing/deploy/secrets/volumes; pricing may change. | Static Modal app lint/cost estimate only. | Add job handle for Modal app/run/volume. |
| `slides-polish` | usable-with-caution | Heavy PPTX/PDF deps; MCP visual review; shape edits risky. | Inspect a tiny PPTX or fail cleanly with missing dep. | Add Writer status; per-slide phase/checkpoint artifacts. |
| `specification-writing` | usable-with-caution | Patent/legal quality; web/MCP optional; many inputs. | Minimal patent inputs -> section index only. | Add Writer status. |
| `sync` | blocked | Push/pull/deploy/rsync/destructive by design; user may not understand git. | `sync status`/dry-run commit message only. | Add Deployer/Coder status for deploy/push phases. |
| `system-profile` | usable-with-caution | Profiling can perturb workload; tool availability varies. | Profile `python -c 'pass'` with available local tools. | Add Coder status; artifact profile report. |
| `tdd` | usable | Strong workflow; asks user confirmation, can slow simple fixes. | Temp function: red/green/refactor one pytest. | Add Coder status hooks per cycle. |
| `training-check` | blocked | CronCreate not available here; can kill training; W&B/API/SSH. | Offline parse saved W&B/log JSON; decision only. | Add Deployer status; never kill without blocker/artifact evidence. |
| `vast-gpu` | blocked | Rental/billing/destroy/SSH; live pricing; irreversible cleanup. | Parse fake `vastai search` output; rank offers only. | Add job handle for instance id, ssh url, cost state. |
| `writer` | usable | Clear boundary, status integrated; web allowed for citations. | Draft from local result fixture; no web. | OK. |
| `writing-systems-papers` | usable-with-caution | CFP/page limits stale; web/MCP listed but not necessary. | Local outline -> systems page budget table. | Add Writer status if used to write artifacts. |

## Status-Stream Integration Gaps

- Add common executor preamble to every concrete skill: `start` on entry, `update` before long/dependent phase, `finish` with artifacts/blocker.
- Cloud/remote skills must write durable `job_handles` before wait: SSH session, screen/tmux, Vast instance, Modal app/run, queue dir, log path.
- Writing/paper/patent skills should record current section, source evidence/result files, output paths, blocked missing inputs.
- Coder-ish skills (`tdd`, `diagnose`, `experiment-bridge`, `system-profile`) should record changed files, tests run, test status, deviation artifact.
- Skills need explicit dry-run smoke path. Same command shape, no network/SSH/API/cloud/GPU/push/destroy.
