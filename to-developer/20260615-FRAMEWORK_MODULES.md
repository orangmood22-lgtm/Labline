# ARIS 框架模块说明

本文档定义开发者侧的框架模块边界。`to-developer/20260613-DEVELOPMENT_LOG.md` 按这里的模块名记录开发变更；发布前再把用户可见部分蒸馏到 `CHANGELOG.md`。

## 模块索引

| 模块 | 主要路径 | 职责 | 更新时同步检查 |
|---|---|---|---|
| `skills` | `skills/`, `.agents/skills/` | 用户侧 Agent 可调用能力、workflow、role skill、shared references、Codex/Claude 兼容镜像。 | `docs/SKILL_DAG.yaml`, `docs/SKILL_CATALOG*.md`, mirror 测试、相关 skill 文档。 |
| `dev-skills` | `to-developer/skills/`, dev checkout `.agents/skills/dev-*` | 开发侧 maintainer-only skills，用于框架维护、review、生成、promote、测试、批量清扫等；必须使用 `dev-` 前缀，不安装到用户项目。 | dev skills installer、`to-developer/` 文档、开发日志、dev-only 测试。 |
| `dev-user-surface` | `skills/skills-codex/`, `docs/SKILL_*`, 用户模板与用户文档生成物 | 开发 checkout 中准备给用户/stable 的表面，包括 User Skill mirror、catalog、DAG、模板和用户文档一致性。 | `aris dev user-surface ...`、生成器、mirror 测试、promote gate。 |
| `tools` | `tools/` | 本地 CLI/脚本工具，包括文档 DAG、release、状态流、飞书 session runner、安装/同步辅助。 | 对应测试、README/工具索引、开发日志。 |
| `templates` | `templates/` | 新项目初始化模板、项目内 agent 配置模板、`project.yaml` 模板。 | 安装器测试、项目文件指南、模板 README。 |
| `docs` | `docs/`, `README.md`, `CONTEXT.md`, `AGENTS.md` | stable 面向用户和 agent 的正式说明、治理术语、入口索引。 | `docs/README.md`, 用户入口链接、相关 generated docs。 |
| `to-developer` | `to-developer/` | dev-only 计划、讨论、handoff、验证日志、开发者文档 DAG。 | `to-developer/DOC_DAG.yaml`, `to-developer/DOC_DAG.mmd`, `tools/update_developer_docs.py --check-only`。 |
| `mcp-servers` | `mcp-servers/` | 本地/远程 MCP bridge，包括 review、LLM chat、Feishu bridge、image bridge。 | `mcp-servers/README.md`, 集成文档、桥接测试。 |
| `deploy` | `deploy/`, `Dockerfile*`, `docker-compose*.yml` | 部署、容器、服务器运行说明。 | `deploy/DEPLOY_GUIDE.md`, `docs/OPERATIONS_GUIDE.md`, 部署 QA。 |
| `compat` | `compat/` | 兼容层、迁移辅助、历史 runtime 适配。 | `compat/README.md`, 迁移文档、相关测试。 |
| `examples` | `examples/` | 示例项目、示例输入、演示材料。 | `examples/README.md`, 相关 docs 中的示例路径。 |
| `incubating` | `incubating/` | 未稳定的新能力试验区。 | Promote 计划、成熟后迁移目标、开发日志。 |
| `legacy` | `legacy/` | 历史实现和保留材料。 | `legacy/README.md`, 迁移/废弃说明。 |
| `tests` | `tests/` | 回归测试、契约测试、脚本测试。 | 被测模块文档、CI/本地验证说明。 |
| `assets` | `assets/` | 文档和演示用静态资源。 | 引用它的 README/docs。 |

## 记录规则

- 改动发生在哪个模块，就在 `to-developer/20260613-DEVELOPMENT_LOG.md` 的同名小节记录。
- 一个改动跨多个模块时，分别记录影响，不要只写在实现所在目录。
- 用户可见能力、安装方式、命令行为、配置方式变化，需要再同步到 stable 文档或 `CHANGELOG.md` 候选项。
- 仅开发者内部计划、讨论、审计、handoff 进入 `to-developer/`，不进入 stable `main`。

## 常见判断

| 改动 | 归入模块 |
|---|---|
| 新增/修改 `SKILL.md` | `skills` |
| 新增/修改 `to-developer/skills/dev-*/SKILL.md` | `dev-skills` |
| 修改 skill DAG/catalog 生成器 | `tools`，同时影响 `skills` 文档派生产物 |
| 修改用户 skill mirror/catalog/DAG 同步逻辑 | `dev-user-surface`，实现脚本归入 `tools` |
| 修改 Feishu bridge HTTP/WS 服务 | `mcp-servers` |
| 修改 Feishu session runner 或控制状态脚本 | `tools` |
| 修改安装器、同步、release 脚本 | `tools` |
| 修改项目模板或 agent 模板 | `templates` |
| 新增用户指南、stable 索引 | `docs` |
| 新增 ADR、迁移记录、技术评估、文档依赖维护规则 | `to-developer` |
| 新增开发计划、审计日志、讨论归档 | `to-developer` |
| 修改 Docker/compose/服务器说明 | `deploy` |
| 新增兼容 shim 或迁移辅助 | `compat` |

## 发布关系

开发侧记录顺序：

```text
具体代码/文档改动
  -> to-developer/20260613-DEVELOPMENT_LOG.md 按模块记录
  -> 用户可见部分进入 CHANGELOG.md
  -> stable 文档 DAG / promote gate 校验
```

`to-developer/20260615-FRAMEWORK_MODULES.md` 只定义开发者侧模块边界。对用户暴露的框架/项目/dev 三层结构仍以 `docs/FRAMEWORK_STRUCTURE.md` 为准。

`dev-skills` 只进入开发侧记录和 dev-only 验证，不进入用户 `CHANGELOG.md`，也不进入 stable `skills/`、用户 skill catalog 或用户 skill DAG。
