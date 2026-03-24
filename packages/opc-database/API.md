# opc-database API 文档

**版本**: v0.4.0

## 模块导入

```python
from opc_database import get_session
from opc_database.repositories import (
    EmployeeRepository,
    TaskRepository,
    TaskMessageRepository,
)
from opc_database.models import (
    Employee,
    Task,
    TaskMessage,
    AgentStatus,
    TaskStatus,
)
```

## 数据库连接

### `get_session()`

异步上下文管理器，提供数据库会话。

```python
async with get_session() as session:
    # 使用 session 进行数据库操作
    repo = EmployeeRepository(session)
    employee = await repo.get_by_id("emp_xxx")
```

### `init_db()`

初始化数据库，创建所有表。

```python
from opc_database import init_db

await init_db()
```

### `check_connection()`

检查数据库连接是否正常。

```python
from opc_database import check_connection

is_ok = await check_connection()
```

## EmployeeRepository

### 构造函数

```python
repo = EmployeeRepository(session: AsyncSession)
```

### 基础CRUD

#### `get_by_id(id: str) -> Optional[Employee]`

根据ID获取员工。

```python
employee = await repo.get_by_id("emp_abc123")
if employee:
    print(employee.name)
```

#### `get_all(limit: int = 100, offset: int = 0) -> List[Employee]`

获取所有员工（分页）。

```python
employees = await repo.get_all(limit=10, offset=0)
```

#### `create(employee: Employee) -> Employee`

创建员工。

```python
from opc_database.models import Employee
import uuid

employee = Employee(
    id=f"emp_{uuid.uuid4().hex[:8]}",
    name="张三",
    monthly_budget=5000.0,
)
await repo.create(employee)
```

#### `update(employee: Employee) -> Employee`

更新员工信息。

```python
employee.name = "李四"
await repo.update(employee)
```

#### `delete(employee: Employee) -> None`

删除员工。

```python
await repo.delete(employee)
```

### 专用方法

#### `get_by_openclaw_id(openclaw_id: str) -> Optional[Employee]`

根据 OpenClaw Agent ID 获取员工。

```python
employee = await repo.get_by_openclaw_id("agent_xxx")
```

#### `get_by_status(status: AgentStatus) -> List[Employee]`

根据状态获取员工列表。

```python
from opc_database.models import AgentStatus

working_employees = await repo.get_by_status(AgentStatus.WORKING)
```

#### `get_available_for_task(estimated_cost: float = 0.0, limit: int = 10) -> List[Employee]`

获取可接受任务的员工（在线且预算充足）。

```python
available = await repo.get_available_for_task(estimated_cost=1000.0)
for emp in available:
    print(f"{emp.name}: 剩余预算 {emp.remaining_budget}")
```

#### `update_budget(employee_id: str, amount: float, operation: str = "add") -> Optional[Employee]`

更新员工预算。

```python
# 增加预算
await repo.update_budget("emp_1", 1000.0, operation="add")

# 使用预算
await repo.update_budget("emp_1", 500.0, operation="use")

# 设置预算
await repo.update_budget("emp_1", 5000.0, operation="set")
```

#### `update_status(employee_id: str, status: AgentStatus, current_task_id: Optional[str] = None) -> Optional[Employee]`

更新员工状态。

```python
from opc_database.models import AgentStatus

await repo.update_status("emp_1", AgentStatus.WORKING, current_task_id="task_1")
```

#### `bind_openclaw_agent(employee_id: str, openclaw_agent_id: str) -> Optional[Employee]`

绑定 OpenClaw Agent。

```python
await repo.bind_openclaw_agent("emp_1", "agent_openclaw_xxx")
```

#### `increment_completed_tasks(employee_id: str) -> Optional[Employee]`

增加已完成任务计数。

```python
await repo.increment_completed_tasks("emp_1")
```

#### `get_budget_stats() -> dict`

获取预算统计。

```python
stats = await repo.get_budget_stats()
print(f"总预算: {stats['total_budget']}")
print(f"已使用: {stats['total_used']}")
print(f"平均剩余: {stats['avg_remaining']}")
```

## TaskRepository

### 构造函数

```python
repo = TaskRepository(session: AsyncSession)
```

### 基础CRUD

#### `get_by_id(id: str) -> Optional[Task]`

根据ID获取任务。

```python
task = await repo.get_by_id("task_xxx")
```

#### `get_all(limit: int = 100, offset: int = 0) -> List[Task]`

获取所有任务（分页）。

```python
tasks = await repo.get_all(limit=50)
```

### 专用方法

#### `get_by_employee(employee_id: str, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Task]`

获取员工的任务列表。

```python
# 获取所有
all_tasks = await repo.get_by_employee("emp_1")

# 仅已完成
from opc_database.models import TaskStatus
completed = await repo.get_by_employee("emp_1", status=TaskStatus.COMPLETED)
```

#### `get_by_status(status: TaskStatus, limit: int = 100) -> List[Task]`

根据状态获取任务。

