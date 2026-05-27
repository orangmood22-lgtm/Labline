# ARIS 改造进度详细汇报（面向非代码背景）

> 写给现在的你：如果你觉得 ARIS 里面的 `SKILL.md`、队列、审计、claim gate 这些东西看起来很多、很散，这份文档的目标就是把“我们到底改了什么、为什么改、现在到哪一步了”讲清楚。
>
> 一句话先说结论：**这次改造的重点，不是让流水线“更能跑”，而是让它“跑完以后产出的研究结果更可信、更可追踪、更不容易自欺欺人”。**

---

## 0. 先说人话版结论

你之前遇到的问题，本质上不是“命令没执行成功”，而是：

- 流程可以机械地跑通；
- 但 **计划**、**实际实现**、**实验结果**、**最后 claim** 之间缺少足够强的“对账机制”；
- 再加上长流程运行过程中，遇到中断、重试、坏响应、状态丢失时，系统缺少统一的恢复规则；
- 所以最后就容易出现一种很危险的情况：
  - 从操作层面看，一切都完成了；
  - 但从科研层面看，结果不一定能支撑你真正想说的话。

这次我做的工作，主要分成两条线：

1. **实验链条加固**：把“计划 → 实现 → 审计 → claim”这条链条补上明确契约。
2. **恢复/可靠性加固**：把“运行中断了怎么办、响应坏了怎么办、状态怎么保存”这些问题收紧。

你可以把它理解成：

- 第一条线是在补 **科研诚实度和可解释性**；
- 第二条线是在补 **工程可靠性和可恢复性**。

---

## 1. 为什么之前“跑通了”，结果却还是不可用？

这是这次所有改造的出发点。

### 1.1 旧问题不是“不会跑”，而是“跑了也不一定有科研意义”

旧链条里，存在几个典型风险：

#### 风险 A：计划写的是一回事，后面实际跑的是另一回事

比如：

- 原计划说跑 test split；
- 实际实现时悄悄用了 val split；
- 原计划说要比较 baseline A / baseline B / 新方法；
- 实际只跑了 baseline A；
- 原计划说要跑 3 个 seed；
- 实际只跑了 1 个。

如果系统不强制记录这些偏差，后面就会出现一个假象：

> “看起来像是在验证原计划，实际上验证的可能只是一个缩水版、偏移版、甚至错误版计划。”

这就是我一直在收紧的 **plan drift（计划漂移）** 问题。

---

#### 风险 B：代码虽然跑了，但关键改动可能根本没生效

这是研究自动化里非常常见、也非常坑的情况。

例如：

- 你加了一个新模块；
- 但这个模块没接到真正前向路径上；
- 或者虽然接上了，但输出和 baseline 完全一样；
- 或者某个开关没生效，导致“实验组”和“对照组”本质上没区别。

这种情况下：

- 训练能跑；
- 输出文件能生成；
- 指标也能算；
- 但这个实验其实没有真正测试到你想测试的改动。

所以这次改造里，我把 **Delta Assertion（差异断言）** 提升成了核心概念：

> 不只是问“程序有没有跑起来”，而是问“实验组和对照组之间，是否真的出现了本来应该出现的差异”。

---

#### 风险 C：最后的 claim 可能比证据更大

旧流程里还有一个很危险的问题：

- 结果文件有了；
- 数字看上去也还行；
- 但这些数字到底支持多强的结论，没有被严格收口。

比如：

- 只在一个数据集上有效，却想写成“通用提升”；
- 只做了 proxy evaluation，却写得像真实 GT 验证；
- 审计已经发现有问题，但最后 claim 还是照常往外说。

这次我重点强化了 `result-to-claim`，让它不再只是“看结果写结论”，而是必须把：

- 计划里的 claim 预期；
- 实际结果；
- 审计结论；
- 实现偏差；
- 恢复期警告；

一起纳入判断。

换句话说：

> 现在系统更像一个“科研法官”，不是一个“数字抄写员”。

---

#### 风险 D：长流程一旦中断，后续状态会变得很暧昧

自动化实验经常会碰到这些情况：

- API 临时返回空响应；
- 某个 JSON 写了一半；
- 队列跑到一半 session 挂了；
- watchdog 看见任务断了，但状态没记清楚；
- 下次恢复时，不知道应该从头跑，还是接着跑。

如果没有统一的恢复规则，系统就会出现一种最糟糕的状态：

- “看起来还活着”，但其实状态已经不可信；
- “看起来能恢复”，但实际上恢复点不明确；
- “看起来没报错”，但可能悄悄丢了一部分关键上下文。

所以第二条改造线，就是把这些恢复行为规范化。

---

## 2. 这次改造到底在改什么？先看总图

现在你可以把 ARIS 里和实验有关的主链条理解成下面这 4 个阶段：

```text
/experiment-plan
    ↓
/experiment-bridge
    ↓
/experiment-audit
    ↓
/result-to-claim
```

它们分别负责：

### 2.1 `/experiment-plan`
负责把“我想证明什么”写成一个足够明确的实验计划。

不是随便列几个实验，而是要回答：

- 我要证明哪些 claim？
- 每个 claim 需要什么证据？
- 哪些实验块对应哪些 claim？
- 用什么 split？
- 用什么 GT？
- 成功标准是什么？
- 如果没差异，怎么判定“改动没生效”？

