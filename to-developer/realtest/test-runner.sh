#!/usr/bin/env bash
set -euo pipefail

LOG_ROOT="${LABLINE_REALTEST_LOG_ROOT:-/labline/test-logs}"
TEST_NAME="${LABLINE_REALTEST_NAME:-smoke}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${LOG_ROOT}/${STAMP}-${TEST_NAME}"
LOG_FILE="${LOG_DIR}/run.log"

mkdir -p "$LOG_DIR" /labline/projects
ln -sfn "$LOG_DIR" "${LOG_ROOT}/latest"

run_default_smoke() {
  echo "[realtest] default smoke"
  echo "[realtest] user=$(id -un) cwd=$(pwd)"
  echo "[realtest] framework=/labline/framework"
  python --version
  node --version || true
  git --version
  if command -v codex >/dev/null 2>&1; then codex --version || true; fi
  if command -v claude >/dev/null 2>&1; then claude --version || true; fi
  /labline/framework/tools/lane framework --version --labline-repo /labline/framework
  /labline/framework/tools/lane project init /labline/projects/smoke-project \
    --labline-repo /labline/framework \
    --direction "real-machine smoke test" \
    --no-commit
  /labline/framework/tools/lane project doctor /labline/projects/smoke-project \
    --labline-repo /labline/framework
  /labline/framework/tools/lane project update /labline/projects/smoke-project \
    --labline-repo /labline/framework
}

{
  echo "[realtest] start=${STAMP}"
  echo "[realtest] log_dir=${LOG_DIR}"
  echo "[realtest] command=${LABLINE_REALTEST_COMMAND:-<default-smoke>}"
  if [ -n "${LABLINE_REALTEST_COMMAND:-}" ]; then
    bash -lc "$LABLINE_REALTEST_COMMAND"
  else
    run_default_smoke
  fi
  echo "[realtest] status=pass"
} 2>&1 | tee "$LOG_FILE"
