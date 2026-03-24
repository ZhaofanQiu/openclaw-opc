# OpenClaw OPC v0.4.1 开发计划

**目标**: 跑通端到端任务流程  
**核心流程**: Dashboard 创建任务 → Core 分配 → OpenClaw 调用 Agent → Agent 执行 → 回调更新状态 → Dashboard 显示完成

---

## 架构原则

1. **模块独立**: 每个模块先完成内部功能，明确对外接口
2. **接口契约**: 模块间通过明确的数据结构交互，不直接依赖实现
3. **测试先行**: 每个模块独立测试通过后，再进行集成调试
4. **逐步集成**: 最后一步才调试模块间的互相依赖

---

## Phase 1: Database 层 - 数据支撑 ✅ (已完成)

**状态**: v0.4.0 已完成  
**职责**: 数据持久化，提供 Repository 接口

### 1.1 功能确认
- [x] Employee 模型与 Repository
- [x] Task 模型与 Repository  
- [x] Company/Budget 模型
- [x] 数据库迁移脚本

### 1.2 对外接口
```python
# Repository 层提供的接口
EmployeeRepository.create() -> Employee
EmployeeRepository.get_by_id() -> Employee | None
EmployeeRepository.update() -> Employee

TaskRepository.create() -> Task
TaskRepository.get_by_id() -> Task | None
TaskRepository.update_status() -> Task
TaskRepository.list_by_employee() -> list[Task]
```

### 1.3 独立测试
```bash
cd packages/opc-database
pytest tests/ -v  # 35 tests passing
```

**验收标准**: ✅ 全部 35 个测试通过

---

## Phase 2: OpenClaw 层 - Agent 通信

**状态**: ✅ 已完成 (2026-03-24)  
**职责**: 与外部 OpenClaw Agent 通信，封装 sessions_send 等操作

### ⚠️ 技术调整说明 (重要)

Phase 2 实际实现与原计划有**重大架构变更**，影响后续 Phase 3-5 的设计：

| 项目 | 原计划 | 实际实现 | 影响 |
|------|--------|----------|------|
| 通信方式 | HTTP API | **CLI 模式** (`openclaw agent --message`) | 无需 HTTP 服务端点 |
| Agent 报告 | HTTP POST 回调 | **结构化数据嵌入** (OPC-REPORT) | Core 需改为解析而非接收 POST |
| Skill 脚本 | 3 个 Python 脚本 | **0 个脚本** (纯文档指引) | Agent 直接生成报告格式 |
| Skill 版本 | opc-bridge-v2 1.0.0 | **opc-bridge v0.4.1** | 版本与主包统一 |

### 新架构模式: 结构化数据嵌入

**原设计 (HTTP 回调)**:
```
OPC Core → HTTP POST → Agent
Agent 执行 → HTTP POST → OPC Core /api/skill/task/{id}/complete
```

**新设计 (结构化嵌入)**:
```
OPC Core → CLI message → Agent
Agent 执行 → Reply with OPC-REPORT → OPC Core parses response
```

**OPC-REPORT 格式**:
```
---OPC-REPORT---
task_id: xxx
status: completed|failed|needs_revision
tokens_used: 800
summary: 任务完成总结
result_files: /path/to/file1.md,/path/to/file2.md
---END-REPORT---
```

### Phase 3-5 影响清单

| 影响模块 | 原设计 | 需调整 |
|----------|--------|--------|
| **Phase 3 Skill API** | `POST /api/skill/task/{id}/complete` | 改为调用 `ResponseParser.parse(agent_reply)` |
| **Phase 3 Task Service** | `handle_task_callback()` 接收 HTTP | `handle_task_result()` 解析文本响应 |
| **Phase 3 状态流转** | 异步回调更新 | 同步解析更新 |
| **Phase 5 集成测试** | 测试 HTTP 回调端点 | 测试文本解析逻辑 |

### 2.1 功能开发

#### 2.1.1 Session 客户端完善
```python
# packages/opc-openclaw/src/opc_openclaw/client/sessions.py

class SessionClient:
    """OpenClaw Session API 客户端"""
    
    async def send_message(
        self, 
        session_key: str, 
        message: str,
        timeout_seconds: int = 300
    ) -> dict:
        """发送消息到 Agent"""
        pass
    
    async def spawn_agent(
        self,
        agent_id: str,
        task: str,
        label: str | None = None
    ) -> dict:
        """创建新 Agent 会话并分配任务"""
        pass
```

