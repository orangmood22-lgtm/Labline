# 可行性方案补充：回溯验证 × 模板设计 × 改造清单

> 作为 `HUMAN_IN_THE_LOOP_FEASIBILITY_REPORT.md` 的补充文档。
> 日期：2026-05-12
> 内容：FPA-IOD 回溯验证、具体模板文件、SKILL.md 改造清单

---

## 一、FPA-IOD 回溯验证：新方案能拦截多少 Bug？

### 1.1 验证方法

将 PAIN_POINT_DIAGNOSIS.md 中记录的 9 个 bug，逐一对照新方案中的每个机制，判断：
- 能否拦截？
- 在哪个阶段拦截？
- 通过什么机制拦截？

### 1.2 完整对照表

| # | Bug | 严重性 | 原ARIS能否拦截 | 新方案能否拦截 | 拦截机制 | 在哪个阶段拦截 |
|---|-----|--------|--------------|--------------|---------|-------------|
| 1 | eval 用训练集（`is_train=True`） | 🔴致命 | ❌ | ✅ **能** | ① 需求文档第二层（Data Flow Spec）会明确写 `eval 使用 val split`<br>② 第四层 Verification Assertion 嵌入 `assert split=="val"`<br>③ experiment-audit Check G（Split Correctness）<br>④ 如果以上全漏：Delta Assertion L2 发现 mAP=100 的极端值 → FAIL | Stage 2（文档审核）或 Stage 3（运行时断言）|
| 2 | 原型未注入分类器 | 🔴致命 | ⚠️可能 | ✅ **能** | ① 需求文档第二层会明确写"注入点：`cls_score.weight[idx] = proto`"<br>② 第三层 Pseudocode 会标记此步为 ⚠️ 关键步骤<br>③ 第四层 Assertion：`assert not torch.equal(weight[idx], original)`<br>④ 审查清单 J（Implementation Conformance）逐项对照<br>⑤ Delta Assertion L0：实验组==对照组 → FAIL | Stage 2（文档+代码审查）或 Stage 3（L0 自动检测）|
| 3 | 原型 256-dim vs 分类器 1024-dim | 🔴致命 | ⚠️部分 | ✅ **能** | ① 需求文档第二层明确标注每层张量 shape<br>② 审查清单 I（Dimension/Shape Compatibility）<br>③ 运行时 assertion：`assert proto.shape[-1] == weight.shape[-1]`<br>④ Phase 3 sanity check 也会报 RuntimeError（已有） | Stage 2（文档审核就能发现） |
| 4 | `import torch.nn as nn` 语法兼容 | 🟡中等 | ❌ | ⚠️ **部分** | 新增的 Stage 0 评估基础设施检查可包含 `python -c "import ..."` 级别的 dry-run。但具体的单行多 import 语法问题仍难以预判 | Stage 0（部分覆盖）|
| 5 | 空间 RoI 尺寸不一致 | 🟡中等 | ❌ | ⚠️ **部分** | 需求文档第二层如果写清"RoI 特征图大小可能不同，需逐样本处理或统一 resize"，可以预防。审查清单 I 的维度检查也能辅助发现 | Stage 2（取决于文档是否覆盖此细节） |
| 6 | `tee` 缓冲导致日志为空 | 🟡中等 | ❌ | ❌ **不能** | 这是 shell 行为的工程细节，新方案不覆盖此类基础设施问题 | — |
| 7 | AP 计算 O(N²) 超时 | 🟡中等 | ❌ | ❌ **不能** | 性能问题不在审查范围。需求文档可以备注"使用 pycocotools 标准实现"来间接规避 | — |
| 8 | GitHub 被墙 | 🟡中等 | ❌ | ❌ **不能** | 网络环境问题，不在方案覆盖范围 | — |
| 9 | detectron2 装不了 | 🟡中等 | ❌ | ⚠️ **部分** | Stage 0 基础设施检查可包含依赖可装性检查（`pip install --dry-run`） | Stage 0（如果实现） |

