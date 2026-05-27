# 人机协作与质量保障机制可行性方案

> 基于 ARCHITECTURE_EXPLORATION_REPORT.md 讨论后的四个核心问题展开深度研究。
> 日期：2026-05-12
> 状态：方案探索阶段，待讨论确认

---

## 背景：讨论中提出的四个核心问题

| # | 问题 | 核心矛盾 |
|---|------|----------|
| 1 | Reviewer 的 Delta Assertion 不够深 | 只判断"有没有差异"，不判断"差异方向是否符合预期" |
| 2 | Leader 不看文件内容会导致盲人指挥 | 人必须参与关键节点，了解技术细节和实验结果 |
| 3 | 代码实现与 idea 构想的一致性难以审查 | 需求文档不够细，实现偏差难以发现 |
| 4 | 人的参与时机与项目并行化 | 人有休息周期，不能随时在线；Agent 需要合理安排等待与并行 |

以下逐一展开可行性方案。

---

## 一、Delta Assertion 深化：从"有差异"到"差异是否合理"

### 1.1 现有问题回顾

当前 ARCHITECTURE_EXPLORATION_REPORT 中提出的 Delta Assertion 只覆盖了最基本的一层：

```
当前设计：
  if 实验组 == 对照组 → FAIL（数值完全相同或差异 < epsilon）
```

但 FPA-IOD 项目暴露了更多层次的问题：

| 问题层次 | 示例 | 当前能否检测 |
|----------|------|-------------|
| L0: 无差异 | 三组结果完全相同（原型未注入） | 能（已设计） |
| L1: 方向反常 | 消融实验去掉模块后性能反而上升 | **不能** |
| L2: 幅度异常 | AP 从 100 直接跌到 0（非渐进退化） | **不能** |
| L3: 趋势异常 | 训练 loss 震荡不收敛但最终指标看起来正常 | **不能** |
| L4: 预期-实际偏差 | 消融应该轻微下降，实际显著下降 | **不能** |

### 1.2 方案：实验预期声明（Experiment Expectation Declaration）

**核心思路**：在实验设计阶段就写下"我预期看到什么"，实验结束后 Reviewer 拿着这个声明做偏差分析。

#### 1.2.1 声明格式设计

在 `EXPERIMENT_PLAN.md` 的每个实验 block 中新增 `expected_outcome` 字段：

```yaml
# 嵌入在 EXPERIMENT_PLAN.md 每个实验 block 中
- run_id: R003
  name: "Ablation: remove FPA module"
  type: ablation
  claim: "FPA module contributes to performance improvement"
  expected_outcome:
    direction: "decrease"           # 预期方向：increase / decrease / neutral
    magnitude: "slight"             # 预期幅度：slight(0-2%) / moderate(2-5%) / large(5%+)
    metric: "mAP@50"
    baseline_ref: "R001"            # 参照哪个 run 的结果
    rationale: "去掉 FPA 模块后，novel class 缺乏频域增广的多样性，原型质量下降，预期 mAP 轻微下降"
    anomaly_flags:                  # 什么情况算异常
      - "delta == 0 → 模块可能未生效（检查 forward pass）"
      - "direction == increase → 模块可能是负贡献（重新审视 idea）"
      - "magnitude == catastrophic(>20%) → 可能存在实现 bug 而非方法问题"
      - "metric == 0 or metric == 100 → 几乎确定是评估代码 bug"
```

#### 1.2.2 Delta Assertion 审查的三层架构

```
                    实验结果到手
                         │
                    ┌────┴────┐
                    │  L0 检查 │  自动化（脚本）
                    │  无差异？ │
                    └────┬────┘
                    PASS │ FAIL → 立即阻塞，诊断代码
                         │
                    ┌────┴────┐
                    │  L1 检查 │  半自动（Reviewer + 规则）
                    │  方向+幅度│
                    └────┬────┘
                    PASS │ WARN/FAIL → 需人工研判
                         │
                    ┌────┴────┐
                    │  L2 检查 │  人工（Human Review Point）
                    │  语义合理性│
                    └────┬────┘
                    PASS │ NEED_DISCUSSION → 汇报 + 等人确认
                         │
                      继续流程
```

**L0 — 自动化检查（脚本级）**：

```python
# tools/delta_assertion.py（新增工具脚本）
def check_l0(experiment_results, control_results, epsilon=1e-6):
    """检查实验组与对照组是否有数值差异"""
    for metric in experiment_results:
        delta = abs(experiment_results[metric] - control_results[metric])
        if delta < epsilon:
            return FAIL(f"实验组与对照组 {metric} 完全相同 (delta={delta})")
    return PASS

def check_l1(result, expectation):
    """检查结果方向和幅度是否符合预期"""
    actual_delta = result[expectation.metric] - baseline[expectation.metric]
    actual_direction = "increase" if actual_delta > 0 else "decrease" if actual_delta < 0 else "neutral"
    
    # 方向检查
    if actual_direction != expectation.direction and expectation.direction != "neutral":
        return WARN(f"方向反常：预期 {expectation.direction}，实际 {actual_direction}")
    
    # 幅度异常检查
    if abs(actual_delta) > 20:  # catastrophic
        return WARN(f"幅度异常：delta={actual_delta}%，可能存在 bug")
    
    # 绝对值异常检查
    if result[expectation.metric] == 0 or result[expectation.metric] == 100:
        return FAIL(f"指标为极端值 {result[expectation.metric]}，几乎确定是评估 bug")
    
    return PASS
```

