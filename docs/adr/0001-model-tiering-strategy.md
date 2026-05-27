# ADR-0001: 三边架构模型分层策略

**状态：** 已采纳  
**日期：** 2026-05-26  
**决策者：** orangmood + AI

## 上下文

ARIS 三边架构（Leader / Executor / Reviewer）需要决定各角色用什么模型。核心 tradeoff：决策质量 vs token 成本。Leader 做规划（低 token 高质量），Executor 写代码（高 token 中质量即可），Reviewer 审查（中 token 高质量 + 跨模型盲区）。

## 决策

### 模型分配

| 角色 | 主力 (Coding Plan) | 备用 (DeepSeek) |
|------|-------------------|----------------|
| Leader | Claude Opus | DeepSeek V4 Pro |
| Executor Agent | Claude Sonnet (`model: "sonnet"`) | DeepSeek V4 Pro |
| Reviewer | GPT-5.5 via Codex MCP | GPT-5.5 (不变) |

### 切换粒度

**会话级**，通过 `cc-switch provider switch` 一键切换整个 Claude Code 的 API provider。不搞 Agent 级混用。

原因：Agent 子进程继承父进程 env，无法单独配 base_url。混用不同 provider 的模型行为差异（tool use 格式等）容易出 bug。

### Provider 预配

三个 provider：
1. `plan` — Coding Plan 官方（长期主力）
2. `中转站` — API 中转（过渡期主力）
3. `deepseek` — DeepSeek 备用（直连或走中转站均可）

## 考虑的替代方案

1. **Agent 级别切换** — Leader 走 Opus，Executor 走 DeepSeek。技术上不可行（env 继承问题）。
2. **Haiku 档位映射** — 中转站把 haiku 映射成 DeepSeek。可行但 hacky，切回 Plan 后 haiku 语义混乱。
3. **全部 Opus** — 质量最高但 token 成本 5x+。

## 后果

- Leader SKILL.md 所有 Agent 调用加 `model: "sonnet"`
- 买 Coding Plan 后 Executor 成本大幅降低（sonnet 包量内）
- 备用切换需手动 `cc-switch`，不自动 failover
- Reviewer 始终走 OpenAI API（独立计费），不受 provider 切换影响
