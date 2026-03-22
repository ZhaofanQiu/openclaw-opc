# OPC 核心架构 v2.0

**日期**: 2026-03-23  
**版本**: v2.0 (重构版)  
**作者**: Kimi Claw

---

## 架构演进

### v1.0 问题

v1.0 架构的问题在于：
- OPC 试图直接控制 Agent 行为（发消息、收回复）
- 实际上无法有效约束 Agent 的执行过程
- Manual 只是发送给 Agent，Agent 未必会读

### v2.0 改进

v2.0 采用 **Skill 驱动** 架构：
- Agent 通过 **opc-bridge skill** 主动获取信息和能力
- OPC 只负责 **分配任务** 和 **接收结果**
- Manual 由 Agent **主动读取**，确保被使用

---

## 核心设计

### 三维度控制 (v2.0)

| 维度 | 形式 | 控制方式 |
|------|------|----------|
| **Bridge Skill** | 代码方法 | 提供 `opc_*` 函数，Agent 调用 |
| **Manual** | Markdown 文档 | Agent 主动 `opc_read_manual()` 读取 |
| **Message** | 文本消息 | OPC 通过 `sessions_send` 发送任务描述 |

**关键改进**: Agent 从"被动接收"变为"主动获取"，确保三维度控制都被执行。

---

## 交互流程

### 任务执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         任务分配阶段                             │
├─────────────────────────────────────────────────────────────────┤
│  OPC                                                              │
│   │  1. 构建任务消息 (包含 task_id, title, description)           │
│   │  2. 通过 sessions_send 发送给 Agent                          │
│   ▼                                                               │
│  Agent                                                            │
│   │  收到任务消息                                                  │
│   │  "你被分配了任务 xxx，请使用 opc_get_current_task() 获取详情" │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         任务执行阶段                             │
├─────────────────────────────────────────────────────────────────┤
│  Agent                                                            │
│   │  3. 调用 opc_get_current_task() 获取任务详情                 │
│   │  4. 调用 opc_read_manual("task", task_id) 读取任务手册       │
│   │  5. 调用 opc_read_manual("position", position_id) 读岗位手册 │
│   │  6. 调用 opc_get_budget() 查询预算                           │
│   │  7. 执行任务（按需调用 opc_db_read/write）                   │
│   │  8. 调用 opc_report_task_result() 报告结果                   │
│   ▼                                                               │
│  OPC (通过 Skill API 接收报告)                                    │
│   │  9. 更新任务状态                                              │
│   │  10. 计算成本，更新预算                                        │
│   │  11. 触发后续流程（如下一步任务）                              │
└─────────────────────────────────────────────────────────────────┘
```

### 关键点

1. **OPC → Agent**: 单向通知（任务分配）
2. **Agent → OPC**: 通过 Skill API 调用（获取信息、报告结果）
3. **Agent 自主**: Agent 决定何时读取手册、如何使用工具

---

## 核心模块

### core/

```
core/
├── agent_interaction_v2.py   # OPC → Agent 交互
├── skill_definition.py       # opc-bridge skill 定义
├── skill_installer.py        # skill 安装器
├── task_executor_v2.py       # 任务执行器
├── bridge_skill.py           # Bridge Skill 文本定义
└── manual_application.py     # 手册应用
```

### opc-bridge Skill

**位置**: `~/.openclaw/skills/opc-bridge/`

**文件**:
- `manifest.yaml` - Skill 配置
- `skill.py` - Skill 实现
- `instructions.md` - 使用说明

**提供的方法**:

```python
# 任务管理
opc_get_current_task()           # 获取当前任务
opc_report_task_result()         # 报告任务结果

# 手册读取
opc_read_manual(type, id)        # 读取手册

# 数据库操作
opc_db_read(table, query)        # 读取数据
opc_db_write(table, data)        # 写入数据

# 预算查询
opc_get_budget()                 # 获取预算
```

---

## API 设计

### Skill API (Agent → OPC)

这些 API 由 opc-bridge skill 调用：

```
GET  /api/agents/{agent_id}/current-task    # 获取当前任务
POST /api/tasks/{task_id}/report            # 报告任务结果
GET  /api/manuals/{type}/{id}               # 读取手册
POST /api/db/read                           # 数据库读取
POST /api/db/write                          # 数据库写入
GET  /api/agents/{agent_id}/budget          # 获取预算
```

### Task API (用户 → OPC)

```
GET  /api/tasks                    # 任务列表
POST /api/tasks                    # 创建任务
GET  /api/tasks/{id}               # 任务详情
POST /api/tasks/{id}/assign        # 分配任务
POST /api/tasks/{id}/start         # 开始任务
POST /api/tasks/{id}/complete      # 完成任务
```

---

## 部署流程

### 一键部署

```bash
# 1. 部署 OPC Core Service
./scripts/deploy.sh

# 2. 安装 opc-bridge skill 到 OpenClaw
python -m src.core.skill_installer --api-key xxx

# 3. 验证安装
python -c "from src.core.skill_installer import check_skill_installed; print(check_skill_installed())"
```

### Skill 自动安装

```python
from src.core.skill_installer import install_skill

# 安装 skill 到用户的 OpenClaw
install_skill(
    opc_api_key="your-api-key",
    openclaw_dir="~/.openclaw"
)
```

---

## 优势

### 相比 v1.0

| 方面 | v1.0 | v2.0 |
|------|------|------|
| 控制方式 | OPC 强制推送 | Agent 主动获取 |
| Manual 使用 | 发送后无法确认 | Agent 主动读取 |
| 灵活性 | 低 | 高 |
| 可扩展性 | 差 | 好 |
| Agent 体验 | 被动接受 | 主动执行 |

### 核心价值

1. **确保三维度控制被执行**
   - Agent 必须调用 `opc_read_manual()` 才能看到手册
   - 比单纯发送消息更可靠

2. **Agent 有自主权**
   - Agent 可以决定何时读取手册
   - Agent 可以按需调用工具
   - 更符合 OpenClaw 的设计理念

3. **易于扩展**
   - 新增能力只需在 skill 中添加方法
   - 不影响 OPC 核心逻辑

---

## 待办

### Phase 1: 核心实现

- [x] skill_definition.py - Skill 定义
- [x] skill_installer.py - Skill 安装器
- [x] agent_interaction_v2.py - 交互模块
- [x] task_executor_v2.py - 执行器

### Phase 2: API 实现

- [ ] Skill API 端点（Agent → OPC）
- [ ] Task API 端点（用户 → OPC）
- [ ] 数据库操作接口

### Phase 3: 集成测试

- [ ] Skill 安装测试
- [ ] 任务分配测试
- [ ] Agent 执行测试
- [ ] 结果报告测试

---

## 参考

- `core/agent_interaction_v2.py` - 交互实现
- `core/skill_definition.py` - Skill 定义
- `core/skill_installer.py` - 安装器
- `core/task_executor_v2.py` - 执行器
