---
name: dev-grill-docs
description: 框架开发侧的文档与术语追问工作流，用于逼清定义、核对上下文并同步更新 dev 文档
argument-hint: "要追问或校准的框架术语、方案或文档段落"
caller: developer
platform: codex
status: dev-only
forked_from: grill-with-docs
forked_from_path: skills/grill-with-docs/SKILL.md
forked_at: 2026-06-17
---

# Dev Grill Docs

`dev-grill-docs` 用于框架开发侧的术语澄清、方案追问和文档校准。它只服务 dev 文档和框架上下文，不进入用户项目，也不做 release / promote 最终决策。

## 做什么

- 一次只追问一个关键分歧
- 用代码库、`CONTEXT.md`、ADR 和现有文档验证说法
- 发现术语冲突时立刻指出并收敛定义
- 需要时同步更新 dev 文档里的 glossary 或 ADR 草案

## 边界

- `CONTEXT.md` 只记术语和约定，不记实现细节
- 不把追问变成无止境讨论
- 不把 dev 文档当成发布审批记录