### 1.3 拦截率对比

| | 原 ARIS | 新方案 |
|---|---------|--------|
| 🔴致命 bug（3个） | 0 / 3 可靠拦截 | **3 / 3 可靠拦截** |
| 🟡中等 bug（6个） | 0 / 6 可靠拦截 | **0 / 6 可靠，3 / 6 部分** |
| **总计** | **0 / 9** | **3 可靠 + 3 部分 = 6 / 9** |

### 1.4 关键结论

**新方案对致命 bug 的拦截率从 0% 提升到 100%。** 这是最重要的收益——致命 bug 是导致 FPA-IOD 项目浪费 28h 工作量的根本原因。

中等 bug 的覆盖提升有限（0% → 50% 部分覆盖），这些主要是工程基础设施问题（shell 行为、网络环境、依赖安装），需要单独的"环境诊断"机制来解决，不在本方案范围内。

### 1.5 逐 Bug 深度回溯

#### Bug #1: eval 用训练集 — 四重拦截网

```
时间线回溯（如果有新方案）：

[Stage 2: 需求文档细化]
  Executor 写 Data Flow Spec：
    "评估阶段：model.eval() → val_loader(split='val') → compute_mAP"
  
  → 如果 Executor 写的时候就写错了（写成 train_loader）：
    Reviewer 审查 Data Flow Spec 时会对照 experiment-plan 中的预期
    experiment-plan 说 "在 val 集上评估"
    Data Flow Spec 写 "train_loader" → 矛盾 → FAIL

  → 如果 Data Flow Spec 写对了但代码写错了：
    第四层 Verification Assertion 嵌入：
      assert val_loader.dataset.split == "val"
    代码运行时 → RuntimeError → 立即发现

  → 如果 assertion 被遗漏了：
    审查清单 J（Implementation Conformance）：
      "评估 split 是否正确？" → Reviewer 对照文档和代码 → 发现不匹配

  → 如果 Reviewer 也没发现：
    实验跑完后，Delta Assertion L2：
      mAP@50 = 100% → 极端值 → FAIL
      "指标为极端值 100，几乎确定是评估 bug"

  结论：4 层拦截，至少有 1 层会生效。
```

#### Bug #2: 原型未注入分类器 — 三重拦截网

```
时间线回溯（如果有新方案）：

[Stage 2: 需求文档细化]
  Data Flow Spec 第 8 步明确写：
    "注入点: cls_score.weight[novel_class_idx] = prototype"
  Pseudocode Spec 标记为 ⚠️ 关键步骤

  → Executor 写代码时遗漏了注入步骤：
    审查清单 J：对照 Pseudocode Spec 逐项检查
    "关键步骤 Phase 3（注入原型到分类器）是否实现？"
    → 代码中找不到对应实现 → FAIL

  → 如果 Reviewer 也没发现：
    第四层 Verification Assertion：
      assert not torch.equal(weight[idx], original_weight[idx])
    运行时 → AssertionError → "原型注入失败"

  → 如果 assertion 被遗漏了：
    Delta Assertion L0：
      实验组 == 对照组 → FAIL
      "三组结果完全相同，核心改动可能未生效"

  结论：3 层拦截，最晚在实验结果出来后立即发现（而非像 FPA-IOD 那样连续迭代 3 个版本）。
```

#### Bug #3: 维度不匹配 — 文档阶段就能发现

```
时间线回溯（如果有新方案）：

[Stage 2: 需求文档细化]
  Data Flow Spec 明确写出每层张量维度：
    "FPA_Augmentor 输出: [N*10, 256, 7, 7]"
    "box_head.fc7 输出: [N, 1024]"
    "PrototypeBank 聚合: [1, 1024]"
    "cls_score.weight 维度: [num_classes, 1024]"

  → 如果 Executor 直接用 256-dim 的 roi_features 做原型（跳过 box_head）：
    Reviewer 审查 Data Flow Spec 就会发现：
    "原型 256-dim 与 cls_score.weight 1024-dim 不匹配"
    → 在写代码之前就修正设计

  → 如果到了代码阶段：
    审查清单 I（Dimension/Shape Compatibility）：
    "module A 输出 shape [256] 是否匹配 module B 期望输入 [1024]？" → FAIL

  结论：文档审核阶段就能发现，节省 GPU 时间。
```

