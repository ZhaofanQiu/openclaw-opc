# opc-openclaw

OpenClaw OPC - OpenClaw Integration Module

**版本**: v0.4.0

## 职责

OpenClaw 生态对接层，封装 OpenClaw API，管理 Agent 生命周期和交互。

## 技术栈

- Python 3.12
- httpx (异步HTTP客户端)
- pydantic v2
- asyncio

## 安装

```bash
cd packages/opc-openclaw
pip install -e ".[dev]"
```

## 快速开始

```python
from opc_openclaw.agent import AgentManager
from opc_openclaw.interaction import Messenger

# Agent生命周期管理
manager = AgentManager(config)
agent = await manager.create_agent(name="员工A")

# 消息交互
messenger = Messenger(config)
await messenger.send(agent.id, "任务内容")
response = await messenger.wait_for_response(agent.id)
```

## 模块结构

```
src/opc_openclaw/
├── client/        # HTTP客户端
├── agent/         # Agent生命周期管理
├── interaction/   # 消息交互
└── skill/         # Skill管理
```

## 文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 架构设计
- [API.md](./API.md) - 对外接口文档

## 测试

```bash
pytest tests/
```

使用 Mock 测试，不依赖真实的 OpenClaw 服务。

## 变更日志

见 [CHANGELOG.md](./CHANGELOG.md)
