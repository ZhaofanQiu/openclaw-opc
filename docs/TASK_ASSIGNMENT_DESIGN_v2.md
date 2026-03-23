# OPC 员工任务分配系统设计 (v2.0 - 实践版)

> **文档版本**: v2.0  
> **更新日期**: 2026-03-23  
> **更新原因**: 闭环测试成功后，基于实践经验修订  
> **相关文档**: `AGENT_INTERACTION_BEST_PRACTICES.md`

---

## 核心方法论（已验证）

1. **三维度控制**: 消息 + 手册 + Skill 回调
2. **异步执行**: OPC 发送消息后等待 Agent 回调
3. **自包含任务**: 任务消息包含所有必要信息
4. **结果回调**: Agent 主动回调报告结果

---

## 实际任务消息格式

### 实际工作中的消息模板

```markdown
# 任务分配

## 任务信息
- 任务ID: {task_id}
- 标题: {title}
- 描述: {description}

## 执行步骤

1. **读取 opc-bridge skill 手册**：
   路径：`/root/.openclaw/skills/opc-bridge-v2/SKILL.md`

2. **执行具体任务**：
   {task_specific_instructions}

3. **报告完成**：
   执行回调脚本：
   ```bash
   python3 /root/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py \
     {task_id} {estimated_tokens} "{result_summary}"
   ```

立即开始执行！
```

### 实际示例

```markdown
# 任务分配

## 任务信息
- 任务ID: task_3dd162c1
- 标题: 最终闭环测试
- 描述: 测试读取手册、执行命令、回调报告

## 执行步骤

1. **读取 opc-bridge skill 手册**：
   路径：`/root/.openclaw/skills/opc-bridge-v2/SKILL.md`

2. **执行任务**：
   执行 shell 命令：echo hello

3. **报告完成**：
   执行回调脚本：
   ```bash
   python3 /root/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py \
     task_3dd162c1 50 "成功"
   ```

立即执行！
```

---

## 完整任务流程（实际运行）

### 流程图

```
┌─────────────┐
│  1.创建任务  │  Task(title, description, status=PENDING)
└──────┬──────┘
       ↓
┌─────────────┐
│  2.分配员工  │  task.assigned_to = employee.id
│             │  task.status = ASSIGNED
└──────┬──────┘
       ↓
┌─────────────────────┐
│  3.构建任务消息      │  包含 task_id + skill 路径 + 回调命令
│  (三维度控制)       │
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│  4.发送给 Agent      │  sessions_send(agent_id, message)
│  (OpenClaw API)     │
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│  5.Agent 处理        │  读取手册 → 执行任务 → 执行回调
│                     │
│  ┌───────────────┐  │
│  │ 读取 SKILL.md │  │  read(/root/.openclaw/skills/...)
│  └───────┬───────┘  │
│          ↓          │
│  ┌───────────────┐  │
│  │ 执行具体任务   │  │  exec(echo hello)
│  └───────┬───────┘  │
│          ↓          │
│  ┌───────────────┐  │
│  │ 执行回调脚本   │──┼──▶ HTTP POST /api/skill/tasks/{id}/report
│  └───────────────┘  │
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│  6.OPC 接收回调      │  更新任务状态 → 扣除预算 → 记录日志
│                     │
│  task.status =      │
│    COMPLETED        │
└─────────────────────┘
```

### 关键时序

```
时间: 0s          2s          15s              20s
      │           │            │                │
      ▼           ▼            ▼                ▼
   ┌─────┐    ┌─────┐     ┌─────┐         ┌─────┐
   │发送 │───▶│Agent│────▶│回调 │────────▶│完成 │
   │消息 │    │接收 │     │执行 │         │状态 │
   └─────┘    │处理 │     └─────┘         └─────┘
              └─────┘
```

**实际测试数据**: 任务 `task_3dd162c1` 从发送到完成约 5 秒

---

## 后端实现要点

### 1. 任务分配服务

```python
# services/task_assignment_service.py

async def assign_task(
    task_id: str,
    employee_id: str,
    agent_id: str  # OpenClaw Agent ID，如 "opc_partner"
):
    # 1. 更新任务状态
    task = db.get_task(task_id)
    task.assigned_to = employee_id
    task.status = TaskStatus.ASSIGNED
    db.commit()
    
    # 2. 构建任务消息
    message = build_task_message(task)
    
    # 3. 发送给 Agent
    client = OpenClawClient()
    result = await client.send_message(
        agent_id=agent_id,
        message=message,
        mode=ExecutionMode.SYNC,  # 等待 Agent 回复
        timeout=120,
        agent_name=employee.name,
        task_id=task_id
    )
    
    return result

def build_task_message(task: Task) -> str:
    """构建标准化的任务消息"""
    return f"""
# 任务分配

## 任务信息
- 任务ID: {task.id}
- 标题: {task.title}
- 描述: {task.description}

## 执行步骤

1. **读取 opc-bridge skill 手册**：
   路径：`/root/.openclaw/skills/opc-bridge-v2/SKILL.md`

2. **执行具体任务**：
   {task.description}

3. **报告完成**：
   执行：`python3 /root/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py \\
     {task.id} {task.estimated_cost} "任务完成结果"`

立即执行！
"""
```

### 2. 回调处理服务