#### 2.1.2 Agent 绑定管理
```python
# packages/opc-openclaw/src/opc_openclaw/agent_manager.py

class AgentManager:
    """Agent 生命周期管理"""
    
    async def bind_agent_to_employee(
        self,
        employee_id: str,
        agent_id: str
    ) -> bool:
        """绑定 Agent 到员工"""
        pass
    
    async def invoke_agent_for_task(
        self,
        agent_id: str,
        task_message: dict
    ) -> str:
        """
        调用 Agent 执行任务
        返回: session_key 用于后续跟踪
        """
        pass
```

### 2.2 对外接口
```python
# OpenClaw 层对外暴露的接口

AgentManager.bind_agent_to_employee() -> bool
AgentManager.invoke_agent_for_task() -> str
SessionClient.send_message() -> dict
```

### 2.3 独立测试
```bash
cd packages/opc-openclaw
pytest tests/ -v  # 需要 35 tests passing
```

**测试重点**:
- HTTP Mock 测试 sessions_send API
- Agent 绑定/解绑流程
- 错误重试机制

**验收标准**: 
- [ ] 35 个测试通过
- [ ] Mock 测试覆盖正常和异常场景

---

## Phase 3: Core 层 - 业务逻辑

**状态**: 🚧 待完善 (需适配 Phase 2 新架构)  
**职责**: 业务 API，协调 Database 和 OpenClaw 层

### ⚠️ Phase 2 架构变更对 Phase 3 的影响

**原设计**: Agent 通过 HTTP POST 回调到 Core 的 Skill API  
**新设计**: Agent 在回复中嵌入 OPC-REPORT，Core 通过 `ResponseParser` 解析

**需修改的组件**:

1. **TaskService.assign_task()** 
   - 原: 发送任务后等待异步回调
   - 新: 发送任务后立即接收回复，调用 `ResponseParser.parse()` 提取结果

2. **Skill API 路由**
   - 原: `POST /api/skill/task/{id}/complete` (HTTP 回调)
   - 新: **可移除或改为内部方法**，不再需要对外暴露 HTTP 端点

3. **状态流转逻辑**
   - 原: PENDING → RUNNING (异步) → COMPLETED (回调)
   - 新: PENDING → RUNNING → COMPLETED (同步解析)

### 3.1 功能开发 (更新后)

#### 3.1.1 Task Service 适配
```python
# packages/opc-core/src/opc_core/services/task_service.py

from opc_openclaw import TaskCaller, TaskAssignment, ResponseParser

class TaskService:
    """任务业务逻辑"""
    
    async def assign_task(
        self,
        task_id: str,
        employee_id: str
    ) -> Task:
        """
        分配任务给员工 (适配 Phase 2 新架构)
        
        流程:
        1. 更新任务状态为 RUNNING
        2. 调用 OpenClaw 层发送任务消息
        3. 接收 Agent 回复
        4. 使用 ResponseParser 解析 OPC-REPORT
        5. 更新任务状态和结果
        """
        # 1. 获取任务和员工信息
        task = await self.task_repo.get_by_id(task_id)
        employee = await self.employee_repo.get_by_id(employee_id)
        
        # 2. 构建任务分配消息
        assignment = TaskAssignment(
            task_id=task_id,
            title=task.title,
            description=task.description,
            agent_id=employee.openclaw_agent_id,
            agent_name=employee.name,
            employee_id=employee_id,
            company_manual_path=...,  # 绝对路径
            employee_manual_path=..., # 绝对路径
            task_manual_path=...,     # 绝对路径
            timeout=900,
            monthly_budget=employee.monthly_budget,
            used_budget=...,  # 从 BudgetService 获取
            remaining_budget=...
        )
        
        # 3. 调用 OpenClaw 层
        caller = TaskCaller()
        response = await caller.assign_task(assignment)
        
        # 4. 解析 Agent 回复中的结构化数据
        from opc_openclaw import ResponseParser
        parser = ResponseParser()
        report = parser.parse(response.content)
        
        # 5. 根据解析结果更新任务
        if report.is_valid:
            task.status = report.status  # completed/failed/needs_revision
            task.result = {
                "summary": report.summary,
                "tokens_used": report.tokens_used,
                "result_files": report.result_files
            }
            # 结算预算...
        else:
            # 解析失败，标记为需人工检查
            task.status = "needs_review"
            task.result = {"error": "Failed to parse agent response", "raw": response.content}
        
        return await self.task_repo.update(task)
```

