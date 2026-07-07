# 飞书 / Lark 集成

本文说明如何用飞书 / Lark 远程控制本地的 Codex CLI 或 Claude Code 会话。

默认推荐使用 [`lark-channel-bridge`](https://github.com/zarazhangrui/lark-coding-agent-bridge)。它是一个外部传输适配器，可以把飞书 / Lark 消息转发给本地 Codex CLI 或 Claude Code，支持流式卡片、按聊天隔离会话、工作区切换，以及首次运行时的二维码配置。

仓库内旧方案 `mcp-servers/feishu-bridge` 加 `tools/labline_feishu_session.py` 仍保留在本文后半部分，作为 legacy / fallback 路径。只有在你明确需要 Labline 的 inbox/outbox 文件、报告生成，或者 tmux 注入已有 TUI 会话时，才使用旧方案。

## 推荐方案：`lark-channel-bridge`

`lark-channel-bridge` 负责把飞书 / Lark 消息转发到本地 `codex` 或 `claude` 进程。它不会把飞书变成远程 shell，不会成为 Labline Leader，也不会替你做 workflow 决策。真正执行仍发生在本地 Codex / Claude Code 会话中，并遵守该 agent 的正常权限和当前工作区。

Labline 用 `lane feishu ...` 包了一层外部 bridge，避免用户记很长的命令。这个 wrapper 不 vendor、不重写 `lark-channel-bridge`，只负责安装、启动、检查和定位日志。

前置条件：

- Node.js >= 20.12
- 本地已安装并登录 Codex CLI 或 Claude Code
- 一个飞书 / Lark PersonalAgent 应用；首次运行的二维码向导可以创建并绑定

安装：

```bash
lane feishu install
lane feishu doctor
```

`lane feishu install` 默认使用 `~/.labline/node` 作为用户级 npm prefix，所以普通用户在共享服务器上也能安装。Labline 运行 `lane feishu ...` 时会自动把该 prefix 的 `bin` 目录加入路径。管理员如果明确想装到系统级，可以用：

```bash
lane feishu install --scope system
```

在当前项目目录做首次前台配置：

```bash
cd [你的project位置]
lane feishu run
```

这会启动：

```text
lark-channel-bridge run --profile labline-codex --agent codex --workspace [当前目录]
```

如果 PersonalAgent 应用还没配置好，首次运行会打开 bridge 的二维码向导。

二维码配置成功后，把 Codex profile 作为后台服务运行：

```bash
cd [你的project位置]
lane feishu start
lane feishu status
```

Claude Code 建议使用单独 profile：

```bash
cd [你的project位置]
lane feishu run --profile lane-claude --agent claude
```

常用本地命令：

```bash
lane feishu stop
lane feishu restart
lane feishu logs --tail 50
```

### 参数含义

| 参数 | 含义 | 多人使用建议 |
|------|------|--------------|
| `--home` | `lark-channel-bridge` 的配置根目录，里面保存飞书应用配置、profile 状态和私有 lark-cli 配置 | 一个人一个 home，例如 `~/.lark-channel-zhangsan` |
| `--profile` | 一个 bridge 运行配置名；同一个 home 下可以有多个 profile | 一个项目一个 profile，例如 `zhangsan-qy-iOD` |
| `--workspace` | 本地 agent 实际工作的项目目录 | 指向要控制的 Labline project，例如 `/labline/projects/qy-iOD` |
| `--agent` | 被 bridge 拉起的本地 agent CLI | 默认 `codex`；Claude Code 兼容时用 `claude` |
| `--no-proxy` | 清理代理变量后启动 bridge | 只在直连飞书可用、代理反而失败时使用 |

推荐显式写全参数，尤其是在多人共用同一个 Linux 账号或 root 账号时：

```bash
lane feishu run \
  --home ~/.lark-channel-zhangsan \
  --profile zhangsan-qy-iOD \
  --workspace /labline/projects/qy-iOD
```

### 多人/多项目操作方式

Labline 推荐的隔离方式是：

- **每个真人一个 `--home`**：绑定自己的飞书/Lark PersonalAgent app，避免二维码配置、OAuth token、lark-cli 私有配置互相覆盖。
- **每个项目一个 `--profile`**：同一个人同时控制多个项目时，用不同 profile 区分。
- **每个 profile 固定一个 `--workspace`**：启动时就绑定到目标 project，飞书里仍可用 `/cd` 临时切换。
- **每个长期 bridge 放进独立 tmux session**：共享服务器、root 账号、容器里优先用 `lane feishu run`，不要依赖 systemd user service。

例子：两个人在同一台服务器、同一个 Linux 账号下分别控制自己的项目：

```bash
tmux new-session -d -s feishu-zhangsan-qy-iOD '
cd /labline/projects/qy-iOD
lane feishu run --home ~/.lark-channel-zhangsan --profile zhangsan-qy-iOD --workspace /labline/projects/qy-iOD
'

tmux new-session -d -s feishu-lisi-mvdet '
cd /labline/projects/mvdet
lane feishu run --home ~/.lark-channel-lisi --profile lisi-mvdet --workspace /labline/projects/mvdet
'
```

如果 A 需要让 B 临时访问自己的项目，有两种安全做法：

1. A 和 B 明确共用同一个项目目录，B 用自己的 `--home` 和自己的 profile 指向 A 的 `--workspace`。
2. 项目目录用 Linux group/ACL 控制读写权限，bridge 只负责消息接入，不负责权限隔离。

不要误解为“拉一个群聊就自动隔离权限”。群聊只能决定哪些人能给 bot 发消息；真正的文件读写权限仍由运行 bridge 的本地用户和项目目录权限决定。

### tmux 推荐启动

服务器、容器、root 账号环境下，优先这样跑：

```bash
tmux new-session -d -s feishu-[用户]-[项目] '
source ~/.proxy_env 2>/dev/null || true
cd [你的project位置]
lane feishu run --home ~/.lark-channel-[用户] --profile [用户]-[项目] --workspace [你的project位置]
'
```

查看：

```bash
tmux attach -t feishu-[用户]-[项目]
lane feishu logs --home ~/.lark-channel-[用户] --profile [用户]-[项目] --tail 100
```

停止：

```bash
tmux kill-session -t feishu-[用户]-[项目]
```

`lane feishu start` 会尝试使用上游 bridge 的后台服务机制。桌面 Linux 可以用；服务器、Docker、root shell 中经常缺少 user systemd/dbus，遇到 `Failed to connect to bus` 时直接改用上面的 tmux + `lane feishu run`。

### 代理约定

Labline 不建议给 bridge 设置 `ALL_PROXY/all_proxy`。实践中 `curl` 可能能通过 `ALL_PROXY` 访问飞书，但 Node/Lark SDK 可能走另一条代理解析路径并出现 `socket hang up`。推荐只设置 HTTP/HTTPS 两套大小写变量：

```bash
export HTTP_PROXY=http://127.0.0.1:[你的代理端口]
export HTTPS_PROXY=http://127.0.0.1:[你的代理端口]
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export NO_PROXY=127.0.0.1,localhost,::1
export no_proxy="$NO_PROXY"
export NODE_USE_ENV_PROXY=1
unset ALL_PROXY all_proxy
```

容器部署会自动生成 `~/.proxy_env`，并提供：

```bash
proxy-on
proxy-off
```

如果启动时报 `could not resolve bot identity`，先看代理诊断：

```bash
lane feishu doctor --home ~/.lark-channel-[用户] --profile [用户]-[项目]
env | grep -i proxy
```

如果直连飞书开放平台可用，而代理路径失败，才使用：

```bash
lane feishu run --no-proxy
lane feishu start --no-proxy
```

有些服务器上飞书开放平台必须直连，但 Codex API 必须走本机代理。这时 bridge 父进程仍用 `--no-proxy`，只给 agent 子进程注入代理：

```bash
LABLINE_AGENT_HTTP_PROXY=http://127.0.0.1:[你的代理端口] \
LABLINE_AGENT_HTTPS_PROXY=http://127.0.0.1:[你的代理端口] \
LABLINE_AGENT_NO_PROXY=127.0.0.1,localhost,::1 \
lane feishu run --no-proxy
```

这些 `LABLINE_AGENT_*_PROXY` 变量只会映射给 Codex agent 子进程和 `native-codex` auto-wakeup，不让 Node/Lark SDK 走代理。

常用飞书 / Lark 命令：

| 命令 | 作用 |
|------|------|
| `/cd <path>` | 切换当前项目 / 工作区目录 |
| `/ws` | 管理已保存工作区，例如 list/save/use |
| `/status` | 显示 profile、agent、工作目录、session、身份和运行状态 |
| `/fork [名称]` | Codex profile 下 fork 当前 Codex thread，并可选设置新 thread 名称 |
| `/rename <名称>` | Codex profile 下重命名当前 Codex thread |

如果启动时没有传 `--workspace`，或者想把一个聊天线程切到另一个 Labline 项目，用：

```text
/cd [你的project位置]
```

## Labline 边界

飞书 / Lark 集成在 Labline 里属于 Transport Adapter Skill 边界。bridge 只负责在聊天和本地 agent 进程之间传输消息、状态、审批、文件或报告。

它不是 Leader，不是 workflow runtime，也不是远程 shell。研究编排仍由当前 Codex / Claude Code 会话和其调用的 Labline skills 负责。

## Remote Observation 和 `/follow`

Labline runtime 状态的项目内真相在 `.labline/runtime/`。Feishu/Lark 只做 Remote Observation 和交互入口：它可以观察 Runtime Task、发送 `/status`、订阅 `/follow`，也可以把“停掉实验”这类请求转成 Runtime Control Intent，但不成为任务 owner。

常见远程消息：

| 消息 | 行为 |
|------|------|
| `/status` | 读取项目 runtime 摘要并返回当前状态 |
| `/follow` | 订阅当前项目或 parent Runtime Task 的进度投影 |
| `/follow <task_id>` | 订阅指定 child/detail task |
| `/unfollow` | 取消当前聊天的投影订阅 |
| “现在怎么样了” | 只读状态问题，走 Remote Observation，不注入 TUI |
| “顺便解释一下结果含义” | 走 bridge-owned BTW thread，不打断当前任务 |
| “停掉这个实验” | 转为高风险 control intent，需要确认或由 Leader/lease 处理 |

`/fork [名称]` 只适用于 Codex profile。它调用 Codex app-server 的 `thread/fork`，把当前 chat 切到 fork 后的新 Codex thread；如果传入名称，再调用 `thread/name/set`。它不会用飞书聊天记录摘要伪造上下文，也不会复制正在运行中的半截 turn；当前任务运行中时应先等待完成或 `/stop`。

`/rename <名称>` 只适用于 Codex profile。它调用 Codex app-server 的 `thread/name/set` 修改当前 chat 绑定的 active Codex thread 名称，不 fork 新 thread，不重命名飞书会话，也不改变消息上下文；当前任务运行中时应先等待完成或 `/stop`。

状态归属规则：

- bridge-owned state：飞书 chat id、open id、消息 archive、Remote Observation subscription、projection delivery state、BTW thread。
- project runtime state：Runtime Task、runtime events、lease、heartbeat、escalation、`archive_ref`、`task_id`、路由诊断。
- 项目 `.labline/runtime/` 不保存飞书 chat/open id、token、私有消息正文或投递失败详情。

普通进度会节流更新同一张投影状态卡；如果旧投影没有可更新的飞书 `message_id`，bridge 会补发一张状态卡并记录后续更新目标。completed、failed、cancelled、blocked、need_decision、anomaly、escalation 会 fresh reply。若同一活动状态已经投递过，但卡片长时间停在“正在调用工具/正在输出”等阶段，或超过 `next_expected_update` 后仍没有新状态，Remote Observation 会发一次 `stale_projection` 提示；这只是飞书显示层可能过期的提醒，不代表任务失败。heartbeat 正常平台期不会产生可见飞书推送。

普通飞书消息不需要提前 `/follow` 才能获得卡片保护。Labline bridge shim 会继续优先更新原 streaming card；如果 stream/update 报错、update 超时，或运行中健康探针发现上一张卡片已经不能确认更新，就自动发送“续接卡片”并把后续状态更新切到新卡片。若 profile 使用 markdown streaming，终态更新会等待 Feishu markdown card 的 throttle flush 和 update queue drain，并默认 fetch 校验原 streaming message 是否仍含“正在调用工具/正在输出/正在思考”；若校验失败或仍是旧运行态，会额外发送一条普通 markdown 终态镜像。续接卡片和终态镜像只表示飞书显示通道兜底，不表示 Codex 任务重启。默认 update 超时由 `LABLINE_STREAM_FLUSH_TIMEOUT_MS` 控制，运行中健康探针由 `LABLINE_CARD_CONTINUATION_IDLE_MS` 控制，卡片最大年龄兜底由 `LABLINE_CARD_CONTINUATION_MAX_AGE_MS` 控制，markdown 终态校验超时由 `LABLINE_MARKDOWN_TERMINAL_VERIFY_TIMEOUT_MS` 控制；如需完全关闭终态镜像，可设置 `LABLINE_MARKDOWN_TERMINAL_FALLBACK_ENABLED=off`。

`/follow` 的可见推送由当前 bridge profile 内置的 Remote Observation poller 完成。poller 默认只扫描当前 workspace/project 且当前 profile 创建的 active subscription；如果换了 bridge profile，建议在新 bot chat 里重新发送 `/follow`。只有确认新旧 profile 使用同一个可投递 bot/chat 权限时，才设置 `LABLINE_PROJECTION_INCLUDE_CROSS_PROFILE=1` 让当前 project poller 接管跨 profile 订阅。poller 会调用 `projection-plan`；`patch` 动作会更新上一张投影状态卡或补发一张可更新状态卡，`fresh_reply` 动作用于 terminal/blocked/anomaly/stale_projection 等需要用户注意的状态。同一 state signature 成功投递后会记录 `delivery-record`，避免 blocked/terminal/stale_projection 状态重复刷屏。可以用 `LABLINE_PROJECTION_POLL_DISABLED=1` 关闭，或用 `LABLINE_PROJECTION_POLL_INTERVAL_MS` 调整轮询间隔。

项目自己的 debug monitor 可以额外发送监控告警，但它必须显式配置 alert chat；它不是 `/follow` 协议投递器，也不会替代 bridge-owned subscription。

如果需要让 Leader 在 runtime escalation、未处理的 terminal failure，或 detached tmux job 退出后自动跑一轮接手，可以显式打开 bridge auto-wakeup：设置 `LABLINE_AUTO_WAKEUP_ENABLED=1` 后重启对应 bridge profile。bridge 只定时调用 `lane workflow wakeup-plan` 判断；`wakeup-plan` 会直接识别未被 `leader.decision` / resolution 处理过、且未被后续 `retry_of` 取代的 `failed` / `cancelled` Runtime Task，也会检查 `tmux` handle：session 已退出且 required artifact 存在时产生 `detached_job_completed` candidate，session 已退出但 required artifact 缺失时产生 `detached_job_exited` candidate，不依赖先跑 heartbeat。真正启动由 `lane workflow wakeup --backend native-codex` 执行，并通过 `.labline/runtime/` 的 `leader_session` lease 和 `wakeup.*` 事件去重。默认检查间隔由 `LABLINE_AUTO_WAKEUP_INTERVAL_MS` 控制，默认 backend 是 `native-codex`；高风险 control intent 仍会停在 `needs_confirmation`，不会自动执行。若维护者确认上一次同一 `wakeup_key` 没有实际唤醒成功，可以手动运行 `lane workflow wakeup-plan --force` 预览，或运行 `lane workflow wakeup --force --backend native-codex` 重试；`--force` 只绕过去重，并继续保留高风险确认和 `leader_session` lease。`native-codex` wakeup 默认用 `codex exec -s danger-full-access`，避免在不支持 unprivileged namespace 的环境里触发 `bwrap` sandbox 失败；可用 `--codex-sandbox` 或 `LABLINE_AUTO_WAKEUP_CODEX_SANDBOX` 覆盖。bridge 会把 started、completed、failed、非健康 skip（例如 `wakeup_already_started`、`lease_unavailable`）和 `needs_confirmation` 通知回投到当前 profile/project 的 active `/follow` chat；没有 `/follow` 订阅但仍需要固定投递时，可用逗号分隔的 `LABLINE_AUTO_WAKEUP_CHAT_ID` 指定 chat。只有确认跨 profile chat 由同一个 bot 可投递时，才设置 `LABLINE_AUTO_WAKEUP_INCLUDE_CROSS_PROFILE=1`。同一检查结果会按 `LABLINE_AUTO_WAKEUP_NOTICE_THROTTLE_MS` 限流，避免每轮计划都刷屏。该输出是用户可见通知，Leader prompt 会要求默认用中文解释决策和下一步，只保留必要的英文状态值、路径和 task id。

长任务规则：

- 预计超过 3 分钟的安装、编译、下载、训练、部署、批量评估或长时间 agent 等待，必须先落到 `.labline/runtime/`：Runtime Task 或 Agent Status Snapshot、durable job handle、日志/结果路径、`next_expected_update`。
- Leader 在飞书 turn 里最多短等 120 秒用于捕获即时失败；任务仍在运行时必须结束当前回复，给出 task id、状态路径、日志路径和后续 `/status` / `/follow` 查询方式。
- 新的可见推送只用于 `completed`、`failed`、`cancelled`、`blocked`、`need_decision`、`anomaly` 或 heartbeat escalation；健康运行平台期只更新本地 runtime/节流投影，不能连续刷屏。

## 旧方案 / Fallback：Labline 托管 Runner

下面是旧的 Labline 托管路径：

```text
mcp-servers/feishu-bridge/server.py + tools/labline_feishu_session.py
```

只有在需要以下能力时继续使用旧方案：

- Labline 管理的运行时文件
- 显式查看 inbox/outbox
- 手机会话合并报告
- tmux live TUI 注入

## 功能状态

| 方向 | 状态 | 路径 |
|------|------|------|
| 本地到飞书 | 支持 | `POST /send`、`POST /update` 更新卡片 |
| 飞书到本地 | 支持 | 飞书长连接 -> `/control/message` |
| 飞书消息到 Codex | Legacy/fallback | `tools/labline_feishu_session.py` 消费 inbox 并运行 `codex exec` |
| Codex 回复到飞书 | Legacy/fallback | runner 写 outbox 并调用 `/send` |
| 接管已打开的 Codex TUI | Legacy/fallback | `--tmux-pane <target>` 把飞书文本注入 live pane |

bridge 本身不执行 shell 命令、tools 或 skills。它只记录消息和审批。Codex 执行发生在用户主动启动的 session runner 中。

## 术语

- **推荐 Bridge**：`lark-channel-bridge`，外部飞书 / Lark 传输适配器，连接本地 Codex CLI 或 Claude Code。
- **Legacy Feishu Bridge**：`mcp-servers/feishu-bridge/server.py`，本地 HTTP 加飞书长连接进程。
- **Remote Session Inbox**：`.labline/feishu-control/inbox/<session_id>.jsonl`。
- **Feishu-Controlled Session**：旧方案里由 `tools/labline_feishu_session.py` 消费的注册会话。
- **Control Lease**：输入所有权标记。飞书消息可以临时取得远程优先权；`/release` 交还给本地。

稳定术语见 [CONTEXT.md](../CONTEXT.md)。详细 ADR 保存在 dev checkout 中，不属于稳定发布文档。

## Legacy 飞书应用配置

在 <https://open.feishu.cn/app> 创建内部应用。

需要启用的应用能力：

- Bot

需要的权限：

- `im:message`
- `im:message:send_as_bot`
- `im:message.p2p_msg:readonly`
- `im:message.group_at_msg:readonly`

需要订阅的事件：

- `im.message.receive_v1`

本地 / 服务器部署时使用长连接模式。修改权限或事件后，创建并发布一个新应用版本。确认应用可见范围包含你的账号。

## Legacy 本地配置

在 framework 或项目根目录创建 `.env`。不要提交这个文件。

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_USER_ID=ou_xxx
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_ENABLE_WS=1
BRIDGE_PORT=5000
LABLINE_PROJECT_ROOT=/lane/lane-dev
LABLINE_FEISHU_CONTROL_ROOT=
```

`FEISHU_USER_ID` 必须和 `FEISHU_RECEIVE_ID_TYPE` 匹配：

| ID 值 | `FEISHU_RECEIVE_ID_TYPE` |
|-------|---------------------------|
| `ou_...` | `open_id` |
| tenant user id | `user_id` |
| union id | `union_id` |

安装 Python 依赖：

```bash
python3 -m venv .venv-feishu
.venv-feishu/bin/pip install -r mcp-servers/feishu-bridge/requirements.txt
```

如果因为代理不一致导致网络失败，把大小写 proxy 环境变量设成一致：

```bash
export HTTP_PROXY=http://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897
export http_proxy=http://127.0.0.1:7897
export https_proxy=http://127.0.0.1:7897
export NO_PROXY=127.0.0.1,localhost
export no_proxy=127.0.0.1,localhost
```

端口按你的本地代理实际配置调整。

## 启动 Legacy Bridge

终端 1：

```bash
cd /lane/lane-dev
set -a; source .env; set +a
export FEISHU_ENABLE_WS=1
export LABLINE_PROJECT_ROOT=/lane/lane-dev
.venv-feishu/bin/python mcp-servers/feishu-bridge/server.py
```

预期输出包含：

```text
Feishu WS receiver enabled
connected to wss://msg-frontier.feishu.cn/ws/v2...
```

Smoke test：

```bash
curl -sS http://127.0.0.1:5000/health
curl -sS -X POST http://127.0.0.1:5000/send \
  -H 'Content-Type: application/json' \
  -d '{"type":"text","content":"Labline Feishu bridge live test"}'
```

## 启动 Legacy Codex Runner

终端 2：

```bash
cd /lane/lane-dev
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /lane/lane-dev \
  --profile leader \
  --bridge-url http://127.0.0.1:5000
```

Codex 回复默认以飞书交互卡片发送，所以基础 Markdown 可以在飞书里渲染。需要纯文本时使用：

```bash
--feishu-format text
```

YOLO 模式会给 Codex 传入 `--dangerously-bypass-approvals-and-sandbox`：

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /lane/lane-dev \
  --profile leader \
  --bridge-url http://127.0.0.1:5000 \
  --feishu-format card \
  --yolo
```

只在可信机器和可信项目中使用 YOLO。该模式下 Codex 可以不经过审批提示直接运行命令。

然后给飞书 bot 发私聊消息。流程是：

```text
Feishu -> bridge -> Remote Session Inbox -> codex exec -> outbox -> Feishu
```

## Live TUI 接管

如果你正在看的 Codex CLI 位于 tmux 内，飞书可以把消息注入到这个正在运行的 live thread。

先列出 tmux pane：

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_command}'
```

用 live injection 模式启动 runner：

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --role leader \
  --project-root /lane/lane-dev \
  --bridge-url http://127.0.0.1:5000 \
  --tmux-pane dev:1.0 \
  --feishu-status-interval-seconds 15
```