---

## 二、具体模板文件设计

### 2.1 Data Flow Specification 模板

```markdown
# Data Flow Specification: [项目名/方法名]

> 本文档定义核心数据处理流程中每个模块的输入输出规格。
> 所有张量 shape 使用 PyTorch 约定: [batch, channels, height, width] 或 [batch, features]。
> ⚠️ 标记表示关键约束，实现时必须严格遵守。

## 1. 输入数据

| 数据 | 来源 | 格式 | shape / 类型 | 备注 |
|------|------|------|-------------|------|
| 训练图像 | [数据集名] train split | tensor | [B, 3, H, W] | H, W 可变 |
| 验证图像 | [数据集名] val split | tensor | [B, 3, H, W] | ⚠️ 评估必须使用 val split |
| Support set | [数据集名] novel classes | tensor | k=5 shots/class | |

## 2. 处理流程

### 阶段 A: [阶段名称]

```
模块名(输入描述) → 输出描述
  输入: [shape]
  输出: [shape]
  关键参数: [列出]
```

### 阶段 B: [阶段名称]

```
模块名(输入描述) → 输出描述
  输入: [shape]
  输出: [shape]
  ⚠️ 关键约束: [描述]
```

### ...（按实际阶段数量添加）

## 3. 注入点 / 集成点

> 不同模块之间的连接方式。这是最容易出错的地方。

| 源模块 | 目标模块 | 传递什么 | shape | ⚠️ 约束 |
|--------|---------|---------|-------|---------|
| [源] | [目标] | [数据描述] | [shape] | [维度必须匹配的条件] |

## 4. 评估流程

| 步骤 | 操作 | ⚠️ 约束 |
|------|------|---------|
| 1 | 加载模型 checkpoint | |
| 2 | 加载评估数据 | ⚠️ 必须使用 val/test split，不是 train |
| 3 | 推理 | |
| 4 | 计算指标 | ⚠️ 使用标准评估库（如 pycocotools） |

## 5. 关键约束汇总

> 从上文中提取所有 ⚠️ 标记的约束，集中列表：

- [ ] 约束 1: [描述]
- [ ] 约束 2: [描述]
- [ ] ...

## 审核记录

| 审核方 | 日期 | 结论 | 备注 |
|--------|------|------|------|
| Reviewer (GPT) | | | |
| 人 | | | |
```

### 2.2 Pseudocode Specification 模板

```markdown
# Pseudocode Specification: [项目名/方法名]

> 本文档用伪代码精确定义核心算法逻辑。
> ⚠️ 关键步骤 标记的代码段必须在实现中完整体现，审查清单 J 会逐项验证。
> 伪代码使用 Python 风格，但不要求可直接运行。

## 1. 核心算法

### 1.1 [算法/模块名称]

```python
def core_method(input_1, input_2, ...):
    """
    功能: [一句话描述]
    输入: input_1 [shape/type], input_2 [shape/type]
    输出: output [shape/type]
    """
    # Step 1: [步骤描述]
    intermediate = operation(input_1)  # [shape]
    
    # ⚠️ 关键步骤: [为什么关键]
    # Step 2: [步骤描述]
    result = critical_operation(intermediate)  # [shape]
    
    return result
```

### 1.2 [第二个核心模块]

```python
# ...
```

## 2. 训练流程

```python
def train(model, data, config):
    # Phase 1: [描述]
    ...
    
    # ⚠️ 关键步骤: [描述为什么关键]
    # Phase 2: [描述]
    ...
    
    # ⚠️ 关键步骤: [描述为什么关键]
    # Phase 3: [描述]
    ...
