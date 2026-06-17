# ARIS Skill Catalog

> 自动生成于 2026-06-17 11:11。共 95 个 skill，12 个分类。
>
> 生成命令：`python3 tools/generate_skill_catalog.py`

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
- [开发工具](#开发工具)（15）

---

## Pipeline/编排

### `/dse-loop`

**Autonomous design space exploration loop for computer architecture and EDA. Runs a program, analyzes results, tunes parameters, and iterates until ...**

参数：`[task-description — include program, parameters, objective, and timeout]`

```
/dse-loop [task-description — include program, parameters, objective, and timeout]
```

### `/init-research`

**一键创建新科研项目。自动: mkdir → git init → install skills → CLAUDE.md → project.yaml → push to git remote。**

参数：`项目名 [--size full|small] [--server SSH别名] [--remote GIT_URL] [--direction 研究方向]`

```
/init-research my-project --direction "研究方向" --server 4090x4
```

### `/leader`

**三边架构总编排：自动派生 Coder/Deployer/Writer，并调独立 Reviewer。一个窗口全流程。**

参数：`[research-direction-or-plan-path]`

```
/leader "基于频域特征的增量目标检测"
```

### `/meta-optimize`

**Analyze ARIS usage logs and propose optimizations to SKILL.md files, reviewer prompts, and workflow defaults. Outer-loop harness optimization inspi...**

参数：`[target-skill-or-all]`

```
/meta-optimize
```

### `/research-pipeline`

**Full research pipeline: Workflow 1 (idea discovery) → implementation → Workflow 2 (auto review loop) → Workflow 3 (paper writing, optional). Goes f...**

参数：`[research-direction]`

```
/research-pipeline "factorized gap in discrete diffusion LMs"
```

---

## 研究发现

### `/comm-lit-review`

**Communications-domain literature review with Claude-style knowledge-base-first retrieval. Use when the task is about communications, wireless, netw...**

```
/comm-lit-review
```

### `/idea-creator`

**Generate and rank research ideas given a broad direction. Use when user says "找idea", "brainstorm ideas", "generate research ideas", "what can we w...**

参数：`[research-direction]`

```
/idea-creator [research-direction]
```

### `/idea-discovery`

**Workflow 1: Full idea discovery pipeline. Orchestrates research-lit → idea-creator → novelty-check → research-review to go from a broad research di...**

参数：`[research-direction]`

```
/idea-discovery "增量目标检测"
```

### `/idea-discovery-robot`

**Workflow 1 adaptation for robotics and embodied AI. Orchestrates robotics-aware literature survey, idea generation, novelty check, and critical rev...**

参数：`[robotics-direction]`

```
/idea-discovery-robot [robotics-direction]
```

### `/novelty-check`

**Verify research idea novelty against recent literature. Use when user says "查新", "novelty check", "有没有人做过", "check novelty", or wants to verify a r...**

参数：`[method-or-idea-description]`

也用于：专利/公文

```
/novelty-check "用频域特征做增量学习的原型对齐"
```

### `/research-lit`

**Search and analyze research papers, find related work, summarize key ideas. Use when user says "find papers", "related work", "literature review", ...**

参数：`[paper-topic-or-url]`

```
/research-lit [paper-topic-or-url]
```

### `/research-refine`

**Turn a vague research direction into a problem-anchored, elegant, frontier-aware, implementation-oriented method plan via iterative GPT-5.4 review....**

```
/research-refine
```

### `/research-review`

**Get a deep critical review of research from GPT via Codex MCP. Use when user says "review my research", "help me review", "get external review", or...**

参数：`[topic-or-scope]`

```
/research-review [topic-or-scope]
```

---

## 搜索/数据源

### `/alphaxiv`

**Quick single-paper lookup via AlphaXiv LLM-optimized summaries with tiered source fallback. Use when user says "explain this paper", "summarize pap...**

参数：`[arxiv-id-or-url]`

```
/alphaxiv [arxiv-id-or-url]
```

### `/arxiv`

**Search, download, and summarize academic papers from arXiv. Use when user says "search arxiv", "download paper", "fetch arxiv", "arxiv search", "ge...**

参数：`[query-or-arxiv-id]`

也用于：论文撰写

```
/arxiv "few-shot incremental learning"
```

### `/deepxiv`

**Search and progressively read open-access academic papers through DeepXiv. Use when the user wants layered paper access, section-level reading, tre...**

参数：`[query-or-paper-id]`

```
/deepxiv [query-or-paper-id]
```

### `/exa-search`

**AI-powered web search via Exa with content extraction. Use when user says "exa search", "web search with content", "find similar pages", or needs b...**

参数：`[search-query-or-url]`

```
/exa-search [search-query-or-url]
```

### `/gemini-search`

**Search research papers via Gemini for broad literature discovery. Use when user says "gemini search", "gemini papers", "search with gemini", or wan...**

参数：`[search-query]`

```
/gemini-search [search-query]
```

### `/openalex`

**Search academic papers via OpenAlex API for open citation data, institutional affiliations, and funding information. Use when user says "openalex s...**

参数：`[search-query]`

```
/openalex [search-query]
```

### `/semantic-scholar`

**Search published venue papers (IEEE, ACM, Springer, etc.) via Semantic Scholar API. Complements /arxiv (preprints) with citation counts, venue meta...**

参数：`query-or-paper-id`

也用于：论文撰写

```
/semantic-scholar query-or-paper-id
```

---

## 实验

### `/ablation-planner`

**Use when main results pass result-to-claim (claim_supported=yes or partial) and ablation studies are needed for paper submission. Codex designs abl...**

参数：`[method-description-or-claim]`

也用于：论文撰写

```
/ablation-planner [method-description-or-claim]
```

### `/analyze-results`

**Analyze ML experiment results, compute statistics, generate comparison tables and insights. Use when user says "analyze results", "compare", or nee...**

参数：`[results-path-or-description]`

```
/analyze-results [results-path-or-description]
```

### `/experiment-audit`

**Audit experiment integrity before claiming results. Uses cross-model review (GPT-5.4) to check for fake ground truth, score normalization fraud, ph...**

参数：`[experiment-dir-or-results-path]`

也用于：审查/质量

```
/experiment-audit [experiment-dir-or-results-path]
```

### `/experiment-bridge`

**Workflow 1.5: Bridge between idea discovery and auto review. Reads EXPERIMENT_PLAN.md, implements experiment code, deploys to GPU, collects initial...**

参数：`[experiment-plan-path-or-topic]`

```
/experiment-bridge
```

### `/experiment-plan`

**Turn a refined research proposal or method idea into a detailed, claim-driven experiment roadmap. Use after `research-refine`, or when the user ask...**

也用于：Pipeline/编排

```
/experiment-plan
```

### `/experiment-queue`

**SSH job queue for multi-seed/multi-config ML experiments with OOM-aware retry, stale-screen cleanup, and wave-transition race prevention. Use when ...**

参数：`[manifest-or-grid-spec]`

```
/experiment-queue [manifest-or-grid-spec]
```

### `/monitor-experiment`

**Monitor running experiments, check progress, collect results. Use when user says "check results", "is it done", "monitor", or wants experiment output.**

参数：`[server-alias or screen-name]`

```
/monitor-experiment --server 4090x4
```

### `/result-to-claim`

**Use when experiments complete to judge what claims the results support, what they don't, and what evidence is still missing. Codex MCP evaluates re...**

参数：`[experiment-description-or-wandb-run]`

也用于：论文撰写

```
/result-to-claim [experiment-description-or-wandb-run]
```

### `/run-experiment`

**Deploy and run ML experiments on local, remote, Vast.ai, or Modal serverless GPU. Use when user says "run experiment", "deploy to server", "跑实验", o...**

参数：`[experiment-description]`

```
/run-experiment --server 4090x4 --script code/train.py
```

### `/training-check`

**Periodically check WandB metrics during training to catch problems early (NaN, loss divergence, idle GPUs). Avoids wasting GPU hours on broken runs...**

参数：`[wandb-run-path]`

```
/training-check [wandb-run-path]
```

---

## 论文撰写

### `/auto-paper-improvement-loop`

**Autonomously improve a generated paper via GPT-5.4 xhigh review → implement fixes → recompile, for 2 rounds. Use when user says \"改论文\", \"improve ...**

参数：`[paper-directory] [— style-ref: <source>] [— edit-whitelist <path>]`

```
/auto-paper-improvement-loop "paper/" --max-rounds 3
```

### `/auto-review-loop`

**Autonomous multi-round research review loop. Repeatedly reviews via Codex MCP, implements fixes, and re-reviews until positive assessment or max ro...**

参数：`[topic-or-scope]`

```
/auto-review-loop [topic-or-scope]
```

### `/auto-review-loop-llm`

**Autonomous research review loop using any OpenAI-compatible LLM API. Configure via llm-chat MCP server or environment variables. Trigger with "auto...**

参数：`[topic-or-scope]`

```
/auto-review-loop-llm [topic-or-scope]
```

### `/auto-review-loop-minimax`

**Autonomous multi-round research review loop using MiniMax API. Use when you want to use MiniMax instead of Codex MCP for external review. Trigger w...**

参数：`[topic-or-scope]`

```
/auto-review-loop-minimax [topic-or-scope]
```

### `/claims-drafting`

**Draft patent claims for an invention. Use when user says \"撰写权利要求\", \"draft claims\", \"写权利要求书\", \"claim drafting\", or wants to create patent cl...**

参数：`[invention-disclosure-path]`

```
/claims-drafting [invention-disclosure-path]
```

### `/formula-derivation`

**Structures and derives research formulas when the user wants to 推导公式, build a theory line, organize assumptions, turn scattered equations into a co...**

参数：`[problem-goal-current-formulas-or-notes]`

也用于：审查/质量

```
/formula-derivation [problem-goal-current-formulas-or-notes]
```

### `/paper-compile`

**Compile LaTeX paper to PDF, fix errors, and verify output. Use when user says \"编译论文\", \"compile paper\", \"build PDF\", \"生成PDF\", or wants to co...**

参数：`[paper-directory]`

```
/paper-compile [paper-directory]
```

### `/paper-plan`

**Generate a structured paper outline from review conclusions and experiment results. Use when user says \"写大纲\", \"paper outline\", \"plan the paper...**

参数：`[topic-or-narrative-doc] [— style-ref: <source>]`

```
/paper-plan [topic-or-narrative-doc] [— style-ref: <source>]
```

### `/paper-write`

**Draft LaTeX paper section by section from an outline. Use when user says \"写论文\", \"write paper\", \"draft LaTeX\", \"开始写\", or wants to generate L...**

参数：`[venue-or-section] [— style-ref: <source>]`

```
/paper-write [venue-or-section] [— style-ref: <source>]
```

### `/paper-writing`

**Workflow 3: Full paper writing pipeline. Orchestrates paper-plan → paper-figure → figure-spec/paper-illustration/mermaid-diagram → paper-write → pa...**

参数：`[narrative-report-path-or-topic] [— style-ref: <source>]`

```
/paper-writing --effort balanced --assurance submission
```

### `/rebuttal`

**Workflow 4: Submission rebuttal pipeline. Parses external reviews, enforces coverage and grounding, drafts a safe text-only rebuttal under venue li...**

参数：`[paper-path-or-review-bundle]`

```
/rebuttal "paper/ + reviews" --venue ICML --character-limit 5000
```

### `/resubmit-pipeline`

**Workflow 5: orchestrate a text-only resubmit of a polished paper to a different venue under hard constraints (no new experiments, no bib edits, no ...**

参数：`[paper-base-dir] [— target-venue: <name>] [— review-corpus: <path>]`

```
/resubmit-pipeline [paper-base-dir] [— target-venue: <name>] [— review-corpus: <path>]
```

### `/writing-systems-papers`

**Paragraph-level structural blueprint for 10-12 page systems papers targeting OSDI, SOSP, ASPLOS, NSDI, and EuroSys. Provides page allocation, parag...**

参数：`[venue-or-section]`

```
/writing-systems-papers [venue-or-section]
```

---

## 论文演示

### `/paper-poster`

**Generate a conference poster (article + tcbposter LaTeX → A0/A1 PDF + editable PPTX + SVG) from a compiled paper. Use when user says \"做海报\", \"制作海...**

参数：`[paper-directory-or-venue] [— style-ref: <source>]`

```
/paper-poster [paper-directory-or-venue] [— style-ref: <source>]
```

### `/paper-slides`

**Generate conference presentation slides (beamer LaTeX → PDF + editable PPTX) from a compiled paper, with speaker notes and full talk script. Use wh...**

参数：`[paper-directory-or-talk-length] [— style-ref: <source>]`

```
/paper-slides "paper/"
```

### `/paper-talk`

**End-to-end conference talk pipeline: paper → slide outline → Beamer + PPTX → per-page polish → assurance checks (claim / citation / anonymity) → fi...**

参数：`[paper-dir] [— talk_type: oral | spotlight | poster-talk | invited] [— minutes: N] [— assurance: draft | polished | conference-ready] [— reference: <pdf>] [— style: generic | why-rf | <venue>] [— style-ref: <paper-source>] [— effort: lite | balanced | max | beast] [— anonymous]`

```
/paper-talk [paper-dir] [— talk_type: oral | spotlight | poster-talk | invited] [— minutes: N] [— assurance: draft | polished | conference-ready] [— reference: <pdf>] [— style: generic | why-rf | <venue>] [— style-ref: <paper-source>] [— effort: lite | balanced | max | beast] [— anonymous]
```

### `/slides-polish`

**Per-page Codex review + targeted python-pptx / Beamer fixes for academic talk slides. Use AFTER /paper-slides (or any externally generated PPTX/Bea...**

参数：`[slides-dir-or-pptx] — reference: <ref-pdf> [— style: generic | why-rf | neurips | icml | iclr | cvpr] [— effort: lite | balanced | max | beast] [— interactive]`

```
/slides-polish [slides-dir-or-pptx] — reference: <ref-pdf> [— style: generic | why-rf | neurips | icml | iclr | cvpr] [— effort: lite | balanced | max | beast] [— interactive]
```

---

## 图表/可视化

### `/embodiment-description`

**Write detailed embodiment descriptions for patent specifications. Use when user says \"撰写实施例\", \"write embodiment\", \"实施例描述\", \"detailed descrip...**

参数：`[claims-path-or-embodiment-details]`

```
/embodiment-description [claims-path-or-embodiment-details]
```

### `/figure-description`

**Process user-provided patent figures and generate formal drawing descriptions. Use when user says \"附图处理\", \"figure description\", \"附图说明\", \"dra...**

参数：`[figure-directory-or-figure-list]`

```
/figure-description [figure-directory-or-figure-list]
```

### `/figure-spec`

**Generate deterministic publication-quality architecture, workflow, and pipeline diagrams from structured JSON (FigureSpec) into editable SVG. Use w...**

参数：`[description-of-diagram]`

也用于：论文撰写

```
/figure-spec [description-of-diagram]
```

### `/mermaid-diagram`

**Generate Mermaid diagrams from user requirements. Saves .mmd and .md files to figures/ directory with syntax verification. Supports flowcharts, seq...**

参数：`[diagram description or requirements]`

也用于：论文撰写、专利/公文

```
/mermaid-diagram [diagram description or requirements]
```

### `/paper-figure`

**Generate publication-quality figures and tables from experiment results. Use when user says \"画图\", \"作图\", \"generate figures\", \"paper figures\"...**

参数：`[figure-plan-or-data-path]`

```
/paper-figure [figure-plan-or-data-path]
```

### `/paper-illustration`

**Generate publication-quality AI illustrations for academic papers using Gemini image generation. Creates architecture diagrams, method illustration...**

参数：`[description-or-method-file] [— style-ref: <source>]`

```
/paper-illustration [description-or-method-file] [— style-ref: <source>]
```

### `/paper-illustration-image2`

**Generate publication-quality academic illustrations through a local Codex app-server bridge that uses Codex native image generation. This is a sepa...**

参数：`[description-or-method-file]`

```
/paper-illustration-image2 [description-or-method-file]
```

### `/pixel-art`

**Generate pixel art SVG illustrations for READMEs, docs, or slides. Use when user says "画像素图", "pixel art", "make an SVG illustration", "README hero...**

参数：`[description of what to draw]`

```
/pixel-art [description of what to draw]
```

---

## 审查/质量

### `/citation-audit`

**Zero-context verification that every bibliographic entry in the paper is real, correctly attributed, and used in a context the cited paper actually...**

参数：`[paper-directory-or-bib-file] [--uncited] [— soft-only]`

```
/citation-audit "paper/"
```

### `/kill-argument`

**Two-thread adversarial review: a fresh reviewer constructs the strongest 200-word rejection memo, then a second fresh reviewer defends the paper po...**

参数：`[paper-directory]`

```
/kill-argument "paper/"
```

### `/paper-claim-audit`

**Zero-context verification that every number, comparison, and scope claim in the paper matches raw result files. Uses a fresh cross-model reviewer w...**

参数：`[paper-directory]`

```
/paper-claim-audit [paper-directory]
```

### `/proof-checker`

**Rigorous mathematical proof verification and fixing workflow. Reads a LaTeX proof, identifies gaps via cross-model review (Codex GPT-5.4 xhigh), fi...**

参数：`[path-to-tex-file or proof-description] [--deep-fix] [--restatement-check]`

也用于：论文撰写

```
/proof-checker [path-to-tex-file or proof-description] [--deep-fix] [--restatement-check]
```

### `/proof-writer`

**Writes rigorous mathematical proofs for ML/AI theory. Use when asked to prove a theorem, lemma, proposition, or corollary, fill in missing proof st...**

参数：`[theorem-statement-and-assumptions]`

```
/proof-writer [theorem-statement-and-assumptions]
```

### `/research-refine-pipeline`

**Run an end-to-end workflow that chains `research-refine` and `experiment-plan`. Use when the user wants a one-shot pipeline from vague research dir...**

```
/research-refine-pipeline
```

---

## 专利/公文

### `/grant-proposal`

**Draft a structured grant proposal from research ideas and literature. Supports KAKENHI (Japan), NSF (US), NSFC (China, including 面上/青年/优青/杰青/海外优青/重...**

参数：`[research-direction — grant-type] [— style-ref: <source>]`

```
/grant-proposal "研究方向" --type NSFC-青年
```

### `/invention-structuring`

**Structure a raw invention idea into a formal invention disclosure. Use when user says \"构建发明\", \"structure invention\", \"发明构建\", \"invention disc...**

参数：`[invention-description-or-brief-path]`

```
/invention-structuring [invention-description-or-brief-path]
```

### `/jurisdiction-format`

**Compile patent application into jurisdiction-specific filing format. Use when user says \"格式转换\", \"jurisdiction format\", \"国家格式\", \"compile pate...**

参数：`[patent-directory-or-jurisdiction]`

```
/jurisdiction-format [patent-directory-or-jurisdiction]
```

### `/patent-novelty-check`

**Assess patent novelty and non-obviousness against prior art. Use when user says \"专利查新\", \"patent novelty\", \"可专利性评估\", \"patentability check\", ...**

参数：`[invention-description-or-brief-path]`

```
/patent-novelty-check [invention-description-or-brief-path]
```

### `/patent-pipeline`

**Full patent drafting pipeline from invention description to jurisdiction-formatted filing documents. Supports CN (CNIPA), US (USPTO), EP (EPO). Sup...**

参数：`[invention-description — jurisdiction]`

```
/patent-pipeline "发明内容描述"
```

### `/patent-review`

**Get an external patent examiner review of a patent application. Use when user says \"专利审查\", \"patent review\", \"审查意见\", \"examiner review\", or w...**

参数：`[patent-directory-or-scope]`

```
/patent-review [patent-directory-or-scope]
```

### `/prior-art-search`

**Search patent databases and academic literature for prior art relevant to an invention. Use when user says \"现有技术检索\", \"prior art search\", \"专利检索...**

参数：`[invention-description-or-path]`

```
/prior-art-search [invention-description-or-path]
```

### `/specification-writing`

**Write the full patent specification from claims and invention disclosure. Use when user says \"撰写说明书\", \"write specification\", \"写说明书\", \"patent...**

参数：`[claims-path]`

```
/specification-writing [claims-path]
```

---

## 工具/同步

### `/feishu-notify`

**Send notifications to Feishu/Lark. Internal utility used by other skills, or manually via /feishu-notify. Supports push-only (webhook) and interact...**

参数：`[message-text]`

```
/feishu-notify [message-text]
```

### `/feishu-session`

**Manage Feishu/Lark remote Codex or Claude Code access, with lark-channel-bridge as the default transport and ARIS phone-session reports as legacy/f...**

参数：`[start|mark-seen|report|merge]`

```
/feishu-session report leader-phone
```

### `/framework-update`

**一键更新 ARIS 框架：git pull + 重建 symlinks。用户不需要懂 git。**

参数：`[--force] [--dry-run]`

```
/framework-update
```

### `/overleaf-sync`

**Two-way sync between a local paper directory and an Overleaf project via the Overleaf Git bridge (Premium feature). Lets you keep ARIS audit/edit w...**

参数：`[setup <project-id> | pull | push | status]`

```
/overleaf-sync pull
```

### `/qzcli`

**Manage GPU compute jobs on the Qizhi (启智) platform using qzcli — a kubectl-style CLI tool. Use when user says "qzcli", "启智平台", "submit job", "stop ...**

参数：`[login|avail|list|create|stop <job-id>|batch|status|watch]`

```
/qzcli [login|avail|list|create|stop <job-id>|batch|status|watch]
```

### `/research-wiki`

**Persistent research knowledge base that accumulates papers, ideas, experiments, claims, and their relationships across the entire research lifecycl...**

参数：`[subcommand: init|ingest|sync|query|update|lint|stats]`

也用于：研究发现

```
/research-wiki init
```

### `/skill-dag-check`

**Analyze skill dependency impact before modification. Shows upstream dependencies, downstream dependents, and artifact flow. Use when planning to mo...**

```
/skill-dag-check
```

### `/sync`

**一键同步科研项目：封装 git add/commit/push/pull + 远程部署。用户不需要懂 git。**

参数：`[push|pull|deploy|status] [--server NAME] [--message 'commit msg']`

也用于：Pipeline/编排

```
/sync push --message "完成 backbone"
```

---

## 计算资源

### `/serverless-modal`

**Run GPU workloads on Modal — training, fine-tuning, inference, batch processing. Zero-config serverless: no SSH, no Docker, auto scale-to-zero. Use...**

参数：`[task-description]`

```
/serverless-modal [task-description]
```

### `/system-profile`

**Profile a target (script, process, GPU, memory, interconnect) using external tools and code instrumentation. Produces structured performance report...**

参数：`<target, e.g. "train.py", "gpu", "pid 1234", "vllm serving">`

```
/system-profile <target, e.g. "train.py", "gpu", "pid 1234", "vllm serving">
```

### `/vast-gpu`

**Rent, manage, and destroy GPU instances on vast.ai. Use when user says \"rent gpu\", \"vast.ai\", \"rent a server\", \"cloud gpu\", or needs on-dem...**

参数：`[task-description or action]`

```
/vast-gpu --min-vram 24 --max-cost 0.5
```

---

## 开发工具

### `/caveman`

**>**

```
/caveman
```

### `/coder`

**代码实现角色 - 只写代码、测试、重构，不做部署、SSH、论文写作**

参数：`实现什么？（描述代码任务）`

```
/coder
```

### `/deployer`

**部署角色 - 只做 SSH 同步、启动训练、监控实验、收集结果，不写代码**

参数：`部署什么？（描述部署任务）`

```
/deployer
```

### `/diagnose`

**Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test. Use ...**

```
/diagnose
```

### `/git-guardrails`

**Set up Claude Code or Codex guardrails to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. Use when u...**

```
/git-guardrails
```

### `/grill-me`

**Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when us...**

```
/grill-me "频域特征模块设计方案"
```

### `/grill-with-docs`

**Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, ADRs) in...**

```
/grill-with-docs "实验方案设计"
```

### `/handoff`

**Compact the current conversation into a handoff document for another agent to pick up.**

参数：`What will the next session be used for?`

```
/handoff
```

### `/review`

**Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes — Standards (does the code follow this repo's documented...**

```
/review main
```

### `/tdd`

**Test-driven development with red-green-refactor loop. Use when user wants to build features or fix bugs using TDD, mentions "red-green-refactor", w...**

```
/tdd
```

### `/to-issues`

**Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices. Use when user want...**

```
/to-issues
```

### `/to-prd`

**Turn the current conversation context into a PRD and publish it to the project issue tracker. Use when user wants to create a PRD from the current ...**

```
/to-prd
```

### `/write-a-skill`

**Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new ...**

```
/write-a-skill
```

### `/writer`

**论文写作角色 - 只写论文、文档、Rebuttal，不写代码、不做部署**

参数：`写什么？（描述写作任务）`

```
/writer
```

### `/zoom-out`

**Tell the agent to zoom out and give broader context or a higher-level perspective. Use when you're unfamiliar with a section of code or need to und...**

```
/zoom-out
```

---

*每个 skill 的完整文档见 `skills/<name>/SKILL.md`。*
