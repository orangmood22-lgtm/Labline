---
name: dev-zoom-out
description: 框架开发侧的上下文扩展工作流，用于把局部代码放回模块、调用方和文档全局里理解
argument-hint: "要放大上下文的代码区域、模块或问题"
caller: developer
platform: codex
status: dev-only
forked_from: zoom-out
forked_from_path: skills/zoom-out/SKILL.md
forked_at: 2026-06-17
---

# Dev Zoom Out

`dev-zoom-out` 用于框架维护中的上下文扩展。它帮助开发者看清模块边界、调用链和文档语境，不进入用户项目，也不做 release / promote 最终决策。

## 关注点

- 相关模块、上游调用方、下游依赖
- 现有 glossary、`CONTEXT.md`、ADR 和计划文档
- 局部改动对整体框架边界的影响

## 输出

- 先给地图，再给局部解释
- 用项目自己的术语命名模块和关系
- 标出不确定点和需要继续下钻的地方

## 边界

- 不用放大上下文替代实际排障
- 不把宏观图景误写成发布决定
- 不把用户项目里的实现细节带进 dev 语境
