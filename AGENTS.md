# ARIS Dev Agent 指南

本文件给 Codex、Claude 和框架开发者读取。开发者文档默认使用中文。

## 必读文档

- `CONTEXT.md`：框架版本、分支、release 术语。
- `to-developer/20260615-FRAMEWORK_MODULES.md`：开发者侧框架模块边界。
- `to-developer/DOC_DAG.yaml`：开发者文档依赖 DAG 源数据。
- `to-developer/DOC_DAG.mmd`：开发者文档依赖图。
- `to-developer/plans/20260613-PROMOTE_FLOW.md`：dev 侧 promote 流程草案。
- `to-developer/plans/20260613-VERSION_MANAGEMENT.md`：版本管理方案。
- `docs/FRAMEWORK_STRUCTURE.md`：framework/project/dev 边界。

## 开发者文档规则

- `to-developer/` 是 dev-only 材料，不能进入 stable `main`。
- 新增、删除、重命名 `to-developer/` 下的 `.md` 或 `.txt` 文档后，必须更新 `to-developer/DOC_DAG.yaml`。
- 更新 DAG 后运行：

```bash
python tools/update_developer_docs.py
python tools/update_developer_docs.py --check-only
```

- 开发者规范、流程、计划、ADR、promote/release 说明默认中文。
- 面向外部工具/API 的字段名、命令、错误信息保持原文。

## Promote 边界

- stable `main` 只保留用户可安装、可 pin、可发布的框架资产。
- dev 中成熟的规范才能 promote 到 stable `docs/`、`CONTEXT.md` 或 stable `AGENTS.md`。
- Promote 前必须排除 `to-developer/`、私有配置、运行状态、缓存和本机日志。
