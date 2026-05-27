# Mattpocock Skills 评估报告

> 已安装 6 个 skill（全部为 symlink），下面是每个的使用场景和在 ARIS 科研框架中的价值。

---

## 已安装 — 必装级

### 1. `/grill-with-docs`

**是什么：** `/grill-me` 的升级版。在 grill 过程中，每个决策落地时**自动更新项目文档**（CONTEXT.md、ADR 等）。

**使用场景：**
- 设计新实验方案时，讨论完直接沉淀到 `docs/adr/` 里
- 讨论框架改动时，决策自动写入 CONTEXT.md
- 避免"讨论完忘记记录"

**怎么触发：**
```
/grill-with-docs "频域特征提取模块的设计方案"
```

**vs `/grill-me`：** grill-me 只问问题不改文件；grill-with-docs 问完顺手更新文档。**讨论架构/设计用 grill-with-docs，快速决策用 grill-me。**

---

### 2. `/git-guardrails`

**是什么：** 给 Claude Code 装 git 安全钩子，拦截危险操作。

**拦截的命令：**
- `git push --force`
- `git reset --hard`
- `git clean -fd`
- `git branch -D`
- 直接 push 到 main/master

**使用场景：**
- 新手刚开始用 ARIS → 先跑一次 `/git-guardrails` 保护起来
- 防止 AI agent 误操作（Leader/Executor 有时会激进操作 git）
- 共享服务器上多人用同一个 repo → 防互相覆盖

**怎么触发：**
```
/git-guardrails
```

一次性设置，装完就生效。

---

### 3. `/to-issues`

**是什么：** 把计划/PRD/实验方案拆成独立的 Issue（GitHub/Gitea），每个 Issue 是一个可执行的垂直切片。

**使用场景：**
- `/experiment-plan` 产出实验计划后 → `/to-issues` 拆成可追踪的 tickets
- 论文 TODO 列表 → 拆成 Issue 分配给不同人
- 大重构计划 → 拆成小步骤，每步一个 Issue

**怎么触发：**
```
/to-issues
```

会读当前上下文（对话 + 文件），自动识别计划并拆分。

**与 ARIS 结合：** experiment-plan → to-issues → 每个 Issue 对应一个实验变体/ablation → 跑完关 Issue。完美配合 Gitea。

---

## 已安装 — 可选级

### 4. `/to-prd`

**是什么：** 把当前对话上下文直接转化为正式 PRD（产品需求文档），发到 Issue tracker。

**使用场景：**
- 和导师/组员讨论完研究方向 → `/to-prd` 输出正式文档
- 设计框架新功能讨论完 → 自动生成 PRD
- 避免"聊完没有落地文档"

**怎么触发：**
```
/to-prd
```

不会再问你问题（和 grill-me 不同），直接从对话中综合生成。

**输出格式：** Problem Statement → Solution → User Stories → Implementation Decisions → Testing Decisions → Out of Scope

**与 ARIS 结合：** 研究方向讨论 → to-prd → 正式 PRD → to-issues → 可执行 tickets。完整的决策→落地链路。

---

### 5. `/review`

**是什么：** 双轴代码审查 — 同时检查"代码规范"和"是否实现了 spec 要求"。

**两个轴：**
- **Standards 轴：** 代码是否符合项目规范（CLAUDE.md、CONTRIBUTING.md、ADR 等）
- **Spec 轴：** 代码是否实现了 Issue/PRD 要求的功能

**使用场景：**
- Executor 写完代码后，跑 `/review` 做初步自检
- 合并前审查：`/review` 对比 main 分支
- 审查别人的 PR

**怎么触发：**
```
/review               # 默认对比 main
/review HEAD~5        # 对比最近 5 个 commit 之前
/review feature-branch  # 对比指定分支
```

**vs ARIS Reviewer（Codex）：** Codex Reviewer 是跨模型审查（GPT 审 Claude 写的），侧重实验诚实度。`/review` 是同模型内快速规范+功能检查。两者互补。

---

### 6. `/write-a-skill`

**是什么：** 引导你写新 skill 的模板和最佳实践。

**使用场景：**
- 想给 ARIS 加新 skill（比如针对某个特定会议的投稿流程）
- 想把常用操作封装成可复用的 skill
- 新人学习 skill 结构

**怎么触发：**
```
/write-a-skill
```

会问你：覆盖什么领域？什么场景触发？需要脚本还是纯指令？然后输出完整的 `SKILL.md` + 辅助文件。

**与 ARIS 结合：** 框架开发者用。写完新 skill → 加到 `skills/` → 更新 CATEGORY_MAP → 重新生成 catalog。

---

## 推荐使用模式

| 场景 | 推荐组合 |
|------|---------|
| 新人上手 | 先跑 `/git-guardrails`，再正常使用 |
| 设计新实验/功能 | `/grill-with-docs` → `/to-prd` → `/to-issues` |
| 快速决策 | `/grill-me`（轻量）|
| 代码提交前 | `/review` 快速自检 |
| 给框架加功能 | `/write-a-skill` 写 skill → `/review` 审查 |

---

## 你提到的"TDD 和 caveman 一直开着"

这两个是**模式型 skill**，触发后持续生效直到关闭：

- **caveman** — 触发后每条回复都精简，直到 "stop caveman"
- **tdd** — 不是持续模式，每次需要主动触发

**建议：** 把 caveman 和 tdd 的规则写入 `CLAUDE.md` 的项目规则里，就能"一直开着"：

```markdown
## 默认模式

- 所有回复使用 caveman 模式（精简表达，保留技术准确度）
- 涉及代码修改时遵循 TDD：先写测试 → 实现 → 重构
- 落地新设计前先 /grill-me 或 /grill-with-docs
```

这样不用每次手动触发。

---

## 未安装（不推荐）

| Skill | 原因 |
|-------|------|
| `improve-codebase-architecture` | 面向产品代码，科研代码结构简单 |
| `prototype` | 面向 UI/产品原型，科研实验用 experiment-bridge |
| `triage` | Issue 工作流管理，科研项目 issue 量小 |
| `writing-beats/fragments/shape` | 英文博客写作，论文有专门 skill |
| `setup-pre-commit` | Husky/Prettier，科研项目不需要 |
| `obsidian-vault` | 个人笔记工具，ARIS 用 research-wiki |
