# 系统架构设计 (Architecture)

## 概述

OpenClaw OPC 采用**四模块单体架构**，通过清晰的包边界（`packages/*`）实现关注点分离。

```
┌─────────────────────────────────────────────────────────────┐
│                      用户层 (User Layer)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │   Web UI (Vue 3 + Vite + Pinia + Element Plus)      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    核心服务层 (Core Service)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  opc-core (FastAPI)                                 │   │
│  │  ├─ 员工/任务/工作流/预算 API                        │   │
│  │  ├─ Partner Agent (辅助创建任务/员工/工作流)         │   │
│  │  ├─ Agent Log 追踪                                  │   │
│  │  └─ 工作流统计与分析                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│      数据层 (Database)      │   │   OpenClaw 集成层          │
│  opc-database               │   │  opc-openclaw               │
│  SQLAlchemy 2.0 (async)     │   │  ├─ HTTP/CLI 客户端         │
│  SQLite (开发) / PostgreSQL │   │  ├─ Agent 生命周期管理      │
│  Repository 模式            │   │  ├─ ResponseParser          │
│                             │   │  └─ Skill 定义与安装器      │
└─────────────────────────────┘   └─────────────────────────────┘
```

---

## 组件详解

### 1. opc-core - 业务 API

**技术栈:**
- Python 3.12+
- FastAPI + Uvicorn
- Pydantic v2

**核心职责:**
- 员工 (Employee) CRUD 与 Agent 绑定
- 任务 (Task) 分配、追踪、状态流转
- 工作流 (Workflow) 多步骤编排与返工
- 预算 (Budget) 追踪与熔断判断
- 手册 (Manual) 管理
- Partner Agent - 对话式辅助
- Agent Log - Agent 交互日志查询

**关键模块:**
```
packages/opc-core/
├── src/opc_core/
│   ├── api/               # FastAPI 路由 (employees, tasks, workflows, analytics, ...)
│   ├── services/          # 业务逻辑 (TaskService, WorkflowService, ...)
│   ├── app.py             # FastAPI 应用工厂
│   └── main.py            # Uvicorn 入口
└── tests/
    ├── unit/
    ├── integration/
    └── api/
```

> **注意:** 当前 opc-core 会直接 serve `opc-ui/dist` 静态文件（SPA fallback），方便本地开发。生产环境建议使用反向代理（nginx/Caddy）将 UI 和 API 分离。

---

### 2. opc-ui - 前端界面

**技术栈:**
- Vue 3 + Vite
- Pinia (状态管理)
- Vue Router
- Element Plus (UI 组件库)
- Chart.js / ECharts (图表)

**核心职责:**
- Dashboard - 任务/员工/预算概览
- 任务管理 - 创建、分配、追踪
- 工作流编辑器 - 步骤配置与执行监控
- 员工管理 - 角色、预算、Agent 绑定
- Analytics - 工作流统计与员工排名
- Partner 面板 - 与 Partner Agent 对话

**关键模块:**
```
packages/opc-ui/
├── src/
│   ├── views/             # 页面视图
│   ├── components/        # 复用组件
│   ├── stores/            # Pinia Store
│   └── router/            # 路由配置
├── dist/                  # 构建输出
└── package.json
```

---

### 3. opc-database - 数据层

**技术栈:**
- SQLAlchemy 2.0 (异步)
- Alembic (迁移)
- aiosqlite / asyncpg

**核心职责:**
- 定义所有 ORM 模型（Employee, Task, WorkflowTemplate, AgentLog 等）
- 提供 Repository 模式的数据访问封装
- 管理数据库连接与事务

**关键模块:**
```
packages/opc-database/
├── src/opc_database/
│   ├── models/            # ORM 模型
│   ├── repositories/      # Repository 实现
│   └── connection.py      # 引擎与会话管理
└── tests/
```

---

### 4. opc-openclaw - OpenClaw 集成

**技术栈:**
- httpx (HTTP 客户端)
- pydantic / pydantic-settings
- PyYAML

**核心职责:**
- 通过 HTTP/CLI 与 OpenClaw Gateway 通信
- Agent 生命周期管理（列举、创建、绑定）
- 任务分配消息构建 (`TaskCaller`)
- Agent 响应解析 (`ResponseParser`)
- Skill 定义 (`SKILL_DEFINITION`) 与安装器 (`SkillInstaller`)

