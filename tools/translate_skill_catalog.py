#!/usr/bin/env python3
"""
tools/translate_skill_catalog.py — 从英文 SKILL_CATALOG.md 生成中文版 SKILL_CATALOG_CN.md

用法：
    python3 tools/generate_skill_catalog.py     # 先生成英文版
    python3 tools/translate_skill_catalog.py     # 再生成中文版

中文翻译固化在本文件的映射表中（AI 翻译初稿 + 人工校对）。
未收录的 skill fallback 到英文原文。
"""

import re
from pathlib import Path
from datetime import datetime

# ─── 中文描述映射表（AI 翻译 + 人工校对） ────────────────────────────────────

CN_DESC = {
    "ablation-planner": "当主结果支撑论文主张时，从审稿人视角设计消融实验。",
    "alphaxiv": "通过 AlphaXiv 摘要快速查询单篇论文，支持分级来源回退。",
    "analyze-results": "分析 ML 实验结果，计算统计量并生成对比表和洞见。",
    "arxiv": "从 arXiv 搜索、下载并总结学术论文。",
    "auto-paper-improvement-loop": "自动迭代：审稿→修复→复审，直到达标或轮次耗尽。",
    "auto-review-loop": "使用 Codex GPT 审稿人的多轮自动审稿循环。",
    "auto-review-loop-llm": "使用 LLM API（非 Codex）的多轮自动审稿循环。",
    "auto-review-loop-minimax": "使用 MiniMax API 的多轮自动审稿循环。",
    "citation-audit": "审查论文草稿中引用的完整性与正确性。",
    "claims-drafting": "根据实验证据起草并验证研究主张。",
    "comm-lit-review": "跨多个来源进行系统性社区文献综述。",
    "deepxiv": "通过 DeepXiv 对论文进行结构化深度分析。",
    "dse-loop": "面向计算机体系结构与 EDA 的自动设计空间探索循环。",
    "embodiment-description": "为专利申请生成正式实施例描述。",
    "exa-search": "通过 Exa AI 搜索引擎检索研究论文。",
    "experiment-audit": "独立审计实验完整性：检查假 GT、刷分和虚假结果。",
    "experiment-bridge": "将实验计划转换为可执行代码实现。",
    "experiment-plan": "设计严谨实验计划，声明预期并设置差异断言。",
    "experiment-queue": "通过 SSH 管理多种子/多配置 ML 实验队列，支持 OOM 重试。",
    "feishu-notify": "向飞书/Lark 发送状态更新通知。",
    "feishu-session": "管理飞书/Lark 远程 Codex 或 Claude Code 会话；默认使用 lark-channel-bridge，Labline 自研 runner 仅作审计/合并 fallback。",
    "figure-description": "处理专利附图并生成正式附图说明。",
    "figure-spec": "生成可编辑 SVG 的确定性出版级架构/流程/管线图。",
    "formula-derivation": "整理并推导研究公式，生成可用于论文的推导包。",
    "framework-update": "一键更新 Labline 框架：git pull + 重建 symlinks。",
    "gemini-search": "通过 Gemini 搜索论文，用于广泛文献发现。",
    "grant-proposal": "根据研究想法起草结构化基金申请书（国自然/NSF/ERC 等）。",
    "idea-creator": "根据宽泛方向生成并排序研究想法。",
    "idea-discovery": "完整想法发现流程：文献调研→生成想法→新颖性检查→评审。",
    "idea-discovery-robot": "面向机器人与具身 AI 的想法发现流程。",
    "init-research": "一键创建新科研项目：mkdir → git init → install skills → CLAUDE.md → project.yaml。",
    "invention-structuring": "将原始发明想法整理为正式发明披露文档。",
    "jurisdiction-format": "按特定法域（CN/US/EP/JP/KR）格式化专利权利要求。",
    "kill-argument": "对抗性审查：模拟最严厉审稿人拒稿，判断论文是否已回应。",
    "leader": "三边架构总编排：自动派生 Executor、调 Reviewer，一个窗口全流程。",
    "planner": "计划角色：产出计划草案、依赖拆解、风险图和 checkpoint。",
    "reviewer": "独立 Reviewer 角色：从原始输入审查计划、代码、实验、claim 或论文。",
    "runtime-task-protocol": "派生角色运行时协议：统一 status、终态和 superseded/resolved 事件。",
    "mermaid-diagram": "生成 Mermaid 图表：架构图、流程图、数据流图。",
    "meta-optimize": "分析 Labline 使用日志，提出 SKILL.md 和工作流优化建议。",
    "monitor-experiment": "监控正在运行的 ML 实验，检查进度并检测问题。",
    "novelty-check": "对比现有文献验证研究想法的新颖性。",
    "openalex": "通过 OpenAlex API 搜索学术论文，含引用量和元数据。",
    "overleaf-sync": "本地项目与 Overleaf 双向同步。",
    "paper-claim-audit": "审计论文主张与实际实验证据的一致性。",
    "paper-compile": "编译 LaTeX 论文并检查错误。",
    "paper-figure": "为论文生成出版级图表。",
    "paper-illustration": "使用 AI 为论文生成插图。",
    "paper-illustration-image2": "使用图生图 AI 模型生成论文插图。",
    "paper-plan": "规划论文结构和大纲。",
    "paper-poster": "从论文生成 A0 学术海报。",
    "paper-slides": "从论文生成 Beamer/PPTX 演示幻灯片。",
    "paper-talk": "端到端学术会议报告 pipeline。",
    "paper-write": "撰写论文单个章节。",
    "paper-writing": "完整论文撰写 pipeline（6+ 阶段）。",
    "patent-novelty-check": "对比现有技术检查专利新颖性。",
    "patent-pipeline": "从想法到可提交文件的完整专利申请 pipeline。",
    "patent-review": "审查并改进专利申请质量。",
    "pixel-art": "生成像素风格插图。",
    "prior-art-search": "检索与专利权利要求相关的现有技术。",
    "proof-checker": "数学证明严格验证与修复，跨模型交叉审查。",
    "proof-writer": "为 ML/AI 理论撰写严格数学证明。",
    "qzcli": "管理启智平台 GPU 计算任务（提交/停止/监控）。",
    "rebuttal": "解析审稿意见，在字数限制内起草回复并管理后续轮次。",
    "research-lit": "搜索并分析研究论文，查找相关工作并总结关键思想。",
    "research-pipeline": "全自动研究 pipeline：想法发现→实现→自动审稿→论文撰写。",
    "research-refine": "通过 GPT 迭代审查将模糊研究方向细化为聚焦方案。",
    "research-refine-pipeline": "端到端 pipeline：串联 research-refine 和 experiment-plan。",
    "research-review": "通过 Codex MCP 获取 GPT 对研究的深度批判性评审。",
    "research-wiki": "持久化研究知识库：论文、想法、实验、主张及其关系。",
    "resubmit-pipeline": "将已打磨论文改投到其他会议/期刊（纯文字调整）。",
    "result-to-claim": "判断实验结果支持哪些主张，缺少哪些证据。",
    "run-experiment": "在本地/远程/Vast.ai/Modal GPU 上部署并运行 ML 实验。",
    "semantic-scholar": "通过 Semantic Scholar API 搜索已发表论文，含引用量。",
    "serverless-modal": "在 Modal 无服务器平台运行 GPU 任务：训练/微调/推理。",
    "slides-polish": "对学术演讲幻灯片逐页 Codex 审查 + 定向修复。",
    "specification-writing": "根据权利要求和发明披露撰写完整专利说明书。",
    "sync": "一键同步科研项目：git add/commit/push/pull + 远程部署。",
    "system-profile": "性能分析：脚本/GPU/内存/互连，生成结构化报告。",
    "training-check": "定期检查 WandB 指标，及早发现训练问题（NaN/损失发散/GPU 空闲）。",
    "vast-gpu": "在 vast.ai 上租用、管理和销毁 GPU 实例。",
    "writing-systems-papers": "系统论文段落级结构蓝图（OSDI/SOSP/ASPLOS 等）。",
    "caveman": "精简回复模式：砍掉废话，保留技术准确度，省 75% token。",
    "tdd": "测试驱动开发：红→绿→重构循环，先写测试再写实现。",
    "diagnose": "系统化 bug 诊断：复现→最小化→假设→验证→修复→回归测试。",
    "zoom-out": "跳出细节看全局：理解代码片段在整体架构中的位置。",
    "grill-me": "对你的方案进行压力测试式提问，逐个解决设计决策。",
    "grill-with-docs": "grill-me 升级版：讨论过程中自动更新项目文档和 ADR。",
    "handoff": "生成交接文档，让新 agent/新会话能无缝接续当前工作。",
    "git-guardrails": "给 Claude Code 装 git 安全钩子，拦截 force push 等危险操作。",
    "to-issues": "把计划/PRD 拆成独立可执行的 Issue（垂直切片）。",
    "to-prd": "把当前对话上下文转化为正式 PRD 文档。",
    "review": "双轴代码审查：规范合规性 + 需求实现度，并行评估。",
    "write-a-skill": "引导创建新 skill：结构、描述、示例、辅助脚本。",
    "coder": "代码实现角色：只写代码、测试、重构，不做部署或论文写作。",
    "deployer": "部署角色：只做 SSH 同步、启动训练、监控实验、收集结果。",
    "skill-dag-check": "修改 skill 前检查依赖影响，列出上游/下游关系。",
    "writer": "论文写作角色：只写论文、文档、Rebuttal，不写代码或部署。",
}

