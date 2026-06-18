---
name: result-to-claim
description: Use when experiments complete to judge what claims the results support, what they don't, and what evidence is still missing. Codex MCP evaluates results against intended claims and routes to next action (pivot, supplement, or confirm). Use after experiments finish — before writing the paper or running ablations.
argument-hint: [experiment-description-or-wandb-run]
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, mcp__codex__codex, mcp__codex__codex-reply
caller: leader
examples:
  - "/result-to-claim exp01 results"
  - "what claims do these results support"
  - "judge if experiments validate the method"
---

# Result-to-Claim Gate

Experiments produce numbers; this gate decides what those numbers *mean*. Collect results from available sources, get a Codex judgment, then auto-route based on the verdict.

## Context: $ARGUMENTS

## When to Use

- After a set of experiments completes (main results, not just sanity checks)
- Before committing to claims in a paper or review response
- When results are ambiguous and you need an objective second opinion

## Workflow

### Step 1: Collect Results

Gather experiment data from whatever sources are available in the project:

1. **`refine-logs/EXPERIMENT_PLAN.md`** (preferred planning contract): claim map, expectation declaration, execution spec, data flow summary, delta assertion, evidence mapping
2. **`refine-logs/IMPLEMENTATION_DEVIATIONS.json`** (preferred drift receipt if implementation changed or was explicitly verified unchanged): plan drift records, claim-impact annotations, artifact-impact notes, or an explicit no-deviation receipt
3. **W&B** (preferred runtime metrics if available): `wandb.Api().run("<entity>/<project>/<run_id>").history()` — metrics, training curves, comparisons
4. **EXPERIMENT_LOG.md**: full results table with baselines and verdicts
5. **EXPERIMENT_TRACKER.md**: check which experiments are DONE vs still running
6. **Log files / result artifacts**: JSON, CSV, logs produced by the runs
7. **docs/research_contract.md` or proposal docs**: intended claims and experiment design, if the plan is incomplete

Assemble the key information:
- What claims were intended to be tested
- What experiments were run (method, dataset, split, config)
- Main metrics and baseline comparisons (deltas)
- Which result artifacts were expected to support each claim
- Whether the planned execution spec (variants / seeds / metrics / constraints) was actually followed
- What `IMPLEMENTATION_DEVIATIONS.json` says about drift, claim impact, artifact impact, and whether any unresolved deviations remain
- Any known confounds, deviations, or caveats

### Step 2: Codex Judgment

Send the collected results to Codex for objective evaluation:

```
mcp__codex__codex:
  config: {"model_reasoning_effort": "xhigh"}
  prompt: |
    RESULT-TO-CLAIM EVALUATION

    I need you to judge whether experimental results support the intended claim.

    Planning contract:
    - Claim map: [paste relevant rows from EXPERIMENT_PLAN.md]
    - Expectation declaration: [split / GT / baseline assumptions]
    - Execution spec: [planned variants / metrics / seeds / key implementation constraints]
    - Delta assertion: [expected concrete difference and no-effect detector]
    - Evidence mapping: [which result files are supposed to support which claims]
    - Implementation deviations: [paste relevant entries from IMPLEMENTATION_DEVIATIONS.json, including claim_impact / artifact_impact / unresolved status]

    Experiments run:
    [list experiments with method, dataset, split, metrics]

    Results:
    [paste key numbers, comparison deltas, significance]

    Baselines:
    [baseline numbers and sources — reproduced or from paper]

    Known caveats / deviations:
    [confounds, missing comparisons, implementation deviations]

    Please evaluate:
    1. claim_supported: yes | partial | no
    2. what_results_support: what the data actually shows
    3. what_results_dont_support: where the data falls short of the claim
    4. missing_evidence: specific evidence gaps
    5. suggested_claim_revision: if the claim should be strengthened, weakened, or reframed
    6. next_experiments_needed: specific experiments to fill gaps (if any)
    7. confidence: high | medium | low
    8. evidence_mapping_status: aligned | partial | broken
    9. delta_assertion_status: satisfied | weak | failed | unavailable

    Be honest. Do not inflate claims beyond what the data supports.
    A single positive result on one dataset does not support a general claim.
