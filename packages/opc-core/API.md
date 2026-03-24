# OPC Core API 文档 (v0.4.1)

**版本**: 0.4.1  
**更新日期**: 2026-03-25  
**状态**: Phase 3 完成

---

## 架构变更说明

### v0.4.1 重大变更

从 v0.4.0 的异步回调模式改为 **同步返回模式**:

| 特性 | v0.4.0 | v0.4.1 |
|------|--------|--------|
| 任务分配 | 异步，等待 HTTP 回调 | **同步，立即返回结果** |
| 结果获取 | 通过 Skill API 回调 | **通过 ResponseParser 解析** |
| 任务状态 | PENDING → RUNNING → 回调更新 | **PENDING → RUNNING → 同步更新** |
| Skill API | 主要通信方式 | **已废弃** |

### 新的数据流

```
Dashboard → POST /tasks/{id}/assign → TaskService.assign_task()
                                              │
                                              ▼
                                       TaskCaller.assign_task()
                                              │
                                              ▼ (CLI)
                                       OpenClaw Agent
                                              │
                                              ▼ (Reply)
                                       ResponseParser.parse()
                                              │
                                              ▼
                                       同步返回任务结果
```

---

## 任务管理 API

### 分配任务 (新架构)

```http
POST /api/v1/tasks/{task_id}/assign
```

分配任务给员工并**同步等待** Agent 执行完成。

**请求体**:
```json
{
  "employee_id": "emp_001"
}
```

**响应** (200 OK):
```json
{
  "message": "Task assigned and completed",
  "task": {
    "id": "task_001",
    "title": "代码审查",
    "status": "completed",
    "assigned_to": "emp_001",
    "actual_cost": 0.45,
    "tokens_output": 450,
    "result": "代码审查完成，发现3个问题",
    "completed_at": "2026-03-25T01:00:00Z"
  }
}
```

**可能的状态**:
- `completed`: 任务成功完成
- `failed`: 任务执行失败
- `needs_review`: 无法解析 Agent 响应，需要人工检查

**错误响应**:
- `404 Not Found`: 任务或员工不存在
- `400 Bad Request`: 员工未绑定 Agent
- `500 Internal Server Error`: 分配过程中发生错误

**⚠️ 注意**: 此操作是同步的，可能需要等待 15-60 秒 (默认超时 900 秒)。

---

### 重试任务

```http
POST /api/v1/tasks/{task_id}/retry
```

重试失败的任务。

**响应** (200 OK):
```json
{
  "message": "Task retried successfully",
  "task": {
    "id": "task_001",
    "status": "completed",
    "rework_count": 1
  }
}
```

**错误响应**:
- `404 Not Found`: 任务不存在
- `400 Bad Request`: 返工次数已达上限

---

### 创建任务

```http
POST /api/v1/tasks
```

**请求体**:
```json
{
  "title": "任务标题",
  "description": "任务描述",
  "priority": "normal",
  "estimated_cost": 100.0
}
```

**响应** (201 Created):
```json
{
  "id": "task_abc123",
  "title": "任务标题",
  "message": "Task created"
}
```

---

### 获取任务列表

```http
GET /api/v1/tasks?status=pending&employee_id=emp_001
```

**查询参数**:
- `status`: 按状态筛选 (pending, running, completed, failed, needs_review)
- `employee_id`: 按员工筛选

**响应**:
```json
{
  "tasks": [...],
  "total": 10
}
```

---

### 获取任务详情

```http
GET /api/v1/tasks/{task_id}
```

**响应**:
```json
{
  "id": "task_001",
  "title": "代码审查",
  "status": "completed",
  "result": "代码审查完成，发现3个问题",
  "actual_cost": 0.45,
  "tokens_output": 450
}
```

---

### 更新任务

```http
PUT /api/v1/tasks/{task_id}
```

**请求体**:
```json
{
  "title": "新标题",
  "description": "新描述",
  "priority": "high"
}
```

---

### 删除任务

```http
DELETE /api/v1/tasks/{task_id}
```

---

### 取消任务

```http
POST /api/v1/tasks/{task_id}/cancel
```

仅可取消 `pending` 状态的任务。

---

## 已废弃 API

### Skill API (已废弃)

以下端点已废弃，不再使用:

- `POST /api/skill/get-current-task` → 任务通过 `/tasks/assign` 同步分配
- `POST /api/skill/report-task-result` → Agent 通过 OPC-REPORT 格式报告结果
- `POST /api/skill/get-budget` → 预算信息包含在任务分配消息中

**保留原因**:
- 向后兼容
- 手动测试接口
- `read-manual` 端点仍可用

---

## 数据模型

### Task 状态

```python
class TaskStatus(str, Enum):
    PENDING = "pending"           # 待执行
    ASSIGNED = "assigned"         # 已分配
    IN_PROGRESS = "in_progress"   # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    NEEDS_REVISION = "needs_revision"  # 需要返工
    NEEDS_REVIEW = "needs_review"      # 需人工检查 (解析失败)
```

### TaskResponse

```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "status": "string",
  "priority": "string",
  "assigned_to": "string | null",
  "estimated_cost": "number",
  "actual_cost": "number",
  "tokens_input": "number",
  "tokens_output": "number",
  "session_key": "string | null",
  "created_at": "string | null",
  "started_at": "string | null",
  "completed_at": "string | null",
  "result": "string | null",
  "rework_count": "number",
  "max_rework": "number"
}
```

---

## 错误处理

### 标准错误格式

```json
{
  "detail": "错误描述"
}
```

### 常见错误码

| 状态码 | 含义 | 场景 |
|--------|------|------|
| 400 | Bad Request | 员工未绑定 Agent、任务状态不允许操作 |
| 404 | Not Found | 任务或员工不存在 |
| 500 | Internal Server Error | 任务分配失败、解析错误 |

---

## 测试

### 运行测试

```bash
# 单元测试
python -m pytest tests/unit/ -v

# API 测试
python -m pytest tests/api/test_tasks_api.py -v

# 集成测试
python -m pytest tests/integration/test_phase3_new_architecture.py -v
```

### 测试覆盖

| 测试类型 | 数量 | 状态 |
|---------|------|------|
| 单元测试 | 35+ | ✅ 通过 |
| API 测试 | 18 | ✅ 通过 |
| 集成测试 | 12 | ✅ 通过 |

---

**文档版本**: 1.0  
**最后更新**: 2026-03-25
