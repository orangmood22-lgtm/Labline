---
name: skill-dag-check
description: Analyze skill dependency impact before modification. Shows upstream dependencies, downstream dependents, and artifact flow. Use when planning to modify, rename, or remove a skill, or when investigating skill relationships.
caller: any
invokes:
  - write-a-skill
examples:
  - "/skill-dag-check paper-write"
  - "analyze skill dependencies"
  - "what skills depend on this one"
---

# Skill DAG Check

Analyze dependency impact for: **$ARGUMENTS**

## Process

1. **Load current DAG**
   ```bash
   ARIS_REPO="${ARIS_REPO:-$(awk -F'\t' '$1=="repo_root"{print $2; exit}' .aris/installed-skills-codex.txt 2>/dev/null)}"
   python3 "$ARIS_REPO/tools/generate_skill_dag.py" --check-only
   ```

2. **Parse target skill** — identify skill name from arguments

3. **Compute impact** — read `docs/SKILL_DAG.yaml`:
   - Direct upstream (what this skill invokes)
   - Direct downstream (what invokes this skill)
   - Transitive upstream (all dependencies)
   - Transitive downstream (all affected skills)

4. **Report findings**:
   - Summary counts
   - List of affected skills grouped by caller type
   - Artifact flow (produces/consumes)

5. **Recommendations**:
   - If **removing**: warn about broken dependents, list all downstream skills
   - If **renaming**: suggest update locations (which SKILL.md files reference this skill)
   - If **adding invokes**: validate those skills exist in the DAG
   - If **changing caller**: warn about caller-type violations

## Output Format

```
## Impact Analysis: paper-writing

### Downstream (affected by changes to this skill)
- Direct: 5 skills (experiment-audit, experiment-bridge, grant-proposal, patent-pipeline, research-pipeline)
- Transitive: 12 skills total

### Upstream (this skill depends on)
- Direct: 15 skills
- Transitive: 28 skills total

### Artifacts
- Produces: paper/main.tex, paper/main.pdf
- Consumes: NARRATIVE_REPORT.md, EXPERIMENT_LOG.md

### Recommendations
- WARNING: 5 skills directly invoke this skill
- Before removing, update callers in: experiment-audit, experiment-bridge, ...
```

## Visualization

For visual exploration, open `docs/skill-dag.html` in a browser:
- Click nodes to see dependency details
- Use Impact Mode to highlight transitive impact chains
- Filter by caller type (leader/executor/any)
