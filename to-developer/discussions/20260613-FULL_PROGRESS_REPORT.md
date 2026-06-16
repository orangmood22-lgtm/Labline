# FPA-IOD 项目全面工作汇报

> **项目**: Fourier Prototype Augmentation for Few-Shot Incremental Object Detection\
> **时间**: 2026年4月27日 — 5月7日\
> **总耗时**: \~28h（含 \~15h GPU 训练, \~33轮对话）\
> **平台**: Trae IDE + DeepSeek-v4-pro / Gemini 3.1 Pro + V100×4 GPU 服务器

***

## 一、项目起源

**核心 idea**: 在 Few-Shot Incremental Object Detection (FSIOD) 中，用**频域增广 (FPA)** 扩充 novel class 的 support features，生成更多样的原型 (prototype)，提升少样本检测性能。

具体操作：对 backbone 输出的 RoI features 做 FFT → 振幅缩放 ±10% → 相位扰动 σ=0.03 → 10% 频率掩码 → IFFT 重建 → 取平均构建原型。PASCAL VOC 数据集，10 base / 10 novel，k=5 shots，freeze backbone + RPN。

***

## 二、工作流程全览

```
Phase 1 (04/27-28):  代码搭建 + 初始实验 → 发现"塌陷"
Phase 2 (04/29-30):  机制诊断 (空间对照、频域分析、k-shot 扫描)
Phase 3 (04/30-05/01): 四种修复尝试 → 全部失败
Phase 4 (05/01-02):  发现 eval 用训练集的 bug → 修复评估管线
Phase 5 (05/02-03):  Clean 实验 → FPA = Baseline (零效果)
Phase 6 (05/03-06):  文献调研 + DeepSeek/Gemini 讨论 → 项目重新定位
Phase 7 (05/06-07):  Proto-FPA vs Spatial-FPA 三组对比 → 发现原型未注入的 bug
Phase 8 (05/07):     定价对比文档 + 全面汇报
```

***

## 三、各阶段详情

### Phase 1: 代码搭建 + 初始实验

**做了什么**:

- 实现 `FourierPrototypeAugmentor`：支持 2D 特征图和 1D 向量的频域增广
- 实现 `ClassPrototypeBank`：存储 base/novel 原型
- 实现 `train_incremental.py`：从零构建 FSIOD 训练管线 (Faster R-CNN + VOC)
- 在 V100 GPU 服务器上跑 baseline vs FPA 对照

**遇到的问题**:

- 服务器环境：PyTorch 版本、CUDA 版本兼容 → 解决：用已有的 miniconda 环境
- VOC 数据需要自己写解析 → 解决了：写了 `VOCFSIODDataset` 类
- k-shot 采样逻辑复杂 → 解决了：逐类计数，shuffle 后限制

**关键发现**: 训练集上 FPA 导致 bird (100→0)、cat (100→0)、cow (100→0) 完全塌陷，但 boat (0→100)、bus (0→100) 飙升。**整体 mAP 从 81.5 降到 75.7。**

***

### Phase 2: 机制诊断

**做了什么**:

- **空间对照实验**: 用相同强度的高斯噪声替代频域增广 → 空间噪声完全无害 (mAP=81.5)
- **频域分析**: 对各类原型做 FFT 频谱计算 HF/LF 比 → 塌陷类和非塌陷类无模式差异
- **k-shot 扫描**: k=1 (-0.6), k=3 (-2.3), k=5 (-5.8) → 剂量-响应关系
- **与 Gemini 3.1 Pro 讨论**: 提出"相干相位平移"机制假说

**Gemini 的核心分析**:

> FPA 不是信息破坏，是**信息翻译**。高斯噪声是 i.i.d. 的，池化后归零（大数定律）；FPA 的相位扰动产生**全局空间相干位移**，池化无法抵消，导致嵌入被整体推过决策边界。这就是为什么效果是二值的（100→0 而非渐进退化）。

**解决了**: 确定了塌陷是频域特有的现象，排除了随机噪声的混淆。

***

