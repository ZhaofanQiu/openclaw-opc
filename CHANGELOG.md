# OpenClaw OPC Changelog

## [0.4.1] - 2026-03-25 (Phase 3 完成)

### Core 层架构升级

- **同步任务分配** - 从异步回调改为同步返回
  - `TaskService.assign_task()` 改为同步流程
  - 使用 `ResponseParser` 解析 Agent 回复
  - 移除对 HTTP 回调的依赖
  - 新增 `NEEDS_REVIEW` 状态处理解析失败

- **API 路由更新**
  - `POST /api/v1/tasks/{id}/assign` - 同步返回任务结果
  - `POST /api/v1/tasks/{id}/retry` - 新增重试任务接口
  - `POST /api/v1/tasks/{id}/complete` - 已移除
  - `POST /api/v1/tasks/{id}/fail` - 已移除
  - `POST /api/v1/tasks/{id}/rework` - 已移除
  - Skill API 标记为废弃 (deprecated=True)

- **ResponseParser 集成**
  - 解析 `OPC-REPORT` 格式响应
  - 支持状态: completed, failed, needs_revision
  - 自动提取 tokens_used 和 result_files

### 测试

- **新增测试** (82 个全部通过)
  - `tests/api/test_tasks_api.py` - 18 个 API 测试
  - `tests/integration/test_phase3_new_architecture.py` - 12 个集成测试
  - 更新 `tests/unit/test_task_api.py` - 适配新架构
  - 修复 `tests/unit/test_employee_api.py` - AgentManager mock

- **文档**
  - `packages/opc-core/API.md` - Core API 完整文档
  - `PLAN_v0.4.1_Phase3_Core.md` - Phase 3 详细规划

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
