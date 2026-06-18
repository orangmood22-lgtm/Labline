# Templates

Labline workflow templates. Copy into a research project, fill in content, then run matching skill (`$skill-name` in Codex, `/skill-name` in Claude Code).

## Project Setup

| Template | Purpose |
|----------|---------|
| [AGENTS_MD_TEMPLATE.md](AGENTS_MD_TEMPLATE.md) | Codex project instructions |
| [CLAUDE_MD_TEMPLATE.md](CLAUDE_MD_TEMPLATE.md) | Claude Code project dashboard |
| [project.yaml.tmpl](project.yaml.tmpl) | Project metadata for sync/deploy/framework update |
| [api-config.yaml.tmpl](api-config.yaml.tmpl) | API provider/model config |
| [gitignore-trace.txt](gitignore-trace.txt) | Optional trace privacy ignore rules |
| [claude-hooks/meta_logging.json](claude-hooks/meta_logging.json) | Claude hook config for meta logging |

## Research / Idea Discovery

| Template | Purpose |
|----------|---------|
| [RESEARCH_BRIEF_TEMPLATE.md](RESEARCH_BRIEF_TEMPLATE.md) | Research direction brief |
| [RESEARCH_BRIEF_TEMPLATE_CN.md](RESEARCH_BRIEF_TEMPLATE_CN.md) | 中文研究简报 |
| [RESEARCH_CONTRACT_TEMPLATE.md](RESEARCH_CONTRACT_TEMPLATE.md) | Active idea contract / session recovery source |
| [IDEA_CANDIDATES_TEMPLATE.md](IDEA_CANDIDATES_TEMPLATE.md) | Surviving idea pool |
| [IDEA_CANDIDATES_TEMPLATE_CN.md](IDEA_CANDIDATES_TEMPLATE_CN.md) | 中文 idea 候选池 |
| [PSEUDOCODE_SPEC_TEMPLATE.md](PSEUDOCODE_SPEC_TEMPLATE.md) | Pseudocode spec for method review/implementation |

## Experiments

| Template | Purpose |
|----------|---------|
| [EXPERIMENT_PLAN_TEMPLATE.md](EXPERIMENT_PLAN_TEMPLATE.md) | Claim-driven experiment roadmap |
| [EXPERIMENT_PLAN_TEMPLATE_CN.md](EXPERIMENT_PLAN_TEMPLATE_CN.md) | 中文实验计划 |
| [EXPERIMENT_LOG_TEMPLATE.md](EXPERIMENT_LOG_TEMPLATE.md) | Structured experiment record |
| [EXPERIMENT_EXPECTATION_DECLARATION_TEMPLATE.md](EXPERIMENT_EXPECTATION_DECLARATION_TEMPLATE.md) | Pre-run expected-result declaration |
| [DATA_FLOW_SPEC_TEMPLATE.md](DATA_FLOW_SPEC_TEMPLATE.md) | Dataset/artifact flow contract |
| [FINDINGS_TEMPLATE.md](FINDINGS_TEMPLATE.md) | Finding log for auto-review loops |
| [MANIFEST_TEMPLATE.md](MANIFEST_TEMPLATE.md) | Output manifest tracking |

## Paper Writing

| Template | Purpose |
|----------|---------|
| [NARRATIVE_REPORT_TEMPLATE.md](NARRATIVE_REPORT_TEMPLATE.md) | Workflow 3 narrative input |
| [PAPER_PLAN_TEMPLATE.md](PAPER_PLAN_TEMPLATE.md) | Paper outline input |

## Patent

| Template | Purpose |
|----------|---------|
| [INVENTION_BRIEF_TEMPLATE.md](INVENTION_BRIEF_TEMPLATE.md) | Invention disclosure |
| [PATENT_CLAIMS_TEMPLATE.md](PATENT_CLAIMS_TEMPLATE.md) | Claims drafting worksheet |
| [PATENT_SPECIFICATION_TEMPLATE.md](PATENT_SPECIFICATION_TEMPLATE.md) | Specification skeleton |

## Usage

```bash
cp templates/EXPERIMENT_PLAN_TEMPLATE.md refine-logs/EXPERIMENT_PLAN.md
# edit, then in Codex:
$experiment-bridge
```

```bash
cp templates/INVENTION_BRIEF_TEMPLATE.md patent/INVENTION_BRIEF.md
# edit, then:
$patent-pipeline "patent/INVENTION_BRIEF.md -- CN"
```
