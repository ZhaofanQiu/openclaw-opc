# OpenClaw OPC v0.4.6

**一人公司管理系统** - v0.4.6 端到端任务流程已跑通 ✅

## 项目状态

**v0.4.6 已完成** - Dashboard 创建任务 → Core 分配 → OpenClaw 调用 Agent → Agent 执行 → 状态更新 → Dashboard 显示完成

| 模块 | 版本 | 状态 | 测试 |
|------|------|------|------|
| opc-database | v0.4.6 | ✅ 完成 | 35+ 个测试 |
| opc-openclaw | v0.4.6 | ✅ 完成 | 35+ 个测试 |
| opc-core | v0.4.6 | ✅ 完成 | 12+ 个集成测试 |
| opc-ui | v0.4.6 | ✅ 完成 | 35+ 个单元测试 |

## 项目架构

采用四模块设计，每个模块独立维护、独立测试：

```
packages/
├── opc-database/     # 数据库层 (SQLAlchemy 2.0)
├── opc-openclaw/     # OpenClaw 集成 (HTTP Client + Agent 管理)
├── opc-core/         # 业务 API (FastAPI)
└── opc-ui/           # 前端 (Vue3 + Vite + Pinia)
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- SQLite (开发) / PostgreSQL (生产)

### 安装后端

```bash
cd packages/opc-database
pip install -e ".[dev]"

cd ../opc-openclaw
pip install -e ".[dev]"

cd ../opc-core
pip install -e ".[dev]"
```

### 安装前端

```bash
cd packages/opc-ui
npm install
```

### 启动服务

```bash
# 终端 1: 后端 API
cd packages/opc-core
python -c "from opc_core import create_app; import uvicorn; uvicorn.run(create_app(), host='0.0.0.0', port=8000)"

# 终端 2: 前端开发服务器
cd packages/opc-ui
npm run dev
```

访问 http://localhost:3000

## 开发文档

- [CHANGELOG](CHANGELOG.md) - 版本变更记录
- [开发规范](DEVELOPMENT.md) - 代码规范与贡献指南
- [架构文档](docs/ARCHITECTURE.md) - 系统架构说明

## 历史版本与计划

旧版本代码可通过 Git 历史 (`git log` / `git checkout`) 追溯。

## 许可证

MIT
