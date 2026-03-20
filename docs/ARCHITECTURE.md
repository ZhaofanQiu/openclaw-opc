# 系统架构设计 (Architecture)

## 概述

OpenClaw OPC 采用分层架构，确保各组件独立演进、松耦合集成。

```
┌─────────────────────────────────────────────────────────────┐
│                      用户层 (User Layer)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web UI     │  │  Desktop App │  │   CLI Tool   │      │
│  │  (React)     │  │  (Electron)  │  │   (Future)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    核心服务层 (Core Service)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  FastAPI + SQLite/PostgreSQL                        │   │
│  │  ├─ 公司管理 API (员工/项目/任务)                   │   │
│  │  ├─ 预算追踪与熔断                                  │   │
│  │  ├─ 实时状态推送 (WebSocket)                        │   │
│  │  └─ 工作手册管理                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP 轮询 / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   OpenClaw 集成层 (Integration)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  OpenClaw Plugin (Skill)                            │   │
│  │  ├─ 拦截 Agent 调用                                 │   │
│  │  ├─ 注入公司上下文 (SOUL.md + 手册)                 │   │
│  │  ├─ 上报 Token 消耗                                 │   │
│  │  └─ 接收 Core Service 指令                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              OpenClaw Gateway                       │   │
│  │         ┌─────┐  ┌─────┐  ┌─────┐                  │   │
│  │         │Agent│  │Agent│  │Agent│  ...             │   │
│  │         └─────┘  └─────┘  └─────┘                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 组件详解

### 1. Core Service (packages/core)

**技术栈:**
- Python 3.10+
- FastAPI (Web 框架)
- SQLAlchemy (ORM)
- SQLite (默认) / PostgreSQL (可选)
- WebSocket (实时推送)

**核心职责:**
- 公司、员工、项目、任务的 CRUD
- 预算追踪与熔断判断
- 手册版本管理
- 与 Plugin 的通信

**关键模块:**
```
core/
├── src/
│   ├── models/          # 数据库模型
│   ├── routers/         # API 路由
│   ├── services/        # 业务逻辑
│   ├── websocket/       # 实时推送
│   └── utils/           # 工具函数
├── tests/
└── Dockerfile
```

### 2. Web UI (packages/ui)

**技术栈:**
- React 18 + TypeScript
- Vite (构建工具)
- PixiJS (像素办公室渲染)
- WebSocket (实时状态)

**核心职责:**
- 像素办公室可视化
- 项目看板、员工管理界面
- 预算仪表盘
- 待处理收件箱

**关键模块:**
```
ui/
├── src/
│   ├── components/      # 通用组件
│   ├── pages/           # 页面
│   ├── stores/          # 状态管理 (Zustand)
│   ├── hooks/           # 自定义 Hooks
│   └── pixi/            # 像素办公室相关
├── public/
└── Dockerfile
```

### 3. OpenClaw Plugin (packages/plugin)

**技术栈:**
- JavaScript/TypeScript
- OpenClaw Skill SDK

**核心职责:**
- 拦截并增强 Agent 调用
- 注入公司上下文
- 上报 Token 消耗
- 执行 Core Service 指令

**关键文件:**
```
plugin/
├── src/
│   ├── interceptor.js   # 调用拦截
│   ├── context.js       # 上下文注入
│   └── reporter.js      # 消耗上报
└── SKILL.md             # OpenClaw Skill 定义
```

---

## 数据流

### 正常任务执行流程

```
1. 用户在 UI 创建任务
   ↓ HTTP POST /api/tasks
2. Core Service 保存任务，分配给 Agent
   ↓ 记录预算预估
3. Plugin 拦截 Agent 调用
   ↓ 注入：SOUL.md + 工作手册 + 任务上下文
4. Agent 执行任务
   ↓ 实时上报 Token 消耗
5. Core Service 更新预算余额
   ↓ 判断是否触发熔断
6. UI 实时显示进度 (WebSocket)
   ↓
7. 任务完成，更新员工经验/手册数据
```

### 熔断触发流程

```
1. Token 消耗达到预算 80%
   ↓
2. Core Service 发送警告到 UI
   ↓
3. Token 消耗达到 100%
   ↓
4. Core Service 发送暂停指令到 Plugin
   ↓
5. Plugin 拦截并暂停 Agent
   ↓
6. UI 显示"预算耗尽"，等待用户决策
   ↓
7. 用户选择：追加预算 / 拆分任务 / 换人
```

---

## 通信协议

### Core Service ↔ Web UI

**HTTP API:**
- RESTful API (CRUD 操作)
- WebSocket (实时状态推送)

**主要事件:**
```
- employee.status_changed
- task.progress_updated
- budget.threshold_reached
- system.alert
```

### Core Service ↔ OpenClaw Plugin

**初始方案 (MVP): HTTP 轮询**
- Plugin 每 5 秒向 Core Service 发送状态
- Core Service 通过 HTTP 响应下发指令

**进阶方案 (V1+): WebSocket 双向**
- 建立持久连接
- 实时双向通信

**数据格式:**
```json
{
  "agent_id": "agent_xxx",
  "task_id": "task_xxx",
  "token_consumed": 150,
  "status": "working|paused|completed",
  "output_preview": "..."
}
```

---

## 安全设计

### 五层防火墙

| 层级 | 机制 | 触发条件 |
|------|------|---------|
| 1. 预算熔断 | 硬停止 | 消耗达到预算 150% |
| 2. 时间沙盒 | 强制暂停 | 连续工作 > 2 小时 |
| 3. 行为白名单 | 操作限制 | 禁止危险操作 |
| 4. 审计日志 | 全程记录 | 所有行为可追溯 |
| 5. 人类决策 | 确认机制 | 关键操作需确认 |

### 数据安全

- 本地 SQLite 存储，数据不离开用户机器 (默认)
- 敏感配置 (API Key) 加密存储
- 定期自动备份

---

## 扩展性考虑

### 未来可能的分拆点

如果项目发展壮大，可以按以下边界分拆：

1. **Core Service 拆分**
   - 公司管理服务
   - 预算追踪服务
   - 实时推送服务

2. **多租户支持**
   - 用户系统
   - 数据隔离
   - SaaS 版本

3. **插件生态**
   - 第三方集成 (n8n, GitHub, 飞书)
   - 自定义员工模板

---

## 技术决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | SQLite (MVP) | 零配置，够用很久 |
| Plugin 通信 | HTTP 轮询 → WebSocket | MVP 简单，后续升级 |
| 像素办公室 | 静态 → 动画 | 先证明价值，再投入 |
| 认证方式 | 本地 Token | 单机使用，后续加用户系统 |

---

*Last Updated: 2026-03-21*
