# OpenClaw OPC Changelog

## [0.4.6] - 2026-03-28 - Workflow UI Optimization

### 核心特性: 工作流界面优化

#### 子功能1: 后端数据模型扩展
- **WorkflowStepConfig 增强** - 新增步骤手册字段
  - `manual_content`: 执行手册内容（Markdown格式）
  - `input_requirements`: 输入要求说明
  - `output_deliverables`: 输出交付物要求

- **手册存储优化** - 采用标准任务手册路径
  - 路径: `data/manuals/tasks/{task_id}.md`
  - 与工作流步骤和普通任务统一
  - 完全向后兼容

- **Partner Prompt 增强** - AI自动生成步骤手册
  - 为每个步骤生成执行手册
  - 包含输入要求和输出交付物
  - 提升Agent执行质量

#### 子功能2: 前端界面改造
- **WorkflowCreateModal 新增** - 工作流创建弹窗
  - 双模式支持: 手动创建 + AI辅助
  - 动态步骤管理（2-10步）
  - 步骤手册配置（可折叠展开）
  - 实时成本统计
  - 响应式设计

- **WorkflowsView 集成** - 弹窗集成
  - 创建按钮改为打开弹窗
  - 与任务创建界面对齐

#### 子功能3: 工作流执行引擎增强
- **步骤数据传递** - 前序输出自动传递
  - `_get_previous_output()`: 提取前序步骤输出
  - `_get_step_context()`: 解析步骤手册信息
  - `_build_step_description()`: 构建完整步骤描述
  - `_build_initial_step_description()`: 构建初始描述

- **Agent 任务消息增强** - 完整上下文传递
  - 工作流上下文（步骤索引、总数）
  - 前序步骤输出（摘要、关键数据、交付物）
  - 当前步骤输入要求
  - 当前步骤输出交付物要求
  - 重要提醒：确保OPC-REPORT包含交付物

#### 子功能4: 集成测试
- **手动创建工作流测试** - 验证手册正确存储
- **多步骤数据传递测试** - 验证步骤间数据流转
- **返工上下文传递测试** - 验证返工信息传递
- **端到端完整流程测试** - 验证完整工作流执行

### API变更

#### POST /workflows - 创建工作流
```json
{
  "steps": [{
    "employee_id": "emp-001",
    "title": "步骤标题",
    "manual_content": "执行手册",        // 新增
    "input_requirements": "输入要求",    // 新增
    "output_deliverables": "输出要求"    // 新增
  }]
}
```

#### POST /workflows/assist - AI辅助创建（增强）
- 响应包含步骤手册字段
- Partner自动生成手册内容

### 文件变更

| 文件 | 变更 |
|------|------|
| `workflow_service.py` | 手册存储 + 步骤数据传递方法 |
| `workflows.py` | API模型扩展 |
| `WorkflowCreateModal.vue` | **新增** - 工作流创建弹窗 |
| `WorkflowsView.vue` | 集成弹窗 |

### 测试覆盖

| 测试文件 | 测试数 | 状态 |
|----------|--------|------|
| `test_subfeature_1.py` | 4 | ✅ 全部通过 |
| `test_subfeature_3.py` | 5 | ✅ 全部通过 |
| `test_subfeature_4.py` | 4 | ✅ 全部通过 |

### 文档

- `docs/features/WORKFLOW_UI_v0.4.6.md` - 功能详细文档
- `memory/2026-03-28.md` - 开发过程记录

---

## [0.4.4] - 2026-03-27 - Partner Agent (Complete) ✅

### Phase 3: UI Dialogs (Completed) ✅ 100%

**核心特性**: 所有 4 个智能辅助功能都有 UI 集成

#### TaskCreateModal (增强)
- ✨ **Partner 智能细化** 区域
- 输入框描述需求
- AI 细化按钮
- 预览面板：
  - 优化标题
  - 详细描述
  - 执行步骤（有序列表）
  - 成本估算 + 理由
  - 推荐员工（如果未选择）
- 一键应用方案

