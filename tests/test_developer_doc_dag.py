from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "update_developer_docs.py"


def load_update_developer_docs():
    spec = importlib.util.spec_from_file_location("update_developer_docs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_developer_doc_dag_check_only_passes():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check-only"],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert "developer doc dag ok:" in result.stdout
    assert result.stderr == ""


def test_generated_mermaid_is_up_to_date():
    docs = load_update_developer_docs()
    data = docs.load_yaml_subset(REPO_ROOT / "to-developer" / "DOC_DAG.yaml")
    errors = docs.validate(data)

    assert errors == []
    assert (REPO_ROOT / "to-developer" / "DOC_DAG.mmd").read_text(
        encoding="utf-8"
    ) == docs.generate_mermaid(data)


def test_validate_reports_uncovered_developer_doc(tmp_path, monkeypatch):
    docs = load_update_developer_docs()
    monkeypatch.setattr(docs, "REPO_ROOT", tmp_path)
    to_developer = tmp_path / "to-developer"
    to_developer.mkdir()
    (to_developer / "DOC_DAG.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                'description: "test"',
                "",
                "nodes:",
                "  to-developer/DOC_DAG.yaml:",
                '    title: "DAG"',
                "    layer: governance",
                "    kind: source",
                "",
                "edges:",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (to_developer / "uncovered.md").write_text("# Missing\n", encoding="utf-8")

    data = docs.load_yaml_subset(to_developer / "DOC_DAG.yaml")

    assert docs.validate(data) == [
        "to-developer file not covered by DAG: to-developer/uncovered.md"
    ]