```python
pending = await repo.get_by_status(TaskStatus.PENDING)
```

#### `assign_task(task_id: str, employee_id: str, assigned_by: Optional[str] = None) -> Optional[Task]`

分配任务给员工。

```python
task = await repo.assign_task("task_1", "emp_1", assigned_by="user_admin")
```

#### `start_task(task_id: str, session_key: Optional[str] = None) -> Optional[Task]`

开始执行任务。

```python
task = await repo.start_task("task_1", session_key="session_xxx")
```

#### `complete_task(task_id: str, result: str, actual_cost: float = 0.0, tokens_input: int = 0, tokens_output: int = 0) -> Optional[Task]`

完成任务。

```python
task = await repo.complete_task(
    "task_1",
    result="任务执行完成，输出xxx",
    actual_cost=500.0,
    tokens_input=1000,
    tokens_output=500,
)
```

#### `fail_task(task_id: str, reason: str) -> Optional[Task]`

标记任务失败。

```python
task = await repo.fail_task("task_1", reason="执行超时")
```

#### `request_rework(task_id: str, feedback: str) -> Optional[Task]`

请求返工。

```python
task = await repo.request_rework("task_1", feedback="请修改xxx部分")
```

#### `get_task_stats() -> dict`

获取任务统计。

```python
stats = await repo.get_task_stats()
print(f"总任务: {stats['total_tasks']}")
print(f"各状态数量: {stats['status_counts']}")
```

## TaskMessageRepository

### 构造函数

```python
repo = TaskMessageRepository(session: AsyncSession)
```

### 方法

#### `get_by_task(task_id: str, limit: int = 100, offset: int = 0) -> List[TaskMessage]`

获取任务的消息列表。

```python
messages = await repo.get_by_task("task_1", limit=50)
for msg in messages:
    print(f"[{msg.sender_type}]: {msg.content}")
```

#### `add_message(task_id: str, sender_type: str, content: str, sender_id: Optional[str] = None, message_type: str = "text") -> TaskMessage`

添加消息。

```python
message = await repo.add_message(
    task_id="task_1",
    sender_type="user",  # "user" | "agent" | "system"
    content="请完成这个任务",
    sender_id="user_admin",
)
```

## 数据模型

### Employee

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 主键 |
| name | str | 姓名 |
| emoji | str | 表情符号 |
| position_level | int | 职位等级 (1-5) |
| openclaw_agent_id | str | OpenClaw Agent ID |
| is_bound | str | 是否绑定 ("true" \| "false") |
| monthly_budget | float | 月度预算 |
| used_budget | float | 已使用预算 |
| status | str | 状态 (idle/working/offline) |
| current_task_id | str | 当前任务ID |
| completed_tasks | int | 已完成任务数 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

**属性**:
- `remaining_budget`: 剩余预算
- `budget_percentage`: 预算百分比 (0-100)
- `mood_emoji`: 心情表情 😊😐😔🚨

**方法**:
- `can_accept_task(estimated_cost) -> bool`
- `to_dict() -> dict`

### Task

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 主键 |
| title | str | 标题 |
| description | str | 描述 |
| assigned_to | str | 分配给员工ID |
| assigned_by | str | 分配者ID |
| status | str | 状态 |
| priority | str | 优先级 |
| estimated_cost | float | 预估成本 |
| actual_cost | float | 实际成本 |
| tokens_input | int | 输入Token数 |
| tokens_output | int | 输出Token数 |
| session_key | str | OpenClaw会话ID |
| result | str | 执行结果 |
| score | int | 评分 (1-5) |
| feedback | str | 反馈 |
| execution_context | str | 执行上下文(JSON) |
| rework_count | int | 返工次数 |
| max_rework | int | 最大返工次数 |

**属性**:
- `remaining_budget`: 剩余预算
- `is_completed`: 是否已完成
- `total_tokens`: 总Token消耗

**方法**:
- `can_rework() -> bool`
- `to_dict() -> dict`

### TaskMessage

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 主键 |
| task_id | str | 任务ID |
| sender_type | str | 发送者类型 |
| sender_id | str | 发送者ID |
| content | str | 内容 |
| message_type | str | 消息类型 |
| metadata | str | 元数据(JSON) |

## 枚举类型

### AgentStatus

- `IDLE = "idle"` - 空闲
- `WORKING = "working"` - 工作中
- `OFFLINE = "offline"` - 离线

### PositionLevel

- `INTERN = 1` - 实习生
- `SPECIALIST = 2` - 专员
- `SENIOR = 3` - 资深
- `EXPERT = 4` - 专家
- `PARTNER = 5` - 合伙人

### TaskStatus

- `PENDING = "pending"` - 待分配
- `ASSIGNED = "assigned"` - 已分配
- `IN_PROGRESS = "in_progress"` - 执行中
- `COMPLETED = "completed"` - 已完成
- `FAILED = "failed"` - 失败

### TaskPriority

- `LOW = "low"`
- `NORMAL = "normal"`
- `HIGH = "high"`
- `URGENT = "urgent"`
