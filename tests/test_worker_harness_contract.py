from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARIS_CLI = REPO_ROOT / "tools" / "aris"


def read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_worker_is_not_a_user_project_role_skill() -> None:
    assert not (REPO_ROOT / "skills" / "worker" / "SKILL.md").exists()
    assert not (REPO_ROOT / "skills" / "skills-codex" / "worker" / "SKILL.md").exists()


def test_user_leader_does_not_dispatch_worker() -> None:
    leader = read("skills/skills-codex/leader/SKILL.md")

    assert "agent_type: worker" not in leader
    assert ".agents/skills/worker/SKILL.md" not in leader
    assert "Worker 何时使用" not in leader
    assert "codex exec" not in leader.lower()
    assert "aris dev worker run" not in leader


def test_codex_shared_references_do_not_define_worker_user_role() -> None:
    for rel in [
        "skills/skills-codex/shared-references/agent-guide.md",
        "skills/skills-codex/shared-references/agent-status-stream.md",
        "skills/skills-codex/shared-references/executor-skill-routing.md",
        "skills/skills-codex/shared-references/executor-blocked-protocol.md",
    ]:
        content = read(rel)
        assert "agent_type: worker" not in content
        assert ".agents/skills/worker/SKILL.md" not in content
        assert "| Worker |" not in content


def test_legacy_dev_worker_namespace_is_not_available() -> None:
    result = subprocess.run(
        [str(ARIS_CLI), "dev", "worker", "config", "--init"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr
    assert "'worker'" in result.stderr


def test_dev_runtime_is_documented_as_dev_only() -> None:
    plan = read("to-developer/plans/20260616-CHEAP_WORKER_DEFAULT_DIVISION.md")

    assert "状态: dev-only 草案" in plan
    assert "不引入新的 ARIS Role" in plan
    assert "aris dev rt use dev-worker deepseek-v4-flash" in plan
    assert "aris dev runtime ..." in plan


def test_user_docs_do_not_show_worker_as_project_role() -> None:
    tripartite = read("docs/TRIPARTITE_ARCHITECTURE_GUIDE.md")
    operations = read("docs/OPERATIONS_GUIDE.md")
    template = read("templates/AGENTS_MD_TEMPLATE.md")

    for content in [tripartite, operations, template]:
        assert "Codex harness worker" not in content
        assert "$worker" not in content
        assert "| **Worker**" not in content
