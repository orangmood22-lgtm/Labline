# ARIS 三边架构配置指南

## 总览

| 角色 | 模型 | 启动方式 |
|------|------|----------|
| **Leader** | Claude Opus 4.6（你的中转） | ccr preset `leader` → `ccr code` |
| **Executor** | DeepSeek V4 Pro（官方） | ccr preset `executor` → `ccr code` |
| **Reviewer** | GPT-5.5 | `codex`（已配好） |

---

## 第一步：创建两个 ccr preset

ccr 通过 `~/.claude-code-router/presets/` 管理不同配置。每个 preset 是一个文件夹，里面放一个 `manifest.json`。

### 1.1 创建 Leader preset

```bash
mkdir -p ~/.claude-code-router/presets/leader
```

写入 `~/.claude-code-router/presets/leader/manifest.json`：

```json
{
  "name": "leader",
  "description": "ARIS Leader - Claude Opus 4.6 via relay",
  "version": "1.0.0",
  "config": {
    "APIKEY": "<你的Anthropic中转key>",
    "Providers": [
      {
        "name": "claude-relay",
        "api_base_url": "<你的中转站地址>/v1/messages",
        "api_key": "<你的Anthropic中转key>",
        "models": ["claude-opus-4-6-20250514"]
      }
    ],
    "Router": {
      "default": "claude-relay,claude-opus-4-6-20250514"
    }
  }
}
```

### 1.2 创建 Executor preset

```bash
mkdir -p ~/.claude-code-router/presets/executor
```

写入 `~/.claude-code-router/presets/executor/manifest.json`：

```json
{
  "name": "executor",
  "description": "ARIS Executor - DeepSeek V4 Pro",
  "version": "1.0.0",
  "config": {
    "APIKEY": "<你的DeepSeek官方key>",
    "Providers": [
      {
        "name": "deepseek",
        "api_base_url": "https://api.deepseek.com/chat/completions",
        "api_key": "<你的DeepSeek官方key>",
        "models": ["deepseek-chat"],
        "transformer": {
          "use": ["deepseek"],
          "deepseek-chat": {
            "use": ["tooluse"]
          }
        }
      }
    ],
    "Router": {
      "default": "deepseek,deepseek-chat"
    }
  }
}
```

> **注意**：DeepSeek 通过 ccr 走的是 OpenAI 兼容格式 (`/chat/completions`)，不是 Anthropic 格式。ccr 的 `deepseek` transformer 会自动做格式转换。

---

## 第二步：启动三个窗口

### 窗口 1：Leader (Claude Opus 4.6)

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
ccr leader    # 加载 leader preset 的配置到 config.json
ccr code      # 启动 Claude Code
```

或者如果 `ccr <preset>` 直接启动不了，先手动切配置再启动：

```bash
# 把 leader preset 的 config 复制为当前配置
cp ~/.claude-code-router/presets/leader/manifest.json ~/.claude-code-router/config.json
# 然后需要从 manifest 里提取 config 字段，或者直接把下面这个写成 config.json：
```

**Leader 的 `~/.claude-code-router/config.json`：**

```json
{
  "APIKEY": "<你的Anthropic中转key>",
  "Providers": [
    {
      "name": "claude-relay",
      "api_base_url": "<你的中转站地址>/v1/messages",
      "api_key": "<你的Anthropic中转key>",
      "models": ["claude-opus-4-6-20250514"]
    }
  ],
  "Router": {
    "default": "claude-relay,claude-opus-4-6-20250514"
  }
}
```

```bash
ccr restart   # 重启 router 服务加载新配置
ccr code      # 启动
```

### 窗口 2：Executor (DeepSeek V4 Pro)

把 `config.json` 换成 Executor 版本再启动：

```json
{
  "APIKEY": "<你的DeepSeek官方key>",
  "Providers": [
    {
      "name": "deepseek",
      "api_base_url": "https://api.deepseek.com/chat/completions",
      "api_key": "<你的DeepSeek官方key>",
      "models": ["deepseek-chat"],
      "transformer": {
        "use": ["deepseek"],
        "deepseek-chat": {
          "use": ["tooluse"]
        }
      }
    }
  ],
  "Router": {
    "default": "deepseek,deepseek-chat"
  }
}
```

```bash
ccr restart
ccr code
```

**⚠️ 问题：ccr 全局只有一个 config.json，两个窗口不能同时跑不同模型。**

### 解决办法：用 `ccr activate` 环境变量隔离

```bash
# 窗口 1 - Leader:
# 先把 config.json 设为 leader 配置，启动 router
ccr start   # router 跑在 :3456

# 在这个终端里用 ccr code 启动 Leader
ccr code

# -------

# 窗口 2 - Executor:
# 不走 ccr router，直接设环境变量让 claude 连 DeepSeek
export ANTHROPIC_BASE_URL="https://api.deepseek.com"
export ANTHROPIC_AUTH_TOKEN="<你的DeepSeek官方key>"
export ANTHROPIC_MODEL="deepseek-chat"
claude    # 直接启动原生 claude code，走 DeepSeek
```

### 窗口 3：Reviewer (GPT-5.5)

```bash
cd /root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition
codex
```

已配好，直接用。

---

## 最简方案（推荐）

如果 preset 切换太麻烦，**最简单的做法**：

```bash
# 窗口 1 - Leader (走 ccr router → Claude Opus)
# config.json 配成你的 Anthropic 中转
ccr code

# 窗口 2 - Executor (直连 DeepSeek，不走 router)
ANTHROPIC_BASE_URL="https://api.deepseek.com" \
ANTHROPIC_AUTH_TOKEN="<你的DeepSeek官方key>" \
ANTHROPIC_MODEL="deepseek-chat" \
claude

# 窗口 3 - Reviewer
codex
```

这样 router 只给 Leader 用，Executor 通过环境变量直连 DeepSeek，互不干扰。

---

## 配好后验证

三个窗口各发一句话测试：

- **Leader 窗口**：`你是什么模型？` → 应该回答 Claude Opus
- **Executor 窗口**：`你是什么模型？` → 应该回答 DeepSeek
- **Reviewer 窗口**：`你是什么模型？` → 应该回答 GPT-5.5

全部通过后告诉我。
