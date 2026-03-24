# OpenClaw OPC Changelog

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
