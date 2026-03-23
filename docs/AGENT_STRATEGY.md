# OPC Agent 使用策略 (v2.0 - 实践版)

> **文档版本**: v2.0  
> **更新日期**: 2026-03-23  
> **更新原因**: 基于闭环测试经验修订  
> **相关文档**: 
> - `AGENT_INTERACTION_BEST_PRACTICES.md`
> - `AGENT_CONFIG_NOTES.md`
> - `TASK_ASSIGNMENT_DESIGN_v2.md`

---

## 核心原则（已验证）

### 1. Agent 配置最小化原则

**关键经验**: Agent 配置越简单越好，**不要**添加 `tools` 和 `skills` 字段。

```json
// ✅ 推荐配置
{
  "id": "opc_employee_001",
  "name": "实习生小刘",
  "workspace": "/root/.openclaw/agents/opc_employee_001/workspace",
  "agentDir": "/root/.openclaw/agents/opc_employee_001"
}

// ❌ 避免（会导致工具受限）
{
  "id": "opc_employee_001",
  "tools": {"allow": ["group:fs"]},
  "skills": ["opc-bridge"]
}
```

### 2. Agent 隔离原则

- 使用 `opc_` 前缀区分 OPC 专用 Agent
- 禁止使用 `main`, `default` 等用户 Agent
- 每个员工绑定一个独立的 OpenClaw Agent

### 3. 三维度控制原则

Agent 交互通过三个维度控制：
1. **消息**: 任务描述和约束
2. **手册**: Skill 指导文件
3. **回调**: Skill API 报告结果

---

## Agent 生命周期管理

### 创建流程

```
用户创建员工
    ↓
OPC 生成 Agent ID (opc_emp_<uuid>)
    ↓
添加到 openclaw.json
    ↓
创建 Agent 工作空间
    ↓
写入 AGENTS.md, SOUL.md, IDENTITY.md
    ↓
重启 OpenClaw Gateway
    ↓
Agent 就绪
```

### 绑定流程

```python
# 1. 创建 OPC 员工记录
employee = Employee.create(
    name="实习生小刘",
    position_level=1,
    monthly_budget=1000
)

# 2. 创建 OpenClaw Agent（自动或手动）
agent_id = f"opc_emp_{employee.id}"

# 添加到 openclaw.json
add_agent_to_config({
    "id": agent_id,
    "name": f"OPC Employee - {employee.name}",
    "workspace": f"/root/.openclaw/agents/{agent_id}/workspace",
    "agentDir": f"/root/.openclaw/agents/{agent_id}"
})

# 3. 绑定关系
employee.openclaw_agent_id = agent_id
employee.is_bound = True
db.commit()

# 4. 重启 Gateway（使配置生效）
restart_openclaw_gateway()
```

### 验证流程

创建 Agent 后必须验证：

```bash
# 验证 1: Agent 能执行命令
openclaw agent --agent opc_emp_xxx \
  --message "执行命令：echo '验证通过'" --json

# 验证 2: Agent 能读取 skill 手册
openclaw agent --agent opc_emp_xxx \
  --message "读取文件：~/.openclaw/skills/opc-bridge-v2/SKILL.md" --json

# 验证 3: 回调脚本能连接到 OPC
python3 ~/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py \
  test_task 50 "验证回调"
```

---

## Agent 命名规范

### 推荐格式

```
opc_<role>_<identifier>
```

示例：
- `opc_partner` - Partner 助手
- `opc_emp_a7f8d2e1` - 员工（内部ID）
- `opc_system` - 系统任务

### 禁止使用的名称

```python
OPC_AGENT_BLACKLIST = [
    "main",           # 用户主 Agent
    "default",        # 默认 Agent
    "root",           # 根用户
    "",               # 空名称
]
```

---

## Agent 工作空间结构

```
~/.openclaw/agents/{agent_id}/
├── agent/
│   ├── workspace/           # 工作目录
│   │   ├── AGENTS.md        # 工作指南
│   │   ├── IDENTITY.md      # Agent 身份
│   │   ├── SOUL.md          # 性格定义
│   │   ├── USER.md          # 用户信息
│   │   ├── TOOLS.md         # 工具说明
│   │   └── tasks/           # 任务输出目录
│   └── ...
└── ...
```

**关键文件**:
- `AGENTS.md`: 告诉 Agent 如何工作
- `IDENTITY.md`: Agent 的身份信息
- `SOUL.md`: Agent 的性格和行为模式
- `TOOLS.md`: 本地工具说明

---

## 任务分配策略

### 分配前检查清单

