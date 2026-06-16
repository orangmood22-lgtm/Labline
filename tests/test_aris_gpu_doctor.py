#!/usr/bin/env python3
"""Regression tests for the 3090x2 GPU deployment doctor."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCTOR = REPO_ROOT / "deploy" / "aris_gpu_doctor.sh"


class ArisGpuDoctorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aris-gpu-doctor-"))
        self.framework = self.tmp / "framework"
        self.projects_root = self.tmp / "projects"
        self.datasets = self.tmp / "datasets"
        (self.framework / "skills" / "leader").mkdir(parents=True)
        self.projects_root.mkdir()
        self.datasets.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *extra_args):
        return subprocess.run(
            [
                "bash",
                str(DOCTOR),
                "--framework",
                str(self.framework),
                "--projects-root",
                str(self.projects_root),
                "--datasets",
                str(self.datasets),
                *extra_args,
            ],
            capture_output=True,
            text=True,
        )

    def test_reports_stale_project_skill_symlink_with_repair_command(self):
        project = self.projects_root / "exp0603"
        skills_dir = project / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        os.symlink("/root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition/skills/leader", skills_dir / "leader")

        result = self._run("--project", "exp0603")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL exp0603 skills: stale target outside framework", result.stdout)
        self.assertIn(
            f"bash {self.framework}/tools/install_aris.sh {self.projects_root}/exp0603 --aris-repo {self.framework} --quiet --no-doc",
            result.stdout,
        )

    def test_reports_missing_project_dataset_link_with_repair_command(self):
        project = self.projects_root / "exp0603"
        skills_dir = project / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        os.symlink(str(self.framework / "skills" / "leader"), skills_dir / "leader")
        (project / "data").mkdir()
        (self.datasets / "VOCdevkit").mkdir()

        result = self._run("--project", "exp0603")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL exp0603 dataset: missing data/VOCdevkit", result.stdout)
        self.assertIn(
            f"ln -s {self.datasets}/VOCdevkit {self.projects_root}/exp0603/data/VOCdevkit",
            result.stdout,
        )

    def test_reports_host_only_dataset_symlink(self):
        project = self.projects_root / "exp0603"
        skills_dir = project / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        os.symlink(str(self.framework / "skills" / "leader"), skills_dir / "leader")
        (project / "data").mkdir()
        (self.datasets / "VOCdevkit").mkdir()
        host_only = self.tmp / "host-shared" / "VOCdevkit"
        host_only.mkdir(parents=True)
        os.symlink(str(host_only), project / "data" / "VOCdevkit")

        result = self._run("--project", "exp0603")

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL exp0603 dataset: symlink target is not container shared dataset", result.stdout)

    def test_accepts_project_with_framework_skills_and_dataset_link(self):
        project = self.projects_root / "exp0603"
        skills_dir = project / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        os.symlink(str(self.framework / "skills" / "leader"), skills_dir / "leader")
        (project / "data").mkdir()
        (self.datasets / "VOCdevkit").mkdir()
        os.symlink("/aris/shared/datasets/VOCdevkit", project / "data" / "VOCdevkit")

        result = self._run("--project", "exp0603")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("OK exp0603 skills", result.stdout)
        self.assertIn("OK exp0603 dataset", result.stdout)

    def test_accepts_container_framework_skill_links_when_checked_on_host(self):
        project = self.projects_root / "exp0603"
        skills_dir = project / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        os.symlink("/aris/framework/skills/leader", skills_dir / "leader")
        (project / "data").mkdir()
        (self.datasets / "VOCdevkit").mkdir()
        os.symlink("/aris/shared/datasets/VOCdevkit", project / "data" / "VOCdevkit")

        result = self._run("--project", "exp0603")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("OK exp0603 skills", result.stdout)

    def test_accepts_legacy_claude_skills_when_codex_skills_missing(self):
        project = self.projects_root / "exp0603"
        skills_dir = project / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        os.symlink(str(self.framework / "skills" / "leader"), skills_dir / "leader")
        (project / "data").mkdir()
        (self.datasets / "VOCdevkit").mkdir()
        os.symlink("/aris/shared/datasets/VOCdevkit", project / "data" / "VOCdevkit")

        result = self._run("--project", "exp0603")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("OK exp0603 skills", result.stdout)


if __name__ == "__main__":
    unittest.main()
