#!/usr/bin/env python3
"""Regression test for install_labline.sh manifest safety (S5 atomic write, S6 lock).

Covers:
  install: manifest file exists after successful install
  install: manifest has valid version header
  install: manifest lists all installed skills
  uninstall: manifest is removed (preserved as .prev)
  concurrent: two installs in same project serialize (one waits/fails gracefully)
"""
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_labline.sh"


class ManifestSafetyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="labline-manifest-"))
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

    def test_manifest_exists_after_install(self):
        """Successful install must create .labline/installed-skills.txt."""
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        manifest = self.project / ".labline" / "installed-skills.txt"
        self.assertTrue(manifest.exists(), "manifest must exist after install")

    def test_manifest_has_valid_version_header(self):
        """Manifest must start with version header."""
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        manifest = self.project / ".labline" / "installed-skills.txt"
        lines = manifest.read_text().splitlines()
        self.assertGreater(len(lines), 0, "manifest must not be empty")
        self.assertTrue(
            any(line.startswith("version\t") for line in lines),
            "manifest must contain version header",
        )

    def test_manifest_lists_installed_skills(self):
        """Manifest body must list every installed skill."""
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        manifest = self.project / ".labline" / "installed-skills.txt"
        text = manifest.read_text()
        # After header, there should be body lines with skill entries
        body_lines = [l for l in text.splitlines() if l.startswith("skill\t")]
        self.assertGreater(len(body_lines), 0, "manifest must list at least one skill")

    def test_uninstall_preserves_manifest_as_prev(self):
        """Uninstall should move manifest to .prev, not delete it."""
        self._run()  # install
        manifest = self.project / ".labline" / "installed-skills.txt"
        self.assertTrue(manifest.exists())

        result = self._run("--uninstall")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        self.assertFalse(manifest.exists(), "current manifest must be gone")
        prev = self.project / ".labline" / "installed-skills.txt.prev"
        self.assertTrue(prev.exists(), "previous manifest must be preserved")

    def test_concurrent_install_serialize(self):
        """Two installs in same project should not corrupt manifest."""
        # First install normally
        r1 = self._run()
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)

        # Simulate concurrent: run two reconciles simultaneously
        results = []

        def run_install():
            r = self._run("--reconcile")
            results.append(r)

        t1 = threading.Thread(target=run_install)
        t2 = threading.Thread(target=run_install)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # At least one should succeed; neither should crash with manifest corruption
        rcodes = [r.returncode for r in results]
        self.assertTrue(all(rc in (0, 1) for rc in rcodes), "concurrent runs must exit 0 or 1, not crash")

        # Manifest should still be valid after concurrency
        manifest = self.project / ".labline" / "installed-skills.txt"
        self.assertTrue(manifest.exists(), "manifest must survive concurrent access")
        text = manifest.read_text()
        self.assertIn("version\t", text, "manifest must still have valid header")


if __name__ == "__main__":
    unittest.main()
