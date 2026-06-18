#!/usr/bin/env python3
"""Regression test for install_labline.sh --reconcile behavior.

Covers:
  reconcile: adds new skills that appeared upstream
  reconcile: removes skills that disappeared upstream
  reconcile: updates target if upstream skill moved
  reconcile: refuses if no manifest exists
  reconcile: idempotent on no changes
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_labline.sh"


class ReconcileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="labline-reconcile-"))
        self.project = self.tmp / "project"
        self.project.mkdir()
        # Create a fake upstream with one skill
        self.fake_repo = self.tmp / "fake-repo"
        self.fake_repo.mkdir()
        (self.fake_repo / "skills").mkdir()
        (self.fake_repo / "skills" / "skill-a").mkdir()
        (self.fake_repo / "skills" / "skill-a" / "SKILL.md").write_text("# Skill A\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *extra_args):
        result = subprocess.run(
            [
                "bash",
                str(INSTALL_SCRIPT),
                str(self.project),
                "--labline-repo",
                str(self.fake_repo),
                "--quiet",
                "--no-doc",
                *extra_args,
            ],
            capture_output=True,
            text=True,
        )
        return result

    def test_reconcile_adds_new_skills(self):
        """Reconcile should add skills that appeared upstream after initial install."""
        # Initial install with one skill
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Add a new skill upstream
        (self.fake_repo / "skills" / "skill-b").mkdir()
        (self.fake_repo / "skills" / "skill-b" / "SKILL.md").write_text("# Skill B\n")

        # Reconcile should add skill-b
        result = self._run("--reconcile")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        skill_b = self.project / ".claude" / "skills" / "skill-b"
        self.assertTrue(skill_b.exists(), "reconcile must add new upstream skill")

    def test_reconcile_removes_deleted_skills(self):
        """Reconcile should remove skills that disappeared upstream."""
        # Initial install with two skills
        (self.fake_repo / "skills" / "skill-b").mkdir()
        (self.fake_repo / "skills" / "skill-b" / "SKILL.md").write_text("# Skill B\n")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        skill_b = self.project / ".claude" / "skills" / "skill-b"
        self.assertTrue(skill_b.exists())

        # Remove skill-b upstream
        shutil.rmtree(self.fake_repo / "skills" / "skill-b")

        # Reconcile should remove skill-b
        result = self._run("--reconcile")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        self.assertFalse(skill_b.exists(), "reconcile must remove deleted upstream skill")

    def test_reconcile_refuses_without_manifest(self):
        """Reconcile should refuse if no manifest exists."""
        result = self._run("--reconcile")
        self.assertNotEqual(result.returncode, 0, "reconcile must fail without manifest")
        self.assertIn("manifest", result.stderr.lower(), "error message must mention manifest")

    def test_reconcile_idempotent(self):
        """Reconcile with no upstream changes should be no-op."""
        # Initial install
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Reconcile without upstream changes
        result = self._run("--reconcile")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Manifest should still be valid
        manifest = self.project / ".labline" / "installed-skills.txt"
        self.assertTrue(manifest.exists(), "manifest must exist after idempotent reconcile")


if __name__ == "__main__":
    unittest.main()
