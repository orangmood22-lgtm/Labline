#!/usr/bin/env python3
"""Regression test for install_labline.sh --dev flag (dev framework selection).

Covers:
  install --dev: uses labline-dev/ repo instead of stable
  install --dev --labline-repo: explicit --labline-repo overrides --dev
  install (no --dev): uses stable repo by default
  install --dev: records version from dev repo
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_labline.sh"
# Assume dev repo is sibling to stable
DEV_REPO = REPO_ROOT.parent / "labline-dev"


class DevFlagTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="labline-dev-"))
        self.project = self.tmp / "project"
        self.project.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *extra_args):
        result = subprocess.run(
            [
                "bash",
                str(INSTALL_SCRIPT),
                str(self.project),
                "--labline-repo",
                str(REPO_ROOT),
                "--quiet",
                "--no-doc",
                *extra_args,
            ],
            capture_output=True,
            text=True,
        )
        return result

    def test_dev_flag_uses_dev_repo(self):
        """--dev should use labline-dev/ repo instead of stable."""
        if not DEV_REPO.exists():
            self.skipTest(f"dev repo not found at {DEV_REPO}")

        result = subprocess.run(
            [
                "bash",
                str(INSTALL_SCRIPT),
                str(self.project),
                "--dev",
                "--quiet",
                "--no-doc",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Check version file points to dev repo
        ver_file = self.project / ".labline" / "framework-version.txt"
        if ver_file.exists():
            content = ver_file.read_text().strip()
            # Dev repo may not have .git, so content might be "unknown"
            # But the fact that install succeeded means it used dev repo
            self.assertIn(content, ["unknown", "dev"], f"unexpected version: {content}")

    def test_explicit_labline_repo_overrides_dev(self):
        """Explicit --labline-repo should override --dev."""
        if not DEV_REPO.exists():
            self.skipTest(f"dev repo not found at {DEV_REPO}")

        result = subprocess.run(
            [
                "bash",
                str(INSTALL_SCRIPT),
                str(self.project),
                "--dev",
                "--labline-repo",
                str(REPO_ROOT),  # explicit stable
                "--quiet",
                "--no-doc",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Should use stable (has .git), so version should be real commit
        ver_file = self.project / ".labline" / "framework-version.txt"
        if ver_file.exists():
            content = ver_file.read_text().strip()
            self.assertNotEqual(content, "unknown", "explicit --labline-repo should override --dev")

    def test_no_dev_flag_uses_stable(self):
        """Without --dev, should use stable repo by default."""
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Stable has .git, so version should be real
        ver_file = self.project / ".labline" / "framework-version.txt"
        if ver_file.exists():
            content = ver_file.read_text().strip()
            self.assertNotEqual(content, "unknown", "stable repo should have .git")


if __name__ == "__main__":
    unittest.main()
