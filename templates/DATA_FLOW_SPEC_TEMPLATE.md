# Data Flow Spec Template

**Project**: 
**Method / Module**: 
**Date**: 
**Owner**: 

## 1. Goal
- What exact mechanism should be implemented?
- Which claim or experiment block does it support?

## 2. Upstream Inputs
| Input Name | Source File / Module | Shape / Type | Semantics | Required? |
|------------|----------------------|--------------|-----------|-----------|
|            |                      |              |           |           |

## 3. Transformation Path
| Step | Location | Input | Operation | Output | Failure Risk |
|------|----------|-------|-----------|--------|--------------|
| 1    |          |       |           |        |              |

## 4. Downstream Injection Point
| Target | File / Function | How It Is Consumed | Why This Is the Critical Path |
|--------|------------------|--------------------|-------------------------------|
|        |                  |                    |                               |

## 5. Train / Eval Data Path
- Training split used:
- Validation / test split used:
- Ground truth source:
- Official metric / eval script:
- Leakage checks:

## 6. Expected Observable Effects
| Observable | Baseline Expectation | Modified Expectation | If Missing, Suspect |
|------------|----------------------|----------------------|---------------------|
|            |                      |                      |                     |

## 7. Assertions To Implement
```python
# Example:
# assert val_loader.dataset.split == "val"
# assert feature.shape[-1] == cls_head.weight.shape[-1]
# assert not torch.equal(modified_weight, original_weight)
```

## 8. Reviewer Checklist
- [ ] Upstream input really exists and is read from the intended source
- [ ] Modification is on the actual forward / eval critical path
- [ ] Train/val/test split usage is explicit and correct
- [ ] Shape / dimension compatibility is documented
- [ ] There is at least one observable effect that can falsify a broken integration
