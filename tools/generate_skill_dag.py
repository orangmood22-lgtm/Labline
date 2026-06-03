#!/usr/bin/env python3
"""Generate SKILL_DAG.yaml from SKILL.md frontmatter fields.

Reads all skills/<name>/SKILL.md files, extracts:
  - caller (leader/executor/any)
  - invokes (list of skill names this skill calls)
  - produces (list of artifact filenames)
  - consumes (list of artifact filenames)

Outputs docs/SKILL_DAG.yaml and validates the graph is acyclic.

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
EXCLUDE = {"shared-references", "skills-codex", "skills-codex.bak"}


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


def scan_invocations(skill_path: Path) -> list:
    """Scan SKILL.md body for /skill-name invocations (heuristic)."""
    text = skill_path.read_text(encoding="utf-8")
    # Remove frontmatter
    text = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)
    # Find /skill-name patterns (in code blocks or prose)
    matches = re.findall(r"(?<![`\w])/([a-z][a-z0-9-]+)", text)
    # Filter to known skill names
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
        invoked = scan_invocations(skill_md)
        # Filter to only known skills
        invoked = [s for s in invoked if s in all_skill_names and s != d.name]

        node = {
            "name": d.name,
            "caller": fm.get("caller", "unknown"),
        }
        if invoked:
            node["invokes"] = sorted(set(invoked))
        if fm.get("produces"):
            node["produces"] = fm["produces"] if isinstance(fm["produces"], list) else [fm["produces"]]
        if fm.get("consumes"):
            node["consumes"] = fm["consumes"] if isinstance(fm["consumes"], list) else [fm["consumes"]]

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
    """Generate self-contained HTML visualization page using Cytoscape.js."""
    invoked_by = compute_invoked_by(nodes)

    # Classify executor sub-roles
    EXECUTOR_CODER = {"tdd", "diagnose", "git-guardrails", "experiment-bridge"}
    EXECUTOR_DEPLOYER = {"run-experiment", "monitor-experiment", "sync", "framework-update", "system-profile", "vast-gpu", "serverless-modal", "experiment-queue", "training-check"}
    EXECUTOR_WRITER = {"paper-write", "paper-compile", "paper-figure", "paper-illustration", "paper-illustration-image2", "paper-slides", "paper-poster", "paper-talk", "rebuttal", "claims-drafting", "formula-derivation", "figure-spec", "figure-description", "mermaid-diagram", "pixel-art", "slides-polish", "proof-writer", "proof-checker", "patent-pipeline", "patent-novelty-check", "patent-review", "grant-proposal", "invention-structuring", "specification-writing", "embodiment-description", "jurisdiction-format", "prior-art-search", "writing-systems-papers"}

    # Build enriched nodes
    nodes_json = []
    for name in sorted(nodes.keys()):
        node = dict(nodes[name])
        node["invoked_by"] = invoked_by.get(name, [])
        # Determine layer
        caller = node.get("caller", "any")
        if caller == "leader":
            node["layer"] = "orchestration"
        elif caller == "executor":
            if name in EXECUTOR_CODER:
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
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.28/dist/cytoscape.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5/dist/cytoscape-dagre.min.js"></script>
<style>
:root {{
  --bg: #fafafa; --surface: #ffffff; --surface2: #f5f5f7; --border: #d2d2d7;
  --text: #1d1d1f; --text2: #6e6e73; --text3: #86868b; --accent: #0071e3;
  --accent2: #2997ff; --danger: #ff3b30; --success: #34c759; --warning: #ff9500;
  --orchestration: #bf5af2; --exec-coder: #0071e3; --exec-deployer: #30d158;
  --exec-writer: #ff9500; --exec-other: #64d2ff; --tools: #8e8e93;
  --radius: 12px; --shadow: 0 2px 8px rgba(0,0,0,0.04); --shadow-lg: 0 8px 32px rgba(0,0,0,0.08);
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
#cy {{ flex:1; background:var(--surface); position:relative; }}
#cy canvas {{ left:0; }}
#sidebar {{ width:340px; background:var(--surface); border-left:1px solid var(--border); overflow-y:auto; transition:width .3s; }}
#sidebar.collapsed {{ width:0; overflow:hidden; }}
.detail-header {{ padding:20px 20px 12px; border-bottom:1px solid var(--border); }}
.detail-header h2 {{ font-size:16px; font-weight:600; letter-spacing:-0.01em; margin-bottom:6px; }}
.badge {{ display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:600; margin-right:6px; }}
.badge-orchestration {{ background:#f0e6ff; color:#7c3aed; }}
.badge-executor-coder {{ background:#e6f0ff; color:#0071e3; }}
.badge-executor-deployer {{ background:#e6ffe6; color:#16a34a; }}
.badge-executor-writer {{ background:#fff5e6; color:#b45309; }}
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
#layout-toggle {{ position:absolute; top:16px; right:16px; z-index:10; }}
</style>
</head>
<body>
<div id="nav">
  <h1>ARIS <span>Skill DAG</span></h1>
  <div id="stats">
    <span><b>{len(nodes)}</b> skills</span>
    <span><b>{dag_data["stats"]["total_edges"]}</b> edges</span>
    <span><b>{dag_data["stats"]["caller_distribution"].get("leader", 0)}</b> leader</span>
    <span><b>{dag_data["stats"]["caller_distribution"].get("executor", 0)}</b> executor</span>
    <span><b>{dag_data["stats"]["caller_distribution"].get("any", 0)}</b> any</span>
  </div>
</div>
<div id="toolbar">
  <input type="text" id="search" placeholder="Search skills..." />
  <div class="btn-group">
    <button class="btn active" data-filter="all">All</button>
    <button class="btn" data-filter="orchestration">Orchestration</button>
    <button class="btn" data-filter="executor-coder">Coder</button>
    <button class="btn" data-filter="executor-deployer">Deployer</button>
    <button class="btn" data-filter="executor-writer">Writer</button>
    <button class="btn" data-filter="tools">Tools</button>
  </div>
  <button class="btn" id="impact-btn" data-filter="impact">⚡ Impact</button>
  <div class="btn-group" id="layout-btns">
    <button class="btn active" data-layout="dagre-tb">↓ TB</button>
    <button class="btn" data-layout="dagre-lr">→ LR</button>
    <button class="btn" data-layout="breadthfirst">◎ BFS</button>
    <button class="btn" data-layout="concentric">◉ Circle</button>
  </div>
</div>
<div id="main">
  <div id="cy">
    <div id="legend">
      <h4>Layers</h4>
      <div class="legend-item"><div class="legend-dot" style="background:var(--orchestration)"></div>Orchestration</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-coder)"></div>Executor · Coder</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-deployer)"></div>Executor · Deployer</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-writer)"></div>Executor · Writer</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--exec-other)"></div>Executor · Other</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--tools)"></div>Tools / Search</div>
    </div>
    <div id="zoom-bar">
      <button onclick="cy.zoom(cy.zoom()*1.3);cy.center()">+</button>
      <button onclick="cy.zoom(cy.zoom()/1.3);cy.center()">−</button>
      <button onclick="cy.fit(undefined,50)">⊡</button>
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

let currentFilter = 'all';
let impactMode = false;
let selectedSkill = null;
let currentLayout = 'dagre-tb';

const LAYER_COLORS = {{
  'orchestration': '#bf5af2', 'executor-coder': '#0071e3', 'executor-deployer': '#30d158',
  'executor-writer': '#ff9500', 'executor': '#64d2ff', 'tools': '#8e8e93'
}};
const LAYER_BG = {{
  'orchestration': '#f0e6ff', 'executor-coder': '#e6f0ff', 'executor-deployer': '#e6ffe6',
  'executor-writer': '#fff5e6', 'executor': '#e6f9ff', 'tools': '#f0f0f0'
}};

const cyElements = [];
DAG_NODES.forEach(n => {{
  cyElements.push({{
    data: {{
      id: n.name, label: n.name, caller: n.caller, layer: n.layer,
      invokes: n.invokes || [], invoked_by: n.invoked_by || [],
      produces: n.produces || [], consumes: n.consumes || []
    }}
  }});
}});
DAG_EDGES.forEach(e => {{
  cyElements.push({{ data: {{ source: e.source, target: e.target }} }});
}});

const cy = cytoscape({{
  container: document.getElementById('cy'),
  elements: cyElements,
  style: [
    {{ selector: 'node', style: {{
      'label': 'data(label)', 'text-valign': 'center', 'text-halign': 'center',
      'font-size': 10, 'font-family': 'Inter, sans-serif', 'font-weight': 500,
      'color': '#1d1d1f', 'text-wrap': 'wrap', 'text-max-width': 80,
      'width': 28, 'height': 28, 'shape': 'round-rectangle',
      'corner-radius': 6, 'border-width': 2, 'border-opacity': 0.8,
      'background-color': 'mapData(layer, "orchestration", 0, "tools", 1, #8e8e93)',
      'border-color': '#d2d2d7', 'padding': 4,
      'transition-property': 'border-color, border-width, opacity',
      'transition-duration': '0.15s'
    }}}},
    {{ selector: 'node[layer="orchestration"]', style: {{ 'background-color': '#f0e6ff', 'border-color': '#bf5af2' }} }},
    {{ selector: 'node[layer="executor-coder"]', style: {{ 'background-color': '#e6f0ff', 'border-color': '#0071e3' }} }},
    {{ selector: 'node[layer="executor-deployer"]', style: {{ 'background-color': '#e6ffe6', 'border-color': '#30d158' }} }},
    {{ selector: 'node[layer="executor-writer"]', style: {{ 'background-color': '#fff5e6', 'border-color': '#ff9500' }} }},
    {{ selector: 'node[layer="executor"]', style: {{ 'background-color': '#e6f9ff', 'border-color': '#64d2ff' }} }},
    {{ selector: 'node[layer="tools"]', style: {{ 'background-color': '#f0f0f0', 'border-color': '#8e8e93' }} }},
    {{ selector: 'node:active', style: {{ 'border-width': 3, 'overlay-opacity': 0 }} }},
    {{ selector: 'node.selected', style: {{ 'border-width': 3, 'border-color': '#0071e3', 'font-weight': 700 }} }},
    {{ selector: 'node.dimmed', style: {{ 'opacity': 0.2 }} }},
    {{ selector: 'node.highlighted', style: {{ 'opacity': 1, 'border-width': 3 }} }},
    {{ selector: 'edge', style: {{
      'width': 1.2, 'line-color': '#d2d2d7', 'curve-style': 'bezier',
      'target-arrow-shape': 'triangle', 'target-arrow-color': '#d2d2d7',
      'arrow-scale': 0.6, 'opacity': 0.6
    }}}},
    {{ selector: 'edge.highlighted', style: {{ 'line-color': '#0071e3', 'target-arrow-color': '#0071e3', 'width': 2, 'opacity': 1 }} }},
    {{ selector: 'edge.dimmed', style: {{ 'opacity': 0.08 }} }}
  ],
  layout: {{ name: 'dagre', rankDir: 'TB', spacingFactor: 1.2, padding: 50 }},
  minZoom: 0.3, maxZoom: 4, wheelSensitivity: 0.3
}});

// Click handler
cy.on('tap', 'node', evt => {{
  const node = evt.target;
  onNodeClick(node.id());
}});

cy.on('tap', evt => {{
  if (evt.target === cy) {{
    cy.elements().removeClass('selected dimmed highlighted');
    document.getElementById('detail').style.display = 'none';
    document.getElementById('placeholder').style.display = 'block';
    selectedSkill = null;
  }}
}});

function onNodeClick(name) {{
  selectedSkill = name;
  const n = nodeMap[name];
  cy.elements().removeClass('selected dimmed highlighted');
  cy.$('#'+name).addClass('selected');

  if (impactMode) {{
    // Highlight impact chain
    const downIds = new Set([name]);
    const upIds = new Set([name]);
    let q = [name];
    while(q.length) {{ let c=q.shift(); (nodeMap[c]?.invoked_by||[]).forEach(d => {{ if(!downIds.has(d)){{downIds.add(d);q.push(d);}} }}); }}
    q = [name];
    while(q.length) {{ let c=q.shift(); (nodeMap[c]?.invokes||[]).forEach(d => {{ if(!upIds.has(d)){{upIds.add(d);q.push(d);}} }}); }}
    const impactIds = new Set([...downIds, ...upIds]);
    cy.nodes().forEach(nd => {{
      if (impactIds.has(nd.id())) nd.addClass('highlighted');
      else nd.addClass('dimmed');
    }});
    cy.edges().forEach(ed => {{
      if (impactIds.has(ed.source().id()) && impactIds.has(ed.target().id())) ed.addClass('highlighted');
      else ed.addClass('dimmed');
    }});
  }}

  // Sidebar detail
  const placeholder = document.getElementById('placeholder');
  const detail = document.getElementById('detail');
  placeholder.style.display = 'none';
  detail.style.display = 'block';

  const upstream = n.invokes || [];
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
    <div class="impact-card">
      <h4>Impact Analysis</h4>
      <div class="impact-row"><span>Direct downstream</span><span class="num">${{downstream.length}}</span></div>
      <div class="impact-row"><span>Transitive downstream</span><span class="num">${{transDown.size}}</span></div>
      <div class="impact-row"><span>Direct upstream</span><span class="num">${{upstream.length}}</span></div>
      <div class="impact-row"><span>Transitive upstream</span><span class="num">${{transUp.size}}</span></div>
    </div>
    <div class="dep-section"><h3>Invokes (${{upstream.length}})</h3>
      <ul class="dep-list">${{upstream.map(s=>'<li onclick="onNodeClick(\\''+s+'\\')">'+s+'</li>').join('')}}</ul></div>
    <div class="dep-section"><h3>Invoked by (${{downstream.length}})</h3>
      <ul class="dep-list">${{downstream.map(s=>'<li onclick="onNodeClick(\\''+s+'\\')">'+s+'</li>').join('')}}</ul></div>
    ${{produces.length?'<div class="dep-section"><h3>Produces</h3><ul class="dep-list">'+produces.map(s=>'<li>'+s+'</li>').join('')+'</ul></div>':''}}
    ${{consumes.length?'<div class="dep-section"><h3>Consumes</h3><ul class="dep-list">'+consumes.map(s=>'<li>'+s+'</li>').join('')+'</ul></div>':''}}
  `;
}}

// Search
document.getElementById('search').addEventListener('input', e => {{
  const term = e.target.value.toLowerCase();
  cy.nodes().forEach(n => {{
    if (!term || n.id().includes(term)) n.style('opacity', 1);
    else n.style('opacity', 0.15);
  }});
}});

// Filter
document.querySelectorAll('#toolbar .btn[data-filter]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('#toolbar .btn[data-filter]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const f = btn.dataset.filter;
    impactMode = f === 'impact';
    currentFilter = impactMode ? 'all' : f;
    cy.elements().removeClass('selected dimmed highlighted');
    cy.nodes().forEach(n => {{
      if (currentFilter === 'all' || n.data('layer') === currentFilter || (!impactMode && n.data('caller') === currentFilter))
        n.style('opacity', 1);
      else n.style('opacity', 0.1);
    }});
  }});
}});

// Layout switch
document.querySelectorAll('#layout-btns .btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('#layout-btns .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const l = btn.dataset.layout;
    let layoutOpts = {{ name: 'dagre', rankDir: 'TB', spacingFactor: 1.2, padding: 50 }};
    if (l === 'dagre-lr') layoutOpts = {{ name: 'dagre', rankDir: 'LR', spacingFactor: 1.2, padding: 50 }};
    else if (l === 'breadthfirst') layoutOpts = {{ name: 'breadthfirst', spacingFactor: 1.5, padding: 50 }};
    else if (l === 'concentric') layoutOpts = {{ name: 'concentric', spacingFactor: 1.2, padding: 50 }};
    cy.layout(layoutOpts).run();
  }});
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
    print(f"Total invocation edges: {edges}")

    if args.check_only:
        sys.exit(1 if cycles else 0)

    # Write YAML
    dag = {
        "version": 1,
        "generated_by": "tools/generate_skill_dag.py",
        "stats": {
            "total_skills": len(nodes),
            "total_edges": edges,
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
            f.write(mermaid)
        print(f"Written: {MERMAID_PATH}")

    if args.html:
        html = generate_html(nodes, dag)
        with open(HTML_PATH, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Written: {HTML_PATH}")


if __name__ == "__main__":
    main()
