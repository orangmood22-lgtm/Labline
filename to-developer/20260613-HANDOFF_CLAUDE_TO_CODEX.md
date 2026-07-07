# Handoff: Claude Code → Codex

> 交接时间: 2026-06-11
> 来源: Claude Code session（coding CLI）
> 目标: Codex session

## 背景

本项目是 Claude Code（coding CLI，Opus 4.6）session 中完成的框架架构重组工作，现交给 Codex session 继续推进。所有变更已 commit 到 `orangmood-tripartite-night-20260512` 分支。

---

## 当前进度

### 已完成

| 工作项 | 说明 | 关键文件 |
|--------|------|---------|
| **三层分离架构** | Framework / Project / Dev 三层边界已定义 | `docs/FRAMEWORK_STRUCTURE.md` |
| **dev framework 骨架** | `aris-dev/` 下 12 个核心目录 + README | `aris-dev/README.md` |
| **开发文档区** | 过程记录、计划、日志集中到 `to-developer/` | `aris-dev/to-developer/` |
| **安装器增强** | `--dev` flag（自动选 dev repo）、version record | `tools/install_aris.sh` |
| **回归测试** | 28 个 installer 相关测试全部通过 | `tests/test_install_aris_*.py`（6 个文件） |
| **治理文档** | CHANGELOG、Promote 流程、仓库演进计划 | 见下方文档索引 |
| **项目资产迁出** | `discussions/` `figures/` 等从 framework 根目录移除 | 已确认根目录干净 |

### 测试总览

```
28 tests pass (installer 相关):
  test_install_aris_version_record.py       4 tests
  test_install_aris_tools_symlink.py        7 tests
  test_install_aris_codex_flag.py           5 tests
  test_install_aris_manifest_safety.py        5 tests
  test_install_aris_dev_flag.py               3 tests
  test_install_aris_reconcile.py              4 tests
```

**注意：** 已有测试 `test_watchdog.py` 等 64 个 pre-existing errors（与本次改动无关，是历史遗留的 Python 2/3 兼容性问题）。

---

## 重要文档位置

| 文档 | 路径 | 用途 |
|------|------|------|
| 三层架构契约 | `aris-orangmood-edition/docs/FRAMEWORK_STRUCTURE.md` | Framework/Project/Dev 边界定义，含 override 策略和版本记录说明 |
| 变更日志 | `aris-orangmood-edition/CHANGELOG.md` | 高亮变更记录（完整历史用 `git log`） |
| Promote 流程 | `aris-dev/to-developer/plans/20260613-PROMOTE_FLOW.md` | Dev → Stable 的准入检查和手动步骤 |
| 仓库演进计划 | `aris-dev/to-developer/plans/20260613-REPO_EVOLUTION_PLAN.md` | Dev/Stable 分仓决策和触发条件 |
| Dev 框架说明 | `aris-dev/README.md` | Dev framework 目录结构和 promote 指引 |
| 安装器脚本 | `aris-orangmood-edition/tools/install_aris.sh` | 核心契约，已加 `--dev` 和 version record |
| 项目模板 | `aris-orangmood-edition/templates/project.yaml.tmpl` | 含 `framework.version` 和 `overrides` 注册表 |

---

## 待办事项（优先级排序）

| 优先级 | 任务 | 说明 | 预估工作量 |
|--------|------|------|---------|
| P1 | **修复已有测试错误** | `test_watchdog.py` 等 64 个 pre-existing failures，Python 2/3 `bytes` vs `str` 问题 | 中等 |
| P2 | **开发第一个 dev skill** | 在 `aris-dev/skills/` 下创建实验性 skill，验证 dev → stable promote 流程 | 大 |
| P3 | **写 promote 检查脚本** | `dev/tools/check_promote_ready.sh`，在第一次真正 promote 前完成 | 小 |
| P4 | **评估分仓** | 见 `20260613-REPO_EVOLUTION_PLAN.md` 触发条件，目前不满足 | 触发后评估 |
| P5 | **--reconcile 增强** | 当前 reconcile 支持 add/remove，可加强为检测 upstream skill 内容变更 | 中等 |

---

## 架构上下文

### 三层分离

```
aris-orangmood-edition/   ← Stable framework（长期资产）
├── skills/ tools/ templates/ deploy/ docs/ tests/
├── examples/ compat/ incubating/ legacy/
└── CHANGELOG.md

aris-dev/                  ← Dev framework（实验线）
├── skills/ tools/ templates/ ...
└── to-developer/          ← 开发文档（plans/ logs/）
   └── plans/
       ├── 20260613-PROMOTE_FLOW.md
       └── 20260613-REPO_EVOLUTION_PLAN.md

各科研项目/                  ← Project（独立仓库，轻量安装层接入 framework）
├── code/ data/ paper/ refine-logs/
├── project.yaml           ← 含 framework version pin + overrides 注册表
└── .claude/skills/ → symlink to framework skills
```

### 安装层契约

- 项目通过 symlink 接入 framework，不复制源码
- `install_aris.sh` 管理 `.claude/skills/` 和 `.aris/`（manifest + version file）
- `--dev` 自动检测同级/父级 `aris-dev/`
- `--Codex` 切换到 `.agents/skills/`

---

## 建议的 skills

继续推进时，根据方向选择：

- **`/tdd`** — 继续为 installer 写回归测试（如 `--reconcile` 内容变更检测、manifest crash 恢复）
- **`/diagnose`** — 修复 `test_watchdog.py` 等已有测试错误
- **`/experiment-plan`** — 如果下一个方向是 ARIS 框架的科研实验功能
- **`/grill-with-docs`** — 如果需要重新审视架构决策或术语定义
- **`/handoff`** — 如果再次需要 session 交接

---

## 注意事项

1. **权限**：当前环境是 root 用户，coding CLI auto mode 对 `rm`/`mkdir`/`git commit`/测试运行 有 classifier block，敏感操作可能需要用户手动执行或在 settings.json 加权限规则。
2. **分支**：当前在 `orangmood-tripartite-night-20260512`，所有变更已 commit。
3. **dev 为空**：`aris-dev/skills/` 等目录只有 README placeholder，尚无实际实验内容。
4. **Codex 差异**：本 session 是 coding CLI（Opus），Codex session 是 GPT-4.5，注意工具能力和 context 差异。
