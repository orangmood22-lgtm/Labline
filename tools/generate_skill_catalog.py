#!/usr/bin/env python3
"""
tools/generate_skill_catalog.py — 自动生成 docs/SKILL_CATALOG.md

扫描 skills/*/SKILL.md 的 YAML frontmatter，按分类输出可搜索的 skill 目录。

用法：
    python3 tools/generate_skill_catalog.py

触发时机：
    - 手动执行
    - /framework-update 成功后自动执行
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# ─── 分类映射表（集中管理） ───────────────────────────────────────────────────

CATEGORY_MAP = {
    # 研究发现
    "idea-discovery": "研究发现",
    "idea-discovery-robot": "研究发现",
    "idea-creator": "研究发现",
    "research-lit": "研究发现",
    "comm-lit-review": "研究发现",
    "novelty-check": "研究发现",
    "research-review": "研究发现",
    "research-refine": "研究发现",

    # 搜索/数据源
    "arxiv": "搜索/数据源",
    "deepxiv": "搜索/数据源",
    "alphaxiv": "搜索/数据源",
    "semantic-scholar": "搜索/数据源",
    "openalex": "搜索/数据源",
    "gemini-search": "搜索/数据源",
    "exa-search": "搜索/数据源",

    # 实验
    "experiment-plan": "实验",
    "experiment-bridge": "实验",
    "experiment-audit": "实验",
    "experiment-queue": "实验",
    "run-experiment": "实验",
    "monitor-experiment": "实验",
    "analyze-results": "实验",
    "result-to-claim": "实验",
    "training-check": "实验",
    "ablation-planner": "实验",

    # 论文撰写
    "paper-writing": "论文撰写",
    "paper-plan": "论文撰写",
    "paper-write": "论文撰写",
    "auto-paper-improvement-loop": "论文撰写",
    "auto-review-loop": "论文撰写",
    "auto-review-loop-llm": "论文撰写",
    "auto-review-loop-minimax": "论文撰写",
    "claims-drafting": "论文撰写",
    "formula-derivation": "论文撰写",
    "writing-systems-papers": "论文撰写",
    "rebuttal": "论文撰写",
    "resubmit-pipeline": "论文撰写",

    # 论文演示
    "paper-slides": "论文演示",
    "paper-poster": "论文演示",
    "paper-talk": "论文演示",
    "slides-polish": "论文演示",

    # 图表/可视化
    "paper-figure": "图表/可视化",
    "paper-illustration": "图表/可视化",
    "paper-illustration-image2": "图表/可视化",
    "figure-spec": "图表/可视化",
    "figure-description": "图表/可视化",
    "mermaid-diagram": "图表/可视化",
    "pixel-art": "图表/可视化",
    "embodiment-description": "图表/可视化",

    # 审查/质量
    "kill-argument": "审查/质量",
    "citation-audit": "审查/质量",
    "proof-checker": "审查/质量",
    "proof-writer": "审查/质量",
    "research-refine-pipeline": "审查/质量",
    "paper-claim-audit": "审查/质量",

    # 论文编译
    "paper-compile": "论文撰写",

    # 专利/公文
    "patent-pipeline": "专利/公文",
    "patent-review": "专利/公文",
    "patent-novelty-check": "专利/公文",
    "prior-art-search": "专利/公文",
    "invention-structuring": "专利/公文",
    "jurisdiction-format": "专利/公文",
    "grant-proposal": "专利/公文",
    "specification-writing": "专利/公文",

    # 工具/同步
    "sync": "工具/同步",
    "framework-update": "工具/同步",
    "overleaf-sync": "工具/同步",
    "research-wiki": "工具/同步",
    "feishu-notify": "工具/同步",
    "feishu-session": "工具/同步",
    "qzcli": "工具/同步",
    "skill-dag-check": "工具/同步",

    # Pipeline/编排
    "leader": "Pipeline/编排",
    "research-pipeline": "Pipeline/编排",
    "init-research": "Pipeline/编排",
    "dse-loop": "Pipeline/编排",
    "meta-optimize": "Pipeline/编排",

    # 计算资源
    "vast-gpu": "计算资源",
    "serverless-modal": "计算资源",
    "system-profile": "计算资源",

    # 开发工具（mattpocock）
    "caveman": "开发工具",
    "tdd": "开发工具",
    "diagnose": "开发工具",
    "zoom-out": "开发工具",
    "grill-me": "开发工具",
    "grill-with-docs": "开发工具",
    "handoff": "开发工具",
    "git-guardrails": "开发工具",
    "to-issues": "开发工具",
    "to-prd": "开发工具",
    "review": "开发工具",
    "write-a-skill": "开发工具",
    "coder": "开发工具",
    "deployer": "开发工具",
    "writer": "开发工具",
}

# 跨类引用（skill 主类之外也常被哪些方向使用）
ALSO_USED_BY = {
    "arxiv": ["论文撰写"],
    "semantic-scholar": ["论文撰写"],
    "experiment-plan": ["Pipeline/编排"],
    "experiment-audit": ["审查/质量"],
    "result-to-claim": ["论文撰写"],
    "mermaid-diagram": ["论文撰写", "专利/公文"],
    "figure-spec": ["论文撰写"],
    "sync": ["Pipeline/编排"],
    "formula-derivation": ["审查/质量"],
    "novelty-check": ["专利/公文"],
    "research-wiki": ["研究发现"],
    "proof-checker": ["论文撰写"],
    "ablation-planner": ["论文撰写"],
}

# 分类排序
CATEGORY_ORDER = [
    "Pipeline/编排",
    "研究发现",
    "搜索/数据源",
    "实验",
    "论文撰写",
    "论文演示",
    "图表/可视化",
    "审查/质量",
    "专利/公文",
    "工具/同步",
    "计算资源",
    "开发工具",
    "未分类",
]

# 示例命令（手动维护高频 skill，其余自动用 argument-hint 生成）
EXAMPLES = {
    "leader": '/leader "基于频域特征的增量目标检测"',
    "init-research": '/init-research my-project --direction "研究方向" --server 4090x4',
    "research-pipeline": '/research-pipeline "factorized gap in discrete diffusion LMs"',
    "sync": "/sync push --message \"完成 backbone\"",
    "framework-update": "/framework-update",
    "idea-discovery": '/idea-discovery "增量目标检测"',
    "experiment-plan": "/experiment-plan",
    "experiment-bridge": "/experiment-bridge",
    "paper-writing": '/paper-writing --effort balanced --assurance submission',
    "rebuttal": '/rebuttal "paper/ + reviews" --venue ICML --character-limit 5000',
    "arxiv": '/arxiv "few-shot incremental learning"',
    "novelty-check": '/novelty-check "用频域特征做增量学习的原型对齐"',
    "run-experiment": "/run-experiment --server 4090x4 --script code/train.py",
    "paper-slides": '/paper-slides "paper/"',
    "auto-paper-improvement-loop": '/auto-paper-improvement-loop "paper/" --max-rounds 3',
    "kill-argument": '/kill-argument "paper/"',
    "citation-audit": '/citation-audit "paper/"',
    "research-wiki": "/research-wiki init",
    "monitor-experiment": "/monitor-experiment --server 4090x4",
    "overleaf-sync": "/overleaf-sync pull",
    "vast-gpu": "/vast-gpu --min-vram 24 --max-cost 0.5",
    "grant-proposal": '/grant-proposal "研究方向" --type NSFC-青年',
    "patent-pipeline": '/patent-pipeline "发明内容描述"',
    "meta-optimize": "/meta-optimize",
    "caveman": "/caveman",
    "tdd": "/tdd",
    "diagnose": "/diagnose",
    "zoom-out": "/zoom-out",
    "grill-me": '/grill-me "频域特征模块设计方案"',
    "grill-with-docs": '/grill-with-docs "实验方案设计"',
    "handoff": "/handoff",
    "git-guardrails": "/git-guardrails",
    "to-issues": "/to-issues",
    "to-prd": "/to-prd",
    "review": "/review main",
    "write-a-skill": "/write-a-skill",
    "coder": "/coder",
    "deployer": "/deployer",
    "skill-dag-check": "/skill-dag-check",
    "feishu-session": "/feishu-session report leader-phone",
    "writer": "/writer",
}


def parse_frontmatter(filepath: Path) -> Optional[dict]:
    """Parse YAML frontmatter from SKILL.md (between --- delimiters)."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    # Match frontmatter block
    match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not match:
        return None

    fm_text = match.group(1)
    result = {}

    # Simple YAML-like parsing (avoid pyyaml dependency for portability)
    for line in fm_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Handle key: value (single line)
        m = re.match(r'^(\w[\w-]*):\s*(.+)$', line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            result[key] = val

    # Multi-line description (handle > continuation)
    if 'description' not in result:
        desc_match = re.search(r'description:\s*[>|]?\s*\n\s+(.+?)(?:\n\w|\n---)', fm_text + '\n---', re.DOTALL)
        if desc_match:
            result['description'] = ' '.join(desc_match.group(1).split())

    return result if result.get('name') else None


def get_first_paragraph(filepath: Path) -> str:
    """Get first non-frontmatter, non-heading paragraph as fallback description."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return ""

    # Strip frontmatter
    text = re.sub(r'^---.*?---\s*', '', text, count=1, flags=re.DOTALL)

    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        return line[:200]
    return ""


def generate_catalog(skills_dir: Path, output_path: Path):
    """Scan all skills and generate catalog markdown."""

    # Collect skill data
    skills = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        name = skill_dir.name
        fm = parse_frontmatter(skill_md)

        if fm:
            desc = fm.get('description', '')
            arg_hint = fm.get('argument-hint', '')
        else:
            desc = get_first_paragraph(skill_md)
            arg_hint = ''

        # Truncate long descriptions
        if len(desc) > 150:
            desc = desc[:147] + "..."

        category = CATEGORY_MAP.get(name, "未分类")
        also = ALSO_USED_BY.get(name, [])
        example = EXAMPLES.get(name, f"/{name} {arg_hint}" if arg_hint else f"/{name}")

        skills.append({
            "name": name,
            "description": desc,
            "category": category,
            "argument_hint": arg_hint,
            "also_used_by": also,
            "example": example,
        })

    # Group by category
    by_category = {}
    for s in skills:
        cat = s["category"]
        by_category.setdefault(cat, []).append(s)

    # Generate markdown
    lines = []
    lines.append("# ARIS Skill Catalog")
    lines.append("")
    lines.append(f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}。共 {len(skills)} 个 skill，{len(by_category)} 个分类。")
    lines.append(">")
    lines.append("> 生成命令：`python3 tools/generate_skill_catalog.py`")
    lines.append("")
    lines.append("## 目录")
    lines.append("")

    for cat in CATEGORY_ORDER:
        if cat in by_category:
            anchor = cat.lower().replace("/", "").replace(" ", "-")
            count = len(by_category[cat])
            lines.append(f"- [{cat}](#{anchor})（{count}）")
    lines.append("")

    # Category sections
    for cat in CATEGORY_ORDER:
        if cat not in by_category:
            continue

        lines.append(f"---")
        lines.append("")
        lines.append(f"## {cat}")
        lines.append("")

        for s in sorted(by_category[cat], key=lambda x: x["name"]):
            lines.append(f"### `/{s['name']}`")
            lines.append("")
            lines.append(f"**{s['description']}**")
            lines.append("")

            if s["argument_hint"]:
                lines.append(f"参数：`{s['argument_hint']}`")
                lines.append("")

            if s["also_used_by"]:
                tags = "、".join(s["also_used_by"])
                lines.append(f"也用于：{tags}")
                lines.append("")

            lines.append(f"```")
            lines.append(s["example"])
            lines.append(f"```")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*每个 skill 的完整文档见 `skills/<name>/SKILL.md`。*")
    lines.append("")

    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"✅ Generated {output_path} ({len(skills)} skills, {len(by_category)} categories)")


def main():
    # Find framework root
    script_dir = Path(__file__).resolve().parent
    framework_dir = script_dir.parent

    skills_dir = framework_dir / "skills"
    output_path = framework_dir / "docs" / "SKILL_CATALOG.md"

    if not skills_dir.is_dir():
        print(f"ERROR: skills/ not found at {skills_dir}", file=sys.stderr)
        sys.exit(1)

    generate_catalog(skills_dir, output_path)


if __name__ == "__main__":
    main()
