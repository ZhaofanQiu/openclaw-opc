# opc-openclaw 架构设计

**版本**: v0.4.0

## 概述

opc-openclaw 是 OpenClaw OPC 的 OpenClaw 集成模块，提供：

- OpenClaw API 客户端（HTTP）
- Agent 生命周期管理（发现、状态检查）
- Agent 消息交互
- opc-bridge Skill 定义

## 架构

```
opc_openclaw/
├── client/            # HTTP 客户端
│   ├── base.py        # 基础客户端
│   ├── sessions.py    # 会话 API
│   └── agents.py      # Agent API
├── agent/             # Agent 管理
│   ├── lifecycle.py   # 生命周期
│   ├── manager.py     # 管理器
│   └── binding.py     # 绑定管理
├── interaction/       # 交互层
│   └── messenger.py   # 消息发送
└── skill/             # Skill 定义
    └── definition.py  # Skill 定义文本
```

## 设计原则

### 1. 客户端分层

```
BaseClient (基础HTTP)
    ├── AgentClient (Agent API)
    └── SessionClient (会话 API)
```

### 2. 高层封装

```
AgentManager (高层管理)
    └── AgentLifecycle (生命周期)

Messenger (消息发送)
    └── SessionClient
```

## 核心组件

### BaseClient

- 异步 HTTP 客户端（httpx）
- 统一的错误处理
- 支持环境变量配置

### SessionClient

OpenClaw 会话管理：

- `spawn_session()`: 创建会话并发送消息
- `send_message()`: 向现有会话发送消息
- `get_session_status()`: 获取会话状态

### AgentManager

Agent 高层管理：

- `list_agents()`: 列出所有 Agent
- `get_agent()`: 获取 Agent 详情
- `is_available()`: 检查可用性

### Messenger

消息交互：

- `send()`: 发送消息给 Agent
- 自动解析 Token 消耗
- 支持同步/异步模式

## Skill 定义

`opc-bridge` Skill 定义安装在 OpenClaw 中，提供：

- `opc_get_current_task()`: 获取当前任务
- `opc_report_task_result()`: 报告任务结果
- `opc_read_manual()`: 读取手册
- `opc_get_budget()`: 查询预算

## 使用示例

### 发送消息

```python
from opc_openclaw import Messenger

async with Messenger() as messenger:
    response = await messenger.send(
        agent_id="agent_1",
        message="请完成这个任务",
        timeout=300
    )
    
    if response.success:
        print(f"Agent回复: {response.content}")
        print(f"Token消耗: {response.total_tokens}")
```

### Agent 管理

```python
from opc_openclaw import AgentManager

async with AgentManager() as manager:
    # 列出所有 Agent
    agents = await manager.list_agents()
    
    # 检查特定 Agent
    is_available = await manager.is_available("agent_1")
```

### 绑定验证

```python
from opc_openclaw import AgentBinding
from opc_openclaw.client import AgentClient

client = AgentClient()
binding = AgentBinding(client)

result = await binding.validate_binding(
    agent_id="agent_1",
    employee_id="emp_1"
)

if result.is_bound:
    print("绑定有效")
else:
    print(f"绑定失败: {result.error}")
```

## 配置

通过环境变量配置：

```bash
# OpenClaw API 地址
OPENCLAW_API_URL=http://localhost:8080

# API 密钥（如果需要）
OPENCLAW_API_KEY=your_api_key
```

## Mock 测试

模块提供 Mock 客户端用于测试：

```python
from tests.conftest import MockClient

mock = MockClient(responses={
    "GET:/api/agents": {"agents": [...]}
})
```
