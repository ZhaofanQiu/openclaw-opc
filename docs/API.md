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
