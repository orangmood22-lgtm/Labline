#!/usr/bin/env python3
"""tests/test_skill_catalog.py — TDD tests for generate_skill_catalog.py"""

import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add tools/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from generate_skill_catalog import parse_frontmatter, generate_catalog, CATEGORY_MAP


def test_parse_frontmatter_basic():
    """Parse standard SKILL.md frontmatter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""---
name: test-skill
description: "A test skill for unit testing."
argument-hint: "[--flag value]"
allowed-tools: Bash(*), Read
---

# Test Skill

Some content here.
""")
        f.flush()
        result = parse_frontmatter(Path(f.name))
    os.unlink(f.name)

    assert result is not None, "frontmatter should parse"
    assert result["name"] == "test-skill"
    assert "test skill" in result["description"].lower()
    assert result.get("argument-hint") == "[--flag value]"


def test_parse_frontmatter_no_quotes():
    """Parse frontmatter without quotes around values."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""---
name: bare-skill
description: No quotes here
argument-hint: [args]
---
""")
        f.flush()
        result = parse_frontmatter(Path(f.name))
    os.unlink(f.name)

    assert result is not None
    assert result["name"] == "bare-skill"
    assert result["description"] == "No quotes here"


def test_parse_frontmatter_missing():
    """Return None if no frontmatter."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Just a heading\n\nNo frontmatter.\n")
        f.flush()
        result = parse_frontmatter(Path(f.name))
    os.unlink(f.name)

    assert result is None


def test_generate_catalog_creates_file():
    """Catalog generation produces output file with correct structure."""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        skills_dir = tmpdir / "skills"
        output = tmpdir / "docs" / "SKILL_CATALOG.md"

        # Create fake skills
        for name in ["sync", "arxiv", "leader"]:
            d = skills_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"""---
name: {name}
description: "Test {name} skill."
argument-hint: "[args]"
---

# {name}
""")

        generate_catalog(skills_dir, output)

        assert output.exists(), "output file should exist"
        content = output.read_text()
        assert "# Labline Skill Catalog" in content
        assert "`/sync`" in content
        assert "`/arxiv`" in content
        assert "`/leader`" in content
    finally:
        shutil.rmtree(tmpdir)


def test_all_skills_categorized():
    """Every real skill should be in CATEGORY_MAP (no '未分类')."""
    framework = Path(__file__).resolve().parent.parent
    skills_dir = framework / "skills"

    unmapped = []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "SKILL.md").exists():
            continue
        if d.name.startswith("skills-codex") or d.name == "shared-references":
            continue  # meta dirs, not user-facing skills
        if d.name not in CATEGORY_MAP:
            unmapped.append(d.name)

    assert unmapped == [], f"Skills missing from CATEGORY_MAP: {unmapped}"


def test_catalog_has_all_categories():
    """Generated catalog should contain all non-empty category sections."""
    framework = Path(__file__).resolve().parent.parent
    skills_dir = framework / "skills"
    output = Path(tempfile.mktemp(suffix=".md"))

    try:
        generate_catalog(skills_dir, output)
        content = output.read_text()

        # All major categories should appear
        for cat in ["Pipeline/编排", "研究发现", "实验", "论文撰写", "工具/同步"]:
            assert f"## {cat}" in content, f"Missing category: {cat}"
    finally:
        output.unlink(missing_ok=True)


def test_also_used_by_appears():
    """Cross-category tags should appear in output."""
    framework = Path(__file__).resolve().parent.parent
    skills_dir = framework / "skills"
    output = Path(tempfile.mktemp(suffix=".md"))

    try:
        generate_catalog(skills_dir, output)
        content = output.read_text()

        # arxiv has also_used_by: ["论文撰写"]
        # Find the arxiv section and check
        assert "也用于：" in content, "Cross-category tags should appear"
    finally:
        output.unlink(missing_ok=True)


if __name__ == "__main__":
    tests = [
        test_parse_frontmatter_basic,
        test_parse_frontmatter_no_quotes,
        test_parse_frontmatter_missing,
        test_generate_catalog_creates_file,
        test_all_skills_categorized,
        test_catalog_has_all_categories,
        test_also_used_by_appears,
    ]

    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  💥 {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'❌' if failed else '✅'} {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
