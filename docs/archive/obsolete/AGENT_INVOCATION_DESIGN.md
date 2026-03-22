# OpenClaw Agent 调用机制设计文档

## 概述

本文档定义 OPC (OpenClaw Partner Company) 系统中 Agent 的调用机制，采用 **Skill + Message + 手册** 三重行为控制机制，确保 Agent 行为可控、可预测、可审计。

---

## 核心概念

### 三重行为控制

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent 行为控制层                          │
├─────────────────────────────────────────────────────────────┤
│  第一层: Skill (技能)                                        │
│  ├── 定义 Agent 能做什么                                     │
│  ├── 技能注册、发现、执行                                     │
│  └── 权限边界控制                                             │
├─────────────────────────────────────────────────────────────┤
│  第二层: Message (消息)                                      │
│  ├── 定义 Agent 何时做                                       │
│  ├── 异步消息队列                                             │
│  └── 会话状态管理                                             │
├─────────────────────────────────────────────────────────────┤
│  第三层: 手册 (Manual)                                       │
│  ├── 定义 Agent 怎么做                                       │
│  ├── 任务描述、约束条件                                       │
│  └── 输出格式规范                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 第一层: Skill (技能控制)

### 1.1 技能定义

技能是 Agent 可调用的能力单元，每个技能包含：

```python
class Skill:
    id: str              # 技能唯一标识
    name: str            # 技能名称
    description: str     # 技能描述
    parameters: dict     # 参数定义
    handler: Callable    # 执行函数
    permissions: list    # 所需权限
    cost_estimate: int   # 预估 Token 消耗
```

### 1.2 技能注册机制

```python
# Skill 注册示例
@skill_registry.register(
    name="file_operations",
    description="文件读写操作",
    permissions=["read", "write"]
)
def handle_file_operations(params):
    # 实现逻辑
    pass
```

### 1.3 Skill 调用流程

```
┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────┐
│  Agent   │───▶│ Skill Router │───▶│ 权限检查   │───▶│ 执行 Skill│
└──────────┘    └──────────────┘    └────────────┘    └──────────┘
                                              │
                                              ▼
                                        ┌────────────┐
                                        │ 结果返回   │
                                        └────────────┘
```

### 1.4 当前实现状态

| 功能 | 状态 | 说明 |
|------|------|------|
| Skill 模型 | ✅ | `models/skill.py` |
| Skill 服务 | ✅ | `services/skill_service.py` |
| 员工技能绑定 | ✅ | `agent_skills_table` |
| 技能成长 | ⚠️ | 基础框架，待完善 |
| Skill 执行 | ❌ | 未实现，当前直接调用 OpenClaw sessions_send |

---

## 第二层: Message (消息控制)

### 2.1 消息类型

```python
class AsyncMessageType(str, Enum):
    TASK_ASSIGNMENT = "task_assignment"      # 任务分配
    TASK_REMINDER = "task_reminder"          # 任务提醒
    SYSTEM_NOTICE = "system_notice"          # 系统通知
    URGENT_REQUEST = "urgent_request"        # 紧急请求
    HEADLINE_UPDATE = "headline_update"      # 头条更新
```

### 2.2 消息生命周期

```
创建(CREATED) → 发送(SENDING) → 已发送(SENT) → 已接收(RECEIVED)
                                                  ↓
                        失败(FAILED) ←──── 已回复(REPLIED) / 超时(EXPIRED)
```

### 2.3 消息调用 Agent 流程

```python
# 1. 创建消息
message = async_message_service.create_message(
    recipient_agent_id="agent_xxx",
    type=AsyncMessageType.TASK_ASSIGNMENT,
    content={"task_id": "xxx", "description": "..."}
)

# 2. 发送消息（异步）
async_message_service.send_message_to_agent(message.id)

# 3. Agent 接收并处理
# - 通过 sessions_send 调用 OpenClaw Agent
# - Agent 在独立 session 中执行

# 4. 接收回复
async_message_service.receive_response(
    message_id=message.id,
    response_data={...}
)
```

### 2.4 当前实现状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 消息模型 | ✅ | `models/async_message.py` |
| 消息服务 | ✅ | `services/async_message_service.py` |
| 消息轮询 | ✅ | 前端 5 秒轮询 |
| 超时处理 | ✅ | 30 分钟超时容忍 |
| WebSocket 实时 | ❌ | 待实现 |

---

## 第三层: 手册 (Manual 控制)

### 3.1 手册定义

手册是任务的完整行为规范，包含：

```python
class TaskManual:
    # 基础信息
    task_title: str
    task_description: str
    expected_output: str
    
    # 约束条件
    constraints: List[str]          # 必须遵守的规则
    forbidden_actions: List[str]    # 禁止的操作
    required_checks: List[str]      # 必须检查的事项
    
    # 输出规范
    output_format: str              # 输出格式 (markdown/json/...)
    output_sections: List[str]      # 必须包含的章节
    
    # 参考资源
    reference_files: List[str]      # 参考文件路径
    related_memories: List[str]     # 相关记忆
```

