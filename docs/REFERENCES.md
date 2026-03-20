# 开源项目参考指南

## 概述

以下开源项目为我们提供了宝贵的参考，在开发过程中应优先研究并适当借鉴，避免重复造轮子。

---

## 1. OpenClaw Dashboard (OpenClaw-bot-review)

**仓库**: https://github.com/xmanrui/OpenClaw-bot-review

### 可借鉴功能

| 功能 | 借鉴点 | 应用到我们项目 |
|------|--------|---------------|
| **配置读取** | 直接读取 `~/.openclaw/openclaw.json` | Core Service 初始化时读取 OpenClaw 配置 |
| **实时监控** | 10秒自动轮询 Gateway 状态 | 我们的员工状态实时同步 |
| **会话管理** | 展示 Agent 会话统计 | 员工工作记录页面 |
| **告警中心** | 规则配置 + 飞书通知 | 预算熔断通知机制 |
| **Pixel Office** | 像素风动画办公室 | 我们的像素办公室基础设计 |
| **主题切换** | 深色/浅色模式 | UI 主题系统 |

### 技术参考
- **前端**: Next.js + Tailwind CSS
- **无数据库设计**: 直接读配置文件 (适合 MVP)
- **Docker 部署**: 参考其 Dockerfile

### 差异点
- 它是只读监控，我们需要完整的 CRUD 管理
- 我们增加预算控制、任务分配等主动管理功能

---

## 2. OpenClaw Mission Control

**仓库**: https://github.com/abhi1693/openclaw-mission-control

### 可借鉴功能

| 功能 | 借鉴点 | 应用到我们项目 |
|------|--------|---------------|
| **组织架构** | Organizations → Boards → Tasks 层级 | 我们的公司 → 项目 → 任务结构 |
| **审批流程** | 敏感操作需审批 | 我们的晋升审批、预算追加审批 |
| **审计日志** | 时间线记录所有操作 | 员工行为审计、预算变更记录 |
| **Gateway 管理** | 连接和操作分布式 Gateway | 我们与 OpenClaw 的集成方式 |
| **认证模式** | Local Token / Clerk JWT | 我们的认证系统设计参考 |

### 技术参考
- **后端**: FastAPI (Python)
- **前端**: React + TypeScript
- **部署**: Docker Compose
- **数据库**: 支持 PostgreSQL

### 差异点
- 它是企业级重管理，我们是轻量化一人公司
- 我们增加游戏化元素（像素办公室、心情系统）

---

## 3. Star Office UI

**仓库**: https://github.com/ringhyacinth/Star-Office-UI

### 可借鉴功能

| 功能 | 借鉴点 | 应用到我们项目 |
|------|--------|---------------|
| **状态可视化** | 6种状态映射到办公室区域 | 员工心情 → 预算状态的映射 |
| **昨日小记** | 从 memory/*.md 读取工作记录 | 员工工作日报生成 |
| **多 Agent 协作** | Join Key 邀请机制 | 员工之间的协作邀请 |
| **像素渲染** | Phaser 游戏引擎 | 我们的像素办公室渲染方案 |
| **状态同步** | HTTP API + 本地文件 | Plugin 与 Core 通信方式 |
| **桌面宠物** | Electron 封装 | 未来桌面版参考 |

### 技术参考
- **后端**: Flask (Python)
- **前端**: Phaser (游戏引擎)
- **部署**: 纯 Python，无需 Docker

### 差异点
- 它主要是"看"，我们需要"管"（任务分配、预算控制）
- 我们增加游戏化数值系统（成长、技能、手册）

---

## 4. ClawCompany

**仓库**: https://github.com/Claw-Company/clawcompany

### 可借鉴功能

| 功能 | 借鉴点 | 应用到我们项目 |
|------|--------|---------------|
| **多模型策略** | 不同角色用不同模型（Opus/ Sonnet/ GPT/ Gemini） | 我们的员工熟练度 → 模型选择 |
| **角色预定义** | CEO/CTO/CFO/CMO 等标准角色 | 我们的岗位模板设计 |
| **成本优化** | 27倍成本降低策略 | 我们的返工率 → 成本控制 |
| **使命分解** | CEO 分解任务给团队 | 我们的任务分配机制 |
| **工具使用** | Agent 使用工具自主执行 | 员工工具使用熟练度 |
| **公司模板** | Trading Desk / Content Agency 等 | 我们的行业模板设计 |
| **实时通信** | WebChat / Telegram / Discord | 我们的通知渠道设计 |

### 技术参考
- **架构**: Monorepo (pnpm workspace)
- **语言**: TypeScript
- **部署**: npx 一键运行
- **通信**: SSE (Server-Sent Events) 实时推送

### 差异点
- 它是 CLI + WebChat 为主，我们是可视化 Web UI
- 它强调"自主执行"，我们强调"可控管理"（预算熔断）
- 我们有像素办公室游戏化体验

---

## 参考策略

### 可直接复用的代码/库

| 来源 | 内容 | 使用方式 |
|------|------|---------|
| OpenClaw Dashboard | 读取 OpenClaw 配置的逻辑 | 参考实现 |
| Star Office UI | Phaser 像素渲染方案 | 参考或直接引用 |
| ClawCompany | Monorepo 结构 | 参考 package.json 配置 |
| ClawCompany | SSE 实时推送 | 参考实现 |
| Mission Control | Docker Compose 配置 | 参考 compose.yml |

### 需要改造的部分

| 来源 | 改造内容 |
|------|---------|
| Dashboard | 从只读改为可写管理 |
| Star Office | 增加可操作性（任务分配）|
| ClawCompany | 增加预算熔断硬边界 |
| Mission Control | 简化审批流程，适合一人公司 |

---

## 快速启动参考

### ClawCompany 的启动方式（值得学习）

```bash
npx clawcompany
# 3步向导，30秒启动
```

我们的目标：
```bash
npx openclaw-opc
# 或
docker-compose up -d
```

### Star Office UI 的部署（极简）

```bash
git clone ...
pip install -r requirements.txt
python app.py
# 无需 Docker，单 Python 文件
```

我们的选择：提供两种方案
- 开发者: Docker Compose
- 快速体验: 纯 Python/Node 启动

---

## 差异化定位

| 项目 | 核心特点 | 我们定位 |
|------|---------|---------|
| Dashboard | 轻量监控 | 完整管理 + 游戏化 |
| Mission Control | 企业治理 | 一人公司 + 预算控制 |
| Star Office | 状态可视化 | 可操作 + 成长系统 |
| ClawCompany | CLI 自动化 | Web UI + 可视化管理 |
| **OpenClaw OPC** | **游戏化一人公司** | **预算可控 + 像素办公室 + 员工成长** |

---

## 检查清单

开发每个功能前，先检查：

- [ ] 参考 Dashboard 有无类似实现
- [ ] 参考 Mission Control 的架构设计
- [ ] 参考 Star Office 的 UI 方案
- [ ] 参考 ClawCompany 的交互逻辑
- [ ] 如无现成方案，再自主设计

---

*Last Updated: 2026-03-21*
