#!/bin/bash
# Labline container entrypoint
# Sets up proxy helpers, SSH, and framework symlinks on first boot

set -e

# ─── API/provider config ────────────────────────────────────────────────────
# Do not write API keys from Docker env into Codex/Claude config files.
# Users configure providers inside the container with cc-switch-cli so keys stay
# personal and accidental group-wide credential reuse is avoided.

# ─── Proxy config ────────────────────────────────────────────────────────────
PROXY_HTTP="${HTTP_PROXY:-${http_proxy:-}}"
PROXY_HTTPS="${HTTPS_PROXY:-${https_proxy:-$PROXY_HTTP}}"
PROXY_NO="${NO_PROXY:-${no_proxy:-127.0.0.1,localhost}}"
LABLINE_PROXY_ENABLED="${LABLINE_PROXY_ENABLED:-1}"

mkdir -p ~/.labline ~/.local/bin

cat > ~/.proxy_env <<EOF
export HTTP_PROXY="${PROXY_HTTP}"
export HTTPS_PROXY="${PROXY_HTTPS}"
export NO_PROXY="${PROXY_NO}"
export http_proxy="${PROXY_HTTP}"
export https_proxy="${PROXY_HTTPS}"
export no_proxy="${PROXY_NO}"
unset ALL_PROXY
unset all_proxy
export NODE_USE_ENV_PROXY=1
EOF

cat > ~/.local/bin/proxy-on <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ ! -s "$HOME/.proxy_env" ]; then
    echo "~/.proxy_env is missing or empty" >&2
    exit 1
fi
if ! grep -q "source ~/.proxy_env # Labline proxy" "$HOME/.bashrc" 2>/dev/null; then
    printf '\nsource ~/.proxy_env # Labline proxy\n' >> "$HOME/.bashrc"
fi
echo "Labline proxy enabled for new shells. Run: source ~/.proxy_env"
EOF

cat > ~/.local/bin/proxy-off <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
sed -i '/source ~\/.proxy_env # Labline proxy/d' "$HOME/.bashrc" 2>/dev/null || true
unset HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy ALL_PROXY all_proxy NODE_USE_ENV_PROXY
echo "Labline proxy disabled for new shells. Current shell env was unset by this process only."
EOF

chmod +x ~/.local/bin/proxy-on ~/.local/bin/proxy-off
export PATH="$HOME/.local/bin:$PATH"
if ! grep -q "Labline local bin" ~/.bashrc 2>/dev/null; then
    {
        echo ""
        echo "# Labline local bin"
        echo 'export PATH="$HOME/.local/bin:$PATH"'
    } >> ~/.bashrc
fi

sudo sed -i '/^HTTP_PROXY=/d;/^HTTPS_PROXY=/d;/^NO_PROXY=/d;/^http_proxy=/d;/^https_proxy=/d;/^no_proxy=/d;/^ALL_PROXY=/d;/^all_proxy=/d;/^NODE_USE_ENV_PROXY=/d' /etc/environment 2>/dev/null || true

if [ "$LABLINE_PROXY_ENABLED" != "0" ] && [ -n "$PROXY_HTTP" ]; then
    # shellcheck disable=SC1090
    . ~/.proxy_env
    # Write both upper/lower names for PAM sessions started by docker exec.
    {
        echo "HTTP_PROXY=\"$HTTP_PROXY\""
        echo "HTTPS_PROXY=\"$HTTPS_PROXY\""
        echo "NO_PROXY=\"$NO_PROXY\""
        echo "http_proxy=\"$http_proxy\""
        echo "https_proxy=\"$https_proxy\""
        echo "no_proxy=\"$no_proxy\""
        echo "NODE_USE_ENV_PROXY=\"1\""
    } | sudo tee -a /etc/environment >/dev/null
    if ! grep -q "source ~/.proxy_env # Labline proxy" ~/.bashrc 2>/dev/null; then
        printf '\nsource ~/.proxy_env # Labline proxy\n' >> ~/.bashrc
    fi
else
    unset HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy ALL_PROXY all_proxy NODE_USE_ENV_PROXY
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
if [ -x /labline/framework/tools/lane ]; then
    ln -sf /labline/framework/tools/lane ~/.local/bin/lane
fi

cat > ~/.labline/labline-shell-hook.sh <<'EOF'
if [ "${LABLINE_AUTO_CHECK_UPDATE:-1}" != "0" ] && [ -x /labline/framework/tools/lane ]; then
    (
        timeout "${LABLINE_UPDATE_CHECK_TIMEOUT:-10s}" \
            /labline/framework/tools/lane framework check-update \
            --labline-repo /labline/framework \
            --if-stale "${LABLINE_UPDATE_CHECK_INTERVAL:-1d}" \
            --notify 2>/dev/null || true
    ) &
fi
EOF

if ! grep -q "Labline shell hook" ~/.bashrc 2>/dev/null; then
    {
        echo ""
        echo "# Labline shell hook"
        echo "[ -f ~/.labline/labline-shell-hook.sh ] && . ~/.labline/labline-shell-hook.sh"
    } >> ~/.bashrc
fi

if [ "${LABLINE_AUTO_CHECK_UPDATE:-1}" != "0" ] && [ -x /labline/framework/tools/lane ]; then
    timeout "${LABLINE_UPDATE_CHECK_TIMEOUT:-10s}" \
        /labline/framework/tools/lane framework check-update \
        --labline-repo /labline/framework \
        --if-stale "${LABLINE_UPDATE_CHECK_INTERVAL:-1d}" \
        --notify 2>/dev/null || true
fi

# ─── First boot: create default project dir ──────────────────────────────────
if [ ! -d /labline/projects/.initialized ]; then
    mkdir -p /labline/projects/.initialized
    echo "Labline container first boot: $(date -Iseconds)" > /labline/projects/.initialized/boot.log
fi

# ─── Execute CMD ─────────────────────────────────────────────────────────────
exec "$@"
