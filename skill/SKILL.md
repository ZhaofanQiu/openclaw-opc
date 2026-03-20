---
name: opc-bridge
description: Connect OpenClaw Agents to OPC Core Service for budget tracking and task management
---

# OPC Bridge

This skill connects your Agent to the OpenClaw OPC (One-Person Company) management system.

## Overview

The OPC Bridge allows your Agent to:
- Report task completion and token usage
- Check for assigned tasks
- Monitor budget status
- Integrate with the company workflow

## Configuration

Set the Core Service URL (optional, defaults to localhost):

```bash
export OPC_CORE_URL="http://localhost:8080"
export OPC_AGENT_ID="your-agent-id"
```

## Functions

### opc_report(task_id, token_used, result_summary, status)

Report task completion to OPC Core Service.

**Parameters:**
- `task_id` (str): The ID of the completed task
- `token_used` (int): Number of tokens consumed
- `result_summary` (str): Brief description of work done
- `status` (str): "completed" or "failed"

**Returns:**
- `success` (bool): Whether the report was accepted
- `cost` (float): OC币 consumed
- `remaining_budget` (float): Updated budget
- `fused` (bool): True if budget exceeded

**Example:**
```python
result = opc_report(
    task_id="abc123",
    token_used=1500,
    result_summary="完成了登录页重构，添加了表单验证",
    status="completed"
)

if result["success"]:
    print(f"✅ 任务完成，消耗 {result['cost']} OC币")
    print(f"💰 剩余预算: {result['remaining_budget']} OC币")
elif result.get("fused"):
    print(f"🚨 预算熔断: {result['message']}")
```

### opc_check_task()

Check for assigned tasks from OPC Core Service.

**Returns:**
- `has_task` (bool): Whether there's a pending task
- `task` (dict): Task details if has_task is True

**Example:**
```python
result = opc_check_task()

if result["has_task"]:
    task = result["task"]
    print(f"📋 新任务: {task['title']}")
    print(f"📝 {task['description']}")
    print(f"💰 预算: {task['estimated_cost']} OC币")
    # Start working on the task...
else:
    print("☕ 暂无任务，休息一下")
```

### opc_get_budget()

Get current budget status.

**Returns:**
- `monthly_budget` (float): Total budget
- `used_budget` (float): Amount used
- `remaining_budget` (float): Amount remaining
- `mood_emoji` (str): Current mood based on budget

**Example:**
```python
budget = opc_get_budget()
print(f"💰 本月预算: {budget['monthly_budget']} OC币")
print(f"📊 已用: {budget['used_budget']} OC币")
print(f"💵 剩余: {budget['remaining_budget']} OC币")
print(f"😊 心情: {budget['mood_emoji']}")
```

## Workflow

### For Employee Agents

1. **Check for tasks** (periodically or on demand):
   ```python
   result = opc_check_task()
   if result["has_task"]:
       task = result["task"]
       # Execute the task...
   ```

2. **Execute the task** using your normal capabilities

3. **Report completion**:
   ```python
   opc_report(
       task_id=task["id"],
       token_used=estimated_tokens,
       result_summary="任务完成描述",
       status="completed"
   )
   ```

### For Partner Agents

1. **Monitor company status** via Core Service APIs
2. **Coordinate task assignment** to employees
3. **Assist in hiring** new employees
4. **Handle budget alerts** and fuse events

## Budget System

- **OC币**: Virtual currency representing token budget
- **Conversion**: 1 OC币 = 100 tokens (configurable)
- **Mood**: Derived from remaining budget percentage
  - 😊 > 60% budget remaining
  - 😐 30-60% budget remaining
  - 😔 10-30% budget remaining
  - 🚨 < 10% budget remaining

## Error Handling

All functions return a dictionary with `success` field:
- `success: True` - Operation successful
- `success: False` - Check `error` field for details

Common errors:
- Core Service not running
- Invalid task_id or agent_id
- Network connectivity issues

## See Also

- OPC Core Service: http://localhost:8080/docs
- Company Dashboard: (UI coming in v0.2.0)
