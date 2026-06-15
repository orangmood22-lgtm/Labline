# ADR-0004: Feishu Control Lease Prioritizes Remote Input

**状态：** 已采纳  
**日期：** 2026-06-14  
**决策者：** orangmood + AI

Feishu-Controlled Sessions will use a Control Lease to prevent unsynchronised local and remote input from racing. In the managed `aris-feishu-session` path, a Feishu message can acquire the lease and make Feishu the active input owner; local input is then blocked or redirected until the lease is released or expires. In the `$feishu-control on` path for an already-open Codex CLI session, the same model is advisory because ARIS cannot reliably intercept arbitrary local terminal input after the process already exists.

This design matches normal use: local control when the user is at the computer, Feishu priority when the user is away. It rejects simultaneous local/remote input and permanent Feishu lockout because both create confusing session state and weak auditability.