```

## 3. 评估流程

```python
def evaluate(model, val_loader):  # ⚠️ 必须是 val_loader
    """
    ⚠️ 约束:
    - 数据来源: val/test split（绝不是 train split）
    - 指标计算: 使用标准库（如 pycocotools）
    - 输出格式: JSON，包含所有指标
    """
    ...
```

## 4. ⚠️ 关键步骤汇总

> 从上文中提取所有 ⚠️ 标记的步骤，集中列表。实现一致性审查（Check J）会逐项对照。

| # | 关键步骤 | 所在函数 | 为什么关键 | 如果缺失的后果 |
|---|---------|---------|-----------|-------------|
| K1 | [描述] | [函数名] | [原因] | [后果] |
| K2 | [描述] | [函数名] | [原因] | [后果] |
| ... | | | | |

## 审核记录

| 审核方 | 日期 | 结论 | 备注 |
|--------|------|------|------|
| Reviewer (GPT) | | | |
| 人 | | | |
```

### 2.3 Experiment Expectation Declaration 模板

```yaml
# Experiment Expectation Declaration
# 嵌入在 EXPERIMENT_PLAN.md 的每个实验 block 中

- run_id: R001
  name: "[实验名称]"
  type: baseline | main | ablation | robustness | analysis
  claim: "[该实验要验证的 claim]"
  
  expected_outcome:
    direction: increase | decrease | neutral
    # increase: 预期指标上升
    # decrease: 预期指标下降（如消融实验去掉有效模块）
    # neutral: 预期无显著变化（如鲁棒性测试）
    
    magnitude: slight | moderate | large
    # slight: 0-2% 变化
    # moderate: 2-5% 变化
    # large: 5%+ 变化
    
    metric: "[主要评估指标，如 mAP@50]"
    baseline_ref: "[参照的 run_id]"
    
    rationale: "[一两句话解释为什么预期这个方向/幅度]"
    
    anomaly_flags:
      zero_delta: "delta ≈ 0 → [可能原因和应对]"
      reverse_direction: "方向反转 → [可能原因和应对]"
      catastrophic: "变化 > 20% → [可能原因和应对]"
      extreme_value: "指标 = 0 或 100 → [可能原因和应对]"
  
  # 可选：与其他实验的关系
  depends_on: [前置实验的 run_id]
  contradicts_if: "[描述什么结果会与其他实验矛盾]"
```

---

## 三、SKILL.md 具体改造清单

### 3.1 改造范围总览

| SKILL.md | 改动类型 | 改动内容 | 优先级 |
|----------|---------|---------|--------|
| `experiment-plan/SKILL.md` | 扩展 | 增加 expected_outcome 字段要求 | P0 |
| `experiment-audit/SKILL.md` | 扩展 | 增加 G/H/I/J/K 五项审查清单 | P0 |
| `experiment-bridge/SKILL.md` | 修改 | 增加需求文档细化阶段、强制 CODE_REVIEW=true | P0 |
| `research-pipeline/SKILL.md` | 修改 | 增加检查点机制、Delta Assertion 触发 | P1 |
| `auto-review-loop/SKILL.md` | 扩展 | 增加连续失败止损触发、阶段报告生成 | P1 |
| `run-experiment/SKILL.md` | 扩展 | 增加 Stage 0 基础设施检查 | P1 |
| `monitor-experiment/SKILL.md` | 扩展 | 增加 Delta Assertion 自动触发 | P2 |
| `result-to-claim/SKILL.md` | 扩展 | 增加 expectation vs actual 对比 | P2 |

### 3.2 各 SKILL.md 具体改动

#### 3.2.1 `experiment-plan/SKILL.md` — P0

**现状**：生成 EXPERIMENT_PLAN.md，包含 run order、claim、success criterion，但没有 expected_outcome。

**改动**：