#### ManualEditModal (新增)
- 📖 公司手册编辑对话框
- 加载当前手册内容
- ✨ **Partner 智能修改** 区域
- 修改需求输入
- AI 修改按钮
- 修改预览文本框
- 应用和保存按钮

#### PartnerWidget 集成
- 「📖 手册」按钮打开 ManualEditModal
- 所有 4 个快捷操作都有对应对话框

---

### Phase 2: Intelligent Assistance (Completed)

**核心特性**: 4 个智能辅助功能

#### 1. 辅助创建员工 (assist_create_employee)
- **API**: `POST /api/v1/partner/assist/create-employee`
- **功能**: Partner 智能设计员工形象
- **返回**: 背景故事、性格特点、行事风格、技能列表、推荐预算、员工手册

#### 2. 辅助创建任务 (assist_create_task)
- **API**: `POST /api/v1/partner/assist/create-task`
- **功能**: 细化任务需求，推荐员工，预估成本
- **返回**: 优化标题、详细描述、执行步骤、成本估算、推荐员工、任务手册

#### 3. 一句话创建工作流 (assist_create_workflow)
- **API**: `POST /api/v1/partner/assist/create-workflow`
- **功能**: 自然语言描述 → 完整工作流配置
- **返回**: 工作流名称、描述、3-5个步骤、每步成本和员工分配

#### 4. 智能修改公司手册 (assist_update_company_manual)
- **API**: `POST /api/v1/partner/assist/update-manual`
- **功能**: 根据用户请求修改公司手册内容
- **返回**: 更新后的完整手册内容

#### PartnerService 增强
- 新增 4 个 assist 方法
- 智能提示词构建（包含员工列表、OC币策略）
- JSON 响应解析和错误处理

#### UI Store 更新
- `assistCreateEmployee()` - 调用员工辅助 API
- `assistCreateTask()` - 调用任务辅助 API
- `assistCreateWorkflow()` - 调用工作流辅助 API
- `assistUpdateManual()` - 调用手册更新 API

---

### Phase 1: Foundation (Completed)

**核心特性**: Partner 员工作为智能管理助手

#### Database 层
- **PartnerMessage 模型** - 存储用户与 Partner 的对话历史
  - 字段: id, partner_id, role, content, has_action, action_type, action_params, action_result
  - 索引: partner_id + created_at

- **PartnerMessageRepository** - 数据访问层
  - get_recent_messages: 获取最近聊天记录
  - get_messages_with_actions: 获取包含操作的消息
  - clear_history_before: 清理历史记录

#### Core 服务层
- **PartnerService** - Partner 业务逻辑
  - chat(): 与 Partner 对话，解析 OPC-ACTION 指令
  - get_chat_history(): 获取聊天历史
  - clear_chat_history(): 清空历史
  - 内置 OC币/Token 换算策略 (1 OC币 ≈ 1000 Tokens)

#### API 端点
- `GET /api/v1/partner/status` - 获取 Partner 状态
- `POST /api/v1/partner/chat` - 与 Partner 对话
- `GET /api/v1/partner/history` - 获取聊天历史
- `DELETE /api/v1/partner/history/{partner_id}` - 清空历史

#### UI 层
- **PartnerWidget** - 全局悬浮框组件
  - 可展开/收起的聊天窗口
  - 快捷操作按钮 (任务/工作流/员工/手册/状态)
  - Markdown 渲染消息内容
  - 加载动画

- **Partner Store** - Pinia 状态管理
  - 自动检测 Partner 员工
  - 消息历史管理
  - 发送消息并处理回复

#### 全局集成
- PartnerWidget 挂载在 App.vue，跨所有页面存在
- 无 Partner 时显示创建引导

### Phase 2: Intelligent Assistance (Planned)
- 辅助创建员工（自动设计背景/性格/手册）
- 辅助创建任务（细化需求/预估成本/推荐员工）
- 一句话创建工作流
- 修改公司手册

---

## [0.4.3] - 2026-03-27 - Production Ready

### 核心改进

**稳定性修复** - WAL 模式 + 事务隔离修复，解决数据库锁问题

