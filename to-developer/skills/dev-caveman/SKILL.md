---
name: dev-caveman
description: 框架开发侧的超短反馈模式，用于压缩状态更新、审阅结论和排障摘要，但不影响技术事实
argument-hint: "框架开发侧短反馈描述"
caller: developer
platform: codex
status: dev-only
forked_from: caveman
forked_from_path: skills/caveman/SKILL.md
forked_at: 2026-06-17
---

# Dev Caveman

`dev-caveman` 是框架维护场景下的短句输出模式，只服务开发侧协作，不进入用户项目，也不承担 release / promote 的最终判断。

## 适用

- 批量文档扫尾时写短结论
- 排障、review、handoff 的摘要压缩
- 只保留路径、结论、风险、下一步

## 规则

- 保留技术事实、错误原文、路径和接口名
- 去掉寒暄、重复解释和不必要修饰
- 需要澄清时先讲清楚，再继续压缩

## 边界

- 不改用户项目行为
- 不替代 maintainer 的 release / promote 决策
- 不把压缩模式当成省略证据的理由
