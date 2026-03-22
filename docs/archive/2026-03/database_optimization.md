# Database Performance Optimization

## 分析发现的问题

### 1. N+1 查询问题

**位置**: `workflow_detail_service.py` - `_serialize_step()` 方法

**问题代码**:
```python
def _serialize_step(self, step: WorkflowStep, viewer_id: str) -> Dict:
    assignee = self.db.query(Agent).filter(Agent.id == step.assignee_id).first()
    # ...
```

**影响**: 当工作流有N个步骤时，会执行N次额外的Agent查询。

**解决方案**: 使用 joinedload 预加载所有assignee信息。

### 2. 重复COUNT查询

**位置**: `workflow_detail_service.py` - `_serialize_workflow()` 方法

**问题代码**:
```python
total_steps = self.db.query(WorkflowStep).filter(
    WorkflowStep.workflow_id == workflow.id
).count()

completed_steps = self.db.query(WorkflowStep).filter(
    WorkflowStep.workflow_id == workflow.id,
    WorkflowStep.status == "completed"
).count()
```

**解决方案**: 使用单个聚合查询或缓存。

### 3. 缺少数据库索引

**需要添加的索引**:

| 表 | 字段 | 原因 |
|----|------|------|
| workflow_steps | workflow_id | 频繁按工作流查询步骤 |
| workflow_steps | assignee_id | 频繁按员工查询待办 |
| workflow_steps | status | 状态筛选 |
| workflow_history | workflow_id | 历史记录查询 |
| workflow_rework_records | workflow_id | 返工记录查询 |
| agents | position_level | Partner查询 |
| agents | is_bound | 绑定状态筛选 |
| tasks | agent_id | 任务查询 |
| tasks | status | 状态筛选 |
| async_messages | recipient_id | 消息收件箱 |

### 4. 大表查询缺少分页

**问题接口**:
- `GET /api/workflows` - 获取所有工作流（需要分页）
- `GET /api/agents/{id}/tasks` - 获取员工所有任务
- `GET /api/async-messages` - 消息列表

---

## 优化实施计划

### Phase 1: 添加数据库索引

```sql
-- workflow_steps 索引
CREATE INDEX idx_workflow_steps_workflow_id ON workflow_steps(workflow_id);
CREATE INDEX idx_workflow_steps_assignee_id ON workflow_steps(assignee_id);
CREATE INDEX idx_workflow_steps_status ON workflow_steps(status);
CREATE INDEX idx_workflow_steps_workflow_status ON workflow_steps(workflow_id, status);

-- workflow_history 索引
CREATE INDEX idx_workflow_history_workflow_id ON workflow_history(workflow_id);
CREATE INDEX idx_workflow_history_created_at ON workflow_history(created_at);

-- workflow_rework_records 索引
CREATE INDEX idx_workflow_rework_workflow_id ON workflow_rework_records(workflow_id);

-- agents 索引
CREATE INDEX idx_agents_position_level ON agents(position_level);
CREATE INDEX idx_agents_is_bound ON agents(is_bound);

-- tasks 索引
CREATE INDEX idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_agent_status ON tasks(agent_id, status);

-- async_messages 索引
CREATE INDEX idx_async_messages_recipient ON async_messages(recipient_id);
CREATE INDEX idx_async_messages_status ON async_messages(status);
CREATE INDEX idx_async_messages_recipient_status ON async_messages(recipient_id, status);
```

### Phase 2: 优化查询（N+1修复）

### Phase 3: 添加分页支持

### Phase 4: 添加查询缓存

---

## 预期性能提升

| 优化项 | 当前 | 优化后 | 提升 |
|--------|------|--------|------|
| 工作流详情加载 | ~500ms (20步骤) | ~100ms | 5x |
| 员工列表 | ~200ms (50员工) | ~50ms | 4x |
| 任务列表 | ~300ms | ~80ms | 3.75x |
| 消息收件箱 | ~250ms | ~60ms | 4x |
