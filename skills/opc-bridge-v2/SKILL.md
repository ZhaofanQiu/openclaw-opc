---
name: opc-bridge-v2
description: "OPC (One-Person Company) Bridge - Connect OpenClaw Agents to OPC Core Service for budget tracking and task management. Use when: (1) Completing an assigned task from OPC and need to report completion, (2) Checking assigned tasks from OPC, (3) Querying budget status. Always call the report script when finishing an OPC task."
---

# OPC Bridge v2

Connect OpenClaw Agents to OPC Core Service for budget tracking and task management.

## When to Use

Use this skill when:
1. **Completing an assigned task from OPC** → MUST call the report script
2. **Checking for assigned tasks** from OPC
3. **Querying budget status** from OPC

## Critical: Always Report Task Completion

When you complete a task assigned by OPC, **you MUST call the report script** to notify OPC.
Failure to do so will leave the task in "assigned" state forever.

### Report Task Completion

After finishing an OPC task, immediately run:

```bash
python3 {baseDir}/scripts/opc-report.py <TASK_ID> <TOKEN_USED> "任务完成总结"
```

**Parameters:**
- `TASK_ID`: The task ID from OPC (e.g., "task_abc123")
- `TOKEN_USED`: Number of tokens consumed (e.g., 500)
- `result_summary`: Brief description of work completed

**Example:**
```bash
python3 {baseDir}/scripts/opc-report.py task_abc123 500 "代码审查完成，发现3个问题"
```

**Response:**
- Success: Returns JSON with `success: true`, `cost`, and `remaining_budget`
- Failure: Check stderr for error details

### Check Assigned Tasks

To check if OPC has assigned you a task:

```bash
python3 {baseDir}/scripts/opc-check-task.py
```

### Query Budget

To check your current budget status:

```bash
python3 {baseDir}/scripts/opc-get-budget.py
```

## Task Execution Workflow

When you receive a task from OPC:

1. **Acknowledge** the task in your response
2. **Execute** the required work
3. **Report completion** using the script above
4. **Confirm** the report was successful

**Example complete workflow:**

```
User assigns task: "Review this code"
  ↓
You: "收到任务，开始执行代码审查..."
  ↓
[Execute the work]
  ↓
You: "代码审查完成，发现问题：..."
  ↓
Call: python3 {baseDir}/scripts/opc-report.py task_xxx 600 "审查完成"
  ↓
You: "任务已报告给 OPC，预算消耗：X OC币"
```

## Environment Variables

- `OPC_CORE_URL`: OPC Core Service URL (default: http://localhost:8080)
- `OPC_AGENT_ID`: Your agent ID (auto-detected from environment)

## Important Notes

- **Never skip the report step** - OPC needs to know you finished
- Always check the script return value
- If report fails, retry once or note the failure in your response