#### Database 层
- **WAL 模式支持** - 启用 Write-Ahead Logging
  - `PRAGMA journal_mode=WAL` - 提升并发性能
  - `PRAGMA synchronous=NORMAL` - 平衡性能与安全
  - `PRAGMA wal_autocheckpoint=1000` - 自动检查点
  - 读不阻塞写，写不阻塞读

#### Core 服务层
- **事务隔离修复** - 修复 `database is locked` 错误
  - `assign_task()` - 创建任务前显式提交事务
  - `_execute_task_in_background()` - session 关闭后再触发工作流回调
  - 避免嵌套 session 导致的锁竞争

- **任务反馈系统** - 完整支持 Agent 人类可读反馈
  - `ParsedReport.human_readable` - 提取非结构化内容
  - `Task.feedback` 字段存储员工反馈
  - API 返回反馈数据
  - 前端 Markdown 渲染展示

#### UI 层
- **员工反馈展示** - TaskDetailView 添加反馈区域
  - 集成 `marked` 库解析 Markdown
  - 支持标题、代码块、列表、分隔线等格式
  - 美观的反馈卡片样式

- **工作流样式统一** - 修复 CSS 变量不一致
  - `WorkflowCreateView` - 统一 `--spacing-*` 变量
  - `WorkflowDetailView` - 统一 `--spacing-*` 变量

- **任务管理增强**
  - 新建任务默认预估成本改为 100 OC币
  - 任务详情页添加删除按钮

### 修复清单

| 问题 | 修复方案 |
|------|----------|
| 工作流子任务卡住 (database is locked) | WAL 模式 + 事务隔离修复 |
| 新建任务默认成本为 0 | 改为 100 |
| 工作流页面样式不一致 | 统一 CSS 变量 |
| 员工反馈 Markdown 解析错误 | 集成 marked 库 |
| 任务详情页无删除按钮 | 添加删除功能 |

### 文档
- 更新各子模块版本号至 v0.4.3

---

## [0.4.2] - 2026-03-25 - Workflow System Complete

### v0.4.2-P2: Workflow Template System

**核心特性**: 工作流模板市场、时间线、分析统计

#### Database 层
- **WorkflowTemplate 模型** - 16个字段支持完整模板功能
  - 基础信息: id, name, description, steps_config
  - 分类标签: category, tags
  - 统计信息: usage_count, avg_rating, rating_count
  - 版本管理: version, parent_template_id, is_system
  - 权限控制: created_by, is_public

- **WorkflowTemplateRating 模型** - 用户评分和评论

- **Repository 层** - 15+ 查询方法
  - 按分类、标签查询
  - 搜索、热门、高评分排序
  - Fork 关系追踪

#### Core 服务层
- **WorkflowTemplateService** - 模板管理
  - CRUD 操作
  - 从模板创建工作流
  - Fork 功能
  - 评分系统

- **WorkflowTimelineService** - 执行时间线
  - 构建完整时间线事件
  - 从日志提取事件
  - 从状态推断事件
  - 摘要统计

- **WorkflowAnalyticsService** - 分析统计
  - 工作流整体统计
  - 步骤耗时分析
  - 趋势分析
  - 员工效率排名

#### UI 层
- **TemplateMarketView** - 模板市场
  - 模板浏览和搜索
  - 评分和评论
  - Fork 功能

- **WorkflowTimelineView** - 执行时间线
  - 可视化时间线
  - 步骤详情

- **WorkflowAnalyticsView** - 分析看板
  - 统计图表
  - 趋势分析

#### API 端点 (27个)
- 模板管理: 8个端点
- 时间线: 2个端点
- 分析统计: 5个端点
- 其他: 12个端点

### v0.4.2-P0/P1: 基础工作流系统

#### Database 层
- **Task 模型扩展** - 14个新字段
  - 工作流关联: workflow_id, step_index
  - 步骤配置: step_title, step_description, estimated_cost
  - 执行状态: workflow_status, started_at, completed_at
  - 返工支持: is_rework, rework_count, parent_task_id, requested_rework_by
  - 数据传递: input_data, output_data
  - 执行日志: execution_log

