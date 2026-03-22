# OPC 任务-工作流统一架构设计 v2.0

## 核心理念

**每个任务都是一个工作流实例**
- 简单任务 = 单步骤工作流（简化版）
- 复杂任务 = 多步骤工作流
- 统一的状态流转、分配机制、监控体系

---

## 架构变化

### 1. 统一数据模型

```
┌─────────────────────────────────────────────────────────────┐
│                      Task (任务)                             │
├─────────────────────────────────────────────────────────────┤
│ id, title, description, created_by                          │
│ status: pending → assigned → in_progress → completed/failed │
│ total_budget, actual_cost                                   │
│ workflow_id → WorkflowDefinition                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              WorkflowInstance (工作流实例)                    │
├─────────────────────────────────────────────────────────────┤
│ task_id, definition_id                                      │
│ current_step_index                                          │
│ overall_status                                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│               WorkflowStep (工作流步骤)                       │
├─────────────────────────────────────────────────────────────┤
│ instance_id, step_index, step_type                          │
│ assigned_agent_id                                           │
│ status: pending → assigned → running → completed/failed     │
│ input_data, output_data                                     │
│ started_at, completed_at                                    │
│ cost_tokens, modified_by (记录修改者)                        │
└─────────────────────────────────────────────────────────────┘
```

### 2. 状态流转

```
简单任务（单步骤）:
 pending → assigned → in_progress → completed
                              ↘ failed

复杂任务（多步骤）:
 pending → step1_assigned → step1_in_progress → step1_completed
                                       ↘ step1_failed
 → step2_assigned → step2_in_progress → step2_completed
                                       ↘ step2_failed
 → ... → all_completed / any_failed
```

---

## Agent 任务状态更新 API

### 核心设计原则

**Agent 主动推送状态，而非被动解析**

每个 Agent 在收到任务时，会获得一个 `task_token`，用于调用状态更新 API。

### API 设计

```python
# Agent 开始执行任务
POST /api/agent-task/start
Headers: X-Task-Token: <task_token>
Body: {
    "step_id": "step_xxx",      # 步骤ID
    "agent_id": "agent_xxx",    # Agent ID（验证用）
}
Response: {
    "success": true,
    "step_status": "in_progress",
    "started_at": "2026-03-23T10:00:00Z"
}

# Agent 更新执行进度（可选，用于长时间任务）
POST /api/agent-task/progress
Headers: X-Task-Token: <task_token>
Body: {
    "step_id": "step_xxx",
    "progress_percent": 50,     # 0-100
    "progress_note": "正在处理第2/4个文件"
}

# Agent 完成任务步骤
POST /api/agent-task/complete
Headers: X-Task-Token: <task_token>
Body: {
    "step_id": "step_xxx",
    "result_summary": "任务完成，生成报告 report.md",
    "output_path": "/workspace/tasks/xxx/output.md",
    "output_data": {             # 结构化输出（可选）
        "files_created": [...],
        "records_updated": 5
    }
}
Response: {
    "success": true,
    "step_status": "completed",
    "next_step": {               # 如果有下一步
        "step_id": "step_yyy",
        "step_type": "review",
        "assigned_agent_id": "agent_zzz"
    } / null
}

# Agent 报告失败
POST /api/agent-task/fail
Headers: X-Task-Token: <task_token>
Body: {
    "step_id": "step_xxx",
    "error_reason": "无法访问数据库",
    "error_details": "Connection timeout after 30s"
}
```

### Task Token 安全机制

```python
class TaskToken:
    """
    一次性任务令牌，用于 Agent 身份验证
    """
    token: str              # UUID
    step_id: str            # 绑定的步骤
    agent_id: str           # 绑定的Agent
    expires_at: datetime    # 过期时间（默认24小时）
    used_at: datetime       # 首次使用时间
    is_revoked: bool        # 是否已撤销
```

---

## 任务分配机制

### 方式一：手动分配

```
用户创建任务 → 选择"手动分配" → 选择Agent → 立即发送任务消息
```

### 方式二：Partner 预任务分配

```
用户创建任务 → 选择"让Partner分配" → 
创建预任务"任务分配" → 发送给 Partner → 
Partner 调用 API 写入分配结果 → 系统记录修改者
```

**Partner 分配任务 API：**

```python
# Partner 分配任务给指定 Agent
POST /api/task-assignment/assign-by-partner
Headers: X-Task-Token: <task_token>  # 预任务的token
Body: {
    "step_id": "step_xxx",
    "assigned_agent_id": "agent_yyy",
    "assignment_note": "由Partner分配：小王擅长数据分析"
}
# 系统记录：modified_by = "partner_agent_id"
```

---

## Token 消耗监控（系统自动）

### 设计原则

**Agent 不报告，系统自己监控**

### 实现方案

```python
class TokenMonitor:
    """
    通过 OpenClaw session_status API 监控实际 token 消耗
    """
    
    def monitor_task_execution(self, agent_id: str, task_step_id: str):
        """
        定期查询 Agent 会话状态，获取 token 消耗
        """
        while task_running:
            status = openclaw.session_status(agent_id=agent_id)
            
            # 更新步骤实际消耗
            step = db.query(WorkflowStep).get(task_step_id)
            step.cost_tokens = status.total_tokens
            step.cost_estimated = False  # 实际值
            
            db.commit()
            time.sleep(30)  # 每30秒更新一次
    
    def estimate_tokens(self, task_type: str, complexity: str) -> int:
        """
        对于新任务，先给预算估计值
        """
        estimates = {
            "database_query": {"simple": 500, "medium": 1500, "complex": 3000},
            "file_processing": {"simple": 800, "medium": 2000, "complex": 5000},
            "research": {"simple": 2000, "medium": 5000, "complex": 10000},
            ...
        }
        return estimates.get(task_type, {}).get(complexity, 1000)
```

