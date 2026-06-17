# ADR-0005: Developer Skills Use a Separate Install Surface

**状态：** 已采纳
**日期：** 2026-06-17
**决策者：** orangmood + AI

ARIS separates User Skills from Developer Skills. User Skills live in the user-facing skill graph and may be installed into research projects or promoted to the Stable Line. Developer Skills use a `dev-` prefix, live under the development-side surface, and are installed only into the ARIS dev checkout for framework maintenance work.

We will add a separate Codex-only dev skills installer instead of extending the user project installers. Reusing `install_aris.sh` or `install_aris_codex.sh` would blur project/user boundaries and make it too easy to sync maintainer-only tools into research projects. A dedicated dev installer keeps manifests, symlinks, update checks, and release gates separate: project installers only install User Skills, while the dev installer only links `dev-*` Developer Skills into the dev checkout's `.agents/skills/`. It does not create `.claude/skills/dev-*` links in the first version, and `aris dev user-surface ...` must not implicitly run `aris dev skills ...`.

Developer Skills may fork selected User Skills when framework-maintenance usage needs to evolve independently from research-project usage. The initial fork set is `dev-caveman`, `dev-tdd`, `dev-diagnose`, `dev-review`, `dev-grill-docs`, `dev-handoff`, and `dev-zoom-out`.
