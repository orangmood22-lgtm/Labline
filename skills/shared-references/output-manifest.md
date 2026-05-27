# Output Manifest Protocol

After writing any output file, append an entry to `MANIFEST.md` in the project root.

## Format

If `MANIFEST.md` does not exist, create it with this header:

```markdown
# Research Output Manifest

> Auto-maintained by ARIS skills. Tracks all generated artifacts across the research lifecycle.

| Timestamp | Skill | File | Stage | Description |
|-----------|-------|------|-------|-------------|
```

Then append one row per output file written:

```
| 2025-06-15 14:30 | /idea-creator | idea-stage/IDEA_REPORT_20250615_143022.md | idea-discovery | 12 ideas generated from "LLM reasoning" direction |
| 2025-06-15 14:30 | /idea-creator | idea-stage/IDEA_REPORT.md | idea-discovery | latest copy |
```

## Stage Values

| Stage | Skills |
|-------|--------|
| `idea-discovery` | /idea-creator, /idea-discovery, /novelty-check, /research-review |
| `implementation` | /research-refine, /research-refine-pipeline, /experiment-plan, /experiment-bridge, /run-experiment |
| `review` | /auto-review-loop |
| `paper` | /paper-writing, /paper-write, /paper-compile |

## Experiment-chain manifest guidance

For load-bearing experiment workflows, record enough detail in the
manifest description field that a later reviewer can reconstruct the
plan → run → audit → claim chain without rereading the whole repo. At a
minimum, manifest rows for these artifact classes should mention the
upstream object they depend on:

- **Plan artifacts** — mention the claim or milestone set they define.
- **Run artifacts** — mention which milestone / run IDs / variants they
  executed, and include any canonical drift or recovery receipt when it
  changes what downstream stages should trust.
- **Audit artifacts** — mention which plan/results set they audited, and
  whether implementation deviations or recovery-state receipts were part
  of the reviewed context.
- **Claim artifacts** — mention which experiment or audit verdict they
  interpret, especially when scope/confidence changed because of drift,
  delta weakness, or recovery warnings.

When practical, include short references such as claim IDs, block IDs,
run IDs, or the source artifact filename in the description column.
This keeps `MANIFEST.md` human-readable while still making cross-stage
traceability possible.

## Pre-flight Check

Before writing output, if the skill depends on a prerequisite file from a previous stage:
1. Check if the prerequisite file exists at its expected stage-scoped path (e.g., `idea-stage/IDEA_REPORT.md`, `review-stage/AUTO_REVIEW.md`)
2. If not found at the stage-scoped path, check the legacy root-level path (e.g., `./IDEA_REPORT.md`, `./AUTO_REVIEW.md`) — see [Path Fallback Rule](output-versioning.md#path-fallback-rule-backward-compatibility)
3. If not found at either path, warn: "⚠️ Expected {file} (from {skill}) but not found. Run {skill} first?"
4. Do not block — the user may have the file elsewhere or want to proceed anyway
