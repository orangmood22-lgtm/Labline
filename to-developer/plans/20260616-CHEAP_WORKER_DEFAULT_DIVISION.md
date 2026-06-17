# 开发侧 cheap worker / gpt-5.4-mini 默认分工

> 创建时间: 2026-06-16
> 适用对象: ARIS 开发侧 Leader、Codex、gpt-5.4-mini worker、reviewer
> 状态: dev-only 草案

本文定义开发侧默认分工。它不引入新的 ARIS Role；它只规定一种默认的 Role Transport / worker 运行方式，用于把低风险、可批量处理的工作从主控路径中剥离出来。

`dev-worker` 的职责文档位于 `to-developer/skills/dev-worker/SKILL.md`。它是 Developer Skill，不是 User Skill，不进入用户项目 role graph。

第一版 Developer Skill 安装面只支持 Codex：`to-developer/skills/dev-*` 链接到 dev checkout 的 `.agents/skills/dev-*`，不创建 `.claude/skills/dev-*`。

第一批 Developer Skill Fork：

- `dev-caveman` <- `skills/caveman`
- `dev-tdd` <- `skills/tdd`
- `dev-diagnose` <- `skills/diagnose`
- `dev-review` <- `skills/review`
- `dev-grill-docs` <- `skills/grill-with-docs`
- `dev-handoff` <- `skills/handoff`
- `dev-zoom-out` <- `skills/zoom-out`

## 默认控制面

开发侧默认由 `Codex` / `leader` 负责最终判断和收口：

- 决定任务是否需要拆分、复核或直接执行。
- 决定是否允许 promote 到 stable。
- 决定是否接受 worker 草案并合并为正式变更。
- 负责对外输出最终结论、解释和变更摘要。

`gpt-5.4-mini` worker 只做高吞吐、低风险、可复核的局部工作，不接管主控权。

## worker 适合处理的工作

`gpt-5.4-mini` worker 默认可以承担这些任务：

- 批量文档整理和格式统一。
- 扫引用、补链接、补交叉引用。
- 测试草案、测试补丁草案、最小回归用例草案。
- 低风险 patch 草案，例如文字修正、注释修正、断言补全、文档索引补全。
- 对现有材料做结构化摘要，但不替代结论。

worker 不负责：

- 最终设计决策。
- 风险定级的最终裁定。
- 直接 promote 到 stable。
- 以自己的输出替代 leader 的审阅和签收。

## worker provider 配置

开发侧默认 worker provider 是 `codex_subagent`，对应 `gpt-5.4-mini`。

如需接入更便宜或更适合批量任务的 OpenAI-compatible provider，可以单独注册命名 provider，而不改变 worker 的职责边界。推荐的 DeepSeek 配置为：

- `provider`: `deepseek-v4-flash`
- `transport`: `openai_compatible`
- `model`: `deepseek-v4-flash`
- `base_url`: `https://api.deepseek.com/v1`
- `api_key_env`: `DEEPSEEK_API_KEY`

注意：

- 只记录环境变量名，不记录 API key 值。
- task file、日志和 stdout 都不能泄露真实密钥。
- `base_url` 可以覆盖，但 provider 名称和 model 仍应保留明确含义，便于批量任务追踪。

规范命令使用 `aris dev rt ...` 短命令；`aris dev runtime ...` 是等价长命令。不保留 `aris dev worker ...` 作为 canonical 入口。

最小配置文件示例：

```dotenv
agent=dev-worker
provider=deepseek-v4-flash
base_url=https://api.deepseek.com/v1
api_key=sk-...
model_name=deepseek-v4-flash
```

注入配置：

```bash
aris dev rt load .env
```

`load` 会将 provider/agent 绑定写入 `~/.aris/dev-runtime.json`，将 API key 写入本机 `~/.aris/dev-runtime.env` 并设为 `0600`。运行时优先读取环境变量，其次读取该本机 secret 文件；stdout、task file、metadata 不打印真实 key。

等价的手动配置命令：

```bash
aris dev rt provider set deepseek-v4-flash --transport openai_compatible --model deepseek-v4-flash --base-url https://api.deepseek.com/v1 --api-key-env DEEPSEEK_API_KEY
aris dev rt use dev-worker deepseek-v4-flash
aris dev rt prompt dev-worker "批量扫文档并补链接" --file docs/FEISHU_INTEGRATION.md
aris dev rt run dev-worker "批量扫文档并补链接" --file docs/FEISHU_INTEGRATION.md
```

## prompt / run / 日志分工

worker 的 CLI 分成两个最小步骤：

1. `prompt` 只负责把任务整理成可追踪的 task 文件。
2. `run` 负责真正调用 provider，并把一次执行落到独立日志目录。

`run` 的最小行为如下：

- 读取 provider 配置中的 `model`、`base_url`、`api_key_env`。
- 从环境变量读取 API key 值，但只在请求时使用，不写入 stdout、task 文件、request.json、response.md 或 metadata.json。
- 对 `transport=openai_compatible`，调用 `POST /chat/completions`。
- 请求消息包含 system guardrails 和 user task prompt。
- 默认超时 120 秒，可通过 CLI 参数覆盖。
- 每次运行写入 `to-developer/logs/dev-workers/<timestamp>-<slug>/`。
- 目录内保存 `task.md`、`request.json`、`response.md`、`metadata.json`。
- stdout 只打印 `run_dir`、`provider`、`model`、`response_file`。
- 不自动 apply patch，不自动 commit，不 promote。

`task.md` 可以来自 `prompt` 生成的文件，也可以通过 `--task-file` 直接指定已有任务文件。

对 `transport=codex_subagent`，CLI runner 不执行实际任务；它会明确报错，表示这类 transport 由当前 Codex session 的 subagent 工具执行。

## 输出追踪要求

worker 的输出必须可追踪、可回放、可复核：

1. 每个输出都要带输入来源，至少包括文件路径、章节名、测试名或任务号。
2. 每个草案都要标记修改范围，避免把局部建议伪装成全局结论。
3. 每个补丁草案都要保留可审查的差异说明，不允许只给最终成品而不留依据。
4. 每个引用修正都要说明依据文件，避免无来源补链。
5. 每个测试草案都要说明预期覆盖点和失败信号，方便 leader 复核。

推荐的输出格式是：

```text
source: <path or task id>
scope: <what changed>
risk: <low / medium / high>
decision: <draft only / needs review / ready for leader>
```

## 协作边界

- `leader` 决定任务拆分和合并顺序。
- `gpt-5.4-mini` worker 或其他 cheap worker provider 产出草案。
- reviewer 独立检查草案。
- 只有 leader 能收口成正式变更。

如果 worker 发现任务超出低风险范围，应该停止在草案层，并把问题回推给 leader，而不是继续扩展成最终方案。

## 适用约束

这个默认分工适用于：

- 开发者文档整理
- 维护性测试草案
- 引用和链接清扫
- 小范围、低风险的补丁草案

这个默认分工不适用于：

- 需要架构决策的改动
- 需要 promote 判断的改动
- 影响用户可见行为的高风险改动
- 需要 reviewer 独立意见才能继续的改动

## 追踪提示

任何由 worker 产出的材料，在进入开发日志或后续计划前，都应保留原始来源链接。若无法回溯到源文件、任务号或草案输入，默认视为不可直接合并。
