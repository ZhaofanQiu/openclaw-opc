# opc-core 架构设计

**版本**: v0.4.0

## 概述

opc-core 是 OpenClaw OPC 的业务逻辑层，基于 FastAPI 实现：

- **API 层**: RESTful API 路由
- **Service 层**: 业务逻辑封装
- **Repository 层**: 通过 opc-database 访问数据

## 架构图

```
┌─────────────────────────────────────┐
│           Client (UI)               │
└──────────────┬──────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────┐
│           FastAPI                   │
│  ┌─────────┬─────────┬──────────┐  │
│  │Employees│  Tasks  │  Budget  │  │
│  │ Manuals │ Reports │Skill API │  │
│  └─────────┴─────────┴──────────┘  │
└──────────────┬──────────────────────┘
               │ Repository
┌──────────────▼──────────────────────┐
│        opc-database                 │
│   EmployeeRepo / TaskRepo           │
└──────────────┬──────────────────────┘
               │ SQL
┌──────────────▼──────────────────────┐
│         SQLite/PostgreSQL           │
└─────────────────────────────────────┘
               │
┌──────────────▼──────────────────────┐
│        opc-openclaw                 │
│   Messenger / AgentManager          │
└──────────────┬──────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────┐
│          OpenClaw                   │
└─────────────────────────────────────┘
```

## 核心组件

### API 层

| 模块 | 功能 | 端点 |
|------|------|------|
| employees.py | 员工管理 | /employees |
| tasks.py | 任务管理 | /tasks |
| budget.py | 预算管理 | /budget |
| manuals.py | 手册管理 | /manuals |
| reports.py | 报表 | /reports |
| skill_api.py | Agent 接口 | /skill |

### Service 层

- **EmployeeService**: 员工业务逻辑
- **TaskService**: 任务业务逻辑

### 依赖注入

```python
async def create_employee(
    data: EmployeeCreate,
    repo: EmployeeRepository = Depends(get_employee_repo)
):
    ...
```

## 数据流

### 任务分配流程

```
1. User ──POST /tasks/{id}/assign──┐
                                   ▼
2. TaskRepo.assign_task()    EmployeeRepo.update_status()
                                   │
3. Messenger.send() ◄──────────────┘
                                   │
4. OpenClaw Agent ◄────────────────┘
```

### Agent 报告流程

```
1. Agent ──POST /skill/report-task-result──┐
                                           ▼
2. TaskRepo.complete_task()  EmployeeRepo.update_budget()
                                           │
3. Response ◄──────────────────────────────┘
```

## 设计原则

1. **单一职责**: 每个 API 模块只处理一类资源
2. **依赖注入**: 通过 FastAPI Depends 管理依赖
3. **异步优先**: 所有 I/O 操作都是异步的
4. **类型安全**: 完整类型注解

## 错误处理

统一的 HTTP 异常处理：

```python
raise HTTPException(status_code=404, detail="Employee not found")
```

## 认证

可选的 API Key 认证（通过环境变量配置）：

```python
async def some_endpoint(
    api_key: str = Depends(verify_api_key)
):
    ...
```
