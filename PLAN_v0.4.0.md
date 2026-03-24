# OpenClaw OPC v0.4.0 架构重构规划

## 版本说明
- **版本号**: v0.4.0（统一版本号，清理混乱的历史版本）
- **重构目标**: 四大模块独立闭环，方便调试和维护
- **原则**: 优先复用V2实现，减少新开发

---

## 一、目录结构（最终形态）

```
openclaw-opc/
├── README.md                     # 项目总览
├── VERSION                       # 版本文件: v0.4.0
├── ARCHITECTURE.md              # 全局架构说明
├── DEVELOPMENT.md               # 开发者标准（必读）
├── DEPLOYMENT.md                # 部署指南
├── CHANGELOG.md                 # 版本变更日志
│
├── archive/                     # 旧版本归档（已过时，仅供参考）
│   ├── v2-backend/             # 当前backend完整备份
│   ├── v2-frontend/            # 当前web完整备份
│   ├── v2-docs/                # 当前docs完整备份
│   └── v2-skills/              # 当前skills完整备份
│   └── README.md               # 归档说明，标注已过时
│
├── packages/                    # 四大独立模块
│   ├── opc-database/           # 模块1: 数据库管理
│   ├── opc-openclaw/           # 模块2: OpenClaw功能封装
│   ├── opc-core/               # 模块3: OPC业务逻辑
│   └── opc-ui/                 # 模块4: 前端UI（整合V1+V2）
│
├── integration/                 # 集成层
│   ├── docker-compose.yml
│   └── Makefile
│
└── scripts/                     # 全局脚本
    ├── setup.sh
    ├── migrate-v2-to-v4.sh
    └── dev-start.sh
```

---

## 二、开发者标准规范

见 [DEVELOPMENT.md](./DEVELOPMENT.md)

**核心要点**:
1. **开发前必读**对应模块的 README.md + ARCHITECTURE.md + API.md
2. **代码规范**: Python用类型注解，前端用Vue3 Composition API
3. **修改流程**: 读文档 → 改代码 → 加测试 → 更新文档 → 提交
4. **测试要求**: 单元测试覆盖率 ≥70%

---

## 三、四大模块详细设计

### 3.1 opc-database（数据库管理）

**技术选型**: Python 3.12 + SQLAlchemy 2.0 + asyncpg + Alembic

**功能范围**: V2版本的数据库模型 + Repository层

```
opc-database/
├── pyproject.toml
├── README.md / ARCHITECTURE.md / API.md / CHANGELOG.md
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
└── src/opc_database/
    ├── models/            # SQLAlchemy模型
    │   ├── company.py     # 公司配置、预算
    │   ├── employee.py    # 员工、技能
    │   ├── project.py     # 项目、工作流
    │   └── task.py        # 任务、步骤、消息
    ├── repositories/      # Repository模式
    │   ├── company_repo.py
    │   ├── employee_repo.py
    │   ├── project_repo.py
    │   └── task_repo.py
    └── migrations/        # Alembic迁移
```

**对外接口**:
```python
from opc_database.repositories import EmployeeRepository

repo = EmployeeRepository(session)
employee = await repo.get_by_id("emp_xxx")
await repo.update_budget("emp_xxx", 100.0)
```

---

### 3.2 opc-openclaw（OpenClaw功能封装）

**技术选型**: Python 3.12 + httpx + pydantic v2 + asyncio

**功能范围**: V2版本的OpenClaw客户端 + Skill管理

```
opc-openclaw/
├── pyproject.toml
├── README.md / ARCHITECTURE.md / API.md / CHANGELOG.md
├── tests/
│   ├── mock/              # OpenClaw API Mock
│   ├── unit/
│   └── integration/
└── src/opc_openclaw/
    ├── client/            # HTTP客户端
    │   ├── base.py
    │   ├── sessions.py
    │   └── agents.py
    ├── agent/             # Agent管理
    │   ├── lifecycle.py
    │   ├── manager.py
    │   └── binding.py
    ├── interaction/       # 交互层
    │   ├── messenger.py
    │   ├── listener.py
    │   └── callback.py
    └── skill/             # Skill管理
        ├── definition.py
        ├── installer.py
        └── registry.py
```

