# Context Memory Contract

> 本地化上下文记忆协议：解决跨会话遗忘问题。会话启动时自动加载，关键决策持久化。

## 问题背景

Labline 框架在长周期科研项目中存在"遗忘"问题：
- 会话断开后，之前讨论的设计决策、实验状态丢失
- 新会话重新问相同问题，浪费 token 和时间
- 无法区分"需要人决断"和"可自动继续"的事项

## 核心原则

**机器可读状态 + 人类可读日志 = 跨会话连续性**

- JSON 状态文件：机器加载，快速恢复上下文
- Markdown 进度日志：人类审阅，理解历史脉络
- 两者互补，不互相替代

## 状态文件

### 位置

```
项目根目录/CONTEXT_MEMORY.json
```

### Schema

```json
{
  "version": 1,
  "schema": "skills/shared-references/context-memory-contract.md",
  "session": {
    "id": "session-YYYYMMDD-HHMM",
    "started_at": "ISO8601",
    "focus": "当前会话焦点（一句话）"
  },
  "persistent_context": {
    "active_project": {
      "path": "项目路径",
      "name": "项目名",
      "research_direction": "研究方向"
    },
    "active_experiments": [
      {
        "id": "expXXX",
        "server": "服务器名",
        "status": "created|running|completed|failed",
        "path": "实验目录"
      }
    ],
    "framework_state": {
      "codex_migration": "pending|complete",
      "last_verified": "YYYY-MM-DD",
      "profiles": ["leader", "executor", "reviewer"],
      "skills_count": 94
    }
  },
  "working_memory": {
    "recent_decisions": [
      {
        "date": "YYYY-MM-DD",
        "decision": "决策内容",
        "rationale": "理由"
      }
    ],
    "pending_questions": [
      {
        "question": "待决问题",
        "requires_human": true|false,
        "context": "背景"
      }
    ],
    "blocked_items": [
      {
        "blocker": "阻塞项",
        "since": "YYYY-MM-DD",
        "attempted": ["尝试过的方案"]
      }
    ]
  },
  "retention_rules": {
    "keep_across_sessions": [
      "active_project",
      "active_experiments",
      "framework_state",
      "recent_decisions (last 7 days)"
    ],
    "clear_on_task_complete": [
      "working_memory.pending_questions",
      "working_memory.blocked_items"
    ],
    "archive_after_days": {
      "recent_decisions": 30,
      "completed_experiments": 90
    }
  },
  "last_updated": "ISO8601"
}
```

## 加载时机

### 会话启动时

1. 检查 `CONTEXT_MEMORY.json` 是否存在
2. 存在 → 读取 `persistent_context` 和 `working_memory`
3. 显示摘要：
```
📋 上下文恢复：
- 项目: labline-orangmood-edition (FSCIOD)
- 活跃实验: exp0603 (created)
- 框架状态: Codex 迁移完成
- 最近决策: Executor 角色拆分 (Jun 5)
- 待决问题: 0
- 阻塞项: 0
```

### 会话结束时

1. 更新 `last_updated`
2. 清理 `clear_on_task_complete` 中的已完成项
3. 写入新决策到 `recent_decisions`

## 分类规则

### 需要人决断（requires_human: true）

- 研究方向变更
- 实验优先级排序
- 止损/转向决策
- 预算/资源分配
- 论文投稿时机

### 可自动继续（requires_human: false）

- 代码实现细节
- 实验参数调优
- 文档格式整理
- 测试用例补充
- 依赖版本升级

## 与其他协议的关系

| 协议 | 职责 |
|------|------|
| `recovery-state-contract.md` | 长运行任务的断点续跑 |
| `executor-blocked-protocol.md` | Executor 遇阻塞的自救流程 |
| `context-memory-contract.md` | 跨会话的上下文连续性 |

三者互补：
- Recovery State → 任务级断点
- Blocked Protocol → 阻塞级自救
- Context Memory → 会话级连续

## 写入规则

- 原子写入（先写临时文件，再 rename）
- 决策追加，不覆盖历史
- `recent_decisions` 保留最近 7 天，超期归档到 `discussions/decision-log/`
- `pending_questions` 和 `blocked_items` 完成即删

## 归档策略

```
discussions/
├── decision-log/
│   ├── 2026-06.md      # 当月决策归档
│   └── 2026-05.md
└── session-summaries/
    └── 2026-06-07.md   # 当日会话摘要
```

归档触发：
- `recent_decisions` 超过 7 天
- 实验状态变为 `completed` 或 `failed`
- 会话显式结束（用户说"结束"或"再见"）

## Hook 集成

Codex `SessionStart` hook 自动加载：

```python
# ~/.codex/hooks/session_start.py
import json
from pathlib import Path

def load_context_memory():
    memory_path = Path.cwd() / "CONTEXT_MEMORY.json"
    if memory_path.exists():
        memory = json.loads(memory_path.read_text())
        print(f"📋 上下文恢复：{memory['persistent_context']['active_project']['name']}")
        # ... 显示摘要
```

## 反模式

- ❌ 把完整对话历史塞进 JSON
- ❌ 用记忆替代 MANIFEST.md 的工件追踪
- ❌ 在 `pending_questions` 模糊描述（"看看那个问题"）
- ❌ 不区分 requires_human，全标记为需要人决断
