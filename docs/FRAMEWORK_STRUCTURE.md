# ARIS 框架目录结构契约

> 版本: 2026-06-10
> 适用对象: framework repo 维护者、项目开发者、部署管理员

## 三层分离原则

ARIS 采用 **framework / project / dev** 三层分离模型，防止不同生命周期和所有权的东西混在一起。

| 层级 | 所有权 | 生命周期 | 存放位置 | 稳定性 |
|------|--------|---------|----------|--------|
| **Framework (stable)** | 框架维护者 | 长期演进、版本发布 | `aris-orangmood-edition/` | 生产级 |
| **Framework (dev)** | 框架开发者 | 实验验证、待 promote | `aris-dev/` | 不稳定 |
| **Project** | 科研人员 | 随研究结束归档 | 各科研项目的独立仓库/目录 | — |
| **Dev-only docs** | 框架开发者 | 过程记录、计划、日志 | `aris-dev/to-developer/` | — |

## Dev Framework 说明

`aris-dev/` 是 framework 的**测试/开发版本线**，结构与 stable 完全一致：

- `skills/` — 候选 skill，验证通过后 promote 到 stable
- `tools/` — 实验性工具（安装器契约 `install_aris.sh` 不可在 dev 改动）
- `templates/` — 新版模板草稿
- `deploy/` — 实验性部署配置
- `docs/` `tests/` `examples/` `compat/` `incubating/` `legacy/` `mcp-servers/` `assets/`

### Promote 流程

1. 在 dev 验证通过（至少一个真实项目或测试通过）
2. 检查通用性、兼容性、文档完整性
3. 复制到 stable 对应目录
4. 更新 `CHANGELOG.md`
5. 运行 stable 回归测试
6. 从 dev 清理（删除或移入 `dev/legacy/`）

Stable promote 规范见 `docs/PROMOTE_FLOW.md`；更细的开发过程记录只保留在 dev checkout。

## Framework Repo 允许内容

framework repo 是**长期资产**，只放以下类别：

- `skills/` — 正式 skill 定义（SKILL.md）
- `tools/` — 框架工具（install_aris.sh、同步脚本、队列管理）
- `templates/` — 项目模板（project.yaml、CLAUDE.md/AGENTS.md 模板）
- `deploy/` — Docker 部署配置
- `docs/` — 面向用户和部署者的文档
- `tests/` — 回归测试
- `examples/` — 框架使用示例（见下方 bucket 说明）
- `compat/` — 兼容性层（旧版支持、迁移脚本）
- `incubating/` — 孵化中资产（未正式发布到 framework）
- `legacy/` — 历史残留文档（清理后不再新增）

**Framework repo 不应长期存放**：
- 具体科研项目的实验代码、数据、论文
- 项目级日志、refine-logs、idea-stage 产出
- 个人或项目专用的私有配置

## Project Repo 内容

每个科研项目是**独立目录/仓库**，通过轻量安装层接入 framework：

```
my-research/
├── project.yaml          # 项目元数据 + framework version pin + overrides 注册表
├── AGENTS.md / CLAUDE.md # Codex 上下文 / Claude Code 兼容上下文
├── code/                 # 实验代码
├── data/                 # 数据集
├── paper/                # 论文材料
├── refine-logs/          # 实验计划与 bridge 日志
├── idea-stage/           # 想法探索产出
├── discussions/          # 进度报告
├── figures/              # 图表
├── overrides/            # 项目本地框架定制（集中管理）
├── .agents/skills/       # Codex skills symlink → framework skills
└── .claude/skills/       # Claude Code 兼容 skills symlink
```

## 顶层 Bucket 语义

新增四个顶层目录，用于给不同类型资产提供清晰的归属：

### `examples/` — 使用示例
- 框架的完整使用示例（一个最小科研项目、一个 skill 开发示例）
- 不是测试，而是面向用户的可运行示范
- 示例内的项目结构应与真实科研项目一致

### `compat/` — 兼容性层
- 旧版 framework 的向后兼容支持
- 迁移脚本（从旧结构到新结构）
- 废弃接口的 shim/adapter
- 目标：让用户平滑升级，不破坏现有项目

### `incubating/` — 孵化中资产
- 实验性 skill、新工具、新模板
- 开发中功能，**不保证稳定性**，可能随时重构或删除
- 一旦成熟，通过 promote 流程移入正式目录（skills/、tools/、templates/）
- 每个 incubating 条目必须包含 `INCUBATING.md`，说明：
  - 实验目的
  - 预计成熟时间或 promote 条件
  - 当前已知限制

### `legacy/` — 历史残留
- 不再维护但暂时保留的文件（如旧版 README、已弃用文档）
- **只出不进**：清理后不再新增
- 每个遗留文件应注明替代位置或弃用原因

## Project Override 策略

项目允许对 framework 做**浅层、受控**的本地定制，但必须：

1. **集中登记**：所有 override 条目登记在 `project.yaml#overrides`
2. **生命周期元数据**：每个 override 必须声明
   - `why` — 为什么需要这个 override（业务原因）
   - `owner` — 负责人
   - `created_at` — 创建时间
   - `promote_or_delete_by` — 预计迁移到 framework 或删除的时间
   - `type` — skill / template / tool / config
3. **禁止未经登记的 override**：Agent 遇未经登记的本地文件覆盖上游，应拒绝或要求登记

override 目录结构示例：

```
my-research/overrides/
├── skills/
│   └── custom-preprocess/
│       └── SKILL.md
└── templates/
    └── custom-plan.tmpl
```

## Framework 版本记录

每个项目通过 `project.yaml` 记录当前使用的 framework 版本：

```yaml
framework:
  path: "[你的framework位置]"
  repo: "https://github.com/..."
  version: "v2.1.0"      # tag/branch
  commit: "abc1234"      # 固定 commit hash
  recorded_at: "2026-06-10T00:00:00Z"
```

升级流程：
1. 框架维护者发布新版本
2. 项目开发者运行 `$framework-update` 或 `bash tools/install_aris.sh --reconcile`
3. 更新 `project.yaml` 中的 version/commit/recorded_at
4. 检查 incubating 条目是否有 promote 机会

## 迁移指南

### 当前 repo 中的项目资产

以下目录是**项目级资产**，不应长期留在 framework repo 根目录：

- `discussions/` — 周报、进度报告
- `figures/` — 论文图表
- `idea-stage/` — 想法探索产出
- `paper/` — 论文材料
- `refine-logs/` — 实验计划与日志

**建议**：
- 若这些目录属于当前活跃科研项目，将来应迁移到独立项目 repo
- 若属于历史项目，可归档到 `legacy/` 或独立 archive repo
- 框架文档中已明确这些为 project assets，新工作不应再向 framework repo 根目录新增此类内容

### 当前 repo 中的 dev-only 资产

- `logs-orang/` — 开发日志，建议移入独立 dev repo 或删除
- `community_papers/` — 若为用户收集，建议作为项目资产；若为框架示例，移入 `examples/`
- `xhs_post.md` — 推广材料，建议作为项目资产或删除

## 相关文件

- 安装与版本管理: `tools/install_aris.sh`
- 项目模板: `templates/project.yaml.tmpl`
- 项目文件指南: `docs/PROJECT_FILES_GUIDE.md`
- 三边架构: `docs/TRIPARTITE_ARCHITECTURE_GUIDE.md`