**L1 — Reviewer 辅助判断（GPT 做语义分析）**：

Reviewer 拿到以下输入：
1. `EXPERIMENT_PLAN.md` 中的 `expected_outcome` 声明
2. 实际实验结果
3. L0/L1 自动检查报告

Reviewer 需要判断：
- 如果方向反常，这是"方法本身的问题"还是"实现 bug"？
- 如果幅度异常，是否有合理的科学解释？
- 综合所有实验结果，整体趋势是否自洽？

**L2 — 人工研判（Human Review Point）**：

以下情况必须等人确认：
- Reviewer 判断"可能是方法本身的问题"（涉及科研方向决策）
- 多个实验的异常模式形成一致性结论（比如"所有消融实验都表明核心模块是负贡献"）
- 结果与已发表文献的结论矛盾

### 1.3 与现有 ARIS 的兼容设计

| 改动点 | 影响范围 | 兼容性 |
|--------|----------|--------|
| `EXPERIMENT_PLAN.md` 增加 `expected_outcome` 字段 | `/experiment-plan` skill | 向后兼容（新字段可选） |
| 新增 `tools/delta_assertion.py` | 工具层 | 纯新增 |
| `experiment-audit` 审查清单增加 G/H/I 三项（已在架构报告中提出） | `/experiment-audit` skill | 扩展现有清单 |
| Reviewer 收到 expectation 声明作为审查上下文 | Codex MCP prompt | 不违反 reviewer-independence（声明是事前写的，不是事后解释） |

### 1.4 关键问题：预期声明是谁写的？

**方案 A：Executor 在 `/experiment-plan` 阶段写**
- 优点：Executor 最了解方法细节，预期最准确
- 缺点：Executor 可能写出"自证预言"式的预期（配合自己的实现 bug）
- 缓解：Reviewer 在代码审查阶段也审查预期声明的合理性

**方案 B：Leader 基于 idea 构想写粗略预期，Executor 细化**
- 优点：粗略方向由决策层把关
- 缺点：Leader 不了解实现细节，可能写不准

**方案 C（推荐）：Executor 写初稿 → Reviewer 审查合理性 → 人在检查点确认**
- 这样形成三层校验：写预期的、审预期的、最终确认的是三个不同角色
- 与"写代码的不能审代码"原则一致——"写预期的不能审预期"

### 1.5 可行性评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 技术可行性 | ★★★★★ | 纯文件格式扩展 + 脚本，无架构障碍 |
| 改造成本 | ★★★★☆ | 主要是写 `delta_assertion.py` 和修改 SKILL.md |
| 收益 | ★★★★★ | 直接解决 FPA-IOD 项目中"100→0 无人报警"和"三组相同无人发现"的问题 |
| 风险 | ★★☆☆☆ | 预期声明写得太松或太紧都会影响判断准确性 |

---

## 二、人机协作协议：人什么时候参与、怎么参与

### 2.1 核心原则

> **人不是系统的可选插件，人是系统的核心组件。**
> 但人的带宽是有限的，系统需要智能地利用人的注意力。

### 2.2 人在科研流水线中不可替代的五个角色

| 角色 | 为什么 Agent 做不好 | 参与形式 |
|------|---------------------|----------|
| **方向决策者** | Agent 没有"科研直觉"，无法判断一个方向的长期潜力 | 关键节点确认 |
| **结果解读者** | Agent 可以描述数字，但无法深度理解数字背后的科学含义 | 实验结果讨论 |
| **需求审核者** | Agent 写的需求文档可能有隐含假设或遗漏 | 文档审批 |
| **质量把关者** | Agent 的代码审查有盲区（集成 bug、语义 bug） | 代码抽查 |
| **风险预警者** | Agent 倾向于"做加法"，不善于判断何时该止损 | 异常告警响应 |

### 2.3 三级参与机制设计

#### Level 1: 异步通知（Async Notification）

**触发条件**：常规进展、阶段完成、非阻塞性信息

**实现方式**：Agent 生成结构化摘要报告 → 存入约定位置 → 人有空时查看

**摘要报告格式**（新增文件：`reports/STAGE_REPORT_<stage>_<timestamp>.md`）：

