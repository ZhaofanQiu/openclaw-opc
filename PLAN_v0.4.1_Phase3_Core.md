# Phase 3: Core 层详细规划

**版本**: v0.4.1  
**目标**: 业务逻辑层，协调 Database 和 OpenClaw 层，适配 Phase 2 新架构  
**核心变更**: 从 HTTP 回调改为同步 ResponseParser 解析

---

## 0. 模块边界说明

### 0.1 Core 层职责

```
┌─────────────────────────────────────────────────────────────┐
│                        Core Layer                            │
│                   (packages/opc-core)                       │
├─────────────────────────────────────────────────────────────┤
│  ✅ 负责:                                                     │
│     - TaskService 业务逻辑                                   │
│     - ResponseParser 解析 Agent 回复                         │
│     - 调用 TaskCaller (来自 opc-openclaw)                    │
│     - API 路由 (tasks.py)                                    │
│                                                              │
│  ❌ 不负责:                                                   │
│     - Skill 定义/修改 (属于 Phase 2)                          │
│     - OpenClaw CLI 实现 (属于 Phase 2)                        │
│     - Agent 生命周期管理 (属于 Phase 2)                        │
│     - 与 Agent 直接通信 (通过 TaskCaller 间接)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 调用
                              ▼
                    ┌─────────────────┐
                    │  opc-openclaw   │
                    │  (Phase 2)      │
                    │  - TaskCaller   │
                    │  - Messenger    │
                    │  - ResponseParser│
                    └─────────────────┘
```

### 0.2 跨层调用规则

| 调用方向 | 允许的调用 | 禁止的调用 |
|---------|-----------|-----------|
| Core → OpenClaw | `TaskCaller.assign_task()`<br>`ResponseParser.parse()` | 直接操作 OpenClaw Config<br>修改 Skill 内容 |
| Core → Database | Repository 所有方法 | 直接 SQL 操作 |
| OpenClaw → Core | **无** (单向调用) | HTTP 回调到 Core |

### 0.3 当前状态

- **Day 1**: ✅ TaskService 核心适配完成
- **Day 2**: ✅ API 路由调整完成
- **Day 3**: ⏳ 集成测试与文档更新

---

## 一、架构适配概览

### 1.1 Phase 2 变更对 Core 层的影响

| 组件 | 原设计 | 新设计 | 影响程度 |
|------|--------|--------|----------|
| **TaskService.assign_task()** | 异步分配，等待 HTTP 回调 | **同步分配，立即解析回复** | 🔴 高 |
| **Skill API 路由** | `POST /api/skill/task/{id}/complete` | **移除或改为内部方法** | 🔴 高 |
| **Task 状态流转** | PENDING → RUNNING → 回调更新 | **PENDING → RUNNING → 同步解析** | 🔴 高 |
| **Budget 结算** | 回调时结算 | **同步返回后结算** | 🟡 中 |
| **错误处理** | 网络超时/回调失败 | **解析失败/Agent 格式错误** | 🟡 中 |

### 1.2 新数据流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Dashboard │────▶│  Core API   │────▶│  TaskService│
│  (UI 点击)  │     │ /tasks/assign│     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                       ┌─────────────┐
                                       │ TaskCaller  │
                                       │.assign_task()│
                                       └──────┬──────┘
                                              │
                                              ▼ CLI
                                       ┌─────────────┐
                                       │ OpenClaw    │
                                       │ Agent       │
                                       └──────┬──────┘
                                              │
                                              ▼ 回复
                                       ┌─────────────┐
                                       │ResponseParser│
                                       │  .parse()   │
                                       └──────┬──────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │ Task.status │
                                       │  同步更新    │
                                       └─────────────┘
```

---

## 二、模块详细设计

### 2.1 Task Service (核心适配)

#### 文件位置
```
packages/opc-core/src/opc_core/services/task_service.py
```

#### 类设计
```python
from opc_openclaw import TaskCaller, TaskAssignment, ResponseParser, ParsedReport
from opc_database import TaskRepository, EmployeeRepository

