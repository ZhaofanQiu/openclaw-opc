# v0.4.6 子功能3: 工作流执行引擎

## 概述

增强工作流执行引擎，实现步骤间的数据自动传递，确保Agent在执行每个步骤时都能获取完整的上下文信息（包括前序输出、输入要求、输出交付物）。

## 核心目标

1. **前序输出传递** - 将前一步骤的输出传递给下一步骤
2. **步骤上下文构建** - 为每个步骤构建完整的执行上下文
3. **任务描述增强** - 在任务描述中嵌入步骤要求和交付物说明
4. **数据格式统一** - 使用JSON格式存储和传递结构化数据

## 关键方法

### 1. `_get_previous_output` - 获取前序输出

```python
async def _get_previous_output(self, current_task: Task) -> Optional[Dict]:
    """
    获取前一步骤的输出数据
    
    Returns:
        {
            "step_index": 0,
            "step_title": "步骤标题",
            "employee_id": "emp-001",
            "employee_name": "员工姓名",
            "output_summary": "输出摘要",
            "structured_output": {...},
            "deliverables": ["交付物1", "交付物2"],
            "metadata": {
                "tokens_used": 1500,
                "completed_at": "2026-03-28T01:00:00Z"
            }
        }
    """
    if current_task.step_index == 0:
        return None
    
    # 查找前一步的任务
    prev_task = await self._find_previous_task(current_task)
    if not prev_task:
        return None
    
    # 提取输出数据
    output_data = json.loads(prev_task.output_data) if prev_task.output_data else {}
    
    return {
        "step_index": prev_task.step_index,
        "step_title": prev_task.title,
        "employee_id": prev_task.assigned_to,
        "employee_name": prev_employee.name if prev_employee else "未知",
        "output_summary": output_data.get("summary", ""),
        "structured_output": output_data.get("structured_output", {}),
        "deliverables": output_data.get("deliverables", []),
        "metadata": {
            "tokens_used": output_data.get("tokens_used", 0),
            "completed_at": prev_task.completed_at.isoformat() if prev_task.completed_at else None
        }
    }
```

### 2. `_get_step_context` - 获取步骤上下文

```python
def _get_step_context(self, task: Task) -> Dict:
    """
    从 execution_context 解析步骤手册信息
    
    Returns:
        {
            "manual_content": "执行手册内容",
            "input_requirements": "输入要求",
            "output_deliverables": "输出交付物"
        }
    """
    if not task.execution_context:
        return {}
    
    try:
        ctx = json.loads(task.execution_context)
        step_manual = ctx.get("step_manual", {})
        return {
            "manual_content": step_manual.get("manual_content", ""),
            "input_requirements": step_manual.get("input_requirements", ""),
            "output_deliverables": step_manual.get("output_deliverables", "")
        }
    except json.JSONDecodeError:
        return {}
```

### 3. `_build_step_description` - 构建步骤描述

```python
def _build_step_description(
    self,
    next_task: Task,
    previous_output: Optional[Dict],
    step_context: Dict
) -> str:
    """
    构建完整的步骤描述
    
    包含:
    - 前序步骤输出
    - 输入要求
    - 输出交付物要求
    
    Returns:
        Markdown格式的步骤描述
    """
    sections = []
    
    # 前序步骤输出
    if previous_output:
        sections.append("## 前序步骤输出")
        sections.append(f"**步骤 {previous_output['step_index'] + 1}**: {previous_output['step_title']}")
        sections.append(f"**执行者**: {previous_output['employee_name']}")
        
        if previous_output['output_summary']:
            sections.append(f"**输出摘要**: {previous_output['output_summary']}")
        
        # 结构化输出
        structured = previous_output.get('structured_output', {})
        if structured:
            sections.append("**关键数据**:")
            for key, value in structured.items():
                sections.append(f"  - {key}: {value}")
        
        # 交付物
        deliverables = previous_output.get('deliverables', [])
        if deliverables:
            sections.append("**交付物**:")
            for d in deliverables:
                sections.append(f"  - {d}")
        
        sections.append("")  # 空行
    
    # 输入要求
    if step_context.get('input_requirements'):
        sections.append("## 输入要求")
        sections.append(step_context['input_requirements'])
        sections.append("")
    
    # 输出交付物
    if step_context.get('output_deliverables'):
        sections.append("## 输出交付物要求")
        sections.append(step_context['output_deliverables'])
        sections.append("")
        sections.append("**重要**: 请确保你的 OPC-REPORT 中包含上述交付物。")
    
    return "\n".join(sections)
```

