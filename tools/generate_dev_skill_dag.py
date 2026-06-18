#!/usr/bin/env python3
"""Generate the dev-only skill DAG from `to-developer/skills/dev-*/SKILL.md`.

The DAG is intentionally tiny: it only understands dev skills under
`to-developer/skills/dev-*`, and it records the optional frontmatter fields
`forked_from`, `forked_from_path`, `forked_at`, and `invokes`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_ROOT = REPO_ROOT / "to-developer" / "skills"
DEFAULT_YAML = REPO_ROOT / "to-developer" / "DEV_SKILL_DAG.yaml"
DEFAULT_MERMAID = REPO_ROOT / "to-developer" / "DEV_SKILL_DAG.mmd"


def project_root_for(skills_root: Path) -> Path:
    """Infer the project root from a `.../to-developer/skills` path."""

    return skills_root.parent.parent


def parse_frontmatter(skill_md: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a SKILL.md file."""

    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    try:
        _, fm_text, _ = text.split("---\n", 2)
    except ValueError:
        return {}
    try:
        data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def as_list(value: Any) -> list[str]:
    """Normalize scalar/list frontmatter values to a list of strings."""

    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)] if str(value) else []


def as_text(value: Any) -> str | None:
    """Normalize an optional frontmatter field to a stripped string."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def discover_dev_skills(skills_root: Path) -> list[Path]:
    """Return all `dev-*` skill markdown files under the given root."""

    if not skills_root.is_dir():
        return []
    return [
        d / "SKILL.md"
        for d in sorted(skills_root.iterdir())
        if d.is_dir() and d.name.startswith("dev-") and (d / "SKILL.md").is_file()
    ]


def build_graph(skills_root: Path) -> dict[str, Any]:
    """Build the dev skill DAG from frontmatter invokes lists."""

    project_root = project_root_for(skills_root)
    skills = {}
    for skill_md in discover_dev_skills(skills_root):
        fm = parse_frontmatter(skill_md)
        name = str(fm.get("name") or skill_md.parent.name)
        node = {
            "name": name,
            "path": str(skill_md.relative_to(project_root)),
            "description": str(fm.get("description") or "").strip(),
            "invokes": as_list(fm.get("invokes")),
        }
        for key in ("caller", "platform", "status", "forked_from", "forked_from_path", "forked_at"):
            value = as_text(fm.get(key))
            if value is not None:
                node[key] = value
        skills[name] = node

    edges = []
    for name, node in sorted(skills.items()):
        for target in node["invokes"]:
            if target in skills:
                edges.append({"from": name, "to": target, "type": "invokes"})

    return {
        "version": 1,
        "generated_by": "tools/generate_dev_skill_dag.py",
        "source": "to-developer/skills/dev-*/SKILL.md",
        "nodes": dict(sorted(skills.items())),
        "edges": edges,
        "stats": {
            "total_skills": len(skills),
            "total_edges": len(edges),
            "total_invokes": sum(len(node["invokes"]) for node in skills.values()),
        },
    }


def render_mermaid(graph: dict[str, Any]) -> str:
    """Render a simple Mermaid graph from the dev DAG."""

    nodes: dict[str, dict[str, Any]] = graph["nodes"]
    edges: list[dict[str, Any]] = graph["edges"]

    def node_id(name: str) -> str:
        return "skill_" + "".join(ch if ch.isalnum() else "_" for ch in name)

    lines = [
        "graph LR",
        "    %% Generated from to-developer/skills/dev-*/SKILL.md by tools/generate_dev_skill_dag.py",
    ]
    for name, node in nodes.items():
        label = name.replace('"', "'")
        desc = (node.get("description") or name).replace('"', "'")
        lines.append(f'    {node_id(name)}["{label}<br/><small>{desc}</small>"]')
    lines.append("")
    for edge in edges:
        lines.append(f'    {node_id(edge["from"])} -- "invokes" --> {node_id(edge["to"])}')
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(graph: dict[str, Any], yaml_path: Path, mermaid_path: Path) -> None:
    """Write the YAML and Mermaid outputs."""

    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        yaml.safe_dump(graph, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    mermaid_path.write_text(render_mermaid(graph), encoding="utf-8")


def generate_dag(
    skills_root: Path = DEFAULT_SKILLS_ROOT,
    yaml_path: Path = DEFAULT_YAML,
    mermaid_path: Path = DEFAULT_MERMAID,
) -> dict[str, Any]:
    """Generate the dev skill DAG and return the structured graph."""

    graph = build_graph(skills_root)
    write_outputs(graph, yaml_path, mermaid_path)
    return graph


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate to-developer dev skill DAG")
    parser.add_argument("--skills-root", type=Path, default=DEFAULT_SKILLS_ROOT)
    parser.add_argument("--yaml-output", type=Path, default=DEFAULT_YAML)
    parser.add_argument("--mermaid-output", type=Path, default=DEFAULT_MERMAID)
    args = parser.parse_args()

    generate_dag(args.skills_root, args.yaml_output, args.mermaid_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
