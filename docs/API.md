# OpenClaw OPC API 文档

**版本**: 0.6.0  
**基础URL**: `http://localhost:8000`  
**Swagger UI**: `http://localhost:8000/docs`

---

## 认证

默认启用 API Key 认证，在请求头中添加:

```
X-API-Key: your-api-key
```

---

## 快速开始

### 1. 初始化 Partner

Partner 是您的 AI 助理，帮助管理公司。

**请求**:
```bash
curl -X POST "http://localhost:8000/api/agents/partner/setup-auto" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "monthly_budget": 10000
  }'
```

**响应**:
```json
{
  "success": true,
  "partner": {
    "id": "abc123",
    "name": "OPC Partner (Partner)",
    "agent_id": "opc_partner_abc",
    "position": "合伙人",
    "monthly_budget": 10000
  },
  "message": "Partner 'OPC Partner (Partner)' is ready!",
  "restart_required": false
}
```

### 2. 雇佣员工

**请求**:
```bash
curl -X POST "http://localhost:8000/api/agents/partner/hire?partner_id=abc123" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "name": "开发助手",
    "emoji": "👨‍💻",
    "monthly_budget": 3000,
    "position_title": "全栈开发"
  }'
```

**响应**:
```json
{
  "success": true,
  "employee": {
    "id": "def456",
    "name": "开发助手",
    "agent_id": null,
    "position": "全栈开发",
    "monthly_budget": 3000
  },
  "hired_by": "OPC Partner (Partner)",
  "message": "成功雇佣信息..."
}
```

### 3. 绑定 Agent

如果员工未绑定 Agent，需要先绑定:

```bash
curl -X POST "http://localhost:8000/api/agents/binding/bind" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "employee_id": "def456",
    "agent_id": "developer_assistant"
  }'
```

### 4. 分配任务

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "title": "开发新功能",
    "description": "实现用户登录功能",
    "agent_id": "def456",
    "estimated_cost": 500
  }'
```

### 5. 创建工作流

```bash
curl -X POST "http://localhost:8000/api/workflows?created_by=abc123" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "title": "Web应用开发",
    "description": "开发一个完整的Web应用",
    "total_budget": 5000,
    "template_id": "web_dev_template"
  }'
```

---

## 核心 API 端点

### 员工管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/agents` | 列出所有员工 |
| GET | `/api/agents/{id}` | 获取员工详情 |
| POST | `/api/agents` | 创建员工 |
| DELETE | `/api/agents/{id}` | 删除员工 |
| POST | `/api/agents/partner/setup-auto` | 自动设置Partner |
| POST | `/api/agents/partner/hire` | Partner雇佣员工 |
| GET | `/api/agents/binding/available` | 获取可绑定的Agent |
| POST | `/api/agents/binding/bind` | 绑定Agent |

### 任务管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 列出任务 |
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks/{id}` | 获取任务详情 |
| POST | `/api/tasks/{id}/assign` | 分配任务 |
| POST | `/api/tasks/{id}/complete` | 完成任务 |

### 工作流管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/workflows` | 列出工作流 |
| POST | `/api/workflows` | 创建工作流 |
| GET | `/api/workflows/{id}` | 获取工作流详情 |
| POST | `/api/workflows/{id}/start` | 启动工作流 |
| POST | `/api/workflows/{id}/steps/current/complete` | 完成当前步骤 |

### 预算管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/budget/summary` | 预算汇总 |
| GET | `/api/budget/agents` | 员工预算详情 |
| POST | `/api/budget/add` | 增加预算 |

### 技能管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/skills` | 列出技能 |
| POST | `/api/skills` | 创建技能 |
| GET | `/api/agent-skill-paths/paths` | 获取成长路径 |
| GET | `/api/agent-skill-paths/agent/{id}` | 获取员工成长路径 |

---

## 数据模型

### Agent (员工)

```json
{
  "id": "string",
  "name": "string",
  "emoji": "string",
  "position_title": "string",
  "position_level": 1,
  "status": "idle",
  "is_online": "online",
  "monthly_budget": 2000.0,
  "used_budget": 0.0,
  "remaining_budget": 2000.0,
  "agent_id": "string",
  "avatar_url": "string"
}
```

### Task (任务)

```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "status": "pending",
  "agent_id": "string",
  "estimated_cost": 100.0,
  "actual_cost": 0.0,
  "created_at": "2024-01-01T00:00:00"
}
```

