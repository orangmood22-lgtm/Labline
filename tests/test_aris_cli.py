#!/usr/bin/env python3
"""Behavior tests for the beginner-facing ARIS CLI."""

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread


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

    def _start_http_server(self, handler_factory):
        server = HTTPServer(("127.0.0.1", 0), handler_factory)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.addCleanup(cleanup)
        return server

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

    def test_framework_version_is_read_only_when_history_directory_is_missing(self):
        workspace = self.tmp / "readonly-workspace"
        workspace.mkdir()
        env = os.environ.copy()
        env["ARIS_WORKSPACE"] = str(workspace)

        result = subprocess.run(
            [str(ARIS_CLI), "framework", "--version", "--aris-repo", str(self.framework), "--quiet"],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("framework:", result.stdout)
        self.assertFalse((workspace / ".aris" / "framework-history").exists())

    def test_framework_state_defaults_to_home_aris_without_workspace_env(self):
        home = self.tmp / "home"
        home.mkdir()
        env = os.environ.copy()
        env.pop("ARIS_WORKSPACE", None)
        env["HOME"] = str(home)

        result = subprocess.run(
            [str(ARIS_CLI), "framework", "check-update", "--no-fetch", "--aris-repo", str(self.framework), "--quiet"],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue((home / ".aris" / "framework-update-status.json").exists())

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

    def test_dev_worker_config_defaults_to_gpt54_mini(self):
        result = self._run(self.tmp, "dev", "worker", "config", "--init")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("default_provider: codex_subagent", result.stdout)
        self.assertIn("default_model: gpt-5.4-mini", result.stdout)
        self.assertIn("default_transport: codex_subagent", result.stdout)

        config = json.loads((self.workspace / ".aris" / "dev-workers.json").read_text())
        self.assertEqual(config["defaults"]["provider"], "codex_subagent")
        self.assertEqual(config["defaults"]["model"], "gpt-5.4-mini")
        self.assertEqual(config["defaults"]["transport"], "codex_subagent")
        self.assertIn("worker", config["roles"])

    def test_dev_worker_provider_set_writes_openai_compatible_provider_config(self):
        result = self._run(
            self.tmp,
            "dev",
            "worker",
            "provider",
            "set",
            "deepseek-v4-flash",
            "--transport",
            "openai_compatible",
            "--model",
            "deepseek-v4-flash",
            "--base-url",
            "https://api.deepseek.com/v1",
            "--api-key-env",
            "DEEPSEEK_API_KEY",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        config = json.loads((self.workspace / ".aris" / "dev-workers.json").read_text())
        provider = config["providers"]["deepseek-v4-flash"]
        self.assertEqual(provider["transport"], "openai_compatible")
        self.assertEqual(provider["model"], "deepseek-v4-flash")
        self.assertEqual(provider["base_url"], "https://api.deepseek.com/v1")
        self.assertEqual(provider["api_key_env"], "DEEPSEEK_API_KEY")

    def test_dev_worker_prompt_uses_named_provider_and_never_writes_key_value(self):
        self._run(
            self.tmp,
            "dev",
            "worker",
            "provider",
            "set",
            "deepseek-v4-flash",
            "--transport",
            "openai_compatible",
            "--model",
            "deepseek-v4-flash",
            "--base-url",
            "https://api.deepseek.com/v1",
            "--api-key-env",
            "DEEPSEEK_API_KEY",
        )
        env = os.environ.copy()
        env["ARIS_WORKSPACE"] = str(self.workspace)
        env["DEEPSEEK_API_KEY"] = "super-secret-value"
        env["NO_PROXY"] = "127.0.0.1,localhost"
        env["no_proxy"] = "127.0.0.1,localhost"
        result = subprocess.run(
            [
                str(ARIS_CLI),
                "dev",
                "worker",
                "prompt",
                "batch a docs sweep",
                "--provider",
                "deepseek-v4-flash",
                "--file",
                "docs/FEISHU_INTEGRATION.md",
                "--aris-repo",
                str(self.framework),
                "--quiet",
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn("super-secret-value", result.stdout)
        task_line = next(line for line in result.stdout.splitlines() if line.startswith("task_file: "))
        task_path = Path(task_line.split(": ", 1)[1])
        content = task_path.read_text()
        self.assertIn("provider: deepseek-v4-flash", content)
        self.assertIn("api_key_env: DEEPSEEK_API_KEY", content)
        self.assertIn("- docs/FEISHU_INTEGRATION.md", content)
        self.assertNotIn("super-secret-value", content)

    def test_dev_worker_run_openai_compatible_posts_messages_and_writes_artifacts(self):
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received["path"] = self.path
                received["auth"] = self.headers.get("Authorization")
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                received["body"] = json.loads(body)
                payload = {"choices": [{"message": {"content": "worker result"}}]}
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format, *args):
                return

        server = self._start_http_server(Handler)
        base_url = f"http://127.0.0.1:{server.server_port}"
        self._run(
            self.tmp,
            "dev",
            "worker",
            "provider",
            "set",
            "deepseek-v4-flash",
            "--transport",
            "openai_compatible",
            "--model",
            "deepseek-v4-flash",
            "--base-url",
            base_url,
            "--api-key-env",
            "DEEPSEEK_API_KEY",
        )
        env = os.environ.copy()
        env["ARIS_WORKSPACE"] = str(self.workspace)
        env["DEEPSEEK_API_KEY"] = "super-secret-value"
        result = subprocess.run(
            [
                str(ARIS_CLI),
                "dev",
                "worker",
                "run",
                "write a tiny finding",
                "--provider",
                "deepseek-v4-flash",
                "--timeout",
                "3",
                "--aris-repo",
                str(self.framework),
                "--quiet",
            ],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(received["path"], "/chat/completions")
        self.assertEqual(received["auth"], "Bearer super-secret-value")
        self.assertEqual(received["body"]["model"], "deepseek-v4-flash")
        self.assertIn("ARIS Dev Worker Guardrails", received["body"]["messages"][0]["content"])
        self.assertIn("write a tiny finding", received["body"]["messages"][1]["content"])
        self.assertNotIn("super-secret-value", result.stdout)

        run_line = next(line for line in result.stdout.splitlines() if line.startswith("run_dir: "))
        run_dir = Path(run_line.split(": ", 1)[1])
        self.assertEqual((run_dir / "response.md").read_text(), "worker result")
        metadata = json.loads((run_dir / "metadata.json").read_text())
        self.assertEqual(metadata["api_key_env"], "DEEPSEEK_API_KEY")
        self.assertNotIn("super-secret-value", (run_dir / "request.json").read_text())
        self.assertNotIn("super-secret-value", (run_dir / "metadata.json").read_text())

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
