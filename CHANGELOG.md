# OpenClaw OPC Changelog

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
