# opc-core 变更日志

所有 opc-core 模块的变更记录。

## [0.4.2] - 2026-03-25

### Workflow 系统

- **工作流服务 (WorkflowService)**
  - `create_workflow()` - 创建多步骤工作流
  - `on_task_completed()` - 任务完成回调，自动触发下一步
  - `request_rework()` - 请求返工机制
  - `_trigger_next_step()` - 触发下一步执行

### 模板系统 (P2)

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

### API 端点 (27个)

- 模板管理: 8个端点
- 时间线: 2个端点
- 分析统计: 5个端点
- 工作流: 12个端点

---

## [0.4.1] - 2026-03-25

### 异步任务架构

- **异步任务执行**
  - `assign_task()` 立即返回 assigned 状态
  - 后台任务 (`_execute_task_in_background`) 使用独立数据库 session
  - 员工状态同步更新为 working（前端立即可见）
  - 支持前端轮询获取最终状态

- **ResponseParser 集成**
  - 解析 `OPC-REPORT` 格式响应
  - 支持状态: completed, failed, needs_revision, needs_review
  - 自动提取 tokens_used、summary、result_files

- **预算结算**
  - 任务完成后自动结算预算
  - 更新员工 used_budget 和 completed_tasks
  - 失败任务支持返工 (rework_count/max_rework)

### API 更新

- `POST /api/v1/tasks` - 创建任务并自动分配
- `POST /api/v1/tasks/{id}/assign` - 分配任务给员工
- `POST /api/v1/tasks/{id}/retry` - 重试失败任务
- `GET /api/v1/tasks/{id}/poll` - 轮询任务状态

### 测试

- 新增 12 个集成测试
  - `tests/integration/test_phase3_new_architecture.py`
  - ResponseParser 解析测试
  - 异步任务分配测试
  - 任务重试测试
  - 错误处理测试

---

## [0.4.0] - 2026-03-24

### 新增

- 初始化模块
- FastAPI 应用框架
- 完整的 RESTful API

### API 路由

- **Employees**: 员工 CRUD、绑定、预算查询
- **Tasks**: 任务 CRUD、分配、执行、消息
- **Budget**: 预算统计、消耗记录
- **Manuals**: 公司/员工/任务手册管理
- **Reports**: Dashboard、绩效、统计报表
- **Skill API**: Agent 交互接口

### 业务服务

- EmployeeService: 员工业务逻辑
- TaskService: 任务业务逻辑

### 特性

- 异步 Repository 模式
- 依赖注入
- 可选 API Key 认证
- CORS 支持
- 完整类型注解