### Workflow (工作流)

```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "status": "draft",
  "total_budget": 5000.0,
  "remaining_budget": 5000.0,
  "current_step_index": 0,
  "progress": 0.0
}
```

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器错误 |

---

## WebSocket

实时通知通过 WebSocket 推送:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications?agent_id=xxx');

ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log('收到通知:', notification);
};
```

### 通知类型

- `step_assigned`: 步骤分配
- `step_completed`: 步骤完成
- `rework_triggered`: 返工触发
- `fuse_triggered`: 熔断触发
- `workflow_completed`: 工作流完成

---

## 限流

默认限流配置:

- 普通接口: 100 请求/分钟
- 创建操作: 20 请求/分钟
- 批量操作: 10 请求/分钟

超出限流返回 429 状态码。

---

## 更多文档

- [数据库优化](./database_optimization.md)
- [未来开发计划](./FUTURE_PLAN.md)
- [项目状态](./PROJECT_STATUS.md)
# API Reference

Complete API documentation for OpenClaw OPC Core Service.

**Base URL**: `http://localhost:8080`  
**OpenAPI Docs**: `http://localhost:8080/docs` (Swagger UI)

---

## Authentication

Currently, OpenClaw OPC does not require authentication. Future versions will add API key support.

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

| Endpoint Type | Limit |
|--------------|-------|
| Read (GET) | 100/minute |
| Create (POST) | 20/minute |
| Delete | 10/minute |
| Health Check | 200/minute |

When rate limit is exceeded, the API returns:
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

---

## Endpoints

### Health Check

#### GET `/health`

Check if the service is running.

**Response**:
```json
{
  "status": "healthy"
}
```

---

### Root

#### GET `/`

Get service information.

**Response**:
```json
{
  "name": "OpenClaw OPC",
  "version": "0.2.0-alpha",
  "status": "running",
  "dashboard": "/dashboard",
  "docs": "/docs"
}
```

---

## Agents API

### OpenClaw Integration

#### GET `/api/agents/openclaw/agents`

List existing agents from OpenClaw configuration.

**Response**:
```json
{
  "agents": [
    {
      "id": "main",
      "name": "My Agent",
      "description": "Main OpenClaw agent"
    }
  ],
  "count": 1,
  "message": "Select one agent as your Partner"
}
```

---

### Partner Management

#### POST `/api/agents/partner/setup`

Setup Partner from existing OpenClaw agent.

**Request Body**:
```json
{
  "openclaw_agent_id": "main",
  "monthly_budget": 10000.0
}
```

**Response**:
```json
{
  "success": true,
  "partner": {
    "id": "agent_001",
    "name": "My Agent (Partner)",
    "agent_id": "main",
    "position": "合伙人",
    "monthly_budget": 10000.0
  },
  "message": "Partner 'My Agent (Partner)' is ready to help you build your company!"
}
```

**Errors**:
- `404`: OpenClaw agent not found
- `400`: Agent already registered

---

#### POST `/api/agents/company/init`

Initialize company with Partner.

**Request Body**:
```json
{
  "partner_agent_id": "main",
  "company_name": "星际工作室"
}
```

**Response**:
```json
{
  "success": true,
  "company_name": "星际工作室",
  "partner": {
    "id": "agent_001",
    "name": "My Agent (Partner)",
    "agent_id": "main"
  },
  "next_steps": [
    "1. Partner will help you hire your first employee",
    "2. Define employee role and budget",
    "3. Create first project",
    "4. Start collaborating!"
  ],
  "message": "Welcome to 星际工作室! Your Partner 'My Agent (Partner)' is ready to assist you."
}
```

---

#### POST `/api/agents/partner/hire`

Partner hires a new employee.

**Query Parameters**:
- `partner_id` (string, required): Partner agent ID

**Request Body**:
```json
{
  "name": "前端阿强",
  "agent_id": "frontend-1",
  "emoji": "🧑‍💻",
  "monthly_budget": 3000.0
}
```

**Response**:
```json
{
  "success": true,
  "employee": {
    "id": "agent_002",
    "name": "前端阿强",
    "agent_id": "frontend-1",
    "position": "初级工程师",
    "monthly_budget": 3000.0
  },
  "hired_by": "My Agent (Partner)",
  "message": "My Agent (Partner) successfully hired 前端阿强 as 初级工程师!"
}
```

