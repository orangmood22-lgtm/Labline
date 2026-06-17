---
name: dev-diagnose
description: 框架开发侧的故障诊断工作流，用于复现、缩小、假设、加探针并补回归
argument-hint: "要排查的框架 bug、失败或性能回退"
caller: developer
platform: codex
status: dev-only
forked_from: diagnose
forked_from_path: skills/diagnose/SKILL.md
forked_at: 2026-06-17
---

# Dev Diagnose

`dev-diagnose` 面向框架维护中的 bug、失败和性能回退。它只处理开发侧可复现问题，不进入用户项目，也不做 release / promote 最终裁决。

## 目标

- 建立稳定、可重复的反馈回路
- 把问题缩小到最小可观察范围
- 用可证伪假设驱动排查
- 在修复后补上回归保护

## 常用信号

- 本地测试失败
- CLI 输出偏差
- 运行时日志、追踪或基准回退
- 可重放的请求、输入或 trace

## 边界

- 先复现，再推理
- 一次只改一个变量
- 不靠猜测代替证据
- 不把临时排障结论当作 release / promote 决策
