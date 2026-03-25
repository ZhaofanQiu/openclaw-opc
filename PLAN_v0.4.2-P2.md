# OpenClaw OPC v0.4.2-P2 详细规划文档

**版本**: v0.4.2-P2  
**目标**: 工作流增强功能（模板、可视化、历史、统计）  
**预计周期**: 4-5 天  
**最后更新**: 2026-03-25

---

## 一、功能清单

用户选择开发的 P2 功能：

| # | 功能 | 模块 | 工时 | 优先级 |
|---|------|------|------|--------|
| 16 | 工作流模板（保存/复用） | database + core + ui | 1.5d | 🔴 高 |
| 18 | 流程图可视化（SVG） | ui | 1.5d | 🟡 中 |
| 19 | 执行历史时间线 | core + ui | 1d | 🟡 中 |
| 20 | 工作流统计报表 | core + ui | 1d | 🟡 中 |

**总计**: 5 天

---

## 二、功能 #16: 工作流模板

### 2.1 需求描述
- 将常用工作流保存为模板
- 从模板快速创建工作流
- 模板分类和标签管理
- 模板版本控制

### 2.2 数据模型设计

```python
# opc_database/models/workflow_template.py

class WorkflowTemplate(Base):
    """工作流模板"""
    
    __tablename__ = "workflow_templates"
    
    # 基本信息
    id: str  # tmpl-xxx
    name: str  # 模板名称
    description: Optional[str]  # 描述
    
    # 模板内容（JSON存储步骤配置）
    steps_config: str  # JSON 数组，存储 WorkflowStepConfig
    
    # 分类和标签
    category: str  # 分类：research/writing/review/etc
    tags: Optional[str]  # JSON 数组 ["AI", "医疗", "报告"]
    
    # 使用统计
    usage_count: int  # 使用次数
    avg_rating: float  # 平均评分 0-5
    rating_count: int  # 评分次数
    
    # 版本控制
    version: int  # 版本号
    parent_template_id: Optional[str]  # 父模板ID（Fork用）
    
    # 创建者
    created_by: str  # 用户ID
    is_system: bool  # 是否系统预设模板
    is_public: bool  # 是否公开
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]  # 最后使用时间


class WorkflowTemplateRating(Base):
    """模板评分"""
    
    __tablename__ = "workflow_template_ratings"
    
    id: str
    template_id: str  # 关联模板
    user_id: str  # 评分用户
    rating: int  # 1-5 星
    comment: Optional[str]  # 评论
    created_at: datetime
```

### 2.3 API 设计

```python
# opc_core/api/workflow_templates.py

# 模板 CRUD
POST   /api/v1/workflow-templates              # 创建模板
GET    /api/v1/workflow-templates              # 列表（支持筛选）
GET    /api/v1/workflow-templates/{id}         # 详情
PUT    /api/v1/workflow-templates/{id}         # 更新
DELETE /api/v1/workflow-templates/{id}         # 删除

# 从模板创建工作流
POST   /api/v1/workflow-templates/{id}/create-workflow  # 实例化

# 评分
POST   /api/v1/workflow-templates/{id}/rate    # 评分
GET    /api/v1/workflow-templates/{id}/ratings # 评分列表

# Fork
POST   /api/v1/workflow-templates/{id}/fork    # Fork模板
```

### 2.4 Service 层设计

```python
# opc_core/services/workflow_template_service.py

class WorkflowTemplateService:
    
    async def create_template(
        self,
        name: str,
        description: str,
        steps_config: list[WorkflowStepConfig],
        category: str,
        tags: list[str],
        created_by: str,
        is_public: bool = False,
    ) -> WorkflowTemplate:
        """创建模板"""
        
    async def create_workflow_from_template(
        self,
        template_id: str,
        initial_input: dict,
        created_by: str,
    ) -> WorkflowResult:
        """从模板创建工作流"""
        
    async def fork_template(
        self,
        template_id: str,
        new_name: str,
        created_by: str,
    ) -> WorkflowTemplate:
        """Fork模板"""
        
    async def rate_template(
        self,
        template_id: str,
        user_id: str,
        rating: int,
        comment: Optional[str],
    ) -> None:
        """评分模板"""
```

