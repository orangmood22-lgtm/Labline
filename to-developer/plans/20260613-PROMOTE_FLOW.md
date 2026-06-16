# Promote 流程（Dev → Stable）

## 什么时候 Promote

Dev 中的能力成熟后，通过本流程升入 Stable framework。

## 准入检查清单

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | **验证通过** | 至少一个真实项目运行无错，或 `dev/tests/` 通过 |
| 2 | **通用性** | 不是特定项目的 hack，可被多个项目复用 |
| 3 | **兼容性** | 不破坏 stable 现有功能；破坏性改动需 backward compat shim |
| 4 | **文档完整** | SKILL.md / README / 用法说明已写 |
| 5 | **测试覆盖** | 有对应回归测试（如适用） |
| 6 | **Changelog** | 已在 `CHANGELOG.md` 或对应文件记录变更 |

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