#### 3.1.2 Skill API 调整 (可选项)

**方案 A: 完全移除 HTTP Skill API**
```python
# 不再需要以下路由:
# POST /api/skill/task/{id}/complete
# POST /api/skill/task/{id}/update

# 所有回调处理改为内部方法调用 ResponseParser
```

**方案 B: 保留用于特殊情况**
```python
# 如果需要支持 Agent 主动推送 (如长时间任务)
# 保留 POST /api/skill/task/{id}/update 用于进度更新
# 但 task/complete 通过 ResponseParser 处理
```

**推荐**: 采用方案 A，保持架构简洁

#### 3.1.3 Employee Service (基本不变)
```python
# packages/opc-core/src/opc_core/services/employee_service.py

class EmployeeService:
    """员工业务逻辑"""
    
    async def hire_employee(
        self,
        name: str,
        position_title: str,
        monthly_budget: int
    ) -> Employee:
        """雇佣新员工"""
        pass
    
    async def bind_agent(
        self,
        employee_id: str,
        agent_id: str
    ) -> bool:
        """绑定 Agent 到员工"""
        # 调用 ConfigManager 修改 OpenClaw config
        pass
```
```python
# packages/opc-core/src/opc_core/services/task_service.py

class TaskService:
    """任务业务逻辑"""
    
    async def create_task(
        self,
        title: str,
        description: str,
        employee_id: str,
        budget: int | None = None
    ) -> Task:
        """创建任务（待分配状态）"""
        pass
    
    async def assign_task(
        self,
        task_id: str,
        employee_id: str
    ) -> Task:
        """
        分配任务给员工
        - 更新任务状态为 PENDING
        - 调用 OpenClaw 层 invoke_agent
        - 记录 session_key
        """
        pass
    
    async def handle_task_callback(
        self,
        task_id: str,
        result: dict
    ) -> Task:
        """
        处理 Agent 回调结果
        - 更新任务状态为 COMPLETED/FAILED
        - 记录执行结果
        - 结算预算
        """
        pass
```

#### 3.1.2 Skill API 回调端点
```python
# packages/opc-core/src/opc_core/api/skill_api.py

@router.post("/skill/task/{task_id}/complete")
async def complete_task(
    task_id: str,
    request: TaskCompleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Agent 完成任务回调
    由 opc-bridge-v2 Skill 调用
    """
    pass

@router.post("/skill/task/{task_id}/update")
async def update_task_progress(
    task_id: str,
    request: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Agent 进度更新回调
    """
    pass
```

#### 3.1.3 Employee Service 完善
```python
# packages/opc-core/src/opc_core/services/employee_service.py

class EmployeeService:
    """员工业务逻辑"""
    
    async def hire_employee(
        self,
        name: str,
        position_title: str,
        monthly_budget: int
    ) -> Employee:
        """雇佣新员工"""
        pass
    
    async def bind_agent(
        self,
        employee_id: str,
        agent_id: str
    ) -> bool:
        """绑定 Agent 到员工"""
        pass
```

### 3.3 对外接口 (更新后)
```python
# Core 层对外暴露的 REST API

# Tasks API
POST   /api/tasks              # 创建任务
GET    /api/tasks/{id}         # 获取任务详情
POST   /api/tasks/{id}/assign  # 分配任务 (同步返回结果)
GET    /api/tasks              # 列表查询

# Skill API (已移除 - Phase 2 架构变更)
# ❌ POST /api/skill/task/{id}/complete  (不再需要)
# ❌ POST /api/skill/task/{id}/update   (不再需要)
# 改为内部 ResponseParser 解析

# Employees API
POST   /api/employees         # 雇佣员工
GET    /api/employees/{id}    # 获取员工详情
POST   /api/employees/{id}/bind  # 绑定 Agent
```
```python
# Core 层对外暴露的 REST API

# Tasks API
POST   /api/tasks              # 创建任务
GET    /api/tasks/{id}         # 获取任务详情
POST   /api/tasks/{id}/assign  # 分配任务
GET    /api/tasks              # 列表查询

# Skill API (Agent 回调)
POST   /api/skill/task/{id}/complete  # 任务完成
POST   /api/skill/task/{id}/update   # 进度更新

# Employees API
POST   /api/employees         # 雇佣员工
GET    /api/employees/{id}    # 获取员工详情
POST   /api/employees/{id}/bind  # 绑定 Agent
```