**对外接口**:
```python
from opc_openclaw.agent import AgentManager
from opc_openclaw.interaction import Messenger

manager = AgentManager(config)
agent = await manager.create_agent(name="员工A")

messenger = Messenger(config)
await messenger.send(agent.id, "任务内容")
response = await messenger.wait_for_response(agent.id)
```

---

### 3.3 opc-core（OPC业务逻辑）

**技术选型**: Python 3.12 + FastAPI + uvicorn + pydantic v2 + WebSocket

**功能范围**: V2版本业务逻辑，去除数据库直接操作，调用opc-database

```
opc-core/
├── pyproject.toml
├── README.md / ARCHITECTURE.md / API.md / CHANGELOG.md
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── src/opc_core/
    ├── app.py             # FastAPI应用工厂
    ├── company/           # 公司管理模块
    │   ├── router.py
    │   ├── service.py
    │   ├── schemas.py
    │   └── manual/
    ├── employee/          # 员工管理模块
    │   ├── router.py
    │   ├── service.py
    │   ├── schemas.py
    │   ├── budget.py
    │   └── skill_path.py
    ├── project/           # 项目管理模块
    │   ├── router.py
    │   ├── service.py
    │   ├── schemas.py
    │   └── workflow/
    ├── task/              # 任务管理模块
    │   ├── router.py
    │   ├── service.py
    │   ├── schemas.py
    │   ├── assignment.py
    │   ├── execution.py
    │   ├── chat.py
    │   └── manual.py
    └── shared/            # 共享组件
        ├── events.py
        └── websocket.py
```

**技术要点**:
- 不直接操作数据库，通过 `opc-database` 的Repository
- 不直接调用OpenClaw，通过 `opc-openclaw` 的接口
- 提供RESTful API + WebSocket

---

### 3.4 opc-ui（前端UI - V1+V2整合）

**技术选型**: Vue 3 + Vite 5 + Pinia + Vue I18n 9 + Chart.js 4 + Element Plus

**功能范围**: 整合V1和V2的所有功能，重复功能以V2为主

```
opc-ui/
├── package.json
├── README.md / ARCHITECTURE.md / COMPONENT.md / API.md / CHANGELOG.md
├── tests/
│   ├── unit/
│   ├── component/
│   └── e2e/
└── src/
    ├── main.js
    ├── App.vue
    ├── router/
    ├── api/               # API客户端
    ├── stores/            # Pinia状态管理
    ├── views/             # 页面
    │   ├── dashboard/     # 仪表盘 (V2为主)
    │   ├── employee/      # 员工管理 (V2为主)
    │   ├── task/          # 任务管理 (V2为主)
    │   ├── pixel/         # 像素办公室 (V2为主)
    │   ├── workflow/      # 工作流 (V1+V2)
    │   ├── report/        # 报表 (V1保留)
    │   ├── log/           # 交互日志 (V2为主)
    │   └── manual/        # 手册 (V2为主)
    ├── components/        # 通用组件
    │   ├── common/        # 基础组件
    │   ├── employee/      # 员工相关
    │   ├── task/          # 任务相关
    │   └── visualization/ # 可视化
    ├── composables/       # Vue3组合式函数
    └── styles/            # 样式系统
```

---

## 四、UI功能决策

### 4.1 已确认的功能决策 ✅

| 功能 | 决策 | 说明 |
|------|------|------|
| **i18n 多语言** | ✅ 保留 | 使用 Vue I18n 实现 |
| **Chart.js 报表图表** | ✅ 保留 | 整合到报表页面 |
| **主题切换** | ❌ 不保留 | 只保留暗黑主题 |
| **技能路径独立页面** | ❌ 不保留 | 如有需要后续再添加 |
| **WebSocket 实时通知** | ✅ 保留 | 统一使用 WebSocket |

### 4.2 技术选型（已确定）

| 模块 | 技术栈 |
|------|--------|
| **opc-database** | Python 3.12 + SQLAlchemy 2.0 + asyncpg + Alembic |
| **opc-openclaw** | Python 3.12 + httpx + pydantic v2 + asyncio |
| **opc-core** | Python 3.12 + FastAPI + uvicorn + pydantic v2 |
| **opc-ui** | Vue 3 + Vite 5 + Pinia + Vue I18n 9 + Chart.js 4 + Element Plus |

