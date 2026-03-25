# opc-openclaw

OpenClaw OPC - OpenClaw Integration Module

**版本**: v0.4.1

## 职责

OpenClaw 生态对接层，封装 OpenClaw CLI，管理 Agent 生命周期和交互。

## 核心特性

- ✅ **CLI 方式通信** - 通过 `openclaw` CLI 命令与 Agent 交互
- ✅ **Config 文件管理** - 读写 `~/.openclaw/config` 管理 Agent 配置
- ✅ **Agent 命名规范** - 只处理 `opc-` 前缀的 Agent（如 `opc-worker-1`）
- ✅ **Skill 安装器** - 自动安装 `opc-bridge` skill 到 OpenClaw
- ✅ **任务调用封装** - 构建完整的任务分配消息

## 技术栈

- Python 3.10+
- PyYAML
- asyncio
- subprocess (CLI 调用)

## 安装

```bash
cd packages/opc-openclaw
pip install -e ".[dev]"
```

## 快速开始

### 1. Agent 管理

```python
from opc_openclaw import AgentManager, ConfigManager

# 从 OpenClaw 配置读取 Agent
manager = AgentManager()
agents = await manager.list_agents()  # 只返回 opc- 开头的 Agent

# 添加新 Agent
config = ConfigManager()
success, msg = config.add_agent(
    agent_id="opc-worker-1",
    model="kimi-coding/k2p5",
    name="Worker One"
)
```

### 2. 消息交互

```python
from opc_openclaw import CLIMessenger

messenger = CLIMessenger()
response = await messenger.send(
    agent_id="opc-worker-1",
    message="请完成代码审查任务",
    timeout=900  # 15 分钟
)

if response.success:
    print(f"回复: {response.content}")
    print(f"Token: {response.total_tokens}")
```

### 3. 任务分配

```python
from opc_openclaw import TaskCaller, TaskAssignment

caller = TaskCaller()
result = await caller.assign_task(TaskAssignment(
    task_id="task-001",
    title="Code Review",
    description="Review auth module",
    agent_id="opc-worker-1",
    agent_name="Worker One",
    employee_id="emp-001",
    company_manual_path="/path/to/company.md",
    employee_manual_path="/path/to/employee.md",
    task_manual_path="/path/to/task.md",
    timeout=900,
))
```

### 4. Skill 安装

```python
from opc_openclaw import SkillInstaller

installer = SkillInstaller()
success, msg = installer.install()  # 安装到 ~/.openclaw/skills/opc-bridge/
```

## 模块结构

```
src/opc_openclaw/
├── client/        # CLI 客户端
│   └── agents.py  # CLIAgentClient
├── agent/         # Agent 生命周期管理
│   ├── manager.py # AgentManager
│   └── lifecycle.py # AgentLifecycle (opc- 命名规范)
├── config/        # Config 管理 (新增)
│   └── manager.py # ConfigManager
├── interaction/   # 消息交互
│   ├── messenger.py   # CLIMessenger
│   └── task_caller.py # TaskCaller
└── skill/         # Skill 管理
    ├── definition.py  # Skill 定义
    └── installer.py   # SkillInstaller (新增)
```

## 设计约束

1. **CLI 方式通信** - 所有交互通过 `openclaw` CLI 命令
2. **Agent 命名规范** - 只处理 `opc-` 开头的 Agent ID
3. **排除系统 Agent** - 过滤 `main` 和 `default`
4. **手册绝对路径** - 任务消息中使用绝对路径
5. **Gateway 重启确认** - 修改 config 后需要用户确认重启

## 文档

- [API.md](./API.md) - 对外接口文档
- [PLAN_v0.4.1_Phase2_OpenClaw.md](../../PLAN_v0.4.1_Phase2_OpenClaw.md) - 详细规划

## 测试

```bash
pytest tests/unit/ -v
```

98 个单元测试全部通过（2 个跳过，1 个警告）。

使用 Mock 测试，不依赖真实的 OpenClaw 服务。

## 变更日志

### v0.4.1 (2026-03-24)

**重大变更**: 从 HTTP API 改为 CLI 方式

#### 新增
- `CLIMessenger` - 通过 CLI 发送消息
- `CLIAgentClient` - 通过 CLI 管理 Agent
- `ConfigManager` - 读写 `~/.openclaw/config`
- `TaskCaller` - 任务分配封装
- `SkillInstaller` - 安装 `opc-bridge` skill

#### 移除
- `BaseClient` - HTTP 基础类
- `SessionClient` - HTTP Session 客户端
- `OpenClawAPIError` - HTTP 异常

#### 变更
- Agent ID 命名规范从 `opc_` 改为 `opc-`（连字符）
- 所有通信改为 CLI 方式

#### 测试
- 98 个单元测试
- 2 个跳过（需要 HTTP 服务）

### v0.4.1

- HTTP API 客户端实现
- Agent 生命周期管理
- Skill 定义