### 2.5 UI 设计

**模板列表页** (`WorkflowTemplatesView.vue`)
```
┌─────────────────────────────────────────────────────────┐
│  工作流模板库                              [创建模板]   │
├─────────────────────────────────────────────────────────┤
│  🔍 搜索模板    [全部] [研究] [写作] [审核] [我的]       │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ 📊 AI研究   │ │ 📝 内容创作 │ │ 🔍 代码审查 │       │
│  │ 研究→分析   │ │ 大纲→撰写   │ │ 自检→互审   │       │
│  │ ⭐ 4.8 (23) │ │ ⭐ 4.5 (15) │ │ ⭐ 4.9 (8)  │       │
│  │ [使用] [Fork]│ │ [使用] [Fork]│ │ [使用] [Fork]│       │
│  └─────────────┘ └─────────────┘ └─────────────┘       │
│  ┌─────────────┐                                       │
│  │ 🏥 医疗报告 │ ← 我的模板                            │
│  │ 3步骤工作流 │                                       │
│  │ [使用] [编辑][删除]                                  │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

**模板创建弹窗**
```
┌─────────────────────────────────────────────────────────┐
│  保存为模板                                     [×]     │
├─────────────────────────────────────────────────────────┤
│  模板名称 *                                             │
│  [AI医疗研究报告模板                              ]     │
│                                                         │
│  描述                                                   │
│  [用于生成AI在医疗领域的综合分析报告...            ]     │
│                                                         │
│  分类 *                                                 │
│  [研究分析 ▼]                                           │
│                                                         │
│  标签                                                   │
│  [AI] [医疗] [研究报告] [+]                             │
│                                                         │
│  可见性                                                 │
│  ( ) 私有  (•) 公开                                     │
│                                                         │
│           [取消]  [保存模板]                            │
└─────────────────────────────────────────────────────────┘
```

### 2.6 实现步骤

| 步骤 | 任务 | 工时 | 文件 |
|------|------|------|------|
| 1 | 创建 WorkflowTemplate 模型 | 0.5h | `models/workflow_template.py` |
| 2 | 创建数据库迁移 | 0.5h | `migrations/add_workflow_template.py` |
| 3 | 实现 TemplateService | 2h | `services/workflow_template_service.py` |
| 4 | 实现 API 路由 | 1.5h | `api/workflow_templates.py` |
| 5 | 实现模板列表页 | 2h | `views/WorkflowTemplatesView.vue` |
| 6 | 实现模板创建弹窗 | 1h | `components/WorkflowTemplateDialog.vue` |
| 7 | 集成到工作流创建页 | 1h | 修改 `WorkflowCreateView.vue` |

---

## 三、功能 #18: 流程图可视化

### 3.1 需求描述
- SVG 绘制工作流流程图
- 步骤节点可视化展示
- 连接线显示执行状态
- 返工路径特殊标记

### 3.2 技术方案

使用 SVG + 自定义布局算法：
```
┌─────────────────────────────────────────────────────────┐
│  工作流流程图: AI医疗研究报告                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐        │
│   │ Step 1  │─────→│ Step 2  │─────→│ Step 3  │        │
│   │ 🟢 完成 │      │ 🟡 执行 │      │ ⚪ 等待 │        │
│   │ Alice   │      │ Bob     │      │ Carol   │        │
│   └────┬────┘      └────┬────┘      └─────────┘        │
│        │                │                               │
│        └────────────────┘                               │
│           ↱ 返工路径                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.3 组件设计

```vue
<!-- components/WorkflowDiagram.vue -->
<template>
  <svg :width="width" :height="height">
    <!-- 连接线 -->
    <g class="edges">
      <path
        v-for="edge in edges"
        :key="edge.id"
        :d="edge.path"
        :class="['edge', edge.status]"
      />
      <!-- 返工线（虚线） -->
      <path
        v-for="rework in reworks"
        :key="rework.id"
        :d="rework.path"
        class="edge rework"
        stroke-dasharray="5,5"
      />
    </g>
    
    <!-- 节点 -->
    <g class="nodes">
      <WorkflowNode
        v-for="node in nodes"
        :key="node.id"
        :x="node.x"
        :y="node.y"
        :title="node.title"
        :status="node.status"
        :employee="node.employee"
        :step-index="node.stepIndex"
        :is-rework="node.isRework"
      />
    </g>
  </svg>
</template>
```

