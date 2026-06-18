from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_realtest_compose_is_dedicated_and_logs_to_host() -> None:
    compose = read("to-developer/realtest/docker-compose.test.yaml")

    assert "labline-realtest" in compose
    assert "container_name: labline-realtest" in compose
    assert "TEST_FRAMEWORK_PATH" in compose
    assert "TEST_PROJECTS_PATH" in compose
    assert "TEST_LOGS_PATH" in compose
    assert ":/labline/test-logs" in compose
    assert "/labline/framework/to-developer/realtest/test-runner.sh" in compose
    assert "LABLINE_AUTO_CHECK_UPDATE=${LABLINE_AUTO_CHECK_UPDATE:-0}" in compose


def test_realtest_runner_writes_timestamped_log_and_default_smoke() -> None:
    runner = read("to-developer/realtest/test-runner.sh")

    assert "set -euo pipefail" in runner
    assert 'LOG_ROOT="${LABLINE_REALTEST_LOG_ROOT:-/labline/test-logs}"' in runner
    assert 'LOG_FILE="${LOG_DIR}/run.log"' in runner
    assert 'tee "$LOG_FILE"' in runner
    assert "project init /labline/projects/smoke-project" in runner
    assert "project doctor /labline/projects/smoke-project" in runner
    assert "project update /labline/projects/smoke-project" in runner


def test_realtest_env_example_requires_separate_scratch_paths() -> None:
    env = read("to-developer/realtest/.env.test.example")

    for item in [
        "TEST_FRAMEWORK_PATH=[你的framework位置]",
        "TEST_PROJECTS_PATH=[你的实机测试项目临时目录]",
        "TEST_LOGS_PATH=[你的实机测试日志目录]",
        "LABLINE_REALTEST_COMMAND=",
        "LABLINE_AUTO_CHECK_UPDATE=0",
    ]:
        assert item in env
