# ARIS Skill 目录（中文版）

> 自动生成于 2026-06-17 10:37。共 96 个 skill，12 个分类。
>
> 生成命令：`python3 tools/translate_skill_catalog.py`

## 目录

- [Pipeline/编排](#pipeline编排)（5）
- [研究发现](#研究发现)（8）
- [搜索/数据源](#搜索数据源)（7）
- [实验](#实验)（10）
- [论文撰写](#论文撰写)（13）
- [论文演示](#论文演示)（4）
- [图表/可视化](#图表可视化)（8）
- [审查/质量](#审查质量)（6）
- [专利/公文](#专利公文)（8）
- [工具/同步](#工具同步)（8）
- [计算资源](#计算资源)（3）
- [开发工具](#开发工具)（16）

---

## Pipeline/编排

### `/dse-loop`

**面向计算机体系结构与 EDA 的自动设计空间探索循环。**

参数：`任务描述`

```
/dse-loop [task-description — include program, parameters, objective, and timeout]
```

### `/init-research`

**一键创建新科研项目：mkdir → git init → install skills → CLAUDE.md → project.yaml。**

参数：`项目名 [--size full|small] [--server SSH别名] [--remote GIT_URL] [--direction 研究方向]`

```
/init-research my-project --direction "研究方向" --server 4090x4
```

### `/leader`

**三边架构总编排：自动派生 Executor、调 Reviewer，一个窗口全流程。**

参数：`研究方向或计划路径`

```
/leader "基于频域特征的增量目标检测"
```

### `/meta-optimize`

**分析 ARIS 使用日志，提出 SKILL.md 和工作流优化建议。**

参数：`目标 skill 或 all`

```
/meta-optimize
```

### `/research-pipeline`

**全自动研究 pipeline：想法发现→实现→自动审稿→论文撰写。**

参数：`研究方向`

```
/research-pipeline "factorized gap in discrete diffusion LMs"
```

---

## 研究发现

### `/comm-lit-review`

**跨多个来源进行系统性社区文献综述。**

```
/comm-lit-review
```

### `/idea-creator`

**根据宽泛方向生成并排序研究想法。**

参数：`研究方向`

```
/idea-creator [research-direction]
```

### `/idea-discovery`

**完整想法发现流程：文献调研→生成想法→新颖性检查→评审。**

参数：`研究方向`

```
/idea-discovery "增量目标检测"
```

### `/idea-discovery-robot`

**面向机器人与具身 AI 的想法发现流程。**

参数：`机器人方向`

```
/idea-discovery-robot [robotics-direction]
```

### `/novelty-check`

**对比现有文献验证研究想法的新颖性。**

参数：`想法描述`

也用于：专利/公文

```
/novelty-check "用频域特征做增量学习的原型对齐"
```

### `/research-lit`

**搜索并分析研究论文，查找相关工作并总结关键思想。**

参数：`论文主题或 URL`

```
/research-lit [paper-topic-or-url]
```

### `/research-refine`

**通过 GPT 迭代审查将模糊研究方向细化为聚焦方案。**

```
/research-refine
```

### `/research-review`

**通过 Codex MCP 获取 GPT 对研究的深度批判性评审。**

参数：`主题或范围`

```
/research-review [topic-or-scope]
```

---

## 搜索/数据源

### `/alphaxiv`

**通过 AlphaXiv 摘要快速查询单篇论文，支持分级来源回退。**

参数：`arXiv ID 或 URL`

```
/alphaxiv [arxiv-id-or-url]
```

### `/arxiv`

**从 arXiv 搜索、下载并总结学术论文。**

参数：`查询词或 arXiv ID`

也用于：论文撰写

```
/arxiv "few-shot incremental learning"
```

### `/deepxiv`

**通过 DeepXiv 对论文进行结构化深度分析。**

参数：`arXiv ID 或 URL`

```
/deepxiv [query-or-paper-id]
```

### `/exa-search`

**通过 Exa AI 搜索引擎检索研究论文。**

参数：`搜索查询`

```
/exa-search [search-query-or-url]
```

### `/gemini-search`

**通过 Gemini 搜索论文，用于广泛文献发现。**

参数：`搜索查询`

```
/gemini-search [search-query]
```

### `/openalex`

**通过 OpenAlex API 搜索学术论文，含引用量和元数据。**

参数：`搜索查询`

```
/openalex [search-query]
```

### `/semantic-scholar`

**通过 Semantic Scholar API 搜索已发表论文，含引用量。**

参数：`查询词或论文 ID`

也用于：论文撰写

```
/semantic-scholar query-or-paper-id
```

---

## 实验

### `/ablation-planner`

**当主结果支撑论文主张时，从审稿人视角设计消融实验。**

参数：`方法描述或主张`

也用于：论文撰写

```
/ablation-planner [method-description-or-claim]
```

### `/analyze-results`

**分析 ML 实验结果，计算统计量并生成对比表和洞见。**

参数：`结果路径或描述`

```
/analyze-results [results-path-or-description]
```

### `/experiment-audit`

**独立审计实验完整性：检查假 GT、刷分和虚假结果。**

参数：`[experiment-dir-or-results-path]`

也用于：审查/质量

```
/experiment-audit [experiment-dir-or-results-path]
```

### `/experiment-bridge`

**将实验计划转换为可执行代码实现。**

参数：`[experiment-plan-path-or-topic]`

```
/experiment-bridge
```

### `/experiment-plan`

**设计严谨实验计划，声明预期并设置差异断言。**

也用于：Pipeline/编排

```
/experiment-plan
```

### `/experiment-queue`

**通过 SSH 管理多种子/多配置 ML 实验队列，支持 OOM 重试。**

参数：`manifest 或 grid spec`

```
/experiment-queue [manifest-or-grid-spec]
```

### `/monitor-experiment`

**监控正在运行的 ML 实验，检查进度并检测问题。**

参数：`[server-alias or screen-name]`

```
/monitor-experiment --server 4090x4
```

### `/result-to-claim`

**判断实验结果支持哪些主张，缺少哪些证据。**

参数：`实验描述或 WandB run`

也用于：论文撰写

```
/result-to-claim [experiment-description-or-wandb-run]
```

### `/run-experiment`

**在本地/远程/Vast.ai/Modal GPU 上部署并运行 ML 实验。**

参数：`实验描述`

```
/run-experiment --server 4090x4 --script code/train.py
```

### `/training-check`

**定期检查 WandB 指标，及早发现训练问题（NaN/损失发散/GPU 空闲）。**

参数：`WandB run 路径`

```
/training-check [wandb-run-path]
```

---

## 论文撰写

### `/auto-paper-improvement-loop`

**自动迭代：审稿→修复→复审，直到达标或轮次耗尽。**

参数：`论文目录 [--max-rounds 轮数]`

```
/auto-paper-improvement-loop "paper/" --max-rounds 3
```

### `/auto-review-loop`

**使用 Codex GPT 审稿人的多轮自动审稿循环。**

参数：`[topic-or-scope]`

```
/auto-review-loop [topic-or-scope]
```

### `/auto-review-loop-llm`

**使用 LLM API（非 Codex）的多轮自动审稿循环。**

参数：`[topic-or-scope]`

```
/auto-review-loop-llm [topic-or-scope]
```

### `/auto-review-loop-minimax`

**使用 MiniMax API 的多轮自动审稿循环。**

参数：`[topic-or-scope]`

```
/auto-review-loop-minimax [topic-or-scope]
```

### `/claims-drafting`

**根据实验证据起草并验证研究主张。**

参数：`[invention-disclosure-path]`

```
/claims-drafting [invention-disclosure-path]
```

### `/formula-derivation`

**整理并推导研究公式，生成可用于论文的推导包。**

参数：`问题/目标/当前公式或笔记`

也用于：审查/质量

```
/formula-derivation [problem-goal-current-formulas-or-notes]
```

### `/paper-compile`

**编译 LaTeX 论文并检查错误。**

参数：`[paper-directory]`

```
/paper-compile [paper-directory]
```

### `/paper-plan`

**规划论文结构和大纲。**

参数：`[topic-or-narrative-doc] [— style-ref: <source>]`

```
/paper-plan [topic-or-narrative-doc] [— style-ref: <source>]
```

### `/paper-write`

**撰写论文单个章节。**

参数：`[venue-or-section] [— style-ref: <source>]`

```
/paper-write [venue-or-section] [— style-ref: <source>]
```

### `/paper-writing`

**完整论文撰写 pipeline（6+ 阶段）。**

参数：`[narrative-report-path-or-topic] [— style-ref: <source>]`

```
/paper-writing --effort balanced --assurance submission
```

### `/rebuttal`

**解析审稿意见，在字数限制内起草回复并管理后续轮次。**

参数：`论文路径或评审包`

```
/rebuttal "paper/ + reviews" --venue ICML --character-limit 5000
```

### `/resubmit-pipeline`

**将已打磨论文改投到其他会议/期刊（纯文字调整）。**

参数：`论文目录；目标会场`

```
/resubmit-pipeline [paper-base-dir] [— target-venue: <name>] [— review-corpus: <path>]
```

### `/writing-systems-papers`

**系统论文段落级结构蓝图（OSDI/SOSP/ASPLOS 等）。**

参数：`会场或章节`

```
/writing-systems-papers [venue-or-section]
```

---

## 论文演示

### `/paper-poster`

**从论文生成 A0 学术海报。**

参数：`论文目录`

```
/paper-poster [paper-directory-or-venue] [— style-ref: <source>]
```

### `/paper-slides`

**从论文生成 Beamer/PPTX 演示幻灯片。**

参数：`论文目录`

```
/paper-slides "paper/"
```

### `/paper-talk`

**端到端学术会议报告 pipeline。**

参数：`论文目录`

```
/paper-talk [paper-dir] [— talk_type: oral | spotlight | poster-talk | invited] [— minutes: N] [— assurance: draft | polished | conference-ready] [— reference: <pdf>] [— style: generic | why-rf | <venue>] [— style-ref: <paper-source>] [— effort: lite | balanced | max | beast] [— anonymous]
```

### `/slides-polish`

**对学术演讲幻灯片逐页 Codex 审查 + 定向修复。**

参数：`幻灯片目录或 pptx`

```
/slides-polish [slides-dir-or-pptx] — reference: <ref-pdf> [— style: generic | why-rf | neurips | icml | iclr | cvpr] [— effort: lite | balanced | max | beast] [— interactive]
```

---

## 图表/可视化

### `/embodiment-description`

**为专利申请生成正式实施例描述。**

参数：`实施例目录或列表`

```
/embodiment-description [claims-path-or-embodiment-details]
```

### `/figure-description`

**处理专利附图并生成正式附图说明。**

参数：`附图目录或附图列表`

```
/figure-description [figure-directory-or-figure-list]
```

### `/figure-spec`

**生成可编辑 SVG 的确定性出版级架构/流程/管线图。**

参数：`图表描述`

也用于：论文撰写

```
/figure-spec [description-of-diagram]
```

### `/mermaid-diagram`

**生成 Mermaid 图表：架构图、流程图、数据流图。**

参数：`图表描述`

也用于：论文撰写、专利/公文

```
/mermaid-diagram [diagram description or requirements]
```

### `/paper-figure`

**为论文生成出版级图表。**

参数：`图表描述`

```
/paper-figure [figure-plan-or-data-path]
```

### `/paper-illustration`

**使用 AI 为论文生成插图。**

参数：`描述`

```
/paper-illustration [description-or-method-file] [— style-ref: <source>]
```

### `/paper-illustration-image2`

**使用图生图 AI 模型生成论文插图。**

参数：`[description-or-method-file]`

```
/paper-illustration-image2 [description-or-method-file]
```

### `/pixel-art`

**生成像素风格插图。**

参数：`描述`

```
/pixel-art [description of what to draw]
```

---

## 审查/质量

### `/citation-audit`

**审查论文草稿中引用的完整性与正确性。**

参数：`论文目录`

```
/citation-audit "paper/"
```

### `/kill-argument`

**对抗性审查：模拟最严厉审稿人拒稿，判断论文是否已回应。**

参数：`论文目录`

```
/kill-argument "paper/"
```

### `/paper-claim-audit`

**审计论文主张与实际实验证据的一致性。**

参数：`[paper-directory]`

```
/paper-claim-audit [paper-directory]
```

### `/proof-checker`

**数学证明严格验证与修复，跨模型交叉审查。**

参数：`tex 文件路径或证明描述`

也用于：论文撰写

```
/proof-checker [path-to-tex-file or proof-description] [--deep-fix] [--restatement-check]
```

### `/proof-writer`

**为 ML/AI 理论撰写严格数学证明。**

参数：`定理陈述和假设`

```
/proof-writer [theorem-statement-and-assumptions]
```

### `/research-refine-pipeline`

**端到端 pipeline：串联 research-refine 和 experiment-plan。**

```
/research-refine-pipeline
```

---

## 专利/公文

### `/grant-proposal`

**根据研究想法起草结构化基金申请书（国自然/NSF/ERC 等）。**

参数：`研究方向 -- 基金类型`

```
/grant-proposal "研究方向" --type NSFC-青年
```

### `/invention-structuring`

**将原始发明想法整理为正式发明披露文档。**

参数：`发明描述`

```
/invention-structuring [invention-description-or-brief-path]
```

### `/jurisdiction-format`

**按特定法域（CN/US/EP/JP/KR）格式化专利权利要求。**

参数：`[patent-directory-or-jurisdiction]`

```
/jurisdiction-format [patent-directory-or-jurisdiction]
```

### `/patent-novelty-check`

**对比现有技术检查专利新颖性。**

参数：`专利权利要求或描述`

```
/patent-novelty-check [invention-description-or-brief-path]
```

### `/patent-pipeline`

**从想法到可提交文件的完整专利申请 pipeline。**

参数：`发明描述`

```
/patent-pipeline "发明内容描述"
```

### `/patent-review`

**审查并改进专利申请质量。**

参数：`专利文档路径`

```
/patent-review [patent-directory-or-scope]
```

### `/prior-art-search`

**检索与专利权利要求相关的现有技术。**

参数：`专利权利要求或发明`

```
/prior-art-search [invention-description-or-path]
```

### `/specification-writing`

**根据权利要求和发明披露撰写完整专利说明书。**

参数：`权利要求路径`

```
/specification-writing [claims-path]
```

---

## 工具/同步

### `/feishu-notify`

**向飞书/Lark 发送状态更新通知。**

参数：`消息文本`

```
/feishu-notify [message-text]
```

### `/feishu-session`

**管理飞书/Lark 远程 Codex 或 Claude Code 会话；默认使用 lark-channel-bridge，ARIS 自研 runner 仅作审计/合并 fallback。**

参数：`[start|mark-seen|report|merge]`

```
/feishu-session report leader-phone
```

### `/framework-update`

**一键更新 ARIS 框架：git pull + 重建 symlinks。**

参数：`[--force] [--dry-run]`

```
/framework-update
```

### `/overleaf-sync`

**本地项目与 Overleaf 双向同步。**

参数：`[setup <project-id> | pull | push | status]`

```
/overleaf-sync pull
```

### `/qzcli`

**管理启智平台 GPU 计算任务（提交/停止/监控）。**

参数：`login|avail|list|create|stop|batch|status|watch`

```
/qzcli [login|avail|list|create|stop <job-id>|batch|status|watch]
```

### `/research-wiki`

**持久化研究知识库：论文、想法、实验、主张及其关系。**

参数：`子命令：init|ingest|sync|query|update|lint|stats`

也用于：研究发现

```
/research-wiki init
```

### `/skill-dag-check`

**修改 skill 前检查依赖影响，列出上游/下游关系。**

```
/skill-dag-check
```

### `/sync`

**一键同步科研项目：git add/commit/push/pull + 远程部署。**

参数：`push|pull|deploy|status [--server 名称] [--message '提交信息']`

也用于：Pipeline/编排

```
/sync push --message "完成 backbone"
```

---

## 计算资源

### `/serverless-modal`

**在 Modal 无服务器平台运行 GPU 任务：训练/微调/推理。**

参数：`任务描述`

```
/serverless-modal [task-description]
```

### `/system-profile`

**性能分析：脚本/GPU/内存/互连，生成结构化报告。**

参数：`目标（如 train.py、gpu、pid 1234）`

```
/system-profile <target, e.g. "train.py", "gpu", "pid 1234", "vllm serving">
```

### `/vast-gpu`

**在 vast.ai 上租用、管理和销毁 GPU 实例。**

参数：`任务描述或操作`

```
/vast-gpu --min-vram 24 --max-cost 0.5
```

---

## 开发工具

### `/caveman`

**精简回复模式：砍掉废话，保留技术准确度，省 75% token。**

```
/caveman
```

### `/coder`

**代码实现角色：只写代码、测试、重构，不做部署或论文写作。**

参数：`实现什么？（描述代码任务）`

```
/coder
```

### `/deployer`

**部署角色：只做 SSH 同步、启动训练、监控实验、收集结果。**

参数：`部署什么？（描述部署任务）`

```
/deployer
```

### `/diagnose`

**系统化 bug 诊断：复现→最小化→假设→验证→修复→回归测试。**

```
/diagnose
```

### `/git-guardrails`

**给 Claude Code 装 git 安全钩子，拦截 force push 等危险操作。**

```
/git-guardrails
```

### `/grill-me`

**对你的方案进行压力测试式提问，逐个解决设计决策。**

```
/grill-me "频域特征模块设计方案"
```

### `/grill-with-docs`

**grill-me 升级版：讨论过程中自动更新项目文档和 ADR。**

```
/grill-with-docs "实验方案设计"
```

### `/handoff`

**生成交接文档，让新 agent/新会话能无缝接续当前工作。**

参数：`What will the next session be used for?`

```
/handoff
```

### `/review`

**双轴代码审查：规范合规性 + 需求实现度，并行评估。**

```
/review main
```

### `/tdd`

**测试驱动开发：红→绿→重构循环，先写测试再写实现。**

```
/tdd
```

### `/to-issues`

**把计划/PRD 拆成独立可执行的 Issue（垂直切片）。**

```
/to-issues
```

### `/to-prd`

**把当前对话上下文转化为正式 PRD 文档。**

```
/to-prd
```

### `/worker`

**低成本辅助执行角色：批量文档、引用清扫、测试草案和低风险 patch 草案。**

参数：`辅助处理什么？（描述低风险批量任务）`

```
/worker
```

### `/write-a-skill`

**引导创建新 skill：结构、描述、示例、辅助脚本。**

```
/write-a-skill
```

### `/writer`

**论文写作角色：只写论文、文档、Rebuttal，不写代码或部署。**

参数：`写什么？（描述写作任务）`

```
/writer
```

### `/zoom-out`

**跳出细节看全局：理解代码片段在整体架构中的位置。**

```
/zoom-out
```

---

*每个 skill 的完整文档见 `skills/<name>/SKILL.md`。*
