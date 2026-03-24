# opc-openclaw API 文档

**版本**: v0.4.0

## 模块导入

```python
from opc_openclaw import (
    AgentManager,
    Messenger,
    MessageType,
    get_skill_definition,
)
from opc_openclaw.client import AgentClient, SessionClient
```

## AgentManager

### 构造函数

```python
manager = AgentManager(client=None, **kwargs)
```

参数:
- `client`: AgentClient 实例（可选）
- `**kwargs`: 传递给 AgentClient 的参数

### 方法

#### `list_agents() -> List[AgentInfo]`

列出所有可用 Agent。

```python
agents = await manager.list_agents()
for agent in agents:
    print(f"{agent.name} ({agent.id}): {agent.status}")
```

#### `get_agent(agent_id: str) -> Optional[AgentInfo]`

获取 Agent 详情。

```python
agent = await manager.get_agent("agent_1")
if agent:
    print(f"模型: {agent.model}")
```

#### `is_available(agent_id: str) -> bool`

检查 Agent 是否可用。

```python
if await manager.is_available("agent_1"):
    print("Agent 可用")
```

## Messenger

### 构造函数

```python
messenger = Messenger(client=None, **kwargs)
```

### 方法

#### `send(agent_id, message, message_type=MessageType.TASK, timeout=300, label=None) -> MessageResponse`

发送消息给 Agent。

```python
response = await messenger.send(
    agent_id="agent_1",
    message="请完成这个任务",
    timeout=300
)

if response.success:
    print(f"回复: {response.content}")
    print(f"Token: {response.total_tokens}")
```

## MessageResponse

| 属性 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| content | str | 响应内容 |
| session_key | str | 会话标识 |
| tokens_input | int | 输入Token数 |
| tokens_output | int | 输出Token数 |
| error | str | 错误信息 |

属性:
- `total_tokens`: 总 Token 消耗 (input + output)

## AgentBinding

### `validate_binding(agent_id, employee_id) -> BindingResult`

验证绑定是否可行。

```python
from opc_openclaw import AgentBinding

binding = AgentBinding(client)
result = await binding.validate_binding("agent_1", "emp_1")

if result.is_bound:
    print("绑定有效")
else:
    print(f"错误: {result.error}")
```

## Skill 定义

### `get_skill_definition() -> str`

获取 opc-bridge Skill 完整定义。

```python
from opc_openclaw import get_skill_definition

definition = get_skill_definition()
print(definition)
```

### `get_skill_yaml() -> str`

获取 Skill YAML 配置。

```python
from opc_openclaw import get_skill_yaml

yaml = get_skill_yaml()
# 保存到文件安装
```

## 客户端（底层）

### AgentClient

```python
from opc_openclaw.client import AgentClient

client = AgentClient()

# 列出 Agent
agents = await client.list_agents()

# 获取详情
agent = await client.get_agent("agent_1")

# 检查健康
is_healthy = await client.check_agent_health("agent_1")
```

### SessionClient

```python
from opc_openclaw.client import SessionClient

client = SessionClient()

# 创建会话
result = await client.spawn_session(
    agent_id="agent_1",
    message="任务内容",
    timeout=300
)

session_key = result["session_key"]

# 发送后续消息
response = await client.send_message(
    session_key=session_key,
    message="补充信息"
)
```

## 错误处理

```python
from opc_openclaw.client import OpenClawAPIError

try:
    response = await messenger.send("agent_1", "消息")
except OpenClawAPIError as e:
    print(f"API错误 ({e.status_code}): {e}")
```