这个模式会把飞书消息直接输入到当前 Codex TUI，等待 0.5 秒，然后默认用 `Enter` 提交。bridge 默认静默排队入站消息；runner 会在 Codex 处理期间更新一张状态卡，最后把 `task_complete.last_agent_message` 发回飞书。

状态卡正文刻意保持很短：

```text
`leader-phone` · 已收到信息 · 0s
`leader-phone` · 思考中 · 15s
`leader-phone` · 处理中 · 30s
`leader-phone` · 已完成 · 61s
```

显式使用纯文本状态：

```bash
--feishu-status-style plain
```

超时时会更新同一张卡：

```text
`leader-phone` · 超时，未收到最终回复
```

如果想恢复旧的额外队列确认消息，设置：

```bash
FEISHU_SEND_QUEUE_ACK=1
```

如果你的 TUI 仍然换行而不是提交，增加延迟或换一个提交键：

```bash
--tmux-submit-delay-seconds 1.0
--tmux-submit-key Enter
```

如果 runner 无法自动定位正确的 Codex transcript，显式绑定：

```bash
--codex-transcript ~/.codex/sessions/YYYY/MM/DD/rollout-....jsonl
```

如果只需要注入确认，不想镜像 transcript 回复：

```bash
--no-watch-codex-response
```