class TaskService:
    """
    任务业务逻辑 (适配 Phase 2 新架构)
    
    核心变更:
    - assign_task() 改为同步流程
    - 使用 ResponseParser 解析 Agent 回复
    - 移除对 HTTP 回调的依赖
    """
    
    def __init__(
        self,
        task_repo: TaskRepository,
        employee_repo: EmployeeRepository,
        budget_service: BudgetService,
        manual_service: ManualService
    ):
        self.task_repo = task_repo
        self.employee_repo = employee_repo
        self.budget_service = budget_service
        self.manual_service = manual_service
        self.task_caller = TaskCaller()
        self.response_parser = ResponseParser()
    
    # ============================================================
    # 核心方法: 任务分配 (需重写)
    # ============================================================
    
    async def assign_task(
        self,
        task_id: str,
        employee_id: str
    ) -> Task:
        """
        分配任务给员工 (新架构: 同步解析)
        
        流程:
        1. 验证任务和员工
        2. 更新任务状态为 RUNNING
        3. 构建任务分配消息 (含预算)
        4. 调用 TaskCaller 发送任务
        5. 使用 ResponseParser 解析回复
        6. 根据解析结果更新任务
        7. 结算预算
        
        Args:
            task_id: 任务ID
            employee_id: 员工ID
            
        Returns:
            Task: 更新后的任务对象
            
        Raises:
            TaskNotFoundError: 任务不存在
            EmployeeNotFoundError: 员工不存在
            AgentNotBoundError: 员工未绑定 Agent
            TaskAssignmentError: 分配失败
        """
        # Step 1: 验证
        task = await self._validate_and_get_task(task_id, employee_id)
        employee = await self.employee_repo.get_by_id(employee_id)
        
        if not employee.openclaw_agent_id:
            raise AgentNotBoundError(f"Employee {employee_id} has no agent bound")
        
        # Step 2: 更新状态为 RUNNING
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        await self.task_repo.update(task)
        
        try:
            # Step 3: 构建任务分配
            assignment = await self._build_task_assignment(task, employee)
            
            # Step 4: 发送任务 (同步等待 Agent 回复)
            response = await self.task_caller.assign_task(assignment)
            
            if not response.success:
                # 发送失败 (Agent 不可用等)
                task.status = TaskStatus.FAILED
                task.result = {
                    "error": "Failed to send task to agent",
                    "details": response.error
                }
                await self.task_repo.update(task)
                raise TaskAssignmentError(f"Failed to assign task: {response.error}")
            
            # Step 5: 解析 Agent 回复
            report = self.response_parser.parse(response.content)
            
            # Step 6: 根据解析结果更新任务
            await self._update_task_from_report(task, report, response)
            
            # Step 7: 结算预算
            await self._settle_budget(task, employee, report)
            
            return task
            
        except Exception as e:
            # 意外错误，标记为失败
            task.status = TaskStatus.FAILED
            task.result = {
                "error": "Unexpected error during task assignment",
                "details": str(e)
            }
            await self.task_repo.update(task)
            raise TaskAssignmentError(f"Task assignment failed: {e}") from e
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    async def _validate_and_get_task(
        self,
        task_id: str,
        employee_id: str
    ) -> Task:
        """验证任务和员工匹配"""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        if task.employee_id != employee_id:
            raise TaskAssignmentError(
                f"Task {task_id} does not belong to employee {employee_id}"
            )
        
        if task.status not in [TaskStatus.PENDING, TaskStatus.NEEDS_REVISION]:
            raise TaskAssignmentError(
                f"Cannot assign task with status {task.status}"
            )
        
        return task
    
    async def _build_task_assignment(
        self,
        task: Task,
        employee: Employee
    ) -> TaskAssignment:
        """构建任务分配对象"""
        # 获取预算信息
        budget_info = await self.budget_service.get_employee_budget(employee.id)
        
        # 获取手册路径 (绝对路径)
        company_manual = self.manual_service.get_company_manual_path()
        employee_manual = self.manual_service.get_employee_manual_path(employee.id)
        task_manual = self.manual_service.get_task_manual_path(task.id)
        
        return TaskAssignment(
            task_id=task.id,
            title=task.title,
            description=task.description,
            agent_id=employee.openclaw_agent_id,
            agent_name=employee.name,
            employee_id=employee.id,
            company_manual_path=company_manual,
            employee_manual_path=employee_manual,
            task_manual_path=task_manual,
            timeout=900,  # 15 分钟
            monthly_budget=budget_info.monthly_budget,
            used_budget=budget_info.used_budget,
            remaining_budget=budget_info.remaining_budget
        )
    
    async def _update_task_from_report(
        self,
        task: Task,
        report: ParsedReport,
        response: TaskResponse
    ) -> None:
        """根据解析结果更新任务"""
        task.completed_at = datetime.now(timezone.utc)
        
        if report.is_valid:
            # 解析成功
            task.status = TaskStatus(report.status) if report.status else TaskStatus.COMPLETED
            task.result = {
                "summary": report.summary,
                "tokens_used": report.tokens_used,
                "result_files": report.result_files,
                "agent_response": response.content,  # 保留原始回复
                "parsed": True
            }
        else:
            # 解析失败 (Agent 未返回 OPC-REPORT 格式)
            task.status = TaskStatus.NEEDS_REVIEW
            task.result = {
                "error": "Failed to parse agent response",
                "parse_errors": report.errors,
                "agent_response": response.content,
                "parsed": False
            }
        
        await self.task_repo.update(task)
    
    async def _settle_budget(
        self,
        task: Task,
        employee: Employee,
        report: ParsedReport
    ) -> None:
        """结算预算"""
        tokens_used = report.tokens_used if report.is_valid else 0
        
        if tokens_used > 0:
            await self.budget_service.record_usage(
                employee_id=employee.id,
                task_id=task.id,
                tokens_used=tokens_used
            )
    
    # ============================================================
    # 其他任务方法 (基本不变)
    # ============================================================
    
    async def create_task(
        self,
        title: str,
        description: str,
        employee_id: str,
        budget: Optional[int] = None
    ) -> Task:
        """创建任务"""
        task = Task(
            id=generate_uuid(),
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            employee_id=employee_id,
            budget=budget,
            created_at=datetime.now(timezone.utc)
        )
        return await self.task_repo.create(task)
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return await self.task_repo.get_by_id(task_id)
    
    async def list_tasks(
        self,
        employee_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """列表查询"""
        return await self.task_repo.list(
            employee_id=employee_id,
            status=status,
            limit=limit,
            offset=offset
        )
    
    async def retry_task(self, task_id: str) -> Task:
        """重试失败的任务"""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        if task.status not in [TaskStatus.FAILED, TaskStatus.NEEDS_REVISION, TaskStatus.NEEDS_REVIEW]:
            raise TaskAssignmentError(f"Cannot retry task with status {task.status}")
        
        # 重置状态并重新分配
        task.status = TaskStatus.PENDING
        task.result = None
        task.completed_at = None
        await self.task_repo.update(task)
        
        return await self.assign_task(task_id, task.employee_id)
```

---

## 三、API 路由调整

### 3.1 Task API (更新)

#### 文件位置
```
packages/opc-core/src/opc_core/api/tasks.py
```

#### 路由列表
```python
from fastapi import APIRouter, Depends, HTTPException
from opc_core.services import TaskService
from opc_core.schemas import TaskCreateRequest, TaskResponse, TaskAssignRequest

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("", response_model=TaskResponse)
async def create_task(
    request: TaskCreateRequest,
    task_service: TaskService = Depends(get_task_service)
):
    """创建任务"""
    task = await task_service.create_task(
        title=request.title,
        description=request.description,
        employee_id=request.employee_id,
        budget=request.budget
    )
    return TaskResponse.from_orm(task)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务详情"""
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_orm(task)

@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: str,
    request: TaskAssignRequest,
    task_service: TaskService = Depends(get_task_service)
):
    """
    分配任务给员工 (同步返回结果)
    
    新架构: 同步等待 Agent 回复，立即返回结果
    响应包含: status, result.summary, result.tokens_used
    """
    try:
        task = await task_service.assign_task(task_id, request.employee_id)
        return TaskResponse.from_orm(task)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except EmployeeNotFoundError:
        raise HTTPException(status_code=404, detail="Employee not found")
    except AgentNotBoundError:
        raise HTTPException(status_code=400, detail="Employee has no agent bound")
    except TaskAssignmentError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    task_service: TaskService = Depends(get_task_service)
):
    """任务列表"""
    status_enum = TaskStatus(status) if status else None
    tasks = await task_service.list_tasks(
        employee_id=employee_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )
    return [TaskResponse.from_orm(t) for t in tasks]

@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """重试失败的任务"""
    try:
        task = await task_service.retry_task(task_id)
        return TaskResponse.from_orm(task)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except TaskAssignmentError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 3.2 Skill API (废弃或保留)

#### 方案 A: 完全移除 (推荐)
```python
# packages/opc-core/src/opc_core/api/__init__.py

# 移除以下导入:
# from . import skill_api

# router.include_router(skill_api.router)
```

#### 方案 B: 保留但标记为废弃
```python
# packages/opc-core/src/opc_core/api/skill_api.py

"""
⚠️ 已废弃 (Phase 2 架构变更)

这些端点不再需要，因为 Agent 通过 OPC-REPORT 格式
在消息回复中直接报告结果，Core 通过 ResponseParser 解析。

保留仅用于特殊情况 (如长时间任务需要主动推送进度)。
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/skill", tags=["skill (deprecated)"])

@router.post("/task/{task_id}/complete")
async def complete_task_deprecated(task_id: str):
    """⚠️ 已废弃: 使用 /tasks/{id}/assign 同步返回结果"""
    raise HTTPException(
        status_code=410,  # Gone
        detail="This endpoint is deprecated. Use /api/tasks/{id}/assign for synchronous results."
    )

@router.post("/task/{task_id}/update")
async def update_task_progress(task_id: str, request: TaskUpdateRequest):
    """
    进度更新 (可选保留)
    
    用于长时间任务主动推送进度。
    非必需，因为短任务已改为同步返回。
    """
    # 实现可选...
    pass
```

---

## 四、数据模型更新

### 4.1 TaskStatus 枚举 (新增状态)

```python
# packages/opc-database/src/opc_database/models/task.py

from enum import Enum

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"           # 待执行
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    NEEDS_REVISION = "needs_revision"  # 需要返工
    NEEDS_REVIEW = "needs_review"      # ★ 新增: 需人工检查 (解析失败)
```

### 4.2 Task 模型 (无需修改)

```python
class Task(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    employee_id: str
    budget: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[dict]  # 存储解析后的结果
```

---

## 五、开发步骤

### Day 1: TaskService 核心适配 ✅ 已完成

**目标**: 实现 `assign_task()` 同步流程

**已完成任务**:
1. ✅ 更新 `TaskStatus` 枚举，添加 `NEEDS_REVIEW`
2. ✅ 实现 `TaskService._validate_and_get_task()`
3. ✅ 实现 `TaskService._build_task_assignment()`
4. ✅ 实现 `TaskService._update_task_from_report()`
5. ✅ 实现 `TaskService._settle_budget()`
6. ✅ 重写 `TaskService.assign_task()` 主流程
7. ✅ 编写单元测试 (Mock TaskCaller 和 ResponseParser)

**验收标准**:
- ✅ `assign_task()` 能正确调用 `TaskCaller.assign_task()`
- ✅ 能使用 `ResponseParser.parse()` 解析回复
- ✅ 能根据解析结果正确更新 Task 状态
- ✅ 单元测试覆盖率 > 80%

### Day 2: API 路由调整 ✅ 已完成

**目标**: 更新 Task API，废弃 Skill API

**已完成任务**:
1. ✅ 更新 `POST /api/tasks/{id}/assign` 路由
2. ✅ 更新 `TaskResponse` Schema (包含 result 字段)
3. ✅ 标记废弃 Skill API (添加 deprecated=True)
4. ✅ 添加 `POST /api/tasks/{id}/retry` 路由
5. ⏳ 更新 API 文档
6. ✅ 编写 API 测试 (18 个测试全部通过)

**完成内容**:
- `tasks.py`: 重写任务分配路由，使用 TaskService 同步流程
- `tasks.py`: 添加 retry_task 路由
- `skill_api.py`: 标记废弃，添加 deprecation 警告
- `test_tasks_api.py`: 18 个 API 测试全部通过

**验收标准**:
- ✅ `/tasks/assign` 同步返回结果
- ✅ 错误处理正确 (404, 400, 500)
- ✅ API 测试通过

### Day 3: 集成与测试 ✅ 已完成

**目标**: 整合测试与文档更新

**已完成任务**:
1. ✅ 编写集成测试 (使用 Mock OpenClaw)
2. ✅ 测试完整流程: 创建 → 分配 → 解析 → 更新
3. ✅ 测试错误场景: 解析失败、Agent 不可用
4. ✅ 性能测试 (同步等待时间)
5. ✅ 更新 API 文档 (API.md)

**完成内容**:
- `test_phase3_new_architecture.py`: 12 个集成测试全部通过
  - ResponseParser 集成测试 (3个)
  - TaskService + ResponseParser 集成测试 (4个)
  - 任务重试集成测试 (2个)
  - 端到端工作流测试 (2个)
  - 性能测试 (1个)
- `API.md`: 完整的 API 文档，包含架构变更说明

**测试统计**:
| 测试类型 | 数量 | 状态 |
|---------|------|------|
| 单元测试 | 35+ | ⚠️ 6个旧测试需清理 |
| API 测试 | 18 | ✅ 全部通过 |
| 集成测试 | 12 | ✅ 全部通过 |

**边界提醒**:
- ⚠️ Core 层只调用 `TaskCaller` 和 `ResponseParser`，不修改 skill 内容
- ⚠️ Skill 相关内容属于 Phase 2 (opc-openclaw 包)
- ⚠️ Core 通过 CLI 与 OpenClaw 交互，不直接操作 Agent

**验收标准**:
- ✅ 集成测试通过 (12/12)
- ✅ 错误场景正确处理
- ✅ 文档更新完成

---

## 六、测试策略

### 6.1 单元测试

```python
# tests/unit/services/test_task_service.py

class TestTaskServiceAssign:
    """TaskService.assign_task() 测试"""
    
    async def test_assign_task_success(self):
        """测试成功分配"""
        # Mock
        mock_task = Task(id="task-1", status=TaskStatus.PENDING)
        mock_employee = Employee(id="emp-1", openclaw_agent_id="opc-worker-1")
        mock_response = TaskResponse(
            success=True,
            content="---OPC-REPORT---\nstatus: completed\ntokens_used: 100\n---END-REPORT---"
        )
        
        # 执行
        with patch.object(TaskCaller, 'assign_task', return_value=mock_response):
            result = await task_service.assign_task("task-1", "emp-1")
        
        # 验证
        assert result.status == TaskStatus.COMPLETED
        assert result.result["tokens_used"] == 100
        assert result.result["parsed"] is True
    
    async def test_assign_task_parse_failure(self):
        """测试解析失败"""
        mock_response = TaskResponse(
            success=True,
            content="I have completed the task"  # 无 OPC-REPORT 格式
        )
        
        with patch.object(TaskCaller, 'assign_task', return_value=mock_response):
            result = await task_service.assign_task("task-1", "emp-1")
        
        assert result.status == TaskStatus.NEEDS_REVIEW
        assert result.result["parsed"] is False
    
    async def test_assign_task_send_failure(self):
        """测试发送失败"""
        mock_response = TaskResponse(success=False, error="Agent not found")
        
        with patch.object(TaskCaller, 'assign_task', return_value=mock_response):
            with pytest.raises(TaskAssignmentError):
                await task_service.assign_task("task-1", "emp-1")
```

### 6.2 API 测试

```python
# tests/api/test_tasks_api.py

class TestAssignTaskAPI:
    """任务分配 API 测试"""
    
    async def test_assign_task_endpoint(self, client):
        """测试分配端点"""
        response = await client.post("/api/tasks/task-1/assign", json={
            "employee_id": "emp-1"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["completed", "failed", "needs_revision", "needs_review"]
        assert "result" in data
```

### 6.3 集成测试

```bash
# scripts/test_phase3.sh

echo "=== Phase 3 集成测试 ==="

# 1. 启动 Core API
cd packages/opc-core
python -c "from opc_core import create_app; import uvicorn; uvicorn.run(create_app(), host='0.0.0.0', port=8000)" &
core_pid=$!
sleep 3

# 2. 创建员工
echo "创建员工..."
emp_response=$(curl -s -X POST http://localhost:8000/api/employees \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "position_title": "Dev", "monthly_budget": 1000}')
emp_id=$(echo $emp_response | jq -r '.id')

# 3. 绑定 Agent
echo "绑定 Agent..."
curl -s -X POST "http://localhost:8000/api/employees/${emp_id}/bind" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "opc-test-worker"}'

# 4. 创建任务
echo "创建任务..."
task_response=$(curl -s -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Test Task\", \"description\": \"Do something\", \"employee_id\": \"${emp_id}\"}")
task_id=$(echo $task_response | jq -r '.id')

# 5. 分配任务 (同步)
echo "分配任务..."
assign_response=$(curl -s -X POST "http://localhost:8000/api/tasks/${task_id}/assign" \
  -H "Content-Type: application/json" \
  -d "{\"employee_id\": \"${emp_id}\"}")

echo "分配结果:"
echo $assign_response | jq .

# 6. 验证
status=$(echo $assign_response | jq -r '.status')
if [ "$status" = "completed" ] || [ "$status" = "needs_review" ]; then
    echo "✅ 测试通过"
else
    echo "❌ 测试失败"
fi

# 清理
kill $core_pid
```

---

## 七、风险与应对

| 风险 | 可能性 | 影响 | 应对 |
|------|--------|------|------|
| ResponseParser 解析失败率高 | 中 | 高 | 优化解析逻辑，添加容错；优化 SKILL.md 引导 |
| 同步等待时间过长 | 中 | 中 | 设置合理 timeout；优化 Agent 响应速度 |
| Agent 格式不兼容 | 低 | 高 | 强化 SKILL.md 示例；提供测试工具 |
| Budget 结算并发问题 | 低 | 中 | 使用数据库事务；添加乐观锁 |

---

## 八、接口契约

### 8.1 Core 层对外接口

```python
# TaskService
TaskService.create_task(title, description, employee_id, budget) -> Task
TaskService.assign_task(task_id, employee_id) -> Task  # ★ 同步返回
TaskService.get_task(task_id) -> Task | None
TaskService.list_tasks(...) -> List[Task]
TaskService.retry_task(task_id) -> Task

# EmployeeService (基本不变)
EmployeeService.hire_employee(...) -> Employee
EmployeeService.bind_agent(employee_id, agent_id) -> bool
```

### 8.2 REST API

```yaml
POST   /api/tasks              # 创建任务
GET    /api/tasks/{id}         # 获取任务
POST   /api/tasks/{id}/assign  # ★ 分配任务 (同步)
GET    /api/tasks              # 任务列表
POST   /api/tasks/{id}/retry   # 重试任务

POST   /api/employees          # 创建员工
GET    /api/employees/{id}     # 获取员工
POST   /api/employees/{id}/bind # 绑定 Agent

# ❌ 废弃 (Phase 2 架构变更)
# POST /api/skill/task/{id}/complete
# POST /api/skill/task/{id}/update
```

---

## 九、验收标准

### 功能验收

- ✅ `TaskService.assign_task()` 同步流程正确
- ✅ `ResponseParser.parse()` 正确解析 Agent 回复
- ✅ Task 状态正确流转 (PENDING → RUNNING → COMPLETED/FAILED/NEEDS_REVIEW)
- ✅ Budget 正确结算
- ✅ 解析失败时状态为 NEEDS_REVIEW
- ✅ `/api/tasks/{id}/assign` 同步返回结果
- ✅ 错误处理正确 (404, 400, 500)

### 测试验收

- ✅ 单元测试 > 80% 覆盖率
- ✅ API 测试覆盖所有端点
- ✅ 集成测试通过
- ✅ 错误场景测试通过

---

## 十、下一步完成情况

### 清理旧测试 ✅ 已完成

**目标**: 修复旧测试导入和逻辑错误

**已完成任务**:
1. ✅ 修复 `test_employee_api.py::test_bind_agent` - 添加 AgentManager mock
2. ✅ 重写 `test_task_api.py` - 适配新架构
3. ✅ 修复 `test_end_to_end.py` - 移除已废弃的 SessionClient 导入
4. ✅ 标记旧架构测试为跳过

**完成内容**:
- `test_employee_api.py`: 修复 patch 导入，添加 AgentManager 异步上下文管理器 mock
- `test_task_api.py`: 
  - 重写为使用 mock_task_service 的新架构测试
  - 添加 `TestTaskAssignNewArchitecture` 测试类
  - 添加 `TestDeprecatedRoutes` 测试类验证已移除路由返回 404
- `test_end_to_end.py`:
  - 修复 SessionClient 导入错误（已在新架构中移除）
  - 使用 try/except 处理可选导入
  - 标记 `TestOpenClawIntegration` 为跳过（旧架构 HTTP API 测试）

**测试统计** (最终):
| 测试类型 | 数量 | 状态 |
|---------|------|------|
| 单元测试 | 82 | ✅ 全部通过 |
| 跳过测试 | 2 | ⚠️ 旧架构 HTTP API 测试 |

**验收标准**:
- ✅ 所有活跃测试通过 (82/82)
- ✅ 无导入错误
- ✅ 旧架构测试已妥善处理（跳过而非失败）

---

**计划版本**: v0.4.1 Phase 3  
**目标日期**: 3 天  
**实际完成**: 2026-03-25  
**文档维护**: 随开发进度更新
