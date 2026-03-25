# OpenClaw OPC v0.4.2 规划文档

**版本目标**: 任务流（Workflow）- 多 Agent 串行协作  
**核心特性**: 拓展 Task 模型 + 结构化数据传递 + 返工机制  
**预计周期**: 6-7 天  
**最后更新**: 2026-03-25

---

## 一、版本概述

### 1.1 目标
实现多 Agent 串行协作的工作流（Workflow）系统，支持：
- 多步骤任务编排（Step 1 → Step 2 → Step 3）
- 步骤间结构化数据传递
- 返工机制（下游节点可要求上游节点返工）
- 返工次数上限控制

### 1.2 非目标（v0.4.2 不做）
- 并行步骤执行
- 条件分支（if/else）
- 循环/迭代
- 子工作流嵌套

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         UI 层 (opc-ui)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Workflow创建  │  │ Workflow详情  │  │ 任务详情(增强)    │  │
│  │   (可视化)    │  │  (流程图+状态) │  │ (结构化IO展示)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Core 层 (opc-core)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               WorkflowService                         │  │
│  │  ├─ create_workflow()    创建工作流                  │  │
│  │  ├─ on_task_completed()  任务完成回调，触发下一步     │  │
│  │  ├─ request_rework()     请求返工                    │  │
│  │  └─ _trigger_next_step() 触发下一步                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               TaskService (复用v0.4.1)                │  │
│  │  ├─ assign_task()    分配任务                        │  │
│  │  └─ ... 其他现有方法                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   OpenClaw 层 (opc-openclaw)                 │
│  ┌──────────────────┐      ┌────────────────────────────┐  │
│  │   TaskCaller     │      │      ResponseParser         │  │
│  │  (消息构建增强)   │      │    (解析返工标记+结构化输出) │  │
│  └──────────────────┘      └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Database 层 (opc-database)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                     Task 模型扩展                     │  │
│  │  workflow_id, step_index, total_steps                │  │
│  │  input_data, output_data (结构化)                    │  │
│  │  depends_on, next_task_id, rework_target             │  │
│  │  is_rework, rework_triggered_by, execution_log       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块独立性

| 模块 | 职责 | 不依赖 |
|------|------|--------|
| **opc-database** | 数据模型定义、持久化 | 其他模块 |
| **opc-openclaw** | Agent 通信、消息格式 | opc-core |
| **opc-core** | 业务逻辑、工作流编排 | opc-ui |
| **opc-ui** | 界面展示、用户交互 | 仅通过 API 依赖 core |

---

## 三、数据模型设计

### 3.1 Task 模型扩展

```python
class Task(Base):
    """Task 模型 - v0.4.2 扩展版"""
    
    # ========================================
    # 现有字段（v0.4.1）
    # ========================================
    id: str
    title: str
    description: str
    status: TaskStatus  # pending/assigned/in_progress/completed/failed/needs_review
    assigned_to: str    # employee_id
    assigned_by: str | None
    
    estimated_cost: float
    actual_cost: float
    tokens_input: int
    tokens_output: int
    
    session_key: str | None
    assigned_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    
    result: str         # Agent 原始回复文本
    result_files: list[str] | None
    
    rework_count: int   # 当前返工次数
    max_rework: int     # 最大返工次数（默认3）
    
    execution_context: dict  # 执行上下文（Manual等）
    
    # ========================================
    # v0.4.2 新增字段
    # ========================================
    
    # --- 工作流关联 ---
    workflow_id: str | None              # 所属工作流ID
    step_index: int                      # 在工作流中的步骤序号 (0-based)
    total_steps: int                     # 工作流总步骤数
    
    # --- 步骤链 ---
    depends_on: str | None               # 依赖的前置任务ID（上一节点）
    next_task_id: str | None             # 下一个任务ID（下一节点）
    
    # --- 结构化数据 ---
    input_data: dict | None              # 结构化输入（包含前置步骤输出）
    output_data: dict | None             # 结构化输出（不仅是文本result）
    
    # --- 返工机制 ---
    is_rework: bool = False              # 是否为返工任务
    rework_target: str | None            # 返工目标节点ID
    rework_triggered_by: str | None      # 触发返工的节点ID
    rework_reason: str | None            # 返工原因
    rework_instructions: str | None      # 返工指令
    
    # --- 执行历史 ---
    execution_log: list[dict]            # 执行历史记录（支持多次返工）
```

