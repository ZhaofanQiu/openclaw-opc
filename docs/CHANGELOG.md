# Changelog

All notable changes to the OpenClaw OPC project will be documented in this file.

## [0.4.5] - 2026-03-27

### Added
- **Agent Log Service** - 完整的 Agent 交互日志系统
  - `log_outgoing()` - 记录发送给 Agent 的消息
  - `log_incoming()` - 记录 Agent 的回复
  - `get_logs()` - 查询日志列表（支持分页和筛选）
  - `get_stats()` - 获取交互统计
  - `get_log_by_id()` - 获取单条日志详情
  - `clear_logs()` - 清空指定 Agent 的日志
  - 内存缓存机制（最近 100 条）
  
- **SQLite 并发写入优化**
  - 添加 `asyncio.Lock` 写入锁防止并发冲突
  - 优化后台任务事务持有时间
  - 缩短数据库连接持有时间，减少锁定冲突

### API Endpoints
- `GET /api/v1/agent-logs` - 查询日志列表
- `GET /api/v1/agent-logs/stats` - 获取统计信息
- `GET /api/v1/agent-logs/{log_id}` - 获取日志详情
- `DELETE /api/v1/agent-logs` - 清空日志

### Changed
- 更新版本号到 v0.4.5
- `AgentLogService` 导出到 `opc_core` 主模块

### Fixed
- 修复并行任务执行时的 `database is locked` 错误
- 优化后台任务 `_execute_task_in_background()` 的事务管理

## [0.4.4] - 2026-03-27

### Added
- Partner 智能辅助功能
- 员工辅助结果类型 (`EmployeeAssistResult`)
- 任务辅助结果类型 (`TaskAssistResult`)
- 工作流辅助结果类型 (`WorkflowAssistResult`)

### Changed
- 优化 Partner 服务架构

## [0.4.3] - 2026-03-24

### Added
- Workflow Timeline Service
- Workflow Analytics Service
- Workflow Template Service

### Changed
- 核心架构优化
- Repository 模式完善

## [0.4.2] - 2026-03-21

### Added
- Workflow Service 工作流引擎
- 工作流步骤配置
- 工作流进度追踪
- 返工限制机制

## [0.4.1] - 2026-03-20

### Added
- Task Service 任务服务
- Employee Service 员工服务
- 基础 API 框架

## [0.4.0] - 2026-03-20

### Added
- FastAPI 应用框架
- 基础数据库模型
- API 认证机制