```markdown
# 阶段报告：Experiment-Bridge Phase 5 完成

**时间**: 2026-05-12 03:00 UTC
**阶段**: experiment-bridge → Phase 5 (Collect Results)
**状态**: 正常完成 ✅

## 关键数字
| 实验 | 指标 | 结果 | vs Baseline | 预期方向 | 符合？ |
|------|------|------|-------------|----------|--------|
| Main (FPA) | mAP@50 | 94.0 | +0.0 | increase | ❌ |
| Ablation-1 | mAP@50 | 93.2 | -0.8 | decrease | ✅ |

## Delta Assertion 结果
- L0 (无差异检查): ⚠️ WARN — Main vs Baseline delta=0
- L1 (方向检查): N/A (delta=0 已触发 L0 warning)

## Agent 判断
需要人确认：Main 实验结果与 Baseline 完全相同，可能存在代码 bug 或方法无效。

## 下一步
- [ ] 等待人确认后决定：诊断代码 / 重新审视方法 / 其他
- [ ] 可并行执行：文献补充调研（不依赖此决策）

## 人需要关注的文件
- `refine-logs/EXPERIMENT_RESULTS.md` — 完整实验结果
- `EXPERIMENT_AUDIT.md` — 审查报告
```

**通知渠道**：
- 飞书/Slack 消息（通过 `/feishu-notify` skill，已有）
- 本地文件系统（`reports/` 目录）
- CLI 输出摘要

#### Level 2: 同步检查点（Sync Checkpoint）

**触发条件**：关键决策点、方向性选择、异常告警

**核心设计：检查点队列（Checkpoint Queue）**

```json
// CHECKPOINT_QUEUE.json（新增文件，Leader 维护）
{
  "queue": [
    {
      "id": "CP-001",
      "priority": "high",
      "type": "direction_decision",
      "created_at": "2026-05-12T03:00:00Z",
      "title": "Main 实验结果为零效果，需要决定下一步",
      "context_file": "reports/STAGE_REPORT_experiment_bridge_20260512.md",
      "options": [
        {"id": "A", "label": "诊断代码 bug", "auto_executable": true},
        {"id": "B", "label": "重新审视方法设计", "auto_executable": false},
        {"id": "C", "label": "补充文献调研后再决定", "auto_executable": true},
        {"id": "D", "label": "终止该方向", "auto_executable": false}
      ],
      "blocking": true,
      "blocked_tasks": ["main-experiment-iteration-2"],
      "non_blocked_tasks": ["literature-supplement", "code-cleanup"],
      "status": "waiting_human",
      "human_response": null,
      "timeout_hours": 12,
      "timeout_action": "notify_again"
    }
  ]
}
```

**检查点的触发规则**：

| 触发条件 | 优先级 | 是否阻塞 | 说明 |
|----------|--------|----------|------|
| Delta Assertion L0 FAIL | **critical** | 阻塞 | 实验组=对照组，几乎确定有 bug |
| Delta Assertion L1 方向反常 | **high** | 阻塞 | 可能是方法问题或 bug |
| 连续 N≥3 次失败 | **high** | 阻塞 | 止损判断必须人来做 |
| Gate 决策（选 idea、Pivot） | **high** | 阻塞 | 方向性决策 |
| 需求文档/架构文档审批 | **medium** | 阻塞 | 人审核后才能开始实现 |
| 里程碑完成 | **low** | 不阻塞 | 通知性，人有空看 |
| 常规进展 | **info** | 不阻塞 | 存日志即可 |

#### Level 3: 协作讨论（Collaborative Discussion）

**触发条件**：里程碑完成后的总结讨论、多选项决策、头脑风暴

**实现方式**：多 Agent + 人的结构化讨论

**讨论议程模板**（`reports/DISCUSSION_AGENDA_<topic>_<timestamp>.md`）：

```markdown
# 讨论议程：第一轮实验全部完成，下一步方向

**发起方**: Leader Agent
**参与方**: 人 + Executor Agent + Reviewer Agent
**预计时长**: 30 min
**前置阅读**: reports/STAGE_REPORT_all_experiments_20260512.md

## 议题 1: 实验结果解读
- Agent 准备的材料：结果汇总表、与文献对比、异常点列表
- 需要人确认：结果解读是否正确？有没有遗漏的角度？

## 议题 2: 下一步方向
- 选项 A: [描述]，预估成本 X GPU-hours，预期收益 Y
- 选项 B: [描述]，预估成本 X GPU-hours，预期收益 Y
- 选项 C: 止损，转向新方向
- 需要人决策：选哪个？或者有其他想法？

## 议题 3: 需求文档修订
- 基于实验结果，需要修订哪些假设？
- 新的实验计划初稿（Executor 准备）是否准确？

## 会后行动项
- [ ] （待填写）
```

### 2.4 人的活跃时间感知机制

**核心问题**：Agent 7×24 运行，但人有作息周期。如何避免在人休息时发送阻塞性请求？

#### 方案设计：活跃窗口 + 消息分级

```json
// HUMAN_AVAILABILITY.json（新增配置文件，人手动设置）
{
  "timezone": "Asia/Shanghai",
  "active_windows": [
    {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "23:00"},
    {"days": ["sat", "sun"], "start": "10:00", "end": "22:00"}
  ],
  "notification_policy": {
    "during_active": {
      "critical": "immediate_notify",
      "high": "immediate_notify",
      "medium": "batch_every_2h",
      "low": "daily_digest",
      "info": "silent_log"
    },
    "during_rest": {
      "critical": "queue_for_next_active + gentle_notify",
      "high": "queue_for_next_active",
      "medium": "queue_for_next_active",
      "low": "daily_digest",
      "info": "silent_log"
    }
  },
  "do_not_disturb": false,
  "vacation_mode": false,
  "delegation": {
    "if_unavailable_12h": "auto_select_safest_option",
    "if_unavailable_24h": "pause_pipeline"
  }
}
```