### 3.2 结构化数据格式

#### input_data 格式

```json
{
  "workflow_context": {
    "workflow_id": "wf_abc123",
    "workflow_name": "研究报告生成",
    "total_steps": 3,
    "current_step": 1
  },
  "previous_outputs": [
    {
      "step_index": 0,
      "task_id": "task_001",
      "employee_id": "emp_researcher",
      "employee_name": "Researcher",
      "output_summary": "研究主题：AI在医疗领域的应用...",
      "structured_output": {
        "research_scope": "AI医疗诊断",
        "key_findings": ["诊断准确率提升30%", "成本降低20%"],
        "data_sources": ["PubMed", "IEEE"]
      },
      "metadata": {
        "tokens_used": 1500,
        "execution_time_ms": 25000
      }
    }
  ],
  "upstream_rework_notes": null
}
```

#### output_data 格式

```json
{
  "summary": "任务执行摘要，给人类看",
  "structured_output": {
    "review_passed": false,
    "issues": ["缺少数据源引用", "结论支撑不足"],
    "suggestions": ["添加参考文献", "补充案例分析"]
  },
  "artifacts": [
    {"type": "file", "path": "/opc/outputs/report_v1.md"},
    {"type": "image", "url": "https://.../chart.png"}
  ],
  "metadata": {
    "tokens_input": 800,
    "tokens_output": 600,
    "execution_time_ms": 18000
  },
  "rework_request": {
    "needs_rework": true,
    "target_step": 0,
    "reason": "数据不完整",
    "instructions": "请补充数据来源引用"
  }
}
```

### 3.3 execution_log 格式

```json
[
  {
    "attempt": 1,
    "task_id": "task_001",
    "status": "completed",
    "started_at": "2026-03-25T10:00:00Z",
    "completed_at": "2026-03-25T10:00:30Z",
    "output_summary": "初步研究结果..."
  },
  {
    "attempt": 2,
    "task_id": "task_001_rework_1",
    "status": "completed",
    "is_rework": true,
    "rework_triggered_by": "task_002",
    "rework_reason": "数据不完整",
    "started_at": "2026-03-25T10:05:00Z",
    "completed_at": "2026-03-25T10:05:45Z",
    "output_summary": "补充数据后的研究结果..."
  }
]
```

---

## 四、业务逻辑设计

### 4.1 WorkflowService 核心方法

```python
class WorkflowService:
    """工作流服务 - 协调多步骤任务执行"""
    
    def __init__(
        self,
        task_repo: TaskRepository,
        emp_repo: EmployeeRepository,
        task_service: TaskService
    ):
        self.task_repo = task_repo
        self.emp_repo = emp_repo
        self.task_service = task_service
    
    # ========================================
    # 工作流生命周期
    # ========================================
    
    async def create_workflow(
        self,
        name: str,
        description: str | None,
        steps: list[WorkflowStepConfig],
        initial_input: dict,
        created_by: str,
        max_rework_per_step: int = 2
    ) -> WorkflowResult:
        """
        创建工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
            steps: 步骤配置列表
            initial_input: 初始输入数据
            created_by: 创建者ID
            max_rework_per_step: 每个步骤最大返工次数
            
        Returns:
            WorkflowResult 包含 workflow_id 和第一个任务ID
        """
    
    async def on_task_completed(self, task_id: str) -> None:
        """
        任务完成回调
        - 检查是否为工作流任务
        - 如果是最后一步，标记工作流完成
        - 否则创建并触发下一步
        """
    
    async def on_task_failed(self, task_id: str, error: str) -> None:
        """
        任务失败回调
        - 标记当前步骤失败
        - 暂停工作流后续步骤
        - 通知用户
        """
    
    # ========================================
    # 返工机制
    # ========================================
    
    async def request_rework(
        self,
        from_task_id: str,      # 当前节点（发现需要返工）
        to_task_id: str,        # 目标节点（需要返工的节点）
        reason: str,            # 返工原因
        instructions: str       # 返工指令
    ) -> Task:
        """
        请求返工
        
        规则：
        1. 只能向前返工（下游→上游，step_index 减小）
        2. 检查目标节点返工次数上限
        3. 创建返工任务，关联到原任务链
        4. 暂停当前及后续所有步骤
        5. 触发返工任务执行
        
        Returns:
            新创建的返工任务
            
        Raises:
            ReworkLimitExceeded: 超过返工次数上限
            InvalidReworkTarget: 不能返工到下游节点
        """
    
    async def get_rework_history(self, workflow_id: str) -> list[dict]:
        """获取工作流的返工历史"""
    
    # ========================================
    # 内部方法
    # ========================================
    
    async def _create_step_tasks(
        self,
        workflow_id: str,
        steps: list[WorkflowStepConfig],
        initial_input: dict
    ) -> list[Task]:
        """创建工作流的所有步骤任务（暂不分配）"""
    
    async def _trigger_next_step(self, current_task: Task) -> Task | None:
        """触发下一步任务"""
    
    async def _pause_downstream_tasks(self, from_task_id: str) -> None:
        """暂停从指定任务开始的所有下游任务"""
    
    async def _create_rework_task(
        self,
        original_task: Task,
        triggered_by: str,
        reason: str,
        instructions: str
    ) -> Task:
        """创建返工任务（复制原任务，增加 rework_count）"""
    
    async def _finalize_workflow(self, workflow_id: str) -> None:
        """标记工作流完成，收集最终结果"""
```

