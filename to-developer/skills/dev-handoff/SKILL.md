---
name: dev-handoff
description: 框架开发侧的交接整理工作流，用于把当前会话压缩成可继续接手的背景包
argument-hint: "要交接的框架工作、分支或问题"
caller: developer
platform: codex
status: dev-only
forked_from: handoff
forked_from_path: skills/handoff/SKILL.md
forked_at: 2026-06-17
---

# Dev Handoff

`dev-handoff` 把当前框架开发会话整理成后续可接手的背景材料。它只面向开发侧续作，不进入用户项目，也不负责 release / promote 的最终判断。

## 产出

- 现状摘要
- 已查阅的路径、计划和差异点
- 未决问题和明确阻塞
- 建议下一步使用的 dev skill

## 规则

- 复用已有 PRD、ADR、diff、日志，不重复抄写
- 涉及敏感信息时先脱敏
- 指向文件路径或已有材料，不凭空扩写结论

## 边界

- 不把交接文档写成最终决策
- 不把临时调查结果伪装成定案
- 不扩散到用户项目外的运行状态