**关键设计决策**：

1. **Critical 级别在休息时间的处理**：不强行叫醒人，而是排队到下一个活跃窗口 + 发一条温和通知（比如手机推送，人看到就看到，没看到就等）
2. **长时间无响应的降级策略**：
   - 12小时无响应 → Agent 自动选择"最安全的选项"（即不做方向性改变，只做不依赖该决策的并行任务）
   - 24小时无响应 → 暂停流水线，等人回来

### 2.5 汇报机制：定期摘要 + 按需深度报告

#### 定期摘要（Daily Digest）

```markdown
# ARIS 日报 — 2026-05-12

## 今日进展
- ✅ idea-discovery 完成，3 个候选 idea
- ✅ experiment-plan 完成，已生成实验计划
- 🔄 experiment-bridge Phase 2（实现代码）进行中
- ⏸️ 等待人确认：idea 选择（CP-001）

## 待人处理
1. [high] CP-001: 选择实验 idea（3选1）→ 阻塞后续实现
2. [low] 文献调研报告可供浏览

## 资源使用
- GPU-hours: 2.3 / 50.0 预算
- API tokens: ~45K (Leader) + ~120K (Executor) + ~30K (Reviewer)

## 明日预计
- 如果 CP-001 今天确认：明天可完成代码实现+审查
- 如果 CP-001 明天确认：今天 Agent 做文献补充调研（不阻塞）
```

#### 按需深度报告

当人要求"详细说说实验结果"时，Agent 生成详细技术报告（类似 `FULL_PROGRESS_REPORT.md` 的格式，但针对特定主题）。

### 2.6 可行性评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 技术可行性 | ★★★★☆ | 核心是文件+队列，但通知渠道需要适配（飞书/Slack） |
| 改造成本 | ★★★☆☆ | 需要新建 checkpoint 管理逻辑、报告生成逻辑 |
| 收益 | ★★★★★ | 解决"人不知道项目在干什么"和"Agent 盲目执行"的根本问题 |
| 风险 | ★★★☆☆ | 过度依赖人的响应可能拖慢流程；需要平衡人的参与度和 Agent 自主性 |

---

## 三、需求文档细化与代码实现一致性审查

### 3.1 问题本质

```
idea 构想（抽象）
    ↓  信息损失 1：idea → 需求文档（可能遗漏隐含假设）
需求文档（半精确）
    ↓  信息损失 2：需求文档 → 代码（可能实现偏差）
代码实现（具体）
    ↓  信息损失 3：代码 → 评估（可能评估方式不匹配）
实验结果
```

FPA-IOD 项目中的每一层都出了问题：
- 损失1：没有明确"原型需要注入到分类器的哪一层"
- 损失2：原型算了但没注入（调用链断裂）
- 损失3：eval 用了训练集

### 3.2 需求文档的细化标准：四层递进

#### 第一层：Method Description（已有，FINAL_PROPOSAL.md）

```markdown
## 方法描述
对 backbone 输出的 RoI features 做 FFT → 振幅缩放 → 相位扰动 → IFFT 重建 → 取平均构建原型
```

**问题**：太抽象，"取平均构建原型"之后呢？原型怎么用？注入到哪里？

#### 第二层：Data Flow Specification（新增，需要人审核）

```markdown
## 数据流规格

### 输入
- RoI features: tensor [N, C, H, W] where C=256, H=W=7
- Support set: k=5 shots per novel class

### 处理流程
1. Backbone(image) → feature_map [B, 256, H', W']
2. RPN(feature_map) → proposals [N, 4]
3. RoI_Align(feature_map, proposals) → roi_features [N, 256, 7, 7]
4. FPA_Augmentor(roi_features) → augmented_features [N*10, 256, 7, 7]  
   # 每个原始 feature 生成 10 个增广版本
5. box_head.fc6(roi_features.flatten()) → [N, 1024]
6. box_head.fc7([N, 1024]) → [N, 1024]
7. **PrototypeBank**: 对每个 novel class，聚合其 support set 的 fc7 输出 → prototype [1, 1024]
8. **注入点**: cls_score.weight[novel_class_idx] = prototype  # ← 这一步必须明确！

### 关键约束
- 原型维度必须 = cls_score.weight 的输入维度 = 1024（不是 256！）
- FPA 增广在 roi_features 层面做（256-dim），但原型在 fc7 层面聚合（1024-dim）
- 评估使用 VOC2007 val split（is_train=False）
```

#### 第三层：Pseudocode Specification（新增，需要人审核）