```python
# routers/skill_api.py

@router.post("/tasks/{task_id}/report")
def report_task_result(
    task_id: str,
    data: TaskReportRequest,
    db: Session = Depends(get_db)
):
    """
    Agent 报告任务完成
    
    关键：支持通过 task_id 反查员工，解决 agent_id 不匹配问题
    """
    # 1. 尝试通过 agent_id 查找员工
    agent = db.query(Agent).filter(
        Agent.openclaw_agent_id == data.agent_id
    ).first()
    
    # 2. 如果找不到，通过 task_id 反查（兜底方案）
    if not agent:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.assigned_to:
            agent = db.query(Agent).filter(
                Agent.id == task.assigned_to
            ).first()
    
    # 3. 更新任务状态
    task = db.query(Task).filter(Task.id == task_id).first()
    task.status = TaskStatus.COMPLETED
    task.actual_cost = calculate_cost(data.tokens_used)
    task.result = data.result
    task.completed_at = datetime.now()
    
    # 4. 扣除预算
    agent.used_budget += task.actual_cost
    
    # 5. 记录交互日志
    log_interaction(
        agent_id=data.agent_id,
        direction="incoming",
        type="callback",
        content=f"Task {task_id} completed"
    )
    
    db.commit()
    
    return {
        "success": True,
        "cost": task.actual_cost,
        "remaining_budget": agent.monthly_budget - agent.used_budget
    }
```

### 3. OpenClaw 客户端

```python
# core/openclaw_client.py

class OpenClawClient:
    """OpenClaw API 封装"""
    
    async def send_message(
        self,
        agent_id: str,          # OpenClaw Agent ID
        message: str,           # 任务消息
        mode: ExecutionMode,    # SYNC / ASYNC
        timeout: int = 120,
        agent_name: str = "",   # 用于日志记录
        task_id: str = ""       # 关联的任务ID
    ) -> SendMessageResult:
        """
        发送消息给 Agent
        
        实际调用 OpenClaw 的 sessions_send API
        """
        # 调用 OpenClaw API
        # ...
```

---

## 前端界面设计

### 任务分配面板

```
┌─────────────────────────────────────────────────────┐
│ 📋 任务分配                                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  员工: [实习生小刘 ▼]                               │
│                                                     │
│  任务标题: [________________________]               │
│                                                     │
│  任务描述:                                          │
│  ┌─────────────────────────────────────────────┐   │
│  │                                             │   │
│  │  输入具体任务要求...                         │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  预估预算: [100] OC币    优先级: [高 ▼]            │
│                                                     │
│  [✓] 自动生成手册                                  │
│                                                     │
│  [🚀 立即分配]                                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 任务执行时间线

```
┌─────────────────────────────────────────────────────┐
│ ⏱️ 执行时间线 - task_3dd162c1                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  10:12:35  📝 OPC 分配任务                          │
│            消息已发送给 Agent (opc_partner)         │
│                                                     │
│  10:12:36  👤 Agent 接收任务                        │
│            开始执行...                              │
│                                                     │
│  10:12:40  🔧 执行任务                              │
│            $ echo hello                             │
│            输出: hello                              │
│                                                     │
│  10:12:41  📤 Agent 回调                            │
│            {"success": true, "cost": 0.5}          │
│                                                     │
│  10:12:41  ✅ 任务完成                              │
│            状态: completed                          │
│            消耗: 0.5 OC币                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 关键经验教训

### 1. 消息必须包含完整信息

**❌ 错误**:
```markdown
请完成这个任务：分析最近的数据
```

**✅ 正确**:
```markdown
# 任务分配

## 任务信息
- 任务ID: task_xxx
...

## 执行步骤
1. 读取 skill 手册：...
2. 执行具体任务：...
3. 使用 opc-report.py 报告结果：...
```

### 2. 回调必须免认证

Agent 没有 API Key，不能通过认证。Skill API 必须免认证访问。

### 3. 回调地址必须正确

- 使用宿主机实际 IP（如 `10.188.153.187:8080`）
- 确保 OPC 服务在 `0.0.0.0:8080` 监听
- 确保网络可达

### 4. 回调路由要健壮

Agent 报告的 `agent_id` 可能与 OPC 中存储的不一致（如 `root` vs `opc_partner`），需要通过 `task_id` 反查员工。

---

## 调试清单

在部署前检查以下事项：

- [ ] Agent 配置正确（无 `tools`/`skills` 字段）
- [ ] Skill 已安装（`~/.openclaw/skills/opc-bridge-v2/` 存在）
- [ ] Skill API 免认证（独立注册，无 `dependencies`）
- [ ] 回调路由支持 task_id 反查
- [ ] 回调脚本使用正确的 OPC 地址
- [ ] OPC 服务在 `0.0.0.0:8080` 监听
- [ ] 测试 Agent 能执行命令
- [ ] 测试 Agent 能读取 skill 手册
- [ ] 测试回调脚本能连接到 OPC

---

**设计时间**: 2026-03-23  
**版本**: v2.0（实践验证版）  
**状态**: ✅ 闭环测试通过  
**相关文档**:
- `AGENT_INTERACTION_BEST_PRACTICES.md`
- `AGENT_CONFIG_NOTES.md`
- `ARCHITECTURE_v2.md`