它产出的核心文件是：

- `refine-logs/EXPERIMENT_PLAN.md`
- `refine-logs/EXPERIMENT_TRACKER.md`

---

### 2.2 `/experiment-bridge`
负责把计划真正落到“实现 + 部署 + 初步结果”上。

它的核心职责不是“瞎写代码然后开跑”，而是：

- 解析计划；
- 确认实现是否符合计划；
- 先做 sanity；
- 看关键差异是否真的出现；
- 然后再决定要不要大规模跑。

如果执行过程中和计划不一致，还必须把偏差写到：

- `refine-logs/IMPLEMENTATION_DEVIATIONS.json`

这个文件非常关键，后面我会详细解释。

---

### 2.3 `/experiment-audit`
负责独立审计。

它的工作不是“帮你润色结果”，而是专门找这些问题：

- GT 是不是真 GT？
- 指标有没有作弊性归一化？
- 结果文件是不是真的存在？
- 代码里的指标函数是不是真的被调用了？
- 计划里的 split / spec / baseline / seed 有没有被偷偷改掉？
- 关键改动到底有没有真正影响系统行为？
- 证据链能不能追溯到具体文件？

它会产出：

- `EXPERIMENT_AUDIT.md`
- `EXPERIMENT_AUDIT.json`

---

### 2.4 `/result-to-claim`
负责最后一道门：

> “这些结果，究竟能支持什么说法？不能支持什么说法？”

它不会再盲信“有数字就能写 claim”，而是要结合：

- 计划期的 claim map；
- 实际执行结果；
- 审计结果；
- implementation deviations；
- delta assertion 状态；
- recovery warning（如果有）。

所以它的作用，本质上是把：

- **实验完成**

变成：

- **结论是否成立**

这两者中间，差别非常大。

---

## 3. 第一条主线：实验链条加固（这是本轮最核心的部分）

这一部分解决的是：

> “从计划到最后 claim，中间不能靠默认脑补，必须靠显式契约和工件对账。”

---

## 3.1 新增了统一的“实验契约词汇”

涉及文件：

- `skills/shared-references/integration-contract.md`

这个文件的作用，简单说就是：

> 给整个实验链条规定一套统一语言，避免每个 skill 各说各话。

现在统一强调的核心术语有 6 个：

1. **Expectation Declaration**
2. **Execution Spec**
3. **Data Flow Summary**
4. **Delta Assertion**
5. **Evidence Mapping**
6. **Implementation Deviations**

下面我用人话解释一下。

### 1）Expectation Declaration
意思是：

> 这个实验在什么前提下才算“有意义”。

例如：

- 必须用哪个 split；
- GT 到底来自哪里；
- 哪些 baseline 必须可用；
- 如果某个前提不满足，什么时候应该停。

如果这个东西不写清楚，后面就很容易出现“跑是跑了，但这个跑法根本不满足原本研究假设”的情况。

---

### 2）Execution Spec
意思是：

> 到底要跑什么。

包括：

- 哪些 block；
- 哪些 variant；
- 哪些 metrics；
- 哪些 seeds；
- 哪些关键超参；
- 哪些实现约束不能改。

以前很多系统的问题是：

- 计划里说一套；
- 实际实现时模糊处理；
- 后面 review 又按计划理解。

现在就是要尽量堵住这个口子。

---

### 3）Data Flow Summary
意思是：

> 数据是怎么流动的。

包括：

- 输入从哪来；
- 如何预处理；
- 走哪条模型路径；
- 输出是什么；
- 最终保存成哪些文件；
- ground truth 是在哪一步接进来的。

这对发现这些问题非常重要：

- 用错 split；
- 用错标签；
- GT 来路不对；
- 新模块是死路径。

---

### 4）Delta Assertion
意思是：

> 新方法相对于对照组，理论上应该出现什么“具体差异”。

注意，这不是泛泛说“希望指标提升”，而是尽量具体：

- 输出应该变什么；
- 哪个中间量应该变；
- 如果完全没变化，怎么快速判断这是“没真正生效”。

这是这轮改造非常关键的思想。

---

### 5）Evidence Mapping
意思是：

> 每个 claim 到底由哪些 block 和哪些结果文件支撑。

这可以防止后面出现：

- 说了一个 claim；
- 但找不到具体哪份实验文件在支撑它。

也就是说，claim 不再只是“语言上像成立”，而是必须能落到具体工件上。

---

### 6）Implementation Deviations
意思是：

> 如果实际实现或执行偏离了计划，要留下正式偏差回执。

这就是新引入的关键 sidecar：

- `refine-logs/IMPLEMENTATION_DEVIATIONS.json`

这个文件是本轮非常核心的成果之一。

---

## 3.2 `EXPERIMENT_PLAN_TEMPLATE.md` 被补强了

涉及文件：

- `templates/EXPERIMENT_PLAN_TEMPLATE.md`
- `skills/experiment-plan/SKILL.md`

你可以把它理解成：

> 以前实验计划更像“研究备忘录”；现在更像“可以被下游执行、审计、claim gate 消费的合同”。

### 现在计划模板里，明确出现了这些章节：