- [ ] Agent 配置正确（无 `tools`/`skills` 字段）
- [ ] Agent 已绑定到员工
- [ ] Agent 能执行命令（验证通过）
- [ ] Agent 能读取 skill 手册
- [ ] 回调脚本配置正确（使用正确的 OPC 地址）
- [ ] 员工预算充足

### 分配流程

```python
def assign_task_to_agent(task: Task, employee: Employee):
    """分配任务给 Agent"""
    
    # 1. 前置检查
    if not employee.openclaw_agent_id:
        raise ValueError("员工未绑定 Agent")
    
    if employee.status != AgentStatus.IDLE:
        raise ValueError("员工当前忙碌")
    
    # 2. 更新状态
    task.assigned_to = employee.id
    task.status = TaskStatus.ASSIGNED
    employee.status = AgentStatus.WORKING
    employee.current_task_id = task.id
    db.commit()
    
    # 3. 构建任务消息（关键！）
    message = build_task_message(task)
    
    # 4. 发送给 Agent
    result = await openclaw_client.send_message(
        agent_id=employee.openclaw_agent_id,
        message=message,
        mode=ExecutionMode.SYNC,
        timeout=120
    )
    
    # 5. 记录交互
    log_interaction(
        agent_id=employee.openclaw_agent_id,
        direction="outgoing",
        type="task_assignment",
        content=message[:200]
    )
    
    return result
```

---

## 常见问题与解决方案

### Q1: Agent 无法执行命令

**症状**: Agent 回复说没有工具或权限

**原因**: Agent 配置了 `tools.allow` 限制了可用工具

**解决**:
```bash
# 1. 编辑 openclaw.json，移除 tools 和 skills 字段
vi ~/.openclaw/openclaw.json

# 2. 重启 Gateway
openclaw gateway restart

# 3. 验证
openclaw agent --agent opc_xxx --message "echo test" --json
```

### Q2: 回调失败 - "Agent not found"

**症状**: Agent 报告回调失败，agent_id 不匹配

**原因**: 回调脚本使用 `USER` 环境变量（如 `root`），与绑定的 agent_id 不同

**解决**: 在回调路由中增加通过 `task_id` 反查员工的逻辑（已修复）

### Q3: 回调失败 - "Connection refused"

**症状**: 回调脚本无法连接到 OPC

**原因**: 
1. OPC 服务未运行
2. 回调脚本使用 `localhost`/`127.0.0.1`
3. OPC 未在 `0.0.0.0` 监听

**解决**:
```python
# 1. 确保 OPC 在 0.0.0.0:8080 监听
uvicorn main_v2:app --host 0.0.0.0 --port 8080

# 2. 更新回调脚本使用宿主机 IP
OPC_CORE_URL = "http://10.188.153.187:8080"

# 3. 测试连接
curl http://10.188.153.187:8080/health
```

### Q4: 任务状态未更新

**症状**: Agent 回调成功，但任务状态仍是 `assigned`

**排查步骤**:
1. 检查 OPC 日志：`tail -f /tmp/opc.log`
2. 检查数据库：`SELECT status FROM tasks_v2 WHERE id = 'task_xxx'`
3. 确认回调处理逻辑正确执行

---

## 监控与运维

### 健康检查

```python
def agent_health_check(agent_id: str) -> dict:
    """检查 Agent 健康状态"""
    
    checks = {
        "config_valid": check_agent_config(agent_id),
        "can_execute": test_agent_execution(agent_id),
        "can_read_skill": test_agent_read_skill(agent_id),
        "callback_works": test_agent_callback(agent_id),
    }
    
    return {
        "agent_id": agent_id,
        "healthy": all(checks.values()),
        "checks": checks
    }
```

### 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| 任务完成率 | 成功完成的任务比例 | < 90% |
| 平均执行时间 | 任务从分配到完成的时间 | > 5分钟 |
| 回调成功率 | Agent 回调成功的比例 | < 95% |
| 预算消耗率 | 实际消耗/预估预算 | > 150% |

---

## 实施路线图

### 当前阶段（已完成）

- ✅ 使用 `opc_partner` 完成闭环测试
- ✅ 确定 Agent 配置最佳实践
- ✅ 修复回调路由和认证问题

### 下一阶段（待开发）

- [ ] 自动 Agent 创建流程
- [ ] Agent 健康检查系统
- [ ] Agent 性能监控

### 远期规划

- [ ] Agent 模板系统
- [ ] 动态扩缩容
- [ ] Agent 间协作

---

**设计时间**: 2026-03-23  
**版本**: v2.0（实践验证版）  
**状态**: ✅ 闭环测试通过  
**相关文档**:
- `AGENT_INTERACTION_BEST_PRACTICES.md`
- `AGENT_CONFIG_NOTES.md`
- `TASK_ASSIGNMENT_DESIGN_v2.md`