```python
## 伪代码规格

# --- 训练阶段 ---
def train_incremental(model, base_data, novel_support_set):
    # Phase 1: Base training (freeze)
    model.backbone.requires_grad_(False)
    model.rpn.requires_grad_(False)
    
    # Phase 2: Build prototypes for novel classes
    proto_bank = {}
    for cls_id, support_images in novel_support_set.items():
        features = []
        for img in support_images:
            feat = model.backbone(img)                    # [1, 256, H', W']
            proposals = model.rpn(feat)                    # [M, 4]
            roi_feat = model.roi_align(feat, proposals)    # [M, 256, 7, 7]
            
            # FPA augmentation
            aug_feats = fpa_augmentor(roi_feat)             # [M*10, 256, 7, 7]
            
            # 通过 box_head 提升到 1024-dim
            fc_feat = model.box_head(aug_feats.flatten(1))  # [M*10, 1024]
            features.append(fc_feat)
        
        proto_bank[cls_id] = torch.cat(features).mean(0)   # [1024]
    
    # Phase 3: ⚠️ 关键步骤 — 注入原型到分类器
    for cls_id, proto in proto_bank.items():
        model.cls_score.weight.data[cls_id] = proto         # ← 必须执行！

# --- 评估阶段 ---
def evaluate(model, val_loader):   # ← 必须是 val_loader，不是 train_loader！
    ...
```

#### 第四层：Verification Assertions（新增，自动化检查）

```python
## 验证断言（嵌入实验代码中）

# assert_1: 原型维度匹配
assert proto_bank[cls_id].shape[-1] == model.cls_score.weight.shape[-1], \
    f"Proto dim {proto_bank[cls_id].shape[-1]} != classifier dim {model.cls_score.weight.shape[-1]}"

# assert_2: 原型已注入
for cls_id in novel_class_ids:
    assert not torch.equal(model.cls_score.weight[cls_id], original_weights[cls_id]), \
        f"Class {cls_id} 的分类器权重未更新，原型注入失败！"

# assert_3: 评估使用正确的 split
assert val_loader.dataset.split == "val", \
    f"评估使用了 {val_loader.dataset.split} split，应使用 val！"

# assert_4: 实验组与对照组输出不同（Delta Assertion）
if experiment_type == "ablation":
    assert not np.allclose(exp_results, ctrl_results, atol=1e-6), \
        "实验组与对照组输出完全相同，核心改动可能未生效！"
```

### 3.3 文档审核流程

```
Executor 写初稿
    ↓
第一层（Method Description）   → Reviewer 审查逻辑完整性
第二层（Data Flow Spec）       → Reviewer 审查维度匹配 + 人审核关键设计决策
第三层（Pseudocode Spec）      → Reviewer 逐行审查 + 人抽查核心逻辑
第四层（Verification Assertions） → 自动嵌入代码
    ↓
人最终审批："可以开始实现了"
    ↓
Executor 按文档实现
    ↓
代码实现一致性审查（见 3.4）
```

### 3.4 代码实现一致性审查（Implementation Conformance Review）

在 Executor 完成代码后，**新增一个审查维度**：不只审代码质量，还审"代码是否忠实实现了需求文档"。

**审查方式**：Reviewer 同时拿到：
1. 需求文档（四层）
2. 实际代码

**审查清单（新增）**：

```markdown
### J. Implementation Conformance Review（实现一致性审查）

对照需求文档逐项检查：

1. **数据流一致性**：代码中的张量流转是否与 Data Flow Spec 一致？
   - 每个模块的输入输出 shape 是否匹配文档描述？
   - 数据流中是否有文档未提及的额外变换？
   
2. **关键步骤完整性**：Pseudocode Spec 中标记为"关键"的步骤是否全部实现？
   - 原型注入是否执行？
   - 评估 split 是否正确？
   - 增广参数是否与文档一致？
   
3. **验证断言嵌入**：Verification Assertions 是否全部嵌入代码？
   - 运行时断言是否存在？
   - 断言条件是否与文档一致？

4. **偏差记录**：如果代码因技术原因偏离了文档（比如维度不匹配需要加投影层），
   是否明确记录了偏差原因？
   
FAIL if: 需求文档的关键步骤在代码中缺失或偏离且无记录。
WARN if: 存在非关键偏差但有合理记录。
```

### 3.5 "人什么时候审"的具体规则

| 文档类型 | 人是否必须审 | 理由 |
|----------|-------------|------|
| Method Description（第一层） | **是，简要审** | 确认方向和核心思路 |
| Data Flow Spec（第二层） | **是，重点审** | 这是最容易出错的地方（维度、注入点、数据流） |
| Pseudocode Spec（第三层） | **是，抽查核心逻辑** | 人不需要逐行看，但要确认关键步骤 |
| Verification Assertions（第四层） | **可选** | 如果前三层审核充分，断言基本不会出错 |
| 代码实现 | **抽查** | Reviewer 做完一致性审查后，人看 Reviewer 的报告 + 抽查关键文件 |

### 3.6 可行性评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 技术可行性 | ★★★★★ | 核心是文档格式规范 + 审查清单扩展 |
| 改造成本 | ★★★☆☆ | 需要定义文档模板、修改多个 SKILL.md、培训 Executor 按格式写文档 |
| 收益 | ★★★★★ | 直接解决"原型未注入"这类集成 bug |
| 风险 | ★★★☆☆ | 文档写得太细可能拖慢 Executor 效率；需要找到"细到什么程度"的平衡点 |

---

## 四、项目并行化与人的工作窗口

### 4.1 核心矛盾再分析