### Token 记录结构

```python
class WorkflowStep:
    # 预算（创建时设置）
    budget_tokens: int          # 预算token数
    budget_estimated: bool      # 是否为估计值
    
    # 实际消耗（执行中更新）
    cost_tokens: int            # 实际消耗token数
    cost_estimated: bool        # false = 实际监控值
    
    # 监控记录
    token_snapshots: List[{     # 执行过程中的快照
        "timestamp": "...",
        "tokens": 1234,
        "source": "session_status"
    }]
```

---

## 前端界面整合

### 任务页面改版

```
┌─────────────────────────────────────────────────────────────┐
│ 任务列表                    [+ 创建任务]                     │
├─────────────────────────────────────────────────────────────┤
│ 筛选: [全部▼] [状态▼] [类型▼]        搜索: [________] 🔍    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📋 优化数据库查询性能                    [进行中]          │
│  ├─ 类型: 复杂工作流                                        │
│  ├─ 步骤: 分析(✓) → 优化(▶) → 测试(○) → 部署(○)           │
│  ├─ 当前: 优化阶段 @实习生小李                              │
│  └─ 预算: 3000/5000 tokens                                │
│                                                             │
│  📄 生成月度报告                          [待分配]          │
│  ├─ 类型: 简单任务                                          │
│  ├─ 分配: Partner 待分配                                    │
│  └─ 预算: 2000 tokens (预估)                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 创建任务流程

```
[选择任务类型]
    ├── 简单任务 → 选择模板 → 填写详情 → 选择分配方式
    │                                    ├── 手动分配 → 选Agent → 创建
    │                                    └── Partner分配 → 创建预任务
    │
    └── 复杂工作流 → 选择模板 → 配置步骤 → 每步分配方式
                                           ├── 手动指定Agent
                                           ├── Partner分配
                                           └── 按技能自动匹配
```

### 员工详情页（简化）

```
┌─────────────────────────────────────────────────────────────┐
│ 👤 实习生小李                                               │
├─────────────────────────────────────────────────────────────┤
│  概览  |  任务历史  |  技能  |  日志                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 任务统计                                                │
│  本月任务: 12    完成: 10    进行中: 2                      │
│  平均耗时: 2.3h   Token效率: 85%                            │
│                                                             │
│  📋 最近任务                                                │
│  ├─ 数据分析报告          [完成]  3/20  消耗: 1500 tokens  │
│  ├─ 代码重构              [完成]  3/18  消耗: 2800 tokens  │
│  └─ API文档编写           [进行中] 3/22  已用: 800 tokens  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 数据库迁移计划

### 阶段一：新增表（向后兼容）

```sql
-- 工作流实例表
CREATE TABLE workflow_instances (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES tasks(id),
    definition_id TEXT,
    current_step_index INTEGER DEFAULT 0,
    overall_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 工作流步骤表（新增 modified_by 字段）
CREATE TABLE workflow_steps (
    id TEXT PRIMARY KEY,
    instance_id TEXT REFERENCES workflow_instances(id),
    step_index INTEGER,
    step_type TEXT,
    assigned_agent_id TEXT REFERENCES agents(id),
    status TEXT DEFAULT 'pending',
    input_data TEXT,
    output_data TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    budget_tokens INTEGER,
    budget_estimated BOOLEAN DEFAULT TRUE,
    cost_tokens INTEGER DEFAULT 0,
    cost_estimated BOOLEAN DEFAULT TRUE,
    modified_by TEXT,              -- 新增：记录修改者
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 任务令牌表
CREATE TABLE task_tokens (
    token TEXT PRIMARY KEY,
    step_id TEXT REFERENCES workflow_steps(id),
    agent_id TEXT REFERENCES agents(id),
    expires_at TIMESTAMP,
    used_at TIMESTAMP,
    is_revoked BOOLEAN DEFAULT FALSE
);
```

### 阶段二：数据迁移

```python
# 将现有简单任务迁移为单步骤工作流
def migrate_existing_tasks():
    for task in db.query(Task).all():
        # 创建工作流实例
        instance = WorkflowInstance(
            task_id=task.id,
            definition_id="simple_task_v1",
            overall_status=task.status
        )
        db.add(instance)
        
        # 创建单步骤
        step = WorkflowStep(
            instance_id=instance.id,
            step_index=0,
            step_type="execution",
            assigned_agent_id=task.assigned_agent_id,
            status=task.execution_status or task.status,
            budget_tokens=task.estimated_tokens or 1000,
            cost_tokens=task.actual_tokens_output or 0
        )
        db.add(step)
```

### 阶段三：清理旧字段（可选）

---

## 实施优先级

1. **P0 - 核心基础**
   - [ ] Task Token 机制
   - [ ] Agent 状态更新 API
   - [ ] Token 自动监控

2. **P1 - 任务分配**
   - [ ] 手动分配流程
   - [ ] Partner 预任务分配
   - [ ] 分配记录追踪（modified_by）

3. **P2 - 前端整合**
   - [ ] 任务页面改版
   - [ ] 创建工作流优化
   - [ ] 员工详情页简化

4. **P3 - 数据迁移**
   - [ ] 现有任务迁移
   - [ ] 旧代码清理

---

*设计时间: 2026-03-23*
*版本: v2.0*