### 3.4 布局算法

```typescript
// 水平布局算法
function calculateLayout(tasks: WorkflowTask[], config: LayoutConfig): Layout {
  const nodeWidth = 180;
  const nodeHeight = 80;
  const gapX = 100;
  const gapY = 50;
  
  // 单行水平布局
  const nodes = tasks.map((task, index) => ({
    id: task.id,
    x: index * (nodeWidth + gapX),
    y: 0, // 如有返工分支可增加Y偏移
    width: nodeWidth,
    height: nodeHeight,
    ...task
  }));
  
  // 计算连接线
  const edges = [];
  for (let i = 0; i < tasks.length - 1; i++) {
    edges.push({
      id: `${tasks[i].id}-${tasks[i+1].id}`,
      from: nodes[i],
      to: nodes[i+1],
      path: calculatePath(nodes[i], nodes[i+1]),
      status: tasks[i].status,
    });
  }
  
  return { nodes, edges };
}
```

### 3.5 节点状态样式

| 状态 | 颜色 | 图标 | 说明 |
|------|------|------|------|
| pending | ⬜ 灰色 | ⚪ | 等待执行 |
| assigned | 🟡 黄色 | 📋 | 已分配 |
| in_progress | 🔵 蓝色 | 🔄 | 执行中 |
| completed | 🟢 绿色 | ✅ | 已完成 |
| rework | 🟠 橙色 | ↩️ | 返工中 |

### 3.6 实现步骤

| 步骤 | 任务 | 工时 |
|------|------|------|
| 1 | 创建 WorkflowNode 组件 | 1h |
| 2 | 实现 SVG 流程图组件 | 3h |
| 3 | 实现布局算法 | 2h |
| 4 | 添加动画效果 | 1h |
| 5 | 集成到详情页 | 1h |
| 6 | 添加交互（点击节点查看详情） | 1h |

---

## 四、功能 #19: 执行历史时间线

### 4.1 需求描述
- 展示工作流完整执行历史
- 包含任务开始、完成、返工等事件
- 时间轴形式展示
- 支持展开查看详情

### 4.2 数据模型

复用现有 `execution_log` 字段，增强内容：

```python
# 执行日志事件类型
class ExecutionEventType(str, Enum):
    WORKFLOW_CREATED = "workflow_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    REWORK_REQUESTED = "rework_requested"
    REWORK_COMPLETED = "rework_completed"
    WORKFLOW_COMPLETED = "workflow_completed"

# 日志条目结构
{
    "timestamp": "2026-03-25T10:30:00Z",
    "event_type": "task_completed",
    "step_index": 0,
    "task_id": "task-xxx",
    "employee_id": "emp-xxx",
    "employee_name": "Alice",
    "details": {
        "summary": "完成任务",
        "tokens_used": 500,
        "duration_seconds": 120,
    }
}
```

### 4.3 API 设计

```python
# GET /api/v1/workflows/{id}/timeline

Response:
{
    "workflow_id": "wf-xxx",
    "timeline": [
        {
            "timestamp": "2026-03-25T10:00:00Z",
            "event_type": "workflow_created",
            "title": "工作流创建",
            "description": "创建 3 步骤工作流",
            "actor": "user-xxx",
        },
        {
            "timestamp": "2026-03-25T10:05:00Z",
            "event_type": "task_assigned",
            "step_index": 0,
            "title": "Step 1: 资料收集",
            "description": "分配给 Alice",
            "actor": "system",
        },
        {
            "timestamp": "2026-03-25T10:30:00Z",
            "event_type": "task_completed",
            "step_index": 0,
            "title": "Step 1 完成",
            "description": "找到50篇相关论文",
            "actor": "Alice",
            "metadata": {
                "tokens_used": 500,
                "duration": "25分钟",
            }
        },
        {
            "timestamp": "2026-03-25T10:32:00Z",
            "event_type": "rework_requested",
            "step_index": 1,
            "title": "返工请求",
            "description": "Bob 请求 Step 1 返工：数据不完整",
            "actor": "Bob",
        },
    ]
}
```

