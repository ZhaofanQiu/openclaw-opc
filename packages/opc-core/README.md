# opc-core

**OpenClaw OPC v0.4.0 - 核心业务模块**

FastAPI 实现的 OPC 业务逻辑层，提供完整的 RESTful API。

## 功能

- **员工管理**: CRUD、绑定、预算查询
- **任务管理**: CRUD、分配、执行、消息
- **预算管理**: 统计、消耗记录
- **手册管理**: 公司/员工/任务手册
- **报表**: Dashboard 数据、绩效统计
- **Skill API**: Agent 交互接口

## 安装

```bash
cd packages/opc-core
pip install -e ".[dev]"
```

## 使用

### 启动服务

```python
from opc_core import create_app
import uvicorn

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 环境变量

```bash
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./opc.db
# 或
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/opc

# API 认证（可选）
OPC_API_KEY=your_api_key

# OpenClaw
OPENCLAW_API_URL=http://localhost:8080
```

## API 列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/employees` | GET/POST | 员工列表/创建 |
| `/api/v1/employees/{id}` | GET/PUT/DELETE | 员工详情/更新/删除 |
| `/api/v1/employees/{id}/bind` | POST | 绑定 OpenClaw Agent |
| `/api/v1/employees/{id}/budget` | GET | 员工预算 |
| `/api/v1/tasks` | GET/POST | 任务列表/创建 |
| `/api/v1/tasks/{id}` | GET/PUT/DELETE | 任务详情/更新/删除 |
| `/api/v1/tasks/{id}/assign` | POST | 分配任务 |
| `/api/v1/tasks/{id}/start` | POST | 开始执行 |
| `/api/v1/tasks/{id}/complete` | POST | 完成任务 |
| `/api/v1/budget/company` | GET | 公司预算 |
| `/api/v1/budget/employees` | GET | 员工预算列表 |
| `/api/v1/manuals/company` | GET/PUT | 公司手册 |
| `/api/v1/manuals/employee/{id}` | GET/PUT | 员工手册 |
| `/api/v1/reports/dashboard` | GET | Dashboard 报表 |
| `/api/v1/skill/get-current-task` | POST | Agent 获取任务 |
| `/api/v1/skill/report-task-result` | POST | Agent 报告结果 |

## 架构

```
opc_core/
├── api/               # API 路由
│   ├── dependencies.py   # 依赖注入
│   ├── employees.py      # 员工 API
│   ├── tasks.py          # 任务 API
│   ├── budget.py         # 预算 API
│   ├── manuals.py        # 手册 API
│   ├── reports.py        # 报表 API
│   ├── skill_api.py      # Skill 接口
│   └── __init__.py       # 路由聚合
├── services/          # 业务服务
│   ├── employee_service.py
│   └── task_service.py
├── app.py             # FastAPI 应用
└── __init__.py        # 模块导出
```

## 测试

```bash
pytest tests/
```

## 文档

- [API 文档](API.md)
- [架构设计](ARCHITECTURE.md)
- [变更日志](CHANGELOG.md)