```markdown
## 新增：Phase 2.5 — Expectation Declaration（在生成实验计划后）

为 EXPERIMENT_PLAN.md 中的每个实验 block 填写 expected_outcome：

1. 对于每个实验，基于方法设计和文献先验，预判：
   - **方向**：该实验的指标相对 baseline 应该上升还是下降？
   - **幅度**：预期变化的大致范围？
   - **异常标志**：什么结果算异常？
   
2. 使用 `templates/EXPERIMENT_EXPECTATION_TEMPLATE.yaml` 格式

3. ⚠️ 预期声明必须在实验跑之前写好，不能事后补写。
   这确保了预期不会被实际结果"反向污染"。

4. 预期声明的合理性将在代码审查阶段由 Reviewer 一并审查。
```

#### 3.2.2 `experiment-audit/SKILL.md` — P0

**现状**：审查清单 A-F（GT Provenance、Score Normalization、Result Existence、Dead Code、Scope、Eval Type）。

**改动**：在 Audit Checklist 中新增 G/H/I/J/K：

```markdown
## 新增审查清单项

### G. Train/Val/Test Split Correctness
For each evaluation script:
1. Which data split is used for evaluation? (train / val / test)
2. Is it the INTENDED evaluation split per EXPERIMENT_PLAN.md?
3. Is there any data leakage (training data appearing in evaluation)?
4. Check for: hardcoded `is_train=True`, `split='train'`, `train_loader` in eval context
FAIL if: Evaluation runs on training data without explicit proxy labeling.

### H. Core Modification Effect Verification (Delta Assertion)
For experiment groups vs control group:
1. Are the outputs numerically different?
2. If outputs are identical, does the proposed modification actually affect the forward pass?
3. Trace the data flow: input → modification → output. Is the modification on the critical path?
4. Check for: computed but unused variables, modules instantiated but not called
FAIL if: Experiment group outputs are identical to control group.

### I. Dimension / Shape Compatibility
For each module integration point:
1. Does the output shape of module A match the expected input shape of module B?
2. Are there any silent broadcasts or reshapes that mask incompatibility?
3. Cross-check against Data Flow Specification if available.
WARN if: Shape mismatches exist but are auto-broadcast.
FAIL if: Shape mismatch would cause runtime error or silent semantic error.

### J. Implementation Conformance Review（需求文档存在时触发）
If Data Flow Spec and/or Pseudocode Spec exist for this project:
1. For each step in Data Flow Spec: is there corresponding code implementing it?
2. For each ⚠️ 关键步骤 in Pseudocode Spec: is it implemented in code?
3. Are Verification Assertions embedded in the code?
4. Are deviations from the spec documented with rationale?
FAIL if: Critical steps missing without documented rationale.
WARN if: Non-critical deviations exist with rationale.
NOT_APPLICABLE if: No spec documents exist.

### K. Expectation Declaration Review（expected_outcome 存在时触发）
If EXPERIMENT_PLAN.md contains expected_outcome fields:
1. Are the expected directions scientifically reasonable?
2. Are the anomaly_flags comprehensive?
3. Do the expectations align with the method's claimed contributions?
4. Are there contradictions between different experiments' expectations?
WARN if: Expectations seem overly optimistic or contradictory.
NOT_APPLICABLE if: No expected_outcome fields exist.
```

#### 3.2.3 `experiment-bridge/SKILL.md` — P0

**现状**：Phase 1 解析计划 → Phase 2 实现代码 → Phase 2.5 代码审查（可关闭）→ Phase 3 Sanity → Phase 4 部署

**改动**：

