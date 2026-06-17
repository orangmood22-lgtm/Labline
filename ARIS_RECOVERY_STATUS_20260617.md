# ARIS 恢复勘察状态 2026-06-17

## 现状

`/aris/aris-dev` 曾被清空，且目录属于 root：

```text
/aris/aris-dev:
drwxr-xr-x 2 root root ...
```

已在 `/tmp/aris-dev-recovered` 从 `/aris/framework` 克隆出恢复工作台，并在验证后同步回 `/aris/aris-dev`。当前 `/aris/aris-dev` 已恢复为 `researcher` 可写仓库，分支为 `recovered-dev`。

## 可用基线

`/aris/framework` 是完整 git 仓库：

```text
HEAD -> main, tag: v0.3.3
origin/main -> 335dbb8 release: document v0.3.3 feishu sender fix
origin/dev  -> 8ac65f1 release: document v0.3.3 feishu sender fix
```

`/aris/framework` 当前 `git status` 干净。

## 已知仍存在的外部状态

```text
/home/researcher/.aris/dev-workers.json
/home/researcher/.aris/framework-history/previous
/home/researcher/.aris/framework-update-status.json
/home/researcher/.aris/project-registry.json
/aris/backups/framework-backup-20260613-143059.tar.gz
```

`dev-workers.json` 很可能保留 DeepSeek provider 配置，但不保留 runner 代码。

## 已知丢失风险

以下内容可能只存在于误删前的 `/aris/aris-dev` 未提交 worktree：

- `to-developer/` developer DAG 和 context archive 最新改动。
- realtest dev-only 容器资产。
- Feishu/Lark `lark-coding-agent-bridge` 方向文档改动。
- `tools/aris` 中 `dev worker provider/prompt/run` 最新实现。
- `tests/test_aris_cli.py` 中 dev worker 测试。
- DeepSeek runner 的测试与文档。
- skill governance / Experiment Integrity / grilling archive 的最新 `CONTEXT.md` 术语扩展。

## 已恢复内容

- 远端 `dev` 基线。
- `aris dev worker config/provider/prompt/run` 开发侧 CLI。
- OpenAI-compatible worker provider 配置和 runner。
- DeepSeek provider 配置说明，`~/.aris/dev-workers.json` 中 `deepseek-v4-flash` 已恢复为 `https://api.deepseek.com/v1`。
- `to-developer/realtest/` dev-only 实机测试容器资产。
- Feishu/Lark 默认 `lark-channel-bridge` 文档方向，旧 ARIS runner 保留为 fallback。
- `CONTEXT.md` 中 Semantic Root、Feature Decision Lineage、Role Transport、Skill edge、Experiment Integrity、Cheap Worker 等术语。
- `to-developer/context-archive/20260616-skill-governance-integrity-feishu.md`。
- `to-developer/plans/20260616-CHEAP_WORKER_DEFAULT_DIVISION.md`。
- 开发者 DOC DAG 和开发日志。

## 已验证

```bash
python tools/update_developer_docs.py --check-only
python -m pytest tests/test_aris_cli.py tests/test_realtest_container_contract.py tests/test_developer_doc_dag.py -q
```

验证结果：

```text
developer doc dag ok: 37 nodes, 31 edges
21 passed, 4 subtests passed
```

## 下一步

1. 继续从 `recovered-patches/` 对照还有哪些未恢复补丁，例如更完整的 Experiment Integrity Workflow 实现和 skill governance 自动化。
2. 根据 `CONTEXT.md` 和 `to-developer/context-archive/` 逐项推进：Feishu/Lark transport、Skill Governance、grill-with-docs 升级、Experiment Integrity Workflow、Role Transport Configuration。
3. 在确认恢复范围后再决定是否提交、推送或重新 promote。
