# 非程序员如何阅读 ARIS 这一套实验链条

> 这份文档是给“不是很会写代码，但想真正看懂 ARIS 这一套研究自动化到底在干什么”的你准备的。
>
> 它不是讲实现细节，而是讲：
>
> - 你应该先看什么、后看什么；
> - 每个关键文件到底在扮演什么角色；
> - 哪些文件是“战略地图”，哪些只是“施工记录”；
> - 哪些地方第一次看可以跳过；
> - 看文件时应该问自己什么问题。

---

# 0. 先建立一个总感觉：ARIS 不是一个脚本，而是一条“研究流水线”

如果你把 ARIS 当成“一个会自动跑实验的脚本”，你会很容易看晕。

更好的理解方式是：

> **ARIS 是一条把“研究想法”一步步变成“最后结论”的流水线。**

它关心的不只是：

- 能不能运行命令；
- 能不能产出文件；

它更关心：

- 这个实验计划是否合理；
- 实际实现有没有偏离计划；
- 跑出来的结果是否可信；
- 最后能不能据此写出一个不过度夸大的 claim。

所以你读 ARIS 时，不要一直问：

- “这段代码在干嘛？”

而应该更多问：

- “这个文件在整条研究链里扮演什么角色？”
- “它是在规定计划？执行实验？审计真实性？还是收口结论？”

这会让你一下子更容易读懂。

---

# 1. 先记住最核心的 4 个阶段

如果你什么都不记，只记住这一条主链就够了：

```text
/experiment-plan
    ↓
/experiment-bridge
    ↓
/experiment-audit
    ↓
/result-to-claim
```

你可以把它翻译成中文：

1. **experiment-plan**：先把“我要证明什么”说清楚。
2. **experiment-bridge**：再把计划真正落到实现和运行上。
3. **experiment-audit**：然后检查这个实验到底诚不诚实、有没有跑偏。
4. **result-to-claim**：最后再判断，这些结果到底支持什么结论。

这 4 个阶段，就是你读 ARIS 时的主线。

**重要建议：以后你读仓库，优先围着这 4 个点转，不要一上来就被一堆工具脚本带跑。**

---

# 2. 最推荐的阅读顺序（非程序员版）

如果你现在准备真正开始看，我建议按下面这个顺序：

## 第一轮：先看“全局理解”

### 1）先看：
- `discussions/ARIS_HARDENING_PROGRESS_REPORT_20260513.md`

为什么先看它？

因为它是我刚写的“总汇报”，相当于先给你一个地图。

它会先帮你理解：

- 这轮改造想解决什么问题；
- 为什么以前会出现“跑通但不可用”；
- 哪些地方已经补强了；
- 还有哪些没彻底做完。

**如果你还没建立全局图，就先别急着钻具体 skill。**

---

### 2）再看：
- `discussions/ARIS_ARCHITECTURE_ANALYSIS.md`
- `discussions/PAIN_POINT_DIAGNOSIS.md`
- `discussions/ARCHITECTURE_EXPLORATION_REPORT.md`

这三份更像：

- 第一份：系统长什么样
- 第二份：原来哪里痛
- 第三份：后来怎么考虑重构方向

你可以把它们理解成：

> “病历 + 病因分析 + 治疗思路”

如果只看当前文件而不看这些背景，你会不知道为什么要改。

---

## 第二轮：看“实验主链”

这时才进入真正最重要的 4 个 skill。

### 3）先看：`templates/EXPERIMENT_PLAN_TEMPLATE.md`

为什么第一个看这个，而不是先看 skill？

因为模板比 skill 更像“输入表格”，更容易懂。

看这个文件时，你不要陷入“每一行怎么写”，而是看：

- 一个实验计划现在被要求写清楚哪些内容？
- 为什么连 split、GT、delta、evidence 都要写？
- 为什么还会有 implementation deviation protocol？

### 你第一次看时重点看这几个标题：

- `Claim Map`
- `Expectation Declaration`
- `Execution Spec`
- `Data Flow Summary`
- `Delta Assertion`
- `Evidence Mapping`
- `Implementation Deviation Protocol`

### 你要问自己的问题：

- 这个模板是在帮我“列实验”，还是在帮我“建立证据链”？

正确答案是后者。

---

### 4）再看：`skills/experiment-plan/SKILL.md`

这个文件是“怎么使用这个模板”的操作说明。

你可以把它理解成：

> “实验计划官的工作手册”

### 看它时要重点理解：

- 为什么实验计划必须 claim-driven（围绕 claim 驱动）
- 为什么每个实验 block 都必须说明存在意义
- 为什么 split / GT source 不能含糊
- 为什么每个 claim 都必须映射到具体结果文件

