# OpenClaw 集成技术方案 (确认版)

## 关键发现

从 OpenClaw 文档中确认：

1. **没有直接拦截钩子** - OpenClaw 不提供 Agent 调用拦截机制
2. **有 Session 查询工具** - `sessions_list`, `session_status` 可以获取 token 使用情况
3. **有跨 Session 通信** - `sessions_send` 可以让 Agent 发送消息给其他 session

## 可行方案：Partner Agent 模式

```
┌─────────────────────────────────────────────────────────────┐
│                    Core Service (FastAPI)                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API: /api/agents/report                            │   │
│  │  API: /api/tasks/complete                           │   │
│  │  API: /api/budget/consume                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ HTTP POST
                           │
┌─────────────────────────────────────────────────────────────┐
│                 OpenClaw Gateway                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Partner    │  │  Employee   │  │  Employee   │         │
│  │  Agent      │  │  Agent 1    │  │  Agent 2    │         │
│  │             │  │             │  │             │         │
│  │ 1.监控所有   │  │ 1.执行任务  │  │ 1.执行任务  │         │
│  │   session   │  │ 2.上报状态  │  │ 2.上报状态  │         │
│  │ 2.汇总上报   │  │    (skill)  │  │    (skill)  │         │
│  │   Core      │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 实现机制

### 1. OPC Skill (安装在每个 Agent)

位置: `~/.openclaw/skills/opc-bridge/SKILL.md`

```yaml
---
name: opc-bridge
description: Connect to OpenClaw OPC for budget tracking
---

# OPC Bridge

Report task completion and token usage to OPC Core Service.

## When to use

- After completing a task
- When budget warning is triggered
- To check current task assignment

## Usage

```javascript
// 任务完成后上报
opc_report({
  task_id: "task_xxx",
  token_used: 450,
  result_summary: "完成了登录页重构"
});

// 查询当前任务
opc_check_task();
```
```

### 2. Partner Agent 配置

在 `openclaw.json` 中配置 Partner Agent：

```json5
{
  agents: {
    list: [
      {
        id: "opc-partner",
        name: "Kimi Partner",
        workspace: "~/.openclaw/workspace-opc-partner",
        // Partner 拥有协调权限
        tools: {
          allow: ["group:sessions", "group:fs", "exec"]
        },
        // 定期任务：监控其他 Agent
        cron: [
          {
            name: "opc-monitor",
            schedule: { kind: "every", everyMs: 30000 },  // 30秒
            payload: {
              kind: "agentTurn",
              message: "检查所有员工 Agent 的状态，如果有新任务分配给它们，或者它们的预算即将耗尽，请上报给 OPC Core Service"
            }
          }
        ]
      },
      {
        id: "employee-1",
        name: "前端阿强",
        workspace: "~/.openclaw/workspace-employee-1",
        tools: {
          allow: ["group:fs", "opc-bridge"]  // 只能使用 bridge skill
        }
      }
    ]
  }
}
```

### 3. Core Service API

```python
# FastAPI endpoints

@app.post("/api/agents/report")
async def agent_report(
    agent_id: str,
    task_id: str,
    token_used: int,
    result_summary: str
):
    """接收 Agent 任务完成上报"""
    # 1. 更新任务状态
    # 2. 扣减预算
    # 3. 检查熔断
    pass

@app.get("/api/agents/{agent_id}/task")
async def get_agent_task(agent_id: str):
    """查询 Agent 当前任务"""
    # 返回分配给该 Agent 的待办任务
    pass

@app.post("/api/agents/{agent_id}/assign")
async def assign_task(agent_id: str, task: Task):
    """分配任务给 Agent"""
    # 1. 保存任务
    # 2. 通知 Partner Agent
    pass
```

### 4. 数据流

**任务分配流程：**
```
1. 用户在 UI 创建任务
   ↓ POST /api/tasks
2. Core Service 保存任务
   ↓ POST /api/agents/{id}/assign
3. Partner Agent 接收通知 (通过 sessions_send)
   ↓
4. Partner Agent 在适当时机通知 Employee Agent
   ↓ sessions_send
5. Employee Agent 开始工作
   ↓ 使用 bridge skill 上报进度
6. Core Service 更新预算
```

**预算追踪流程：**
```
1. Employee Agent 完成工作
   ↓ 调用 opc_report()
2. Skill 发送 HTTP POST 到 Core
   ↓
3. Core 更新预算余额
   ↓ 检查是否触发熔断
4. 如果熔断，Core 通知 Partner
   ↓
5. Partner 协调处理 (暂停/拆分/换人等)
```

## 方案优势

| 优势 | 说明 |
|------|------|
| **无需修改 OpenClaw** | 完全使用公开接口 |
| **松耦合** | Core Service 和 OpenClaw 独立运行 |
| **可扩展** | 新增 Agent 只需配置和安装 Skill |
| **安全** | 通过 tools.allow 控制 Agent 权限 |

## 技术风险与缓解

| 风险 | 缓解方案 |
|------|---------|
| Agent 不上报 | Partner Agent 定期轮询检查 |
| 上报延迟 | 异步处理，允许 5-10 秒延迟 |
| Token 统计不准确 | 使用 session_status 工具精确获取 |
| Partner Agent 故障 | UI 显示离线状态，允许手动接管 |

## Week 1 验证计划

**Day 1-2: 基础搭建**
- [ ] 创建 Core Service FastAPI 骨架
- [ ] 创建 OPC Bridge Skill 骨架
- [ ] 验证 HTTP 通信

**Day 3-4: Agent 集成**
- [ ] 配置 Partner Agent
- [ ] 配置 Employee Agent
- [ ] 验证 sessions_send 跨 Agent 通信

**Day 5-7: 完整流程**
- [ ] 任务创建 → 分配 → 执行 → 上报 完整流程
- [ ] 预算扣减验证
- [ ] 熔断机制验证

---

*Technical validation based on OpenClaw documentation*
