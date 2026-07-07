# Caller:any Skill Usability Audit

Scope: `/aris/aris-dev/skills/**/SKILL.md` with `caller: any`, plus shared refs. No network/API/cloud/SSH/GPU actions run.

## Top blockers

- Codex/Claude drift: `skills/` and `skills/skills-codex/` disagree on helper resolution, reviewer routing, assurance, output protocols, and some skill statuses.
- Issue backend absent: `to-prd`, `to-issues` require tracker + labels but define no local fallback beyond draft docs.
- External deps common: Gemini, Exa, DeepXiv, Feishu, qzcli, OpenAlex/S2/arXiv all need network/auth/CLI/API conditions.
- Some caller:any skills contain orchestration or costly actions: `idea-creator` can launch pilots; `qzcli` submits/stops GPU jobs.
- Naming mismatch: `comm-lit-review/SKILL.md` has `name: comm-lit-review-claude-single`, but docs/examples imply `/comm-lit-review`.
- Several docs still reference Claude paths/tools from Codex context (`~/.claude`, `mcp__codex__*`, `installed-skills.txt`).

## Per-skill ratings

| Skill | Rating | Practical blockers | Safe smoke test | External deps | Docs gaps |
|---|---|---|---|---|---|
| `alphaxiv` | usable-with-caution | Network tiers; wiki side effect path uses CC resolver | Parse arXiv ID from sample arg; do not fetch | AlphaXiv/arXiv web | Needs Codex resolver variant or explicit platform note |
| `arxiv` | usable-with-caution | Network API/download; fallback inline Python writes PDFs | `python3 tools/arxiv_fetch.py --help` | arXiv API | Uses `http://export.arxiv.org`; wiki resolver CC-only |
| `caveman` | usable | Persistence can surprise later turns | Load skill; verify terse response rule | None | Clear |
| `comm-lit-review` | usable-with-caution | Heavy web search; no deterministic helper | Run source-selection parse on `— sources: local` | Zotero/Obsidian/Web | Frontmatter name mismatch; shared comm refs live only under `skills-codex/comm-lit-review/references` |
| `deepxiv` | usable-with-caution | Optional CLI/token; network reads | `python3 tools/deepxiv_fetch.py --help` | `deepxiv` CLI / web | Resolver says project `tools/` only; no ARIS_REPO fallback |
| `exa-search` | usable-with-caution | Requires API key; content extraction paid/rate-limited | `python3 tools/exa_search.py --help` | `EXA_API_KEY`, `exa-py` | Should document no-op/clear error before search |
| `feishu-notify` | usable-with-caution | Sends external messages; interactive mode can wait | `test ! -f ~/.claude/feishu.json || jq . ~/.claude/feishu.json` | Feishu webhook/bridge | Config path Claude-specific; Codex path not discussed |
| `gemini-search` | usable-with-caution | `status: needs-adaptation`; needs MCP/CLI/auth; model aliases time-sensitive | `gemini --version` only | Gemini CLI/MCP/API key | Claude MCP setup in Codex skill; mirror only changes `platform` |
| `git-guardrails` | usable-with-caution | Codex hook format unspecified; writes hooks/settings | Execute bundled script with fake JSON input only | None | `status: needs-codex-adaptation`; needs exact Codex hook config |
| `grill-me` | usable | One-question loop may stall if user expected batch | Invoke with tiny plan; confirm one question emitted | None | Minimal but sufficient |
| `grill-with-docs` | usable-with-caution | Mutates `CONTEXT.md`/ADRs; session can sprawl | Read existing `CONTEXT.md`/ADR paths only | None | Relative refs exist; should say exact write paths in multi-context repos |
| `handoff` | usable | Writes outside workspace temp; no path convention | Dry-run outline only; no file write | None | OS temp path vague |
| `idea-creator` | usable-with-caution | Web + reviewer MCP + optional GPU pilots; can call run/monitor experiment | Run Phase 0 wiki resolver only, no web/reviewer | Web, Codex MCP, GPU optional | Uses missing invoked skills not in caller:any; CC resolver; output protocol links ok |
| `openalex` | usable-with-caution | Network/rate limits; `requests`; mirror status conflict | `python3 tools/openalex_fetch.py --help` | OpenAlex API, `requests` | Top says active/both; codex mirror says needs-adaptation and different resolver |
| `pixel-art` | usable-with-caution | `open` preview may fail headless; SVG quality manual | Generate tiny SVG to temp path only | None | "cute" trigger subjective; no accessibility checklist |
| `qzcli` | blocked | Cloud/GPU job create/stop/list can mutate external platform; needs creds | `qzcli --help` only | qzcli, Qizhi creds/API | Needs explicit read-only/safe mode and cost/destructive warnings |
| `research-lit` | usable-with-caution | Broad source matrix; many optional MCP/API paths; local PDF parsing undefined | `find tools -name '*fetch.py'` and local source parse | Web, Zotero, Obsidian, S2, Exa, Gemini, OpenAlex | Default `all` excludes named optional sources; easy user confusion |
| `research-wiki` | usable-with-caution | Mutates wiki; hard-fails if helper missing | `python3 tools/research_wiki.py --help` | arXiv for ingest by ID | Uses CC resolver; Codex mirror ref differs |
| `semantic-scholar` | usable-with-caution | S2 rate limits; network; fallback inline API unspecified | `python3 tools/semantic_scholar_fetch.py --help` | S2 API/key optional | Good, but no local no-network mode |
| `skill-dag-check` | usable | Depends generated DAG freshness | `python3 tools/generate_skill_dag.py --check-only` | None | Codex mirror uses ARIS_REPO resolver; top-level uses local path |
| `to-issues` | blocked | No issue backend/tool/label vocab provided | Draft markdown issue body from sample PRD only | Issue tracker unknown | `status: needs-issue-backend`; says run missing `/setup-matt-pocock-skills` |
| `to-prd` | blocked | Same missing issue backend; publishes externally by design | Draft PRD markdown only | Issue tracker unknown | `status: needs-issue-backend`; no fallback path contract |
| `write-a-skill` | usable-with-caution | Creates/modifies skills; DAG update can drift mirrors | Run DAG check only | None | Top/codex path differs; says SKILL under 100 lines but many repo skills exceed |
| `zoom-out` | usable | Needs repo exploration; no output template | Ask for module map on tiny fixture | None | Clear |

## Mirror/drift notes

- Identical mirrors: `caveman`, `git-guardrails`, `grill-me`, `grill-with-docs`, `handoff`, `to-issues`, `to-prd`, `zoom-out`.
- Non-identical mirrors: `gemini-search` platform only; `openalex` status/resolver; `skill-dag-check` resolver; `write-a-skill` resolver.
- Shared refs differ materially in Codex mirror: `assurance-contract`, `effort-contract`, `integration-contract`, `reviewer-independence`, `reviewer-routing`, `wiki-helper-resolution`, output protocols. This can make same skill behave differently depending which ref path loads.

## Recommended fixes

1. Add explicit `safe-smoke` section to every external skill: `--help`, parser-only, or dry-run command.
2. Standardize resolver snippets for Codex vs Claude; avoid mixed `installed-skills.txt` / `installed-skills-codex.txt`.
3. Mark `qzcli` as read-only by default; require explicit user approval for create/stop/batch.
4. Give `to-prd`/`to-issues` a local markdown fallback, or keep `blocked` until tracker tool exists.
5. Rename or alias `comm-lit-review-claude-single` so trigger, folder, and frontmatter agree.
