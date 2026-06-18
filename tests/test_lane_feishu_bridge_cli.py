#!/usr/bin/env python3
"""Behavior tests for the Labline Feishu/Lark bridge CLI wrapper."""

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
LANE_CLI = REPO_ROOT / "tools" / "lane"


class FeishuBridgeCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lane-feishu-cli-"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.framework = self.tmp / "framework"
        (self.framework / "tools").mkdir(parents=True)
        (self.framework / "templates").mkdir()
        self._write_executable("node", "printf 'v20.12.0\\n'\n")
        self._write_executable("lark-channel-bridge", "printf '0.3.1\\n'\n")
        self._write_executable("codex", "printf 'codex fake\\n'\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_executable(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body, encoding="utf-8")
        path.chmod(0o755)

    def _env(self, **extra: str) -> dict:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env.pop("LABLINE_WORKSPACE", None)
        env.update(extra)
        return env

    def _run(self, *args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(LANE_CLI), "--labline-repo", str(self.framework), *args],
            cwd=str(cwd or self.tmp),
            capture_output=True,
            text=True,
            env=env or self._env(),
        )

    def test_feishu_install_dry_run_uses_lark_channel_bridge_package(self) -> None:
        npm = self._run("feishu", "install", "--dry-run")
        self.assertEqual(npm.returncode, 0, msg=npm.stderr)
        self.assertIn(f"command: npm i -g --prefix {self.home / '.labline' / 'node'} lark-channel-bridge", npm.stdout)
        self.assertIn(f"bin_dir: {self.home / '.labline' / 'node' / 'bin'}", npm.stdout)

        pnpm = self._run("feishu", "install", "--manager", "pnpm", "--dry-run")
        self.assertEqual(pnpm.returncode, 0, msg=pnpm.stderr)
        self.assertIn(f"command: pnpm add -g --global-bin-dir {self.home / '.labline' / 'node' / 'bin'} lark-channel-bridge", pnpm.stdout)

        system = self._run("feishu", "install", "--scope", "system", "--dry-run")
        self.assertEqual(system.returncode, 0, msg=system.stderr)
        self.assertIn("command: npm i -g lark-channel-bridge", system.stdout)

    def test_feishu_run_dry_run_defaults_to_codex_profile_and_current_workspace(self) -> None:
        project = self.tmp / "project"
        project.mkdir()

        result = self._run("feishu", "run", "--dry-run", cwd=project)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("lark-channel-bridge run", result.stdout)
        self.assertIn("--profile labline-codex", result.stdout)
        self.assertIn("--agent codex", result.stdout)
        self.assertIn(f"--workspace {project}", result.stdout)

    def test_feishu_start_can_target_claude_lark_and_app_id(self) -> None:
        project = self.tmp / "project"
        project.mkdir()

        result = self._run(
            "feishu",
            "start",
            "--profile",
            "labline-claude",
            "--agent",
            "claude",
            "--workspace",
            str(project),
            "--app-id",
            "cli_xxx",
            "--tenant",
            "lark",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--profile labline-claude", result.stdout)
        self.assertIn("--agent claude", result.stdout)
        self.assertIn(f"--workspace {project}", result.stdout)
        self.assertIn("--app-id cli_xxx", result.stdout)
        self.assertIn("--tenant lark", result.stdout)

    def test_feishu_doctor_reports_bridge_agent_and_state_paths(self) -> None:
        result = self._run("feishu", "doctor", "--home", str(self.tmp / "lark-home"))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("node: ok", result.stdout)
        self.assertIn("lark-channel-bridge: ok (0.3.1)", result.stdout)
        self.assertIn("agent.codex: ok", result.stdout)
        self.assertIn("profile: labline-codex", result.stdout)
        self.assertIn(f"home: {self.tmp / 'lark-home'}", result.stdout)

    def test_feishu_doctor_warns_when_lowercase_and_uppercase_proxy_differ(self) -> None:
        result = self._run(
            "feishu",
            "doctor",
            env=self._env(
                http_proxy="http://bad-proxy:10808",
                HTTP_PROXY="http://good-proxy:7897",
                https_proxy="http://bad-proxy:10808",
                HTTPS_PROXY="http://good-proxy:7897",
            ),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("proxy.http_proxy: http://bad-proxy:10808", result.stdout)
        self.assertIn("proxy.HTTP_PROXY: http://good-proxy:7897", result.stdout)
        self.assertIn("proxy.warning: http_proxy and HTTP_PROXY differ", result.stdout)
        self.assertIn("proxy.warning: https_proxy and HTTPS_PROXY differ", result.stdout)

    def test_feishu_bridge_run_sets_user_local_npm_prefix_for_child_auto_installs(self) -> None:
        log = self.tmp / "bridge-env.txt"
        self._write_executable(
            "lark-channel-bridge",
            "\n".join(
                [
                    "if [[ \"${1:-}\" == \"--version\" ]]; then printf '0.3.1\\n'; exit 0; fi",
                    "printf 'NPM_CONFIG_PREFIX=%s\\n' \"${NPM_CONFIG_PREFIX:-}\" > \"$LABLINE_FAKE_BRIDGE_LOG\"",
                    "printf 'npm_config_prefix=%s\\n' \"${npm_config_prefix:-}\" >> \"$LABLINE_FAKE_BRIDGE_LOG\"",
                    "printf 'PATH=%s\\n' \"$PATH\" >> \"$LABLINE_FAKE_BRIDGE_LOG\"",
                ]
            )
            + "\n",
        )

        result = self._run(
            "feishu",
            "status",
            "--home",
            str(self.tmp / "lark-home"),
            env=self._env(LABLINE_FAKE_BRIDGE_LOG=str(log)),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        content = log.read_text(encoding="utf-8")
        self.assertIn(f"NPM_CONFIG_PREFIX={self.home / '.labline' / 'node'}", content)
        self.assertIn(f"npm_config_prefix={self.home / '.labline' / 'node'}", content)
        self.assertIn(str(self.home / ".labline" / "node" / "bin"), content)

    def test_feishu_bridge_no_proxy_clears_proxy_env_for_node_sdk(self) -> None:
        log = self.tmp / "bridge-no-proxy-env.txt"
        self._write_executable(
            "lark-channel-bridge",
            "\n".join(
                [
                    "if [[ \"${1:-}\" == \"--version\" ]]; then printf '0.3.1\\n'; exit 0; fi",
                    "printf 'http_proxy=%s\\n' \"${http_proxy:-}\" > \"$LABLINE_FAKE_BRIDGE_LOG\"",
                    "printf 'https_proxy=%s\\n' \"${https_proxy:-}\" >> \"$LABLINE_FAKE_BRIDGE_LOG\"",
                    "printf 'HTTP_PROXY=%s\\n' \"${HTTP_PROXY:-}\" >> \"$LABLINE_FAKE_BRIDGE_LOG\"",
                    "printf 'HTTPS_PROXY=%s\\n' \"${HTTPS_PROXY:-}\" >> \"$LABLINE_FAKE_BRIDGE_LOG\"",
                ]
            )
            + "\n",
        )

        result = self._run(
            "feishu",
            "run",
            "--no-proxy",
            env=self._env(
                LABLINE_FAKE_BRIDGE_LOG=str(log),
                http_proxy="http://bad-proxy:10808",
                https_proxy="http://bad-proxy:10808",
                HTTP_PROXY="http://good-proxy:7897",
                HTTPS_PROXY="http://good-proxy:7897",
            ),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        content = log.read_text(encoding="utf-8")
        self.assertIn("http_proxy=\n", content)
        self.assertIn("https_proxy=\n", content)
        self.assertIn("HTTP_PROXY=\n", content)
        self.assertIn("HTTPS_PROXY=\n", content)

    def test_feishu_logs_tails_latest_profile_log(self) -> None:
        logs = self.tmp / "lark-home" / "profiles" / "labline-codex" / "logs" / "daemon"
        logs.mkdir(parents=True)
        (logs / "bridge.jsonl").write_text(
            textwrap.dedent(
                """\
                {"event":"one"}
                {"event":"two"}
                {"event":"three"}
                """
            ),
            encoding="utf-8",
        )

        result = self._run("feishu", "logs", "--home", str(self.tmp / "lark-home"), "--tail", "2")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(f"logs: {self.tmp / 'lark-home' / 'profiles' / 'labline-codex' / 'logs'}", result.stdout)
        self.assertNotIn('{"event":"one"}', result.stdout)
        self.assertIn('{"event":"two"}', result.stdout)
        self.assertIn('{"event":"three"}', result.stdout)


if __name__ == "__main__":
    unittest.main()
