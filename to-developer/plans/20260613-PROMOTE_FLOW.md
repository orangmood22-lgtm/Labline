# Promote 流程（Dev → Stable）

## 什么时候 Promote

Dev 中的能力成熟后，通过本流程升入 Stable framework。

Promote 只适用于用户可安装、可 pin、可发布的资产。Developer Skill、Developer Material、dev runtime state 和私有配置不进入 stable。

## Promote Candidate Type

Promote 前必须先给候选变更定性：

| 类型 | 是否可 promote | 说明 |
|---|---:|---|
| `user-skill` | 是 | 面向科研项目用户的 `skills/<name>/`，可安装到项目。 |
| `user-tool` | 是 | 用户或管理员会直接使用的 `tools/` 能力。 |
| `user-template` | 是 | 项目初始化或用户配置模板。 |
| `user-doc` | 是 | stable 用户/管理员文档。 |
| `deploy-asset` | 是 | Docker、compose、部署脚本、管理员部署资产。 |
| `compat-asset` | 是 | 迁移、兼容 shim。 |
| `mcp-server` | 是 | 用户可用或集成必需的 MCP/bridge。 |
| `test` | 是 | 支撑 stable 行为的测试。 |
| `example` | 是 | 用户可运行示例。 |
| `static-asset` | 是 | 文档或演示引用的静态资产。 |
| `developer-skill` | 否 | `to-developer/skills/dev-*`，只服务框架开发，不安装到用户项目。 |
| `developer-material` | 否 | 计划、讨论、handoff、ADR、开发日志。 |
| `dev-runtime-state` | 否 | 本机运行状态、日志、缓存、临时测试状态。 |
| `private-config` | 否 | API key、SSH、私有 host、个人配置。 |

Developer Skill 成熟后不能原样 promote。只能把其中用户可见、可安装的部分重新提炼成 `user-skill`、`user-tool`、`user-doc` 等候选类型，再走本流程。

## 准入检查清单

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | **验证通过** | 至少一个真实项目运行无错，或 `dev/tests/` 通过 |
| 2 | **候选类型** | 属于允许 promote 的 Promote Candidate Type |
| 3 | **通用性** | 不是特定项目的 hack，可被多个项目复用 |
| 4 | **兼容性** | 不破坏 stable 现有功能；破坏性改动需 backward compat shim |
| 5 | **文档完整** | SKILL.md / README / 用法说明已写 |
| 6 | **测试覆盖** | 有对应回归测试（如适用） |
| 7 | **Changelog** | 用户可见变化已进入 `CHANGELOG.md`；dev-only 变化只进开发日志 |

## Promote 步骤

```bash
# 1. 确认要 promote 的内容完整
cd /root/Projects/aris/Auto-research-in-sleep/aris-dev
ls skills/<new-skill>/

# 2. 先 dry-run 查看计划
tools/promote_to_stable.sh \
  --component skills/<new-skill> \
  --stable /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition \
  --dry-run

# 3. Promote 到 stable
tools/promote_to_stable.sh \
  --component skills/<new-skill> \
  --stable /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition

# 4. 在 stable 补充文档和链接
cd /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
# - 更新 skills/README.md（如有目录索引）
# - 更新 CHANGELOG.md

# 5. 运行 stable 回归测试
python -m unittest discover tests/

# 6. 从 dev 清理（删除或移入 dev/legacy/）
rm -rf /root/Projects/aris/Auto-research-in-sleep/aris-dev/skills/<new-skill>
```

`tools/promote_to_stable.sh` 默认拒绝覆盖 stable 已有内容，并只允许 promote framework 边界内的目录：

- `skills/`
- `tools/`
- `templates/`
- `deploy/`
- `docs/`
- `tests/`
- `examples/`
- `compat/`
- `mcp-servers/`
- `assets/`

开发记录、私有配置和过程材料（例如 `to-developer/`）不应 promote 到 stable。

## 边界情况

| 场景 | 处理 |
|------|------|
| 新增 skill | 直接复制到 `stable/skills/`，最简单 |
| 修改现有 skill | 检查是否破坏已有项目；破坏性改动走 `stable/compat/` 或版本号 |
| 修改 install_aris.sh | 核心工具，谨慎修改，必须经过完整测试 |
| 修改 template | 影响新项目初始化，不影响已安装项目，相对安全 |
| 不通用 / 太项目-specific | 留在 dev，或降级为项目 `overrides/` |

## 历史版本追溯

`CHANGELOG.md` 只记录人为整理的高亮变更。

完整历史可自动从 commit 历史读取：

```bash
# 查看所有 commit
git -C /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition log --oneline

# 查看某文件历史
git -C /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition log --oneline -- tools/install_aris.sh

# 生成 changelog 草稿（按 tag 分组）
git -C /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition log --pretty=format:"%s" $(git describe --tags --abbrev=0)..HEAD
```

## TODO

- [ ] 写自动化检查脚本 `dev/tools/check_promote_ready.sh`（更完整地检查测试、文档、CHANGELOG）
