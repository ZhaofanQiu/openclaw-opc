# opc-database 变更日志

所有 opc-database 模块的变更记录。

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