```markdown
## 改动 1: CODE_REVIEW 默认值改为 true 且不可关闭

旧：
  - **CODE_REVIEW = true** — ... Set `false` to skip.
新：
  - **CODE_REVIEW = true** — GPT-5.4 xhigh reviews experiment code before deployment. 
    ⚠️ This setting is MANDATORY and cannot be overridden to false. 
    Cross-model code review is a non-negotiable integrity constraint.

## 改动 2: 新增 Phase 1.5 — Specification Authoring（在 Phase 1 和 Phase 2 之间）

### Phase 1.5: Write Technical Specifications

Before writing any code, create detailed specifications:

1. **Data Flow Specification** (`refine-logs/DATA_FLOW_SPEC.md`)
   - Use template: `templates/DATA_FLOW_SPEC_TEMPLATE.md`
   - Cover: all module inputs/outputs with tensor shapes
   - Mark: integration points and critical constraints with ⚠️
   
2. **Pseudocode Specification** (`refine-logs/PSEUDOCODE_SPEC.md`)
   - Use template: `templates/PSEUDOCODE_SPEC_TEMPLATE.md`  
   - Cover: core algorithm, training flow, evaluation flow
   - Mark: ⚠️ 关键步骤 that must appear in implementation
   
3. **Verification Assertions** (`refine-logs/VERIFICATION_ASSERTIONS.md`)
   - List runtime assertions to embed in code
   - Cover: dimension checks, injection verification, split verification, delta checks

4. **Send specs to Reviewer for review** (same mechanism as Phase 2.5 code review)

5. **[CHECKPOINT] Specifications ready for human review**
   - Generate STAGE_REPORT with spec summary
   - If human checkpoint enabled: wait for human approval before Phase 2
   - If AUTO_PROCEED: wait 10 seconds, then proceed

## 改动 3: Phase 2.5 审查清单扩展

在现有的 6 项代码审查基础上，新增：

    7. **Implementation Conformance**: Does the code faithfully implement 
       DATA_FLOW_SPEC.md and PSEUDOCODE_SPEC.md? Check each ⚠️ critical step.
    8. **Verification Assertions embedded**: Are all assertions from 
       VERIFICATION_ASSERTIONS.md present in the code?
    9. **Split correctness**: Does evaluation code use the correct data split?
       Check for hardcoded `is_train=True` or `split='train'`.

## 改动 4: Phase 5 结果收集后增加 Delta Assertion

### Phase 5.5: Delta Assertion（在收集结果后、Handoff 前）

After collecting initial results:

1. Run `tools/delta_assertion.py` with:
   - Experiment results
   - Control/baseline results  
   - Expected outcomes from EXPERIMENT_PLAN.md

2. L0 check (automatic):
   - If experiment == control → FAIL → stop and report
   
3. L1 check (automatic + Reviewer):
   - If direction mismatch or extreme values → WARN → report to human
   
4. If all PASS → proceed to Handoff
5. If FAIL → generate diagnostic task, report to human, do NOT proceed
```

#### 3.2.4 `research-pipeline/SKILL.md` — P1

**改动**：

```markdown
## 改动 1: 新增 Stage 0 — Infrastructure Check（在 Stage 1 之前）

### Stage 0: Infrastructure Check

Before any experiments, verify the evaluation infrastructure:

1. **Environment probe**: Python version, installed packages, GPU availability
2. **Data availability**: Check that required datasets exist and are readable
3. **Eval pipeline dry-run**: Run evaluation on 5 samples to confirm the pipeline works
4. **Split verification**: Confirm which split is used for evaluation
5. **Dependency check**: Verify all required packages can be imported

If any check fails → fix before proceeding. Do not start experiments on broken infrastructure.

## 改动 2: Gate 决策增加人机协作触发

### Gate 1 改造

旧: AUTO_PROCEED=true 时自动选 #1
新: 
  - AUTO_PROCEED=true 时，仍自动选 #1，但同时生成 STAGE_REPORT 通知人
  - AUTO_PROCEED=false 时，加入 CHECKPOINT_QUEUE 等待人确认
  - 无论哪种模式，如果有 HUMAN_AVAILABILITY.json 且人在活跃时间内，发送通知

## 改动 3: 止损机制与连续失败计数

在 PIPELINE_STATE.json 中追踪连续失败次数：
  - 每次 Delta Assertion FAIL 或 auto-review-loop 评分下降 → consecutive_failures++
  - consecutive_failures >= 3 → 强制暂停，触发方向性审查
  - 方向性审查结果: CONTINUE（重置计数）/ PIVOT（回退 idea） / ABORT（终止）
```