- `Claim Map`
- `Paper Storyline`
- `Expectation Declaration`
- `Execution Spec`
- `Data Flow Summary`
- `Delta Assertion`
- `Evidence Mapping`
- `Implementation Deviation Protocol`
- `Run Order and Milestones`
- `Compute and Data Budget`
- `Risks and Mitigations`
- `Final Checklist`

这意味着什么？

以前你写计划，更多是在想：

- 我要跑哪些实验？

现在你还必须额外讲清楚：

- 这个实验为什么存在；
- 它想证明哪个 claim；
- 用什么证据来证明；
- 如果计划后面变了，偏差怎么记录；
- 如果结果没有体现预期差异，应该怎么判定失败。

### 这对于非程序员也很重要

因为这类模板的价值，不只是让程序更懂，而是让“人类以后回来审查时”也更容易看懂：

- 原计划是什么；
- 为什么这么设计；
- 后面偏离了没有；
- 如果偏离了，偏到什么程度。

也就是说，它是在帮你补“研究记账本”。

---

## 3.3 `experiment-bridge` 现在不只是“把计划变成代码”

涉及文件：

- `skills/experiment-bridge/SKILL.md`

这是整个链条里最像“施工队”的一个 skill。

以前它更偏向：

- 读计划；
- 写代码；
- 部署；
- 收结果。

现在它被加上了更强的“合规检查”职责。

### 新强化的点有几个：

#### 1）它必须显式读取计划中的关键契约部分

也就是：

- Expectation Declaration
- Execution Spec
- Data Flow Summary
- Delta Assertion
- Evidence Mapping

这很重要，因为这等于在桥接阶段就提前说：

> 后面审计和 claim gate 会检查这些，所以实现阶段不能装作没看见。

---

#### 2）它必须做实现一致性自查

也就是说，在真正部署前，它要问：

- 超参是不是按计划暴露出来了？
- split 和 GT 是否按计划一致？
- block-level variants / metrics / seeds 是否保留？
- data flow 是不是按声明的路径在走？
- delta assertion 代表的差异，是不是真的有机会出现？
- evidence mapping 里预期的结果文件，最后会不会真的写出来？

这一步的意义是：

> 在花 GPU 钱之前，先检查“实验结构上是否还是你原本要的实验”。

---

#### 3）新增 `IMPLEMENTATION_DEVIATIONS.json`

这是最关键的变化之一。

如果执行时偏离计划，就不能再只是“脑子里知道”或者“日志里顺手提一句”，而是要写一个正式 sidecar。

这个 sidecar 至少要记录：

- `plan_reference`：偏离的是计划里的哪个地方
- `deviation_type`：偏差类型（split / metric / baseline / variant / seed / hyperparameter / implementation_constraint / artifact / other）
- `planned_value`：原计划值
- `actual_value`：实际值
- `reason`：为什么偏了
- `claim_impact`：对 claim 的影响程度
- `artifact_impact`：会影响哪些结果文件/工件
- `status`：planned / accepted / unresolved
- `owner`：谁记录的
- `timestamp`：什么时候记录的

### 为什么这东西这么重要？

因为以前很多“研究自动化翻车”，不是因为系统完全不会跑，而是因为：

- 计划悄悄缩水了；
- 后面又没人承认这个缩水对结论的影响。

现在这个 sidecar 的作用就是：

> 只要偏了，就留下机器可读的正式收据。

后面的 audit 和 claim gate 就不能再装看不见。

---

#### 4）sanity check 现在增加了“差异必须可观察”

以前 sanity 更多是在看：

- 程序能不能跑通；
- 有没有崩；
- 显存够不够；
- 输出格式对不对。

现在多了一层：

- 关键改动有没有真的让系统行为发生差异？

如果实验组和对照组：

- 输出完全一样；
- 指标完全一样；
- 中间激活完全没变化；
- 或者关键路径明显没接上；

那就不应该继续大规模部署。

这相当于在大规模烧资源前，先做“活性检测”。

---

## 3.4 `experiment-audit` 现在更像真正的“科研审计”了

涉及文件：

- `skills/experiment-audit/SKILL.md`
- `skills/shared-references/experiment-integrity.md`
- `skills/shared-references/reviewer-independence.md`

这部分原来就有，但这次被显著强化。

### 它现在不仅查传统问题，还查 4 类新增关键问题：

1. **Split Correctness**
   - 原计划 intended split 是什么？
   - 实际代码和结果用的 split 是什么？
   - 有没有 silent fallback 或 leakage？

2. **Implementation Conformance**
   - 计划里的 variants / baselines / seeds / metrics 是否真的跑了？
   - 关键实现约束是否被偷偷改掉？
   - `IMPLEMENTATION_DEVIATIONS.json` 是否诚实、完整、与代码结果一致？
   - 如果 sidecar 说“没有偏差”，代码是否真的支持这个说法？

3. **Delta Assertion / Core Modification Effect**
   - 核心改动有没有带来可观察的具体差异？
   - 如果没差异，这个改动是不是其实不在关键路径上？

4. **Evidence Mapping Traceability**
   - claim 能不能追溯到明确的 block 和结果文件？
   - 这些文件是不是足以支撑当前 claim 强度？

### 它仍然保留传统审计问题

比如：

- fake ground truth
- score normalization fraud
- phantom results
- insufficient scope
- dead code detection

这意味着：

> 现在 audit 不只是“查有没有明显造假式错误”，还开始查“你是不是其实没有真的验证原计划”。