```
Agent 时间线：  ████████████████████████████████████████████████  （7×24 连续）
人的时间线：    ▓▓▓▓▓▓▓▓░░░░░▓▓▓▓▓▓▓▓░░░░░▓▓▓▓▓▓▓▓░░░░░        （活跃-休息交替）
              ▓ = 活跃    ░ = 休息

阻塞点：       ────────────X──────────X───────X────────────       （需人决策的时刻）
```

**效率损失的三个来源**：
1. Agent 在等人，但有其他可做的事 → 应该并行
2. 人在休息，Agent 把阻塞请求堆到队列 → 应该批量处理
3. 多条实验线互相不依赖，但串行执行 → 应该真正并行

### 4.2 任务依赖图（Task Dependency Graph）

**关键洞察**：不是所有任务都是线性依赖的。把流水线建模为 DAG，就能找到并行化机会。

```
                    idea-discovery
                    /          \
                idea-A          idea-B（如果人说"先做A，同时调研B相关文献"）
                  |               |
            experiment-plan-A   lit-review-B（并行！）
                  |               |
           [人审核 plan-A]    [存报告，不阻塞]
                  |               
            code-impl-A         
                  |              
           [Reviewer 审代码]     
                  |              
            run-experiment-A     
                  |              
           [Delta Assertion]     
                  |              
       ┌─────────┴──────────┐
       │                    │
  [结果正常]            [结果异常]
       │                    │
  auto-review-loop    [等人判断] ← 此时可以先做 idea-B 的 experiment-plan
       │
  paper-writing
```

### 4.3 并行化的三种模式

#### 模式 1：流水线内并行（Intra-Pipeline Parallelism）

同一个项目内，不同实验互相独立时并行执行。

**已有支持**：`experiment-bridge` 的 `MAX_PARALLEL_RUNS = 4` 和 `/experiment-queue` 已经支持多实验并行。

**需要扩展**：
- 多个 ablation 实验可以同时跑
- 主实验和文献补充调研可以同时进行
- 代码审查等待期间可以做其他准备工作

#### 模式 2：等待期并行（Wait-Time Utilization）

当一条任务线被阻塞（等人、等 GPU、等 Reviewer 回复）时，切到另一条不依赖该阻塞的任务线。

**实现机制**：

```json
// TASK_POOL.json（Leader 维护的任务池）
{
  "active_tasks": [
    {
      "id": "T-001",
      "description": "Main experiment implementation",
      "status": "blocked",
      "blocked_by": "CP-001 (waiting human decision)",
      "priority": 1
    },
    {
      "id": "T-002",
      "description": "Literature survey for alternative approach",
      "status": "ready",
      "blocked_by": null,
      "priority": 2,
      "note": "不依赖 CP-001，可以先做"
    },
    {
      "id": "T-003",
      "description": "Code cleanup and documentation",
      "status": "ready",
      "blocked_by": null,
      "priority": 3,
      "note": "低优先级，填充空闲时间"
    }
  ]
}
```

**Leader 的调度逻辑**：
```
while pipeline_running:
    task = get_highest_priority_unblocked_task(TASK_POOL)
    if task:
        assign_to_executor(task)
    else:
        # 所有任务都被阻塞
        if has_prep_work():
            do_prep_work()  # 预案准备：为人的不同决策预先准备材料
        else:
            wait_and_poll(interval=30min)
```

#### 模式 3：多方向探索并行（Multi-Direction Parallelism）

当 Gate 决策涉及多个候选方向时，可以在有限预算内对多个方向做浅度探索。

**场景**：idea-discovery 产出 3 个候选 idea，人还没确认选哪个。

**策略**：
- 对每个 idea 做轻量级可行性验证（dry-run、维度检查、框架兼容性）
- 但**不做完整实验**（等人确认后才投入 GPU 资源）
- 这样人回来后可以看到"每个方向的可行性评估"，做更有信息的决策

```
人休息中...

Agent 并行做：
├─ idea-A: 写实验计划初稿 + 检查数据集可用性 + 代码框架搭建
├─ idea-B: 写实验计划初稿 + 检查关键依赖是否可装
└─ idea-C: 快速文献补充 → 发现与已有工作高度重叠 → 标记为低优先

人醒来后看到：
"idea-A 和 B 都可行，C 与 XX 论文重叠。推荐 A，plan 初稿已写好待审。"
```

### 4.4 预案机制（Contingency Preparation）

当 Agent 等待人的决策时，可以为**多种可能的决策结果**预先准备：

```
等待人对 CP-001 的决策：

决策 A: "诊断代码 bug"
  → Agent 预先准备：诊断脚本已写好，待人确认后立即执行

决策 B: "重新审视方法设计"
  → Agent 预先准备：相关文献列表已整理，方法对比表已做

决策 C: "止损"
  → Agent 预先准备：postmortem 报告模板已填写
```

**限制**：预案准备的成本应该远低于完整执行的成本。如果预案本身也很贵（比如需要 GPU），那就不做预案，只做文本级准备。

### 4.5 人的批量处理模式

当人上线后，不是逐条处理队列中的请求，而是先看一个**汇总视图**：