#### 3.2.5 `auto-review-loop/SKILL.md` — P1

**改动**：

```markdown
## 改动 1: 每轮结束生成阶段报告

### Phase E 改造（每轮 Documentation 阶段）

在现有的 REVIEW_STATE.json 更新后，新增：

1. 生成 `reports/STAGE_REPORT_review_round_N_<timestamp>.md`
   包含：本轮评分、主要问题、修改内容、下轮计划

2. 如果 HUMAN_CHECKPOINT=true：等人确认后继续
   如果 HUMAN_CHECKPOINT=false：继续，但报告存入 reports/ 供人异步查看

## 改动 2: 连续失败触发止损

### 新增：Phase F — Regression Check（每轮 Phase E 之后）

Check if the current round made things worse:

1. Compare current score with previous round's score
2. If score decreased for 2 consecutive rounds:
   - Set `regression_flag = true` in REVIEW_STATE.json
   - Generate warning in STAGE_REPORT
3. If score decreased for 3 consecutive rounds:
   - STOP the loop (even if MAX_ROUNDS not reached)
   - Generate CHECKPOINT_QUEUE entry: "连续 3 轮退化，需人决定是否继续"
   - Switch to direction review mode (not just "how to fix" but "is this fixable")
```

#### 3.2.6 `run-experiment/SKILL.md` — P1

**改动**：

```markdown
## 改动: Pre-flight Check 扩展

### 现有 Pre-flight Check
- GPU availability
- Screen session management

### 新增 Pre-flight 项目

4. **Code compatibility check**:
   - `python -c "import torch; import [key_packages]"` 
   - Verify Python version compatibility
   
5. **Data path verification**:
   - Check that all data paths referenced in config/argparse actually exist
   - Check read permissions
   
6. **Quick dry-run** (if not already done in Stage 0):
   - Run 1 iteration of training + 1 evaluation on 5 samples
   - Confirm no crashes, output format correct
```

#### 3.2.7 `monitor-experiment/SKILL.md` — P2

**改动**：

```markdown
## 改动: 实验完成后自动触发 Delta Assertion

### Phase 3 改造（Result Collection 阶段）

After collecting results and updating the tracker:

1. If EXPERIMENT_PLAN.md has expected_outcome for this run:
   - Run `tools/delta_assertion.py` on the collected results
   - Include assertion results in the notification message

2. If Delta Assertion FAIL:
   - Change notification type from `experiment_done` to `experiment_anomaly`
   - Include anomaly details in notification body
```

#### 3.2.8 `result-to-claim/SKILL.md` — P2

**改动**：

```markdown
## 改动: 增加 Expectation vs Actual 对比

### 新增 Phase: Expectation Alignment Check

Before mapping results to claims:

1. Read expected_outcome from EXPERIMENT_PLAN.md
2. For each experiment:
   - Compare actual direction vs expected direction
   - Compare actual magnitude vs expected magnitude
   - Flag mismatches

3. Include in Codex prompt:
   "The experimenter expected [direction] [magnitude] change. 
    The actual result was [actual]. 
    Does this discrepancy suggest a method issue, implementation bug, or valid scientific finding?"

4. If Codex judges "implementation bug likely" → recommend code audit before claiming
```

---

## 四、新增工具脚本设计

### 4.1 `tools/delta_assertion.py`

