# opc-core 变更日志

所有 opc-core 模块的变更记录。

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
