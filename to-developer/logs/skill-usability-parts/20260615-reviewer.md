# Reviewer Skill Usability Audit

Scope: `caller: reviewer` skills under `/aris/aris-dev/skills`, plus shared reviewer protocols: `reviewer-independence.md`, `reviewer-routing.md`, `review-tracing.md`.

Local checks only. No network/API/SSH/cloud/GPU/push/deploy/rental actions run.

## Cross-Cut Findings

- Main runtime gap: many skills assume Claude-style tools (`Agent`, `WebSearch`, `WebFetch`, `mcp__codex__codex`, `mcp__codex__codex-reply`). Current Codex runtime does not expose those exact tools.
- Reviewer protocol gap: `reviewer-independence.md` says pass file paths, not executor summaries. Several skills still build briefings or paste curated content into reviewer prompts.
- Transport gap: `reviewer-routing.md` standardizes Codex MCP xhigh and optional Oracle. Many skills mention Codex MCP but do not implement Oracle routing or fallback artifacts.
- Trace gap: `review-tracing.md` requires traces after each reviewer call. Some skills mention tracing, but reviewer failure/offline paths are uneven.
- Duplicate skill: `/skills/review/SKILL.md` and `/skills/skills-codex/review/SKILL.md` are byte-identical. Both say `status: needs-runtime-adaptation`.
- Missing local prereq: `docs/agents/issue-tracker.md` referenced by `review` is absent.
- Shared refs/helpers exist: reviewer protocols, `tools/save_trace.sh`, `tools/verify_paper_audits.sh`, patent refs, experiment-integrity refs.

## Per-Skill Ratings

| Skill | Rating | Top practical blockers | Safe smoke-test suggestion | Reviewer-independence risks | Transport/runtime issues |
|---|---|---|---|---|---|
| `analyze-results` | usable-with-caution | No strict schema; may overinterpret data; writes docs opportunistically. | Use tiny local JSON/CSV fixture; verify mean/std/delta table only, no edits. | Same agent interprets results; no independent reviewer path. | Uses generic `Agent`, `Write`, `Edit`; portable only if caller maps these. |
| `review` | blocked | `status: needs-runtime-adaptation`; missing `docs/agents/issue-tracker.md`; duplicate copy. | Run header parse + `git diff <base>...HEAD --name-only` on toy repo; no agents. | Two subagents may receive fetched spec summaries, not primary issue artifacts. | Requires `Agent` subagents; not available here. |
| `skills-codex/review` | blocked | Same as root `review`; duplicate creates routing ambiguity. | Same as `review`; also assert only one `review` skill selected. | Same as root `review`. | Same as root `review`. |
| `research-review` | blocked | Contradicts shared independence: tells executor to compile comprehensive briefing and says reviewer cannot read files. | Dry-run prompt builder should emit file paths only; assert no prose summary in prompt. | High: full executor framing, known weaknesses, interpretations sent to reviewer. | Requires Codex MCP/reply; no offline/fallback artifact. |
| `experiment-audit` | usable-with-caution | Good path-only design, but cannot complete without external reviewer. | Fixture project with eval script/result/config; test artifact discovery list and ERROR artifact when reviewer unavailable. | Low if Step 1 truly collects paths only. | Requires Codex MCP xhigh; Oracle routing referenced but not concretely wired. |
| `paper-claim-audit` | usable-with-caution | Strong zero-context rules; needs careful path/hash convention; reviewer failure path must still emit JSON. | Tiny paper + one result JSON; dry-run file discovery, hash keys, NOT_APPLICABLE/BLOCKED decisions. | Low: explicit fresh thread, raw files only. | Requires Codex MCP; tracing text mentions `codex-reply` generically though rules forbid reply. |
| `citation-audit` | usable-with-caution | Web lookup required per entry; expensive; interactive fix step; bib parsing edge cases. | Local `.bib` + `.tex` with no network: verify cite extraction, uncited set-diff, BLOCKED/ERROR artifact. | Medium: contexts are pasted, but citation sentence context is necessary; avoid executor analysis. | Requires web + Codex MCP; `latexmk` compile step may be unavailable/slow. |
| `proof-checker` | usable-with-caution | Very large workflow; mutates proofs; compile assumptions; parse/schema complexity. | Tiny theorem-free `.tex`: must emit `PROOF_AUDIT.json` with `NOT_APPLICABLE`; no reviewer call. | Medium: Phase 3 uses fix summaries in same thread; allowed only inside same run, but easy to leak executor framing. | Requires Codex MCP/reply and LaTeX; Oracle referenced but no explicit runtime branch. |
| `novelty-check` | usable-with-caution | Mandatory recent web search; no offline mode; broad "all papers found" prompt can be huge. | Offline smoke: extract 3-5 claims from local text and emit "search not run" BLOCKED/ERROR note. | Medium: executor curates prior work list and may bias reviewer. | Requires WebSearch/WebFetch + Codex MCP; no graceful no-network path specified. |
| `prior-art-search` | usable-with-caution | Patent DB search brittle; legal/FTO language risky; no deterministic DB API. | Local invention brief only: verify concept extraction and report skeleton with `[NOT_SEARCHED]`. | Low: mostly search/report skill, no external reviewer. | Requires WebSearch/WebFetch; Espacenet via WebFetch likely unreliable. |
| `patent-novelty-check` | usable-with-caution | Depends on prior-art report quality; advisory legal conclusions; broad claim drafting inside audit. | Local mock `PRIOR_ART_REPORT.md`; verify claim-element matrix creation without MCP. | Medium: reviewer prompt gets executor-drafted claims/prior-art summaries; prefer file paths + matrices. | Codex MCP optional fallback exists; web tools listed but not central. |
| `patent-review` | blocked | Passes summarized claims/spec/prior art; Round 2 uses `mcp__codex__codex` with `threadId` instead of explicit reply; auto-fix legal docs. | Dry-run: collect patent file paths and produce examiner prompt with paths only; no edits. | High: office-action prompt contains executor-selected summaries and "changes made" rationale. | Requires Codex MCP/reply; no trace section; Claude setup command embedded. |

