# OPC Agent 使用策略

## 问题背景

- 用户的 OpenClaw 环境中已有 `main` agent 正在执行其他任务
- 直接使用用户的 agent 会干扰其正常工作
- 需要隔离 OPC 的 agent 与用户的 agent

## 解决方案

### 1. Agent 命名规范

OPC 只使用以下命名规范的 agent：

```
opc_<name>          # 通用员工
opc_partner         # Partner 助手（已存在）
opc_employee_<id>   # 特定员工
opc_system          # 系统级任务
```

**禁止使用**：
- `main` - 用户的主 agent
- `default` - 默认 agent
- 用户自定义的其他 agent

### 2. Agent 创建策略

#### 方案 A: 预创建（推荐）

在 OPC 初始化时，通过 OpenClaw CLI 创建所需的 agent：

```bash
# 创建 Partner agent
openclaw agents create opc_partner --description "OPC Partner Assistant"

# 创建员工 agent
openclaw agents create opc_emp_001 --description "OPC Employee - 实习生小刘"
```

#### 方案 B: 动态创建

在创建员工时，自动创建对应的 agent：

```python
# 伪代码
def create_employee(name, position):
    agent_id = f"opc_emp_{generate_id()}"
    
    # 1. 创建 OpenClaw agent
    subprocess.run([
        "openclaw", "agents", "create", agent_id,
        "--description", f"OPC Employee - {name}"
    ])
    
    # 2. 创建 OPC 员工记录
    employee = Employee.create(
        name=name,
        openclaw_agent_id=agent_id,
        ...
    )
    
    return employee
```

### 3. 配置项

在 `config.py` 或环境变量中添加：

```python
# OPC Agent 配置
OPC_AGENT_PREFIX = "opc_"           # Agent ID 前缀
OPC_AGENT_AUTO_CREATE = True        # 是否自动创建 agent
OPC_DEFAULT_PARTNER_AGENT = "opc_partner"  # 默认 Partner agent

# Agent 黑名单（禁止使用的 agent）
OPC_AGENT_BLACKLIST = ["main", "default"]
```

### 4. 验证逻辑

在发送消息前，验证 agent 是否可用：

```python
def validate_agent(agent_id: str) -> bool:
    """验证 agent 是否可用于 OPC"""
    
    # 检查黑名单
    if agent_id in OPC_AGENT_BLACKLIST:
        return False
    
    # 检查前缀（如果配置了强制前缀）
    if OPC_ENFORCE_PREFIX and not agent_id.startswith(OPC_AGENT_PREFIX):
        return False
    
    # 检查 agent 是否存在
    result = subprocess.run(
        ["openclaw", "agents", "list", "--json"],
        capture_output=True, text=True
    )
    agents = json.loads(result.stdout)
    
    return agent_id in [a["id"] for a in agents]
```

### 5. 工作流程

#### 员工入职流程

```
1. HR (用户) 在 OPC Dashboard 创建员工
   ↓
2. OPC 自动创建 OpenClaw agent (opc_emp_<id>)
   ↓
3. OPC 配置 agent 工作空间 (SKILL.md + TOOLS.md)
   ↓
4. 员工就绪，等待任务分配
```

#### 任务分配流程

```
1. Manager (用户) 分配任务给员工
   ↓
2. OPC 调用 OpenClaw agent (opc_emp_<id>)
   ↓
3. Agent 通过 Skill 读取手册、报告进度
   ↓
4. 任务完成，Agent 调用 opc_report_task_result()
```

### 6. 隔离性保证

| 层面 | 隔离措施 |
|------|----------|
| Agent ID | opc_ 前缀命名空间 |
| 工作空间 | 独立的工作目录 |
| 配置 | 独立的 IDENTITY.md / SOUL.md |
| 会话 | 独立的 session key |
| 资源 | 独立的预算限制 |

## 实现建议

### 短期（当前）

1. 使用已存在的 `opc_partner` 进行测试
2. 添加 agent 黑名单验证
3. 在文档中明确说明 agent 使用规范

### 中期

1. 实现自动 agent 创建
2. 员工入职时自动绑定 agent
3. 添加 agent 状态监控

### 长期

1. 支持 agent 模板（快速创建同类员工）
2. agent 资源池管理
3. 动态扩缩容

## 相关文件

- `backend/src/core/openclaw_client.py` - 添加验证逻辑
- `backend/src/core/agent_manager.py` - agent 生命周期管理（新增）
- `backend/src/routers/agents.py` - 创建员工时绑定 agent
- `backend/src/models/agent_v2.py` - 添加 agent 状态字段