这是一种更细、更接近真实科研审稿逻辑的升级。

---

## 3.5 `result-to-claim` 现在变成真正的“结论闸门”

涉及文件：

- `skills/result-to-claim/SKILL.md`

这是本轮我非常看重的一块。

### 它现在会主动消费这些输入：

1. `EXPERIMENT_PLAN.md`
2. `IMPLEMENTATION_DEVIATIONS.json`
3. 运行结果（如 W&B、日志、JSON/CSV）
4. `EXPERIMENT_LOG.md`
5. `EXPERIMENT_TRACKER.md`
6. `EXPERIMENT_AUDIT.json`（如果存在）
7. 其他 proposal / contract 文档

### 这意味着什么？

以前更像：

- “拿到几个数字，判断支持/不支持。”

现在更像：

- “这些数字是在什么计划前提下得到的？”
- “执行过程中有没有偏差？”
- “审计是否发现证据链断裂？”
- “delta assertion 是否真的满足？”
- “如果恢复过程里有重要 warning，这会不会影响信心？”

### 新逻辑里最关键的两个收口规则

#### 规则 1：如果 implementation deviation unresolved，或者 `breaks_claim_test`
那么默认不能再把受影响 claim 当作被支持。

也就是说：

- 只要偏差严重到破坏 claim 测试；
- 或者偏差尚未解决；
- 那最终 verdict 就必须收紧，甚至判 unsupported。

---

#### 规则 2：如果 deviation 只是 `narrow_scope` 或 `weakens_evidence`
那就必须明确缩小 claim 说法，或者明确指出缺失证据。

这非常符合真实科研写作：

- 不是所有偏差都等于全盘失败；
- 但很多偏差确实意味着你不能再说得那么大。

### 它还要求写“claim verdict artifact”

也就是最终不只是口头上说“partial/yes/no”，而是要把结论作为正式工件写下来，至少包括：

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
- integrity_status

这一步很关键，因为它把“科研结论”也变成了一个可追踪、可回放的工件。

---

## 4. 第二条主线：恢复/可靠性加固

这一部分解决的是：

> “自动化系统不是每次都完美运行，所以必须把出错、重试、恢复这些行为变成显式规则。”

---

## 4.1 新增 `recovery-state-contract.md`

涉及文件：

- `skills/shared-references/recovery-state-contract.md`

这是本轮新加的共享参考文档之一。

你可以把它理解成：

> 给所有“长时间运行、容易被外部环境打断”的环节，规定一个统一恢复语言。

它强调的是：

- markdown 继续做人类可读记录；
- JSON sidecar 负责机器可读的恢复状态；
- 不搞大而全的新框架；
- 只补最必要的“恢复收据”。

### 它规定了最小恢复状态应该长什么样

推荐字段包括：

- `run_id`
- `stage`
- `status`
- `attempt`
- `last_successful_step`
- `resume_cursor`
- `error_class`
- `backoff_until`
- `artifact_refs`
- `updated_at`

你不用把这些字段背下来，只需要知道它们在解决什么：

> 下次系统恢复时，不能靠猜，要知道“我是哪个 run、现在在哪个阶段、之前成功到哪一步、为什么停、什么时候才能重试、哪些工件还可信”。

这就是恢复系统的“病历卡”。

---

## 4.2 对失败进行了统一分类

这个也很关键。

以前系统里很容易出现这种情况：

- 出了错；
- 但没有统一类别；
- 最后所有错误都被混在一起对待。

现在 recovery contract 里把错误分成了几类：

- `transient_network`
- `retryable_http`
- `retryable_parse`
- `validation_error`
- `environment_error`
- `logic_error`
- `unknown`

### 这个分类的意义是什么？

因为不同错误应该有不同处理策略：

#### 可以重试的
比如：

- 网络暂时断；
- 上游服务短暂异常；
- 返回空 JSON 但状态类允许重试。

这类应该：

- 限次重试；
- 指数退避；
- 记录 backoff；
- 从合适 checkpoint 继续。

#### 不该傻重试的
比如：

- 配置错了；
- 输入路径错了；
- 环境缺依赖；
- 代码逻辑本身有 bug。

这类如果还疯狂重试，只会：

- 浪费时间；
- 把状态越搞越乱；
- 误导人以为系统“还在努力工作”。

所以 contract 里要求：

> 该 fail fast 的，就尽快 fail fast。

---

## 4.3 `queue_manager.py` 被进一步对齐到恢复契约

涉及文件：

- `tools/experiment_queue/queue_manager.py`
- `tests/test_queue_manager_state.py`

你可以把 queue manager 理解为：

> 大批量实验的调度器和现场总控。

它现在的重要改进点包括：

### 1）状态文件是正式恢复收据

它的 `queue_state.json` 被明确当作：

- 调度器当前状态的 canonical receipt
- 恢复时的关键依据

这意味着：

- phase 到哪了；
- job 哪些完成了；
- 哪些在跑；
- 依赖链怎样；
- 重启后怎么恢复；

这些信息不能只藏在终端输出里，而要落盘。

---

### 2）原子写入（atomic write）

这个词听起来技术味重，但你可以把它理解成：

> “要么整份文件写成功，要么保持旧文件，不允许写到一半就留下半残文件。”

为什么这很重要？

因为状态文件最怕这种情况：

