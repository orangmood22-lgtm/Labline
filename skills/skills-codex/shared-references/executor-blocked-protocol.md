# Executor Blocked Protocol

适用于 Coder / Deployer / Writer / Worker。

1. 遇到阻塞，先尝试一种低风险绕过。
2. 失败后再尝试第二种低风险绕过。
3. 两次都失败，写 `BLOCKED_REPORT.md` 并停止。
4. 不要让 Leader 代替你执行，也不要扩大权限或任务范围。

Worker 额外约束：如果阻塞需要架构决策、真实密钥、服务器权限、实验 claim 判定或 promote/rollback，必须直接停止并交回 Leader。
