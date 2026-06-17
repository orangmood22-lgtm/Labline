---
name: dev-review
description: 框架开发侧的 diff review 工作流，用于检查标准符合性和 dev 规格符合性，但只输出草案结论
argument-hint: "要 review 的框架 diff、分支或提交范围"
caller: developer
platform: codex
status: dev-only
forked_from: review
forked_from_path: skills/review/SKILL.md
forked_at: 2026-06-17
---

# Dev Review

`dev-review` 用于审查框架仓库里的变更，重点看标准符合性和 dev 侧规格符合性。它只给开发侧评审结论，不进入用户项目，也不做最终 release / promote 决策。

## 适用

- 审查 dev-only 文档、脚本、工具和维护性改动
- 对照 `AGENTS.md`、`CONTEXT.md`、ADR 和计划文档找偏差
- 报告风险、遗漏和边界不清的地方

## 输出要求

- 先列问题，再给摘要
- 区分硬违规和判断题
- 明确哪些只是草案意见，需要 maintainer 定夺

## 边界

- 不替代代码作者自查
- 不把 review 结论包装成最终发布门禁
- 不向用户项目扩散审查范围
