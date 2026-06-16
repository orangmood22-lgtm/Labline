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
PROXY_HTTP="${HTTP_PROXY:-${http_proxy:-}}"
PROXY_HTTPS="${HTTPS_PROXY:-${https_proxy:-$PROXY_HTTP}}"
PROXY_NO="${NO_PROXY:-${no_proxy:-127.0.0.1,localhost}}"

if [ -n "$PROXY_HTTP" ]; then
    export HTTP_PROXY="$PROXY_HTTP"
    export HTTPS_PROXY="$PROXY_HTTPS"
    export NO_PROXY="$PROXY_NO"
    export http_proxy="$PROXY_HTTP"
    export https_proxy="$PROXY_HTTPS"
    export no_proxy="$PROXY_NO"
    # Write both upper/lower names for PAM sessions started by docker exec.
    sudo sed -i '/^HTTP_PROXY=/d;/^HTTPS_PROXY=/d;/^NO_PROXY=/d;/^http_proxy=/d;/^https_proxy=/d;/^no_proxy=/d' /etc/environment 2>/dev/null || true
    {
        echo "HTTP_PROXY=\"$HTTP_PROXY\""
        echo "HTTPS_PROXY=\"$HTTPS_PROXY\""
        echo "NO_PROXY=\"$NO_PROXY\""
        echo "http_proxy=\"$http_proxy\""
        echo "https_proxy=\"$https_proxy\""
        echo "no_proxy=\"$no_proxy\""
    } | sudo tee -a /etc/environment >/dev/null
fi

if [ -n "$GIT_HTTP_PROXY" ]; then
    git config --global http.proxy "$GIT_HTTP_PROXY" || true
fi
if [ -n "$GIT_HTTPS_PROXY" ]; then
    git config --global https.proxy "$GIT_HTTPS_PROXY" || true
fi

# ─── SSH key from mount ──────────────────────────────────────────────────────
if [ -d /run/secrets/ssh ]; then
    cp /run/secrets/ssh/* ~/.ssh/ 2>/dev/null || true
    chmod 600 ~/.ssh/id_* 2>/dev/null || true
    chmod 644 ~/.ssh/*.pub 2>/dev/null || true
fi

# ─── Framework update check on boot/shell (if network available) ─────────────
mkdir -p ~/.aris ~/.local/bin
if [ -x /aris/framework/tools/aris ]; then
    ln -sf /aris/framework/tools/aris ~/.local/bin/aris
fi

cat > ~/.aris/aris-shell-hook.sh <<'EOF'
if [ "${ARIS_AUTO_CHECK_UPDATE:-1}" != "0" ] && [ -x /aris/framework/tools/aris ]; then
    (
        timeout "${ARIS_UPDATE_CHECK_TIMEOUT:-10s}" \
            /aris/framework/tools/aris framework check-update \
            --aris-repo /aris/framework \
            --if-stale "${ARIS_UPDATE_CHECK_INTERVAL:-1d}" \
            --notify 2>/dev/null || true
    ) &
fi
EOF

if ! grep -q "ARIS shell hook" ~/.bashrc 2>/dev/null; then
    {
        echo ""
        echo "# ARIS shell hook"
        echo "[ -f ~/.aris/aris-shell-hook.sh ] && . ~/.aris/aris-shell-hook.sh"
    } >> ~/.bashrc
fi

if [ "${ARIS_AUTO_CHECK_UPDATE:-1}" != "0" ] && [ -x /aris/framework/tools/aris ]; then
    timeout "${ARIS_UPDATE_CHECK_TIMEOUT:-10s}" \
        /aris/framework/tools/aris framework check-update \
        --aris-repo /aris/framework \
        --if-stale "${ARIS_UPDATE_CHECK_INTERVAL:-1d}" \
        --notify 2>/dev/null || true
fi

# ─── First boot: create default project dir ──────────────────────────────────
if [ ! -d /aris/projects/.initialized ]; then
    mkdir -p /aris/projects/.initialized
    echo "ARIS container first boot: $(date -Iseconds)" > /aris/projects/.initialized/boot.log
fi

# ─── Execute CMD ─────────────────────────────────────────────────────────────
exec "$@"
