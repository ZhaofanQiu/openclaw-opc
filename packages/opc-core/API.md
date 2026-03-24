# opc-core API 文档

**版本**: v0.4.0

## 基础信息

- **基础URL**: `http://localhost:8000`
- **API前缀**: `/api/v1`
- **认证**: Bearer Token（可选，通过 `Authorization: Bearer <token>`）

## 通用响应格式

成功响应:
```json
{
  "data": {...}
}
```

错误响应:
```json
{
  "detail": "错误信息"
}
```

## 员工管理

### 列出员工

```http
GET /api/v1/employees
```

参数:
- `status` (可选): idle/working/offline

响应:
```json
{
  "employees": [...],
  "total": 10
}
```

### 创建员工

```http
POST /api/v1/employees
```

请求体:
```json
{
  "name": "张三",
  "emoji": "🤖",
  "position_level": 2,
  "monthly_budget": 2000,
  "openclaw_agent_id": "agent_1"
}
```

### 获取员工详情

```http
GET /api/v1/employees/{id}
```

### 更新员工

```http
PUT /api/v1/employees/{id}
```

### 删除员工

```http
DELETE /api/v1/employees/{id}
```

### 绑定 Agent

```http
POST /api/v1/employees/{id}/bind
```

请求体:
```json
{
  "openclaw_agent_id": "agent_1"
}
```

### 解绑 Agent

```http
POST /api/v1/employees/{id}/unbind
```

### 获取预算

```http
GET /api/v1/employees/{id}/budget
```

响应:
```json
{
  "monthly_budget": 2000,
  "used_budget": 500,
  "remaining": 1500,
  "percentage": 25,
  "mood": "😊"
}
```

## 任务管理

### 列出任务

```http
GET /api/v1/tasks
```

参数:
- `status` (可选): pending/assigned/in_progress/completed/failed
- `employee_id` (可选): 按员工筛选

### 创建任务

```http
POST /api/v1/tasks
```

请求体:
```json
{
  "title": "编写文档",
  "description": "编写 API 文档",
  "priority": "high",
  "estimated_cost": 500
}
```

### 获取任务详情

```http
GET /api/v1/tasks/{id}
```

### 更新任务

```http
PUT /api/v1/tasks/{id}
```

### 删除任务

```http
DELETE /api/v1/tasks/{id}
```

### 分配任务

```http
POST /api/v1/tasks/{id}/assign
```

请求体:
```json
{
  "employee_id": "emp_1"
}
```

### 开始任务

```http
POST /api/v1/tasks/{id}/start
```

### 完成任务

```http
POST /api/v1/tasks/{id}/complete
```

请求体:
```json
{
  "result": "任务已完成",
  "actual_cost": 450
}
```

### 标记失败

```http
POST /api/v1/tasks/{id}/fail?reason=超时
```

### 请求返工

```http
POST /api/v1/tasks/{id}/rework?feedback=需要修改
```

### 发送消息

```http
POST /api/v1/tasks/{id}/messages
```

请求体:
```json
{
  "content": "请加快进度",
  "sender_type": "user"
}
```

## 预算管理

### 公司预算

```http
GET /api/v1/budget/company
```

响应:
```json
{
  "total_budget": 10000,
  "total_used": 3000,
  "total_remaining": 7000,
  "employee_count": 5
}
```

### 员工预算列表

```http
GET /api/v1/budget/employees
```

### 记录消耗

```http
POST /api/v1/budget/record-consumption
```

请求体:
```json
{
  "employee_id": "emp_1",
  "task_id": "task_1",
  "tokens_input": 1000,
  "tokens_output": 500
}
```

## 手册管理

### 公司手册

```http
GET /api/v1/manuals/company
PUT /api/v1/manuals/company
```

### 员工手册

```http
GET /api/v1/manuals/employee/{id}
PUT /api/v1/manuals/employee/{id}
POST /api/v1/manuals/employee/{id}/init
```

### 任务手册

```http
GET /api/v1/manuals/task/{id}
POST /api/v1/manuals/task/generate
POST /api/v1/manuals/task/{id}/regenerate
```

## 报表

### Dashboard

```http
GET /api/v1/reports/dashboard
```

响应:
```json
{
  "employees": {...},
  "tasks": {...},
  "summary": {
    "status": "normal",
    "health_score": 85
  }
}
```

### 员工绩效

```http
GET /api/v1/reports/employees
```

### 任务统计

```http
GET /api/v1/reports/tasks
```

## Skill API (Agent 调用)

### 获取当前任务

```http
POST /api/v1/skill/get-current-task
```

请求体:
```json
{
  "agent_id": "agent_1"
}
```

### 报告任务结果

```http
POST /api/v1/skill/report-task-result
```

请求体:
```json
{
  "agent_id": "agent_1",
  "task_id": "task_1",
  "result": "任务已完成",
  "tokens_used": 1500
}
```

### 获取预算

```http
POST /api/v1/skill/get-budget
```

### 读取手册

```http
POST /api/v1/skill/read-manual
```

请求体:
```json
{
  "agent_id": "agent_1",
  "manual_type": "task",
  "manual_id": "task_1"
}
```

## 健康检查

```http
GET /health
GET /
```
