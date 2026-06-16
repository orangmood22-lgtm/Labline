# ARIS Research Framework — Container Image
# Lightweight: no GPU runtime (experiments SSH to GPU servers)
# Base: Ubuntu 22.04 + Node.js + Python 3.11 + Claude Code + Codex CLI

FROM ubuntu:22.04

LABEL maintainer="ARIS Framework"
LABEL description="AI Research Infrastructure — per-user container"

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ─── System packages ─────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git git-lfs openssh-client rsync tmux vim \
    python3.11 python3.11-venv python3-pip \
    ca-certificates gnupg sudo jq tree \
    && rm -rf /var/lib/apt/lists/*

# Make python3.11 default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# ─── Node.js (for Claude Code + Codex CLI) ───────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ─── Claude Code ─────────────────────────────────────────────────────────────
RUN npm install -g @anthropic-ai/claude-code

# ─── Codex CLI ───────────────────────────────────────────────────────────────
RUN npm install -g @openai/codex

# ─── CC-Switch CLI (API provider management) ────────────────────────────────
RUN curl -fsSL https://github.com/SaladDay/cc-switch-cli/releases/latest/download/install.sh | bash \
    || (curl -LO https://github.com/saladday/cc-switch-cli/releases/latest/download/cc-switch-cli-linux-x64-musl.tar.gz \
        && tar -xzf cc-switch-cli-linux-x64-musl.tar.gz \
        && mv cc-switch /usr/local/bin/ \
        && rm -f cc-switch-cli-linux-x64-musl.tar.gz)

# ─── Python scientific stack (lightweight, no torch — that's on GPU servers) ──
RUN pip install --no-cache-dir \
    pyyaml requests matplotlib numpy scipy pandas \
    wandb tensorboard

# ─── Directory structure ─────────────────────────────────────────────────────
RUN mkdir -p /aris/framework /aris/projects /aris/shared/datasets /aris/shared/pretrained

# ─── User setup (non-root) ───────────────────────────────────────────────────
ARG USERNAME=researcher
ARG UID=1000
ARG GID=1000

RUN groupadd -g ${GID} ${USERNAME} \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER ${USERNAME}
WORKDIR /home/${USERNAME}

# ─── ARIS framework clone ────────────────────────────────────────────────────
# Framework cloned at build time; update via /framework-update at runtime
ARG ARIS_REPO=https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git
ARG ARIS_BRANCH=main

RUN git clone --depth 1 -b ${ARIS_BRANCH} ${ARIS_REPO} /aris/framework || true

# ─── Config directories ─────────────────────────────────────────────────────
RUN mkdir -p ~/.claude ~/.codex ~/.aris ~/.ssh \
    && chmod 700 ~/.ssh

# ─── Default API config (user overrides via mount or `aris project init`) ────
COPY templates/api-config.yaml.tmpl /home/${USERNAME}/.aris/api.yaml

# ─── Entrypoint ──────────────────────────────────────────────────────────────
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
USER root
RUN chmod +x /usr/local/bin/entrypoint.sh
USER ${USERNAME}

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