### 4.2 返工触发场景

```python
# 场景1: Agent 在输出中标记需要返工
# 由 ResponseParser 解析，core 层处理

# 场景2: UI 用户手动触发返工
# 用户在工作流详情页选择"请求返工"

# 场景3: 任务执行失败，用户选择重试
# 同节点重新执行（step_index 不变）
```

### 4.3 状态流转

```
工作流状态:
    PENDING → RUNNING → COMPLETED
                    ↓
                 FAILED（可重试）
                    ↓
                 REWORKING → RUNNING

步骤状态:
    PENDING → ASSIGNED → IN_PROGRESS → COMPLETED
                                      ↓
                                   REWORK_REQUESTED
                                      ↓
                                   REWORKING → IN_PROGRESS
```

---

## 五、OpenClaw 层增强

### 5.1 TaskAssignment 扩展

```python
@dataclass
class TaskAssignment:
    # 现有字段...
    
    # v0.4.2 新增
    workflow_context: dict | None = None    # 工作流上下文
    input_data: dict | None = None          # 结构化输入
    is_rework: bool = False                 # 是否为返工任务
    rework_context: dict | None = None      # 返工上下文
    
    # rework_context:
    # {
    #     "original_task_id": "task_001",
    #     "rework_count": 1,
    #     "max_rework": 2,
    #     "triggered_by": "task_002",
    #     "triggered_by_name": "Reviewer",
    #     "reason": "数据不完整",
    #     "instructions": "请补充数据来源引用",
    #     "previous_attempts": [...]
    # }
```

### 5.2 Messenger 消息格式

```
========================================
OpenClaw OPC - 工作流任务分配
========================================

工作流: 研究报告生成 (步骤 2/3)
任务ID: task_002

⚠️ 返工任务 (第 1/2 次)
返工原因: 数据不完整
返工要求: 请补充数据来源引用

----------------------------------------
前置步骤输出
----------------------------------------

[Step 1: Researcher]
研究主题：AI在医疗领域的应用
关键发现：
- 诊断准确率提升30%
- 成本降低20%
数据源：PubMed, IEEE

----------------------------------------
你的任务
----------------------------------------

审查上述研究结果，验证数据完整性：
1. 检查是否有数据源引用
2. 验证关键数据的准确性
3. 如有问题，请求返工并说明原因

----------------------------------------
输出格式要求
----------------------------------------

请使用 OPC-REPORT 格式，并包含以下结构化输出：

---OPC-OUTPUT---
{
  "review_passed": true/false,
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}
---OPC-REPORT---
task_id: task_002
status: completed/needs_rework
tokens_used: 800
summary: 审查结果摘要...
---END-REPORT---

如果需要返工，添加：
---OPC-REWORK---
target_step: 0
reason: 返工原因
instructions: 返工指令
---END-REWORK---
```

### 5.3 ResponseParser 扩展