### 4.3 V1独有功能保留清单

- ✅ template-editor.html (模板编辑器)
- ✅ reports.html (报表统计)
- ❌ agent-skill-path.html (不保留)

---

## 五、迁移执行计划

### Phase 0: 准备阶段 ✅ 已完成

- [x] 创建新目录结构
- [x] 完整备份V2到 archive/v2-*
- [x] 初始化各模块的 pyproject.toml / package.json
- [x] 创建根目录文档模板 (README.md, DEVELOPMENT.md, CHANGELOG.md, VERSION)
- [x] 创建各模块README

### Phase 1: opc-database ✅ 已完成

- [x] 迁移 models/ 到 opc-database/src/models/
  - [x] base.py - 基础模型
  - [x] employee.py - 员工模型 + EmployeeSkill
  - [x] task.py - 任务模型 + TaskMessage
  - [x] company.py - 公司预算和配置
- [x] 实现 Repository 层
  - [x] base.py - 基础Repository
  - [x] employee_repo.py - 员工数据访问
  - [x] task_repo.py - 任务数据访问
- [x] 数据库连接管理 (connection.py)
- [x] 编写单元测试（≥70%覆盖率）
  - [x] test_employee.py
  - [x] test_task.py
- [x] 编写模块文档
  - [x] ARCHITECTURE.md
  - [x] API.md
  - [x] CHANGELOG.md

**状态**: ✅ 已完成

### Phase 2: opc-openclaw ✅ 已完成

- [x] 迁移 core/agent_interaction_v2.py 相关功能
  - [x] 会话管理 (SessionClient)
  - [x] 消息发送 (Messenger)
  - [x] Agent 管理 (AgentManager)
- [x] 迁移 core/openclaw_client.py
  - [x] BaseClient - HTTP客户端基类
  - [x] AgentClient - Agent API
  - [x] SessionClient - 会话 API
- [x] 迁移 core/skill_*.py
  - [x] definition.py - Skill 定义
  - [x] SKILL_DEFINITION 文本
- [x] 实现 Mock 测试框架
  - [x] MockClient
  - [x] test_agent.py
  - [x] test_messenger.py
  - [x] test_skill.py
- [x] 编写模块文档
  - [x] ARCHITECTURE.md
  - [x] API.md
  - [x] CHANGELOG.md

**状态**: ✅ 已完成

### Phase 3: opc-core（5-7天）
- [ ] 迁移 routers/ 到对应模块
- [ ] 重构 services/ 使用 opc-database Repository
- [ ] 重构 Agent 调用使用 opc-openclaw
- [ ] 集成测试
- [ ] 编写API文档

### Phase 4: opc-ui（5-7天）
- [ ] 创建Vue3项目结构
- [ ] 迁移 V2 页面（优先级高）
- [ ] 整合 V1 独有功能
- [ ] 组件化重构
- [ ] 编写组件文档

### Phase 5: 集成与验证（2-3天）
- [ ] docker-compose 配置
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 文档完善

**总计**: 约3-4周

---

## 六、文档分层结构

### 6.1 顶层文档（项目根目录）
- `README.md` - 项目总览、快速开始
- `DEVELOPMENT.md` - 开发者标准（必读）
- `ARCHITECTURE.md` - 全局架构说明
- `DEPLOYMENT.md` - 部署指南
- `CHANGELOG.md` - 版本变更
- `VERSION` - 版本号: v0.4.0

### 6.2 模块内文档（每个packages/*）
- `README.md` - 模块说明、快速开始
- `ARCHITECTURE.md` - 模块架构设计
- `API.md` - 对外接口文档
- `CHANGELOG.md` - 模块版本变更
- `tests/` - 独立测试

### 6.3 归档文档（archive/）
- `README.md` - 说明这些文件已过时，仅供参考

---

## 七、当前状态

**Phase 0 已完成** ✅

目录结构已创建，配置文件已初始化，V2代码已备份。

可以开始 Phase 1: opc-database 的开发。

---

*最后更新: 2026-03-24*