#### OpenClaw 层
- **ResponseParser** - 解析 Agent 响应
  - `OPC-OUTPUT` 块解析
  - `OPC-REWORK` 返工请求解析
  - 状态识别: completed, failed, needs_revision, needs_review

#### Core 服务层
- **WorkflowService** - 工作流核心
  - `create_workflow()` - 创建工作流
  - `on_task_completed()` - 任务完成回调，自动触发下一步
  - `request_rework()` - 请求返工
  - `_trigger_next_step()` - 触发下一步执行

#### UI 层
- **WorkflowsView** - 工作流列表
- **WorkflowCreateView** - 创建工作流
- **WorkflowDetailView** - 工作流详情（流程图+状态）

### 测试 (77个全部通过)

- **Database 模型测试**: 12个
- **Database 仓库测试**: 20个
- **Core 服务测试**: 14个
- **Core 时间线测试**: 11个
- **E2E 场景测试**: 20个

### 场景测试
- ✅ 内容创作流水线
- ✅ 代码审查流水线
- ✅ 客户服务响应
- ✅ 数据报告生成

### 文档
- `TEST_SCENARIOS_v0.4.2.md` - 测试场景设计
- `TEST_REPORT_v0.4.2.md` - 测试执行报告
- `PLAN_v0.4.2.md` - 开发计划（已归档）
- `PLAN_v0.4.2-P2.md` - P2 开发计划（已归档）

---

## [0.4.1] - 2026-03-25 - v0.4.1 完成

### 端到端任务流程跑通

**核心成就**: Dashboard 创建任务 → Core 分配 → OpenClaw 调用 Agent → Agent 执行 → 状态更新 → Dashboard 显示完成

### Core 层 - 异步架构

- **异步任务执行**
  - `assign_task()` 立即返回 assigned 状态
  - 后台任务使用独立数据库 session
  - 员工状态同步更新为 working（前端立即可见）
  - 前端轮询获取最终状态

- **ResponseParser 集成**
  - 解析 `OPC-REPORT` 格式响应
  - 支持状态: completed, failed, needs_revision, needs_review
  - 自动提取 tokens_used 和 result_files

- **预算结算**
  - 任务完成后自动结算预算
  - 更新员工 used_budget 和 completed_tasks

### UI 层

- **任务管理**
  - 新增 TaskCreateModal 组件
  - 自动分配流程（创建任务后立即分配）
  - 任务列表轮询状态更新
  - 单位显示修复（tokens → OC币）
  - 时间戳格式修复（添加 Z 后缀）

### 测试 (47 个全部通过)

- **Phase 3 Core 集成测试**: 12 个
  - `tests/integration/test_phase3_new_architecture.py`
  - ResponseParser 解析测试
  - 异步任务分配测试
  - 任务重试测试
  - 错误处理测试

- **Phase 4 UI 单元测试**: 35 个
  - stores/auth.spec.js (5)
  - stores/employees.spec.js (12)
  - composables/useStatus.spec.js (9)
  - utils/api.spec.js (9)

### 文档

- `PLAN_v0.4.1.md` - 开发计划（已归档）
- 更新 `API.md` - API 接口文档

---

## [0.4.0] - 2026-03-24

### 架构重构

- **模块化架构** - 项目拆分为 4 个独立包
  - `opc-database`: 数据库模型与 Repository 层
  - `opc-openclaw`: OpenClaw HTTP Client 与 Agent 管理
  - `opc-core`: FastAPI 业务 API
  - `opc-ui`: Vue3 前端

### 清理与归档

- 归档 V2 后端代码 (`backend/` → `archive/v2-backend-full/`)
- 归档 V2 前端代码 (`web/` → `archive/v2-frontend-full/`)
- 归档过时文档和脚本
- 清理根目录，保持项目整洁

### 文档

- 新增 `PLAN_v0.4.0.md` - 完整架构规划
- 新增 `DEVELOPMENT.md` - 开发规范
- 更新 `README.md` - 项目说明

## [0.3.x] 及更早版本

历史版本请查看 `archive/` 目录。