- 程序写到一半崩了；
- 结果 JSON 只写了一半；
- 下次读的时候，系统根本不知道这份文件是真是假。

现在相关代码采用了“先写临时文件，再替换正式文件”的模式，来减少这种风险。

---

### 3）默认状态形状更清晰

测试里现在明确检查：

- `meta.project`
- `meta.manifest_path`
- `meta.started`
- `phases`
- `jobs`

也就是说，系统恢复时不应该拿到一份模糊状态，而应该拿到一份结构明确、至少包含关键恢复信息的状态对象。

---

## 4.4 `watchdog.py` 的持久化语义更清楚了

涉及文件：

- `tools/watchdog.py`
- `tests/test_recovery_hardening.py`

watchdog 你可以理解为：

> 长任务的看门狗 / 观察员。

它负责记录：

- 注册了哪些任务；
- 每个任务当前状态怎样；
- 是否出现异常或告警。

### 本轮重点不是大改功能，而是强化“它产出的状态本身就是恢复收据”

关键持久化工件包括：

- `tasks.json`
- `status/*.json`
- `alerts.log`

### 为什么这重要？

因为如果任务挂了，你不能只靠“我记得刚才屏幕上好像还在跑”这种人脑记忆。

需要让另一个进程、另一个 session、或者未来的你，一看这些文件就知道：

- 哪个任务注册过；
- 什么时候注册；
- 当前状态是什么；
- 是否已经 stalled / dead / alert。

### 测试现在还专门检查了：

- `write_status()` 会原子写 JSON；
- 不会留下临时残片文件；
- `register_task()` 会写入 `tasks.json`；
- 并且带上 `registered_at`。

这让“任务存在过、何时存在、状态是否可靠”变得更有根据。

---

## 4.5 `semantic_scholar_fetch.py` 的重试逻辑被加固了

涉及文件：

- `tools/semantic_scholar_fetch.py`
- `tests/test_recovery_hardening.py`

这个工具不是实验主链里最核心的一环，但它很适合做恢复策略的样板。

### 本轮主要加固的是：

- 对可重试 HTTP 状态做重试；
- 对“HTTP 200 但 body 为空 / JSON 坏掉”这种坑做有限重试；
- 使用指数退避；
- 超过预算后要明确失败，而不是无限重试。

### 这解决了什么现实问题？

实际 API 世界里很常见这种恶心情况：

- 状态码 200；
- 但内容是空字符串；
- 或者内容根本不是完整 JSON；
- 如果你天真地把“200 = 成功”写死，系统就会直接崩或者误判。

现在相当于承认了一点：

> 上游世界并不总是体面，所以恢复逻辑也要现实一点。

### 新增测试保护的行为包括：

- 第一次拿到空 200 响应，第二次成功时，系统应能恢复；
- 超过重试预算时，要抛出明确错误；
- `URLError` 这种网络错误，应该走 network error 路径，不是静默吞掉。

---

## 5. 测试层面现在保护了什么？

这一块你很关心，因为“写了文档”和“真的被回归测试兜住”不是一回事。

当前本轮能明确确认的测试保护，主要是 **有针对性的回归测试**，不是全链路集成测试。

这一点我要明确说清楚。

---

## 5.1 `tests/test_recovery_hardening.py`

这个文件现在重点保护两大类行为：

### A. Semantic Scholar fetch 的恢复行为

保护点包括：

- 空 200 响应后重试并最终成功；
- 指数退避延迟逻辑；
- 重试预算耗尽后明确报错；
- 网络错误时走正确异常路径。

这类测试的意义是：

> 防止以后有人改代码时，把这些“看似小但很容易让自动流程变脆”的恢复行为又改坏了。

---

### B. watchdog 的持久化行为

保护点包括：

- 状态 JSON 原子写入；
- 不留临时文件残渣；
- `tasks.json` 正确写入；
- 注册任务时包含 `registered_at`。

这类测试的意义是：

> 防止任务状态文件变成“看起来有文件、实际上不可信”。

---

## 5.2 `tests/test_queue_manager_state.py`

这个文件现在保护：

- `save_state()` 的原子写入；
- `load_state()` 在新状态下能初始化默认结构；
- 已存在状态文件时能正确读取恢复。

特别是初始化默认状态时，现在会更明确检查：

- project 名称；
- manifest 路径；
- started 时间戳；
- phases 默认状态；
- jobs 空列表。

这意味着：

> 队列恢复时至少有一个更稳定的“底盘结构”。

---

## 5.3 `tests/test_build_manifest_state.py`

这个文件不是本轮最核心焦点，但它也很重要，因为它保护了：

- manifest JSON 的原子写入；
- grid expansion 是否按预期展开；
- `expected_output` 是否被正确推导。

你可以把它理解成：

> 在实验调度系统里，除了状态本身，任务清单的生成也不能太脆。

---

## 5.4 现在测试还没覆盖什么？

这部分我必须实话实说。

### 目前还没有从现有证据里看到的强覆盖包括：

1. **完整的端到端实验链集成测试**
   - 也就是从计划 → bridge → audit → result-to-claim 一整条链一起验证。

2. **watchdog + queue manager 联动恢复测试**
   - 目前更多是各自单元/回归层面的保护。

3. **真正注入崩溃/中断场景的强恢复测试**
   - 比如写文件写到一半、强行 kill、重启恢复这种更真实的灾难演练。

