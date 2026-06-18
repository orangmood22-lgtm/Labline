from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "tools" / "release" / "check_release_ready.py"
TAGGER = REPO_ROOT / "tools" / "release" / "tag_release.sh"


def load_checker():
    spec = importlib.util.spec_from_file_location("check_release_ready", CHECKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run(cmd, cwd):
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def init_release_repo(path: Path) -> None:
    run(["git", "init"], path)
    run(["git", "checkout", "-b", "main"], path)
    run(["git", "config", "user.email", "test@example.com"], path)
    run(["git", "config", "user.name", "Test User"], path)
    (path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [v0.1.1] - 2026-06-13\n\n"
        "### Fixed\n"
        "- Installer path handling.\n",
        encoding="utf-8",
    )
    dev_log = path / "to-developer" / "20260613-DEVELOPMENT_LOG.md"
    dev_log.parent.mkdir(parents=True)
    dev_log.write_text(
        "# Labline Development Log\n\n"
        "## [Unreleased]\n\n"
        "### tools\n"
        "- Installer path handling.\n",
        encoding="utf-8",
    )
    run(["git", "add", "CHANGELOG.md", "to-developer/20260613-DEVELOPMENT_LOG.md"], path)
    run(["git", "commit", "-m", "initial"], path)
    run(["git", "tag", "-a", "v0.1.0", "-m", "Labline v0.1.0"], path)


def test_bump_version_patch_and_minor():
    checker = load_checker()
    assert checker.bump_version("v0.1.0", "patch") == "v0.1.1"
    assert checker.bump_version("v0.1.0", "minor") == "v0.2.0"


def test_release_checker_accepts_clean_patch_release():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        init_release_repo(repo)
        result = run(
            [
                sys.executable,
                str(CHECKER),
                "--repo",
                str(repo),
                "--bump",
                "patch",
                "--print-version-only",
            ],
            REPO_ROOT,
        )
        assert result.stdout.strip() == "v0.1.1"


def test_tag_release_dry_run_does_not_create_tag():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        init_release_repo(repo)
        result = run(
            [
                "bash",
                str(TAGGER),
                "--repo",
                str(repo),
                "--bump",
                "patch",
            ],
            REPO_ROOT,
        )
        assert "DRY RUN" in result.stdout
        tags = run(["git", "tag", "--list", "v0.1.1"], repo)
        assert tags.stdout.strip() == ""


def test_tag_release_apply_creates_local_tag_without_push():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        init_release_repo(repo)
        run(
            [
                "bash",
                str(TAGGER),
                "--repo",
                str(repo),
                "--bump",
                "patch",
                "--apply",
            ],
            REPO_ROOT,
        )
        tags = run(["git", "tag", "--list", "v0.1.1"], repo)
        assert tags.stdout.strip() == "v0.1.1"


if __name__ == "__main__":
    tests = [
        test_bump_version_patch_and_minor,
        test_release_checker_accepts_clean_patch_release,
        test_tag_release_dry_run_does_not_create_tag,
        test_tag_release_apply_creates_local_tag_without_push,
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
