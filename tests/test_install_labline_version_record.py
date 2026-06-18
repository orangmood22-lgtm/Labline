#!/usr/bin/env python3
"""Regression test for install_labline.sh framework version recording.

Covers:
  install: records framework version + commit to .labline/ after successful install
  install: writes "unknown" when labline-repo has no .git
  dry-run: does not write version files
  uninstall: removes version files (best-effort cleanup)
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_labline.sh"


class VersionRecordTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="labline-version-"))
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

    def test_install_records_framework_version(self):
        """After install, .labline/ should contain version and commit files."""
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        ver_file = self.project / ".labline" / "framework-version.txt"
        commit_file = self.project / ".labline" / "framework-commit.txt"

        self.assertTrue(ver_file.exists(), "framework-version.txt must exist after install")
        self.assertTrue(commit_file.exists(), "framework-commit.txt must exist after install")

        # REPO_ROOT has .git, so both should contain real values (not "unknown")
        ver_content = ver_file.read_text().strip()
        commit_content = commit_file.read_text().strip()
        self.assertNotEqual(ver_content, "unknown", "version should be recorded from git")
        self.assertNotEqual(commit_content, "unknown", "commit should be recorded from git")
        self.assertEqual(len(commit_content), 40, "commit should be full SHA-1 hash")

    def test_install_records_unknown_for_repo_without_git(self):
        """If labline-repo has no .git, version files should contain 'unknown'."""
        fake_repo = self.tmp / "fake-repo"
        fake_repo.mkdir()
        # Create minimal structure so installer accepts it
        (fake_repo / "skills").mkdir()
        (fake_repo / "tools").mkdir()

        result = subprocess.run(
            [
                "bash",
                str(INSTALL_SCRIPT),
                str(self.project),
                "--labline-repo",
                str(fake_repo),
                "--quiet",
                "--no-doc",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        ver_file = self.project / ".labline" / "framework-version.txt"
        commit_file = self.project / ".labline" / "framework-commit.txt"

        self.assertEqual(ver_file.read_text().strip(), "unknown")
        self.assertEqual(commit_file.read_text().strip(), "unknown")

    def test_dry_run_does_not_write_version_files(self):
        """--dry-run should not create version files."""
        result = self._run("--dry-run")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        ver_file = self.project / ".labline" / "framework-version.txt"
        commit_file = self.project / ".labline" / "framework-commit.txt"

        self.assertFalse(ver_file.exists(), "dry-run must not create version file")
        self.assertFalse(commit_file.exists(), "dry-run must not create commit file")

    def test_uninstall_removes_version_files(self):
        """Uninstall should clean up version files."""
        self._run()  # install first
        ver_file = self.project / ".labline" / "framework-version.txt"
        commit_file = self.project / ".labline" / "framework-commit.txt"
        self.assertTrue(ver_file.exists())
        self.assertTrue(commit_file.exists())

        result = self._run("--uninstall")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        self.assertFalse(ver_file.exists(), "uninstall must remove version file")
        self.assertFalse(commit_file.exists(), "uninstall must remove commit file")


if __name__ == "__main__":
    unittest.main()