### 3.3 独立测试
```bash
cd packages/opc-core
# 使用 Mock 测试，不依赖真实 OpenClaw
pytest tests/unit/ -v  # 需要 30+ tests passing
```

**测试重点**:
- Task 状态流转测试
- Employee 增删改查
- Skill API 回调处理（Mock）

**验收标准**:
- [ ] 30+ 单元测试通过
- [ ] Mock 覆盖 OpenClaw 调用
- [ ] API 文档与实际一致

---

## Phase 4: UI 层 - 用户界面

**状态**: 🚧 待完善 (需适配 Phase 3 同步 API)  
**职责**: Vue3 前端，调用 Core API

### ⚠️ Phase 2 架构变更对 Phase 4 的影响

**原设计**: 任务分配是异步操作，需要轮询或 WebSocket 等待回调  
**新设计**: 任务分配是**同步操作**，`POST /api/tasks/{id}/assign` 直接返回结果

**UI 需调整**:
1. **任务分配按钮**: 显示 loading，等待同步响应
2. **任务状态展示**: 分配后立即显示 completed/failed (无需轮询)
3. **错误处理**: 直接显示解析失败等错误信息

### 4.1 功能开发

#### 4.1.1 任务管理页面
```javascript
// packages/opc-ui/src/views/TasksView.vue

// 功能列表:
- 创建任务表单 (标题、描述、预算、选择员工)
- 任务列表展示 (状态、员工、创建时间)
- 任务详情页 (状态流转、执行日志)
- 任务筛选 (按状态、员工、时间)
```

#### 4.1.2 员工管理页面
```javascript
// packages/opc-ui/src/views/EmployeesView.vue

// 功能列表:
- 员工列表展示
- 雇佣新员工
- 绑定/更换 Agent
- 员工详情 (任务统计、预算使用)
```

#### 4.1.3 API 客户端封装
```javascript
// packages/opc-ui/src/api/tasks.js

export const taskApi = {
  create: (data) => api.post('/api/tasks', data),
  get: (id) => api.get(`/api/tasks/${id}`),
  assign: (id, employeeId) => api.post(`/api/tasks/${id}/assign`, { employee_id: employeeId }),
  list: (params) => api.get('/api/tasks', { params }),
}

// packages/opc-ui/src/api/employees.js
export const employeeApi = {
  create: (data) => api.post('/api/employees', data),
  get: (id) => api.get(`/api/employees/${id}`),
  bind: (id, agentId) => api.post(`/api/employees/${id}/bind`, { agent_id: agentId }),
  list: () => api.get('/api/employees'),
}
```

### 4.2 对外接口
```
UI 层不对外暴露接口，而是调用 Core API
```

### 4.3 独立测试
```bash
cd packages/opc-ui
npm run test  # 需要 35 tests passing
```

**测试重点**:
- Store (Pinia) 测试
- API 客户端测试
- 组件单元测试

**验收标准**:
- [ ] 35 个测试通过
- [ ] 页面能正常渲染
- [ ] API 调用正确

---

## Phase 5: 集成调试 - 端到端验证

**状态**: 🚧 待进行 (需基于新架构)  
**职责**: 验证四个模块协同工作

### ⚠️ Phase 2 架构变更对 Phase 5 的影响

**原集成测试重点**:
- HTTP 回调端点是否正常工作
- 异步状态流转是否正确
- WebSocket/轮询是否及时

**新集成测试重点**:
- CLI 命令执行是否正常
- `ResponseParser.parse()` 是否正确提取数据
- 同步任务分配流程是否完整
- 错误解析场景（Agent 未返回 OPC-REPORT）

### 5.1 集成步骤 (更新后)

#### Step 1: Database + Core 集成
```bash
# 启动 Core API，使用真实 Database
cd packages/opc-core
python -c "from opc_core import create_app; import uvicorn; uvicorn.run(create_app(), host='0.0.0.0', port=8000)"

# 测试 API
curl -X POST "http://localhost:8000/api/employees" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试员工", "position_title": "测试岗位", "monthly_budget": 1000}'
```

#### Step 2: Core + OpenClaw 集成 (关键)
```bash
# 配置 OpenClaw CLI (无需 HTTP 连接)
export OPENCLAW_BIN="/usr/bin/openclaw"

# 测试任务分配 (同步模式)
curl -X POST "http://localhost:8000/api/tasks/{task_id}/assign" \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "emp_xxx"}'

# 响应应包含:
# - task.status: completed/failed/needs_revision
# - task.result.summary: Agent 总结
# - task.result.tokens_used: Token 消耗
```

