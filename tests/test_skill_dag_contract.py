#!/usr/bin/env python3
"""Regression tests for SKILL_DAG formal edge semantics."""

import shutil
import tempfile
from pathlib import Path
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
