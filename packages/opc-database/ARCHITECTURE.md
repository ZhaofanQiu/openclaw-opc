# opc-database 架构设计

**版本**: v0.4.0

## 概述

opc-database 是 OpenClaw OPC 的数据库管理模块，提供：

- 异步数据库连接管理 (SQLAlchemy 2.0 + asyncpg/aiosqlite)
- ORM 数据模型定义
- Repository 数据访问层
- 数据库迁移 (Alembic)

## 架构

```
opc_database/
├── connection.py      # 数据库连接管理
├── models/            # ORM 模型
│   ├── base.py        # 基础模型
│   ├── company.py     # 公司相关
│   ├── employee.py    # 员工相关
│   └── task.py        # 任务相关
└── repositories/      # 数据访问层
    ├── base.py        # 基础仓库
    ├── employee_repo.py
    └── task_repo.py
```

## 模型设计

### 实体关系图

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Employee    │────<│     Task     │────<│TaskMessage   │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id (PK)      │     │ id (PK)      │     │ id (PK)      │
│ name         │     │ title        │     │ task_id (FK) │
│ emoji        │     │ description  │     │ sender_type  │
│ status       │     │ assigned_to  │────<│ content      │
│ budget...    │     │ status       │     └──────────────┘
└──────────────┘     │ priority     │
                     │ budget...    │
                     └──────────────┘
```

### Employee 模型

员工是任务执行的主体。

**核心字段**:
- `id`: 员工唯一标识
- `name`: 姓名
- `position_level`: 职位等级 (1-5)
- `openclaw_agent_id`: 绑定的 OpenClaw Agent
- `monthly_budget` / `used_budget`: 预算管理
- `status`: 工作状态 (idle/working/offline)

**业务方法**:
- `can_accept_task(cost)`: 检查是否能接受任务
- `remaining_budget`: 剩余预算 (属性)
- `mood_emoji`: 根据预算返回心情表情

### Task 模型

表示需要执行的工作单元。

**核心字段**:
- `id`: 任务唯一标识
- `title` / `description`: 标题和描述
- `assigned_to`: 分配的员工
- `status`: 状态 (pending/assigned/in_progress/completed/failed)
- `priority`: 优先级
- `estimated_cost` / `actual_cost`: 预算
- `result`: 执行结果

**业务方法**:
- `can_rework()`: 是否可以返工
- `is_completed`: 是否已完成 (属性)

### TaskMessage 模型

记录任务执行过程中的消息。

**核心字段**:
- `task_id`: 所属任务
- `sender_type`: 发送者类型 (user/agent/system)
- `content`: 消息内容
- `message_type`: 消息类型

## Repository 模式

### BaseRepository

提供通用CRUD操作:
- `get_by_id(id)`
- `get_all(limit, offset)`
- `create(instance)`
- `update(instance)`
- `delete(instance)`
- `count()`

### EmployeeRepository

员工专用操作:
- `get_by_openclaw_id(id)`
- `get_by_status(status)`
- `get_available_for_task(cost)` - 获取可用员工
- `update_budget(id, amount, operation)`
- `update_status(id, status, task_id)`
- `bind_openclaw_agent(id, agent_id)`
- `increment_completed_tasks(id)`
- `get_budget_stats()`

### TaskRepository

任务专用操作:
- `get_by_employee(id, status)`
- `get_by_status(status)`
- `assign_task(id, emp_id, by)`
- `start_task(id, session_key)`
- `complete_task(id, result, cost, tokens...)`
- `fail_task(id, reason)`
- `request_rework(id, feedback)`
- `get_task_stats()`

### TaskMessageRepository

消息专用操作:
- `get_by_task(id, limit, offset)`
- `add_message(task_id, type, content, ...)`

## 使用示例

### 基本CRUD

```python
from opc_database import get_session
from opc_database.repositories import EmployeeRepository

async with get_session() as session:
    repo = EmployeeRepository(session)
    
    # 创建
    emp = Employee(id="emp_1", name="张三", monthly_budget=5000)
    await repo.create(emp)
    
    # 查询
    found = await repo.get_by_id("emp_1")
    
    # 更新预算
    await repo.update_budget("emp_1", 100.0, operation="use")
```

### 任务分配

```python
from opc_database.repositories import TaskRepository, EmployeeRepository

async with get_session() as session:
    task_repo = TaskRepository(session)
    emp_repo = EmployeeRepository(session)
    
    # 找到可用员工
    available = await emp_repo.get_available_for_task(estimated_cost=500)
    if available:
        # 分配任务
        await task_repo.assign_task("task_1", available[0].id)
```

## 数据库配置

通过环境变量配置:

```bash
# SQLite (默认，开发环境)
DB_TYPE=sqlite
OPC_DB_PATH=./data/opc.db

# PostgreSQL (生产环境)
DB_TYPE=postgresql
PG_HOST=localhost
PG_PORT=5432
PG_USER=opc
PG_PASSWORD=xxx
PG_DATABASE=openclaw_opc
```

## 迁移

使用 Alembic 管理数据库迁移:

```bash
# 创建迁移
alembic revision --autogenerate -m "add new table"

# 升级
alembic upgrade head

# 降级
alembic downgrade -1
```
