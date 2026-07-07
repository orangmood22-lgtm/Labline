# 仓库架构演进计划

> 创建日期: 2026-06-11
> 状态: 已确认，待触发执行

## 背景

当前 ARIS 采用**同仓双目录**结构：

```
Auto-research-in-sleep/
├── aris-orangmood-edition/   ← stable framework
├── aris-dev/                  ← dev framework + 开发文档
└── aris-framework/            ← 空，预留
```

dev 目录已建立骨架（skills/ tools/ templates/ 等），但**尚无实际实验内容**。

---

## 决策一：dev / stable 是否分仓？

### 当前策略：保持同仓

**理由：**
1. dev 还是空的，没有内容需要物理隔离
2. 同仓下 promote 是简单的 `cp -r`，开发效率最高
3. 安装器 `--dev` 标志已支持自动检测同级 `aris-dev/`
4. 拆仓有成本（双 repo 管理、CI 配置、安装器路径更新）

### 未来分仓触发条件

满足以下任一条件时，启动分仓：

| # | 触发条件 | 当前状态 |
|---|---------|---------|
| 1 | `aris-dev/skills/` 下有 3+ 个在验证的候选 skill | ❌ 0 个 |
| 2 | stable 准备对外发布/开源 | ❌ 未计划 |
| 3 | dev 的实验 commit 频繁污染 stable git history | ❌ 无 |
| 4 | 框架使用者抱怨 clone 了过多 dev 内容 | ❌ 无使用者反馈 |

### 分仓目标结构（未来执行）

```
github.com/orangmood22-lgtm/aris-framework.git
├── skills/
├── tools/
├── templates/
├── deploy/
├── docs/
├── tests/
├── examples/
├── compat/
├── incubating/
├── legacy/
├── mcp-servers/
├── assets/
├── CHANGELOG.md
└── README.md

github.com/orangmood22-lgtm/aris-dev.git
├── skills/          ← 候选 skill
├── tools/           ← 实验性工具
├── templates/       ← 新版模板草稿
├── deploy/
├── docs/
├── tests/
├── examples/
├── compat/
├── incubating/
├── legacy/
├── mcp-servers/
├── assets/
├── to-developer/    ← 开发文档（plans/ logs/）
└── README.md
```

---

## 决策二：Promote 策略开发

### 当前状态

- ✅ 有准入检查清单（`20260613-PROMOTE_FLOW.md`）
- ✅ 有开发者文档 DAG 自动更新脚本（`tools/update_developer_docs.py`）
- ❌ 无跨仓库/跨目录的 promote 工具

### 策略：延后到第一次真正 promote 时

**理由：**
1. dev 还是空的，没有东西需要 promote
2. 第一次 promote 时才知道真正的痛点是什么（路径？测试？文档？）
3. 过早写工具可能解决错误的问题

### 预期工具（第一次 promote 时开发）

```bash
# 在 dev repo 根目录运行
bash tools/check_promote_ready.sh skills/<new-skill>

# 输出示例：
#   [PASS] SKILL.md exists
#   [PASS] tests/ pass (3/3)
#   [WARN] no project has validated this skill yet
#   [FAIL] CHANGELOG.md entry missing
#
#   Result: 2 PASS, 1 WARN, 1 FAIL → not ready for promote
```

---

## 行动清单

| 优先级 | 任务 | 触发条件 | 状态 |
|--------|------|---------|------|
| P1 | 保持同仓，继续开发 | 当前 | ✅ 执行中 |
| P2 | 维护 `to-developer/DOC_DAG.yaml` 并运行 `tools/update_developer_docs.py` | 新增/删除/重命名开发者文档 | ✅ 执行中 |
| P3 | dev 中产生第一个候选 skill | dev/skills/ 非空 | ⏳ 等待 |
| P4 | 编写 `check_promote_ready.sh` | 第一次 promote 前 | ⏳ 等待 |
| P5 | 评估分仓必要性 | 触发条件满足 | ⏳ 等待 |
| P6 | 执行分仓（如需） | P5 评估通过 | ⏳ 等待 |

---

## 相关文件

- `aris-dev/to-developer/plans/20260613-PROMOTE_FLOW.md` — Promote 手动流程
- `aris-dev/to-developer/DOC_DAG.yaml` — 开发者文档依赖源数据
- `aris-dev/tools/update_developer_docs.py` — 生成/校验开发者文档 DAG
- `aris-orangmood-edition/CHANGELOG.md` — 版本变更记录
- `aris-orangmood-edition/docs/FRAMEWORK_STRUCTURE.md` — 三层架构说明
- `aris-orangmood-edition/tools/install_aris.sh` — 安装器（已支持 `--dev`）