### 4. `_build_initial_step_description` - 构建初始描述

```python
def _build_initial_step_description(
    self,
    step: WorkflowStepConfig,
    initial_input: Dict
) -> str:
    """
    为第一个步骤构建初始描述
    
    Returns:
        Markdown格式的初始步骤描述
    """
    sections = []
    
    # 初始输入
    if initial_input:
        sections.append("## 初始输入")
        for key, value in initial_input.items():
            sections.append(f"- **{key}**: {value}")
        sections.append("")
    
    # 输入要求
    if step.input_requirements:
        sections.append("## 输入要求")
        sections.append(step.input_requirements)
        sections.append("")
    
    # 输出交付物
    if step.output_deliverables:
        sections.append("## 输出交付物要求")
        sections.append(step.output_deliverables)
        sections.append("")
        sections.append("**重要**: 请确保你的 OPC-REPORT 中包含上述交付物。")
    
    return "\n".join(sections)
```

## `_trigger_next_step` 增强

```python
async def _trigger_next_step(self, current_task: Task) -> Optional[Task]:
    """
    触发下一步任务 (v0.4.6 - 增强数据传递)
    """
    # 1. 获取前一步的输出
    previous_output = await self._get_previous_output(current_task)
    
    # 2. 获取下一步的任务
    next_task = await self._get_next_task(current_task)
    if not next_task:
        return None
    
    # 3. 获取下一步的上下文
    step_context = self._get_step_context(next_task)
    
    # 4. 构建步骤描述
    step_description = self._build_step_description(
        next_task, previous_output, step_context
    )
    
    # 5. 准备 previous_outputs 列表
    input_data = json.loads(next_task.input_data) if next_task.input_data else {}
    previous_outputs = input_data.get("previous_outputs", [])
    
    if previous_output:
        previous_outputs.append(previous_output)
    
    # 6. 更新下一步的输入数据
    next_task.set_input_data({
        "workflow_context": {
            "workflow_id": next_task.workflow_id,
            "step_index": next_task.step_index,
            "total_steps": next_task.total_steps,
            "step_title": next_task.title
        },
        "previous_outputs": previous_outputs,
        "current_step_description": step_description
    })
    
    # 7. 更新任务描述（追加步骤描述）
    original_desc = next_task.description or ""
    if step_description:
        next_task.description = f"{original_desc}\n\n{step_description}"
    
    # 8. 保存并触发
    await self.task_repo.update(next_task)
    await self.task_service.assign_task(next_task.id, next_task.assigned_to)
    
    return next_task
```

## `create_workflow` 增强

```python
async def create_workflow(self, ...) -> WorkflowCreationResult:
    """
    创建工作流 (v0.4.6 - 增强初始步骤描述)
    """
    created_tasks = []
    
    for i, step in enumerate(steps):
        # 创建任务
        task = Task(...)
        
        # v0.4.6: 构建初始步骤描述
        initial_step_description = self._build_initial_step_description(
            step, initial_input
        )
        
        # 设置输入数据
        task.set_input_data({
            "workflow_context": {
                "workflow_id": workflow_id,
                "step_index": i,
                "total_steps": len(steps),
                "step_title": step.title
            },
            "initial_input": initial_input,
            "previous_outputs": [],
            "current_step_description": initial_step_description  # v0.4.6
        })
        
        # v0.4.6: 更新任务描述
        if initial_step_description:
            task.description = f"{step.description}\n\n{initial_step_description}"
        
        # ... 保存任务
        
    # 触发第一个任务
    if created_tasks:
        await self.task_service.assign_task(
            created_tasks[0].id, 
            created_tasks[0].assigned_to
        )
```

## 数据流

