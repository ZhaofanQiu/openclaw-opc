# opc-openclaw 变更日志

所有 opc-openclaw 模块的变更记录。

## [0.4.1] - 2026-03-25

### ResponseParser

- **OPC-REPORT 解析器**
  - 解析 Agent 回复中的结构化数据
  - 支持格式：
    ```
    ---OPC-REPORT---
    task_id: xxx
    status: completed|failed|needs_revision
    tokens_used: 800
    summary: 任务总结
    result_files: /path/to/file1.md,/path/to/file2.md
    ---END-REPORT---
    ```
  - 返回 ParsedReport 对象
    - is_valid: 是否解析成功
    - status: 任务状态
    - tokens_used: Token 消耗
    - summary: 执行摘要
    - result_files: 结果文件列表
    - errors: 解析错误信息

### TaskCaller

- 封装 Agent 调用逻辑
- 构建任务分配消息 (TaskAssignment)
- 处理 Agent 响应
- 集成 ResponseParser

### Skill 更新

- opc-bridge v0.4.1
- 支持 OPC-REPORT 格式
- 引导 Agent 生成结构化报告

---

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
