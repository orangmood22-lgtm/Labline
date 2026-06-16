#!/usr/bin/env python3
"""Behavior tests for the beginner-facing ARIS CLI."""

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ARIS_CLI = REPO_ROOT / "tools" / "aris"


class ArisCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aris-cli-"))
        self.workspace = self.tmp / "workspace"
        self.workspace.mkdir()
        self.framework = self.workspace / "framework"
        self.framework.mkdir()
        (self.framework / "tools").mkdir()
        (self.framework / "templates").mkdir()
        (self.framework / "skills").mkdir()
        self._write_fake_installers()
        shutil.copy(REPO_ROOT / "templates" / "project.yaml.tmpl", self.framework / "templates" / "project.yaml.tmpl")
        shutil.copy(REPO_ROOT / "templates" / "AGENTS_MD_TEMPLATE.md", self.framework / "templates" / "AGENTS_MD_TEMPLATE.md")
        shutil.copy(REPO_ROOT / "templates" / "CLAUDE_MD_TEMPLATE.md", self.framework / "templates" / "CLAUDE_MD_TEMPLATE.md")
        subprocess.run(["git", "init"], cwd=str(self.framework), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Framework"], cwd=str(self.framework), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "framework@example.invalid"], cwd=str(self.framework), check=True, capture_output=True)
        (self.framework / "README.md").write_text("framework\n")
        subprocess.run(["git", "add", "-A"], cwd=str(self.framework), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "framework baseline"], cwd=str(self.framework), check=True, capture_output=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=str(self.framework), check=True, capture_output=True)
        self.remote = self.tmp / "framework-remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(self.remote)], cwd=str(self.framework), check=True, capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(self.framework), check=True, capture_output=True)
        self.initial_commit = self._git(["rev-parse", "HEAD"])

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_fake_installers(self):
        installer = textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail
            project="$1"
            mkdir -p "$project/.aris" "$project/.claude/skills" "$project/.agents/skills"
            if [[ " $* " == *" --uninstall "* ]]; then
              rm -f "$project/.aris/installed-skills.txt" "$project/.aris/installed-skills-codex.txt"
              exit 0
            fi
            if [[ " $* " == *" --codex "* ]]; then
              printf 'version\\t1\\nkind\\tname\\tsource_rel\\ttarget_rel\\tmode\\n' > "$project/.aris/installed-skills-codex.txt"
            else
              printf 'version\\t1\\nkind\\tname\\tsource_rel\\ttarget_rel\\tmode\\n' > "$project/.aris/installed-skills.txt"
            fi
            """
        )
        codex_installer = textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail
            project="$1"
            mkdir -p "$project/.aris" "$project/.agents/skills"
            if [[ " $* " == *" --uninstall "* ]]; then
              rm -f "$project/.aris/installed-skills-codex.txt"
              exit 0
            fi
            printf 'version\\t1\\nkind\\tname\\tsource_rel\\ttarget_rel\\tmode\\n' > "$project/.aris/installed-skills-codex.txt"
            """
        )
        for name, body in {"install_aris.sh": installer, "install_aris_codex.sh": codex_installer}.items():
            path = self.framework / "tools" / name
            path.write_text(body)
            path.chmod(0o755)

    def _run(self, cwd: Path, *args: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["ARIS_WORKSPACE"] = str(self.workspace)
        return subprocess.run(
            [str(ARIS_CLI), *args, "--aris-repo", str(self.framework), "--quiet"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            env=env,
        )

    def _git(self, args: list[str]) -> str:
        return subprocess.run(["git", *args], cwd=str(self.framework), check=True, capture_output=True, text=True).stdout.strip()

    def _registry(self) -> dict:
        return json.loads((self.workspace / ".aris" / "project-registry.json").read_text())

    def _update_status(self) -> dict:
        return json.loads((self.workspace / ".aris" / "framework-update-status.json").read_text())

    def _write_update_status(self, data: dict):
        path = self.workspace / ".aris" / "framework-update-status.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def _push_framework_update(self, message: str = "framework update") -> str:
        updater = self.tmp / f"framework-updater-{len(list(self.tmp.glob('framework-updater-*')))}"
        subprocess.run(["git", "clone", "-b", "main", str(self.remote), str(updater)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Framework"], cwd=str(updater), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "framework@example.invalid"], cwd=str(updater), check=True, capture_output=True)
        (updater / "README.md").write_text(message + "\n")
        subprocess.run(["git", "add", "-A"], cwd=str(updater), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=str(updater), check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(updater), check=True, capture_output=True)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(updater), check=True, capture_output=True, text=True).stdout.strip()

    def test_project_init_current_directory_creates_runnable_project_baseline_and_registers_project(self):
        project = self.tmp / "project"
        project.mkdir()

        result = self._run(project, "project", "init", ".", "--name", "demo", "--direction", "test direction")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        self.assertTrue((project / "project.yaml").exists())
        self.assertTrue((project / "AGENTS.md").exists())
        self.assertTrue((project / "CLAUDE.md").exists())
        self.assertTrue((project / ".gitignore").exists())
        self.assertTrue((project / ".git").exists())
        self.assertTrue((project / ".aris" / "manifest.json").exists())
        self.assertTrue((project / ".aris" / "installed-skills.txt").exists())
        self.assertTrue((project / ".aris" / "installed-skills-codex.txt").exists())
        for rel in ["code", "data", "outputs", "refine-logs", "idea-stage", "paper", "discussions", "figures", "overrides"]:
            self.assertTrue((project / rel).is_dir(), rel)

        project_yaml = (project / "project.yaml").read_text()
        self.assertIn('name: "demo"', project_yaml)
        self.assertIn('direction: "test direction"', project_yaml)
        self.assertIn("schema_version: 1", project_yaml)
        self.assertEqual(project_yaml.count("schema_version:"), 1)
        self.assertIn(f'path: "{self.framework}"', project_yaml)

        manifest = json.loads((project / ".aris" / "manifest.json").read_text())
        self.assertEqual(manifest["project_name"], "demo")
        self.assertEqual(manifest["schema_version"], 1)
        self.assertIn("codex", manifest["clients"])
        self.assertIn("claude", manifest["clients"])
        self.assertIn(str(project.resolve()), self._registry()["projects"])

    def test_project_init_path_creates_directory_or_attaches_existing_directory(self):
        root = self.tmp / "root"
        root.mkdir()

        result = self._run(root, "project", "init", "./named-demo", "--direction", "new dir")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        project = root / "named-demo"
        self.assertTrue((project / "project.yaml").exists())
        self.assertTrue((project / ".git").exists())
        self.assertIn('name: "named-demo"', (project / "project.yaml").read_text())

        again = self._run(root, "project", "init", "./named-demo", "--direction", "attach")
        self.assertEqual(again.returncode, 0, msg=again.stderr)
        self.assertIn(str(project.resolve()), self._registry()["projects"])

    def test_project_init_existing_project_preserves_user_files_and_history(self):
        project = self.tmp / "existing"
        project.mkdir()
        user_file = project / "code" / "train.py"
        user_file.parent.mkdir()
        user_file.write_text("print('keep')\n")
        subprocess.run(["git", "init"], cwd=str(project), check=True, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=str(project), check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=User", "-c", "user.email=user@example.invalid", "commit", "-m", "user work"],
            cwd=str(project),
            check=True,
            capture_output=True,
        )

        result = self._run(project, "project", "init", ".", "--name", "attached", "--direction", "attach")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        self.assertEqual(user_file.read_text(), "print('keep')\n")
        log = subprocess.run(["git", "log", "--oneline"], cwd=str(project), check=True, capture_output=True, text=True)
        self.assertIn("user work", log.stdout)
        self.assertNotIn("init: attached", log.stdout)

    def test_project_doctor_update_detach_default_to_current_directory(self):
        project = self.tmp / "project"
        project.mkdir()
        init_result = self._run(project, "project", "init", ".", "--name", "demo", "--direction", "doctor")
        self.assertEqual(init_result.returncode, 0, msg=init_result.stderr)

        doctor = self._run(project, "project", "doctor")
        self.assertEqual(doctor.returncode, 0, msg=doctor.stderr)
        self.assertIn("project.yaml: ok", doctor.stdout)

        update = self._run(project, "project", "update")
        self.assertEqual(update.returncode, 0, msg=update.stderr)

        detach = self._run(project, "project", "detach")
        self.assertEqual(detach.returncode, 0, msg=detach.stderr)
        self.assertFalse((project / ".aris" / "manifest.json").exists())
        self.assertNotIn(str(project.resolve()), self._registry()["projects"])

    def test_project_version_defaults_to_current_directory(self):
        project = self.tmp / "project"
        project.mkdir()
        init_result = self._run(project, "project", "init", ".", "--name", "demo", "--direction", "version")
        self.assertEqual(init_result.returncode, 0, msg=init_result.stderr)

        result = self._run(project, "project", "--version")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("project:", result.stdout)
        self.assertIn("framework_commit:", result.stdout)

    def test_framework_version_update_and_rollback(self):
        project = self.tmp / "project"
        project.mkdir()
        init_result = self._run(project, "project", "init", ".", "--name", "demo", "--direction", "sync")
        self.assertEqual(init_result.returncode, 0, msg=init_result.stderr)
        (project / ".aris" / "installed-skills.txt").unlink()

        version = self._run(project, "framework", "--version")
        self.assertEqual(version.returncode, 0, msg=version.stderr)
        self.assertIn(self.initial_commit[:7], version.stdout)

        new_commit = self._push_framework_update()

        check_update = self._run(project, "framework", "check-update")
        self.assertEqual(check_update.returncode, 0, msg=check_update.stderr)
        self.assertIn("status: update available", check_update.stdout)
        self.assertIn(new_commit[:7], check_update.stdout)
        self.assertEqual(self._git(["rev-parse", "HEAD"]), self.initial_commit)

        update = self._run(project, "framework", "update")
        self.assertEqual(update.returncode, 0, msg=update.stderr)
        self.assertIn("project sync: 1 updated", update.stdout)
        self.assertTrue((project / ".aris" / "installed-skills.txt").exists())
        self.assertEqual(self._git(["rev-parse", "HEAD"]), new_commit)

        rollback = self._run(project, "framework", "rollback")
        self.assertEqual(rollback.returncode, 0, msg=rollback.stderr)
        self.assertEqual(self._git(["rev-parse", "HEAD"]), self.initial_commit)

    def test_framework_check_update_notify_reminds_at_most_once_per_day(self):
        project = self.tmp / "project"
        project.mkdir()
        init_result = self._run(project, "project", "init", ".", "--name", "demo", "--direction", "notify")
        self.assertEqual(init_result.returncode, 0, msg=init_result.stderr)
        new_commit = self._push_framework_update("framework notify update")

        first = self._run(project, "framework", "check-update", "--if-stale", "1d", "--notify")
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        self.assertIn("[ARIS] framework update available", first.stdout)
        self.assertIn(new_commit[:7], first.stdout)

        second = self._run(project, "framework", "check-update", "--if-stale", "1d", "--notify")
        self.assertEqual(second.returncode, 0, msg=second.stderr)
        self.assertEqual(second.stdout, "")

        status = self._update_status()
        status["last_notified_at"] = "2000-01-01T00:00:00Z"
        self._write_update_status(status)

        third = self._run(project, "framework", "check-update", "--if-stale", "1d", "--notify")
        self.assertEqual(third.returncode, 0, msg=third.stderr)
        self.assertIn("[ARIS] framework update available", third.stdout)

    def test_framework_update_can_skip_registered_project_sync(self):
        project = self.tmp / "project"
        project.mkdir()
        init_result = self._run(project, "project", "init", ".", "--name", "demo", "--direction", "sync")
        self.assertEqual(init_result.returncode, 0, msg=init_result.stderr)
        (project / ".aris" / "installed-skills.txt").unlink()

        result = self._run(project, "framework", "update", "--no-project-sync")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertFalse((project / ".aris" / "installed-skills.txt").exists())
        self.assertIn("project sync: skipped", result.stdout)

    def test_short_legacy_commands_are_not_supported(self):
        for command in ["init", "update", "doctor", "detach"]:
            result = subprocess.run(
                [str(ARIS_CLI), "--aris-repo", str(self.framework), "--quiet", command],
                cwd=str(self.tmp),
                capture_output=True,
                text=True,
            )
            with self.subTest(command=command):
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("invalid choice", result.stderr)

    def test_cli_works_when_invoked_through_path_symlink(self):
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "aris").symlink_to(ARIS_CLI)
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["ARIS_WORKSPACE"] = str(self.workspace)
        project = self.tmp / "path-project"
        project.mkdir()

        result = subprocess.run(
            ["aris", "project", "init", ".", "--direction", "path mode", "--aris-repo", str(self.framework), "--quiet"],
            cwd=str(project),
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue((project / "project.yaml").exists())


if __name__ == "__main__":
    unittest.main()