### 4.4 UI 设计

```
┌─────────────────────────────────────────────────────────┐
│  执行历史时间线                                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│  2026-03-25 10:00                                       │
│  🟢 工作流创建                              by 用户      │
│     创建 3 步骤工作流：AI医疗研究报告                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│  2026-03-25 10:05                                       │
│  📋 Step 1 分配                             by 系统      │
│     资料收集 → 分配给 Alice                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│  2026-03-25 10:30                                       │
│  ✅ Step 1 完成                             by Alice     │
│     找到50篇相关论文                                    │
│     消耗: 500 tokens | 用时: 25分钟                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│  2026-03-25 10:32                                       │
│  ↩️ 返工请求                                by Bob       │
│     请求 Step 1 返工：数据不完整                        │
│     指令: 请补充数据来源引用                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.5 实现步骤

| 步骤 | 任务 | 工时 |
|------|------|------|
| 1 | 扩展执行日志事件类型 | 0.5h |
| 2 | 实现 TimelineService | 1.5h |
| 3 | 添加 timeline API | 1h |
| 4 | 实现时间线组件 | 2h |
| 5 | 集成到详情页 | 1h |

---

## 五、功能 #20: 工作流统计报表

### 5.1 需求描述
- 工作流成功率统计
- 平均耗时分析
- 返工率统计
- 员工效率排名

### 5.2 统计指标设计

```python
# opc_core/services/workflow_analytics_service.py

@dataclass
class WorkflowStats:
    """工作流统计"""
    # 基础统计
    total_workflows: int
    completed_workflows: int
    failed_workflows: int
    in_progress_workflows: int
    
    # 成功率
    completion_rate: float  # 完成率 %
    
    # 耗时统计（分钟）
    avg_duration: float  # 平均耗时
    min_duration: float
    max_duration: float
    
    # 返工统计
    total_reworks: int
    avg_reworks_per_workflow: float  # 平均返工次数
    rework_rate: float  # 返工率 %
    
    # 步骤统计
    avg_step_duration: list[StepDuration]  # 每步平均耗时


@dataclass
class EmployeeWorkflowStats:
    """员工工作流统计"""
    employee_id: str
    employee_name: str
    
    tasks_completed: int
    tasks_reworked: int
    avg_task_duration: float
    
    rework_rate: float  # 该员工任务的返工率
```

### 5.3 API 设计

```python
# GET /api/v1/analytics/workflows
# 查询参数: start_date, end_date, category

Response:
{
    "period": {"start": "2026-03-01", "end": "2026-03-25"},
    "overview": {
        "total_workflows": 45,
        "completed": 40,
        "failed": 2,
        "in_progress": 3,
        "completion_rate": 88.9,
    },
    "duration": {
        "avg_minutes": 125.5,
        "min_minutes": 45,
        "max_minutes": 320,
    },
    "rework": {
        "total_reworks": 15,
        "avg_per_workflow": 0.33,
        "rework_rate": 33.3,
    },
    "step_stats": [
        {"step_index": 0, "avg_minutes": 45, "rework_count": 3},
        {"step_index": 1, "avg_minutes": 60, "rework_count": 8},
        {"step_index": 2, "avg_minutes": 20, "rework_count": 4},
    ],
    "daily_trend": [
        {"date": "2026-03-20", "created": 3, "completed": 2},
        {"date": "2026-03-21", "created": 5, "completed": 4},
        ...
    ]
}