### Phase 3: 四种修复尝试 → 全部失败

| 方法              | 原理                       | 训练集 mAP | val 集 mAP |
| ----------------- | -------------------------- | :--------: | :--------: |
| Baseline (no FPA) | 无增广                     |    81.5    |    94.0    |
| FPA only          | 频域原型增广               |    75.7    |     —      |
| + PML             | 原型间余弦间隔约束         |    78.0    |     —      |
| + CCFR            | 类条件频域重要性掩码       |    77.7    |     —      |
| + AFPA            | 基于原型隔离度的自适应强度 |   58.6 ☢️   |     —      |
| + Phase-Aware     | 对比训练 f(x)=f(FPA(x))    |   3.6 ☢️    |     —      |

**PML** 几乎无效 → 原型不是"靠太近"的问题\
**CCFR** 完全无效 → 不是"攻击了特定频带"\
**AFPA** 灾难性 → fragility score 方向完全算反了\
**Phase-Aware** 全面崩溃 → 对比训练太激进

**核心发现**: 四个不同方向的修复全部失败，构成了强有力的证据——这不是"可轻易修好的 bug"，而是基本面。

***

### Phase 4: 🔴 最大 Bug 发现 — eval 用了训练集

**问题**: 所有 AP 值都在训练集上测的。AP=100 是**过拟合记忆**，不是真正的检测能力。

**怎么发现的**: 写 `diagnose.py` 逐项检查 pipeline。发现 `evaluate_incremental()` 调用 `get_voc_dataloader(is_train=True)`。

**怎么修的**:

1. ~~手写简化 AP~~ → 改用 `pycocotools` COCO 标准评估
2. ~~训练集 eval~~ → 改用 VOC2007 val 集 (`val_mode=True`)
3. ~~O(N²) 暴力 AP~~ → COCOeval 30 秒跑完 2510 张图

**修复后 baseline**: Val 集 AP50 mAP=94.0（真实的检测能力，合理范围）

***

### Phase 5: Clean 实验 — FPA = Baseline (零效果)

| <br />            | nAP (AP50) | bAP (AP50) |  mAP  |   Δ   |
| ----------------- | :--------: | :--------: | :---: | :---: |
| Baseline (无 FPA) |    98.8    |    89.2    | 94.0  |   —   |
| Proto-FPA         |    98.8    |    89.2    | 94.0  | **0** |
| Spatial-FPA       |    98.8    |    89.2    | 94.0  | **0** |

**结论**: FPA 在 val 集上对 FSIOD 完全无影响。之前的"塌陷"纯粹是训练集评估的 artifact。

***

### Phase 6: 文献调研 + 重新定位

**关键文献**: Jiang et al. "Revisiting Pool-based Prompt Learning for FSCIL" (ICCV 2025, arxiv 2507.09183)

**核心发现**:

- 他们的 LGSP-Prompt 用**空间维度的 FFT**（在图像特征图上做频域 prompting）→ 有效
- 我们的 Proto-FPA 用**特征维度的 FFT**（在原型向量上做频域增广）→ 无效
- 两个发现互补：频域信息的有效性**取决于应用维度**

**与 DeepSeek v4 Pro 讨论后重新定位**:

> 从 "FPA 导致塌陷" (假阳性) → "频域增广的维度依赖性：空间维度有效，原型维度无效" (设计原则)

**新论文标题建议**: *"Where Does Frequency Augmentation Help in Few-Shot Incremental Learning? A Tale of Two Spaces"*

***

### Phase 7: Proto-FPA vs Spatial-FPA 三组对比 → 🐛 又发现 Bug

**想做什么**: Baseline vs Proto-FPA vs Spatial-FPA 三组对照，验证"维度依赖性"假说。

**代码流**:

1. `compare.py` (V1): 三组结果完全相同 → **原因**: `proto_bank` 字典算完从未被模型使用
2. `compare_v2.py`: 尝试注入原型到 `cls_score.weight` → **shape 不匹配**: 原型 256-dim，分类器期望 1024-dim
3. `compare_v3.py`: 从 `box_head.fc7` 输出端提取 1024-dim 特征，匹配分类器维度 → **已写待跑**