关闭 heartbeat 卡片：

```bash
--no-feishu-status-updates
```

强制使用旧行为：每次状态间隔发送一条新消息：

```bash
--feishu-status-mode send
```

不要对同一个 `--session-id` 同时运行 live injection 和 fresh `codex exec` runner；它们会竞争同一个 inbox。

继续最新保存的 Codex 对话：

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --bridge-url http://127.0.0.1:5000 \
  --resume-last
```

如果最新 Codex session 是你正在使用的活跃 TUI，不要用 `--resume-last`。`codex exec resume --last` 可能附着到这个 live session，而 `--output-last-message` 仍为空；runner 会报告 Codex 没有产生最终回复。此时优先使用 fresh exec 模式，或通过 `--codex-session-id` 绑定一个明确的非活跃 session。

如果 inbox 里已有旧消息，并且你不想重放：

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --bridge-url http://127.0.0.1:5000 \
  --mark-seen \
  --once
```

绑定指定的已保存 Codex 对话：

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --bridge-url http://127.0.0.1:5000 \
  --codex-session-id <codex-session-id>
```

## Legacy 飞书命令

| 消息 | 作用 |
|------|------|
| 普通文本 | 发送到活跃 session inbox |
| `$skill ...` | 作为普通文本发给 Codex runner；是否调用 skill/tool 由 Codex 判断 |
| `/sessions` | 列出已注册 session |
| `/use <session_id>` | 切换活跃 session |
| `@<session_id> message` | 将一条消息路由给指定 session |
| `/release` | 把 Feishu Control Lease 交还给本地 |
| `/interrupt` | 用 tmux `C-c` 中断当前 live Codex TUI 任务 |
| `/btw <question>` | 用当前 transcript 上下文问一个旁路问题；状态在飞书更新；答案回到飞书但不进入主 CLI thread |
| `/approve <code>` | 批准一个 pending action |
| `/reject <code>` | 拒绝一个 pending action |
| `/resume <target>` | 记录 resume 意图 |

被拒绝的命令：

- `/run ...`
- `/tool ...`

旧 bridge 会刻意拒绝执行这些命令。

## Legacy 运行时文件

默认根目录：

```text
.labline/feishu-control/
  sessions.json
  inbox/<session_id>.jsonl
  outbox/<session_id>.jsonl
  approvals/<code>.json
  runners/<session_id>.json
  reports/<session_id>.md
  responses/<session_id>/*.txt
```

这些文件是项目运行时状态，已被 Git 忽略。

## Legacy 手机会话合并

手机控制会话视为一个 fork。不要假设手机 runner 的隐藏 Codex 上下文会自动回到本地 TUI。只合并可审计状态。

生成报告：

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --write-report
```

生成报告并打印本地合并 prompt：

```bash
.venv-feishu/bin/python tools/labline_feishu_session.py \
  --session-id leader-phone \
  --project-root /lane/lane-dev \
  --merge-prompt
```

报告包含 inbox 消息、outbox 回复、runner 状态、`git status --short` 和 `git diff --stat`。回到电脑后，把打印出的 prompt 用在本地 Codex thread 里。

同一 fallback workflow 也暴露为 `feishu-session` skill。

## 测试

运行聚焦测试：

```bash
.venv-feishu/bin/python -m pytest \
  tests/test_labline_feishu_session.py \
  tests/test_feishu_control.py \
  tests/test_feishu_bridge_server.py \
  tests/test_agent_status.py -q
```

手动 live 检查：

```bash
curl -sS http://127.0.0.1:5000/health
curl -sS http://127.0.0.1:5000/control/sessions
```

给 bot 发私聊消息，然后检查：

```bash
tail -5 .labline/feishu-control/inbox/<session_id>.jsonl
tail -5 .labline/feishu-control/outbox/<session_id>.jsonl
```

## 排障

**本地能发到飞书，但飞书不能发消息给 bot**

- Bot 能力未启用。
- 应用版本未发布。
- 应用可见范围不包含你的账号。
- 缺少 `im:message.p2p_msg:readonly`。
- 缺少 `im.message.receive_v1` 事件。
- 长连接没有运行。

**`Invalid ids`**

`FEISHU_USER_ID` 和 `FEISHU_RECEIVE_ID_TYPE` 不匹配。`ou_...` 使用 `open_id`。

**收不到入站消息**

确认 bridge 输出里有连接到 `msg-frontier.feishu.cn`。如果没有，检查应用事件模式和已发布版本。

**Proxy connection refused**

大小写 proxy 环境变量可能指向不同端口。把它们设成一致。

## Legacy 限制

- legacy fresh runner 路径会对每条飞书消息调用一次 `codex exec` 或 `codex exec resume`。
- 审批 UI 卡片 / 按钮后端已就绪，但交互卡片体验尚未打磨。
- legacy bridge 不执行 tools。这是有意设计。
- legacy 路径偏 Codex；默认 Codex + Claude Code 远控请使用 `lark-channel-bridge`。
