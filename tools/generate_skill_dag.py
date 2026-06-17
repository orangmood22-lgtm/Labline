#!/usr/bin/env python3
"""Generate SKILL_DAG.yaml from SKILL.md frontmatter fields.

Reads all skills/<name>/SKILL.md files, extracts:
  - caller (leader/executor/any)
  - invokes (list of skill names this skill calls)
  - produces (list of artifact filenames)
  - consumes (list of artifact filenames)

Only frontmatter `invokes` creates formal graph edges. Body mentions such as
`/paper-write` are heuristic hints and are written to `inferred_mentions`.

Outputs docs/SKILL_DAG.yaml and validates the formal graph is acyclic.

Usage:
    python3 tools/generate_skill_dag.py [--check-only] [--mermaid] [--html]
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml


SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "SKILL_DAG.yaml"
MERMAID_PATH = Path(__file__).resolve().parent.parent / "docs" / "SKILL_DAG.mmd"
HTML_PATH = Path(__file__).resolve().parent.parent / "docs" / "skill-dag.html"
EXCLUDE = {
    "shared-references",
    "skills-codex",
    "skills-codex.bak",
    "skills-codex-claude-review",
    "skills-codex-gemini-review",
}


def parse_frontmatter(skill_path: Path) -> dict:
    """Extract YAML frontmatter from SKILL.md."""
    text = skill_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def as_list(value) -> list:
    """Normalize scalar/list frontmatter fields."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def scan_inferred_mentions(skill_path: Path) -> list:
    """Scan SKILL.md body for /skill-name or $skill-name mentions (heuristic)."""
    text = skill_path.read_text(encoding="utf-8")
    # Remove frontmatter
    text = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)
    # Find command-like mentions in code blocks or prose. These are not formal
    # dependency edges; many are examples, comparisons, or fallback suggestions.
    matches = re.findall(r"(?<![`\w])[/\$]([a-z][a-z0-9-]+)", text)
    return list(set(matches))


def build_graph(skills_dir: Path) -> dict:
    """Build the full skill graph."""
    nodes = {}
    all_skill_names = set()

    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name in EXCLUDE:
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        all_skill_names.add(d.name)

    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name in EXCLUDE:
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue

        fm = parse_frontmatter(skill_md)
        explicit_invokes = [
            str(s)
            for s in as_list(fm.get("invokes"))
            if str(s) in all_skill_names and str(s) != d.name
        ]
        inferred = [
            s
            for s in scan_inferred_mentions(skill_md)
            if s in all_skill_names and s != d.name and s not in explicit_invokes
        ]

        node = {
            "name": d.name,
            "caller": fm.get("caller", "unknown"),
            "description": fm.get("description", ""),
        }
        if explicit_invokes:
            node["invokes"] = sorted(set(explicit_invokes))
        if inferred:
            node["inferred_mentions"] = sorted(set(inferred))
        for key in ("platform", "status"):
            if fm.get(key):
                node[key] = fm[key]
        if fm.get("produces"):
            node["produces"] = as_list(fm["produces"])
        if fm.get("consumes"):
            node["consumes"] = as_list(fm["consumes"])
        if fm.get("examples"):
            node["examples"] = as_list(fm["examples"])

        nodes[d.name] = node

    return nodes


