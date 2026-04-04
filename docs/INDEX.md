# OpenClaw OPC 文档索引

> **当前版本**: v0.4.6

---

## 核心文档

| 文档 | 说明 |
|------|------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 系统架构与模块边界 |
| [`../DEVELOPMENT.md`](../DEVELOPMENT.md) | 本地开发规范与 setup 指南 |
| [`../CLAUDE.md`](../CLAUDE.md) | AI Agent 开发规范（必读） |
| [`../CHANGELOG.md`](../CHANGELOG.md) | 版本变更记录（单一 truth source） |

## API 文档

API 文档按模块维护在各自的包目录下：

| 模块 | 文档 |
|------|------|
| opc-core | [`packages/opc-core/API.md`](../packages/opc-core/API.md) |
| opc-openclaw | [`packages/opc-openclaw/API.md`](../packages/opc-openclaw/API.md) |
| opc-database | [`packages/opc-database/API.md`](../packages/opc-database/API.md) |

## 功能说明

| 文档 | 说明 |
|------|------|
| [`features/AGENT_LOG_SERVICE.md`](features/AGENT_LOG_SERVICE.md) | Agent 交互日志服务 (v0.4.5) |
| [`features/WORKFLOW_UI_v0.4.6.md`](features/WORKFLOW_UI_v0.4.6.md) | 工作流界面优化 (v0.4.6) |

## 运维与部署

| 文档 | 说明 |
|------|------|
| [`../DEPLOYMENT.md`](../DEPLOYMENT.md) | 部署总览 |
| [`operations/CPOLAR_SETUP.md`](operations/CPOLAR_SETUP.md) | Cpolar 内网穿透部署 |
| [`operations/CLOUDFLARE_TUNNEL.md`](operations/CLOUDFLARE_TUNNEL.md) | Cloudflare Tunnel 部署 |
| [`operations/POSTGRESQL_MIGRATION.md`](operations/POSTGRESQL_MIGRATION.md) | PostgreSQL 迁移指南 |

## 参考

| 文档 | 说明 |
|------|------|
| [`REFERENCES.md`](REFERENCES.md) | 参考资料与开源项目借鉴 |
| [`TECHNICAL.md`](TECHNICAL.md) | 技术实现细节与方案确认 |
| [`api_examples.py`](api_examples.py) | API 调用示例（Python） |
| [`api_examples.sh`](api_examples.sh) | API 调用示例（Shell） |
