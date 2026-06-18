#!/usr/bin/env python3
"""Generate the dev-only skill catalog from `to-developer/skills/dev-*/SKILL.md`.

The developer skill catalog is intentionally separate from the user-facing
skill catalog. It only scans `dev-*` skills under `to-developer/skills/` and
writes `to-developer/DEV_SKILL_CATALOG.md`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_ROOT = REPO_ROOT / "to-developer" / "skills"
DEFAULT_OUTPUT = REPO_ROOT / "to-developer" / "DEV_SKILL_CATALOG.md"


@dataclass(frozen=True)
class DevSkill:
    name: str
    path: Path
    description: str
    caller: str | None
    platform: str | None
    status: str | None
    forked_from: str | None
    forked_from_path: str | None
    forked_at: str | None
    invokes: list[str]


def project_root_for(skills_root: Path) -> Path:
    """Infer the project root from a `.../to-developer/skills` path."""

    return skills_root.parent.parent


def parse_frontmatter(skill_md: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a SKILL.md file.

    If the file has no frontmatter or the frontmatter is invalid, return an
    empty mapping.
    """

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
    """Normalize a scalar/list frontmatter value to a list of strings."""

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


def read_dev_skill(skill_md: Path) -> DevSkill:
    """Read a single dev skill from frontmatter and path metadata."""

    fm = parse_frontmatter(skill_md)
    description = str(fm.get("description") or "").strip()
    return DevSkill(
        name=str(fm.get("name") or skill_md.parent.name),
        path=skill_md,
        description=description,
        caller=as_text(fm.get("caller")),
        platform=as_text(fm.get("platform")),
        status=as_text(fm.get("status")),
        forked_from=as_text(fm.get("forked_from")),
        forked_from_path=as_text(fm.get("forked_from_path")),
        forked_at=as_text(fm.get("forked_at")),
        invokes=as_list(fm.get("invokes")),
    )


def build_catalog(skills_root: Path) -> list[DevSkill]:
    """Load and sort all dev skills from the given root."""

    return [read_dev_skill(skill_md) for skill_md in discover_dev_skills(skills_root)]


def render_catalog(skills: list[DevSkill], skills_root: Path, output_path: Path) -> str:
    """Render the dev skill catalog markdown."""

    project_root = project_root_for(skills_root)
    lines = [
        "# Labline Dev Skill Catalog",
        "",
        f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}。共 {len(skills)} 个 dev skill。",
        ">",
        "> 生成命令：`python3 tools/generate_dev_skill_catalog.py`",
        "",
    ]

    if not skills:
        lines.extend(
            [
                "_未发现 `to-developer/skills/dev-*/SKILL.md`。_",
                "",
            ]
        )
    else:
        lines.append("## 目录")
        lines.append("")
        for skill in skills:
            lines.append(f"- [`/{skill.name}`](#{skill.name})")
        lines.append("")

        for skill in skills:
            lines.extend(
                [
                    "---",
                    "",
                    f"## `/{skill.name}`",
                    "",
                    f"- Path: `{skill.path.relative_to(project_root)}`",
                ]
            )
            if skill.description:
                lines.append(f"- Description: {skill.description}")
            if skill.caller:
                lines.append(f"- Caller: `{skill.caller}`")
            if skill.platform:
                lines.append(f"- Platform: `{skill.platform}`")
            if skill.status:
                lines.append(f"- Status: `{skill.status}`")
            if skill.forked_from:
                lines.append(f"- Forked from: `{skill.forked_from}`")
            if skill.forked_from_path:
                lines.append(f"- Forked from path: `{skill.forked_from_path}`")
            if skill.forked_at:
                lines.append(f"- Forked at: `{skill.forked_at}`")
            if skill.invokes:
                lines.append(f"- Invokes: {', '.join(f'`{name}`' for name in skill.invokes)}")
            else:
                lines.append("- Invokes: _none_")
            lines.append("")

    content = "\n".join(lines).rstrip() + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return content


def generate_catalog(skills_root: Path = DEFAULT_SKILLS_ROOT, output_path: Path = DEFAULT_OUTPUT) -> str:
    """Generate the catalog file and return the rendered markdown."""

    skills = build_catalog(skills_root)
    return render_catalog(skills, skills_root, output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate to-developer dev skill catalog")
    parser.add_argument("--skills-root", type=Path, default=DEFAULT_SKILLS_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    generate_catalog(args.skills_root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