### 第一次看时哪些可以跳过？

你第一次不需要死盯：

- 所有输出格式细枝末节
- 太长的 markdown 模板重复段
- 一些组合 skill 的说明

你先抓住它的核心思想：

> **计划阶段就要把后面审计和 claim gate 需要的证据结构先埋好。**

---

### 5）接着看：`skills/experiment-bridge/SKILL.md`

这是整条链里最像“施工现场总管”的文件。

它负责把计划变成：

- 实现
- sanity 检查
- 部署
- 收结果

### 你第一次看它时，最值得重点看的不是所有部署细节，而是这 5 类内容：

#### A. 它从计划里读哪些东西
重点找：
- Expectation Declaration
- Execution Spec
- Data Flow Summary
- Delta Assertion
- Evidence Mapping

这说明 bridge 已经不是“随便把计划翻译成命令”，而是在强行继承计划契约。

#### B. 它怎么做一致性自查
重点看它会问：
- split 对不对
- GT 对不对
- variants / metrics / seeds 对不对
- data flow 有没有跑偏
- delta assertion 是否可观察

#### C. 它为什么强调 sanity-first
也就是：
- 不先跑大规模
- 先验证小规模是否有生命迹象

#### D. 它为什么要求写 `IMPLEMENTATION_DEVIATIONS.json`
这是第一次阅读 bridge 时最值得你停下来想的点：

> 如果计划和实现不一致，系统现在不允许你装作没发生。

#### E. 它什么时候会停止继续扩大实验规模
尤其要注意：
- 如果 delta assertion 失败
- 如果关键改动没有产生预期差异
- 就不应该继续烧 GPU

### 第一次看时哪些可以先略过？

- 各种具体 GPU / vast.ai / Modal 细节
- route 到 `/run-experiment` 还是 `/experiment-queue` 的实现层面细节
- 某些工具不可用时的 graceful degradation 描述

先抓“大原则”，再看部署细节。

---

### 6）然后看：`skills/experiment-audit/SKILL.md`

这个文件建议你慢一点看。

因为它实际上是整条链里最像“独立审查员”的部分。

### 读它时，你要先知道一件事：

它不是在“帮实验说好话”，它是在“帮你拆穿实验里不可信的地方”。

### 第一次看重点看这些检查项：

- Ground Truth Provenance
- Score Normalization
- Result File Existence
- Dead Code Detection
- Scope Assessment
- Split Correctness
- Implementation Conformance
- Delta Assertion / Core Modification Effect
- Evidence Mapping Traceability

你不必一开始记住名字，但你要知道它们分别是在问：

- GT 是不是真的来自数据集？
- 分数有没有被做奇怪归一化？
- 结果文件是不是真的存在？
- 指标函数是不是根本没被调用？
- 实验规模够不够支撑你说的话？
- 实际跑的东西是不是仍然是原计划想跑的那个东西？
- 关键改动是不是真的生效？
- claim 到底能不能追溯到具体证据？

### 这里你最该记住的一个思想：

> **“实验跑完” 和 “实验可信” 不是一回事。**

audit 就是专门处理这两者差别的。

### 同时建议搭配看两个共享参考文件：
- `skills/shared-references/experiment-integrity.md`
- `skills/shared-references/reviewer-independence.md`

它们会帮助你明白：

- 为什么不能自己审自己
- 为什么 reviewer 必须独立读文件
- 为什么 fake GT / phantom results / overstated scope 都是严重问题

---

### 7）最后看：`skills/result-to-claim/SKILL.md`

这是主链最后一步，也是最像“裁判”的文件。

它的核心问题不是：

- “这次实验有没有输出结果？”

而是：

- “这些结果，到底允许你说什么？”

### 第一次看时，你重点看这些：

#### A. 它会读取哪些输入
尤其注意它不只读结果，还会读：
- `EXPERIMENT_PLAN.md`
- `IMPLEMENTATION_DEVIATIONS.json`
- `EXPERIMENT_AUDIT.json`
- 各类结果文件

#### B. 它最终产出的不是自由发挥，而是结构化 verdict
例如：
- claim_supported
- confidence
- missing_evidence
- suggested_claim_revision
- delta_assertion_status
- implementation_deviation_impact
- recovery_context_status

#### C. 它对什么特别敏感
比如：
- unresolved deviation
- `breaks_claim_test`
- audit fail
- evidence mapping broken
- delta assertion failed

### 你要从这里理解一个非常重要的研究自动化原则：