# GET /api/v1/analytics/workflows/employee-ranking
Response:
{
    "rankings": [
        {
            "employee_id": "emp-001",
            "employee_name": "Alice",
            "tasks_completed": 25,
            "avg_duration": 35.5,
            "rework_rate": 12.0,
            "score": 92.5,
        },
        ...
    ]
}
```

### 5.4 UI 设计

**统计报表页** (`WorkflowAnalyticsView.vue`)
```
┌─────────────────────────────────────────────────────────┐
│  工作流统计报表                              [导出PDF]  │
├─────────────────────────────────────────────────────────┤
│  时间范围: [最近7天 ▼]  分类: [全部 ▼]                  │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ 总工作流    │ │ 完成率      │ │ 平均耗时    │       │
│  │    45       │ │   88.9%     │ │  125分钟    │       │
│  └─────────────┘ └─────────────┘ └─────────────┘       │
│  ┌─────────────┐ ┌─────────────┐                       │
│  │ 返工率      │ │ 进行中      │                       │
│  │   33.3%     │ │    3        │                       │
│  └─────────────┘ └─────────────┘                       │
├─────────────────────────────────────────────────────────┤
│  📊 每日趋势                                            │
│  [折线图: 创建数/完成数/返工数]                         │
├─────────────────────────────────────────────────────────┤
│  📊 步骤耗时分析                                        │
│  [柱状图: Step1 45min | Step2 60min | Step3 20min]      │
├─────────────────────────────────────────────────────────┤
│  🏆 员工效率排名                                        │
│  1. Alice    92.5分  完成25个  平均35分钟              │
│  2. Bob      88.0分  完成20个  平均42分钟              │
│  3. Carol    85.5分  完成18个  平均38分钟              │
└─────────────────────────────────────────────────────────┘
```

### 5.5 实现步骤

| 步骤 | 任务 | 工时 |
|------|------|------|
| 1 | 创建 AnalyticsService | 2h |
| 2 | 实现统计查询方法 | 2h |
| 3 | 添加统计 API | 1h |
| 4 | 实现图表组件（折线图、柱状图） | 2h |
| 5 | 实现统计报表页 | 2h |

---

## 六、整体排期

### Week 1 (4-5天)

| 天数 | 上午 | 下午 | 晚上 |
|------|------|------|------|
| Day 1 | #16 模板模型+迁移 | #16 TemplateService | #16 API路由 |
| Day 2 | #16 UI模板列表 | #16 UI创建弹窗 | #18 流程图组件 |
| Day 3 | #18 布局算法+样式 | #18 集成到详情页 | #19 时间线Service |
| Day 4 | #19 时间线UI | #20 AnalyticsService | #20 图表组件 |
| Day 5 | #20 统计报表页 | 集成测试 | 文档整理 |

---

## 七、文件变更清单

### 后端新增
```
opc-database/
├── models/
│   └── workflow_template.py        # 模板模型
│
opc-core/
├── services/
│   ├── workflow_template_service.py    # 模板服务
│   ├── workflow_timeline_service.py    # 时间线服务
│   └── workflow_analytics_service.py   # 统计服务
│
├── api/
│   ├── workflow_templates.py       # 模板API
│   └── workflow_analytics.py       # 统计API
```

### 前端新增
```
opc-ui/
├── src/
│   ├── views/
│   │   ├── WorkflowTemplatesView.vue   # 模板库
│   │   └── WorkflowAnalyticsView.vue   # 统计报表
│   │
│   ├── components/
│   │   ├── WorkflowDiagram.vue         # 流程图
│   │   ├── WorkflowNode.vue            # 流程节点
│   │   ├── WorkflowTimeline.vue        # 时间线
│   │   └── WorkflowTemplateDialog.vue  # 模板弹窗
│   │
│   ├── stores/
│   │   └── workflowTemplates.js        # 模板store
```

---

## 八、验收标准

### 功能验收
- [ ] 可以保存工作流为模板
- [ ] 可以从模板创建工作流
- [ ] 流程图正确显示步骤和连接
- [ ] 时间线展示完整执行历史
- [ ] 统计报表显示正确数据

### 性能验收
- [ ] 模板列表加载 < 500ms
- [ ] 流程图渲染 < 300ms
- [ ] 统计查询 < 1s

---

**规划版本**: v0.4.2-P2  
**预计完成**: 2026-03-30  
**文档状态**: 待确认