#### Step 3: Core + UI 集成
```bash
# 配置 UI API 地址
# packages/opc-ui/.env.local
VITE_API_BASE_URL=http://localhost:8000

# 启动前端
cd packages/opc-ui
npm run dev
```

#### Step 4: 完整端到端测试 (更新后)
```
新流程:
1. Dashboard 创建员工
2. Dashboard 绑定 Agent
3. Dashboard 创建任务
4. Dashboard 点击"分配任务"
   ↓ 同步等待
5. Core 调用 TaskCaller.assign_task()
   ↓ CLI 执行
6. Agent 收到任务并执行
   ↓ 回复消息
7. Core 调用 ResponseParser.parse()
   ↓ 解析 OPC-REPORT
8. Core 更新任务状态
   ↓ 同步返回
9. Dashboard 立即显示任务完成

注意: 第 4-9 步是同步的，无需轮询
```

### 5.2 集成测试脚本 (更新后)
```bash
# scripts/e2e_test_v2.sh
# 基于 ResponseParser 的端到端测试

echo "=== E2E Test: Task Assignment with ResponseParser ==="

# 1. 创建员工
EMPLOYEE_ID=$(curl -s -X POST ... | jq -r '.id')

# 2. 绑定 Agent
curl -s -X POST "/api/employees/${EMPLOYEE_ID}/bind" \
  -d '{"agent_id": "opc-test-worker"}'

# 3. 创建任务
TASK_ID=$(curl -s -X POST ... | jq -r '.id')

# 4. 分配任务 (同步)
RESULT=$(curl -s -X POST "/api/tasks/${TASK_ID}/assign" \
  -d "{\"employee_id\": \"${EMPLOYEE_ID}\"}")

# 5. 验证结果 (立即返回，无需等待)
echo "Task Status: $(echo $RESULT | jq -r '.status')"
echo "Result Summary: $(echo $RESULT | jq -r '.result.summary')"
echo "Tokens Used: $(echo $RESULT | jq -r '.result.tokens_used')"

# 验证点:
# - status 应为 completed/failed/needs_revision
# - result.summary 不为空
# - result.tokens_used > 0
```
```bash
# 启动 Core API，使用真实 Database
cd packages/opc-core
python -c "from opc_core import create_app; import uvicorn; uvicorn.run(create_app(), host='0.0.0.0', port=8000)"

# 测试 API
curl -X POST "http://localhost:8000/api/employees" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试员工", "position_title": "测试岗位", "monthly_budget": 1000}'
```

#### Step 2: Core + OpenClaw 集成
```bash
# 配置 OpenClaw 连接
export OPENCLAW_BASE_URL="http://localhost:8080"
export OPENCLAW_API_KEY="..."

# 测试 Agent 绑定和任务分配
```

#### Step 3: Core + UI 集成
```bash
# 配置 UI API 地址
# packages/opc-ui/.env.local
VITE_API_BASE_URL=http://localhost:8000

# 启动前端
cd packages/opc-ui
npm run dev
```

#### Step 4: 完整端到端测试
```
完整流程:
1. Dashboard 创建员工
2. Dashboard 绑定 Agent
3. Dashboard 创建任务
4. Core 分配任务给 Agent
5. Agent 收到任务并执行
6. Agent 回调报告结果
7. Dashboard 显示任务完成
```

### 5.2 集成测试脚本
```bash
# scripts/e2e_test.sh
# 自动化端到端测试
```

### 5.3 验收标准
- [ ] 能从 Dashboard 完整走通一次任务流程
- [ ] 任务状态实时同步
- [ ] 预算正确结算
- [ ] 错误场景有友好提示

---

## 开发顺序建议

```
Week 1:
  Day 1-2: Phase 2 - OpenClaw 层完善 + 测试
  Day 3-4: Phase 3 - Core 层 Task/Employee Service + 测试
  Day 5:   Phase 3 - Core 层 Skill API + 测试

Week 2:
  Day 1-2: Phase 4 - UI 层任务管理页面
  Day 3-4: Phase 4 - UI 层员工管理页面 + API 对接
  Day 5:   Phase 5 - 集成调试

Week 3 (预留):
  Bug 修复、文档更新、性能优化
```

---

## 接口契约定义