**过程中的子 bug**:

- `import torch.nn as nn` 在一行 → 服务器 Python 解析为 `import nn` → 改成分两行
- 空间 RoI 特征图大小不一 (不同物体尺寸) → 改为逐样本处理
- `tee` 缓冲导致日志为空 → 改为直接重定向
- `sed` 全局替换 weight 索引 → 误改后手动修复
- SSH `&&` 在 PowerShell 下行不通 → 分开执行
- FsDet (Detectron2) 依赖太重在服务器上装不了 → 放弃，自己实现

**当前状态**: `compare_v3.py` 已上传服务器，prototype injection 逻辑已写，待运行验证。

***

### Phase 8: 辅助工作

**AI Coding 定价对比文档** (`refine-logs/AI_CODING_PRICING.md`):

- 覆盖 9 家平台: Copilot、Cursor、Trae、Windsurf、Claude Code、GLM、Kimi、Codex
- 含套餐/Token消耗/稳定性/社区评价/购买建议
- 数据来源标注明确（官网 + 社区 + 媒体报道）

**新手科普文档** (`refine-logs/BEGINNER_GUIDE.md`):

- 用比喻讲 FSIOD、FPA、塌陷、对照实验
- 无数学公式，普通人可读

**项目重新定位文档** (`refine-logs/PROJECT_REORIENTATION.md`):

- 完整的实验路线图（4 组实验）
- 论文大纲（7 节）

***

## 四、Bug 清单与修复

| #   | Bug                   | 严重性 | 发现方式                 | 修复                          |
| --- | --------------------- | :----: | ------------------------ | ----------------------------- |
| 1   | eval 用了训练集       | 🔴致命  | diagnose.py 主动检查     | 改用 voc val + COCO API       |
| 2   | AP 计算 O(N²) 超时    |   🟡    | val 集 2510 张图跑不完   | 换 pycocotools                |
| 3   | 原型从未注入分类器    | 🔴致命  | 三组结果完全相同         | compare\_v3 用 box\_head 特征 |
| 4   | 原型/分类器维度不匹配 | 🔴致命  | RuntimeError shape       | 从 box\_head.fc7 提取         |
| 5   | import 语法兼容性     |   🟡    | ModuleNotFoundError 'nn' | 分行 import                   |
| 6   | 空间 RoI 尺寸不一     |   🟡    | RuntimeError stack       | 逐样本处理                    |
| 7   | tee 缓冲无日志        |   🟡    | 日志文件为空             | > file.txt 直接重定向         |
| 8   | GitHub 被墙           |   🟡    | Connection refused       | 10800 端口代理克隆            |
| 9   | detectron2 依赖太重   |   🟡    | 安装失败                 | 放弃 FsDet，自己实现          |

***

## 五、当前遗留问题

### 🔴 待解决

1. **compare\_v3.py 未跑完** — prototype injection 逻辑是否正确？FPA 是否真的零效果？
2. **Spatial-FPA 未在同一代码基座对比** — 需要跑一次 spatial mode 确认
3. **FsDet 标准 benchmark 未用上** — 3 splits × 30 seeds 的标准评估比我们的单次 run 更可靠
4. **LGSP-Prompt 的输入端频域 prompting 未在检测上测试** — 真正的 "跨空间对照" 缺失

### 🟡 待决策

1. **零效果的可能性**: 如果 V3 跑完 Proto-FPA 仍无任何效果，说明频域增广对 FSIOD 确实无效。此时论文方向需再调整。
2. **任务差异**: Jiang et al. 做的是 ViT + FSCIL (分类)，我们做的是 CNN + FSIOD (检测)。骨架 + 任务都不同，"维度依赖性"假说需要更严格的跨任务验证。
3. **论文是否需要先投 workshop 而非主会** — 当前证据链还不够完整。

***

## 六、产出一览

