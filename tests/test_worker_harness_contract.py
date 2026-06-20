from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LANE_CLI = REPO_ROOT / "tools" / "lane"
ROLE_CONTRACT_FILES = [
    "skills/shared-references/role-contracts.md",
    "skills/skills-codex/shared-references/role-contracts.md",
]
ROLE_DEFAULT_BINDINGS = {
    "Leader": "gpt-5.5",
    "Planner": "gpt-5.4",
    "Coder": "gpt-5.4-mini",
    "Deployer": "gpt-5.4-mini",
    "Writer": "gpt-5.4",
    "Reviewer": "gpt-5.4",
}
ROLE_CONTRACT_REF_DOCS = [
    "docs/TRIPARTITE_ARCHITECTURE_GUIDE.md",
    "templates/AGENTS_MD_TEMPLATE.md",
]


def read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_worker_is_not_a_user_project_role_skill() -> None:
    assert not (REPO_ROOT / "skills" / "worker" / "SKILL.md").exists()
    assert not (REPO_ROOT / "skills" / "skills-codex" / "worker" / "SKILL.md").exists()
    assert not (REPO_ROOT / "skills" / "dev-realtest" / "SKILL.md").exists()
    assert not (REPO_ROOT / "skills" / "skills-codex" / "dev-realtest" / "SKILL.md").exists()


def test_user_leader_does_not_dispatch_worker() -> None:
    leader = read("skills/skills-codex/leader/SKILL.md")

    assert "agent_type: worker" not in leader
    assert ".agents/skills/worker/SKILL.md" not in leader
    assert "Worker 何时使用" not in leader
    assert "codex exec" not in leader.lower()
    assert "lane dev worker run" not in leader


def test_codex_shared_references_do_not_define_worker_user_role() -> None:
    for rel in [
        "skills/skills-codex/shared-references/agent-guide.md",
        "skills/skills-codex/shared-references/role-contracts.md",
        "skills/skills-codex/shared-references/agent-status-stream.md",
        "skills/skills-codex/shared-references/executor-skill-routing.md",
        "skills/skills-codex/shared-references/executor-blocked-protocol.md",
    ]:
        content = read(rel)
        assert "agent_type: worker" not in content
        assert ".agents/skills/worker/SKILL.md" not in content
        assert "| Worker |" not in content
        assert "| Dev Real-Machine Tester |" not in content


def test_legacy_dev_worker_namespace_is_not_available() -> None:
    result = subprocess.run(
        [str(LANE_CLI), "dev", "worker", "config", "--init"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr
    assert "'worker'" in result.stderr


def test_user_docs_do_not_show_worker_as_project_role() -> None:
    tripartite = read("docs/TRIPARTITE_ARCHITECTURE_GUIDE.md")
    operations = read("docs/OPERATIONS_GUIDE.md")
    template = read("templates/AGENTS_MD_TEMPLATE.md")

    for content in [tripartite, operations, template]:
        assert "Codex harness worker" not in content
        assert "$worker" not in content
        assert "| **Worker**" not in content


def test_role_contract_runtime_bindings_are_documented() -> None:
    for rel in ROLE_CONTRACT_FILES:
        content = read(rel)

        assert "Role Contract defines responsibility" in content
        assert "Default Runtime Binding" in content
        for role, model in ROLE_DEFAULT_BINDINGS.items():
            assert f"| {role} |" in content
            assert model in content
        assert "| Worker |" not in content
        assert "Developer-side `dev-worker` is separate from user roles" in content


def test_core_user_docs_reference_role_contracts() -> None:
    for rel in ROLE_CONTRACT_REF_DOCS:
        content = read(rel)
        assert "role-contracts.md" in content
        for role, model in ROLE_DEFAULT_BINDINGS.items():
            assert role in content
            assert model in content


def test_user_runtime_binding_defaults_are_documented() -> None:
    docs = [
        read("docs/OPERATIONS_GUIDE.md"),
        read("docs/TRIPARTITE_ARCHITECTURE_GUIDE.md"),
        read("templates/AGENTS_MD_TEMPLATE.md"),
        read("skills/skills-codex/shared-references/agent-guide.md"),
        read("skills/skills-codex/leader/SKILL.md"),
    ]

    for content in docs:
        for role, model in ROLE_DEFAULT_BINDINGS.items():
            assert role in content
            assert model in content

    codex_leader = read("skills/skills-codex/leader/SKILL.md")
    codex_agent_guide = read("skills/skills-codex/shared-references/agent-guide.md")
    role_contracts = read("skills/skills-codex/shared-references/role-contracts.md")
    assert 'model: "sonnet"' not in codex_leader
    assert "Opus" not in codex_leader
    assert "Sonnet" not in codex_agent_guide
    assert "Role Contract defines responsibility" in role_contracts
    assert "Developer-side `dev-worker` is separate from user roles" in role_contracts


def test_experiment_integrity_ledger_contract_is_documented() -> None:
    ledger = read("docs/EXPERIMENT_TRANSPARENCY_LEDGER.md")
    docs_index = read("docs/README.md")
    shared_refs = [
        read("skills/shared-references/experiment-integrity.md"),
        read("skills/skills-codex/shared-references/experiment-integrity.md"),
    ]

    assert "EXPERIMENT_TRANSPARENCY_LEDGER.md" in docs_index
    assert "Experiment Integrity is a workflow module, not a single skill." in ledger
    assert "does not require LangGraph" in ledger
    for record_type in [
        "`dataset`",
        "`split`",
        "`metric`",
        "`run`",
        "`deviation`",
        "`artifact`",
        "`claim`",
        "`checkpoint`",
    ]:
        assert record_type in ledger

    for content in shared_refs:
        assert "Experiment Integrity is a workflow module, not a single skill." in content
        assert "docs/EXPERIMENT_TRANSPARENCY_LEDGER.md" in content
        assert "refine-logs/EXPERIMENT_TRANSPARENCY_LEDGER.md" in content
        assert "refine-logs/checkpoints/" in content