```python
class ParsedReport:
    # 现有字段...
    is_valid: bool
    status: TaskStatus
    tokens_used: int
    summary: str
    result_files: list[str]
    errors: list[str]
    
    # v0.4.2 新增
    structured_output: dict | None = None
    
    # 返工标记
    needs_rework: bool = False
    rework_target_step: int | None = None
    rework_reason: str | None = None
    rework_instructions: str | None = None

class ResponseParser:
    def parse(self, content: str) -> ParsedReport:
        # 解析 OPC-REPORT 块
        report = self._parse_report_block(content)
        
        # 解析 OPC-OUTPUT 块（结构化输出）
        if "---OPC-OUTPUT---" in content:
            report.structured_output = self._parse_output_block(content)
        
        # 解析 OPC-REWORK 块（返工请求）
        if "---OPC-REWORK---" in content:
            rework = self._parse_rework_block(content)
            report.needs_rework = True
            report.rework_target_step = rework.get("target_step")
            report.rework_reason = rework.get("reason")
            report.rework_instructions = rework.get("instructions")
            report.status = TaskStatus.NEEDS_REWORK
        
        return report
```

---

## 六、UI 设计

### 6.1 新增页面

| 页面 | 路径 | 功能 |
|------|------|------|
| Workflow 列表 | `/workflows` | 查看所有工作流 |
| Workflow 创建 | `/workflows/create` | 可视化创建/编辑工作流 |
| Workflow 详情 | `/workflows/:id` | 流程图、状态、控制 |

### 6.2 Workflow 创建页

```
┌─────────────────────────────────────────────────────────┐
│  创建工作流                                    [保存]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  名称: [研究报告生成工作流                    ]          │
│  描述: [自动生成研究报告，包含研究、审查、编辑三个步骤]   │
│                                                         │
│  步骤编排:                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐             │
│  │ Step 1  │───▶│ Step 2  │───▶│ Step 3  │             │
│  │Research │    │ Review  │    │  Edit   │             │
│  │ [员工A] │    │ [员工B] │    │ [员工C] │             │
│  │⚙️ 设置  │    │⚙️ 设置  │    │⚙️ 设置  │             │
│  └─────────┘    └─────────┘    └─────────┘             │
│                                                         │
│  [+ 添加步骤]                                           │
│                                                         │
│  全局设置:                                              │
│  每步最大返工次数: [2]                                  │
│  失败重试策略: [○ 停止  ● 跳过  ○ 人工确认]              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Workflow 详情页

```
┌─────────────────────────────────────────────────────────┐
│  研究报告生成工作流                              [停止]  │
│  状态: 🟢 运行中 | 进度: 2/3 | 已耗时: 5分钟             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  流程图:                                                │
│                                                         │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐             │
│  │ ✅ Step │───▶│ 🔄 Step │───▶│ ⏳ Step │             │
│  │    1    │    │    2    │    │    3    │             │
│  │ Research│    │ Review  │    │  Edit   │             │
│  │  已完成  │    │ 运行中  │    │  等待   │             │
│  │[查看详情]│    │[查看详情]│    │[查看详情]│             │
│  └─────────┘    └─────────┘    └─────────┘             │
│       ↑              ↑                                  │
│       └──────────────┘                                  │
│      返工历史: 1次 (Step1 → Step2 请求返工)             │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  当前步骤详情 (Step 2 - Review)                         │
│  ─────────────────────────────────────────────────────  │
│  负责员工: Reviewer                                     │
│  状态: 运行中 (已运行 2分钟)                             │
│  预算: 150/200 OC币                                     │
│                                                         │
│  [查看任务详情]  [请求返工]  [跳过此步]                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 6.4 任务详情增强

```
┌─────────────────────────────────────────────────────────┐
│  任务: Review研究结果                                    │
│  工作流: 研究报告生成 (Step 2/3)                         │
├─────────────────────────────────────────────────────────┤
│  结构化输入                                              │
│  ─────────────────────────────────────────────────────  │
│  ├─ 工作流上下文                                         │
│  │   工作流ID: wf_abc123                                 │
│  │   总步骤: 3                                           │
│  │   当前步骤: 2                                         │
│  ├─ 前置步骤输出 ▼                                       │
│  │   [Step 1: Researcher]                                │
│  │   研究主题：AI在医疗领域的应用                         │
│  │   关键发现：...                                       │
│  │   结构化数据: {▼}                                     │
│  └─ 返工备注: 无                                         │
├─────────────────────────────────────────────────────────┤
│  结构化输出                                              │
│  ─────────────────────────────────────────────────────  │
│  ├─ 执行摘要: 审查完成，发现数据引用缺失                   │
│  ├─ 结构化数据 ▼                                         │
│  │   {                                                   │
│  │     "review_passed": false,                           │
│  │     "issues": ["缺少数据源引用"],                     │
│  │     "suggestions": ["添加参考文献"]                   │
│  │   }                                                   │
│  ├─ 返工请求 ▼                                           │
│  │   目标步骤: Step 1 (Research)                         │
│  │   原因: 数据不完整                                    │
│  │   指令: 请补充数据来源引用                             │
│  └─ 执行日志: [查看历史]                                  │
├─────────────────────────────────────────────────────────┤
│  [上一步] [返回工作流] [下一步]                           │
└─────────────────────────────────────────────────────────┘
```

