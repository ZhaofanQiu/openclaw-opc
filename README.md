# OpenClaw OPC v0.4.0

**一人公司管理系统** - 模块化架构重构版本

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

- [架构规划](PLAN_v0.4.0.md) - v0.4.0 详细架构设计
- [开发规范](DEVELOPMENT.md) - 代码规范与贡献指南
- [CHANGELOG](CHANGELOG.md) - 版本变更记录

## 历史版本

旧版本代码已归档到 `archive/` 目录，包括：
- V2 后端完整代码
- V2 前端完整代码
- 过时文档和设计稿

## 许可证

MIT
