# ARIS 痛点诊断：FPA-IOD 实验复盘 × 架构根因分析

> 基于 `FULL_PROGRESS_REPORT.md` 的实际踩坑经验，对照 ARIS 源码架构，逐一定位根因。

---

## 一、诊断方法论

你的 FPA-IOD 项目虽然是在 Trae + DeepSeek/Gemini 上手动驱动的，但暴露出的问题模式**精准映射到 ARIS 架构的结构性缺陷**。下面按"表象 → 根因 → ARIS 架构缺陷"三层展开。

---

## 二、致命痛点逐项分析

### 痛点 1：eval 用了训练集 —— 28h 工作建立在错误基础上

**表象**：
- Phase 1-3 所有实验结论（塌陷、四种修复全失败）都基于训练集评估
- 直到 Phase 4 写 `diagnose.py` 才发现 `evaluate_incremental()` 调了 `get_voc_dataloader(is_train=True)`
- 修复后发现 FPA = Baseline（零效果），之前的"塌陷"是过拟合 artifact

**根因**：
- Stage 2（实现代码）和 Stage 3（跑实验）由同一个 AI session 完成
- 写 eval 代码的 AI 自己 review 自己 → 无法发现 `is_train=True` 这种语义级 bug
- 代码在语法和运行层面完全正确，只是逻辑错误 → 常规 debug 不会触发

**ARIS 架构对应缺陷**：

| ARIS 设计 | 理论上应该怎样 | 实际上为什么失效 |
|---|---|---|
| `/experiment-bridge` Phase 2.5 的 GPT 代码审查 | GPT-5.4 xhigh 审查实验代码，检查 eval 正确性 | 审查清单第 5 条写了"CRITICAL: Does evaluation use the dataset's actual ground truth labels — NOT another model's output as ground truth?"但**没有覆盖 train/val split 这个维度** |
| `/experiment-audit` | 跨模型审查实验完整性，检查 "fake ground truth" | 审查清单 A 项"Ground Truth Provenance"只检查 GT 是否来自数据集 vs 模型输出，**不检查是否在正确的 split 上评估** |
| `/result-to-claim` | Codex 判断结果是否支持 claim | 它接收的是已经算好的数字，**无法回溯这些数字是怎么算出来的** |

**结论**：ARIS 的审查体系有一个盲区——**评估代码的数据流正确性**。`experiment-audit` 检查的是"GT 是否造假"，但不检查"eval 是否在正确的数据集 split 上跑"。这是一个非常常见且致命的 bug 模式，却不在任何审查清单里。

---

### 痛点 2：原型从未注入分类器 —— 代码写了白写

**表象**：
- Phase 7 的 `compare.py` 三组结果完全相同
- 原因：`proto_bank` 字典算完后，从未被模型的 `cls_score.weight` 使用
- 连续迭代 3 个版本（compare.py → v2 → v3）才接近修复

**根因**：
- AI 写代码时，每个模块（FPA 模块、原型 bank、分类器）各自逻辑正确
- 但**模块间的接线**有断路——原型算了但没注入，注入了但维度不匹配
- 这是"集成 bug"：单元测试通过，集成测试爆炸

**ARIS 架构对应缺陷**：

| ARIS 设计 | 理论上应该怎样 | 实际上为什么失效 |
|---|---|---|
| Stage 2 的"自审" | Claude 写完代码后做 self-review，检查"Are results saved to JSON/CSV?" | 自审清单关注的是外围质量（argparse、seed、logging），**不检查核心数据通路是否连通** |
| `/experiment-bridge` 代码审查 | GPT 审查代码是否"correctly implements the method" | GPT 看到的是代码文本，**如果每个函数各自正确但调用链有断裂**，静态审查很难发现 |
| 没有 Sanity Check 的断言机制 | `/experiment-bridge` Phase 3 跑 sanity check | Sanity check 只验证"训练循环跑不跑得通"，**不验证"核心改动是否真正生效"**（比如：FPA 组的预测结果应该和 baseline 不同） |

