#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="$SCRIPT_DIR/check_release_ready.py"
PYTHON_BIN="${PYTHON:-python3}"
REPO="."
APPLY=0
PUSH_TAG=0
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="$2"
      shift 2
      ;;
    --apply)
      APPLY=1
      shift
      ;;
    --push-tag)
      PUSH_TAG=1
      shift
      ;;
    --help|-h)
      cat <<'USAGE'
Usage:
  tools/release/tag_release.sh [vX.Y.Z | --bump patch|minor] [--apply] [--push-tag]

Default mode is dry-run. Use --apply to create a local annotated tag.
Use --push-tag in addition to --apply to push the tag to origin.
USAGE
      exit 0
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ "$PUSH_TAG" -eq 1 && "$APPLY" -ne 1 ]]; then
  echo "ERROR: --push-tag requires --apply" >&2
  exit 2
fi

"$PYTHON_BIN" "$CHECKER" --repo "$REPO" "${ARGS[@]}"
VERSION="$("$PYTHON_BIN" "$CHECKER" --repo "$REPO" "${ARGS[@]}" --print-version-only)"

if [[ "$APPLY" -ne 1 ]]; then
  echo "DRY RUN: would create annotated tag $VERSION in $REPO"
  echo "Run with --apply to create the local tag."
  exit 0
fi

git -C "$REPO" tag -a "$VERSION" -m "Labline $VERSION"
echo "Created local tag $VERSION"

if [[ "$PUSH_TAG" -eq 1 ]]; then
  git -C "$REPO" push origin "$VERSION"
  echo "Pushed tag $VERSION to origin"
else
  echo "Tag not pushed. Run again with --apply --push-tag to publish it."
fi
