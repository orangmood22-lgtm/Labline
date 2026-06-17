from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARIS_CLI = REPO_ROOT / "tools" / "aris"


def read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_worker_is_a_mainline_and_codex_role_skill() -> None:
    main = read("skills/worker/SKILL.md")
    codex = read("skills/skills-codex/worker/SKILL.md")

    for content in [main, codex]:
        assert "name: worker" in content
        assert "caller: executor" in content
        assert "Codex harness subagent" in content
        assert "OpenAI-compatible/DeepSeek 只是可选 transport" in content
        assert "不做最终决策" in content
        assert "不自动 commit / push / promote" in content


def test_leader_can_dispatch_worker_through_codex_harness() -> None:
    leader = read("skills/skills-codex/leader/SKILL.md")

    assert "worker" in leader
    assert "spawn_agent:" in leader
    assert "agent_type: worker" in leader
    assert "model: gpt-5.4-mini" in leader
    assert ".agents/skills/worker/SKILL.md" in leader
    assert "不是外部 CLI 替代品" in leader
    assert "codex exec" not in leader.lower()
    assert "aris dev worker run" not in leader


def test_worker_contract_does_not_define_external_cli_as_primary_runtime() -> None:
    for rel in ["skills/worker/SKILL.md", "skills/skills-codex/worker/SKILL.md"]:
        content = read(rel)
        lowered = content.lower()

        assert "spawn_agent:" in content
        assert "agent_type: worker" in content
        assert "默认 worker transport 是 Codex harness subagent" in content
        assert "runtime binding view" in lowered
        assert "codex exec" not in lowered
        assert "aris dev worker run" not in content


def test_codex_shared_references_include_worker_runtime_protocols() -> None:
    for rel in [
        "skills/skills-codex/shared-references/agent-guide.md",
        "skills/skills-codex/shared-references/agent-status-stream.md",
        "skills/skills-codex/shared-references/executor-skill-routing.md",
        "skills/skills-codex/shared-references/executor-blocked-protocol.md",
    ]:
        content = read(rel)
        assert "Worker" in content or "worker" in content


def test_dev_worker_config_default_is_codex_harness_provider() -> None:
    with tempfile.TemporaryDirectory(prefix="aris-worker-contract-") as tmp:
        workspace = Path(tmp) / "workspace"
        framework = Path(tmp) / "framework"
        (framework / "tools").mkdir(parents=True)
        (framework / "templates").mkdir()
        env = os.environ.copy()
        env["ARIS_WORKSPACE"] = str(workspace)

        result = subprocess.run(
            [str(ARIS_CLI), "dev", "worker", "config", "--init", "--aris-repo", str(REPO_ROOT), "--quiet"],
            cwd=tmp,
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        config = json.loads((workspace / ".aris" / "dev-workers.json").read_text(encoding="utf-8"))
        assert config["defaults"]["provider"] == "codex_subagent"
        assert config["providers"]["codex_subagent"]["transport"] == "codex_subagent"
        assert config["roles"]["worker"]["provider"] == "codex_subagent"


def test_user_docs_show_worker_as_harness_role() -> None:
    tripartite = read("docs/TRIPARTITE_ARCHITECTURE_GUIDE.md")
    operations = read("docs/OPERATIONS_GUIDE.md")
    template = read("templates/AGENTS_MD_TEMPLATE.md")

    assert "Worker" in tripartite
    assert "低风险辅助执行角色" in tripartite
    assert "Codex harness worker" in operations
    assert "Codex harness worker / cheap provider" in template
