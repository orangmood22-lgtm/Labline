# Pseudocode Spec Template

**Project**: 
**Method / Module**: 
**Date**: 
**Owner**: 

## 1. Intent
- One-paragraph statement of what the implementation should do.
- Include the non-goal: what should NOT accidentally change.

## 2. Pseudocode
```text
for each batch / sample / class:
    read source features from <module>
    apply <transformation>
    verify <condition>
    inject into <target>
    run evaluation on <split>
    save metrics to <artifact>
```

## 3. Mapping To Real Code
| Pseudocode Step | Expected File | Expected Function / Class | Notes |
|-----------------|---------------|---------------------------|-------|
|                 |               |                           |       |

## 4. Edge Cases
- Empty class / no support samples:
- Shape mismatch:
- Variable-length / variable-size inputs:
- Missing checkpoints / missing result files:
- Metric computation failure:

## 5. Verification Hooks
- Unit-level assertion:
- Integration-level assertion:
- Delta assertion trigger:
- Expected failure signatures:

## 6. Reviewer Questions
- [ ] Does the pseudocode match the method description rather than a simplified approximation?
- [ ] Does every critical transformation have a concrete code location?
- [ ] Are failure branches specified instead of silently ignored?
- [ ] Can a reviewer trace from idea → pseudocode → code without guessing?
