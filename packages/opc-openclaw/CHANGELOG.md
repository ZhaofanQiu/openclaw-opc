# opc-openclaw 变更日志

所有 opc-openclaw 模块的变更记录。

## [0.4.0] - 2026-03-24

### 新增

- 初始化模块
- HTTP 客户端封装（httpx）
- Agent 生命周期管理
- Agent 消息交互
- opc-bridge Skill 定义

### 客户端

- BaseClient: 基础 HTTP 客户端
- AgentClient: Agent API 客户端
- SessionClient: 会话 API 客户端

### Agent 管理

- AgentManager: 高层管理接口
- AgentLifecycle: 生命周期管理
- AgentBinding: 绑定验证

### 交互

- Messenger: 消息发送器
- MessageResponse: 响应模型

### Skill

- opc-bridge v2.0.0 定义
- 支持 opc_get_current_task
- 支持 opc_report_task_result
- 支持 opc_read_manual
- 支持 opc_get_budget
