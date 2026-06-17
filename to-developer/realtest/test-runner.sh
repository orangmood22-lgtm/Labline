#!/usr/bin/env bash
set -euo pipefail

LOG_ROOT="${ARIS_REALTEST_LOG_ROOT:-/aris/test-logs}"
TEST_NAME="${ARIS_REALTEST_NAME:-smoke}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${LOG_ROOT}/${STAMP}-${TEST_NAME}"
LOG_FILE="${LOG_DIR}/run.log"

mkdir -p "$LOG_DIR" /aris/projects
ln -sfn "$LOG_DIR" "${LOG_ROOT}/latest"

run_default_smoke() {
  echo "[realtest] default smoke"
  echo "[realtest] user=$(id -un) cwd=$(pwd)"
  echo "[realtest] framework=/aris/framework"
  python --version
  node --version || true
  git --version
  if command -v codex >/dev/null 2>&1; then codex --version || true; fi
  if command -v claude >/dev/null 2>&1; then claude --version || true; fi
  /aris/framework/tools/aris framework --version --aris-repo /aris/framework
  /aris/framework/tools/aris project init /aris/projects/smoke-project \
    --aris-repo /aris/framework \
    --direction "real-machine smoke test" \
    --no-commit
  /aris/framework/tools/aris project doctor /aris/projects/smoke-project \
    --aris-repo /aris/framework
  /aris/framework/tools/aris project update /aris/projects/smoke-project \
    --aris-repo /aris/framework
}

{
  echo "[realtest] start=${STAMP}"
  echo "[realtest] log_dir=${LOG_DIR}"
  echo "[realtest] command=${ARIS_REALTEST_COMMAND:-<default-smoke>}"
  if [ -n "${ARIS_REALTEST_COMMAND:-}" ]; then
    bash -lc "$ARIS_REALTEST_COMMAND"
  else
    run_default_smoke
  fi
  echo "[realtest] status=pass"
} 2>&1 | tee "$LOG_FILE"
