# opc-openclaw API 文档

**版本**: v0.4.1

## 概述

opc-openclaw 提供 CLI 方式与 OpenClaw 交互的能力。

## 核心导入

```python
from opc_openclaw import (
    # Agent 管理
    AgentManager,
    ConfigManager,
    AgentConfig,
    
    # 消息交互
    CLIMessenger,
    MessageType,
    TaskCaller,
    TaskAssignment,
    TaskResponse,
    
    # Skill 管理
    SkillInstaller,
    get_skill_definition,
    get_skill_yaml,
)
```

---

## AgentManager

Agent 管理器，提供高层 Agent 管理能力。

### 构造函数

```python
manager = AgentManager(agent_client=None, openclaw_bin=None)
```

参数:
- `agent_client`: CLIAgentClient 实例（可选）
- `openclaw_bin`: OpenClaw CLI 路径（可选，默认从环境变量读取）

### 方法

#### `list_agents() -> List[AgentInfo]`

列出所有可用 Agent（只返回 `opc-` 开头的）。

```python
agents = await manager.list_agents()
for agent in agents:
    print(f"{agent.name} ({agent.id}): {agent.status}")
```

#### `get_agent(agent_id: str) -> Optional[AgentInfo]`

获取 Agent 详情（只接受 `opc-` 开头的 ID）。

```python
agent = await manager.get_agent("opc-worker-1")
if agent:
    print(f"模型: {agent.model}")
```

#### `is_available(agent_id: str) -> bool`

检查 Agent 是否可用。

```python
if await manager.is_available("opc-worker-1"):
    print("Agent 可用")
```

---

## ConfigManager

Config 管理器，读写 `~/.openclaw/config` 文件。

### 构造函数

```python
config = ConfigManager(config_path=None)
```

参数:
- `config_path`: 配置文件路径（可选，默认 `~/.openclaw/config`）

### 方法

#### `read_agents() -> List[AgentConfig]`

读取所有 Agent 配置（只返回 `opc-` 开头的）。

```python
agents = config.read_agents()
for agent in agents:
    print(f"{agent.id}: {agent.model}")
```

#### `validate_agent_id(agent_id: str) -> Tuple[bool, str]`

验证 Agent ID 命名规范。

```python
is_valid, error = config.validate_agent_id("opc-worker-1")
if not is_valid:
    print(f"错误: {error}")
```

规范:
- 必须以 `opc-` 开头
- 不能是 `main` 或 `default`
- 只能包含字母、数字、下划线、连字符

#### `add_agent(agent_id, model, name=None, description="", **kwargs) -> Tuple[bool, str]`

添加新 Agent。

```python
success, msg = config.add_agent(
    agent_id="opc-worker-1",
    model="kimi-coding/k2p5",
    name="Worker One",
    description="Code review specialist"
)
# 返回: (True, "Agent added. You need to restart Gateway...")
```

#### `remove_agent(agent_id: str) -> Tuple[bool, str]`

移除 Agent。

```python
success, msg = config.remove_agent("opc-worker-1")
```

#### `request_restart_gateway(force=False) -> Tuple[bool, str]`

请求重启 OpenClaw Gateway。

```python
# 第一次调用需要确认
success, msg = await config.request_restart_gateway(force=False)
# 返回: (False, "RESTART_CONFIRMATION_REQUIRED...")

# 确认后重启
success, msg = await config.request_restart_gateway(force=True)
# 返回: (True, "Gateway restarted successfully")
```

⚠️ **警告**: 重启会中断所有正在进行的对话！

---

## CLIMessenger

CLI 消息发送器，通过 `openclaw` CLI 发送消息。

### 构造函数

```python
messenger = CLIMessenger(openclaw_bin=None)
```

### 方法

#### `send(agent_id, message, message_type=MessageType.TASK, timeout=900) -> MessageResponse`

发送消息给 Agent。

```python
response = await messenger.send(
    agent_id="opc-worker-1",
    message="请完成这个任务",
    message_type=MessageType.TASK,
    timeout=900  # 15 分钟
)

if response.success:
    print(f"回复: {response.content}")
    print(f"Token: {response.total_tokens}")
else:
    print(f"错误: {response.error}")
```

CLI 命令:
```bash
openclaw agent --agent opc-worker-1 --message "..." --json --timeout 900
```

---

## TaskCaller

任务调用器，封装任务分配流程。

### 构造函数

```python
caller = TaskCaller(messenger=None)
```

### 方法

#### `assign_task(task: TaskAssignment) -> TaskResponse`

分配任务给 Agent。

