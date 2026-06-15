# ARIS Promote 规范

本规范给 Codex、Claude、框架维护者和开发者读取。它定义如何把 `dev` 中成熟的框架改动提升到 stable `main`。

## 核心原则

- `main` 是 stable framework line，只放用户可安装、可 pin、可发布的框架资产。
- `dev` 是集成开发线，可以保留开发记录、计划、审计材料和未发布实验。
- `to-developer/` 是 dev-only 材料，不能出现在 stable `main`、本机 stable checkout 或发布包中。
- Promote 的目标不是“复制所有改动”，而是把通用、验证过、文档完整的框架能力提升到 stable。

## Stable 允许内容

stable 可以包含：

- `skills/`
- `tools/`
- `templates/`
- `deploy/`
- `docs/`
- `tests/`
- `examples/`
- `compat/`
- `incubating/`
- `legacy/`
- `mcp-servers/`
- `assets/`
- 顶层用户文档和配置样例，如 `README.md`、`CHANGELOG.md`、`CONTEXT.md`、`.env.example`

stable 不应包含：

- `to-developer/`
- 私有配置、密钥、token、SSH 信息
- 项目级实验代码、数据、论文、运行日志
- 只对某个本地机器有效的路径或代理配置
- 未登记、未解释生命周期的临时 hack

## Promote 准入条件

Promote 前必须满足：

1. **验证通过**：相关测试通过，或至少一个真实项目/本地流程跑通。
2. **通用性明确**：不是单一项目专用 hack。
3. **兼容性明确**：不破坏 stable 现有用法；破坏性变更必须有兼容层或明确迁移说明。
4. **文档完整**：用户能从 stable 文档中理解安装、配置、启动、限制和风险。
5. **测试覆盖**：有合理回归测试；无法自动测试时写明人工验证方式。
6. **Changelog 更新**：用户可见变化写入 `CHANGELOG.md`。
7. **边界干净**：不把 `to-developer/` 或私有运行状态带入 stable。

## 标准流程

1. 在 `dev` 完成功能和测试。
2. 明确 promote 范围，只选择 stable 允许内容。
3. 更新 stable 可读文档，例如 `docs/*.md`、`README.md`、`mcp-servers/README.md`。
4. 更新 `CHANGELOG.md` 的 `[Unreleased]`。
5. 运行相关测试。涉及 skill/catalog/DAG 时，重新生成对应产物。
6. 合入 `main`，优先 fast-forward；不能 fast-forward 时先解释原因。
7. 在 `main` 上再次运行关键测试。
8. push `main`。
9. 同步本机 stable checkout，例如 `/aris/framework`、`/aris/projects/aris-framework`。
10. 确认 stable checkout 中不存在 `to-developer/`。

## Codex 执行规则

Codex 在执行 promote 或 stable 合入时必须：

- 先读本文件和 `docs/FRAMEWORK_STRUCTURE.md`。
- 先展示将进入 stable 的文件范围。
- 默认排除 `to-developer/`、`.aris/`、`.venv-*`、`.env`、缓存和运行日志。
- 不使用 `git reset --hard` 或会丢弃用户改动的命令，除非用户明确要求。
- 如果发现 stable 文档引用 dev-only 路径，必须改成 stable 可读路径。
- 如果 release 工具要求 dev-only 文件，必须调整 release 工具，而不是把 dev-only 文件塞回 stable。

## 本机 Stable 同步检查

同步 stable 后至少检查：

```bash
git -C /aris/framework status --short --branch
test ! -e /aris/framework/to-developer

git -C /aris/projects/aris-framework status --short --branch
test ! -e /aris/projects/aris-framework/to-developer
```

如果路径不存在，按实际本机 stable checkout 路径替换。

## 常见错误

- 把 `to-developer/plans/*.md` 当作 stable 规范引用。
- 只在 dev 文档写接入说明，stable 用户读不到。
- 把本地 `.env`、`.aris/feishu-control/`、`.venv-feishu/` 提交。
- 合入 stable 后没有重新跑测试。
- 推送 `main` 后没有同步本机 stable checkout。