```

### Step 3: Parse and Normalize

Extract structured fields from Codex response:

```markdown
- claim_supported: yes | partial | no
- what_results_support: "..."
- what_results_dont_support: "..."
- missing_evidence: "..."
- suggested_claim_revision: "..."
- next_experiments_needed: "..."
- confidence: high | medium | low
- evidence_mapping_status: aligned | partial | broken
- delta_assertion_status: satisfied | weak | failed | unavailable
- implementation_deviation_impact: none | narrow_scope | weakens_evidence | breaks_claim_test | unknown
- recovery_context_status: none | reviewed | relevant_warning | unknown
```

### Step 3.5: Check Experiment Integrity (if audit exists)

**Skip this step if `EXPERIMENT_AUDIT.json` does not exist.**

```
if EXPERIMENT_AUDIT.json exists:
    read integrity_status from file
    read split_correctness / implementation_conformance / delta_assertion / evidence_mapping checks
    attach to verdict output:
        integrity_status: pass | warn | fail

    if implementation_conformance == fail:
        treat planned-claim coverage as broken unless the verdict is explicitly narrowed to the actually implemented scope

    if IMPLEMENTATION_DEVIATIONS.json reports any item with status == "unresolved" or claim_impact == "breaks_claim_test":
        treat the affected claim as unsupported unless the verdict is explicitly narrowed away from the deviated scope
        append to verdict: "[PLAN DRIFT] — unresolved implementation deviation affects claim coverage"
        downgrade confidence by one level unless already "low"

    if IMPLEMENTATION_DEVIATIONS.json reports claim_impact == "narrow_scope" or "weakens_evidence":
        require the verdict to state the narrower supported scope or missing evidence explicitly

    if delta_assertion == fail:
        treat the core mechanism claim as unsupported unless strong contrary evidence exists elsewhere

    if evidence_mapping == fail:
        label the verdict as claim-traceability-broken even if some numbers look positive

    if integrity_status == "fail":
        append to verdict: "[INTEGRITY CONCERN] — audit found issues, see EXPERIMENT_AUDIT.md"
        downgrade confidence to "low" regardless of Codex judgment

    if integrity_status == "warn":
        append to verdict: "[INTEGRITY: WARN] — audit flagged potential issues"
else:
    integrity_status = "unavailable"
    verdict is labeled "provisional — no integrity audit run"
    (this does NOT block anything — pipeline continues normally)
```

### Step 3.6: Write Claim Verdict Artifact

Write a load-bearing verdict artifact (markdown, JSON, or both according to project conventions) that records at minimum:
- claim_supported
- confidence
- what_results_support
- what_results_dont_support
- missing_evidence
- suggested_claim_revision
- evidence_mapping_status
- delta_assertion_status
- implementation_deviation_impact
- recovery_context_status
- integrity_status (if audit exists)

This artifact is the receipt for downstream paper-writing or reviewer-facing claim edits. If the verdict is rerun, preserve timestamped history per `shared-references/output-versioning.md`.



#### `no` — Claim not supported

1. Record postmortem in findings.md (Research Findings section):
   - What was tested, what failed, hypotheses for why
   - Constraints for future attempts (what NOT to try again)
2. Update CLAUDE.md Pipeline Status
3. Decide whether to pivot to next idea from IDEA_CANDIDATES.md or try an alternative approach

#### `partial` — Claim partially supported

1. Update the working claim to reflect what IS supported
2. Record the gap in findings.md
3. Design and run supplementary experiments to fill evidence gaps
4. Re-run result-to-claim after supplementary experiments complete
5. **Multiple rounds of `partial` on the same claim** → record analysis in findings.md, consider whether to narrow the claim scope or switch ideas

#### `yes` — Claim supported

1. Record confirmed claim in project notes
2. If ablation studies are incomplete → trigger `/ablation-planner`
3. If all evidence is in → ready for paper writing

### Step 5: Update Research Wiki (if active)

**Skip this step entirely if `research-wiki/` does not exist.**

If `research-wiki/` exists, resolve `$WIKI_SCRIPT` per the canonical
chain documented in
[`shared-references/wiki-helper-resolution.md`](../shared-references/wiki-helper-resolution.md)
(Variant B — warn-and-skip for caller skills). The verdict / claim
status / idea-outcome page edits below run on raw markdown and don't
need the helper, but edges, query-pack rebuild, and the log line do.

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 1
LABLINE_REPO="${LABLINE_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .labline/installed-skills.txt 2>/dev/null)}"
WIKI_SCRIPT=".labline/tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || WIKI_SCRIPT="tools/research_wiki.py"
[ -f "$WIKI_SCRIPT" ] || { [ -n "${LABLINE_REPO:-}" ] && WIKI_SCRIPT="$LABLINE_REPO/tools/research_wiki.py"; }
[ -f "$WIKI_SCRIPT" ] || {
  echo "WARN: research_wiki.py not found; verdict will be reported but wiki edges/query-pack/log will be skipped. Fix: bash tools/install_labline.sh, export LABLINE_REPO, or cp <Labline-repo>/tools/research_wiki.py tools/." >&2
  WIKI_SCRIPT=""
}
```