4. **并发写入冲突场景**
   - 当前看的是原子写模式，但不是并发冲突完整仿真。

5. **更强的 claim gate 端到端回放测试**
   - 例如自动验证“当 deviation = breaks_claim_test 时，最终 claim 必须被压下来”。

所以你现在要把测试状态理解为：

> 关键薄弱点已经开始被补上，但离“整个系统已经被全链路证明非常稳”还差一步。

---

## 6. `MANIFEST.md` 现在扮演什么角色？

涉及文件：

- `MANIFEST.md`
- `skills/shared-references/output-manifest.md`
- `skills/shared-references/output-versioning.md`

这部分很容易被低估，但其实很关键。

### 简单说，`MANIFEST.md` 就是全项目的“工件流水账”

它会记录：

- 什么时候；
- 哪个 skill；
- 写了哪个文件；
- 属于哪个 stage；
- 这份文件是干什么的。

### 这次我进一步强化了它的要求

现在它不只是“记一下写了什么”，还强调：

- run artifacts 要说明对应哪个 milestone / run IDs / variants；
- audit artifacts 要说明审的是哪一套 plan/results；
- claim artifacts 要说明在解释哪次实验或哪份审计；
- 如果 drift 或 recovery receipt 会影响下游信任，也要在描述里体现。

### 为什么这重要？

因为后面你最怕看到这种场景：

- 文件很多；
- 名字都差不多；
- 不知道哪份是最新版；
- 也不知道哪份是支撑哪个 claim 的。

`MANIFEST.md` 的作用就是尽量让这个问题变轻。

它不是万能的，但它能把“工件溯源”做得比以前清楚很多。

---

## 7. 这轮具体做了哪些“可落地”的改动？

我按“你醒来后最关心”的方式给你归纳成 done / improved / not yet 三类。

---

## 7.1 已经做完的（Done）

### A. 实验链条契约已经统一到一套核心语言上

已完成：

- `Expectation Declaration`
- `Execution Spec`
- `Data Flow Summary`
- `Delta Assertion`
- `Evidence Mapping`
- `Implementation Deviations`

这些概念现在已经不只是讨论文档里的想法，而是已经进入：

- shared references
- plan template
- experiment-plan
- experiment-bridge
- experiment-audit
- result-to-claim

---

### B. `IMPLEMENTATION_DEVIATIONS.json` 已经被确立为正式 load-bearing artifact

也就是说，它不是“随便写个注释”的级别，而是：

- bridge 要写；
- audit 要检查；
- result-to-claim 要消费；
- versioning 要保留历史；
- manifest 要能追踪。

这是本轮非常关键的一个成果。

---

### C. `experiment-audit` 的检查面已经明显变广

现在它不只查传统 integrity 问题，还会查：

- split correctness
- implementation conformance
- delta assertion
- evidence mapping
- deviation sidecar 诚实性

这让“计划是否真的被验证”第一次开始被系统化检查。

---

### D. `result-to-claim` 已经开始真正收口 claim 范围

特别是：

- unresolved deviation
- `breaks_claim_test`
- `narrow_scope`
- `weakens_evidence`

这些状态现在都会影响最终 claim verdict。

这会显著减少“结果数字看起来不错，于是 claim 说大了”的风险。

---

### E. 恢复状态契约已经建立

`recovery-state-contract.md` 已经存在，明确规定了：

- 什么时候需要 recovery contract；
- 状态字段最小集；
- 错误分类；
- 重试策略；
- checkpoint seam；
- 写入规则；
- 与 experiment-chain artifact 的关系。

---

### F. queue/watchdog/fetch 的关键恢复点已有文档和测试支撑

包括：

- atomic writes
- retry classification
- retry budget exhaustion
- resumability metadata
- task registration receipts

这意味着恢复逻辑已经开始从“经验主义”变成“有最小制度保障”。

---

## 7.2 已经明显改善，但还没完全闭环的（Improved, but not fully solved）

### A. 合同/文档层已经更清晰，但真正端到端自动执行还需要进一步验证

现在文档和 skill 逻辑已经更一致了，但这不自动等于：

- 所有真实项目一跑就完全稳定；
- 所有边界情况都已被证伪。

换句话说：

> 契约已经更清楚了，但“这套契约在各种真实项目中都能稳健跑起来”还需要更多实战回放。

---

### B. 恢复能力现在是“重点薄弱点已加固”，不是“全系统灾备级成熟”

现状更像：

- 关键状态文件写入更安全；
- 关键重试路径更明确；
- 关键错误类型不再混成一团；

但还不是：

- 任意崩溃都能优雅恢复；
- 任意多组件联动都能自动无损续跑。

---

### C. claim gate 更谨慎了，但还需要更多自动化回放来证明“所有收口规则都真的触发正确”

现在逻辑层已经比以前强很多，但还缺更强的整链验证去证明：

- 某类 drift 出现时；
- 审计发现某类 warning/fail；
- 最终 claim 是否总是按预期收紧。

---

## 7.3 还没真正完成的（Not started yet / still remaining）

### A. 一条完整的端到端演练

这是我认为后面最值得补的一步。

也就是：

