#!/usr/bin/env bash
# Sync the current Labline dev checkout to a remote framework directory.
#
# Default mode is dry-run. Pass --apply to write to the remote.

set -euo pipefail

HOST="${LABLINE_DEV_SYNC_HOST:-}"
REMOTE_FRAMEWORK="${LABLINE_DEV_SYNC_REMOTE_FRAMEWORK:-/data/Labline/framework}"
BRIDGE_CLI="${LABLINE_DEV_SYNC_BRIDGE_CLI:-}"
TRANSPORT="${LABLINE_DEV_SYNC_TRANSPORT:-auto}"
APPLY=false
PATCH_BRIDGE=false

usage() {
  cat <<'EOF'
Usage:
  LABLINE_DEV_SYNC_HOST=<ssh-host> to-developer/scripts/sync_dev_framework_remote.sh [--apply] [--patch-bridge]

Options:
  --host HOST                 SSH host alias.
  --remote-framework PATH     Remote framework directory.
  --patch-bridge              Run Labline lark-channel-bridge patcher after sync.
  --bridge-cli PATH           Remote bridge dist/cli.js or package bin path.
  --transport auto|rsync|tar  Sync transport. tar fallback does not delete stale remote files.
  --apply                     Actually write changes. Without this, rsync is dry-run.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --remote-framework)
      REMOTE_FRAMEWORK="$2"
      shift 2
      ;;
    --patch-bridge)
      PATCH_BRIDGE=true
      shift
      ;;
    --bridge-cli)
      BRIDGE_CLI="$2"
      shift 2
      ;;
    --transport)
      TRANSPORT="$2"
      shift 2
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$TRANSPORT" in
  auto|rsync|tar) ;;
  *)
    echo "invalid --transport: $TRANSPORT" >&2
    exit 2
    ;;
esac

if [[ -z "$HOST" ]]; then
  echo "LABLINE_DEV_SYNC_HOST or --host is required" >&2
  exit 2
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

EXCLUDES=(
  .git/
  .labline/
  .agents/
  .claude/
  .codex/
  __pycache__/
  .pytest_cache/
  .mypy_cache/
  .ruff_cache/
  node_modules/
  recovered-patches/
  logs-orang/
  to-developer/logs/dev-runtime/
  to-developer/logs/dev-workflow/
  to-developer/discussions/settings*.json
  to-developer/discussions/ssh.txt
  .env
  .env.*
)

have_local_rsync=false
have_remote_rsync=false
if command -v rsync >/dev/null 2>&1; then
  have_local_rsync=true
fi
if ssh "$HOST" "command -v rsync >/dev/null 2>&1"; then
  have_remote_rsync=true
fi

if [[ "$TRANSPORT" == auto ]]; then
  if [[ "$have_local_rsync" == true && "$have_remote_rsync" == true ]]; then
    TRANSPORT=rsync
  else
    TRANSPORT=tar
  fi
fi

if [[ "$TRANSPORT" == rsync && ( "$have_local_rsync" != true || "$have_remote_rsync" != true ) ]]; then
  echo "rsync transport requires rsync on both local and remote hosts" >&2
  exit 127
fi

ssh "$HOST" "mkdir -p '$REMOTE_FRAMEWORK'"

if [[ "$TRANSPORT" == rsync ]]; then
  RSYNC_ARGS=(-az --delete --itemize-changes)
  for pattern in "${EXCLUDES[@]}"; do
    RSYNC_ARGS+=("--exclude=$pattern")
  done
  if [[ "$APPLY" != true ]]; then
    RSYNC_ARGS=(-n "${RSYNC_ARGS[@]}")
  fi
  rsync "${RSYNC_ARGS[@]}" ./ "$HOST:$REMOTE_FRAMEWORK/"
else
  if [[ "$APPLY" != true ]]; then
    echo "tar transport dry-run is not available because remote rsync is missing; rerun with --apply to stream files without deleting stale remote files" >&2
    exit 127
  fi
  TAR_ARGS=(-czf -)
  for pattern in "${EXCLUDES[@]}"; do
    TAR_ARGS+=("--exclude=$pattern")
  done
  tar "${TAR_ARGS[@]}" . | ssh "$HOST" "tar -xzf - -C '$REMOTE_FRAMEWORK'"
  echo "sync transport: tar (stale remote files are not deleted)"
fi

if [[ "$PATCH_BRIDGE" == true && "$APPLY" == true ]]; then
  if [[ -z "$BRIDGE_CLI" ]]; then
    BRIDGE_CLI="/root/.labline/node/lib/node_modules/lark-channel-bridge/dist/cli.js"
  fi
  PATCH_ARGS=("$REMOTE_FRAMEWORK/tools/patch_lark_channel_bridge_labline.py" --bridge-cli "$BRIDGE_CLI" --framework "$REMOTE_FRAMEWORK")
  PATCH_ARGS+=(--apply)
  REMOTE_PATCH_CMD="$(printf '%q ' python3 "${PATCH_ARGS[@]}")"
  ssh "$HOST" "$REMOTE_PATCH_CMD"
elif [[ "$PATCH_BRIDGE" == true ]]; then
  echo "patch-bridge: dry-run skipped; patcher runs after --apply sync"
fi

if [[ "$APPLY" == true ]]; then
  echo "sync: applied to $HOST:$REMOTE_FRAMEWORK"
else
  echo "sync: dry-run only; rerun with --apply to modify $HOST:$REMOTE_FRAMEWORK"
fi