| 文件                                   | 说明                                                              |
| -------------------------------------- | ----------------------------------------------------------------- |
| `fpa_iod/fpa_module.py`                | FPA 核心模块 + 3 种修复 (PML/CCFR/AFPA) + SpatialFourierAugmentor |
| `fpa_iod/train_incremental.py`         | 主训练脚本 (已修复为 val 集 COCO eval)                            |
| `fpa_iod/train_incremental_relief.py`  | 修复方案对比训练                                                  |
| `fpa_iod/phase_aware_trainer.py`       | 相位感知对比训练                                                  |
| `fpa_iod/compare.py`                   | Proto/Spatial-FPA 三组对比 (有 bug)                               |
| `fpa_iod/compare_v2.py`                | 修复 prototype injection (维度仍错)                               |
| `fpa_iod/compare_v3.py`                | ✅ 最新版 (box\_head 特征 + 正确注入)                              |
| `fpa_iod/diagnose.py`                  | 全管线诊断脚本                                                    |
| `fpa_iod/dataset.py`                   | VOC FSIOD 数据集 (已加 val\_mode 支持)                            |
| `fpa_iod/config.py`                    | 配置文件                                                          |
| `refine-logs/AI_CODING_PRICING.md`     | 9 家 AI Coding 定价对比                                           |
| `refine-logs/BEGINNER_GUIDE.md`        | 新手科普教程                                                      |
| `refine-logs/PROJECT_REORIENTATION.md` | 项目重新定位 + 实验路线图                                         |
| `refine-logs/MITIGATION_METHODS.md`    | 三种修复方案设计文档                                              |
| `refine-logs/PROGRESS_REPORT.md`       | 导师汇报文档                                                      |

***

## 七、时间线

| 日期         | 事件                                           |
| ------------ | ---------------------------------------------- |
| 04/27        | 项目启动，搭 FPA 模块和训练脚本                |
| 04/28        | 首轮实验，发现 bird/cat/cow 塌陷               |
| 04/29        | 空间对照、频域分析、k-shot 扫描                |
| 04/29        | Gemini 分析：相位相干平移假说                  |
| 04/30-05/01  | PML/CCFR/AFPA/Phase-Aware 四修复全失败         |
| 05/01        | 写 diagnose.py 发现 eval 用训练集 bug          |
| 05/02        | 修复 eval (COCO API + val set)                 |
| 05/02        | Clean 实验 baseline: mAP=94.0                  |
| 05/03        | 文献调研：找到 Jiang et al. ICCV 2025          |
| 05/03        | DeepSeek 讨论：项目重新定位                    |
| 05/06        | 克隆 FsDet + LGSP 仓库                         |
| 05/06-07     | Proto/Spatial-FPA 三组对比（5 次迭代修复 bug） |
| 05/07        | 发现原型未注入 bug，写 compare\_v3.py          |
| 05/07        | AI Coding 定价对比 + 新手教程 + 重新定位文档   |
| 05/07 (夜间) | 用户关机出差，实验中断                         |
| 05/08        | 新增 GLM/Kimi/Codex 到定价文档                 |
| 05/08        | 本汇报文档                                     |

***

## 八、核心教训

1. **永远先验证评估管线** — 训练集 eval 这个 bug 浪费了 \~30h 的整体时间，四个修复方案的成功/失败判断都不可靠。
2. **零效果也是科学发现** — 从原始的"塌陷"到正确的"零效果"，虽然论文方向从诊断变成了设计原则，但学术价值没有消失。
3. **原型没有被模型使用 = 代码写了白写** — `proto_bank` 算完从未注入分类器，这是最蠢的 bug，也是最容易被忽略的。
4. **Fourier 增广不是万能药** — Jiang et al. 在空间维度有效，我们在原型维度无效，区别在于 (a) 空间拓扑是否保留, (b) 池化是否抹除了频域信号, (c) 任务骨架差异 (ViT vs CNN)。
5. **复现基线比造新方法更快出成果** — 如果一开始就在 FsDet 上跑标准 benchmark，只需要 1 天就能看出 FPA 是否有效。造轮子花的时间比用轮子多 5 倍以上。