**Agent 结果协议:**
Agent 在回复末尾必须包含 `OPC-REPORT` 格式块：

```
---OPC-REPORT---
task_id: <任务ID>
status: completed|failed|needs_revision
tokens_used: <数字>
summary: <单行总结>
result_files: <可选的文件路径>
---END-REPORT---
```

 additionally 支持 `OPC-OUTPUT`（结构化 JSON 输出）和 `OPC-REWORK`（返工指令）。

**关键模块:**
```
packages/opc-openclaw/
├── src/opc_openclaw/
│   ├── agent/             # AgentManager, AgentLifecycle
│   ├── client/            # HTTP/CLI 客户端
│   ├── interaction/       # Messenger, TaskCaller, ResponseParser
│   ├── skill/             # Skill 定义、安装器
│   └── config.py          # Agent 配置管理
└── tests/
```

---

## 数据流

### 正常任务执行流程

```
1. 用户在 UI 创建任务
   ↓ HTTP POST /api/v1/tasks
2. opc-core 保存任务，更新状态为 PENDING
   ↓ 用户/系统分配员工
3. opc-core 调用 opc-openclaw 构建任务消息
   ↓ HTTP/CLI 发送到 OpenClaw Gateway
4. Agent 执行任务
   ↓ 返回包含 OPC-REPORT 的响应
5. opc-openclaw.ResponseParser 解析结果
   ↓ opc-core 更新任务状态、实际成本、Token 消耗
6. UI 通过轮询/刷新查看最新状态
   ↓
7. 如果是工作流任务，自动触发下一步
```

### 工作流执行流程

```
1. 用户创建 Workflow（多个步骤）
   ↓ opc-core 将 Workflow 拆分为多个关联的 Task
2. 执行第一个 Task
   ↓ Agent 完成后解析 OPC-REPORT
3. WorkflowService.on_task_completed() 触发
   ↓ 自动分配下一个 Task（传递前置输出作为输入）
4. 循环直到所有步骤完成或失败
   ↓
5. 支持返工：任意步骤可触发 OPC-REWORK 回到上游步骤
```

### 预算熔断流程

```
1. 分配任务时检查员工 remaining_budget
   ↓
2. 如果预估成本超过预算的 150%
   ↓ 拒绝分配，返回预算不足错误
3. 任务完成后结算 actual_cost
   ↓ 更新员工 used_budget
4. UI 实时显示预算仪表盘
```

---

## 模块依赖规则

```
opc-ui ──HTTP──► opc-core
                    │
        ┌──────────┴──────────┐
        ▼                     ▼
  opc-database          opc-openclaw
```

**禁止以下依赖方向：**
- `opc-database` 禁止依赖 `opc-core` 或 `opc-openclaw`
- `opc-openclaw` 禁止依赖 `opc-core`
- `opc-core` 的 API Router 禁止直接操作文件系统或调用 `subprocess`

---

## 安全设计

| 层级 | 机制 | 触发条件 |
|------|------|---------|
| 1. 预算熔断 | 拒绝分配 | 预估成本 > 预算 150% |
| 2. 返工限制 | 强制结束 | 返工次数 > max_rework |
| 3. 审计日志 | Agent Log | 记录所有 Agent 交互 |
| 4. API Key | 本地验证 | 敏感操作需 api_key |

---

## 扩展性考虑

1. **数据库升级**
   - 当前默认 SQLite，可通过环境变量切换至 PostgreSQL
   - Alembic 迁移脚本已就位

2. **前端分离部署**
   - 当前 opc-core 直接 serve `opc-ui/dist`
   - 生产环境建议用 nginx 反向代理替代

3. **实时状态**
   - 当前 UI 通过轮询获取状态
   - 未来可引入 WebSocket 或 SSE 实现推送

---

## 技术决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 后端框架 | FastAPI + SQLAlchemy 2.0 | 现代异步 Python 栈，类型友好 |
| 前端框架 | Vue 3 + Vite | 轻量、快速、生态成熟 |
| 状态管理 | Pinia | Vue 3 官方推荐 |
| UI 组件 | Element Plus | 企业级组件丰富 |
| 数据库 | SQLite (默认) | 零配置，单机场景够用 |
| Agent 通信 | HTTP/CLI 客户端 | 直接调用 OpenClaw Gateway，无需 Plugin |

---

*Last Updated: 2026-04-03 (v0.4.6)*
