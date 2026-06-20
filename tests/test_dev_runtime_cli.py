#!/usr/bin/env python3
"""Behavior tests for the developer runtime CLI."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread


REPO_ROOT = Path(__file__).resolve().parent.parent
LANE_CLI = REPO_ROOT / "tools" / "lane"


class DevRuntimeCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="labline-dev-runtime-"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.framework = self.tmp / "framework"
        (self.framework / "tools").mkdir(parents=True)
        (self.framework / "templates").mkdir()
        (self.framework / "to-developer" / "logs").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _env(self, **extra: str) -> dict:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env.pop("LABLINE_WORKSPACE", None)
        env.update(extra)
        return env

    def _run(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(LANE_CLI), *args, "--labline-repo", str(self.framework), "--quiet"],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            env=env or self._env(),
        )

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

    def test_dev_runtime_config_defaults_and_use_bind_dev_worker_to_deepseek_v4_flash(self) -> None:
        config = self._run("dev", "runtime", "config", "--init")
        self.assertEqual(config.returncode, 0, msg=config.stderr)
        self.assertIn(f"config: {self.home / '.labline' / 'dev-runtime.json'}", config.stdout)
        self.assertIn("default_provider: codex_subagent", config.stdout)
        self.assertIn("default_transport: codex_subagent", config.stdout)
        self.assertIn("default_model: gpt-5.4-mini", config.stdout)
        self.assertIn("role.dev-realtest: provider=codex_subagent codex_subagent/gpt-5.4-mini", config.stdout)
        self.assertIn("role.dev-worker: provider=codex_subagent codex_subagent/gpt-5.4-mini", config.stdout)

        config_path = self.home / ".labline" / "dev-runtime.json"
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["defaults"]["provider"], "codex_subagent")
        self.assertEqual(payload["defaults"]["transport"], "codex_subagent")
        self.assertEqual(payload["defaults"]["model"], "gpt-5.4-mini")
        self.assertEqual(payload["roles"]["dev-realtest"]["provider"], "codex_subagent")
        self.assertIn("build and run GPU and non-GPU Docker deployment smoke tests", payload["roles"]["dev-realtest"]["allowed_work"])
        self.assertIn("silently deviating from published docs instead of reporting doc drift", payload["roles"]["dev-realtest"]["forbidden_work"])
        self.assertEqual(payload["roles"]["dev-worker"]["provider"], "codex_subagent")

        provider = self._run(
            "dev",
            "rt",
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
        self.assertEqual(provider.returncode, 0, msg=provider.stderr)
        self.assertIn("provider: deepseek-v4-flash", provider.stdout)
        self.assertIn("transport: openai_compatible", provider.stdout)
        self.assertIn("model: deepseek-v4-flash", provider.stdout)
        self.assertIn("base_url: https://api.deepseek.com/v1", provider.stdout)
        self.assertIn("api_key_env: DEEPSEEK_API_KEY", provider.stdout)

        use = self._run("dev", "rt", "use", "dev-worker", "deepseek-v4-flash")
        self.assertEqual(use.returncode, 0, msg=use.stderr)
        self.assertIn("role: dev-worker", use.stdout)
        self.assertIn("provider: deepseek-v4-flash", use.stdout)
        self.assertIn("transport: openai_compatible", use.stdout)
        self.assertIn("model: deepseek-v4-flash", use.stdout)

        payload = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["providers"]["deepseek-v4-flash"]["transport"], "openai_compatible")
        self.assertEqual(payload["providers"]["deepseek-v4-flash"]["model"], "deepseek-v4-flash")
        self.assertEqual(payload["providers"]["deepseek-v4-flash"]["base_url"], "https://api.deepseek.com/v1")
        self.assertEqual(payload["providers"]["deepseek-v4-flash"]["api_key_env"], "DEEPSEEK_API_KEY")
        self.assertEqual(payload["roles"]["dev-worker"]["provider"], "deepseek-v4-flash")
        self.assertEqual(payload["roles"]["dev-worker"]["transport"], "openai_compatible")
        self.assertEqual(payload["roles"]["dev-worker"]["model"], "deepseek-v4-flash")

    def test_dev_runtime_config_json_output_is_parseable_and_secret_safe(self) -> None:
        env_file = self.tmp / ".env"
        env_file.write_text(
            "\n".join(
                [
                    "agent=dev-worker",
                    "provider=deepseek-v4-flash",
                    "base_url=https://api.deepseek.com/v1",
                    "api_key=super-secret-value",
                    "model_name=deepseek-v4-flash",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        load = self._run("dev", "rt", "load", str(env_file))
        self.assertEqual(load.returncode, 0, msg=load.stderr)

        result = self._run("dev", "rt", "config", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["config"], str(self.home / ".labline" / "dev-runtime.json"))
        self.assertEqual(payload["providers"]["deepseek-v4-flash"]["model"], "deepseek-v4-flash")
        self.assertEqual(payload["providers"]["deepseek-v4-flash"]["api_key_env"], "LABLINE_DEV_RT_DEEPSEEK_V4_FLASH_API_KEY")
        self.assertEqual(payload["roles"]["dev-worker"]["provider"], "deepseek-v4-flash")
        self.assertNotIn("super-secret-value", result.stdout)

    def test_dev_runtime_prompt_writes_guardrailed_task_file_and_never_leaks_api_key(self) -> None:
        self._run(
            "dev",
            "rt",
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
        self._run("dev", "rt", "use", "dev-worker", "deepseek-v4-flash")

        env = self._env(DEEPSEEK_API_KEY="super-secret-value")
        result = self._run(
            "dev",
            "runtime",
            "prompt",
            "dev-worker",
            "batch a docs sweep",
            "--provider",
            "deepseek-v4-flash",
            "--file",
            "docs/FEISHU_INTEGRATION.md",
            env=env,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("runtime_provider: deepseek-v4-flash", result.stdout)
        self.assertIn("runtime_transport: openai_compatible", result.stdout)
        self.assertIn("runtime_model: deepseek-v4-flash", result.stdout)
        self.assertIn("runtime_base_url: https://api.deepseek.com/v1", result.stdout)
        self.assertIn("runtime_api_key_env: DEEPSEEK_API_KEY", result.stdout)
        self.assertIn("spawn_hint: use this prompt with a low-cost dev runtime role and review its patch before applying", result.stdout)
        self.assertNotIn("super-secret-value", result.stdout)

        task_line = next(line for line in result.stdout.splitlines() if line.startswith("task_file: "))
        task_file = Path(task_line.split(": ", 1)[1])
        self.assertTrue(task_file.exists())
        content = task_file.read_text(encoding="utf-8")
        self.assertIn("# Labline Dev Runtime Task", content)
        self.assertIn("role: dev-worker", content)
        self.assertIn("provider: deepseek-v4-flash", content)
        self.assertIn("transport: openai_compatible", content)
        self.assertIn("model: deepseek-v4-flash", content)
        self.assertIn("base_url: https://api.deepseek.com/v1", content)
        self.assertIn("api_key_env: DEEPSEEK_API_KEY", content)
        self.assertIn("You are not alone in the codebase.", content)
        self.assertIn("Stay inside the declared write scope.", content)
        self.assertIn("Never log, print, or persist API key values; only record the environment variable name.", content)
        self.assertIn("- docs/FEISHU_INTEGRATION.md", content)
        self.assertNotIn("super-secret-value", content)

    def test_dev_realmachine_tester_prompt_documents_real_server_scope(self) -> None:
        result = self._run(
            "dev",
            "rt",
            "prompt",
            "dev-realtest",
            "validate Docker deployment on the 5090 server",
            "--file",
            "deploy/DEPLOY_GUIDE.md",
            "--file",
            "deploy/docker-compose.gpu.yaml",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("runtime_provider: codex_subagent", result.stdout)

        task_line = next(line for line in result.stdout.splitlines() if line.startswith("task_file: "))
        task_file = Path(task_line.split(": ", 1)[1])
        content = task_file.read_text(encoding="utf-8")
        self.assertIn("# Labline Dev Runtime Task", content)
        self.assertIn("role: dev-realtest", content)
        self.assertIn("validate Docker deployment on the 5090 server", content)
        self.assertIn("Allowed work:", content)
        self.assertIn("follow published deployment and operations docs on a real managed server", content)
        self.assertIn("build and run GPU and non-GPU Docker deployment smoke tests", content)
        self.assertIn("collect versions, container state, logs, command output summaries, and pass/fail evidence", content)
        self.assertIn("Forbidden work:", content)
        self.assertIn("destructive server cleanup without explicit maintainer approval", content)
        self.assertIn("silently deviating from published docs instead of reporting doc drift", content)
        self.assertIn("- deploy/DEPLOY_GUIDE.md", content)
        self.assertIn("- deploy/docker-compose.gpu.yaml", content)

    def test_dev_runtime_load_env_file_binds_provider_and_run_uses_saved_secret(self) -> None:
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received["path"] = self.path
                received["auth"] = self.headers.get("Authorization")
                length = int(self.headers.get("Content-Length", "0"))
                received["body"] = json.loads(self.rfile.read(length).decode("utf-8"))
                payload = {"choices": [{"message": {"content": "loaded env result"}}]}
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format, *args):
                return

        server = self._start_http_server(Handler)
        env_file = self.tmp / ".env"
        env_file.write_text(
            "\n".join(
                [
                    "agent=dev-worker",
                    "provider=deepseek-v4-flash",
                    f"base_url=http://127.0.0.1:{server.server_port}",
                    "api_key=super-secret-value",
                    "model_name=deepseek-v4-flash",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        load = self._run("dev", "rt", "load", str(env_file))
        self.assertEqual(load.returncode, 0, msg=load.stderr)
        self.assertIn("agent: dev-worker", load.stdout)
        self.assertIn("provider: deepseek-v4-flash", load.stdout)
        self.assertIn("model: deepseek-v4-flash", load.stdout)
        self.assertIn("api_key_env: LABLINE_DEV_RT_DEEPSEEK_V4_FLASH_API_KEY", load.stdout)
        self.assertIn(f"secret_file: {self.home / '.labline' / 'dev-runtime.env'}", load.stdout)
        self.assertNotIn("super-secret-value", load.stdout)

        config = json.loads((self.home / ".labline" / "dev-runtime.json").read_text(encoding="utf-8"))
        provider = config["providers"]["deepseek-v4-flash"]
        self.assertEqual(provider["api_key_env"], "LABLINE_DEV_RT_DEEPSEEK_V4_FLASH_API_KEY")
        self.assertEqual(config["roles"]["dev-worker"]["provider"], "deepseek-v4-flash")
        self.assertNotIn("super-secret-value", json.dumps(config))

        secret_file = self.home / ".labline" / "dev-runtime.env"
        self.assertEqual(secret_file.stat().st_mode & 0o777, 0o600)

        run = self._run("dev", "rt", "run", "dev-worker", "hello from env", "--timeout", "3")
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        self.assertEqual(received["path"], "/chat/completions")
        self.assertEqual(received["auth"], "Bearer super-secret-value")
        self.assertEqual(received["body"]["model"], "deepseek-v4-flash")
        self.assertNotIn("super-secret-value", run.stdout)
        run_dir = Path(next(line for line in run.stdout.splitlines() if line.startswith("run_dir: ")).split(": ", 1)[1])
        self.assertEqual((run_dir / "response.md").read_text(encoding="utf-8"), "loaded env result")
        self.assertNotIn("super-secret-value", (run_dir / "request.json").read_text(encoding="utf-8"))
        self.assertNotIn("super-secret-value", (run_dir / "metadata.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
