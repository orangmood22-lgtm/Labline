#!/usr/bin/env python3
"""Check whether ARIS is ready to create a framework release tag."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


VERSION_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def run_git(repo: Path, args: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def parse_version(version: str) -> Tuple[int, int, int]:
    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(f"invalid formal version: {version}")
    return tuple(int(part) for part in match.groups())


def bump_version(latest: str, bump: str) -> str:
    major, minor, patch = parse_version(latest)
    if bump == "patch":
        return f"v{major}.{minor}.{patch + 1}"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    raise ValueError(f"unsupported bump: {bump}")


def list_formal_tags(repo: Path) -> List[str]:
    tags = run_git(repo, ["tag", "--list", "v[0-9]*.[0-9]*.[0-9]*"]).splitlines()
    formal = []
    for tag in tags:
        if VERSION_RE.match(tag):
            formal.append(tag)
    return sorted(formal, key=parse_version)


def latest_formal_tag(repo: Path) -> Optional[str]:
    tags = list_formal_tags(repo)
    return tags[-1] if tags else None


def resolve_target_version(repo: Path, explicit_version: Optional[str], bump: Optional[str]) -> str:
    if explicit_version and bump:
        raise ValueError("provide either an explicit version or --bump, not both")
    if explicit_version:
        parse_version(explicit_version)
        return explicit_version
    if not bump:
        raise ValueError("provide a version like v0.1.0 or --bump patch|minor")
    latest = latest_formal_tag(repo)
    if latest is None:
        if bump == "minor":
            return "v0.1.0"
        raise ValueError("cannot --bump patch without an existing formal tag")
    return bump_version(latest, bump)


def ensure_clean_worktree(repo: Path) -> None:
    status = run_git(repo, ["status", "--porcelain"])
    if status:
        raise ValueError("worktree is not clean")


def ensure_on_main(repo: Path) -> None:
    branch = run_git(repo, ["branch", "--show-current"])
    if branch != "main":
        raise ValueError(f"release tags must be created from main, current branch is {branch!r}")


def ensure_tag_absent(repo: Path, version: str) -> None:
    tags = run_git(repo, ["tag", "--list", version])
    if tags:
        raise ValueError(f"tag already exists: {version}")


def ensure_newer_than_latest(repo: Path, version: str) -> None:
    latest = latest_formal_tag(repo)
    if latest and parse_version(version) <= parse_version(latest):
        raise ValueError(f"target version {version} is not newer than latest formal tag {latest}")


def changelog_has_version(repo: Path, version: str) -> bool:
    path = repo / "CHANGELOG.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    pattern = rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$"
    return re.search(pattern, text, flags=re.MULTILINE) is not None


def development_log_ready(repo: Path) -> bool:
    path = repo / "to-developer" / "20260613-DEVELOPMENT_LOG.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "## [Unreleased]" in text and "- Pending." not in text


def minor_release_files_exist(repo: Path) -> List[str]:
    required = [
        "docs/SKILL_CATALOG.md",
        "docs/SKILL_CATALOG_CN.md",
        "docs/SKILL_DAG.yaml",
        "docs/SKILL_DAG.mmd",
        "docs/skill-dag.html",
    ]
    return [path for path in required if not (repo / path).exists()]


def infer_release_kind(repo: Path, version: str) -> str:
    latest = latest_formal_tag(repo)
    if latest is None:
        return "minor"
    latest_major, latest_minor, _ = parse_version(latest)
    major, minor, patch = parse_version(version)
    if major != latest_major or minor != latest_minor:
        return "minor"
    if patch > 0:
        return "patch"
    return "minor"


def collect_errors(repo: Path, version: str, release_kind: str, skip_git_state: bool) -> List[str]:
    errors: List[str] = []
    if not skip_git_state:
        for check in (ensure_on_main, ensure_clean_worktree):
            try:
                check(repo)
            except (RuntimeError, ValueError) as exc:
                errors.append(str(exc))
    for check in (ensure_tag_absent, ensure_newer_than_latest):
        try:
            check(repo, version)
        except (RuntimeError, ValueError) as exc:
            errors.append(str(exc))
    if not changelog_has_version(repo, version):
        today = date.today().isoformat()
        errors.append(f"CHANGELOG.md must contain: ## [{version}] - {today}")
    if not development_log_ready(repo):
        errors.append("to-developer/20260613-DEVELOPMENT_LOG.md must exist and contain non-placeholder Unreleased entries")
    if release_kind == "minor":
        missing = minor_release_files_exist(repo)
        if missing:
            errors.append("minor release missing generated files: " + ", ".join(missing))
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="explicit formal version, e.g. v0.1.0")
    parser.add_argument("--repo", default=".", help="repository path")
    parser.add_argument("--bump", choices=["patch", "minor"], help="compute next version from latest formal tag")
    parser.add_argument("--kind", choices=["patch", "minor"], help="override inferred release gate")
    parser.add_argument("--skip-git-state", action="store_true", help="skip current-branch and clean-worktree checks")
    parser.add_argument("--print-version-only", action="store_true", help="print only the resolved target version")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        version = resolve_target_version(repo, args.version, args.bump)
        release_kind = args.kind or infer_release_kind(repo, version)
        if args.print_version_only:
            print(version)
            return 0
        errors = collect_errors(repo, version, release_kind, args.skip_git_state)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if errors:
        print(f"Release check failed for {version} ({release_kind}):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Release check passed: {version} ({release_kind})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
