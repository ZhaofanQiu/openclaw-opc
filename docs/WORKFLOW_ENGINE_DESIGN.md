# 统一工作流引擎设计文档

## 核心概念

### 1. 流程定义 (Workflow Definition)
每个业务任务对应一个流程模板，定义步骤序列、角色、流转规则。

### 2. 步骤类型 (Step Types)
- **PLAN** - 规划：分析需求，制定方案
- **EXECUTE** - 执行：实际完成工作
- **REVIEW** - 评审：对工作成果进行评分
- **APPROVE** - 审批：预算/方案审批
- **TEST** - 测试：验证功能/质量
- **VERIFY** - 验证：最终确认
- **DELIVER** - 交付：交给用户

### 3. 流转动作 (Actions)
- **PASS** - 通过，进入下一步
- **REJECT** - 不通过，返回返工
- **REWORK** - 标记需要返工
- **SKIP** - 跳过（特定条件下）
- **ESCALATE** - 升级（给Partner）

### 4. 返工机制
- 任何步骤可以指定返工目标步骤
- 返工时携带评分和评论
- 返工次数追踪

## 数据模型

### WorkflowTemplate（流程模板）
```
- id: 模板ID
- name: 模板名称
- description: 描述
- steps: JSON数组，定义步骤序列
  [
    {
      "step_id": "plan",
      "name": "需求规划",
      "type": "PLAN",
      "assignee_role": "architect",  // 可指定角色或具体agent
      "next_steps": ["execute"],     // 默认下一步
      "rework_target": null,         // 返工目标
      "approval_threshold": null,    // 审批阈值（仅APPROVE类型）
      "auto_assign": false,          // 是否自动分配
      "timeout_hours": 24            // 超时时间
    },
    {
      "step_id": "execute",
      "name": "开发实现",
      "type": "EXECUTE",
      "assignee_role": "developer",
      "next_steps": ["review"],
      "rework_target": "execute",    // 返工回到自己
    },
    {
      "step_id": "review",
      "name": "代码评审",
      "type": "REVIEW",
      "assignee_role": "reviewer",
      "next_steps": ["test"],
      "rework_target": "execute",    // 不通过返回开发
      "review_criteria": ["quality", "performance", "security"]
    },
    {
      "step_id": "test",
      "name": "测试验证",
      "type": "TEST",
      "assignee_role": "tester",
      "next_steps": ["verify"],
      "rework_target": "execute",
    },
    {
      "step_id": "verify",
      "name": "最终确认",
      "type": "VERIFY",
      "assignee_role": "partner",    // Partner专属
      "next_steps": ["deliver"],
      "rework_target": "execute",
    },
    {
      "step_id": "deliver",
      "name": "交付用户",
      "type": "DELIVER",
      "assignee_role": "partner",
      "next_steps": [],               // 流程结束
    }
  ]
- is_active: 是否启用
- created_at: 创建时间
```

### WorkflowInstance（流程实例）
```
- id: 实例ID
- template_id: 模板ID
- title: 任务标题
- description: 任务描述
- status: PENDING/IN_PROGRESS/COMPLETED/CANCELLED
- current_step_id: 当前步骤ID
- created_by: 创建者
- created_at: 创建时间
- completed_at: 完成时间
- context: JSON - 流程上下文数据
```

### WorkflowStepInstance（步骤实例）
```
- id: 步骤实例ID
- workflow_id: 流程实例ID
- step_id: 步骤定义ID
- status: PENDING/ASSIGNED/IN_PROGRESS/COMPLETED/REWORK
- assignee_id: 分配的员工ID
- assigned_at: 分配时间
- started_at: 开始时间
- completed_at: 完成时间
- result: 结果数据（JSON）
  {
    "action": "PASS|REJECT|REWORK",
    "score": 85,                    // REVIEW类型的评分
    "comment": "评审意见",
    "artifacts": ["代码链接", "文档"],
    "budget_used": 500
  }
- review_scores: JSON - 多维度评分
  {
    "quality": 90,
    "performance": 85,
    "security": 88
  }
- rework_count: 返工次数
- previous_step_id: 上一步（用于返工回溯）
```

### WorkflowHistory（流程历史）
```
- id: 历史记录ID
- workflow_id: 流程实例ID
- step_instance_id: 步骤实例ID
- action: 执行的动作
- from_status: 变更前状态
- to_status: 变更后状态
- actor_id: 执行者
- comment: 备注
- created_at: 时间
```

## API设计

### 流程模板管理
```
POST   /api/workflow-templates          // 创建模板
GET    /api/workflow-templates          // 列取模板
GET    /api/workflow-templates/{id}     // 获取模板
PUT    /api/workflow-templates/{id}     // 更新模板
DELETE /api/workflow-templates/{id}     // 删除模板
```

### 流程实例管理
```
POST   /api/workflows                   // 启动流程
GET    /api/workflows                   // 列取流程
GET    /api/workflows/{id}              // 获取流程详情
POST   /api/workflows/{id}/cancel       // 取消流程
GET    /api/workflows/{id}/history      // 流程历史
```

### 步骤执行
```
POST   /api/workflows/{id}/steps/current/assign    // 分配当前步骤
POST   /api/workflows/{id}/steps/current/start     // 开始执行
POST   /api/workflows/{id}/steps/current/complete  // 完成步骤
POST   /api/workflows/{id}/steps/current/rework    // 标记返工
GET    /api/workflows/pending/{agent_id}           // 获取员工待办
```

### 评审专用
```
POST   /api/workflows/{id}/steps/current/review    // 提交评审
       // body: { scores: {quality: 90, ...}, comment: "", action: "PASS|REJECT" }
```

## 场景示例

### 场景1：简单开发任务
```
[规划] → [开发] → [测试] → [交付]
```

### 场景2：需要审批的大任务
```
[规划] → [审批] → [开发] → [评审] → [测试] → [验证] → [交付]
         ↓
      (预算>1000才需要)
```

### 场景3：评审不通过返工
```
[开发] → [评审] --不通过--> [开发]
           ↓通过
         [测试]
```

## 与现有系统的整合

### 1. 任务系统整合
- 现有的 Task 可以关联到一个 WorkflowInstance
- Task 的 assign/complete 操作改为驱动 Workflow

### 2. 审批流整合
- 审批作为 Workflow 中的一种步骤类型
- 原有 ApprovalRequest 数据迁移到 WorkflowStepInstance

### 3. 预算系统整合
- 每个步骤可以消耗预算
- 累计预算消耗追踪在 WorkflowInstance 上

## 实现优先级

1. **核心模型** - WorkflowTemplate, WorkflowInstance, WorkflowStepInstance
2. **基础服务** - 启动流程、步骤流转
3. **返工机制** - 评分、返工、回溯
4. **角色分配** - 根据角色自动分配员工
5. **预算整合** - 步骤级预算控制
6. **前端界面** - 流程可视化、待办列表

## 数据库迁移策略

### 方案A：完全替换（推荐）
- 新系统完全替换旧的任务/审批系统
- 旧数据迁移到新模型
- 一次性切换

### 方案B：渐进式
- 新 Workflow 系统并行运行
- 逐步将旧任务迁移到新系统
- 过渡期双轨运行