### 3.2 手册生成流程

```
用户输入 → 模板引擎 → 手册生成 → Agent 接收 → 按手册执行
```

### 3.3 手册模板示例

```markdown
# 任务手册: {{task_title}}

## 任务描述
{{task_description}}

## 预期输出
{{expected_output}}

## 约束条件
{{#each constraints}}
- {{this}}
{{/each}}

## 输出格式
请按照以下格式输出:

```json
{
  "summary": "任务摘要",
  "result": "执行结果",
  "files": ["生成的文件列表"],
  "notes": "备注"
}
```

## 检查清单
{{#each required_checks}}
- [ ] {{this}}
{{/each}}
```

### 3.4 当前实现状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 手册模型 | ⚠️ | 部分在 Task 模型中 |
| 手册生成 | ❌ | 未实现 |
| 模板引擎 | ❌ | 未实现 |
| 输出解析 | ⚠️ | 基础解析，待完善 |

---

## 完整调用流程

```
┌────────────────────────────────────────────────────────────────┐
│                         用户创建任务                            │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 1: 手册生成 (Manual Layer)                               │
│  ├── 收集任务信息                                              │
│  ├── 选择手册模板                                              │
│  ├── 生成完整手册                                              │
│  └── 存储到任务上下文                                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 2: Skill 检查 (Skill Layer)                              │
│  ├── 检查员工技能是否匹配                                       │
│  ├── 验证技能权限                                              │
│  └── 确定可调用的技能集                                         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 3: 消息封装 (Message Layer)                              │
│  ├── 创建异步消息                                              │
│  ├── 封装任务内容 + 手册                                        │
│  ├── 设置超时和优先级                                           │
│  └── 发送到消息队列                                             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 4: Agent 唤醒                                            │
│  ├── 检查 Agent 在线状态                                        │
│  ├── 通过 sessions_send 调用                                    │
│  ├── 传递完整上下文 (手册+约束)                                  │
│  └── Agent 在隔离 session 中执行                                │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  Step 5: 结果处理                                              │
│  ├── 接收 Agent 输出                                           │
│  ├── 解析输出格式                                              │
│  ├── 验证约束遵守情况                                           │
│  ├── 更新任务状态                                              │
│  └── 触发后续步骤或通知                                         │
└────────────────────────────────────────────────────────────────┘
```

---

## API 设计

### Agent 调用端点

```python
# 创建并发送任务消息
POST /api/async-messages/send
{
    "recipient_agent_id": "string",     # Agent ID
    "type": "task_assignment",          # 消息类型
    "title": "string",                  # 消息标题
    "content": {                        # 消息内容
        "task_id": "string",
        "manual": {                     # 完整手册
            "description": "string",
            "constraints": [...],
            "expected_output": "..."
        },
        "skills_available": [...]       # 可用技能列表
    },
    "priority": "normal",               # 优先级
    "timeout_minutes": 30               # 超时时间
}

# Agent 报告结果
POST /api/tasks/{task_id}/report
{
    "agent_id": "string",
    "status": "completed|failed",
    "result_summary": "string",
    "token_used": 0,
    "output_data": {...}                # 结构化输出
}
```

---

## 待实现功能

### P0 (必须)
- [ ] 手册模板引擎
- [ ] 手册生成服务
- [ ] 输出格式解析器
- [ ] Skill 执行框架

### P1 (重要)
- [ ] WebSocket 实时通知
- [ ] Agent 状态心跳
- [ ] 技能自动发现
- [ ] 手册版本管理

### P2 (优化)
- [ ] 手册智能推荐
- [ ] 约束自动验证
- [ ] 输出质量评分
- [ ] Agent 行为分析

---

## 附录

### A. 消息类型对照表

| 场景 | 消息类型 | 触发条件 |
|------|----------|----------|
| 任务分配 | TASK_ASSIGNMENT | 任务分配给 Agent |
| 任务提醒 | TASK_REMINDER | 任务即将超时 |
| 返工通知 | REWORK_REQUEST | 任务需要返工 |
| 紧急请求 | URGENT_REQUEST | 熔断事件 |
| 系统通知 | SYSTEM_NOTICE | 系统级事件 |

### B. Skill 分类

| 类别 | 示例 Skill | 说明 |
|------|------------|------|
| 文件操作 | file_read, file_write | 文件系统访问 |
| 代码执行 | code_run, test_execute | 代码执行环境 |
| 网络请求 | http_get, api_call | 外部 API 调用 |
| 数据处理 | json_parse, csv_process | 数据转换 |
| 记忆访问 | memory_read, memory_write | 知识库操作 |

---

*文档版本: v1.0*  
*更新日期: 2026-03-23*  
*状态: 设计阶段*