```
创建工作流
    ↓
为每个步骤创建任务
    - 设置 workflow_context
    - 设置 initial_input
    - 设置 current_step_description (v0.4.6)
    - 更新 description
    - 创建手册文件
    ↓
触发第一个任务
    - Agent收到: 初始输入 + 步骤描述 + 手册路径
    ↓
Agent执行 → 返回 OPC-REPORT
    - output_data: {summary, structured_output, deliverables}
    ↓
on_task_completed 回调
    ↓
_trigger_next_step
    1. 获取前一步输出 (_get_previous_output)
    2. 获取下一步上下文 (_get_step_context)
    3. 构建步骤描述 (_build_step_description)
       - 包含前序输出
       - 包含输入要求
       - 包含输出交付物
    4. 更新下一步输入数据
    5. 更新下一步任务描述
    6. 触发下一步任务
    ↓
Agent执行下一步（收到完整上下文）
    - 前序步骤输出
    - 当前步骤要求
    - 交付物要求
    ↓
... 继续直到完成
```

## Agent 收到的任务消息示例

### 第一个步骤

```markdown
【任务分配】

任务: 内容创作工作流 - Step 1: 选题策划

## 工作流上下文
当前步骤: 1 / 3
工作流ID: wf-abc123

## 任务描述
确定文章选题和方向

## 初始输入
- **goal**: 完成AI趋势分析文章
- **target_length**: 2000字

## 输入要求
项目背景资料、目标受众分析

## 输出交付物要求
选题报告（包含主题、关键词、目标受众）

**重要**: 请确保你的 OPC-REPORT 中包含上述交付物。

## 📚 执行前必须阅读以下手册
1. 公司手册: `/home/user/opc/manuals/company.md`
2. 员工手册: `/home/user/opc/manuals/employees/emp-001.md`
3. 任务手册: `/home/user/opc/manuals/tasks/task-xxx.md`
```

### 第二个步骤

```markdown
【任务分配】

任务: 内容创作工作流 - Step 2: 撰写正文

## 工作流上下文
当前步骤: 2 / 3
工作流ID: wf-abc123

## 任务描述
撰写文章正文

## 前序步骤输出
**步骤 1**: 选题策划
**执行者**: 编辑小李
**输出摘要**: 确定了"AI发展趋势"选题，关键词：多模态、Agent、边缘AI
**关键数据**:
  - trend_1: 多模态AI
  - trend_2: AI Agent
  - trend_3: 边缘AI
**交付物**:
  - 选题报告.md

## 输入要求
需要选题报告、关键词列表、目标受众分析

## 输出交付物要求
完整的文章正文（2000字以上），包含：
1. 引人入胜的开头
2. 三个核心论点
3. 实用案例
4. 总结展望

**重要**: 请确保你的 OPC-REPORT 中包含上述交付物。

## 📚 执行前必须阅读以下手册
...
```

## 测试

### 测试文件
`test_subfeature_3.py`

### 测试用例

| 测试 | 描述 |
|------|------|
| `_get_previous_output` | 验证前序输出提取 |
| `_get_step_context` | 验证步骤上下文解析 |
| `_build_step_description` | 验证步骤描述构建 |
| `_build_initial_step_description` | 验证初始描述构建 |
| `_trigger_next_step` | 验证完整集成 |

### 运行测试

```bash
cd /root/.openclaw/workspace/openclaw-opc
python3 test_subfeature_3.py
```

### 预期输出

```
✅ _get_previous_output 测试通过
✅ _get_step_context 测试通过
✅ _build_step_description 测试通过
✅ _build_initial_step_description 测试通过
✅ _trigger_next_step 集成测试通过

总计: 5/5 通过
🎉 子功能3测试全部通过！
```

## 向后兼容性

- ✅ 旧工作流继续正常运行（无手册信息则不添加描述）
- ✅ 无手册字段的任务不受影响
- ✅ 数据格式保持JSON，易于扩展

## 相关文件

| 文件 | 说明 |
|------|------|
| `workflow_service.py` | 核心方法实现 |
| `test_subfeature_3.py` | 测试脚本 |

---

*文档版本: v0.4.6*  
*最后更新: 2026-03-28*