CN_ARG_HINT = {
    "ablation-planner": "方法描述或主张",
    "alphaxiv": "arXiv ID 或 URL",
    "analyze-results": "结果路径或描述",
    "arxiv": "查询词或 arXiv ID",
    "auto-paper-improvement-loop": "论文目录 [--max-rounds 轮数]",
    "citation-audit": "论文目录",
    "comm-lit-review": "研究主题",
    "deepxiv": "arXiv ID 或 URL",
    "dse-loop": "任务描述",
    "embodiment-description": "实施例目录或列表",
    "exa-search": "搜索查询",
    "experiment-queue": "manifest 或 grid spec",
    "feishu-notify": "消息文本",
    "figure-description": "附图目录或附图列表",
    "figure-spec": "图表描述",
    "formula-derivation": "问题/目标/当前公式或笔记",
    "framework-update": "[--force] [--dry-run]",
    "gemini-search": "搜索查询",
    "grant-proposal": "研究方向 -- 基金类型",
    "idea-creator": "研究方向",
    "idea-discovery": "研究方向",
    "idea-discovery-robot": "机器人方向",
    "init-research": "项目名 [--size full|small] [--server SSH别名] [--remote GIT_URL] [--direction 研究方向]",
    "invention-structuring": "发明描述",
    "kill-argument": "论文目录",
    "leader": "研究方向或计划路径",
    "planner": "规划任务描述",
    "reviewer": "审查对象、rubric 或目标",
    "runtime-task-protocol": "角色、task id 或状态场景",
    "mermaid-diagram": "图表描述",
    "meta-optimize": "目标 skill 或 all",
    "novelty-check": "想法描述",
    "openalex": "搜索查询",
    "paper-figure": "图表描述",
    "paper-illustration": "描述",
    "paper-poster": "论文目录",
    "paper-slides": "论文目录",
    "paper-talk": "论文目录",
    "patent-novelty-check": "专利权利要求或描述",
    "patent-pipeline": "发明描述",
    "patent-review": "专利文档路径",
    "pixel-art": "描述",
    "prior-art-search": "专利权利要求或发明",
    "proof-checker": "tex 文件路径或证明描述",
    "proof-writer": "定理陈述和假设",
    "qzcli": "login|avail|list|create|stop|batch|status|watch",
    "rebuttal": "论文路径或评审包",
    "research-lit": "论文主题或 URL",
    "research-pipeline": "研究方向",
    "research-review": "主题或范围",
    "research-wiki": "子命令：init|ingest|sync|query|update|lint|stats",
    "resubmit-pipeline": "论文目录；目标会场",
    "result-to-claim": "实验描述或 WandB run",
    "run-experiment": "实验描述",
    "semantic-scholar": "查询词或论文 ID",
    "serverless-modal": "任务描述",
    "slides-polish": "幻灯片目录或 pptx",
    "specification-writing": "权利要求路径",
    "sync": "push|pull|deploy|status [--server 名称] [--message '提交信息']",
    "system-profile": "目标（如 train.py、gpu、pid 1234）",
    "training-check": "WandB run 路径",
    "vast-gpu": "任务描述或操作",
    "writing-systems-papers": "会场或章节",
}

