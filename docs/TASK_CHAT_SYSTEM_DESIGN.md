# OPC 任务系统 v3.0 - 离线聊天协作模型

## 核心概念

**任务 = 离线聊天会话**
- 任务分配 = 聊天的第一句话
- 员工回复 = 聊天消息
- 任务详情页 = 完整聊天记录

---

## 任务类型

### 1. 单员工任务（简单任务）

```
┌─────────────────────────────────────────┐
│  任务发布者（用户或其他员工）              │
│     ↓ 分配任务                           │
│  执行员工                                │
│     ↓ 回复                               │
│  发布者查看 → 反馈/返工/打分结算          │
└─────────────────────────────────────────┘
```

**特点：**
- 一对一聊天
- 发布者有反馈权、返工权、评分权
- 新消息推送通知

### 2. 复杂任务流（多步骤）

```
┌─────────────────────────────────────────────────────────────┐
│  任务发布者                                                  │
│     ↓ 创建任务流                                             │
│  Step 1 (员工A)                                              │
│     ↓ 完成 / 返工                                            │
│  Step 2 (员工B)                                              │
│     ↓ 完成 / 返工给A                                         │
│  Step 3 (员工C)                                              │
│     ↓ 完成                                                   │
│  返回给发布者 → 反馈/评分/结算                                │
└─────────────────────────────────────────────────────────────┘
```

**流转规则：**
- **推进**：当前步骤完成 → 自动流转到下一步
- **返工**：当前步骤退回 → 返回上一步并附带反馈
- **协作**：每步的输入 = 上一步的输出 + 返工反馈（如有）

---

## 数据模型

### 任务步骤（核心）

```python
class TaskStep:
    """任务步骤 = 聊天会话容器"""
    
    id: str
    task_id: str
    step_index: int              # 步骤序号
    step_name: str               # 步骤名称
    
    # 参与者
    assigner_id: str             # 分配者（上一步员工 或 任务发布者）
    assigner_type: str           # "user" | "agent"
    executor_id: str             # 执行员工
    
    # 状态
    status: "pending" | "assigned" | "in_progress" | 
           "completed" | "failed" | "rework"
    
    # 聊天历史
    messages: List[TaskMessage]  # 该步骤的所有消息
    
    # 流转控制
    next_step_id: str            # 下一步（null=最后一步）
    prev_step_id: str            # 上一步（null=第一步）
    rework_count: int            # 返工次数
    max_rework: int              # 最大返工次数
    
    # 输入输出
    input_context: dict          # 步骤输入（上一步输出+返工反馈）
    output_result: dict          # 步骤输出
    
    # 评价
    score: int                   # 1-5分
    feedback: str                # 文字反馈
    settled: bool                # 是否已结算


class TaskMessage:
    """任务消息 = 聊天记录"""
    
    id: str
    step_id: str
    
    # 发送者
    sender_id: str
    sender_type: "user" | "agent" | "system"
    sender_name: str
    
    # 内容
    content: str                 # 消息文本
    message_type: "assignment" | "reply" | "feedback" | 
                   "rework" | "progress" | "system"
    
    # 附件
    attachments: List[{
        "type": "file" | "code" | "database_record",
        "name": str,
        "path": str,
        "preview": str
    }]
    
    # 状态
    is_read: bool
    read_at: datetime
    
    created_at: datetime
```

---

## 核心 API

### 1. 任务流转 API

```python
# 员工完成任务，推进到下一步
POST /api/task-steps/{step_id}/complete
Headers: X-Task-Token: xxx
Body: {
    "result_summary": "完成数据分析，生成报告",
    "output_files": [
        {"path": "/tasks/xxx/report.md", "type": "markdown"}
    ],
    "output_data": {...}  # 结构化输出
}
→ 自动创建下一步并通知下一个员工

# 员工返工（退回上一步）
POST /api/task-steps/{step_id}/rework
Headers: X-Task-Token: xxx
Body: {
    "rework_reason": "数据格式不符合要求，需要重新清洗",
    "suggestions": "请参考标准格式 xxx"
}
→ 原步骤状态变为 rework，上一步状态变为 in_progress
→ 上一步员工收到返工通知

# 员工报告失败
POST /api/task-steps/{step_id}/fail
Headers: X-Task-Token: xxx
Body: {
    "fail_reason": "无法访问数据库",
    "error_details": "Connection timeout"
}
→ 任务流暂停，通知任务发布者
```

### 2. 消息交互 API

```python
# 发送反馈/追问（发布者 → 员工）
POST /api/task-steps/{step_id}/feedback
Body: {
    "content": "关于第三点，能否详细说明？",
    "sender_id": "user_xxx",  # 或 agent_xxx
    "sender_type": "user"
}
→ 添加到消息历史，通知员工

# 员工回复反馈
POST /api/task-steps/{step_id}/reply
Headers: X-Task-Token: xxx
Body: {
    "content": "详细说明如下...",
    "attachments": [...]
}

# 获取聊天记录
GET /api/task-steps/{step_id}/messages
→ 返回完整消息列表
```

### 3. 评价结算 API

```python
# 发布者评价并结算
POST /api/task-steps/{step_id}/settle
Body: {
    "score": 4,                    # 1-5分
    "feedback": "完成质量不错，但速度可以更快",
    "bonus_tokens": 100            # 额外奖励（可选）
}
→ 更新员工预算、技能成长
→ 标记步骤完成
```

---

## 消息推送机制

### 推送场景