```python
from opc_openclaw import TaskAssignment

task = TaskAssignment(
    task_id="task-001",
    title="Code Review",
    description="Review authentication module",
    agent_id="opc-worker-1",
    agent_name="Worker One",
    employee_id="emp-001",
    company_manual_path="/abs/path/to/company.md",
    employee_manual_path="/abs/path/to/employee.md",
    task_manual_path="/abs/path/to/task.md",
    timeout=900,  # 15 分钟
)

result = await caller.assign_task(task)

if result.success:
    print(f"Agent 响应: {result.content}")
    print(f"Token 消耗: {result.total_tokens}")
```

任务消息格式:
```
# 任务分配: {title}

你是 {agent_name}，是 OpenClaw OPC 的一名员工。

## 📚 执行前必须阅读以下手册（使用绝对路径）
1. 公司手册: {company_manual_absolute_path}
2. 员工手册: {employee_manual_absolute_path}
3. 任务手册: {task_manual_absolute_path}

## 📝 任务信息
- **任务ID**: {task_id}
- **标题**: {title}
- **描述**: {description}

## ⚠️ 关键要求
1. **先读手册，再执行任务**
2. **使用 opc-bridge skill 报告结果**：
   请使用 opc-bridge skill 的 opc_report_task(...)
3. **结果文件**: 将工作成果保存到文件，使用绝对路径
```

---

## SkillInstaller

Skill 安装器，安装 `opc-bridge` skill。

### 构造函数

```python
installer = SkillInstaller(skill_dir=None)
```

参数:
- `skill_dir`: 安装目录（可选，默认 `~/.openclaw/skills/opc-bridge/`）

### 方法

#### `install() -> Tuple[bool, str]`

安装 Skill。

```python
success, msg = installer.install()
# 安装到 ~/.openclaw/skills/opc-bridge/
# - SKILL.md
# - scripts/opc-report.py
# - scripts/opc-check-task.py
# - scripts/opc-get-budget.py
```

#### `uninstall() -> Tuple[bool, str]`

卸载 Skill。

```python
success, msg = installer.uninstall()
```

#### `is_installed() -> bool`

检查是否已安装。

```python
if installer.is_installed():
    print("Skill 已安装")
```

---

## 数据类型

### AgentInfo

| 属性 | 类型 | 说明 |
|------|------|------|
| id | str | Agent ID |
| name | str | 显示名称 |
| model | str | 模型名称 |
| status | str | 状态 |
| is_active | bool | 是否活跃 |

### AgentConfig

| 属性 | 类型 | 说明 |
|------|------|------|
| id | str | Agent ID |
| name | str | 显示名称 |
| model | str | 模型名称 |
| description | str | 描述 |
| config | dict | 额外配置 |

### MessageResponse

| 属性 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| content | str | 响应内容 |
| session_key | str | 会话标识 |
| tokens_input | int | 输入 Token |
| tokens_output | int | 输出 Token |
| error | str | 错误信息 |
| total_tokens | int | 总 Token (属性) |

### TaskAssignment

| 属性 | 类型 | 说明 |
|------|------|------|
| task_id | str | 任务 ID |
| title | str | 标题 |
| description | str | 描述 |
| agent_id | str | Agent ID (opc-开头) |
| agent_name | str | Agent 名称 |
| employee_id | str | 员工 ID |
| company_manual_path | str | 公司手册绝对路径 |
| employee_manual_path | str | 员工手册绝对路径 |
| task_manual_path | str | 任务手册绝对路径 |
| timeout | int | 超时时间（默认 900 秒） |

### TaskResponse

| 属性 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| content | str | 响应内容 |
| session_key | str | 会话标识 |
| tokens_input | int | 输入 Token |
| tokens_output | int | 输出 Token |
| error | str | 错误信息 |
| total_tokens | int | 总 Token (属性) |

### MessageType

枚举值:
- `TASK` - 任务分配
- `WAKEUP` - 唤醒
- `NOTIFICATION` - 通知

---

## Skill 定义

### `get_skill_definition() -> str`

获取 opc-bridge Skill 完整定义文本。

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
```

---

## 错误处理

所有方法都通过返回值指示错误:

```python
# ConfigManager 返回 (success, message)
success, msg = config.add_agent("opc-worker-1", "kimi-coding/k2p5")
if not success:
    print(f"错误: {msg}")

# Messenger 返回 MessageResponse
response = await messenger.send("opc-worker-1", "消息")
if not response.success:
    print(f"错误: {response.error}")
```

常见错误:
- `OpenClaw CLI not found: ...` - CLI 未安装
- `Agent ID must start with "opc-"` - 命名规范错误
- `Timeout after ...` - 超时
- `Agent not found` - Agent 不存在