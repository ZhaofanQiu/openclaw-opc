# OpenClaw OPC 部署指南

> v0.4.0 模块化架构部署指南

---

## 📋 前置要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.12+ | 后端运行环境 |
| Node.js | 18+ | 前端构建 |
| OpenClaw | latest | Agent 运行环境 |
| Git | - | 代码管理 |

验证环境：
```bash
python3 --version    # >= 3.12
node --version       # >= 18
openclaw --version   # 已安装
```

---

## 🚀 快速部署

### 方式一：开发环境（推荐）

#### 1. 克隆仓库

```bash
git clone https://github.com/ZhaofanQiu/openclaw-opc.git
cd openclaw-opc
```

#### 2. 安装后端模块

```bash
# 安装数据库模块
cd packages/opc-database
pip install -e ".[dev]"

# 安装 OpenClaw 集成模块
cd ../opc-openclaw
pip install -e ".[dev]"

# 安装核心业务模块
cd ../opc-core
pip install -e ".[dev]"
```

#### 3. 安装前端

```bash
cd packages/opc-ui
npm install
```

#### 4. 启动服务

终端 1 - 后端 API：
```bash
cd packages/opc-core
python -c "from opc_core import create_app; import uvicorn; uvicorn.run(create_app(), host='0.0.0.0', port=8000)"
```

终端 2 - 前端开发服务器：
```bash
cd packages/opc-ui
npm run dev
```

访问：http://localhost:3000

---

### 方式二：Docker 部署（生产）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: opc
      POSTGRES_PASSWORD: opc_password
      POSTGRES_DB: opc
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # OPC Core API
  opc-core:
    build:
      context: ./packages/opc-core
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://opc:opc_password@postgres:5432/opc
      - OPENCLAW_URL=http://host.docker.internal:8080
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  # OPC UI (Nginx)
  opc-ui:
    build:
      context: ./packages/opc-ui
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - opc-core

volumes:
  postgres_data:
```

启动：
```bash
docker-compose up -d
```

---

## ⚙️ 配置说明

### 环境变量

#### opc-database
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///data/opc.db` | 数据库连接 |

#### opc-openclaw
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLAW_URL` | `http://localhost:8080` | OpenClaw Gateway |
| `OPENCLAW_API_KEY` | - | API Key（可选）|

#### opc-core
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | - | 复用 opc-database |
| `OPENCLAW_URL` | `http://localhost:8080` | OpenClaw 地址 |
| `API_KEY` | - | 管理 API Key |

#### opc-ui
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_BASE` | `/api/v1` | API 基础路径 |

---

## 🔧 模块独立测试

每个模块可独立测试：

```bash
# 测试数据库模块
cd packages/opc-database
pytest tests/ -v --cov=opc_database

# 测试 OpenClaw 模块（使用 Mock）
cd packages/opc-openclaw
pytest tests/ -v --cov=opc_openclaw

# 测试核心业务（使用 TestClient）
cd packages/opc-core
pytest tests/ -v --cov=opc_core

# 测试前端
cd packages/opc-ui
npm run test
```

---

## 🧪 验证部署

### 1. 健康检查

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.4.0"}
```

### 2. API 文档

访问：http://localhost:8000/docs

### 3. 前端登录

1. 访问 http://localhost:3000
2. 输入 API Key（在 opc-core 中配置）
3. 进入 Dashboard

---

## 📁 目录结构

部署后的项目结构：

```
openclaw-opc/
├── packages/
│   ├── opc-database/      # 数据库模块
│   │   ├── src/
│   │   └── tests/
│   ├── opc-openclaw/      # OpenClaw 集成
│   │   ├── src/
│   │   └── tests/
│   ├── opc-core/          # 业务 API
│   │   ├── src/
│   │   └── tests/
│   └── opc-ui/            # Vue3 前端
│       ├── src/
│       └── tests/
├── data/                   # 数据目录（SQLite/头像）
│   └── .gitkeep
├── docs/                   # 文档
├── archive/                # 归档（V2 代码）
└── memory/                 # 开发日志
```

---

## 🐛 故障排除

### 问题 1: 模块导入失败

**症状**: `ModuleNotFoundError: No module named 'opc_database'`

**解决**:
```bash
cd packages/opc-database
pip install -e "."
```

### 问题 2: 数据库连接失败

**症状**: `asyncpg.exceptions.ConnectionDoesNotExistError`

**解决**:
1. 检查 PostgreSQL 是否运行
2. 验证 `DATABASE_URL` 配置
3. 开发环境可使用 SQLite：`sqlite+aiosqlite:///data/opc.db`

### 问题 3: 前端 API 请求失败

**症状**: `Failed to fetch`

**解决**:
1. 检查后端是否运行在 `localhost:8000`
2. 检查 vite.config.js 代理配置
3. 检查 CORS 配置

### 问题 4: 权限错误

**症状**: `401 Unauthorized`

**解决**:
1. 在 Dashboard 输入正确的 API Key
2. 检查 opc-core 的 `API_KEY` 环境变量

---

## 📝 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-03-24 | v0.4.0 | 重构为模块化架构，四大独立包 |
| 2026-03-21 | v0.3.x | 旧版单体架构 |

---

## 📚 相关文档

- `PLAN_v0.4.0.md` - 架构重构规划
- `DEVELOPMENT.md` - 开发者规范
- `DESIGN.md` - 产品设计文档
- `packages/*/README.md` - 各模块文档