- 造一个小而真实的 sample experiment chain；
- 从 `EXPERIMENT_PLAN.md` 开始；
- 走过 bridge；
- 产出 deviation / result；
- 走 audit；
- 再走 result-to-claim；
- 注入几个典型 failure / drift 场景；
- 看最后 claim 是否真的被正确收紧。

这会比单看文档和单元测试更能说明系统是不是真的“通了”。

---

### B. 更强的恢复演练

例如：

- 中途 kill queue；
- 状态写一半；
- watchdog 检测 dead/stalled 后恢复；
- 重新启动后验证是否从正确阶段继续。

这类测试比普通单测更像真正线上事故演练。

---

### C. 其他相关 skill 的进一步对齐

我已经做了一次 focused consistency sweep，把最核心的 experiment-chain/recovery references 再补了一轮。

但从系统工程角度说，未来仍可能需要继续检查这些外围 skill：

- 是否有别的 caller 文档仍在用旧说法；
- 是否还有某些地方默认把“没有 sidecar”当成“没问题”；
- 是否还有地方没有把 drift / recovery context 继续向下传递。

这类工作现在不是最紧急，但后面仍值得继续扫。

---

## 8. 用“前后对比”帮你更直观看懂这轮改造

这一节我用几个具体场景来说明。

---

### 场景 1：计划里要跑 test split，结果实现时换成 val split

#### 以前

- 可能只是代码里改了；
- 或者实现时默认 fallback 了；
- 后面没有正式记录；
- audit 也未必系统检查；
- 最后 claim 可能还按“test split 结论”来写。

#### 现在

- plan 里会明确写 intended split；
- bridge 要检查 execution spec 是否一致；
- 如果偏了，要写 `IMPLEMENTATION_DEVIATIONS.json`；
- audit 要核对 split correctness；
- result-to-claim 必须根据偏差影响缩小 claim 或判 unsupported。

### 这带来的本质变化

> 从“默认你没偏”变成“只要偏了，就留下正式证据并影响后续结论”。

---

### 场景 2：你加的新模块根本没接进关键路径

#### 以前

- 程序照样能跑；
- 输出照样能写；
- 甚至指标还会有随机波动；
- 但这个实验本质上没在测试你的新改动。

#### 现在

- plan 要写 Delta Assertion；
- bridge 的 sanity 要检查改动是否真的造成可观察差异；
- audit 还会检查 core modification effect；
- 如果没差异却还在大谈方法有效，audit 会 fail / warn；
- result-to-claim 会把这种情况压下来。

### 本质变化

> 从“能跑就算活”变成“必须证明关键改动真的活着”。

---

### 场景 3：API 返回 HTTP 200，但 body 是空的

#### 以前

- 很可能直接 JSON decode 崩掉；
- 或者被当成正常成功处理，留下坏状态；
- 后面恢复时逻辑混乱。

#### 现在

- fetch 层会把它识别为可重试 parse 类失败；
- 按预算和退避策略重试；
- 成功则继续；
- 超预算则明确报错；
- 相关行为已经有 targeted regression tests 保护。

### 本质变化

> 从“200 就盲信”变成“200 也要对内容质量保持怀疑”。

---

### 场景 4：任务跑到一半 session 挂了

#### 以前

- 你可能只知道“刚才还在跑”；
- 不确定队列状态是否完整；
- 不确定 tasks/status 是否可信；
- 恢复时很容易从头再来或重复跑。

#### 现在

- queue manager 的状态更明确；
- watchdog 的持久化收据更明确；
- recovery contract 也规定了 stage / attempt / backoff / artifact_refs 这类概念；
- 至少系统已经开始朝“可恢复”而不是“靠记忆恢复”走。

### 本质变化

> 从“出事后靠人回忆现场”变成“出事后尽量看状态收据恢复”。

---

## 9. 如果你现在要自己读这个仓库，优先看哪些文件？

这里我按“看什么问题，就读什么文件”给你一个导航。

### 9.1 如果你想看“实验计划应该怎么写”
先看：

- `templates/EXPERIMENT_PLAN_TEMPLATE.md`
- `skills/experiment-plan/SKILL.md`

看这两个，你会明白：

- 计划不再只是列实验；
- 它已经变成带 claim / spec / delta / evidence 的正式输入工件。

---

### 9.2 如果你想看“计划如何变成实际执行”
看：

- `skills/experiment-bridge/SKILL.md`

重点看：

- 计划解析
- 实现一致性自查
- deviation sidecar 规则
- sanity / delta assertion
- deploy / collect flow

---

### 9.3 如果你想看“系统怎么防止自欺欺人”
看：

- `skills/experiment-audit/SKILL.md`
- `skills/shared-references/experiment-integrity.md`
- `skills/shared-references/reviewer-independence.md`

这几份会帮你理解：

- 为什么 executor 不能自己判断自己实验诚不诚实；
- 为什么必须有独立 reviewer；
- 为什么 split / GT / traceability / scope 都要被查。

---

### 9.4 如果你想看“最终 claim 是怎么被收口的”
看：

- `skills/result-to-claim/SKILL.md`

重点看：

- 它读哪些输入；
- 什么情况会把 claim 判成 partial / no；
- deviation / audit / delta / recovery warning 怎么影响结论。

---

### 9.5 如果你想看“系统怎么记账、怎么追踪工件”
看：

- `MANIFEST.md`
- `skills/shared-references/output-manifest.md`
- `skills/shared-references/output-versioning.md`