```python
#!/usr/bin/env python3
"""
Delta Assertion Tool for ARIS
Checks experiment results against expectations and baselines.

Usage:
  python3 tools/delta_assertion.py \
    --results results/experiment_results.json \
    --baseline results/baseline_results.json \
    --expectations refine-logs/EXPERIMENT_PLAN.md \
    --output DELTA_ASSERTION_REPORT.json

Exit codes:
  0 = all PASS
  1 = at least one WARN (non-blocking)
  2 = at least one FAIL (blocking)
"""

# L0: Zero-delta check
# - Compare experiment vs control numerically
# - FAIL if all metrics identical (within epsilon)

# L1: Direction check  
# - Compare actual direction vs expected direction
# - WARN if mismatch

# L1b: Magnitude check
# - WARN if magnitude is catastrophic (>20% change)
# - FAIL if metric hits extreme value (0 or 100 for percentage metrics)

# L1c: Cross-experiment consistency
# - WARN if ablation results contradict each other

# Output: JSON report with per-experiment verdicts
# {
#   "overall_verdict": "PASS|WARN|FAIL",
#   "experiments": [
#     {
#       "run_id": "R001",
#       "l0_verdict": "PASS",
#       "l1_direction_verdict": "PASS", 
#       "l1_magnitude_verdict": "WARN",
#       "details": "..."
#     }
#   ]
# }
```

### 4.2 `tools/generate_stage_report.py`

```python
#!/usr/bin/env python3
"""
Stage Report Generator for ARIS
Generates structured markdown reports for human consumption.

Usage:
  python3 tools/generate_stage_report.py \
    --stage experiment-bridge \
    --phase "Phase 5: Collect Results" \
    --status completed \
    --results results/ \
    --delta-report DELTA_ASSERTION_REPORT.json \
    --output reports/STAGE_REPORT_<stage>_<timestamp>.md

Reads:
  - PIPELINE_STATE.json for global context
  - EXPERIMENT_PLAN.md for expectations
  - Delta assertion report for anomalies
  - Recent experiment results

Outputs:
  - Structured markdown report with:
    - Key numbers table
    - Delta assertion results
    - Agent's preliminary judgment
    - Next steps (with blocking/non-blocking classification)
    - Files human should review
"""
```

---

## 五、与现有 shared-references 的兼容性分析

| 现有协议 | 是否需要修改 | 说明 |
|----------|-------------|------|
| `reviewer-independence.md` | **不需要** | 新方案完全遵守"只传文件路径"原则。expected_outcome 是事前写的客观声明，不是 executor 的事后解释 |
| `experiment-integrity.md` | **小幅扩展** | 需要增加"评估 split 正确性"作为新的 integrity 维度 |
| `effort-contract.md` | **小幅扩展** | 新增 spec authoring 的 effort 分级（lite=跳过 spec / balanced=写 Data Flow / max=写 Pseudocode / beast=写全四层） |
| `assurance-contract.md` | **不需要** | 新增的 Check G-K 自然融入现有 verdict 状态机（PASS/WARN/FAIL/NOT_APPLICABLE/BLOCKED/ERROR） |
| `integration-contract.md` | **不需要** | 新方案遵循其 6 项要求（activation predicate、canonical helper、concrete artifact、visible checklist、backfill、verifier） |
| `output-versioning.md` | **不需要** | 新增的报告文件遵循现有的时间戳 + 固定名双写策略 |
| `review-tracing.md` | **不需要** | 新增的审查维度自然记录 trace |

---

## 六、effort 分级对 Spec 深度的影响

| effort 级别 | Spec 要求 | 人审核要求 | Delta Assertion |
|-------------|----------|-----------|-----------------|
| **lite** | 跳过 spec（只写 Method Description） | 不要求 | L0 只检查（自动） |
| **balanced** | Data Flow Spec（第二层） | 人审核 Data Flow Spec | L0 + L1 自动检查 |
| **max** | Data Flow + Pseudocode（第二三层） | 人审核两份 spec | L0 + L1 + Reviewer L2 |
| **beast** | 全四层 + Verification Assertions | 人审核全部 + 抽查代码 | 全部三层 + 人最终判断 |

这与 effort-contract.md 的分级哲学一致：更高的 effort 带来更深的审查，但基本的安全网（L0 Delta Assertion）在所有级别都存在。

---

*补充文档生成时间：2026-05-12。与主文档 `HUMAN_IN_THE_LOOP_FEASIBILITY_REPORT.md` 配合阅读。*