> **有数字，不等于有结论；有结论，也不等于能说大结论。**

这个 skill 就是负责把结论收紧的。

---

# 3. 再读一层：共享参考文件是“规则书”

很多非程序员读仓库时会犯一个错误：

- 一直只盯着主 skill；
- 但忽略了 shared-references。

其实 shared-references 很像：

> “裁判规则书 / 术语手册 / 统一行为约定”

它们很重要，因为这些文件决定了：

- 不同 skill 之间如何对齐；
- 什么叫合规；
- 什么叫有效输出；
- 什么叫可恢复；
- 什么叫独立审查。

下面是最推荐读的几个。

---

## 3.1 `skills/shared-references/integration-contract.md`

这是“跨 skill 契约总规则”。

你不用第一次就全看完，但建议看中间讲 experiment-chain vocabulary 的部分。

### 你要重点理解：

系统现在希望跨 skill 共享一套小而稳定的词汇，而不是每个 skill 发明自己的说法。

其中最重要的就是这 6 个词：

- Expectation
- Execution Spec
- Data Flow
- Delta Assertion
- Evidence Mapping
- Implementation Deviations

### 你可以把它理解成：

> 这份文件在说：“以后不同阶段说话要用同一种语言，才能前后对账。”

---

## 3.2 `skills/shared-references/output-versioning.md`

这份文件是“输出版本管理规则”。

它主要回答：

- 什么时候要写 timestamped 文件
- 什么时候保留 latest copy
- 哪些状态文件如果覆盖了，历史要先保留
- 老项目和新目录结构如何兼容

### 非程序员该怎么读？

你不一定要记规则细节，但你要知道这份文件在解决什么：

> “文件很多时，怎么避免你以后搞不清哪份是最新版、哪份是旧版、哪份是在解释哪一轮结果。”

---

## 3.3 `skills/shared-references/output-manifest.md`

这份文件是“工件记账规则”。

它配合根目录的 `MANIFEST.md` 看。

### 你应该理解成：

- output-versioning = 解决“文件怎么留历史”
- output-manifest = 解决“文件是谁写的、属于哪一阶段、是干什么的”

### 所以它的价值是：

当你以后看到一堆文件时，不至于完全失忆。

---

## 3.4 `skills/shared-references/recovery-state-contract.md`

这是“恢复规则书”。

如果你未来想理解：

- 任务中断后怎么办；
- 状态怎么保存；
- 什么错误该重试；
- 什么错误应该立刻停；

这份文件是你最应该读的共享参考之一。

### 非程序员阅读时建议抓住 4 个问题：

1. 哪些场景需要恢复状态？
2. 一份恢复状态至少应记录什么？
3. 哪些错误可以重试，哪些不能？
4. 恢复时应该从哪一层继续，而不是从头全重跑？

你不用背 JSON 字段，但要知道这些字段是在回答上面 4 个问题。

---

## 3.5 `skills/shared-references/experiment-integrity.md`

这是“实验诚实度底线规则”。

第一次看时你重点看：

- fake ground truth
- score normalization fraud
- phantom results
- insufficient scope
- evaluation types

### 你要把它理解成：

> 这份文件不是在教你怎么把结果写得漂亮，而是在规定哪些做法不能碰。

---

## 3.6 `skills/shared-references/reviewer-independence.md`

这是“为什么 reviewer 不能被 executor 先加工内容再送审”的规则。

这份文件对理解“三边架构”很重要。

### 核心思想就一句：

> reviewer 要看到原始工件，而不是 executor 先嚼过一遍的总结。

如果 reviewer 只看 executor 的转述，那独立审查的意义就大打折扣了。

---

# 4. 工具文件该怎么看？不要一上来就深挖

很多人一进代码仓库就喜欢先看 `tools/`，但如果你不是程序员，我建议反过来。

**先理解主链逻辑，再回头看工具。**

因为工具是“怎么做”，主链是“为什么做”。

下面是你比较值得看的几个工具文件，以及建议读法。

---

## 4.1 `tools/experiment_queue/queue_manager.py`

这份文件负责“大批量实验的排队与调度”。

### 非程序员看它时，不要试图一行行读懂实现。
你应该重点看它在概念上负责什么：

- job / phase 是怎么组织的
- `queue_state.json` 为什么重要
- 为什么要支持 restart-safe
- 为什么要做 OOM retry / stale-screen cleanup / phase dependency

### 你应该问：

- 如果实验很多，它怎么避免乱掉？
- 如果中途挂了，它靠什么恢复？

如果你已经看过 `recovery-state-contract.md`，再回头看它，会更容易理解。

---

## 4.2 `tools/watchdog.py`

