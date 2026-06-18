#!/bin/bash
# tools/sync.sh — Standalone sync script (no Claude Code needed)
# Can be called directly or by /sync skill
#
# Usage:
#   bash sync.sh push [--message "msg"]
#   bash sync.sh pull
#   bash sync.sh deploy [--server NAME]
#   bash sync.sh status

set -euo pipefail

# ─── Find project root (has project.yaml) ────────────────────────────────────
find_project_root() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        [ -f "$dir/project.yaml" ] && echo "$dir" && return 0
        dir="$(dirname "$dir")"
    done
    echo "ERROR: No project.yaml found. Not in Labline project." >&2
    exit 1
}

PROJECT_DIR=$(find_project_root)
cd "$PROJECT_DIR"

# ─── Parse project.yaml (basic, no deps) ─────────────────────────────────────
yaml_get() {
    # Simple yaml value extractor: yaml_get "git.remote" project.yaml
    local key="$1" file="${2:-project.yaml}"
    grep -A0 "^  ${key##*.}:" "$file" 2>/dev/null | head -1 | sed 's/.*: *"\?\([^"]*\)"\?.*/\1/' | sed 's/^ *//;s/ *$//'
}

yaml_list() {
    # Extract list items under a key
    local key="$1" file="${2:-project.yaml}"
    sed -n "/^${key}:/,/^[^ ]/p" "$file" | grep '^ *-' | sed 's/^ *- *"\?\([^"]*\)"\?.*/\1/'
}

GIT_REMOTE=$(yaml_get "remote" project.yaml)
GIT_BRANCH=$(yaml_get "branch" project.yaml)
GIT_BRANCH="${GIT_BRANCH:-main}"
AUTO_COMMIT=$(yaml_get "auto_commit" project.yaml)
AUTO_COMMIT="${AUTO_COMMIT:-true}"

# ─── Build exclude args ──────────────────────────────────────────────────────
EXCLUDE_ARGS=""
while IFS= read -r pattern; do
    [ -n "$pattern" ] && EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$pattern"
done <<< "$(yaml_list "sync_exclude")"

# ─── Commands ─────────────────────────────────────────────────────────────────
ACTION="${1:-push}"
shift 2>/dev/null || true

case "$ACTION" in
push)
    MSG=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --message|-m) MSG="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    # Check dirty
    if [ -z "$(git status --porcelain)" ]; then
        echo "✅ Nothing to sync. Already clean."
        exit 0
    fi

    # Auto commit
    git add -A
    if [ -z "$MSG" ]; then
        CHANGED=$(git diff --cached --stat | tail -1 | sed 's/^ *//')
        MSG="sync: $(date '+%Y-%m-%d %H:%M') — $CHANGED"
    fi
    git commit -m "$MSG"

    # Push if remote configured
    if [ -n "$GIT_REMOTE" ] && git remote | grep -q .; then
        git push origin "$GIT_BRANCH" 2>&1
        echo "✅ Pushed to remote."
    else
        echo "✅ Committed locally (no remote configured)."
    fi
    ;;

pull)
    if [ -z "$GIT_REMOTE" ]; then
        echo "No remote configured. Nothing to pull."
        exit 0
    fi

    STASHED=false
    if [ -n "$(git status --porcelain)" ]; then
        git stash push -m "auto-stash $(date '+%H:%M')"
        STASHED=true
    fi

    git pull origin "$GIT_BRANCH" --rebase

    if [ "$STASHED" = true ]; then
        git stash pop || echo "⚠️ Stash conflict. Run: git stash show -p"
    fi
    echo "✅ Pulled latest."
    ;;

deploy)
    TARGET_SERVER=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --server|-s) TARGET_SERVER="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    # Parse servers from project.yaml
    SERVERS=$(python3 -c "
import yaml, sys
with open('project.yaml') as f:
    cfg = yaml.safe_load(f)
servers = cfg.get('servers', []) or []
for s in servers:
    if not s: continue
    name = s.get('name','')
    host = s.get('host','')
    path = s.get('path','')
    if host and path:
        print(f'{name}|{host}|{path}')
" 2>/dev/null)

    if [ -z "$SERVERS" ]; then
        echo "No servers configured in project.yaml."
        exit 1
    fi

    while IFS='|' read -r name host path; do
        [ -z "$host" ] && continue
        if [ -n "$TARGET_SERVER" ] && [ "$name" != "$TARGET_SERVER" ]; then
            continue
        fi

        echo "🚀 Deploying to $name ($host:$path)..."
        ssh "$host" "mkdir -p $path"
        rsync -avz --delete \
            $EXCLUDE_ARGS \
            --exclude='.git/' \
            ./ "${host}:${path}/"
        echo "✅ Deployed to $name."
    done <<< "$SERVERS"
    ;;

status)
    echo "📂 Project: $(basename "$PROJECT_DIR")"
    echo "🌿 Branch:  $(git branch --show-current)"

    # Local status
    MODIFIED=$(git status --porcelain | wc -l)
    echo "📝 Local:   $MODIFIED file(s) changed"

    # Remote status
    if [ -n "$GIT_REMOTE" ] && git remote | grep -q .; then
        git fetch origin "$GIT_BRANCH" 2>/dev/null || true
        AHEAD=$(git rev-list --count "origin/$GIT_BRANCH..$GIT_BRANCH" 2>/dev/null || echo "?")
        BEHIND=$(git rev-list --count "$GIT_BRANCH..origin/$GIT_BRANCH" 2>/dev/null || echo "?")
        echo "🔗 Remote:  $GIT_REMOTE"
        echo "   Status:  $AHEAD ahead, $BEHIND behind"
    else
        echo "🔗 Remote:  (none)"
    fi

    # Server status
    echo "🖥️  Servers:"
    python3 -c "
import yaml
with open('project.yaml') as f:
    cfg = yaml.safe_load(f)
servers = cfg.get('servers', []) or []
if not servers:
    print('   (none configured)')
for s in servers:
    if not s: continue
    print(f\"   {s.get('name','?')}: {s.get('host','')}:{s.get('path','')}\")
" 2>/dev/null || echo "   (parse error)"
    ;;

*)
    echo "Usage: sync.sh [push|pull|deploy|status] [options]"
    echo "  push [--message MSG]     Save & upload"
    echo "  pull                     Fetch latest from remote"
    echo "  deploy [--server NAME]   Rsync to GPU server"
    echo "  status                   Show sync state"
    exit 1
    ;;
esac
