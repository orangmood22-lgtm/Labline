# ADR-0003: Feishu Control Uses Opt-In Codex Sessions

**状态：** 已采纳  
**日期：** 2026-06-14  
**决策者：** orangmood + AI

ARIS will make Feishu control an opt-in input and approval channel for live Codex Sessions, not a remote tool runner or a way to take over arbitrary historical threads. Feishu messages enter a Remote Session Inbox; the live Codex Session reads them and executes skills or tools under the normal local permission model. Remote Action Approval is scoped to one explicitly described pending action with expiry, rather than granting broad session authority.

This keeps the CLI as the execution boundary while still letting Feishu feel like a remote CLI for messages, checkpoint replies, status checks, and approvals. The rejected alternatives were bridge-executed tools, `tmux send-keys`/PTY injection into existing windows, and session-wide approve-all grants; all are more convenient but create higher risk of wrong-session execution, weak auditability, or remote shell equivalence.
