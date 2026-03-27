# v0.4.6 子功能1: 后端数据模型扩展

## 概述

扩展工作流数据模型，支持为每个步骤配置执行手册，包括手册内容、输入要求和输出交付物。

## 技术决策

### 设计变更：采用标准任务手册路径

**原设计**:
- 路径: `data/manuals/workflows/{wf_id}/step_{N}.md`
- 需要新增 `step_manual_path` 字段到 TaskAssignment

**最终设计**:
- 路径: `data/manuals/tasks/{task_id}.md`
- **无需修改** TaskAssignment，复用现有 `task_manual_path`

**变更原因**:
1. 统一性 - 工作流步骤和普通任务使用相同的手册机制
2. 简单性 - 无需修改 `_build_task_assignment`，无需添加新字段
3. 兼容性 - 完全向后兼容，不影响现有代码
4. 可维护性 - 减少代码复杂度

## 数据模型

### WorkflowStepConfig (Dataclass)

```python
@dataclass
class WorkflowStepConfig:
    employee_id: str                    # 执行员工ID
    title: str                          # 步骤标题
    description: str = ""               # 步骤描述
    estimated_cost: float = 100.0       # 预估成本
    
    # v0.4.6 新增字段
    manual_content: Optional[str] = None      # 执行手册内容
    input_requirements: Optional[str] = None  # 输入要求
    output_deliverables: Optional[str] = None # 输出交付物
```

### WorkflowStep (API Model)

```python
class WorkflowStep(BaseModel):
    employee_id: str
    title: str
    description: str = ""
    estimated_cost: float = 100.0
    
    # v0.4.6 新增
    manual_content: Optional[str] = None
    input_requirements: Optional[str] = None
    output_deliverables: Optional[str] = None
```

## 实现细节

### 1. 手册文件创建

```python
def _write_task_manual_file(task_id: str, step: WorkflowStepConfig) -> str:
    """
    写入任务手册文件 (v0.4.6)
    使用标准路径: data/manuals/tasks/{task_id}.md
    """
    tasks_dir = MANUALS_DIR / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    manual_path = tasks_dir / f"{task_id}.md"
    
    content = f"""# {step.title} - 任务手册

## 执行手册
{step.manual_content or "无"}

## 输入要求
{step.input_requirements or "无特殊要求"}

## 输出交付物
{step.output_deliverables or "按任务描述执行"}
"""
    
    manual_path.write_text(content, encoding="utf-8")
    return str(manual_path)
```

### 2. 工作流创建时调用

```python
async def create_workflow(self, ...):
    for i, step in enumerate(steps):
        # 创建任务
        task = Task(...)
        
        # v0.4.6: 为每个步骤创建手册文件
        if step.manual_content:
            manual_path = _write_task_manual_file(task.id, step)
            print(f"[DEBUG] 创建步骤手册: {manual_path}")
        
        # 设置 execution_context 包含手册信息
        task.execution_context = json.dumps({
            "step_index": i,
            "step_manual": {
                "title": step.title,
                "manual_content": step.manual_content,
                "input_requirements": step.input_requirements,
                "output_deliverables": step.output_deliverables,
            }
        })
```

## 数据流

```
创建工作流
    ↓
为每个步骤:
    - 创建 Task (生成 task_id)
    - 调用 _write_task_manual_file(task_id, step)
    - 手册写入: data/manuals/tasks/{task_id}.md
    - execution_context 存储手册信息
    ↓
任务分配 → _build_task_assignment
    - 使用标准路径: /home/user/opc/manuals/tasks/{task.id}.md
    - 无需额外处理，现有逻辑复用
    ↓
Agent 通过路径读取手册 → 执行
```

## Partner Prompt 更新

### 系统提示词增强

```
为每个步骤生成:
- manual_content: 详细的执行手册（Markdown格式，包含步骤目标、执行方法、注意事项）
- input_requirements: 该步骤需要什么输入数据/资料
- output_deliverables: 该步骤必须交付什么成果物
```

### 响应格式要求

```json
{
  "name": "工作流名称",
  "description": "工作流描述",
  "steps": [
    {
      "employee_id": "emp-xxx",
      "title": "步骤标题",
      "description": "步骤描述",
      "estimated_cost": 100,
      "manual_content": "## 执行手册\n...",
      "input_requirements": "需要...",
      "output_deliverables": "交付..."
    }
  ]
}
```

## 测试

### 测试文件
`test_subfeature_1.py`

### 测试用例

| 测试 | 描述 | 验证点 |
|------|------|--------|
| 数据模型扩展 | WorkflowStepConfig支持新字段 | manual_content, input_requirements, output_deliverables |
| 手册文件创建 | 标准路径存储 | 路径格式: data/manuals/tasks/{task_id}.md |
| TaskService使用标准路径 | 无需修改_build_task_assignment | 复用现有task_manual_path逻辑 |
| Partner Prompt生成 | AI自动生成手册 | 响应包含所有新字段 |

### 运行测试

```bash
cd /root/.openclaw/workspace/openclaw-opc
python3 test_subfeature_1.py
```

### 预期输出

```
✅ 数据模型扩展 测试通过
✅ 任务手册文件创建（标准路径） 测试通过
✅ TaskService 使用标准路径 测试通过
✅ Partner Prompt 测试通过

总计: 4/4 通过
🎉 子功能1测试全部通过！
```

## 向后兼容性

- ✅ 现有工作流不受影响（不传手册字段则不创建文件）
- ✅ 现有任务不受影响
- ✅ 无数据库迁移需求
- ✅ 标准路径与现有任务手册兼容

## 相关文件

| 文件 | 说明 |
|------|------|
| `workflow_service.py` | `_write_task_manual_file`函数，手册创建逻辑 |
| `workflows.py` | `WorkflowStep` API模型 |
| `partner_service.py` | `WorkflowStepAssist` dataclass，Prompt更新 |
| `partner.py` | `WorkflowStepAssistResponse` API模型 |
| `test_subfeature_1.py` | 测试脚本 |

---

*文档版本: v0.4.6*  
*最后更新: 2026-03-28*