---

## 七、实现优先级

### P0 - 核心功能（必须完成）

| 序号 | 模块 | 任务 | 工时 | 依赖 |
|------|------|------|------|------|
| 1 | database | Task 模型扩展（新增字段） | 0.5d | 无 |
| 2 | database | 数据库迁移脚本 | 0.5d | #1 |
| 3 | core | WorkflowService.create_workflow() | 1d | #2 |
| 4 | core | WorkflowService.on_task_completed() 回调 | 0.5d | #3 |
| 5 | openclaw | TaskAssignment 扩展 | 0.5d | 无 |
| 6 | openclaw | Messenger 工作流消息构建 | 0.5d | #5 |
| 7 | core | 工作流触发下一步逻辑 | 0.5d | #4, #6 |
| 8 | ui | Workflow 创建页 | 1d | #3 |
| 9 | ui | Workflow 详情页（基础） | 1d | #7 |
| 10 | integration | 端到端测试 | 0.5d | #1-9 |

**P0 总计**: 6 天

### P1 - 返工机制（重要）

| 序号 | 模块 | 任务 | 工时 | 依赖 |
|------|------|------|------|------|
| 11 | core | WorkflowService.request_rework() | 1d | P0 |
| 12 | core | 返工次数限制检查 | 0.5d | #11 |
| 13 | openclaw | ResponseParser 返工标记解析 | 0.5d | P0 |
| 14 | core | 返工回调处理 | 0.5d | #11, #13 |
| 15 | ui | Workflow 详情页返工交互 | 0.5d | #11 |

**P1 总计**: 3 天

### P2 - 增强功能（可选）

| 序号 | 模块 | 任务 | 工时 | 依赖 |
|------|------|------|------|------|
| 16 | core | 工作流模板（保存/复用） | 1d | P0 |
| 17 | core | 批量创建任务（预分配所有步骤） | 0.5d | P0 |
| 18 | ui | 流程图可视化（SVG/Canvas） | 1d | P0 |
| 19 | ui | 执行历史时间线 | 0.5d | P1 |
| 20 | core | 工作流统计报表 | 0.5d | P0 |

**P2 总计**: 3.5 天

---

## 八、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 返工机制复杂度高 | 中 | 高 | P0 先跑通基础工作流，P1 再添加返工 |
| 步骤间数据传递格式不稳定 | 中 | 中 | 使用 JSON Schema 验证，预留扩展字段 |
| UI 流程图实现复杂 | 低 | 中 | P2 再做复杂可视化，P0/P1 用列表展示 |
| 测试覆盖不足 | 中 | 高 | 每个核心方法必须单元测试 |

---

## 九、验收标准

### 功能验收

- [ ] 可以创建包含 3 个步骤的工作流
- [ ] 步骤按顺序执行，前一步完成触发后一步
- [ ] 步骤间数据正确传递（下游能看到上游输出）
- [ ] 下游可以请求返工到上游任意步骤
- [ ] 返工次数达到上限后禁止再次返工
- [ ] 工作流完成后可以查看完整执行历史

### 性能验收

- [ ] 工作流创建 < 1s
- [ ] 步骤切换（触发下一步）< 500ms
- [ ] 返工请求处理 < 1s

### 测试验收

- [ ] WorkflowService 单元测试覆盖 > 80%
- [ ] 至少 1 个端到端工作流测试
- [ ] UI 组件测试覆盖关键交互

---

## 十、后续版本规划

### v0.4.3 - 并行步骤
- 支持并行分支（Fork/Join）
- 条件分支（基于上游输出决定路径）

### v0.5.0 - 工作流模板市场
- 预置常用工作流模板
- 用户分享自定义模板
- 模板评分/评论

---

**文档版本**: 1.0  
**编写者**: OPC Team  
**审核状态**: 待确认
