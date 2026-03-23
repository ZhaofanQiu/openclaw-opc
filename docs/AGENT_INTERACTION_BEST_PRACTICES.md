# OPC Agent 交互最佳实践

> **文档目的**: 总结 OPC 与 OpenClaw Agent 交互的实践经验，避免重复踩坑
> 
> **适用范围**: 开发者在进行 OPC 相关开发时参考
> 
> **最后更新**: 2026-03-23（闭环测试成功后）

---

## 🚨 最重要的三条经验

### 1. Agent 配置要简单

**❌ 错误做法**（会导致工具权限受限）:
```json
{
  "id": "my_agent",
  "tools": {"allow": ["group:fs", "opc-bridge"]},
  "skills": ["opc-bridge"]
}
```

**✅ 正确做法**（使用默认完整工具集）:
```json
{
  "id": "my_agent",
  "name": "My Agent",
  "workspace": "/path/to/workspace",
  "agentDir": "/path/to/agent"
}
```

**原因**: 
- OpenClaw 默认提供完整工具集（`exec`, `read`, `write`, `web_search` 等）
- 添加 `tools.allow` 会**限制** Agent 只能使用列出的工具
- Skill 通过文件系统提供，不需要在配置中注册

---

### 2. Skill API 必须免认证

Agent 回调 OPC 时不能使用 API Key 认证（因为 Agent 不知道密钥）。

**解决方案**:
```python
# main_v2.py
# Skill API 单独注册，无认证依赖
app.include_router(
    skill_api.router,
    prefix="/api/skill",
    tags=["Skill API"],
    dependencies=[]  # 无认证
)
```

**回调路由增强**（解决 agent_id 不匹配问题）:
```python
@router.post("/tasks/{task_id}/report")
def report_task_result(task_id: str, data: TaskReportRequest, db: Session = Depends(get_db)):
    # 1. 先尝试通过 agent_id 查找
    agent = db.query(Agent).filter(Agent.openclaw_agent_id == data.agent_id).first()
    
    # 2. 如果找不到，通过 task_id 反查
    if not agent:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task and task.assigned_to:
            agent = db.query(Agent).filter(Agent.id == task.assigned_to).first()
    
    # 3. 报告任务完成
    ...
```

---

### 3. 回调脚本要使用正确的 OPC 地址

Agent 执行回调脚本时需要能访问到 OPC 服务。

**配置 opc-report.py**:
```python
# 使用宿主机实际 IP，而不是 localhost/127.0.0.1
OPC_CORE_URL = os.getenv("OPC_CORE_URL", "http://10.188.153.187:8080")
```

**验证连接**:
```bash
# 在 Agent 环境中测试
python3 /root/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py test_task 50 "test"
```

---

## 📋 完整的 Agent 交互流程

### 阶段 1: 任务分配 (OPC → Agent)

```python
# 1. 创建任务
task = Task(
    id="task_xxx",
    title="任务标题",
    description="任务描述",
    status=TaskStatus.PENDING
)

# 2. 分配给员工
task.assigned_to = employee.id
task.status = TaskStatus.ASSIGNED
db.commit()

# 3. 发送消息给 Agent
message = f"""
# 任务分配

## 任务信息
- 任务ID: {task.id}
- 标题: {task.title}
- 描述: {task.description}

## 执行步骤
1. 读取 opc-bridge skill 手册：
   /root/.openclaw/skills/opc-bridge-v2/SKILL.md

2. 执行具体任务（如：echo hello）

3. 报告完成：
   python3 /root/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py \\
     {task.id} 50 "任务完成结果"

立即执行！
"""

client.send_message(
    agent_id=employee.openclaw_agent_id,  # 如 "opc_partner"
    message=message,
    mode=ExecutionMode.SYNC,
    timeout=120
)
```

**关键要点**:
- 消息中必须明确告诉 Agent 读取 skill 手册
- 必须提供完整的回调命令（包括 task_id）
- 使用 `ExecutionMode.SYNC` 等待 Agent 回复

---

### 阶段 2: 任务执行 (Agent 内部)

Agent 收到消息后会：
1. 使用 `read` 工具读取 SKILL.md
2. 理解任务要求和回调方式
3. 使用 `exec` 执行具体任务
4. 使用 `exec` 执行回调脚本

**Agent 的执行示例**:
```
用户: # 任务分配 ...

我: 收到任务，开始执行：

步骤1: 读取手册...
   ✓ 已读取 /root/.openclaw/skills/opc-bridge-v2/SKILL.md
   ✓ 理解回调命令格式

步骤2: 执行任务...
   $ echo hello
   ✓ 输出: hello

步骤3: 报告完成...
   $ python3 /root/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py task_xxx 50 "成功"
   ✓ 回调成功: {"success": true, "cost": 0.5}
```