```markdown
# 待处理事项汇总 — 2026-05-12 09:00

## 紧急（阻塞中）
1. CP-001: Main 实验零效果，需决定下一步 [阻塞 8h]
   - 推荐：先诊断代码（Agent 已准备好诊断脚本）
   - 备选：重新审视方法 / 止损

## 待审核
2. experiment-plan-A 初稿待审 [不阻塞，但审完后可加速]
3. 文献调研报告可供浏览 [纯信息，不阻塞]

## 已自动处理（仅供知）
4. Code cleanup 已完成
5. 依赖安装检查已完成

## 今日预计
- 如果 09:30 前确认 CP-001 → 预计下午可有新实验结果
- 如果同时审完 experiment-plan-A → 预计明天可开始新方向
```

### 4.6 可行性评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 技术可行性 | ★★★★☆ | 任务池+依赖图是标准调度问题；多方向并行需要 Agent 子任务支持 |
| 改造成本 | ★★★☆☆ | Leader 的调度逻辑需要从简单的串行变为 DAG 调度 |
| 收益 | ★★★★★ | 最大化利用等待时间，显著提升端到端效率 |
| 风险 | ★★★☆☆ | 并行度太高可能导致 Leader 上下文膨胀；预案准备可能浪费资源 |

---

## 五、综合架构：四个机制如何协同工作

### 5.1 全景流程图

```
人设置 HUMAN_AVAILABILITY.json
    │
    ▼
Leader 启动流水线
    │
    ├─── Stage 0: 评估基础设施检查（自动）
    │
    ├─── Stage 1: idea-discovery（Executor）
    │         │
    │         ▼
    │    [Reviewer 审查 idea]
    │         │
    │         ▼
    │    Gate 1 → 【Level 2 检查点：人选 idea】
    │         │         同时 Agent 做多方向浅度探索（模式3）
    │         │
    │    人确认 ←─── 人上线看汇总 ←─── 日报推送
    │         │
    │         ▼
    ├─── 需求文档细化（Executor 写 → Reviewer 审 → 人审核）
    │         │
    │    【Level 2 检查点：人审批需求文档】
    │         │
    │         ▼
    ├─── Stage 2: 代码实现（Executor）
    │         │
    │         ▼
    │    [Reviewer 代码审查 + 实现一致性审查]
    │         │
    │    人抽查代码（可选，基于 Reviewer 报告）
    │         │
    │         ▼
    ├─── Stage 3: 跑实验（Executor）
    │         │
    │         ▼
    │    Delta Assertion 三层检查
    │    ├── L0 自动 → PASS/FAIL
    │    ├── L1 Reviewer → PASS/WARN
    │    └── L2 人判断 → 如果需要
    │         │
    │    如果 PASS → 继续
    │    如果 WARN → 【Level 1 通知人】+ Agent 继续做可并行任务
    │    如果 FAIL → 【Level 2 检查点：等人决策】+ Agent 做预案准备
    │         │
    │         ▼
    ├─── Stage 4: auto-review-loop
    │    （每轮结束 → Level 1 通知 + 日报）
    │    （连续3轮失败 → Level 2 检查点：止损决策）
    │         │
    │         ▼
    │    【Level 3 协作讨论：实验完成总结】
    │         │
    │         ▼
    └─── Stage 5+: paper-writing（如果适用）
```

### 5.2 四个机制的交互关系

```
Delta Assertion ──发现异常──→ 触发 Level 2 检查点 ──通知人──→ 人机协作协议
                                    │
                              等待人决策
                                    │
                              Agent 执行 ──→ 并行化机制（做不依赖该决策的任务）
                                    │
                              人确认后执行 ──→ 需求文档审查（如果涉及方向调整）
```

### 5.3 新增文件清单

| 文件 | 位置 | 维护者 | 用途 |
|------|------|--------|------|
| `HUMAN_AVAILABILITY.json` | 项目根目录 | 人 | 活跃时间配置 |
| `CHECKPOINT_QUEUE.json` | 项目根目录 | Leader | 待人处理的检查点队列 |
| `TASK_POOL.json` | 项目根目录 | Leader | 任务池（含依赖关系） |
| `tools/delta_assertion.py` | tools/ | 工具 | Delta Assertion 自动化检查 |
| `reports/STAGE_REPORT_*.md` | reports/ | Leader/Executor | 阶段报告 |
| `reports/DAILY_DIGEST_*.md` | reports/ | Leader | 日报 |
| `reports/DISCUSSION_AGENDA_*.md` | reports/ | Leader | 讨论议程 |
| `templates/DATA_FLOW_SPEC_TEMPLATE.md` | templates/ | 模板 | 数据流规格模板 |
| `templates/PSEUDOCODE_SPEC_TEMPLATE.md` | templates/ | 模板 | 伪代码规格模板 |

### 5.4 新增/修改的审查清单项

| 清单项 | 所属 Skill | 状态 |
|--------|-----------|------|
| G. Train/Val/Test Split Correctness | experiment-audit | 新增（已在架构报告中提出） |
| H. Core Modification Effect Verification (Delta Assertion) | experiment-audit | 新增（已在架构报告中提出） |
| I. Dimension / Shape Compatibility | experiment-audit | 新增（已在架构报告中提出） |
| **J. Implementation Conformance Review** | experiment-audit 或 experiment-bridge | **本文新增** |
| **K. Expectation Declaration Review** | experiment-audit | **本文新增** |

