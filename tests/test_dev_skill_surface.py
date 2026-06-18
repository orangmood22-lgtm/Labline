from __future__ import annotations

import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"

sys.path.insert(0, str(TOOLS_DIR))

from generate_dev_skill_catalog import generate_catalog as generate_dev_catalog
from generate_dev_skill_dag import generate_dag as generate_dev_dag
from generate_skill_catalog import generate_catalog as generate_user_catalog
from generate_skill_dag import build_graph as build_user_graph


def write_skill(root: Path, name: str, frontmatter: str, body: str = "") -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n{frontmatter}---\n\n{body}",
        encoding="utf-8",
    )


def test_dev_prefix_scan_and_outputs_exist() -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        skills_root = tmp / "to-developer" / "skills"
        write_skill(
            skills_root,
            "dev-alpha",
            (
                "description: Dev alpha\n"
                "invokes:\n  - dev-beta\n"
                "caller: developer\n"
                "platform: codex\n"
                "status: dev-only\n"
                "forked_from: alpha\n"
                "forked_from_path: skills/alpha/SKILL.md\n"
                "forked_at: 2026-06-17\n"
            ),
        )
        write_skill(
            skills_root,
            "dev-beta",
            "description: Dev beta\n",
        )
        write_skill(
            skills_root,
            "alpha",
            "description: User alpha\n",
        )

        catalog_path = tmp / "to-developer" / "DEV_SKILL_CATALOG.md"
        dag_yaml_path = tmp / "to-developer" / "DEV_SKILL_DAG.yaml"
        dag_mmd_path = tmp / "to-developer" / "DEV_SKILL_DAG.mmd"

        catalog = generate_dev_catalog(skills_root, catalog_path)
        graph = generate_dev_dag(skills_root, dag_yaml_path, dag_mmd_path)

        assert catalog_path.exists()
        assert dag_yaml_path.exists()
        assert dag_mmd_path.exists()
        assert "/dev-alpha" in catalog
        assert "## `/alpha`" not in catalog
        assert "Forked from: `alpha`" in catalog
        assert "Forked from path: `skills/alpha/SKILL.md`" in catalog
        assert "Forked at: `2026-06-17`" in catalog
        assert graph["stats"]["total_skills"] == 2
        assert graph["nodes"]["dev-alpha"]["invokes"] == ["dev-beta"]
        assert graph["nodes"]["dev-alpha"]["forked_from"] == "alpha"
        assert graph["nodes"]["dev-alpha"]["forked_from_path"] == "skills/alpha/SKILL.md"
        assert graph["nodes"]["dev-alpha"]["forked_at"] == "2026-06-17"
        assert "alpha" not in graph["nodes"]
        assert yaml.safe_load(dag_yaml_path.read_text(encoding="utf-8"))["nodes"]["dev-beta"]["invokes"] == []
        mermaid = dag_mmd_path.read_text(encoding="utf-8")
        assert "skill_dev_alpha" in mermaid
        assert "dev-alpha[" not in mermaid
    finally:
        shutil.rmtree(tmp)


def test_user_surface_excludes_dev_skills() -> None:
    repo_skills = REPO_ROOT / "skills"
    user_graph = build_user_graph(repo_skills)
    assert all(not name.startswith("dev-") for name in user_graph)

    user_catalog_path = Path(tempfile.mktemp(suffix=".md"))
    try:
        generate_user_catalog(repo_skills, user_catalog_path)
        content = user_catalog_path.read_text(encoding="utf-8")
        assert "/dev-" not in content
    finally:
        user_catalog_path.unlink(missing_ok=True)

    dag_yaml = REPO_ROOT / "docs" / "SKILL_DAG.yaml"
    dag_data = yaml.safe_load(dag_yaml.read_text(encoding="utf-8"))
    assert all(not str(node.get("name", "")).startswith("dev-") for node in dag_data.get("nodes", []))


def test_dev_generators_can_be_run_as_scripts() -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        skills_root = tmp / "to-developer" / "skills"
        write_skill(skills_root, "dev-worker", "description: worker\n")

        catalog_path = tmp / "to-developer" / "DEV_SKILL_CATALOG.md"
        dag_yaml_path = tmp / "to-developer" / "DEV_SKILL_DAG.yaml"
        dag_mmd_path = tmp / "to-developer" / "DEV_SKILL_DAG.mmd"

        catalog_cmd = [
            sys.executable,
            str(TOOLS_DIR / "generate_dev_skill_catalog.py"),
            "--skills-root",
            str(skills_root),
            "--output",
            str(catalog_path),
        ]
        dag_cmd = [
            sys.executable,
            str(TOOLS_DIR / "generate_dev_skill_dag.py"),
            "--skills-root",
            str(skills_root),
            "--yaml-output",
            str(dag_yaml_path),
            "--mermaid-output",
            str(dag_mmd_path),
        ]

        assert subprocess.run(catalog_cmd, cwd=REPO_ROOT, check=False).returncode == 0
        assert subprocess.run(dag_cmd, cwd=REPO_ROOT, check=False).returncode == 0
        assert catalog_path.exists()
        assert dag_yaml_path.exists()
        assert dag_mmd_path.exists()
    finally:
        shutil.rmtree(tmp)
