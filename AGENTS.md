# ARIS 开发 Agent 指南

本文件给 Codex、Claude 和框架开发者读取。开发者文档默认使用中文。

## 必读文档

- `CONTEXT.md`：框架版本、分支、release 术语。
- `docs/FRAMEWORK_STRUCTURE.md`：framework/project/dev 边界。
- `docs/PROMOTE_FLOW.md`：dev 到 stable 的 promote 规范。
- `docs/README.md`：文档索引。

## Stable 边界

- `main` 是 stable framework line。
- `dev` 是集成开发线。
- `to-developer/` 是 dev-only 材料，不能进入 stable `main`。
- stable 文档不能依赖 `to-developer/` 路径；需要给 Codex 或开发者读取的规范必须放在 `docs/`、`CONTEXT.md` 或本文件。

## Promote 规则

做 promote 或合入 stable 前：

1. 读取 `docs/PROMOTE_FLOW.md`。
2. 列出进入 stable 的文件范围。
3. 排除 `to-developer/`、私有配置、运行状态、缓存和本机日志。
4. 更新 `CHANGELOG.md`。
5. 运行相关测试。
6. 合入 `main` 后同步本机 stable checkout，并确认没有 `to-developer/`。

## 文档语言

- 开发者规范、流程、计划、ADR、promote/release 说明默认中文。
- 面向外部工具/API 的字段名、命令、错误信息保持原文。
- 现有英文文档无需无意义翻译；新增开发者文档优先中文。

