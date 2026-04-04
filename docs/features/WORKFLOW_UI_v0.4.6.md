# v0.4.6 工作流界面优化 - 功能文档

## 概述

v0.4.6 版本对工作流创建和管理界面进行全面优化，实现与任务创建界面的对齐，提升用户体验并增强工作流步骤的执行指导能力。

## 版本信息

- **版本号**: v0.4.6
- **发布时间**: 2026-03-28
- **开发周期**: 4个子功能并行开发
- **状态**: ✅ 开发完成，待测试

## 核心特性

### 1. 工作流创建弹窗 (WorkflowCreateModal)

#### 功能描述
将工作流创建从页面路由改为弹窗形式，与任务创建界面保持一致。

#### 界面特点
- **双模式支持**: 手动创建 + AI辅助创建
- **动态步骤管理**: 支持2-10个步骤，可自由添加/删除
- **步骤手册配置**: 每步可配置执行手册、输入要求、输出交付物
- **实时成本统计**: 动态显示预估总成本
- **响应式设计**: 适配不同屏幕尺寸

#### 技术实现
- 文件: `packages/opc-ui/src/components/workflows/WorkflowCreateModal.vue`
- 状态管理: `visible`, `activeTab` (manual/assist)
- 事件: `update:visible`, `created`

### 2. 步骤手册支持

#### 功能描述
为工作流的每个步骤添加执行手册支持，Agent可在执行前阅读手册获取指导。

#### 手册字段
| 字段 | 说明 | 必填 |
|------|------|------|
| `manual_content` | 执行手册内容（Markdown格式） | 否 |
| `input_requirements` | 输入要求说明 | 否 |
| `output_deliverables` | 输出交付物要求 | 否 |

#### 存储路径
```
data/manuals/tasks/{task_id}.md
```
采用标准任务手册路径，与工作流步骤统一。

#### 数据结构
```python
class WorkflowStepConfig:
    employee_id: str
    title: str
    description: str = ""
    estimated_cost: float = 100.0
    # v0.4.6 新增
    manual_content: Optional[str] = None
    input_requirements: Optional[str] = None
    output_deliverables: Optional[str] = None
```

### 3. 步骤数据传递

#### 功能描述
增强工作流执行引擎，实现步骤间的数据自动传递。

#### 数据流
```
创建工作流
    ↓
为每个步骤创建任务 + 手册文件
    ↓
触发第一个任务
    - 输入数据: initial_input + current_step_description
    - 任务描述: 原始描述 + 步骤描述
    ↓
Agent 执行 → 返回 OPC-REPORT
    ↓
触发下一步
    - 获取前一步输出
    - 构建步骤描述（含前序输出 + 输入要求 + 输出交付物）
    - 更新下一步输入数据
    ↓
Agent 执行下一步（收到完整上下文）
```

#### Agent 收到的任务消息示例
```markdown
【任务分配】

任务: 内容创作工作流 - Step 2: 撰写正文

## 工作流上下文
当前步骤: 2 / 3
工作流ID: wf-abc123

## 任务描述
撰写文章正文

## 前序步骤输出
**步骤 1**: 选题策划
**执行者**: 编辑小李
**输出摘要**: 确定了"AI发展趋势"选题...
**关键数据**:
  - trend_1: 多模态AI
  - trend_2: AI Agent

## 输入要求
需要选题报告、关键词列表、目标受众分析

## 输出交付物要求
完整的文章正文（2000字以上）

**重要**: 请确保你的 OPC-REPORT 中包含上述交付物。
```

### 4. AI辅助创建工作流

#### 功能描述
通过自然语言描述，让Partner AI自动规划工作流步骤。

#### API端点
```
POST /workflows/assist
```

#### 请求体
```json
{
  "description": "帮我创建一个调研报告生成工作流，包含选题、调研、撰写三个步骤",
  "budget_limit": 1000
}
```

#### 响应体
```json
{
  "workflow_plan": {
    "name": "调研报告生成工作流",
    "description": "完整的调研报告生成流程",
    "steps": [
      {
        "employee_id": "emp-001",
        "title": "选题策划",
        "description": "...",
        "estimated_cost": 100,
        "manual_content": "## 选题策划手册\n...",
        "input_requirements": "项目背景资料",
        "output_deliverables": "选题报告"
      }
    ]
  },
  "total_estimated_cost": 500,
  "confidence": 0.95
}
```

## API变更

### 新增/修改端点

