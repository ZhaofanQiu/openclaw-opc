# opc-database 变更日志

所有 opc-database 模块的变更记录。

## [0.4.2] - 2026-03-25

### Workflow 模型扩展

- **Task 模型** - 14个新字段
  - 工作流关联: workflow_id, step_index
  - 步骤配置: step_title, step_description, estimated_cost
  - 执行状态: workflow_status, started_at, completed_at
  - 返工支持: is_rework, rework_count, parent_task_id, requested_rework_by
  - 数据传递: input_data, output_data
  - 执行日志: execution_log

### 模板模型 (P2)

- **WorkflowTemplate 模型**
  - 16个字段: id, name, description, steps_config
  - 分类标签: category, tags
  - 统计信息: usage_count, avg_rating, rating_count
  - 版本管理: version, parent_template_id, is_system
  - 权限控制: created_by, is_public, is_archived

- **WorkflowTemplateRating 模型**
  - 用户评分和评论

### Repository 层

- **WorkflowTemplateRepository**
  - 15+ 查询方法
  - 按分类、标签查询
  - 搜索、热门、高评分排序
  - Fork 关系追踪

- **WorkflowTemplateRatingRepository**
  - 评分 CRUD
  - 统计查询

---

## [0.4.1] - 2026-03-25

### 模型更新

- **Task 模型**
  - 新增状态：needs_review (解析失败需人工检查)
  - 新增字段：rework_count, max_rework (返工计数)
  - 支持任务重试流程

- **Employee 模型**
  - 新增字段：completed_tasks (已完成任务计数)
  - 支持预算结算统计

### Repository 增强

- **TaskRepository**
  - 支持状态流转查询
  - 支持返工计数更新

- **EmployeeRepository**
  - 支持预算结算
  - 支持任务计数更新

### 测试

- 35 个单元测试全部通过
- 模型测试覆盖所有字段
- Repository 测试覆盖 CRUD 操作

---

## [0.4.0] - 2026-03-24

### 新增

- 初始化模块
- 支持 SQLAlchemy 2.0 异步操作
- 支持 SQLite (aiosqlite) 和 PostgreSQL (asyncpg)

### 模型

- Employee 模型：员工管理
- EmployeeSkill 模型：员工技能
- Task 模型：任务管理
- TaskMessage 模型：任务消息
- CompanyBudget 模型：公司预算
- CompanyConfig 模型：公司配置

### Repository

- BaseRepository：通用CRUD
- EmployeeRepository：员工数据访问
- TaskRepository：任务数据访问
- TaskMessageRepository：消息数据访问

### 测试

- 单元测试覆盖率 ≥70%
- Employee 模型测试
- Task 模型测试