| 场景 | 接收者 | 推送内容 |
|------|--------|----------|
| 新任务分配 | 执行员工 | "您有一个新任务：xxx" |
| 员工回复 | 任务发布者 | "员工xxx回复了任务" |
| 推进到下一步 | 下一步员工 | "任务xxx需要您处理" |
| 返工通知 | 上一步员工 | "任务被返工，原因：xxx" |
| 任务失败 | 任务发布者 | "任务执行失败：xxx" |
| 收到反馈 | 执行员工 | "发布者有了新的反馈" |

### 推送方式

```python
# 站内通知（消息中心）
notification_service.send(
    recipient_id=agent_id,
    type="task_assigned",
    title="新任务",
    message="您有一个新任务：数据分析",
    link="/tasks/xxx"
)

# WebSocket 实时推送
websocket.emit(f"agent:{agent_id}", {
    "type": "new_task",
    "task_id": "xxx",
    "title": "数据分析"
})

# 外部消息（飞书/Discord等 - 可选）
if agent.external_channel:
    send_external_message(agent.external_channel, message)
```

---

## 任务详情页设计

### 页面结构

```
┌─────────────────────────────────────────────────────────────┐
│ 📋 任务标题                               [状态: 进行中]    │
├─────────────────────────────────────────────────────────────┤
│  步骤1    步骤2    步骤3    步骤4                          │
│   (✓)    → (✓)    → (▶)    → (○)                         │
│  员工A   员工B   员工C   员工D                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  💬 当前步骤对话                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 👤 你（分配者）                                      │   │
│  │ 请分析这个数据文件，生成可视化报告                    │   │
│  │ [附件: data.csv]                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🤖 员工小李                                          │   │
│  │ 好的，我来进行数据分析。预计2小时完成。              │   │
│  │                                                     │   │
│  │ 更新：已完成数据清洗，正在进行可视化...              │   │
│  │ [时间戳: 10:30]                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🤖 员工小李                                          │   │
│  │ 分析完成！                                           │   │
│  │                                                     │   │
│  │ 主要发现：                                           │   │
│  │ 1. Q3销售额增长23%                                  │   │
│  │ 2. 华东区表现最佳                                    │   │
│  │                                                     │   │
│  │ [附件: report.md] [附件: chart.png]                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [需要修改，返工]  [追问]  [确认完成并评价]                  │
└─────────────────────────────────────────────────────────────┘
```

### 操作按钮（根据角色和状态）

**任务发布者视角：**
- 进行中 → [追问] [返工] [确认完成并评价]
- 已完成 → [再次分配（类似任务）]

**执行员工视角：**
- 被分配 → [开始执行] [拒绝]
- 执行中 → [发送进度更新] [请求帮助] [完成任务]
- 有反馈 → [回复反馈]

**多步骤任务（中间步骤员工）：**
- 完成 → [推进到下一步] [返工给上一步]

---

## Bridge Skill 集成

### 消息格式

```
📋 新任务分配 | 任务ID: task_xxx | 步骤: 数据分析

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 任务要求
请使用 opc-bridge skill 完成以下任务：
{task_description}

## 📁 可用资源
- 数据库访问（通过 bridge）
- 文件系统（通过 bridge）
- 网络搜索（通过 bridge）

## 📤 输出要求
完成任务后，请：
1. 调用 /api/task-steps/{step_id}/complete 报告完成
2. 如有文件输出，保存到指定路径
3. 在此回复简要说明

## 🔗 任务Token
{task_token}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 返工机制详细流程

```
Step 2 (员工B) 发现 Step 1 (员工A) 的输出有问题

员工B 调用 POST /api/task-steps/step_2/rework
{
    "rework_reason": "数据格式错误，缺少时间戳字段",
    "suggestions": "请参考 schema_v2.json 重新导出"
}

系统处理：
1. Step 2 状态变为 "waiting_rework"
2. Step 1 状态变为 "rework"（从 completed 回退）
3. 员工A 收到返工通知
4. Step 1 的消息历史新增一条系统消息：
   "员工B 返工此步骤，原因：数据格式错误..."

员工A 重新执行后：
→ 调用 complete，Step 1 回到 completed
→ Step 2 状态自动变为 in_progress
→ 员工B 收到通知继续处理
```

**返工限制：**
- 每步最大返工次数（默认 3 次）
- 超过限制 → 任务失败，通知发布者介入

---

## Token 监控（自动）

```python
# 系统在后台监控每个执行中任务的 token 消耗
class TaskTokenMonitor:
    def monitor_step(self, step_id: str, agent_id: str):
        """持续监控步骤的 token 消耗"""
        while step.status == "in_progress":
            status = session_status(agent_id=agent_id)
            
            step.actual_tokens = status.total_tokens
            step.cost_estimated = False
            db.commit()
            
            # 预算预警
            if step.actual_tokens > step.budget_tokens * 0.8:
                notification.send(
                    recipient=step.assigner_id,
                    message=f"任务 {step.id} Token 消耗超过80%"
                )
            
            time.sleep(60)  # 每分钟更新
```

---

## 实施优先级

### Phase 1: 核心聊天系统
- [ ] TaskStep + TaskMessage 模型
- [ ] 消息 API（分配、回复、反馈）
- [ ] 任务详情页（聊天记录界面）

### Phase 2: 任务流转
- [ ] complete/rework/fail API
- [ ] 步骤推进逻辑
- [ ] 返工机制

### Phase 3: 评价结算
- [ ] 评分系统
- [ ] 预算扣减
- [ ] 技能成长

### Phase 4: 消息推送
- [ ] 站内通知
- [ ] WebSocket 实时推送
- [ ] 外部渠道集成

---

*设计时间: 2026-03-23*
*版本: v3.0 - 离线聊天协作模型*
