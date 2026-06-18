# `skills-codex`

Codex-native mirror and adaptation layer for the main Labline `skills/` package.

## Scope

- Base mirror coverage: all user-facing mainline skills under `skills/`
- Support directory: `shared-references/`
- Default reviewer contract for reviewer-heavy skills:
  - round 1: `spawn_agent`
  - follow-up: `send_input`
  - reasoning effort: `xhigh`
- Optional overlays:
  - `skills-codex-claude-review`
  - `skills-codex-gemini-review`

This package is still an appendage to the Claude mainline, not a separate Codex-first product line.

## Recommended Install

Project-local install is the default path for Codex:

```bash
git clone https://github.com/orangmood22-lgtm/Auto-research-in-sleep.git ~/labline_repo
cd ~/your-project

bash ~/labline_repo/tools/install_labline_codex.sh .
```

This creates a flat managed layout:

```text
.agents/skills/<skill-name> -> ~/labline_repo/skills/skills-codex/<skill-name>
.labline/installed-skills-codex.txt
AGENTS.md   # managed Codex block
```

Reconcile after upstream changes:

```bash
cd ~/labline_repo && git pull
bash ~/labline_repo/tools/install_labline_codex.sh ~/your-project --reconcile
```

Uninstall only managed Codex entries:

```bash
bash ~/labline_repo/tools/install_labline_codex.sh ~/your-project --uninstall
```

## Optional Overlays

Install the base first, then choose an overlay:

```bash
bash ~/labline_repo/tools/install_labline_codex.sh ~/your-project --reconcile --with-claude-review-overlay
```

```bash
bash ~/labline_repo/tools/install_labline_codex.sh ~/your-project --reconcile --with-gemini-review-overlay
```

Overlays only replace reviewer routing. They do not replace the base mirror or the executor model.

## Copy Install and Update

If you intentionally use a copied Codex install instead of managed project symlinks:

```bash
mkdir -p ~/.codex/skills
cp -a ~/labline_repo/skills/skills-codex/. ~/.codex/skills/
```

Update copied installs with:

```bash
bash ~/labline_repo/tools/smart_update_codex.sh
bash ~/labline_repo/tools/smart_update_codex.sh --apply
```

For a copied project-local Codex install:

```bash
bash ~/labline_repo/tools/smart_update_codex.sh --project ~/your-project
bash ~/labline_repo/tools/smart_update_codex.sh --project ~/your-project --apply
```

`smart_update_codex.sh` refuses symlink-managed installs and redirects them to `install_labline_codex.sh --reconcile`.

## Non-Degrading Skills

The following Codex skills must not silently degrade when their required capability is missing:

- `comm-lit-review`
- `research-lit`
- `paper-poster`
- `pixel-art`

If the required source, reviewer, or local preview capability is unavailable, the skill should stop and tell the user what to configure.