# ─── 分类中文名（与 generate_skill_catalog.py 一致） ─────────────────────────

# 这些已经是中文了，但标题/框架文字需要翻译
FRAMEWORK_TEXT = {
    "title": "Labline Skill 目录（中文版）",
    "auto_generated": "自动生成于",
    "total_skills": "个 skill",
    "total_categories": "个分类",
    "gen_command": "生成命令",
    "params": "参数",
    "also_used_by": "也用于",
    "footer": "每个 skill 的完整文档见 `skills/<name>/SKILL.md`。",
    "toc": "目录",
}


def translate_catalog(en_path: Path, cn_path: Path):
    """Read EN catalog, replace with CN translations, output CN version."""
    if not en_path.exists():
        print(f"ERROR: {en_path} not found. Run generate_skill_catalog.py first.")
        return

    content = en_path.read_text("utf-8")

    # Replace title
    content = content.replace("# Labline Skill Catalog", f"# {FRAMEWORK_TEXT['title']}")

    # Replace auto-generated line
    content = re.sub(
        r'> 自动生成于 [\d-]+ [\d:]+。',
        f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}。",
        content,
    )
    content = content.replace(
        "生成命令：`python3 tools/generate_skill_catalog.py`",
        "生成命令：`python3 tools/translate_skill_catalog.py`",
    )

    # Replace each skill's description
    # Pattern: ### `/skill-name`\n\n**description**
    def replace_desc(m):
        skill_name = m.group(1)
        cn = CN_DESC.get(skill_name)
        if cn:
            return f'### `/{skill_name}`\n\n**{cn}**'
        return m.group(0)  # keep original

    content = re.sub(
        r'### `/([^`]+)`\n\n\*\*([^*]+)\*\*',
        replace_desc,
        content,
    )

    # Replace argument hints
    # Pattern: 参数：`hint`
    def replace_arg(m):
        # Find which skill this belongs to by looking backwards
        return m.group(0)  # We'll handle this differently

    # More targeted: replace argument hints by finding skill context
    lines = content.split('\n')
    current_skill = None
    new_lines = []
    for line in lines:
        # Track current skill
        sm = re.match(r'^### `/([\w-]+)`', line)
        if sm:
            current_skill = sm.group(1)

        # Replace argument hint line
        if current_skill and line.startswith('参数：`'):
            cn_arg = CN_ARG_HINT.get(current_skill)
            if cn_arg:
                line = f'参数：`{cn_arg}`'

        new_lines.append(line)

    content = '\n'.join(new_lines)

    # Replace footer
    content = content.replace(
        "*每个 skill 的完整文档见 `skills/<name>/SKILL.md`。*",
        f"*{FRAMEWORK_TEXT['footer']}*",
    )

    cn_path.write_text(content, "utf-8")
    print(f"✅ Generated {cn_path}")


def main():
    script_dir = Path(__file__).resolve().parent
    framework_dir = script_dir.parent

    en_path = framework_dir / "docs" / "SKILL_CATALOG.md"
    cn_path = framework_dir / "docs" / "SKILL_CATALOG_CN.md"

    translate_catalog(en_path, cn_path)


if __name__ == "__main__":
    main()
