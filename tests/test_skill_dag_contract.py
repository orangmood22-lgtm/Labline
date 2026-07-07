#!/usr/bin/env python3
"""Regression tests for SKILL_DAG formal edge semantics."""

import shutil
import tempfile
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from generate_skill_dag import assert_no_inferred_mentions, build_graph, collect_inferred_mentions


def write_skill(root: Path, name: str, frontmatter: str, body: str = "") -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\n{frontmatter}---\n\n{body}",
        encoding="utf-8",
    )


def test_body_mentions_do_not_create_formal_edges():
    tmp = Path(tempfile.mkdtemp())
    try:
        write_skill(
            tmp,
            "alpha",
            "caller: any\n",
            "Compare with /beta, but do not invoke it.",
        )
        write_skill(tmp, "beta", "caller: any\n")

        graph = build_graph(tmp)

        assert graph["alpha"].get("invokes", []) == []
        assert graph["alpha"].get("inferred_mentions") == ["beta"]
        assert collect_inferred_mentions(graph) == [("alpha", ["beta"])]
    finally:
        shutil.rmtree(tmp)


def test_frontmatter_invokes_create_formal_edges():
    tmp = Path(tempfile.mkdtemp())
    try:
        write_skill(
            tmp,
            "alpha",
            "caller: any\ninvokes:\n  - beta\n",
            "Also mentions /gamma in prose.",
        )
        write_skill(tmp, "beta", "caller: any\n")
        write_skill(tmp, "gamma", "caller: any\n")

        graph = build_graph(tmp)

        assert graph["alpha"].get("invokes") == ["beta"]
        assert graph["alpha"].get("inferred_mentions") == ["gamma"]
        assert collect_inferred_mentions(graph) == [("alpha", ["gamma"])]
    finally:
        shutil.rmtree(tmp)


def test_fail_on_inferred_mentions_helper_reports_offenders():
    tmp = Path(tempfile.mkdtemp())
    try:
        write_skill(
            tmp,
            "alpha",
            "caller: any\n",
            "Compare with /beta, but do not invoke it.",
        )
        write_skill(tmp, "beta", "caller: any\n")

        graph = build_graph(tmp)

        try:
            assert_no_inferred_mentions(graph)
        except ValueError as exc:
            assert str(exc) == "Inferred mentions detected:\n  alpha: beta"
        else:
            raise AssertionError("expected inferred mention validation to fail")
    finally:
        shutil.rmtree(tmp)


def test_platform_metadata_does_not_declare_dead_end_compatibility():
    repo = Path(__file__).resolve().parent.parent
    graph = build_graph(repo / "skills")
    allowed_platforms = {"both", "claude", "codex"}
    failures = []

    for name, node in graph.items():
        platform = node.get("platform")
        status = node.get("status")
        if platform and platform not in allowed_platforms:
            failures.append(f"{name}: invalid platform={platform}")
        if status == "claude-only":
            failures.append(f"{name}: status=claude-only conflicts with dual-track target")

    assert failures == [], "\n".join(failures)


def test_runtime_task_protocol_is_wired_into_all_user_roles():
    repo = Path(__file__).resolve().parent.parent
    graph = build_graph(repo / "skills")
    role_skills = {"leader", "planner", "coder", "deployer", "writer", "reviewer"}

    assert (repo / "skills" / "shared-references" / "runtime-task-protocol.md").exists()
    assert "runtime-task-protocol" in graph
    missing_roles = sorted(role for role in role_skills if role not in graph)
    assert missing_roles == []

    missing_invokes = sorted(
        role
        for role in role_skills
        if "runtime-task-protocol" not in graph[role].get("invokes", [])
    )
    assert missing_invokes == []

    contract = (repo / "skills" / "shared-references" / "role-contracts.md").read_text(encoding="utf-8")
    for role in ["Leader", "Planner", "Coder", "Deployer", "Writer", "Reviewer"]:
        assert f"| {role} |" in contract
    assert "runtime-task-protocol.md" in contract

    protocol = (repo / "skills" / "shared-references" / "runtime-task-protocol.md").read_text(encoding="utf-8")
    for term in [
        "--next-expected-update",
        "--required-artifact",
        "--verdict-artifact",
        "--retry-of",
        "Runtime Task identity",
        "terminal success",
        "Observability Failure Retry Policy",
        "transport evidence",
        "NO_VERDICT_EXECUTION_FAILURE",
    ]:
        assert term in protocol


def test_leader_embedded_dispatch_prompts_include_runtime_protocol():
    repo = Path(__file__).resolve().parent.parent
    leader = (repo / "skills" / "leader" / "SKILL.md").read_text(encoding="utf-8")

    expected_agent_ids = [
        "coder-${pipeline_id}-phase2",
        "deployer-${pipeline_id}-sanity",
        "deployer-${pipeline_id}-full",
        "writer-${pipeline_id}-paper",
    ]
    for agent_id in expected_agent_ids:
        assert f"agent_id: {agent_id}" in leader

    expected_runtime_task_ids = [
        "agent-coder-${pipeline_id}-phase2",
        "agent-deployer-${pipeline_id}-sanity",
        "agent-deployer-${pipeline_id}-full",
        "agent-writer-${pipeline_id}-paper",
    ]
    for task_id in expected_runtime_task_ids:
        assert f"runtime_task_id: {task_id}" in leader

    assert leader.count("Runtime Task Contract") >= len(expected_agent_ids)
    assert leader.count("Read .claude/skills/shared-references/runtime-task-protocol.md") >= len(
        expected_agent_ids
    )
    assert leader.count(".labline/tools/agent_status.py") >= len(expected_agent_ids)
    for term in [
        "observability_failure=true",
        "boot_no_progress",
        "NO_VERDICT_EXECUTION_FAILURE",
        "前台独立 review transport",
    ]:
        assert term in leader


def test_leader_review_prompts_include_reviewer_runtime_status_contract():
    repo = Path(__file__).resolve().parent.parent
    prompts = (repo / "skills" / "shared-references" / "leader-review-prompts.md").read_text(
        encoding="utf-8"
    )
    sections = re.split(r"\n## §\d+ ", prompts)[1:]

    assert len(sections) == 5
    required_terms = [
        "agent_id",
        "runtime-task-protocol.md",
        ".labline/tools/agent_status.py",
        "verdict artifact",
        "terminal status",
    ]
    failures = []
    for index, section in enumerate(sections, start=1):
        missing = [term for term in required_terms if term not in section]
        if missing:
            failures.append(f"§{index}: {', '.join(missing)}")

    assert not failures, "Reviewer prompts must carry runtime status contract:\n" + "\n".join(failures)


if __name__ == "__main__":
    tests = [
        test_body_mentions_do_not_create_formal_edges,
        test_frontmatter_invokes_create_formal_edges,
        test_fail_on_inferred_mentions_helper_reports_offenders,
        test_platform_metadata_does_not_declare_dead_end_compatibility,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"OK {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
    sys.exit(1 if failed else 0)
