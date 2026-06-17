# 2026-06-16 Context Archive: Skill Governance, Integrity, and Feishu Transport

本归档记录 2026-06-16 `grill-with-docs` 会话中已经收口的框架治理语义。当前有效术语仍以根目录 `CONTEXT.md` 为准；本文件用于保留决策脉络和后续功能升级的可追溯入口。

## 本轮已收口方向

### Skill governance

- 将 skill 文档中的技能名称出现区分为 Invocation Edge、Reference Edge、Skill List Entry 和 Unclassified Skill Mention。
- 全库依赖分类属于 Skill Governance 和后续工具链，不属于 `grill-with-docs` 本体职责。
- `grill-with-docs` 是 Design Grilling 的标准入口，负责在人类治理门前澄清术语、假设和边界，并把稳定术语写回 `CONTEXT.md`。
- Global Context Sweep 是 grilling 的内部宽度检查，不能破坏一次只问一个问题的交互规则。

### Role and transport boundaries

- ARIS Role 是稳定职责边界；Role Transport 是实现角色的运行机制。
- Reviewer 可以由本地 agent、CLI session、MCP 或 API 实现，但不能削弱 reviewer independence。
- transport 变化不应改写 Logical Skill Graph，只进入 Runtime Binding View。

### Experiment integrity

- `experiment-integrity` 是顶层 workflow/module short name，不是 skill 名。
- Experiment Integrity Verification 是 workflow 内部节点，不是整套 workflow。
- Experiment Integrity Workflow 的项目状态可持久、可恢复；运行进程只在需要处理工作、检查或人类决策时激活。
- experiment-plan、experiment-bridge、experiment-audit、result-to-claim 是 Integrity Participant Skill，产出 artifact、receipt、audit 或 claim judgment。
- `refine-logs/EXPERIMENT_INTEGRITY.md` 是人类入口摘要和证据索引，不是 checkpoint 数据库。
- live queue/status 属于 Project Runtime State；audit-facing reports/evidence index 默认可提交、可审计。

### Grilling archive and feature lineage

- `CONTEXT.md` 是 Semantic Root，不在开发者 DAG 中强制画出所有文档对它的全局依赖。
- 每次重要功能升级应保留 Feature Decision Lineage：context archive -> ADR/plan -> implementation -> validation。
- Framework governance grilling 归档放在 `to-developer/context-archive/YYYYMMDD-topic.md`。

### Feishu/Lark transport

- Feishu/Lark 接入属于 Transport Adapter Skill/bridge 层，不是 Leader、workflow runtime 或 remote shell。
- 新方向是接入 `lark-channel-bridge` 作为默认 Feishu/Lark transport，替代当前薄弱的 `feishu-session` 自研桥接路径。
- 旧的 `mcp-servers/feishu-bridge` + `tools/aris_feishu_session.py` 可保留为 ARIS-managed legacy/fallback path。

## 后续一件一件做

1. Feishu/Lark transport 迁移：更新 `feishu-session` skill、用户文档、管理员部署文档，默认推荐 `lark-channel-bridge`。
2. Skill governance 实现：补 skill DAG/metadata 规则，区分 invocation/reference/list/discovery/unclassified。
3. `grill-with-docs` 升级：增加 Global Context Sweep、context archive 输出和 Feature Decision Lineage 记录。
4. Experiment Integrity Workflow：先写开发者方案和用户使用文档，再决定最小运行时实现。
5. Role transport configuration：项目初始化和运行中配置角色 transport/model/client 的默认与覆盖方式。

## 当前第一刀

本轮实现先处理 Feishu/Lark transport 迁移、dev-only realtest、cheap worker provider/run 恢复。其他项只保留在 lineage 中，不在同一改动里混做。
