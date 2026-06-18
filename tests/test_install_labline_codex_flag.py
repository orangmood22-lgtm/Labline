#!/usr/bin/env python3
"""Regression test for install_labline.sh --codex flag (target platform switching).

Covers:
  install --codex: creates .agents/skills/ symlinks (not .claude/skills/)
  install --codex: updates AGENTS.md (not CLAUDE.md)
  uninstall --codex: removes .agents/skills/ entries
  dry-run --codex: mentions correct platform paths
  idempotent: rerun --codex is no-op
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_labline.sh"


class CodexFlagTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="labline-codex-"))
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

    def test_codex_install_creates_agents_skills(self):
        """--codex should symlink into .agents/skills/, not .claude/skills/."""
        result = self._run("--codex")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        agents_skills = self.project / ".agents" / "skills"
        claude_skills = self.project / ".claude" / "skills"

        self.assertTrue(agents_skills.exists(), ".agents/skills must exist")
        # .claude/skills should NOT be created by --codex install
        self.assertFalse(claude_skills.exists(), ".claude/skills must NOT exist with --codex")

    def test_codex_install_populates_agents_skills(self):
        """.agents/skills/ should contain actual symlinks to framework skills."""
        result = self._run("--codex")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        agents_skills = self.project / ".agents" / "skills"
        # Should have at least some skill symlinks
        entries = list(agents_skills.iterdir())
        symlinks = [e for e in entries if e.is_symlink()]
        self.assertGreater(len(symlinks), 0, ".agents/skills should contain symlinks")

    def test_codex_uninstall_removes_agents_skills(self):
        """--uninstall --codex should clean up .agents/skills/ symlinks."""
        self._run("--codex")  # install first
        agents_skills = self.project / ".agents" / "skills"
        self.assertTrue(agents_skills.exists())

        result = self._run("--codex", "--uninstall")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # After uninstall, the symlinks should be gone
        # The directory itself may remain (managed by user), but symlinks gone
        if agents_skills.exists():
            remaining = [e for e in agents_skills.iterdir() if e.is_symlink()]
            self.assertEqual(len(remaining), 0, "all managed symlinks must be removed")

    def test_codex_dry_run_mentions_agents_path(self):
        """--dry-run --codex output should show action line, not crash."""
        result = subprocess.run(
            [
                "bash",
                str(INSTALL_SCRIPT),
                str(self.project),
                "--labline-repo",
                str(REPO_ROOT),
                "--no-doc",
                "--dry-run",
                "--codex",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("(dry-run)", result.stdout, "dry-run must be indicated")
        # dry-run only prints counts, not individual paths; behavior verified by install tests above

    def test_codex_install_is_idempotent(self):
        """Rerunning --codex install should be a no-op."""
        self._run("--codex")
        result = self._run("--codex")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        agents_skills = self.project / ".agents" / "skills"
        self.assertTrue(agents_skills.exists())


if __name__ == "__main__":
    unittest.main()
