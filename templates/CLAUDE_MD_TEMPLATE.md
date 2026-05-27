# Project: {project-name}

## 默认模式

- caveman 模式默认开启（精简回复，保留技术准确度）
- 代码修改遵循 TDD（仅限 Python/实验代码，文档/配置不要求）
- 新设计/架构决策落地前必须 /grill-me 或 /grill-with-docs
- 新用户首次使用建议跑 /git-guardrails

## Pipeline Status

```yaml
stage: idle          # idle | idea-discovery | implementation | training | review | paper
idea: ""             # Current idea title (one line)
contract: ""         # Path to research_contract.md (e.g., idea-stage/docs/research_contract.md)
current_branch: ""   # Git branch for this idea
baseline: ""         # Baseline numbers for comparison
training_status: idle  # idle | running | complete | failed
language: en         # en | zh — controls skill output language (see shared-references/output-language.md)
active_tasks: []
next: ""             # Concrete next step
last_updated: ""     # YYYY-MM-DD HH:mm — auto-updated by skills on every output write
```

## Project Constraints

- {constraint 1}
- {constraint 2}

## Non-Goals

- {non-goal 1}

## Compute Budget

- {budget details, e.g., "8x A100 for 24h via vast.ai"}
