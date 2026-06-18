from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_developer_doc_update_check_passes():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "update_developer_docs.py"), "--check-only"],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_developer_doc_dag_mermaid_is_current():
    before = (REPO_ROOT / "to-developer" / "DOC_DAG.mmd").read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "update_developer_docs.py")],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    after = (REPO_ROOT / "to-developer" / "DOC_DAG.mmd").read_text(encoding="utf-8")
    assert after == before


def test_developer_doc_dag_ignores_dev_runtime_logs():
    log_dir = REPO_ROOT / "to-developer" / "logs" / "dev-runtime" / "dev-worker" / "dag-test"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "task.md").write_text("# task\n", encoding="utf-8")
        (log_dir / "response.md").write_text("# response\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "update_developer_docs.py"), "--check-only"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_developer_doc_dag_still_checks_uncovered_log_files():
    log_file = REPO_ROOT / "to-developer" / "logs" / "uncovered-test" / "nested.md"
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("# uncovered\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "update_developer_docs.py"), "--check-only"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode != 0
        assert "uncovered-test/nested.md" in result.stderr
    finally:
        shutil.rmtree(log_file.parent, ignore_errors=True)