**结论**：ARIS 缺少一个关键环节——**"改动生效性验证"（Delta Assertion）**。跑完实验后，不仅要检查"代码没报错"，还要检查"实验组和对照组的输出确实不同"。如果 FPA 组 = Baseline 组 = 完全相同的数字，这本身就是一个红旗信号，应该立即触发诊断。

---

### 痛点 3：四种修复方案全部失败，但没有及时止损

**表象**：
- PML、CCFR、AFPA、Phase-Aware 四种修复方案，从 -3.5 到 -77.9 的灾难性退化
- 整个 Phase 3 消耗了约 2 天时间
- 直到四种全试完才停下来反思"是不是基本面有问题"

**根因**：
- 没有"止损机制"：当连续 N 次修复都失败时，应该触发"方向性反思"而不是继续在同一维度尝试
- AI 倾向于"做加法"——问题出了就叠模块，而不是退一步检查基础假设

**ARIS 架构对应缺陷**：

| ARIS 设计 | 理论上应该怎样 | 实际上为什么失效 |
|---|---|---|
| `/auto-review-loop` 最多 4 轮 | 轮次上限防止无限循环 | 但每轮只问"怎么改进"，**从不问"这个方向本身对不对"** |
| `/result-to-claim` | 判断结果是否支持 claim | 只在实验完成后触发一次，**不在中间迭代时触发** |
| 没有"Pivot Gate" | — | ARIS 流水线里没有一个显式的"方向性重评估"节点。当连续失败时，应该触发的是 `/novelty-check` 或文献再调研，而不是继续在同一框架内修补 |

**结论**：ARIS 的 review loop 是"改进型"的——假定方向正确，只做细节修补。缺少"战略级撤退"机制：当连续 N 轮改进都无法达标时，应该自动触发更高层级的方向性审查。

---

### 痛点 4：维度不匹配等工程 bug 反复出现

**表象**：
- 原型 256-dim vs 分类器 1024-dim 的 shape mismatch
- `import torch.nn as nn` 的语法兼容性
- 空间 RoI 尺寸不一导致 stack 失败
- `tee` 缓冲、`sed` 全局替换误伤、SSH `&&` PowerShell 不兼容

**根因**：
- 这些都是**环境感知不足**的问题——AI 不知道目标服务器的 Python 版本特性、shell 行为差异、模型内部张量维度
- ARIS 的 `/run-experiment` 只做"Pre-flight Check"（GPU 空不空），**不做代码兼容性检查**

**ARIS 架构对应缺陷**：

Stage 2（实现）假定代码在本地能跑 = 在远程也能跑。没有：
- 远程环境 probe（Python 版本、已装包列表、shell 类型）
- 代码的 dry-run 验证（`python -c "import ..."` 级别的快速检查）
- 张量维度的静态分析（读模型结构，确认输入输出 shape 匹配）

---

### 痛点 5：从 Phase 1 到 Phase 7，上下文早已超载

**表象**：
- 33 轮对话，横跨 8 个 Phase
- 后期的 bug 修复越来越低效——比如 compare.py 迭代了 3 个版本才修好

**根因**：
- 单 session 里积累了太多历史上下文（文献调研、四种修复方案的代码、调试过程）
- 后期 session 的有效上下文空间被大量已过时的信息挤占
- AI 在 Phase 7 写代码时，可能还残留着 Phase 3 的修复思路的"惯性"

**ARIS 架构对应缺陷**：

这正是架构分析中指出的**"单 Session 串行，无真正隔离"**问题。ARIS 的 `COMPACT` 模式和 `REVIEW_STATE.json` 只为 auto-review-loop 做了有限的状态压缩，但：
- idea-discovery 阶段的大量文献没有压缩机制
- Stage 2 实现阶段的调试过程没有压缩机制
- 失败的修复尝试会持续占据上下文，却不会被标记为"已废弃，不要参考"

---

## 三、ARIS 审查体系的盲区总结

将你的 9 个 bug 与 ARIS 的审查清单做交叉比对：