这份文件负责“长期观察任务状态”。

### 你不需要先读代码细节。
先理解它在记录什么：

- `tasks.json`
- `status/*.json`
- `alerts.log`

### 你应该把它想成：

> 一个长期任务的“值班记录员”。

它的价值不是帮你计算指标，而是帮助你在任务挂掉、卡住、超时、没响应时，还有痕迹可查。

---

## 4.3 `tools/semantic_scholar_fetch.py`

这份文件比较适合作为“恢复逻辑样板”来看。

### 你第一次看时，只要理解这些问题：

- 它为什么需要 retry？
- 什么叫 retryable parse / retryable http？
- 为什么 200 响应也不一定代表真的成功？

它不一定是整条实验主链里最关键的工具，但它能很好地体现：

> 这套系统正在逐步学会把“现实世界的不稳定”当作常态来处理。

---

# 5. 测试文件怎么读，才不会看成“天书”？

如果你不是程序员，第一次看到 `tests/*.py` 很容易脑袋发紧。

我的建议是：

> **不要先看代码语法，先看测试名和断言在保护什么行为。**

你可以把测试理解成：

- “这类 bug 以后不允许再悄悄回来。”

---

## 5.1 `tests/test_recovery_hardening.py`

这份文件你第一次看，不用管 mock 细节。

你就看测试函数名，理解它们在保护什么：

- 空响应后重试成功
- 退避时间递增
- 超过重试预算会失败
- 网络错误会走正确错误路径
- watchdog 状态写入是原子的
- 注册任务会留下正式记录

### 你可以把这份测试理解成：

> “把最容易让恢复逻辑变脆的地方先钉死。”

---

## 5.2 `tests/test_queue_manager_state.py`

这份主要是在保护：

- 队列状态保存
- 队列状态恢复
- 默认状态结构正确

### 你要理解的是：

如果这些行为没有测试，后面某次改动很可能把恢复底盘弄坏，但表面上看不出来。

---

## 5.3 `tests/test_build_manifest_state.py`

这份可以放在第三优先级看。

它更偏向：

- 调度 manifest 的持久化
- grid expansion
- expected output 推导

### 第一次看不懂也没关系
因为它不是主链理解的第一关键点。

---

# 6. 哪些文件第一次看可以大胆跳过？

这点非常重要，不然你很容易把自己淹死在细节里。

## 第一次阅读时，可以先跳过或略读：

### 1）各种安装脚本
例如：
- `tools/install_aris.sh`
- 其他安装/部署辅助脚本

原因：
它们更多解决“怎么装起来”，不是“这套实验链在干什么”。

---

### 2）各种 provider / GPU 平台细节
例如：
- vast.ai 生命周期说明
- Modal 说明
- 一些具体 command routing

原因：
这些属于运行环境层，不是你理解主链逻辑的第一优先级。

---

### 3）过长的输出格式模板重复块
很多 `SKILL.md` 里会有大段输出格式说明。

第一次看时，你不必逐字读完所有模板文字。

你更应该看的是：

- 它要求输出哪些类型的工件；
- 这些工件为什么存在。

---

### 4）外围组合型 skill
比如某些 paper-writing、review 组合 skill。

它们当然有价值，但如果你的目标是先理解“实验链为什么改成这样”，优先级不如主链 4 个 skill + shared references 高。

---

# 7. 非程序员读每个文件时，最应该问自己的问题

这是我最推荐你养成的阅读方法。

每看一个文件，不要问：

- “这段代码语法是什么意思？”

先问下面这 5 个问题：

## 问题 1：这个文件属于哪个阶段？
是：
- 计划
- 实现/执行
- 审计
- 结论
- 恢复/记账/共享规则

如果阶段都没分清，你会很容易把不同职责混起来。

---

## 问题 2：这个文件产出什么工件？
比如：
- 计划文件
- 跟踪文件
- 偏差 sidecar
- 审计报告
- claim verdict
- recovery state

你要逐步形成一个感觉：

> ARIS 不只是“跑程序”，而是在不停生成一串有角色分工的工件。

---

## 问题 3：这个文件在防止什么失败模式？
例如：

- 防止计划漂移？
- 防止关键改动死路？
- 防止 fake GT？
- 防止 claim 说大？
- 防止中断后状态混乱？

这是比“它写了什么”更重要的问题。

---

## 问题 4：它依赖上游什么信息？
例如：

- bridge 依赖 plan
- audit 依赖 code/result/deviation
- result-to-claim 依赖 audit/result/plan

这能帮助你看懂整条链条的前后关系。

---

