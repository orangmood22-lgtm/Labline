from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_realtest_compose_is_dedicated_and_logs_to_host() -> None:
    compose = read("to-developer/realtest/docker-compose.test.yaml")

    assert "aris-realtest" in compose
    assert "container_name: aris-realtest" in compose
    assert "TEST_FRAMEWORK_PATH" in compose
    assert "TEST_PROJECTS_PATH" in compose
    assert "TEST_LOGS_PATH" in compose
    assert ":/aris/test-logs" in compose
    assert "/aris/framework/to-developer/realtest/test-runner.sh" in compose
    assert "ARIS_AUTO_CHECK_UPDATE=${ARIS_AUTO_CHECK_UPDATE:-0}" in compose


def test_realtest_runner_writes_timestamped_log_and_default_smoke() -> None:
    runner = read("to-developer/realtest/test-runner.sh")

    assert "set -euo pipefail" in runner
    assert 'LOG_ROOT="${ARIS_REALTEST_LOG_ROOT:-/aris/test-logs}"' in runner
    assert 'LOG_FILE="${LOG_DIR}/run.log"' in runner
    assert 'tee "$LOG_FILE"' in runner
    assert "project init /aris/projects/smoke-project" in runner
    assert "project doctor /aris/projects/smoke-project" in runner
    assert "project update /aris/projects/smoke-project" in runner


def test_realtest_env_example_requires_separate_scratch_paths() -> None:
    env = read("to-developer/realtest/.env.test.example")

    for item in [
        "TEST_FRAMEWORK_PATH=[你的framework位置]",
        "TEST_PROJECTS_PATH=[你的实机测试项目临时目录]",
        "TEST_LOGS_PATH=[你的实机测试日志目录]",
        "ARIS_REALTEST_COMMAND=",
        "ARIS_AUTO_CHECK_UPDATE=0",
    ]:
        assert item in env
