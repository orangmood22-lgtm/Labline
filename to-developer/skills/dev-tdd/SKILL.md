---
name: dev-tdd
description: 框架开发侧的测试先行工作流，用于把文档、工具和低风险改动绑定到可验证行为上
argument-hint: "要实现或修复的框架行为"
caller: developer
platform: codex
status: dev-only
forked_from: tdd
forked_from_path: skills/tdd/SKILL.md
forked_at: 2026-06-17
---

# Dev TDD

`dev-tdd` 用于框架模块和开发工具链的测试先行实现。它只管开发侧行为验证，不进入用户项目，也不替代最终 release / promote 判断。

## 适用

- 框架脚本、校验器、文档生成器、辅助工具的行为补丁
- 低风险重构前后的回归保护
- 需要明确公共接口或输出契约的改动

## 工作方式

- 先确定可观察行为，再写一个最小测试
- 一次只验证一个行为
- 优先用公共接口、CLI、脚本输出或真实文件结果
- GREEN 后再做必要重构

## 边界

- 不在用户项目里铺开横切测试
- 不为未确认的未来行为提前造测试
- 不把测试草案当作 release / promote 决策