---

#### POST `/api/agents/partner/heartbeat`

Partner heartbeat - reports that it's still alive.

**Query Parameters**:
- `partner_id` (string, required): Partner agent ID

**Response**:
```json
{
  "success": true,
  "message": "Heartbeat received",
  "timestamp": "2026-03-21T06:30:00.000000"
}
```

---

#### GET `/api/agents/partner/health`

Check Partner health status.

**Query Parameters**:
- `partner_id` (string, required): Partner agent ID

**Response**:
```json
{
  "partner_id": "main",
  "name": "My Agent (Partner)",
  "is_online": true,
  "status": "online",
  "last_heartbeat": "2026-03-21T06:30:00.000000",
  "seconds_since_heartbeat": 15.5,
  "warning": false
}
```

---

#### GET `/api/agents/partner/status`

Get company status for Partner.

**Query Parameters**:
- `partner_id` (string, required): Partner agent ID

**Response**:
```json
{
  "success": true,
  "partner": "My Agent (Partner)",
  "company_status": {
    "pending_tasks": 5,
    "available_agents": 3,
    "total_budget": 10000.0,
    "used_budget": 2500.0
  }
}
```

---

#### POST `/api/agents/partner/assign/{task_id}`

Partner auto-assigns a task to the best available agent.

**Path Parameters**:
- `task_id` (string, required): Task ID to assign

**Query Parameters**:
- `partner_id` (string, required): Partner agent ID
- `strategy` (string, optional): Assignment strategy (`budget`, `workload`, `combined`). Default: `budget`

**Response**:
```json
{
  "success": true,
  "task_id": "task_001",
  "assigned_to": "frontend-1",
  "agent_name": "前端阿强",
  "strategy": "budget",
  "message": "Task assigned to 前端阿强"
}
```

---

#### POST `/api/agents/partner/assign-all`

Partner assigns all pending tasks.

**Query Parameters**:
- `partner_id` (string, required): Partner agent ID
- `strategy` (string, optional): Assignment strategy. Default: `budget`

**Response**:
```json
{
  "success": true,
  "summary": {
    "total": 5,
    "successful": 4,
    "failed": 1
  },
  "assignments": [...]
}
```

---

### Agent CRUD

#### GET `/api/agents`

List all agents.

**Query Parameters**:
- `available_only` (boolean, optional): Only return IDLE agents

**Response**:
```json
[
  {
    "id": "agent_001",
    "name": "My Agent (Partner)",
    "emoji": "👑",
    "position_title": "合伙人",
    "status": "idle",
    "mood_emoji": "😊",
    "total_budget": 10000.0,
    "remaining_budget": 7500.0
  }
]
```

---

#### POST `/api/agents`

Create a new agent.

**Request Body**:
```json
{
  "name": "后端小王",
  "agent_id": "backend-1",
  "emoji": "👨‍💻",
  "monthly_budget": 3000.0
}
```

**Response**: Agent object

---

#### GET `/api/agents/{agent_id}`

Get agent details.

**Path Parameters**:
- `agent_id` (string, required): Agent ID

**Response**: Agent object

---

#### GET `/api/agents/{agent_id}/task`

Get current task assigned to agent.

**Path Parameters**:
- `agent_id` (string, required): Agent ID

**Response**:
```json
{
  "has_task": true,
  "task": {
    "id": "task_001",
    "title": "重构登录页",
    "description": "使用React重构登录页面",
    "estimated_cost": 200.0
  }
}
```

Or if no task:
```json
{
  "has_task": false
}
```

---

#### POST `/api/agents/report`

Report task completion from Agent.

**Request Body**:
```json
{
  "agent_id": "frontend-1",
  "task_id": "task_001",
  "token_used": 5000,
  "result_summary": "完成登录页重构，优化了UI",
  "status": "completed"
}
```

**Response**:
```json
{
  "success": true,
  "task_id": "task_001",
  "status": "completed",
  "actual_cost": 50.0,
  "remaining_budget": 2450.0,
  "message": "Task completed and budget updated"
}
```

---

## Tasks API

#### GET `/api/tasks`

List all tasks.

**Query Parameters**:
- `status` (string, optional): Filter by status (`pending`, `assigned`, `completed`, `failed`)

**Response**: Array of Task objects

---

#### POST `/api/tasks`

Create a new task.

