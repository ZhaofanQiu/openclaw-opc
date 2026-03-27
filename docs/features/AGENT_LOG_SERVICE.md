# Agent Log Service - 交互日志服务

**版本**: v0.4.5  
**模块**: `opc_core.services.agent_log_service`  
**作者**: OpenClaw OPC Team

---

## 概述

Agent Log Service 是 OpenClaw OPC 的 Agent 交互日志系统，用于记录和管理与 OpenClaw Agent 的所有交互记录。支持日志记录、查询、统计和清空功能。

## 核心特性

- ✅ 记录发送给 Agent 的消息 (outgoing)
- ✅ 记录 Agent 的回复 (incoming)
- ✅ 支持按 Agent ID、任务 ID、交互类型筛选
- ✅ 内存缓存机制（最近 100 条）
- ✅ 完整的统计信息（成功率、token 消耗等）
- ✅ SQLite 并发写入优化（asyncio.Lock）

---

## 数据模型

### AgentLog

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 日志唯一标识 |
| agent_id | str | Agent ID |
| agent_name | str | Agent 名称 |
| interaction_type | str | 交互类型 (message/task_assignment/...) |
| direction | str | 方向 (outgoing/incoming) |
| content | str | 发送内容（限制 10000 字符） |
| response | str | 回复内容（限制 10000 字符） |
| task_id | str | 关联任务 ID |
| meta_info | dict | 元数据（成功率、token 数、耗时等） |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

---

## API 方法

### log_outgoing

记录发送给 Agent 的消息。

```python
@classmethod
async def log_outgoing(
    cls,
    agent_id: str,
    agent_name: Optional[str] = None,
    interaction_type: str = "message",
    content: str = "",
    task_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> str
```

**参数**:
- `agent_id`: Agent ID
- `agent_name`: Agent 名称（可选，默认使用 agent_id）
- `interaction_type`: 交互类型，默认 "message"
- `content`: 发送的内容（自动截断至 10000 字符）
- `task_id`: 关联任务 ID（可选）
- `metadata`: 额外元数据（可选）

**返回**: 日志 ID（用于后续关联 incoming 记录）

**示例**:
```python
log_id = await AgentLogService.log_outgoing(
    agent_id="opc_partner",
    agent_name="实习生小王",
    interaction_type="task_assignment",
    content="请完成以下任务...",
    task_id="task_xxx",
    metadata={"priority": "high"}
)
```

---

### log_incoming

记录从 Agent 接收的回复。

```python
@classmethod
async def log_incoming(
    cls,
    log_id: str,
    response: str = "",
    success: bool = True,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    tokens_input: int = 0,
    tokens_output: int = 0
)
```

**参数**:
- `log_id`: 对应的 outgoing 日志 ID
- `response`: Agent 回复内容
- `success`: 是否成功
- `error_message`: 错误信息（如果有）
- `duration_ms`: 耗时（毫秒）
- `tokens_input`: 输入 token 数
- `tokens_output`: 输出 token 数

**示例**:
```python
await AgentLogService.log_incoming(
    log_id=log_id,
    response="任务已完成...",
    success=True,
    duration_ms=5000,
    tokens_input=100,
    tokens_output=200
)
```

---

### get_logs

查询日志列表（支持分页和筛选）。

```python
@classmethod
async def get_logs(
    cls,
    agent_id: Optional[str] = None,
    interaction_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]
```

**返回**:
```python
{
    "logs": [...],      # 日志列表
    "total": 100,       # 总数
    "limit": 50,        # 每页数量
    "offset": 0         # 偏移量
}
```

---

### get_stats

获取交互统计信息。

```python
@classmethod
async def get_stats(
    cls,
    agent_id: Optional[str] = None,
    days: int = 7
) -> Dict[str, Any]
```

**返回**:
```python
{
    "total_interactions": 100,    # 总交互次数
    "success_rate": 0.95,         # 成功率
    "avg_duration_ms": 5000,      # 平均耗时
    "total_tokens_input": 10000,  # 总输入 token
    "total_tokens_output": 20000, # 总输出 token
    "by_type": {...},             # 按类型统计
    "by_day": {...}               # 按天统计
}
```

---

### get_log_by_id

获取单条日志详情。

```python
@classmethod
async def get_log_by_id(cls, log_id: str) -> Optional[Dict[str, Any]]
```

---

### clear_logs

清空指定 Agent 的日志。

```python
@classmethod
async def clear_logs(agent_id: Optional[str] = None) -> int
```

**返回**: 删除的日志数量

---

## HTTP API 端点

### GET /api/v1/agent-logs

查询日志列表。

**查询参数**:
- `agent_id`: 按 Agent ID 筛选
- `interaction_type`: 按交互类型筛选
- `limit`: 每页数量（默认 50）
- `offset`: 偏移量（默认 0）

**响应**:
```json
{
  "logs": [...],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

---

### GET /api/v1/agent-logs/stats

获取统计信息。

**查询参数**:
- `agent_id`: 指定 Agent（可选）
- `days`: 统计天数（默认 7）

**响应**:
```json
{
  "total_interactions": 100,
  "success_rate": 0.95,
  "avg_duration_ms": 5000,
  "total_tokens_input": 10000,
  "total_tokens_output": 20000,
  "by_type": {...},
  "by_day": {...}
}
```

---

### GET /api/v1/agent-logs/{log_id}

获取单条日志详情。

---

### DELETE /api/v1/agent-logs

清空日志。

**查询参数**:
- `agent_id`: 指定 Agent（可选，不指定则清空所有）

**响应**:
```json
{
  "cleared_count": 10
}
```

---

## 并发优化

### 问题
SQLite 数据库不支持并发写入，多个后台任务同时写入日志时会出现 `database is locked` 错误。

### 解决方案

#### Phase 1: 写入锁
在 `AgentLogService` 中添加 `asyncio.Lock`：

```python
class AgentLogService:
    _write_lock = asyncio.Lock()
    
    @classmethod
    async def log_outgoing(cls, ...):
        async with cls._write_lock:  # 串行化写入
            async with get_session() as session:
                # 写入操作
```

#### Phase 2: 事务优化
优化后台任务，缩短数据库连接持有时间：

```python
# Step 1: 获取任务信息（短事务）
async with get_session() as session:
    # 读取任务信息
    await session.commit()  # 立即提交

# Step 2: 调用 Agent（不持有数据库锁）
response = await task_caller.assign_task(assignment)

# Step 3: 更新结果（短事务）
async with get_session() as session:
    # 更新任务状态
    await session.commit()  # 立即提交
```

---

## 使用示例

### 在 Task Service 中记录日志

```python
from opc_core.services import AgentLogService

class TaskService:
    async def assign_task(self, ...):
        # 记录 outgoing
        log_id = await AgentLogService.log_outgoing(
            agent_id=employee.agent_id,
            agent_name=employee.name,
            interaction_type="task_assignment",
            content=assignment.to_prompt(),
            task_id=task.id
        )
        
        # 调用 Agent
        response = await self.task_caller.assign_task(assignment)
        
        # 记录 incoming
        await AgentLogService.log_incoming(
            log_id=log_id,
            response=response.content,
            success=response.success,
            duration_ms=response.duration_ms,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output
        )
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.4.5 | 2026-03-27 | 初始版本，添加完整日志功能 |
| v0.4.5 | 2026-03-27 | 添加 SQLite 并发写入优化 |
