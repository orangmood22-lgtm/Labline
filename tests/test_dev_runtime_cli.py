#!/usr/bin/env python3
"""Behavior tests for the developer runtime CLI."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ARIS_CLI = REPO_ROOT / "tools" / "aris"


class DevRuntimeCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aris-dev-runtime-"))
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
        env.pop("ARIS_WORKSPACE", None)
        env.update(extra)
        return env

    def _run(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(ARIS_CLI), *args, "--aris-repo", str(self.framework), "--quiet"],
            cwd=str(self.tmp),
            capture_output=True,
            text=True,
            env=env or self._env(),
        )

    def test_dev_runtime_config_defaults_and_use_bind_dev_worker_to_deepseek_v4_flash(self) -> None:
        config = self._run("dev", "runtime", "config", "--init")
        self.assertEqual(config.returncode, 0, msg=config.stderr)
        self.assertIn(f"config: {self.home / '.aris' / 'dev-runtime.json'}", config.stdout)
        self.assertIn("default_provider: codex_subagent", config.stdout)
        self.assertIn("default_transport: codex_subagent", config.stdout)
        self.assertIn("default_model: gpt-5.4-mini", config.stdout)
        self.assertIn("role.dev-worker: provider=codex_subagent codex_subagent/gpt-5.4-mini", config.stdout)

        config_path = self.home / ".aris" / "dev-runtime.json"
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["defaults"]["provider"], "codex_subagent")
        self.assertEqual(payload["defaults"]["transport"], "codex_subagent")
        self.assertEqual(payload["defaults"]["model"], "gpt-5.4-mini")
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
        self.assertIn("# ARIS Dev Worker Task", content)
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


if __name__ == "__main__":
    unittest.main()