**Request Body**:
```json
{
  "title": "重构登录页",
  "description": "使用React重构",
  "estimated_cost": 200.0,
  "required_skills": ["javascript", "ui-design"],
  "priority": "high",
  "due_date": "2026-03-25T00:00:00"
}
```

**Response**: Task object

---

#### GET `/api/tasks/{task_id}`

Get task details.

**Path Parameters**:
- `task_id` (string, required): Task ID

**Response**: Task object

---

#### POST `/api/tasks/{task_id}/assign`

Manually assign a task to an agent.

**Path Parameters**:
- `task_id` (string, required): Task ID

**Request Body**:
```json
{
  "agent_id": "frontend-1"
}
```

**Response**: Assignment result

---

## Budget API

#### GET `/api/budget/company`

Get company budget overview.

**Response**:
```json
{
  "total_budget": 10000.0,
  "used_budget": 2500.0,
  "remaining_budget": 7500.0,
  "usage_percentage": 25.0,
  "status": "healthy"
}
```

---

#### GET `/api/budget/agents/{agent_id}`

Get agent budget details.

**Path Parameters**:
- `agent_id` (string, required): Agent ID

**Response**:
```json
{
  "agent_id": "frontend-1",
  "agent_name": "前端阿强",
  "total_budget": 3000.0,
  "used_budget": 500.0,
  "remaining_budget": 2500.0,
  "usage_percentage": 16.7,
  "transactions": [...]
}
```

---

## Reports API

#### GET `/api/reports/daily`

Get daily report.

**Query Parameters**:
- `date_str` (string, optional): Date in YYYY-MM-DD format. Default: yesterday

**Response**: Daily report with task stats, budget consumption, agent performance

---

#### GET `/api/reports/weekly`

Get weekly report.

**Query Parameters**:
- `week_start` (string, optional): Week start date in YYYY-MM-DD format

**Response**: Weekly report with daily breakdown

---

#### GET `/api/reports/recent`

Get recent days summary.

**Query Parameters**:
- `days` (integer, optional): Number of days. Default: 7

**Response**: Recent days statistics

---

## Skills API

#### GET `/api/skills`

List all skills.

**Response**: Array of Skill objects

---

#### GET `/api/skills/match/{task_id}`

Find best matching agents for a task.

**Path Parameters**:
- `task_id` (string, required): Task ID

**Response**:
```json
{
  "task_id": "task_001",
  "matches": [
    {
      "agent_id": "frontend-1",
      "agent_name": "前端阿强",
      "match_score": 95.0,
      "matching_skills": ["javascript", "ui-design"]
    }
  ]
}
```

---

## Notifications API

#### GET `/api/notifications`

Get notifications list.

**Response**: Array of Notification objects

---

#### POST `/api/notifications/{notification_id}/read`

Mark notification as read.

**Path Parameters**:
- `notification_id` (string, required): Notification ID

---

#### DELETE `/api/notifications/{notification_id}`

Delete a notification.

**Path Parameters**:
- `notification_id` (string, required): Notification ID

---

## Config API

#### GET `/api/config`

Get system configuration.

**Response**: Config object

---

#### POST `/api/config`

Update system configuration.

**Request Body**: Partial config object

**Response**: Updated config object

---

## Monitor API

#### GET `/api/monitor/status`

Get system monitor status.

**Response**: Monitor status with task counts, agent counts, etc.

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

Common HTTP status codes:

| Status | Description |
|--------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

---

## Models

### Agent

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| name | string | Display name |
| agent_id | string | OpenClaw agent ID |
| emoji | string | Display emoji |
| position_title | string | Job title |
| position_level | string | `junior`, `senior`, `lead`, `partner` |
| status | string | `idle`, `busy`, `offline` |
| mood_emoji | string | Current mood |
| total_budget | float | Monthly budget |
| remaining_budget | float | Remaining budget |
| is_online | string | `online`, `offline` |

### Task

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| title | string | Task title |
| description | string | Task description |
| status | string | `pending`, `assigned`, `completed`, `failed` |
| estimated_cost | float | Estimated OC coin cost |
| actual_cost | float | Actual cost (after completion) |
| assigned_to | string | Agent ID (if assigned) |
| required_skills | array | List of skill names |
| priority | string | `low`, `medium`, `high` |
| due_date | datetime | Task deadline |

---

*Last Updated: 2026-03-21 - v0.2.1*