def detect_cycles(nodes: dict) -> list:
    """Detect cycles using DFS. Returns list of cycles found."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in nodes}
    cycles = []
    path = []

    def dfs(u):
        color[u] = GRAY
        path.append(u)
        for v in nodes[u].get("invokes", []):
            if v not in color:
                continue
            if color[v] == GRAY:
                cycle_start = path.index(v)
                cycles.append(path[cycle_start:] + [v])
            elif color[v] == WHITE:
                dfs(v)
        path.pop()
        color[u] = BLACK

    for name in nodes:
        if color[name] == WHITE:
            dfs(name)

    return cycles


def generate_mermaid(nodes: dict) -> str:
    """Generate Mermaid flowchart from DAG."""
    lines = ["graph TD"]
    # Style by caller
    leader_nodes = []
    executor_nodes = []
    any_nodes = []

    for name, node in sorted(nodes.items()):
        caller = node.get("caller", "unknown")
        if caller == "leader":
            leader_nodes.append(name)
        elif caller == "executor":
            executor_nodes.append(name)
        else:
            any_nodes.append(name)

        for target in node.get("invokes", []):
            lines.append(f"    {name} --> {target}")

    lines.append("")
    if leader_nodes:
        lines.append(f"    classDef leader fill:#ff9999,stroke:#cc0000")
        lines.append(f"    class {','.join(leader_nodes[:20])} leader")
    if executor_nodes:
        lines.append(f"    classDef executor fill:#99ccff,stroke:#0066cc")
        lines.append(f"    class {','.join(executor_nodes[:20])} executor")
    if any_nodes:
        lines.append(f"    classDef any fill:#99ff99,stroke:#009900")
        lines.append(f"    class {','.join(any_nodes[:20])} any")

    return "\n".join(lines)


def compute_invoked_by(nodes: dict) -> dict:
    """Compute reverse dependency: for each skill, which skills invoke it."""
    invoked_by = defaultdict(list)
    for name, node in nodes.items():
        for target in node.get("invokes", []):
            if target in nodes:
                invoked_by[target].append(name)
    return {k: sorted(v) for k, v in invoked_by.items()}


def compute_impact(nodes: dict, skill_name: str) -> dict:
    """Compute transitive impact of modifying a skill.

    Returns dict with:
      - direct_upstream: skills this one directly invokes
      - direct_downstream: skills that directly invoke this one
      - transitive_upstream: all skills this one depends on
      - transitive_downstream: all skills affected by changes to this one
    """
    if skill_name not in nodes:
        return {"error": f"Skill '{skill_name}' not found"}

    # BFS downstream (who depends on this skill, transitively)
    visited_down = set()
    queue = [skill_name]
    while queue:
        current = queue.pop(0)
        # Find skills that invoke current
        for name, node in nodes.items():
            if current in node.get("invokes", []) and name not in visited_down:
                visited_down.add(name)
                queue.append(name)

    # BFS upstream (what does this skill depend on, transitively)
    visited_up = set()
    queue = [skill_name]
    while queue:
        current = queue.pop(0)
        for target in nodes.get(current, {}).get("invokes", []):
            if target not in visited_up:
                visited_up.add(target)
                queue.append(target)

    invoked_by = compute_invoked_by(nodes)

    return {
        "skill": skill_name,
        "direct_upstream": nodes[skill_name].get("invokes", []),
        "direct_downstream": invoked_by.get(skill_name, []),
        "transitive_upstream": sorted(visited_up),
        "transitive_downstream": sorted(visited_down),
        "transitive_upstream_count": len(visited_up),
        "transitive_downstream_count": len(visited_down),
    }


def generate_html(nodes: dict, dag_data: dict) -> str:
    """Generate self-contained HTML visualization page using D3.js force layout."""
    invoked_by = compute_invoked_by(nodes)

    # Classify executor sub-roles
    EXECUTOR_CODER = {"tdd", "diagnose", "git-guardrails", "experiment-bridge", "ablation-planner"}
    EXECUTOR_DEPLOYER = {"run-experiment", "monitor-experiment", "sync", "framework-update", "system-profile", "vast-gpu", "serverless-modal", "experiment-queue", "training-check"}
    EXECUTOR_WRITER = {"paper-write", "paper-compile", "paper-figure", "paper-illustration", "paper-illustration-image2", "paper-slides", "paper-poster", "paper-talk", "rebuttal", "claims-drafting", "formula-derivation", "figure-spec", "figure-description", "mermaid-diagram", "pixel-art", "slides-polish", "proof-writer", "patent-pipeline", "grant-proposal", "invention-structuring", "specification-writing", "embodiment-description", "jurisdiction-format", "writing-systems-papers", "overleaf-sync", "paper-plan"}
    # Meta skills (role definitions, not tools)
    EXECUTOR_META = {"coder", "deployer", "writer"}

    # Build enriched nodes
    nodes_json = []
    for name in sorted(nodes.keys()):
        node = dict(nodes[name])
        node["invoked_by"] = invoked_by.get(name, [])
        caller = node.get("caller", "any")
        if caller == "leader":
            node["layer"] = "orchestration"
        elif caller == "reviewer":
            node["layer"] = "reviewer"
        elif caller == "executor":
            if name in EXECUTOR_META:
                node["layer"] = "executor-meta"
            elif name in EXECUTOR_CODER:
                node["layer"] = "executor-coder"
            elif name in EXECUTOR_DEPLOYER:
                node["layer"] = "executor-deployer"
            elif name in EXECUTOR_WRITER:
                node["layer"] = "executor-writer"
            else:
                node["layer"] = "executor"
        else:
            node["layer"] = "tools"
        nodes_json.append(node)
    nodes_json_str = json.dumps(nodes_json, ensure_ascii=False, indent=2)

    # Build edges
    edges_json = []
    for name in sorted(nodes.keys()):
        for target in nodes[name].get("invokes", []):
            if target in nodes:
                edges_json.append({"source": name, "target": target})
    edges_json_str = json.dumps(edges_json, ensure_ascii=False, indent=2)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARIS Skill DAG</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
:root {{
  --bg: #fafafa; --surface: #ffffff; --surface2: #f5f5f7; --border: #d2d2d7;
  --text: #1d1d1f; --text2: #6e6e73; --text3: #86868b; --accent: #0071e3;
  --orchestration: #bf5af2; --reviewer: #ff6b6b; --exec-coder: #0071e3; --exec-deployer: #30d158;
  --exec-writer: #ff9500; --exec-meta: #8b5cf6; --exec-other: #64d2ff; --tools: #8e8e93;
  --radius: 12px; --shadow: 0 2px 8px rgba(0,0,0,0.04);
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif; background:var(--bg); color:var(--text); -webkit-font-smoothing:antialiased; }}
#nav {{ position:sticky; top:0; z-index:100; background:rgba(250,250,250,0.8); backdrop-filter:saturate(180%) blur(20px); border-bottom:1px solid var(--border); padding:12px 32px; display:flex; align-items:center; gap:20px; }}
#nav h1 {{ font-size:18px; font-weight:600; letter-spacing:-0.02em; }}
#nav h1 span {{ color:var(--accent); }}
#stats {{ display:flex; gap:16px; font-size:12px; color:var(--text3); font-weight:500; }}
#stats b {{ color:var(--text); font-weight:600; }}
#toolbar {{ padding:10px 32px; background:var(--surface); border-bottom:1px solid var(--border); display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
#search {{ padding:7px 14px; border-radius:8px; border:1px solid var(--border); background:var(--surface2); color:var(--text); width:260px; font-size:13px; font-family:inherit; transition:all .2s; }}
#search:focus {{ outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(0,113,227,0.15); }}
.btn {{ padding:5px 14px; border-radius:20px; border:1px solid var(--border); background:var(--surface); color:var(--text2); cursor:pointer; font-size:12px; font-weight:500; font-family:inherit; transition:all .2s; }}
.btn:hover {{ border-color:var(--accent); color:var(--accent); }}
.btn.active {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
.btn-group {{ display:flex; gap:4px; }}
.btn-group .btn {{ border-radius:0; }}
.btn-group .btn:first-child {{ border-radius:20px 0 0 20px; }}
.btn-group .btn:last-child {{ border-radius:0 20px 20px 0; }}
#main {{ display:flex; height:calc(100vh - 98px); }}
#graph {{ flex:1; background:var(--surface); position:relative; overflow:hidden; }}
#graph svg {{ width:100%; height:100%; }}
#sidebar {{ width:340px; background:var(--surface); border-left:1px solid var(--border); overflow-y:auto; transition:width .3s; }}
#sidebar.collapsed {{ width:0; overflow:hidden; }}
.detail-header {{ padding:20px 20px 12px; border-bottom:1px solid var(--border); }}
.detail-header h2 {{ font-size:16px; font-weight:600; letter-spacing:-0.01em; margin-bottom:6px; }}
.badge {{ display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:600; margin-right:6px; }}
.badge-orchestration {{ background:#f0e6ff; color:#7c3aed; }}
.badge-reviewer {{ background:#ffe6e6; color:#dc2626; }}
.badge-executor-coder {{ background:#e6f0ff; color:#0071e3; }}
.badge-executor-deployer {{ background:#e6ffe6; color:#16a34a; }}
.badge-executor-writer {{ background:#fff5e6; color:#b45309; }}
.badge-executor-meta {{ background:#f0e6ff; color:#7c3aed; }}
.badge-executor {{ background:#e6f9ff; color:#0891b2; }}
.badge-tools {{ background:#f0f0f0; color:#6b7280; }}
.impact-card {{ margin:16px 20px; background:var(--surface2); border-radius:var(--radius); padding:14px; }}
.impact-card h4 {{ font-size:12px; font-weight:600; color:var(--text2); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:10px; }}
.impact-row {{ display:flex; justify-content:space-between; padding:4px 0; font-size:13px; }}
.impact-row .num {{ font-weight:600; color:var(--accent); }}
.dep-section {{ padding:0 20px; margin-bottom:12px; }}
.dep-section h3 {{ font-size:12px; font-weight:600; color:var(--text3); text-transform:uppercase; letter-spacing:0.05em; padding:8px 0 6px; border-bottom:1px solid var(--border); }}
.dep-list {{ list-style:none; }}
.dep-list li {{ padding:5px 10px; margin:2px 0; border-radius:6px; font-size:13px; cursor:pointer; transition:background .15s; }}
.dep-list li:hover {{ background:var(--surface2); }}
#placeholder {{ text-align:center; padding:80px 20px; color:var(--text3); }}
#placeholder h3 {{ font-size:14px; font-weight:500; margin-bottom:4px; }}
#placeholder p {{ font-size:12px; }}
#zoom-bar {{ position:absolute; bottom:20px; right:20px; display:flex; flex-direction:column; gap:4px; z-index:10; }}
#zoom-bar button {{ width:36px; height:36px; border-radius:8px; border:1px solid var(--border); background:var(--surface); color:var(--text2); cursor:pointer; font-size:16px; display:flex; align-items:center; justify-content:center; box-shadow:var(--shadow); transition:all .2s; }}
#zoom-bar button:hover {{ background:var(--surface2); border-color:var(--accent); color:var(--accent); }}
#legend {{ position:absolute; top:16px; left:16px; background:rgba(255,255,255,0.9); backdrop-filter:blur(8px); border-radius:var(--radius); padding:12px 16px; font-size:11px; box-shadow:var(--shadow); z-index:10; }}
#legend h4 {{ font-weight:600; margin-bottom:6px; font-size:11px; color:var(--text2); text-transform:uppercase; letter-spacing:0.05em; }}
.legend-item {{ display:flex; align-items:center; gap:6px; margin:3px 0; }}
.legend-dot {{ width:10px; height:10px; border-radius:3px; }}
.link {{ stroke:#d2d2d7; stroke-width:1.2; fill:none; opacity:0.5; }}
.link.highlighted {{ stroke:var(--accent); stroke-width:2.5; opacity:1; }}
.link.dimmed {{ opacity:0.05; }}
.node-rect {{ rx:6; ry:6; stroke-width:2; cursor:pointer; transition:opacity .15s; }}
.node-rect.highlighted {{ stroke-width:3; }}
.node-rect.dimmed {{ opacity:0.15; }}
.node-label {{ font-size:8px; font-family:'Inter',sans-serif; font-weight:500; fill:#1d1d1f; pointer-events:none; text-anchor:middle; dominant-baseline:central; }}
</style>
</head>
<body>
<div id="nav">
  <h1>ARIS <span>Skill DAG</span></h1>
  <div id="stats">
    <span><b>{len(nodes)}</b> skills</span>
    <span><b>{dag_data["stats"]["total_edges"]}</b> edges</span>
    <span><b>{dag_data["stats"]["caller_distribution"].get("leader", 0)}</b> leader</span>
    <span><b>{dag_data["stats"]["caller_distribution"].get("reviewer", 0)}</b> reviewer</span>
    <span><b>{dag_data["stats"]["caller_distribution"].get("executor", 0)}</b> executor</span>
    <span><b>{dag_data["stats"]["caller_distribution"].get("any", 0)}</b> any</span>
  </div>
</div>
<div id="toolbar">
  <input type="text" id="search" placeholder="Search skills..." />
  <button class="btn" id="lang-toggle" data-lang="en">中/EN</button>
  <div class="btn-group">
    <button class="btn active" data-filter="all">All</button>
    <button class="btn" data-filter="orchestration">Orchestration</button>
    <button class="btn" data-filter="reviewer">Reviewer</button>
    <button class="btn" data-filter="executor-coder">Coder</button>
    <button class="btn" data-filter="executor-deployer">Deployer</button>
    <button class="btn" data-filter="executor-writer">Writer</button>
    <button class="btn" data-filter="tools">Tools</button>
  </div>
  <button class="btn" id="impact-btn" data-filter="impact">⚡ Impact</button>
</div>
<div id="main">
  <div id="graph">
    <div id="legend">
      <h4>Layers</h4>
      <div class="legend-item"><div class="legend-dot" style="background:var(--orchestration)"></div>Orchestration</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--reviewer)"></div>Reviewer</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-coder)"></div>Executor · Coder</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-deployer)"></div>Executor · Deployer</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-writer)"></div>Executor · Writer</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-meta)"></div>Executor · Meta</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-other)"></div>Executor · Other</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--tools)"></div>Tools / Search</div>
    </div>
    <div id="zoom-bar">
      <button id="zoom-in">+</button>
      <button id="zoom-out">−</button>
      <button id="zoom-fit">⊡</button>
    </div>
  </div>
  <div id="sidebar">
    <div id="placeholder"><h3>Select a skill</h3><p>Click a node to see details & impact</p></div>
    <div id="detail" style="display:none"></div>
  </div>
</div>
<script>
const DAG_NODES = {nodes_json_str};
const DAG_EDGES = {edges_json_str};

const nodeMap = {{}};
DAG_NODES.forEach(n => nodeMap[n.name] = n);

const LAYER_FILL = {{
  'orchestration': '#f0e6ff', 'reviewer': '#ffe6e6', 'executor-coder': '#e6f0ff', 'executor-deployer': '#e6ffe6',
  'executor-writer': '#fff5e6', 'executor-meta': '#f0e6ff', 'executor': '#e6f9ff', 'tools': '#f0f0f0'
}};
const LAYER_STROKE = {{
  'orchestration': '#bf5af2', 'reviewer': '#dc2626', 'executor-coder': '#0071e3', 'executor-deployer': '#30d158',
  'executor-writer': '#ff9500', 'executor-meta': '#8b5cf6', 'executor': '#64d2ff', 'tools': '#8e8e93'
}};

let currentFilter = 'all';
let impactMode = false;
let selectedSkill = null;
let currentLang = 'en';

// Bilingual translations
const I18N = {{
  en: {{
    title: 'ARIS Skill DAG',
    skills: 'skills', edges: 'edges', leader: 'leader', reviewer: 'reviewer', executor: 'executor', any: 'any',
    searchPlaceholder: 'Search skills...',
    all: 'All', orchestration: 'Orchestration', coder: 'Coder', deployer: 'Deployer', writer: 'Writer', tools: 'Tools',
    impact: '⚡ Impact',
    layers: 'Layers',
    selectSkill: 'Select a skill', clickNode: 'Click a node to see details & impact',
    impactAnalysis: 'Impact Analysis',
    directDownstream: 'Direct downstream', transitiveDownstream: 'Transitive downstream',
    directUpstream: 'Direct upstream', transitiveUpstream: 'Transitive upstream',
    invokes: 'Invokes', invokedBy: 'Invoked by', produces: 'Produces', consumes: 'Consumes'
  }},
  zh: {{
    title: 'ARIS 技能依赖图',
    skills: '技能', edges: '边', leader: '编排', reviewer: '审查', executor: '执行', any: '通用',
    searchPlaceholder: '搜索技能...',
    all: '全部', orchestration: '编排层', coder: '编码', deployer: '部署', writer: '写作', tools: '工具',
    impact: '⚡ 影响分析',
    layers: '层级',
    selectSkill: '选择技能', clickNode: '点击节点查看详情和影响范围',
    impactAnalysis: '影响分析',
    directDownstream: '直接下游', transitiveDownstream: '传递下游',
    directUpstream: '直接上游', transitiveUpstream: '传递上游',
    invokes: '调用', invokedBy: '被调用', produces: '产出', consumes: '消费'
  }}
}};

function updateLang(lang) {{
  currentLang = lang;
  const t = I18N[lang];
  document.querySelector('#nav h1').innerHTML = `ARIS <span>${{t.title.split(' ').slice(1).join(' ')}}</span>`;
  document.querySelector('#search').placeholder = t.searchPlaceholder;
  document.querySelectorAll('.btn-group .btn')[0].textContent = t.all;
  document.querySelector('#legend h4').textContent = t.layers;
  document.querySelector('#placeholder h3').textContent = t.selectSkill;
  document.querySelector('#placeholder p').textContent = t.clickNode;
  document.getElementById('lang-toggle').textContent = lang === 'en' ? '中/EN' : 'EN/中';
}}

document.getElementById('lang-toggle').onclick = () => {{
  updateLang(currentLang === 'en' ? 'zh' : 'en');
}};

// SVG setup
const container = document.getElementById('graph');
const width = container.clientWidth;
const height = container.clientHeight;

const svg = d3.select('#graph').append('svg')
  .attr('width', width).attr('height', height);

const g = svg.append('g');

// Zoom
const zoom = d3.zoom().scaleExtent([0.2, 5]).on('zoom', (event) => {{
  g.attr('transform', event.transform);
}});
svg.call(zoom);

document.getElementById('zoom-in').onclick = () => svg.transition().duration(300).call(zoom.scaleBy, 1.4);
document.getElementById('zoom-out').onclick = () => svg.transition().duration(300).call(zoom.scaleBy, 0.7);
document.getElementById('zoom-fit').onclick = () => {{
  const bounds = g.node().getBBox();
  if (bounds.width === 0) return;
  const scale = 0.9 / Math.max(bounds.width / width, bounds.height / height);
  const tx = width / 2 - scale * (bounds.x + bounds.width / 2);
  const ty = height / 2 - scale * (bounds.y + bounds.height / 2);
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
}};

// Arrow marker
svg.append('defs').append('marker')
  .attr('id', 'arrowhead').attr('viewBox', '0 -5 10 10')
  .attr('refX', 28).attr('refY', 0).attr('markerWidth', 6).attr('markerHeight', 6)
  .attr('orient', 'auto')
  .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#d2d2d7');

// Prepare data
const simNodes = DAG_NODES.map(n => ({{...n, id: n.name}}));
const nameToIdx = {{}};
simNodes.forEach((n, i) => nameToIdx[n.name] = i);
const simLinks = DAG_EDGES.filter(e => nameToIdx[e.source] !== undefined && nameToIdx[e.target] !== undefined)
  .map(e => ({{source: e.source, target: e.target}}));

// Force simulation
const simulation = d3.forceSimulation(simNodes)
  .force('link', d3.forceLink(simLinks).id(d => d.id).distance(60).strength(0.3))
  .force('charge', d3.forceManyBody().strength(-200))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(40));

// Draw links
const link = g.append('g').selectAll('line')
  .data(simLinks).join('line')
  .attr('class', 'link')
  .attr('marker-end', 'url(#arrowhead)');

// Draw nodes
const node = g.append('g').selectAll('g')
  .data(simNodes).join('g')
  .attr('class', 'node-group')
  .call(d3.drag()
    .on('start', (event, d) => {{ if(!event.active) simulation.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on('drag', (event, d) => {{ d.fx=event.x; d.fy=event.y; }})
    .on('end', (event, d) => {{ if(!event.active) simulation.alphaTarget(0); d.fx=null; d.fy=null; }})
  );

node.append('rect')
  .attr('class', 'node-rect')
  .attr('width', 70).attr('height', 24)
  .attr('x', -35).attr('y', -12)
  .attr('fill', d => LAYER_FILL[d.layer] || '#f0f0f0')
  .attr('stroke', d => LAYER_STROKE[d.layer] || '#8e8e93');

node.append('text')
  .attr('class', 'node-label')
  .attr('y', 1)
  .text(d => d.name);

// Tick
simulation.on('tick', () => {{
  link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
  node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
}});

// Click
node.on('click', (event, d) => {{
  event.stopPropagation();
  onNodeClick(d.id);
}});

svg.on('click', () => {{
  d3.selectAll('.node-rect').classed('highlighted dimmed', false).attr('stroke-width', 2);
  d3.selectAll('.link').classed('highlighted dimmed', false);
  document.getElementById('detail').style.display = 'none';
  document.getElementById('placeholder').style.display = 'block';
  selectedSkill = null;
}});

function onNodeClick(name) {{
  selectedSkill = name;
  const n = nodeMap[name];
  if (!n) return;

  // Reset styles
  d3.selectAll('.node-rect').classed('highlighted', false).classed('dimmed', false).attr('stroke-width', 2);
  d3.selectAll('.link').classed('highlighted', false).classed('dimmed', false);

  if (impactMode) {{
    const downIds = new Set([name]);
    const upIds = new Set([name]);
    let q = [name];
    while(q.length) {{ let c=q.shift(); (nodeMap[c]?.invoked_by||[]).forEach(d => {{ if(!downIds.has(d)){{downIds.add(d);q.push(d);}} }}); }}
    q = [name];
    while(q.length) {{ let c=q.shift(); (nodeMap[c]?.invokes||[]).forEach(d => {{ if(!upIds.has(d)){{upIds.add(d);q.push(d);}} }}); }}
    const impactIds = new Set([...downIds, ...upIds]);

    d3.selectAll('.node-rect').classed('dimmed', d => !impactIds.has(d.id));
    d3.selectAll('.node-rect').classed('highlighted', d => impactIds.has(d.id));
    d3.selectAll('.link').classed('dimmed', d => !(impactIds.has(d.source.id) && impactIds.has(d.target.id)));
    d3.selectAll('.link').classed('highlighted', d => impactIds.has(d.source.id) && impactIds.has(d.target.id));
  }} else {{
    d3.selectAll('.node-rect').classed('highlighted', d => d.id === name).attr('stroke-width', d => d.id === name ? 3 : 2);
  }}

  // Sidebar
  const placeholder = document.getElementById('placeholder');
  const detail = document.getElementById('detail');
  placeholder.style.display = 'none';
  detail.style.display = 'block';

  const upstream = n.invokes || [];
  const inferred = n.inferred_mentions || [];
  const downstream = n.invoked_by || [];
  const produces = n.produces || [];
  const consumes = n.consumes || [];

  let transDown = new Set(), transUp = new Set();
  (function bfsDown(s) {{ let q=[s],v=new Set(); while(q.length){{ let c=q.shift(); (nodeMap[c]?.invoked_by||[]).forEach(d => {{ if(!v.has(d)){{v.add(d);transDown.add(d);q.push(d);}} }}); }} }})(name);
  (function bfsUp(s) {{ let q=[s],v=new Set(); while(q.length){{ let c=q.shift(); (nodeMap[c]?.invokes||[]).forEach(d => {{ if(!v.has(d)){{v.add(d);transUp.add(d);q.push(d);}} }}); }} }})(name);

  const layerBadge = `<span class="badge badge-${{n.layer}}">${{n.layer}}</span>`;
  const callerBadge = `<span class="badge badge-${{n.caller==='executor'?'executor':n.layer}}">${{n.caller}}</span>`;

  detail.innerHTML = `
    <div class="detail-header">
      <h2>${{name}}</h2>
      ${{layerBadge}} ${{callerBadge}}
    </div>
    <div class="desc-section" style="padding:12px 20px;border-bottom:1px solid var(--border);">
      <p style="font-size:13px;color:var(--text2);line-height:1.5;">${{n.description || 'No description'}}</p>
    </div>
    ${{n.examples && n.examples.length ? '<div class="dep-section"><h3>Examples</h3><ul class="dep-list">' + n.examples.map(e => '<li style="font-size:12px;color:var(--text2);">' + e + '</li>').join('') + '</ul></div>' : ''}}
    <div class="impact-card">
      <h4>Impact Analysis</h4>
      <div class="impact-row"><span>Direct downstream</span><span class="num">${{downstream.length}}</span></div>
      <div class="impact-row"><span>Transitive downstream</span><span class="num">${{transDown.size}}</span></div>
      <div class="impact-row"><span>Direct upstream</span><span class="num">${{upstream.length}}</span></div>
      <div class="impact-row"><span>Transitive upstream</span><span class="num">${{transUp.size}}</span></div>
    </div>
    <div class="dep-section"><h3>Invokes (${{upstream.length}})</h3>
      <ul class="dep-list">${{upstream.map(s=>'<li onclick="onNodeClick(\\''+s+'\\')">'+s+'</li>').join('')}}</ul></div>
    ${{inferred.length?'<div class="dep-section"><h3>Inferred mentions (not DAG edges)</h3><ul class="dep-list">'+inferred.map(s=>'<li onclick="onNodeClick(\\''+s+'\\')">'+s+'</li>').join('')+'</ul></div>':''}}
    <div class="dep-section"><h3>Invoked by (${{downstream.length}})</h3>
      <ul class="dep-list">${{downstream.map(s=>'<li onclick="onNodeClick(\\''+s+'\\')">'+s+'</li>').join('')}}</ul></div>
    ${{produces.length?'<div class="dep-section"><h3>Produces</h3><ul class="dep-list">'+produces.map(s=>'<li>'+s+'</li>').join('')+'</ul></div>':''}}
    ${{consumes.length?'<div class="dep-section"><h3>Consumes</h3><ul class="dep-list">'+consumes.map(s=>'<li>'+s+'</li>').join('')+'</ul></div>':''}}
  `;
}}
window.onNodeClick = onNodeClick;

// Search
document.getElementById('search').addEventListener('input', e => {{
  const term = e.target.value.toLowerCase();
  d3.selectAll('.node-rect').attr('opacity', d => !term || d.id.includes(term) ? 1 : 0.15);
  d3.selectAll('.node-label').attr('opacity', d => !term || d.id.includes(term) ? 1 : 0.15);
}});

// Filter
document.querySelectorAll('#toolbar .btn[data-filter]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('#toolbar .btn[data-filter]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const f = btn.dataset.filter;
    impactMode = f === 'impact';
    currentFilter = impactMode ? 'all' : f;
    d3.selectAll('.node-rect').classed('highlighted dimmed', false);
    d3.selectAll('.link').classed('highlighted dimmed', false);
    d3.selectAll('.node-rect').attr('opacity', d => currentFilter === 'all' || d.layer === currentFilter ? 1 : 0.1);
    d3.selectAll('.node-label').attr('opacity', d => currentFilter === 'all' || d.layer === currentFilter ? 1 : 0.1);
  }});
}});

// Auto-fit after simulation settles
simulation.on('end', () => {{
  setTimeout(() => document.getElementById('zoom-fit').click(), 100);
}});
</script>
</body>
</html>'''

def main():
    parser = argparse.ArgumentParser(description="Generate SKILL_DAG.yaml")
    parser.add_argument("--check-only", action="store_true", help="Only validate, don't write")
    parser.add_argument("--mermaid", action="store_true", help="Also generate Mermaid diagram")
    parser.add_argument("--html", action="store_true", help="Also generate HTML visualization")
    args = parser.parse_args()

    nodes = build_graph(SKILLS_DIR)
    print(f"Scanned {len(nodes)} skills")

    # Check for cycles
    cycles = detect_cycles(nodes)
    if cycles:
        print(f"WARNING: {len(cycles)} cycle(s) detected:")
        for c in cycles:
            print(f"  {' -> '.join(c)}")
    else:
        print("No cycles detected (DAG valid)")

    # Stats
    callers = defaultdict(int)
    for node in nodes.values():
        callers[node.get("caller", "unknown")] += 1
    print(f"Caller distribution: {dict(callers)}")

    edges = sum(len(n.get("invokes", [])) for n in nodes.values())
    inferred_mentions = sum(len(n.get("inferred_mentions", [])) for n in nodes.values())
    print(f"Total invocation edges: {edges}")
    print(f"Total inferred mentions: {inferred_mentions}")

    if args.check_only:
        sys.exit(1 if cycles else 0)

    # Write YAML
    dag = {
        "version": 1,
        "generated_by": "tools/generate_skill_dag.py",
        "stats": {
            "total_skills": len(nodes),
            "total_edges": edges,
            "total_inferred_mentions": inferred_mentions,
            "caller_distribution": dict(callers),
            "has_cycles": bool(cycles),
        },
        "nodes": [nodes[k] for k in sorted(nodes.keys())],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(dag, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Written: {OUTPUT_PATH}")

    if args.mermaid:
        mermaid = generate_mermaid(nodes)
        with open(MERMAID_PATH, "w", encoding="utf-8") as f:
            f.write(mermaid + "\n")
        print(f"Written: {MERMAID_PATH}")

    if args.html:
        html = generate_html(nodes, dag)
        with open(HTML_PATH, "w", encoding="utf-8") as f:
            f.write(html + "\n")
        print(f"Written: {HTML_PATH}")


if __name__ == "__main__":
    main()