## Top Practical Blockers

1. Tool names are not portable across runtimes. Need adapter layer or per-platform tool mapping.
2. Several reviewer skills need offline/error artifact contracts, not silent inability when MCP/web absent.
3. Independence protocol is not uniformly applied. `research-review` and `patent-review` are worst.
4. Duplicate `review` skill should be deduped or clearly namespaced.
5. Web-heavy skills need dry-run/local smoke mode to test extraction and artifact emission without network.

## Transport/Runtime Issues

- Codex MCP tools are referenced as callable, but absent in this session.
- Oracle routing is a shared spec, not consistently implemented in skill bodies.
- `Agent` subagent workflow is Claude-specific and blocks `review` portability.
- `WebSearch`/`WebFetch` names are Claude-specific; current runtime web tool differs and was not used due user ban.
- `latexmk`/`pdflatex` compile steps are runtime-dependent and should degrade to "compile not run" artifacts.

## Reviewer-Independence Risks

- Forbidden pattern present: executor compiles research/patent summaries before review.
- Allowed exception present but fragile: same-thread reply for proof closure. Must never cross top-level runs.
- Citation context paste is acceptable only as raw local sentence context, not interpretation.
- Patent novelty/review should pass primary files and prior-art report paths; reviewer should read directly.

## Safe Smoke Tests

- Header lint: parse all `SKILL.md` front matter; assert unique names or explicit namespace.
- Dependency lint: referenced shared files/helpers exist.
- Prompt lint: reviewer prompt templates must contain file paths and must not contain executor "summary/findings/recommendation" fields unless raw context exception is declared.
- Offline artifact lint: for audit skills, create tiny fixtures and assert JSON verdicts for `NOT_APPLICABLE`, `BLOCKED`, and `ERROR`.
- Runtime lint: fail fast when `mcp__codex__codex`, web, Agent, or LaTeX tools are unavailable; write trace/error metadata.
