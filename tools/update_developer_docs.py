#!/usr/bin/env python3
"""更新 Labline dev-only 开发者文档派生产物。

当前职责：
- 校验 `to-developer/DOC_DAG.yaml`
- 生成 `to-developer/DOC_DAG.mmd`
- 检查 `to-developer/` 下的 markdown/txt 文档是否被 DAG 节点覆盖

开发者文档属于 dev-only，不进入 stable `main`。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "to-developer" / "DOC_DAG.yaml"
DEFAULT_MERMAID = REPO_ROOT / "to-developer" / "DOC_DAG.mmd"


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def load_yaml_subset(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    section: str | None = None
    current_node: str | None = None
    current_edge: dict[str, Any] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" "):
            key, _, value = stripped.partition(":")
            if value.strip():
                data[key] = parse_scalar(value)
                section = None
            else:
                section = key
                data.setdefault(key, {} if key == "nodes" else [])
            current_node = None
            current_edge = None
            continue
        if section == "nodes":
            if line.startswith("  ") and not line.startswith("    "):
                current_node = stripped[:-1] if stripped.endswith(":") else stripped.partition(":")[0]
                data["nodes"].setdefault(current_node, {})
                continue
            if current_node and line.startswith("    "):
                key, _, value = stripped.partition(":")
                data["nodes"][current_node][key] = parse_scalar(value)
                continue
        if section == "edges":
            if line.startswith("  - "):
                current_edge = {}
                data["edges"].append(current_edge)
                body = stripped[2:].strip()
                if body:
                    key, _, value = body.partition(":")
                    current_edge[key] = parse_scalar(value)
                continue
            if current_edge is not None and line.startswith("    "):
                key, _, value = stripped.partition(":")
                current_edge[key] = parse_scalar(value)
                continue
        raise ValueError(f"unsupported yaml line: {raw_line}")
    return data


def node_id(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not re.match(r"^[A-Za-z_]", value):
        value = "n_" + value
    return value


def path_exists(name: str) -> bool:
    if "*" in name:
        return bool(list(REPO_ROOT.glob(name)))
    return (REPO_ROOT / name).exists()


def path_is_covered(path: Path, nodes: set[str]) -> bool:
    rel = str(path.relative_to(REPO_ROOT))
    if rel in nodes:
        return True
    for node in nodes:
        if "*" in node and path.match(node):
            return True
    return False


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = data.get("nodes") or {}
    edges = data.get("edges") or []
    if not isinstance(nodes, dict):
        return ["nodes must be a mapping"]
    if not isinstance(edges, list):
        return ["edges must be a list"]

    for name, meta in nodes.items():
        if not isinstance(meta, dict):
            errors.append(f"node {name}: metadata must be a mapping")
            continue
        if meta.get("kind") in {"generated", "stable_target"}:
            continue
        if not path_exists(name):
            errors.append(f"node {name}: path/glob does not exist")

    for idx, edge in enumerate(edges):
        src = edge.get("from") if isinstance(edge, dict) else None
        dst = edge.get("to") if isinstance(edge, dict) else None
        if src not in nodes:
            errors.append(f"edge[{idx}]: unknown from node {src!r}")
        if dst not in nodes:
            errors.append(f"edge[{idx}]: unknown to node {dst!r}")
        if isinstance(edge, dict) and not edge.get("type"):
            errors.append(f"edge[{idx}]: missing type")

    for cycle in detect_cycles(nodes, edges):
        errors.append("cycle detected: " + " -> ".join(cycle))

    node_names = set(nodes)
    ignored_roots = [
        REPO_ROOT / "to-developer" / "logs" / "dev-runtime",
    ]
    for path in sorted((REPO_ROOT / "to-developer").glob("**/*")):
        if path.is_file() and path.suffix in {".md", ".txt"}:
            if path.name == "DOC_DAG.mmd":
                continue
            if any(root in path.parents for root in ignored_roots):
                continue
            if not path_is_covered(path, node_names):
                errors.append(f"to-developer file not covered by DAG: {path.relative_to(REPO_ROOT)}")

    return errors


def detect_cycles(nodes: dict[str, Any], edges: list[dict[str, Any]]) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = edge.get("from")
        dst = edge.get("to")
        if src in nodes and dst in nodes:
            graph[src].append(dst)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in nodes}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(name: str) -> None:
        color[name] = GRAY
        stack.append(name)
        for nxt in graph.get(name, []):
            if color[nxt] == WHITE:
                visit(nxt)
            elif color[nxt] == GRAY:
                cycles.append(stack[stack.index(nxt):] + [nxt])
        stack.pop()
        color[name] = BLACK

    for name in nodes:
        if color[name] == WHITE:
            visit(name)
    return cycles


def generate_mermaid(data: dict[str, Any]) -> str:
    nodes: dict[str, dict[str, Any]] = data["nodes"]
    edges: list[dict[str, Any]] = data.get("edges") or []
    lines = [
        "graph LR",
        "    %% Generated from to-developer/DOC_DAG.yaml by tools/update_developer_docs.py",
    ]
    for name, meta in sorted(nodes.items()):
        title = str(meta.get("title") or name).replace('"', "'")
        layer = str(meta.get("layer") or "")
        label = f"{name}<br/><small>{title} · {layer}</small>" if layer else f"{name}<br/><small>{title}</small>"
        lines.append(f'    {node_id(name)}["{label}"]')
    lines.append("")
    for edge in edges:
        typ = str(edge.get("type") or "relates_to").replace('"', "'")
        lines.append(f'    {node_id(str(edge["from"]))} -- "{typ}" --> {node_id(str(edge["to"]))}')

    class_defs = {
        "governance": "fill:#ede9fe,stroke:#6d28d9",
        "generated": "fill:#f3f4f6,stroke:#4b5563",
        "log": "fill:#fef3c7,stroke:#b45309",
        "handoff": "fill:#dbeafe,stroke:#1d4ed8",
        "promote": "fill:#dcfce7,stroke:#15803d",
        "release": "fill:#fee2e2,stroke:#b91c1c",
        "architecture": "fill:#fce7f3,stroke:#be185d",
        "deploy": "fill:#e0f2fe,stroke:#0369a1",
        "discussion": "fill:#ffedd5,stroke:#c2410c",
        "stable": "fill:#ecfccb,stroke:#4d7c0f",
    }
    layers: dict[str, list[str]] = defaultdict(list)
    for name, meta in nodes.items():
        layers[str(meta.get("layer") or "other")].append(node_id(name))
    lines.append("")
    for layer, style in class_defs.items():
        lines.append(f"    classDef {layer} {style}")
    for layer, ids in sorted(layers.items()):
        if layer in class_defs and ids:
            lines.append(f"    class {','.join(sorted(ids))} {layer}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--mermaid", default=str(DEFAULT_MERMAID))
    args = parser.parse_args(argv)

    source = Path(args.source)
    mermaid = Path(args.mermaid)
    data = load_yaml_subset(source)
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not args.check_only:
        mermaid.write_text(generate_mermaid(data), encoding="utf-8")
        print(f"wrote {mermaid}")
    print(f"developer doc dag ok: {len(data.get('nodes', {}))} nodes, {len(data.get('edges', []))} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
