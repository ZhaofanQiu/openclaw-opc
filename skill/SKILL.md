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
- Track exact token consumption via session_status

## Configuration

Set the Core Service URL (optional, defaults to localhost):

```bash
export OPC_CORE_URL="http://localhost:8080"
export OPC_AGENT_ID="your-agent-id"
```

## Functions

### opc_report(task_id, token_used, result_summary, status, **kwargs)

Report task completion to OPC Core Service.

**Parameters:**
- `task_id` (str): The ID of the completed task
- `token_used` (int): Number of tokens consumed (total)
- `result_summary` (str): Brief description of work done
- `status` (str): "completed" or "failed"
- `tokens_input` (int, optional): Actual input tokens from session_status
- `tokens_output` (int, optional): Actual output tokens from session_status
- `session_key` (str, optional): OpenClaw session identifier
- `is_exact` (bool, optional): True if values are exact from session_status

**Returns:**
- `success` (bool): Whether the report was accepted
- `cost` (float): OC币 consumed
- `remaining_budget` (float): Updated budget
- `fused` (bool): True if budget exceeded
- `is_exact` (bool): Whether exact token tracking was recorded

**Example:**
```python
# With estimated tokens
result = opc_report(
    task_id="abc123",
    token_used=1500,
    result_summary="完成了登录页重构，添加了表单验证",
    status="completed"
)

# With exact tokens from session_status
result = opc_report(
    task_id="abc123",
    token_used=1523,
    result_summary="完成了登录页重构，添加了表单验证",
    status="completed",
    tokens_input=850,
    tokens_output=673,
    session_key="session_abc123",
    is_exact=True
)

if result["success"]:
    print(f"✅ 任务完成，消耗 {result['cost']} OC币")
    print(f"💰 剩余预算: {result['remaining_budget']} OC币")
    if result.get("is_exact"):
        print(f"📊 精确追踪已记录")
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

### opc_report_exact(task_id, tokens_input, tokens_output, session_key, result_summary)

Report task completion with exact token consumption from session_status.

**Parameters:**
- `task_id` (str): The ID of the completed task
- `tokens_input` (int): Actual input tokens from session_status
- `tokens_output` (int): Actual output tokens from session_status
- `session_key` (str): OpenClaw session identifier
- `result_summary` (str): Brief description of work done

**Returns:**
- `success` (bool): Whether the report was accepted
- `cost` (float): OC币 consumed
- `remaining_budget` (float): Updated budget

**Example:**
```python
# Get exact token consumption from session_status
# Then report to OPC Core Service
result = opc_report_exact(
    task_id="abc123",
    tokens_input=850,
    tokens_output=673,
    session_key="session_abc123",
    result_summary="完成了登录页重构"
)

if result["success"]:
    print(f"✅ 精确报告成功，消耗 {result['cost']} OC币")
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

3. **Get exact token consumption** (if supported):
   ```python
   # Use session_status tool to get actual token usage
   # This is done automatically by OpenClaw or Partner Agent
   ```

4. **Report completion** (with exact tokens if available):
   ```python
   opc_report(
       task_id=task["id"],
       token_used=estimated_tokens,  # Fallback if exact not available
       result_summary="任务完成描述",
       status="completed",
       tokens_input=actual_input,    # From session_status
       tokens_output=actual_output,  # From session_status
       session_key=session_key,      # From session_status
       is_exact=True                 # Mark as exact tracking
   )
   ```

### For Partner Agents

1. **Monitor company status** via Core Service APIs
2. **Coordinate task assignment** to employees
3. **Assist in hiring** new employees
4. **Handle budget alerts** and fuse events
5. **Collect exact token consumption** after task completion:
   ```python
   # After task completion, get session_status
   # Report exact consumption to Core Service
   result = opc_report_exact(
       task_id=completed_task_id,
       tokens_input=session_data["tokens_input"],
       tokens_output=session_data["tokens_output"],
       session_key=session_data["session_key"],
       result_summary="任务已完成，精确Token已记录"
   )
   ```

## Budget System

- **OC币**: Virtual currency representing token budget
- **Conversion**: 1 OC币 = 100 tokens (configurable)
- **Mood**: Derived from remaining budget percentage
  - 😊 > 60% budget remaining
  - 😐 30-60% budget remaining
  - 😔 10-30% budget remaining
  - 🚨 < 10% budget remaining

## Exact Token Tracking

The OPC Bridge now supports precise token consumption tracking:

1. **Estimated Values**: When exact tokens aren't available, the system uses estimates based on task complexity
2. **Exact Values**: When `is_exact=True`, the actual tokens from `session_status` are recorded
3. **Comparison**: Reports show the difference between estimated and actual consumption

### Benefits

- More accurate budget forecasting
- Better understanding of actual costs
- Improved task estimation over time

## Error Handling

All functions return a dictionary with `success` field:
- `success: True` - Operation successful
- `success: False` - Check `error` field for details

Common errors:
- Core Service not running
- Invalid task_id or agent_id
- Network connectivity issues
- Session key not found

## See Also

- OPC Core Service: http://localhost:8080/docs
- Company Dashboard: (UI coming in v0.2.0)
- OpenClaw session_status: Use to get exact token consumption