| Bug | 严重性 | ARIS 中谁该抓住 | 实际能否抓住 | 盲区原因 |
|---|---|---|---|---|
| eval 用训练集 | 🔴致命 | `/experiment-audit` Check A | ❌ 不能 | 清单只查 GT 来源，不查 split |
| 原型未注入分类器 | 🔴致命 | `/experiment-bridge` Phase 2.5 | ⚠️ 可能 | 依赖 GPT 能否从静态代码发现调用链断裂 |
| 原型/分类器维度不匹配 | 🔴致命 | `/experiment-bridge` Phase 3 sanity | ⚠️ 部分 | Sanity check 会报 RuntimeError，但只在部署后 |
| import 语法兼容 | 🟡中等 | `/run-experiment` pre-flight | ❌ 不能 | Pre-flight 只查 GPU，不查代码兼容性 |
| 空间 RoI 尺寸不一 | 🟡中等 | 同上 | ❌ 不能 | 同上 |
| tee 缓冲无日志 | 🟡中等 | 无对应审查 | ❌ 不能 | 完全不在 ARIS 视野内 |
| AP 计算 O(N²) 超时 | 🟡中等 | 无对应审查 | ❌ 不能 | 性能问题不在审查范围 |
| GitHub 被墙 | 🟡中等 | 无对应审查 | ❌ 不能 | 网络环境不在 ARIS 视野内 |
| detectron2 装不了 | 🟡中等 | 无对应审查 | ❌ 不能 | 依赖安装不在审查范围 |

**9 个 bug 中，ARIS 能可靠抓住的：0 个。可能抓住的：2 个。完全抓不住的：7 个。**

---

## 四、根因汇总：五个结构性缺陷

| # | 缺陷 | 一句话描述 | 你的实验中的体现 |
|---|---|---|---|
| D1 | **Executor 自审自判** | 写代码的和审代码的是同一个 AI，或者审查发生得太晚 | eval 用训练集跑了 4 个 Phase 才被发现 |
| D2 | **审查清单有盲区** | experiment-audit 不查 split，不查数据通路连通性 | 原型未注入、eval 用错 split 都漏过 |
| D3 | **没有 Delta Assertion** | 实验组 vs 对照组的输出差异不做自动校验 | compare.py 三组结果完全相同却没有自动报警 |
| D4 | **没有战略止损** | 连续失败时不触发方向性反思 | 四种修复全败后才人工叫停 |
| D5 | **上下文无隔离** | 全流程在单 session 里，历史噪声累积 | 33 轮对话后期 bug 修复效率明显下降 |

---

## 五、对三边架构改造的启示

上述五个缺陷指向的改造方向：

| 缺陷 | 需要什么 | 三边架构中谁负责 |
|---|---|---|
| D1: 自审自判 | Executor 不能审自己的代码 | **Reviewer** 必须在 Executor 写完代码后立即介入，不是等到实验跑完 |
| D2: 审查盲区 | 更完整的审查清单 + 可扩展的审查框架 | **Reviewer** 的审查协议需要升级，覆盖 split 正确性、数据通路连通性 |
| D3: 缺 Delta Assertion | 实验结果的自动一致性检查 | **Leader** 在收到实验结果后，先做基础一致性检查再决定下一步 |
| D4: 缺战略止损 | 连续失败时触发方向性审查 | **Leader** 维护全局进度，连续 N 次失败时强制触发 Pivot Gate |
| D5: 上下文无隔离 | 每个阶段独立 session，通过文件交接 | **Leader** 负责分发任务和收集产出，**Executor** 每次任务是干净的 session |

---

## 六、下一步

以上诊断为三边架构改造提供了具体的需求锚点。接下来的讨论议题：

1. **Leader / Executor / Reviewer 的职责边界**怎么划？
2. **文件契约**需要升级到什么程度？（schema 校验？checklist 文件？）
3. **审查时机**怎么安排？（写完代码立即审？跑完 sanity 再审？每轮都审？）
4. **止损机制**怎么实现？（Leader 的"Pivot Gate"触发条件是什么？）
5. **上下文隔离**怎么落地？（Agent 子任务？Worktree 隔离？文件级交接？）