---

### 9.6 如果你想看“长任务失败后怎么恢复”
看：

- `skills/shared-references/recovery-state-contract.md`
- `tools/experiment_queue/queue_manager.py`
- `tools/watchdog.py`
- `tools/semantic_scholar_fetch.py`
- `tests/test_recovery_hardening.py`
- `tests/test_queue_manager_state.py`

---

## 10. 现在这轮改造，对你来说最大的实际收益是什么？

如果从“你以后真的要继续用这个系统做研究”来讲，我觉得收益主要有 5 个。

### 收益 1：更难出现“跑了半天，最后不知道这些结果在证明什么”
因为现在 claim、block、evidence、result file 之间的映射更明确了。

---

### 收益 2：更难出现“计划和实际偷偷偏了，但没人知道”
因为现在 drift 已经被正式收据化。

---

### 收益 3：更难出现“关键改动没生效，系统却还继续烧 GPU”
因为 delta assertion 和 sanity gate 被提升了。

---

### 收益 4：更难出现“出了问题只能靠回忆恢复现场”
因为恢复状态、任务状态、队列状态都更明确了。

---

### 收益 5：以后你回头看项目时，会更容易知道“哪个文件在扮演什么角色”
因为现在 shared references、manifest、versioning、plan template 之间的职责边界比以前清楚得多。

---

## 11. 我对当前状态的实话判断

如果你问我：

> “现在这个系统已经完全变成可靠科研自动化了吗？”

我的诚实回答是：**还没有。**

但如果你问：

> “和之前相比，现在是不是已经明显朝‘不容易自欺欺人、不容易无痕漂移、不容易状态混乱’的方向前进了一大步？”

我的回答是：**是，已经前进了一大步。**

更具体地说：

### 现在最强的进展在于

- 契约更明确；
- 偏差更可追踪；
- 审计更像真正审计；
- claim gate 更会收口；
- 恢复状态更制度化；
- 一些关键薄弱点已经有针对性测试保护。

### 现在最大的剩余短板在于

- 还缺更强的端到端实战演练；
- 还缺更完整的跨组件恢复验证；
- 还缺更系统的“在坏场景下注入故障，看最终 claim 是否正确收紧”的全链路验证。

所以最准确的定位应该是：

> **我们已经把系统从“容易机械成功但科研失真”的状态，推进到了“结构上更诚实、更可审计、更可恢复”的状态；但还需要一轮更强的端到端验证，才能真正证明这套改造在实战里闭环。**

---

## 12. 我建议的下一步

如果你让我从现在继续往下推进，我建议顺序是：

### 第一步：做一条小型端到端演练

目标：

- 用一个小案例，把 plan → bridge → audit → result-to-claim 真正串起来；
- 故意注入 1~2 个偏差/失败；
- 看最后 claim 是否真的被正确压住。

这是最能验证本轮改造是否“从文档落到了行为”的一步。

---

### 第二步：做一轮恢复场景演练

比如：

- 中途 kill queue；
- 模拟坏 JSON / 空响应；
- watchdog 记录异常；
- 然后恢复并检查工件一致性。

---

### 第三步：继续扫外围 skill 的术语漂移

虽然核心链条已经补得比较到位，但外围文档和 skill 仍值得继续清理，确保没有地方还在默默使用旧假设。

---

## 13. 最后给你的极简理解版本

如果你之后只记住 4 句话，我希望是这 4 句：

1. **以前的问题不是“没跑起来”，而是“跑起来也不代表科研上成立”。**
2. **这轮改造最核心的是把计划、实现、审计、claim 之间补成了更明确的证据链。**
3. **`IMPLEMENTATION_DEVIATIONS.json` 和 recovery state 这两类 sidecar，是这轮改造里最关键的新“收据机制”。**
4. **现在系统更诚实、更可追踪了，但还需要一轮端到端演练来证明它真正闭环。**

---

## 14. 本文涉及的关键文件索引

### 主链条
- `templates/EXPERIMENT_PLAN_TEMPLATE.md`
- `skills/experiment-plan/SKILL.md`
- `skills/experiment-bridge/SKILL.md`
- `skills/experiment-audit/SKILL.md`
- `skills/result-to-claim/SKILL.md`

### 共享契约
- `skills/shared-references/integration-contract.md`
- `skills/shared-references/output-versioning.md`
- `skills/shared-references/output-manifest.md`
- `skills/shared-references/recovery-state-contract.md`
- `skills/shared-references/experiment-integrity.md`
- `skills/shared-references/reviewer-independence.md`

### 可靠性 / 恢复
- `tools/experiment_queue/queue_manager.py`
- `tools/watchdog.py`
- `tools/semantic_scholar_fetch.py`

### 测试
- `tests/test_recovery_hardening.py`
- `tests/test_queue_manager_state.py`
- `tests/test_build_manifest_state.py`

### 过程记录
- `MANIFEST.md`
- `discussions/0512过程.txt`
- `discussions/NIGHT_PROGRESS_20260512.md`

---

如果你愿意，下一步我可以继续直接给你做第二份文档：

**《我作为非程序员，应该怎么阅读 ARIS 这一套实验链条》**

那份会更偏“读仓库导航图 + 阅读顺序 + 每个文件怎么看”，比这份更像上手指南。