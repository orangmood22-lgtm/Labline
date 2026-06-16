# ARIS Codex CLI Migration

**Date**: 2026-06-05
**Status**: Phase 1-5 complete, dual-track period active

## Summary

ARIS project migrated from Claude Code to Codex CLI, following the guide at https://blakecrosley.com/zh-Hans/blog/claude-code-to-codex-migration.

## What Changed

### Phase 1: AGENTS.md (repo + global + template)

| File | Purpose |
|------|---------|
| `AGENTS.md` | Repo-level project instructions (Codex reads this) |
| `~/.codex/AGENTS.md` | Global conventions across all ARIS projects |
| `templates/AGENTS_MD_TEMPLATE.md` | Template for new ARIS projects |
| `CLAUDE.md` | Kept with redirect notice for dual-track period |

### Phase 2: Skills Migration

- `.agents/skills/` — symlinks pointing to `skills/` (Codex auto-discovers from here)
- `.claude/skills/` — symlinks for Claude Code, kept for dual-track
- Both point to the same canonical `skills/*/SKILL.md` files
- `install_aris.sh` now supports `--codex` flag

### Phase 4: Profiles

Three profiles in `~/.codex/config.toml`:

| Profile | Reasoning | Sandbox | Use |
|---------|-----------|---------|-----|
| `leader` | high | workspace-write | Research planning, gate decisions |
| `executor` | medium | workspace-write | Code, deploy, write |
| `reviewer` | xhigh | read-only | Independent audit, code review |

### Phase 5: Hooks

| Hook | File | Purpose |
|------|------|---------|
| SessionStart | `~/.codex/hooks/session_start.py` | Inject ARIS context + date |
| PreToolUse:Bash | `~/.codex/hooks/pre_tool_use_bash.py` | Block dangerous commands |
| Stop | `~/.codex/hooks/stop.py` | Citation integrity gate |

## What Did NOT Change

- **94 user-facing skills** — frontmatter is compatible, Codex ignores unknown fields
- **Skill content** — same canonical files, no rewrites needed
- **Shared references** — 24 files in `skills/shared-references/`, unchanged
- **Experiment chain contract** — same vocabulary, same protocols

## Key Differences: Claude Code vs Codex

| Feature | Claude Code | Codex CLI |
|---------|-------------|-----------|
| Project file | `CLAUDE.md` | `AGENTS.md` |
| Skill syntax | `/skill-name` | `$skill-name` |
| Skill path | `.claude/skills/` | `.agents/skills/` |
| Agent dispatch | `Agent(model, prompt)` | No equivalent |
| Profiles | N/A | `config.toml [profiles]` |
| Hooks | N/A | SessionStart/PreToolUse/Stop |
| Permissions | `settings.local.json` | sandbox + approval_policy |

## Three-Party Architecture Adaptation

The Agent tool (multi-model subagent dispatch) has no Codex equivalent. Current approach:

**Conservative: Multi-window + profiles**
- Leader: `codex exec -p leader`
- Executor: `codex exec -p executor`
- Reviewer: `codex exec -p reviewer`
- Skills communicate via files (unchanged)
- Human coordinates between windows

## Dual-Track Period

Both Claude Code and Codex CLI are functional during transition:

```bash
# Claude Code (existing)
cc                          # Interactive session

# Codex CLI (new)
codex exec -p leader "..."  # Leader session
codex exec -p executor "..." # Executor session
codex exec -p reviewer "..." # Reviewer session
```

**Duration**: 2 weeks, then evaluate stability.

## Verification Checklist

- [x] `AGENTS.md` exists and is readable
- [x] `~/.codex/AGENTS.md` exists with global conventions
- [x] `.agents/skills/` symlinks match `.claude/skills/`
- [x] `~/.codex/config.toml` has leader/executor/reviewer profiles
- [x] `~/.codex/hooks/` has 3 hook scripts (executable)
- [x] `install_aris.sh` supports `--codex` flag
- [x] `CLAUDE.md` has migration redirect notice
- [ ] `codex exec -p leader "Read AGENTS.md and list skills"` (manual test)
- [ ] Full experiment-plan → experiment-bridge flow with Codex (manual test)
