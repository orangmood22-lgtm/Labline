#!/bin/bash
# ARIS container entrypoint
# Sets up API config, SSH, and framework symlinks on first boot

set -e

# ─── API config from env vars ────────────────────────────────────────────────
if [ -n "$ANTHROPIC_API_KEY" ]; then
    mkdir -p ~/.claude
    cat > ~/.claude/settings.json <<EOF
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "$ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL": "${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
  }
}
EOF
fi

if [ -n "$OPENAI_API_KEY" ]; then
    mkdir -p ~/.codex
    cat > ~/.codex/auth.json <<EOF
{"OPENAI_API_KEY": "$OPENAI_API_KEY"}
EOF
fi

# ─── Proxy config ────────────────────────────────────────────────────────────
if [ -n "$HTTP_PROXY" ]; then
    export http_proxy="$HTTP_PROXY"
    export https_proxy="${HTTPS_PROXY:-$HTTP_PROXY}"
    export no_proxy="${NO_PROXY:-127.0.0.1,localhost}"
fi

# ─── SSH key from mount ──────────────────────────────────────────────────────
if [ -d /run/secrets/ssh ]; then
    cp /run/secrets/ssh/* ~/.ssh/ 2>/dev/null || true
    chmod 600 ~/.ssh/id_* 2>/dev/null || true
    chmod 644 ~/.ssh/*.pub 2>/dev/null || true
fi

# ─── Framework update on boot (if network available) ─────────────────────────
if [ -d /aris/framework/.git ]; then
    cd /aris/framework && git pull --ff-only 2>/dev/null || true
fi

# ─── First boot: create default project dir ──────────────────────────────────
if [ ! -d /aris/projects/.initialized ]; then
    mkdir -p /aris/projects/.initialized
    echo "ARIS container first boot: $(date -Iseconds)" > /aris/projects/.initialized/boot.log
fi

# ─── Execute CMD ─────────────────────────────────────────────────────────────
exec "$@"
