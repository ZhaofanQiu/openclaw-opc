# opc-database

OpenClaw OPC - Database Management Module

**版本**: v0.4.0

## 职责

所有数据持久化层，提供ORM模型和Repository数据访问接口。

## 技术栈

- Python 3.12
- SQLAlchemy 2.0 (async)
- asyncpg (PostgreSQL)
- Alembic (数据库迁移)
- pydantic v2

## 安装

```bash
# 开发环境
cd packages/opc-database
pip install -e ".[dev]"

# 生产环境
pip install .
```

## 快速开始

```python
from opc_database.connection import get_session
from opc_database.repositories import EmployeeRepository

async with get_session() as session:
    repo = EmployeeRepository(session)
    employee = await repo.get_by_id("emp_xxx")
```

## 模块结构

```
src/opc_database/
├── models/          # SQLAlchemy ORM模型
├── repositories/    # 数据访问层（Repository模式）
└── migrations/      # Alembic迁移脚本
```

## 文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 架构设计
- [API.md](./API.md) - Repository接口文档

## 测试

```bash
pytest tests/
pytest --cov=src tests/  # 带覆盖率
```

## 变更日志

见 [CHANGELOG.md](./CHANGELOG.md)