#### 1. POST /workflows
创建工作流，支持步骤手册字段。

**请求体变更**:
```json
{
  "name": "工作流名称",
  "description": "工作流描述",
  "steps": [
    {
      "employee_id": "emp-001",
      "title": "步骤标题",
      "description": "步骤描述",
      "estimated_cost": 100,
      "manual_content": "执行手册内容",        // 新增
      "input_requirements": "输入要求",        // 新增
      "output_deliverables": "输出交付物要求"  // 新增
    }
  ],
  "initial_input": {}
}
```

#### 2. POST /workflows/assist
AI辅助创建工作流（已存在，v0.4.6增强手册生成）。

#### 3. GET /workflows/{workflow_id}
获取工作流详情，响应包含步骤手册信息。

## 向后兼容性

- ✅ 现有工作流不受影响
- ✅ 手册字段为可选，不传则不创建手册文件
- ✅ 标准任务手册路径，与现有任务兼容
- ✅ Agent 日志正常记录
- ✅ 无数据库迁移需求

## 文件变更清单

| 文件路径 | 变更类型 | 说明 |
|----------|----------|------|
| `packages/opc-core/src/opc_core/services/workflow_service.py` | 修改 | 手册存储 + 步骤数据传递 |
| `packages/opc-core/src/opc_core/api/workflows.py` | 修改 | API模型扩展 |
| `packages/opc-core/src/opc_core/services/partner_service.py` | 修改 | Prompt增强（已存在） |
| `packages/opc-core/src/opc_core/api/partner.py` | 修改 | 响应模型扩展（已存在） |
| `packages/opc-ui/src/components/workflows/WorkflowCreateModal.vue` | 新增 | 工作流创建弹窗 |
| `packages/opc-ui/src/views/WorkflowsView.vue` | 修改 | 集成弹窗 |

## 测试覆盖

| 测试文件 | 测试内容 | 状态 |
|----------|----------|------|
| `test_subfeature_1.py` | 数据模型扩展 + 手册存储 | ✅ 4/4 |
| `test_subfeature_3.py` | 步骤数据传递 | ✅ 5/5 |
| `test_subfeature_4.py` | 集成测试 | ✅ 4/4 |

## 使用指南

### 创建带手册的工作流

```bash
curl -X POST http://localhost:8080/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "调研报告工作流",
    "description": "生成完整调研报告",
    "steps": [
      {
        "employee_id": "emp-001",
        "title": "选题策划",
        "description": "确定调研主题",
        "estimated_cost": 100,
        "manual_content": "## 选题策划手册\n\n1. 分析市场需求\n2. 确定目标受众\n3. 评估可行性",
        "input_requirements": "项目背景、市场数据",
        "output_deliverables": "选题报告（含主题、目标、方法）"
      },
      {
        "employee_id": "emp-002",
        "title": "调研执行",
        "description": "执行调研计划",
        "estimated_cost": 200,
        "manual_content": "## 调研执行手册\n\n1. 设计问卷\n2. 收集数据\n3. 分析结果",
        "input_requirements": "选题报告",
        "output_deliverables": "调研数据和分析报告"
      }
    ],
    "initial_input": {"project": "AI市场调研"}
  }'
```

### AI辅助创建

```bash
curl -X POST http://localhost:8080/workflows/assist \
  -H "Content-Type: application/json" \
  -d '{
    "description": "帮我创建一个内容创作工作流，从选题到发布",
    "budget_limit": 1000
  }'
```

## 常见问题

### Q1: 步骤手册和任务手册的关系？
**A**: 工作流步骤的手册存储在标准任务手册路径 `data/manuals/tasks/{task_id}.md`，与普通任务的手册机制完全一致。

### Q2: 如果不传手册字段会怎样？
**A**: 不会创建手册文件，Agent执行任务时不会收到手册路径，与现有行为一致。

### Q3: 已有工作流需要更新吗？
**A**: 不需要。v0.4.6完全向后兼容，现有工作流继续正常运行。

### Q4: 步骤数据传递的格式是什么？
**A**: 数据以JSON格式存储在任务的 `input_data` 字段中，包含 `previous_outputs` 和 `current_step_description`。

## 相关文档

- [架构文档](../ARCHITECTURE.md) - 系统架构说明
- [CHANGELOG.md](../../CHANGELOG.md) - 版本变更日志

---

*文档版本: v0.4.6*  
*最后更新: 2026-03-28*  
*作者: OpenClaw OPC Team*