### Task 数据结构 (更新后)
```python
class TaskStatus(str, Enum):
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    NEEDS_REVISION = "needs_revision"  # 需要返工
    NEEDS_REVIEW = "needs_review"      # 需人工检查 (解析失败)

class Task(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    employee_id: str
    budget: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    result: dict | None      # 包含 summary, tokens_used, result_files
```

### Agent 回调数据结构 (已废弃)
```python
# ❌ 以下结构不再使用 (Phase 2 架构变更)
# class TaskCompleteRequest(BaseModel): ...
# class TaskUpdateRequest(BaseModel): ...

# ✅ 新结构: Agent 回复中的 OPC-REPORT 格式
# 由 ResponseParser 解析为 ParsedReport

class ParsedReport(BaseModel):
    is_valid: bool
    task_id: str | None
    status: str | None       # "completed" | "failed" | "needs_revision"
    tokens_used: int | None
    summary: str | None
    result_files: list[str]
    errors: list[str]
```

---

## 风险与应对

| 风险 | 可能性 | 影响 | 应对 |
|------|--------|------|------|
| OpenClaw API 不稳定 | 中 | 高 | 添加重试机制、降级处理 |
| Agent 回调延迟 | 中 | 中 | WebSocket 推送、轮询兜底 |
| 数据库性能瓶颈 | 低 | 中 | 查询优化、缓存 |
| UI/UX 调整需求 | 高 | 低 | 预留重构时间 |

---

## 附录: 开发检查清单

### 每个模块开发前
- [ ] 明确对外接口
- [ ] 定义数据结构
- [ ] 编写测试用例

### 每个模块开发后
- [ ] 单元测试通过
- [ ] 代码格式化 (black/ruff)
- [ ] 接口文档更新

### 集成阶段
- [ ] 模块间接口匹配
- [ ] 端到端流程验证
- [ ] 错误场景测试
- [ ] 性能基准测试

---

## 附录: Phase 2 架构变更总结

### 变更原因

1. **简化架构**: 移除 HTTP 服务端点，减少组件依赖
2. **可靠性**: CLI 模式比 HTTP 更稳定，无需处理网络超时
3. **同步流程**: 短任务可直接同步完成，无需复杂状态管理
4. **版本统一**: Skill 版本与主包版本对齐

### 变更影响矩阵

| 模块 | 影响程度 | 需修改内容 |
|------|----------|------------|
| Phase 3 TaskService | 🔴 高 | `assign_task()` 改为同步解析 |
| Phase 3 Skill API | 🔴 高 | 可移除 HTTP 端点 |
| Phase 3 Budget | 🟡 中 | 结算时机改为同步 |
| Phase 4 UI | 🟡 中 | 分配改为同步等待 |
| Phase 5 E2E | 🟡 中 | 测试脚本改为验证解析 |
| Phase 1 Database | 🟢 低 | Task 模型新增 needs_review 状态 |

### 向后兼容性

- **Agent**: 无需修改，遵循 SKILL.md 即可
- **Database**: 新增状态枚举值，需迁移
- **API**: `/api/skill/*` 端点可废弃

### 开发优先级建议 (更新后)

```
Week 1 (调整后):
  Day 1: Phase 3 - TaskService 适配 ResponseParser
  Day 2: Phase 3 - 移除/修改 Skill API，更新状态流转
  Day 3: Phase 3 - 测试与 Budget 结算适配
  Day 4: Phase 4 - UI 同步分配流程
  Day 5: Phase 4 - UI 状态展示更新

Week 2:
  Day 1-2: Phase 5 - 新架构集成测试
  Day 3:   文档更新
  Day 4-5: Bug 修复与优化
```

### 关键类引用

```python
# Phase 3 开发时需使用
from opc_openclaw import (
    TaskCaller,        # 分配任务
    TaskAssignment,    # 任务数据
    TaskResponse,      # 任务响应
    ResponseParser,    # ★ 新增: 解析 OPC-REPORT
    ParsedReport,      # ★ 新增: 解析结果
)

# 使用示例
response = await TaskCaller().assign_task(assignment)
report = ResponseParser().parse(response.content)

if report.is_valid:
    task.status = report.status
    task.result = {
        "summary": report.summary,
        "tokens_used": report.tokens_used,
        "result_files": report.result_files
    }
else:
    task.status = "needs_review"
    task.result = {"errors": report.errors}
```

---

**计划版本**: v0.4.1  
**最后更新**: 2026-03-25 (标记 Phase 2 架构变更影响)  
**文档维护**: 本计划随开发进度更新