```
if research-wiki/ exists:
    # 1. Create experiment page
    Create research-wiki/experiments/<exp_id>.md with:
      - node_id: exp:<id>
      - idea_id: idea:<active_idea>
      - date, hardware, duration, metrics
      - verdict, confidence, reasoning summary

    # 2. Update claim status (page edits run unconditionally; edges only if $WIKI_SCRIPT resolved)
    for each claim resolved by this verdict:
        if verdict == "yes":
            Update claim page: status → supported
            [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" add_edge research-wiki/ --from "exp:<id>" --to "claim:<cid>" --type supports --evidence "<metric>"
        elif verdict == "partial":
            Update claim page: status → partial
            [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" add_edge research-wiki/ --from "exp:<id>" --to "claim:<cid>" --type supports --evidence "partial"
        else:
            Update claim page: status → invalidated
            [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" add_edge research-wiki/ --from "exp:<id>" --to "claim:<cid>" --type invalidates --evidence "<why>"

    # 3. Update idea outcome (raw markdown, helper-free)
    Update research-wiki/ideas/<idea_id>.md:
      - outcome: positive | mixed | negative
      - If negative: fill "Failure / Risk Notes" and "Lessons Learned"
      - If positive: fill "Actual Outcome" and "Reusable Components"

    # 4. Rebuild + log (only if $WIKI_SCRIPT resolved)
    [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" rebuild_query_pack research-wiki/
    [ -n "$WIKI_SCRIPT" ] && python3 "$WIKI_SCRIPT" log research-wiki/ "result-to-claim: exp:<id> verdict=<verdict> for idea:<idea_id>"

    # 5. Re-ideation suggestion
    Count failed/partial ideas since last /idea-creator run.
    If >= 3: print "💡 3+ ideas tested since last ideation. Consider re-running /idea-creator — the wiki now knows what doesn't work."
```

## Rules

- **Codex is the judge, not CC.** CC collects evidence and routes; Codex evaluates. This prevents post-hoc rationalization.
- Do not inflate claims beyond what the data supports. If Codex says "partial", do not round up to "yes".
- A single positive result on one dataset does not support a general claim. Be honest about scope.
- If `confidence` is low, treat the judgment as inconclusive and add experiments rather than committing to a claim.
- If Codex MCP is unavailable (call fails), CC makes its own judgment and marks it `[pending Codex review]` — do not block the pipeline.
- Always record the verdict and reasoning in findings.md, regardless of outcome.
- Final claim outputs must surface implementation deviation impact and any relevant recovery-state warnings when those affect scope or confidence.

## Review Tracing

After each `mcp__codex__codex` or `mcp__codex__codex-reply` reviewer call, save the trace following `shared-references/review-tracing.md`. Use `tools/save_trace.sh` or write files directly to `.labline/traces/<skill>/<date>_run<NN>/`. Respect the `--- trace:` parameter (default: `full`).