---

## 六、实施路线图

### Phase 1: 最小可行版（3-5 天）

**优先做收益最高、成本最低的改动：**

1. **需求文档模板**：创建 Data Flow Spec 和 Pseudocode Spec 模板
2. **Delta Assertion 脚本**：实现 `tools/delta_assertion.py`（L0 + L1 自动检查）
3. **实验预期声明格式**：在 EXPERIMENT_PLAN.md 中增加 `expected_outcome` 字段
4. **审查清单扩展**：experiment-audit 增加 G/H/I/J/K 五项

**此阶段不改架构**，只增加文档规范和工具脚本。

### Phase 2: 人机协作基础（5-7 天）

5. **Checkpoint Queue 机制**：实现 CHECKPOINT_QUEUE.json 管理
6. **阶段报告生成**：实现 STAGE_REPORT 自动生成
7. **日报生成**：实现 DAILY_DIGEST 自动生成
8. **HUMAN_AVAILABILITY.json 配置**：实现活跃窗口感知

### Phase 3: 并行化调度（7-10 天）

9. **TASK_POOL 管理**：实现任务依赖图和调度逻辑
10. **等待期并行**：Leader 在等待人时自动切到可用任务
11. **预案机制**：为多种决策结果预先准备

### Phase 4: 端到端验证（3-5 天）

12. **用 FPA-IOD 做回归测试**：验证 Delta Assertion 能否在 Phase 1 就发现 eval bug
13. **用新项目做前向测试**：验证全流程人机协作是否顺畅
14. **调整参数**：根据实际使用调整检查点触发条件、通知频率等

---

## 七、开放问题（待讨论）

### Q1: 需求文档细化到什么程度？

**权衡**：太粗 → 实现偏差；太细 → 写文档本身消耗太多时间，且限制了 Executor 的灵活性。

**初步建议**：
- 核心模块（idea 的创新点）：细化到伪代码级
- 辅助模块（数据加载、训练循环、日志）：只写接口规格
- 标准组件（backbone、optimizer）：引用已有配置即可

### Q2: 人不在时 Agent 的自主权限边界？

**当前设计是保守的**：关键决策一律等人。但这可能导致 Agent 长时间闲置。

**激进方案**：给 Agent 设置"自主决策预算"——在预算内可以自行决定（比如自动选排名第一的 idea），超出预算必须等人。

**问题**：这与 FPA-IOD 的 `AUTO_PROCEED=true` 自动选了导致后续问题如出一辙。需要谨慎。

### Q3: Leader 到底要不要看文件内容？

架构报告中建议"Leader 不看文件内容"以保持上下文精简。但你指出这会导致盲人指挥。

**折中方案**：
- Leader 不看代码文件（太长，交给 Reviewer）
- Leader **看结构化摘要**（实验结果表、审查报告摘要）
- Leader **看需求文档**（只有几页，值得读）
- 关键决策前，Leader 读取相关的 STAGE_REPORT

**实际效果**：Leader 的上下文消耗从"不读任何文件"增加到"读摘要和报告"，大约多用 2000-5000 tokens/次，可接受。

### Q4: 如何衡量人机协作的效率？

**需要追踪的指标**：
- 检查点平均等待时间（人响应延迟）
- Agent 等待期利用率（等待人时做了多少有效工作）
- 人的每次参与的平均耗时
- 因人参与而避免的错误数量
- 端到端项目完成时间 vs 纯自动模式

### Q5: 多项目并行怎么办？

如果人同时管多个 ARIS 项目，检查点队列会跨项目叠加。需要一个**全局仪表盘**，而不是每个项目单独看。

**初步想法**：一个全局的 `~/.aris/GLOBAL_CHECKPOINT_QUEUE.json`，汇聚所有项目的待处理事项。

---

## 八、总结

| 机制 | 解决的核心问题 | 技术复杂度 | 收益 |
|------|--------------|-----------|------|
| Delta Assertion 深化 | "100→0 无人报警"、"消融方向反常无人发现" | 低 | 极高 |
| 人机协作协议 | "人不知道项目进展"、"Agent 盲目执行" | 中 | 极高 |
| 需求文档细化 | "原型未注入"、"eval 用训练集" | 低-中 | 极高 |
| 并行化调度 | "Agent 等人时闲置"、"串行效率低" | 中-高 | 高 |

**四个机制互相强化**：
- Delta Assertion 发现问题 → 触发人机协作 → 人做决策 → 并行化保证效率
- 需求文档细化 → 减少实现偏差 → 减少 Delta Assertion 的 FAIL → 减少人的干预次数

**建议优先级**：Delta Assertion > 需求文档细化 > 人机协作协议 > 并行化调度

前两个改动成本低、收益高，可以立即开始。后两个需要更多架构改造，可以在前两个验证后再启动。

---

*文档生成时间：2026-05-12。待你回来后一起讨论确认。*
