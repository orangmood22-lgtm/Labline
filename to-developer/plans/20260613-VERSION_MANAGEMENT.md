# ARIS Version Management

ARIS uses lightweight semantic versioning before `v1.0.0`. This document defines the branch roles, release tags, changelog split, and guarded release tooling.

## Branch Roles

| Branch | Purpose | Tag policy |
|--------|---------|------------|
| `main` | Stable framework line. Research projects should pin versions from here. | Formal release tags only |
| `dev` | Integration line for reviewed but not-yet-released changes. | Prerelease tags only when needed |
| `feature/*` | Short-lived branch for one new capability. Merge to `dev`. | No tags |
| `fix/*` | Short-lived branch for one bug/doc/deploy/compat fix. Merge to `dev` or `main` depending on urgency. | No tags |
| `upstream-base` | Historical upstream/base snapshot. | No new tags |

## Version Numbers

Use formal tags:

```text
vMAJOR.MINOR.PATCH
```

Before `v1.0.0`:

- `v0.MINOR.0` is a user-visible capability release.
- `v0.MINOR.PATCH` is a fix release with normal usage unchanged.
- `v1.0.0` waits until installer behavior, skill schema, dev-to-stable flow, and project pinning are stable.

Current baseline:

```text
v0.1.0 = current main stable baseline
```

## Tag Policy

Formal release tags belong on `main`:

```text
v0.1.0
v0.1.1
v0.2.0
```

`dev` may use prerelease tags only for reproducible testing:

```text
v0.2.0-dev.1
v0.2.0-rc.1
```

Research projects should pin formal release tags, not prerelease tags, unless they intentionally test an unreleased framework snapshot.

## Changelog Split

`CHANGELOG.md` is user-facing. It records only changes users need to know when deciding whether to upgrade.

`to-developer/20260613-DEVELOPMENT_LOG.md` is maintainer-facing. It records module-level changes so maintainers do not reconstruct history from individual commits.

Use this flow:

1. During development, update `to-developer/20260613-DEVELOPMENT_LOG.md` by module.
2. Before release, distill user-visible changes into `CHANGELOG.md`.
3. Use Git history for the full commit-level trace.

## Developer Material Policy

Versioned:

- `to-developer/20260613-DEVELOPMENT_LOG.md`
- `to-developer/plans/*.md`
- `to-developer/deploy-QAs/*.md`
- non-private `to-developer/discussions/*.md`

Ignored:

- `to-developer/discussions/settings*.json`
- `to-developer/discussions/ssh.txt`

Never commit API keys, tokens, server secrets, SSH credentials, or private host notes.

## Release Gates

### Patch Release Gate

Use for `v0.1.0 -> v0.1.1`:

- Current branch is `main`.
- Worktree is clean.
- Target tag does not already exist.
- `CHANGELOG.md` has `## [vX.Y.Z] - YYYY-MM-DD`.
- `to-developer/20260613-DEVELOPMENT_LOG.md` has relevant module entries.
- Related test or manual check passed.

### Minor Release Gate

Use for `v0.1.0 -> v0.2.0`:

- All patch gate items.
- Skill catalog and DAG artifacts are regenerated when skills changed:
  - `docs/SKILL_CATALOG.md`
  - `docs/SKILL_CATALOG_CN.md`
  - `docs/SKILL_DAG.yaml`
  - `docs/SKILL_DAG.mmd`
  - `docs/skill-dag.html`
- Installer or project-template tests pass when installation behavior changed.
- Codex mirror tests pass when skills changed.
- At least one fresh install, `--dev`, or dev-to-stable validation is done for release-significant changes.

## Release Tooling

Check release readiness:

```bash
python3.8 tools/release/check_release_ready.py --bump patch
python3.8 tools/release/check_release_ready.py --bump minor
python3.8 tools/release/check_release_ready.py v0.2.0
```

Tag release safely:

```bash
# Dry-run only. Does not create a tag.
tools/release/tag_release.sh --bump patch

# Create local annotated tag.
tools/release/tag_release.sh --bump patch --apply

# Create and push tag.
tools/release/tag_release.sh --bump patch --apply --push-tag
```

`tag_release.sh` must not create or push tags unless the maintainer passes explicit flags.

## Project Pinning

Project `project.yaml` should record both tag and commit:

```yaml
framework:
  version: "v0.1.0"
  commit: "<commit-sha>"
  recorded_at: "2026-06-13T00:00:00Z"
```

Patch releases should be safe to adopt for most projects. Minor releases should be reviewed before upgrading long-running projects.