## 问题 5：它的输出会影响下游什么判断？
例如：

- deviation sidecar 会影响 audit 和 claim gate
- audit 结果会影响最终 claim 强度
- recovery warning 会影响是否信任当前状态

这会帮助你理解为什么有些文件虽然不是“主结果文件”，却很重要。

---

# 8. 一个真正适合你的阅读顺序（极简 90 分钟版）

如果你只想用一两个小时，快速建立感知，我建议这样读：

## 第 1 步（15 分钟）
看：
- `discussions/ARIS_HARDENING_PROGRESS_REPORT_20260513.md`

目标：
- 建立全局问题意识

---

## 第 2 步（15 分钟）
看：
- `templates/EXPERIMENT_PLAN_TEMPLATE.md`

目标：
- 看懂一份“合格实验计划”现在被要求写什么

---

## 第 3 步（20 分钟）
看：
- `skills/experiment-bridge/SKILL.md`

目标：
- 看懂系统是怎么把计划变成执行的
- 重点关注 deviation 和 sanity/delta

---

## 第 4 步（20 分钟）
看：
- `skills/experiment-audit/SKILL.md`
- `skills/shared-references/experiment-integrity.md`

目标：
- 看懂系统怎么查实验有没有“自欺欺人”

---

## 第 5 步（20 分钟）
看：
- `skills/result-to-claim/SKILL.md`

目标：
- 看懂系统怎么把结果收缩成可信 claim

这 90 分钟读完，你对主链会有非常明显的理解提升。

---

# 9. 如果你之后愿意继续深入，第二层阅读顺序

在第一轮看完后，再补这些：

## 第二层建议读：
- `skills/shared-references/integration-contract.md`
- `skills/shared-references/output-versioning.md`
- `skills/shared-references/output-manifest.md`
- `skills/shared-references/recovery-state-contract.md`
- `tools/experiment_queue/queue_manager.py`
- `tools/watchdog.py`
- `tests/test_recovery_hardening.py`
- `tests/test_queue_manager_state.py`

第二层阅读的目标不再是“看懂主链是什么”，而是：

- 看懂主链靠什么规则维持一致；
- 看懂系统怎么记账；
- 看懂中断恢复怎么设计；
- 看懂哪些关键薄弱点已经被测试兜住。

---

# 10. 你读懂 ARIS 的标志是什么？

最后，我给你一个非常实用的判断标准。

如果你读完之后，已经能用自己的话回答下面这些问题，就说明你已经不只是“看过文件”，而是真的开始看懂了：

1. `experiment-plan` 为什么不能只是列实验，而必须写 claim / spec / delta / evidence？
2. `experiment-bridge` 为什么必须在偏离计划时写 `IMPLEMENTATION_DEVIATIONS.json`？
3. `experiment-audit` 为什么不能由 executor 自己完成？
4. `result-to-claim` 为什么不能只看数字，还要看 audit / deviation / delta / recovery context？
5. `recovery-state-contract` 为什么重要？它是在解决什么现实问题？
6. `MANIFEST.md` 为什么不是可有可无的日志，而是工件追踪账本？

如果这 6 个问题你已经能回答得八九不离十，那说明你已经掌握了这套系统最关键的骨架。

---

# 11. 最后给你的超短版导航

如果以后你又忘了，我建议你只记这一版：

## 想看“计划怎么写”
看：
- `templates/EXPERIMENT_PLAN_TEMPLATE.md`
- `skills/experiment-plan/SKILL.md`

## 想看“计划怎么变成执行”
看：
- `skills/experiment-bridge/SKILL.md`

## 想看“系统怎么防止实验自欺欺人”
看：
- `skills/experiment-audit/SKILL.md`
- `skills/shared-references/experiment-integrity.md`
- `skills/shared-references/reviewer-independence.md`

## 想看“最后结论怎么被收口”
看：
- `skills/result-to-claim/SKILL.md`

## 想看“中断后怎么恢复”
看：
- `skills/shared-references/recovery-state-contract.md`
- `tools/experiment_queue/queue_manager.py`
- `tools/watchdog.py`

## 想看“整个项目做了什么改造”
看：
- `discussions/ARIS_HARDENING_PROGRESS_REPORT_20260513.md`
- `MANIFEST.md`

---

如果你愿意，下一步我可以继续直接给你写第三份：

# 《ARIS 主链 4 个核心技能的超白话逐段讲解》

它会更像：
- 每个 skill 一节
- 按段落解释它在干嘛
- 告诉你哪些段最重要
- 告诉你哪些段第一次可以略读

那份会更适合你“真正逐文件读源码前”做热身。