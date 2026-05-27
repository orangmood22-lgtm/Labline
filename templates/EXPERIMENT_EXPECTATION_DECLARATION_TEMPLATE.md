# Experiment Expectation Declaration Template

**Experiment Set**: 
**Date**: 
**Primary Claim**: 
**Linked Plan File**: 

## Runs

### Run: RXXX
- **Name**:
- **Type**: baseline / main / ablation / sanity / diagnostic
- **Compared Against**:
- **Metric of Record**:
- **Expected Direction**: increase / decrease / neutral
- **Expected Magnitude**: tiny / slight / moderate / large / catastrophic-for-bug-only
- **Expected Range**:
- **Rationale**:
- **If Opposite Direction Happens**:
- **If Delta == 0 Happens**:
- **If Extreme Value Happens (0, 100, NaN, inf)**:
- **Implementation-sensitive signals**:
- **Claim impact if confirmed**:

## Global Anomaly Rules
- `delta == 0` for a supposed effective modification → suspect broken integration or dead path
- unexpected sign reversal → suspect idea failure OR implementation bug; inspect both
- catastrophic drop when theory predicts mild change → first suspect bug before theory failure
- extreme scores (0 / 100 / NaN / inf) → suspect eval or metric pipeline bug before interpreting scientifically

## Reviewer Checklist
- [ ] Every must-run experiment has an expectation declaration
- [ ] Expectations are written before result interpretation
- [ ] Expected direction is tied to a rationale, not vibes
- [ ] Anomaly handling is explicit