---

### 阶段 3: 结果回调 (Agent → OPC)

Agent 执行 `opc-report.py`，该脚本：
1. 构造 HTTP POST 请求
2. 发送到 `/api/skill/tasks/{task_id}/report`
3. 携带 `agent_id`, `result`, `tokens_used`

OPC 接收到回调后：
1. 查找对应员工（通过 agent_id 或 task_id）
2. 更新任务状态为 `completed`
3. 扣除预算
4. 记录交互日志

---

## ⚠️ 常见错误及解决方案

### 错误 1: Agent 无法执行命令

**症状**: Agent 回复说没有权限或工具

**原因**: Agent 配置了 `tools.allow` 限制了可用工具

**解决**: 从 `openclaw.json` 中移除 `tools` 和 `skills` 字段

---

### 错误 2: 回调返回 401 Unauthorized

**症状**: Agent 报告回调失败，HTTP 401

**原因**: Skill API 路由继承了全局认证依赖

**解决**: 在 `main_v2.py` 中单独注册 Skill API 路由，不添加认证依赖

---

### 错误 3: 回调返回 "Agent not found"

**症状**: Agent 报告回调失败，agent_id 不匹配

**原因**: 回调脚本使用 `USER` 环境变量作为 agent_id（如 `root`），与绑定的 agent_id（如 `opc_partner`）不匹配

**解决**: 在回调路由中增加通过 `task_id` 反查员工的逻辑

---

### 错误 4: 回调连接被拒绝

**症状**: `Connection refused` 或 `Network is unreachable`

**原因**: 
1. OPC 服务未运行
2. 回调脚本使用 `localhost`/`127.0.0.1`，但 Agent 在隔离网络环境中
3. 防火墙限制

**解决**:
1. 确保 OPC 服务在 `0.0.0.0:8080` 监听
2. 使用宿主机实际 IP（如 `10.188.153.187:8080`）
3. 检查网络连通性

---

### 错误 5: 任务状态未更新

**症状**: 回调返回成功，但任务状态仍是 `assigned`

**原因**: 
1. 数据库事务未提交
2. 回调处理异常被吞掉

**解决**: 检查日志，确保回调处理逻辑正确执行

---

## 🔧 调试技巧

### 1. 验证 Agent 能力

```bash
# 测试 Agent 是否能执行命令
openclaw agent --agent opc_partner --message "执行命令：echo test" --json
```

### 2. 测试回调脚本

```bash
# 直接测试回调脚本
python3 /root/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py \
  task_test 50 "测试结果"
```

### 3. 检查 OPC 日志

```bash
tail -f /tmp/opc.log | grep -E "callback|report|task_xxx"
```

### 4. 检查数据库状态

```bash
cd /root/.openclaw/workspace/openclaw-opc/backend/src
python3 -c "
from database import SessionLocal
from models.task_v2 import Task
db = SessionLocal()
task = db.query(Task).filter(Task.id == 'task_xxx').first()
print(f'Status: {task.status}, Cost: {task.actual_cost}')
db.close()
"
```

---

## 📝 任务消息最佳实践

### DO（推荐）

```markdown
# 任务分配

## 任务信息
- 任务ID: {task_id}
- 标题: 明确的任务标题

## 执行步骤
1. 首先读取 skill 手册：
   /root/.openclaw/skills/opc-bridge-v2/SKILL.md

2. 执行具体任务（明确说明）

3. 使用 opc-report.py 报告结果（提供完整命令）

## 约束条件
- 预算: {budget} OC币
- 截止时间: {deadline}
```

### DON'T（避免）

```markdown
# 任务分配

请完成这个任务：{description}

完成后告诉我。

（缺少：skill 手册路径、回调命令、明确的执行步骤）
```

---

## 🎯 总结

成功跑通 OPC → Agent → OPC 闭环的关键：

1. **Agent 配置保持简单** - 不要添加 `tools` 和 `skills` 字段
2. **Skill API 必须免认证** - 否则 Agent 无法回调
3. **回调路由要健壮** - 支持通过 task_id 反查
4. **回调地址要正确** - 使用宿主机 IP，确保网络可达
5. **任务消息要完整** - 明确告诉 Agent 如何读取手册和回调

---

**相关文档**:
- `AGENT_CONFIG_NOTES.md` - Agent 配置详情
- `ARCHITECTURE_v2.md` - 系统架构设计
- `../backend/src/routers/skill_api.py` - Skill API 实现
