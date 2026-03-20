# OpenClaw One-Person Company (OPC)

> 基于 OpenClaw 的多 Agent 协作可视化管理工具
> 将 AI Agent 作为员工管理，构建你的一人公司

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.2.0--alpha-blue)](https://github.com/ZhaofanQiu/openclaw-opc)
[![OpenClaw](https://img.shields.io/badge/Built%20for-OpenClaw-green)](https://openclaw.ai)

---

## 🎯 核心理念

**不是让 AI 替代你，而是让 AI 成为你的团队，你当 CEO。**

OpenClaw OPC 是一个数字化的微型公司操作系统，让你能够将多个 OpenClaw Agent 组织成一个协作团队，像管理真实公司一样管理它们。

### 关键特性

- 🏢 **员工化管理** - Agent 拥有职位、技能、预算
- 💰 **预算控制** - Token 消耗转化为 OC币，实时熔断保护
- 👑 **Partner 协调** - Partner Agent 自动分配任务
- 📊 **可视化仪表板** - Web UI 实时查看公司状态
- 🎨 **像素办公室** - 游戏化可视化，实时监控员工状态
- 🛡️ **安全第一** - 预算熔断机制，防止 Token 无限消耗
- 📈 **工作日报** - 自动生成每日工作汇总

---

## 🚀 快速开始

### 使用 Docker (推荐)

```bash
# 1. 克隆仓库
git clone https://github.com/ZhaofanQiu/openclaw-opc.git
cd openclaw-opc

# 2. 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 文件修改配置

# 3. 一键启动
chmod +x start.sh
./start.sh

# 4. 打开浏览器访问
# Dashboard:      http://localhost:3000
# 像素办公室:      http://localhost:3000/pixel-office
# 工作日报:        http://localhost:3000/reports
# API Docs:       http://localhost:8080/docs
```

### 手动安装

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 启动 Core Service
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8080

# 3. 打开前端
# 访问 http://localhost:8080/dashboard/
```

---

## 📁 项目结构

```
openclaw-opc/
├── backend/              # Core Service (FastAPI)
│   ├── src/
│   │   ├── main.py       # FastAPI 应用
│   │   ├── models/       # 数据库模型
│   │   ├── routers/      # API 路由
│   │   └── services/     # 业务逻辑
│   ├── requirements.txt
│   └── Dockerfile
├── web/                  # 前端仪表板
│   ├── index.html        # Dashboard
│   ├── pixel-office.html # 像素办公室
│   └── reports.html      # 工作日报
├── skill/                # OPC Bridge Skill
│   └── SKILL.md
├── docs/                 # 文档
│   ├── PROGRESS_REPORT.md  # 进展报告
│   ├── TECHNICAL.md        # 技术方案
│   └── ROADMAP.md          # 路线图
├── docker-compose.yml    # Docker 编排
├── nginx.conf            # Nginx 配置
└── start.sh              # 一键启动脚本
```

---

## 📖 API 文档

启动服务后访问：http://localhost:8080/docs

### 主要端点

#### Agent 管理
```
GET  /api/agents                     # 列出所有员工
POST /api/agents                     # 创建员工
GET  /api/agents/{id}                # 员工详情
GET  /api/agents/{id}/task           # 查询当前任务
```

#### Partner 管理
```
POST /api/agents/partner/setup       # 设置 Partner
POST /api/agents/partner/hire        # Partner 招聘员工
GET  /api/agents/partner/status      # Partner 查看公司状态
POST /api/agents/partner/assign/{id} # Partner 自动分配任务
POST /api/agents/partner/assign-all  # Partner 批量分配任务
POST /api/agents/partner/heartbeat   # Partner 心跳检测
GET  /api/agents/partner/health      # Partner 健康状态
```

#### 任务管理
```
GET  /api/tasks                      # 列出任务
POST /api/tasks                      # 创建任务
GET  /api/tasks/{id}                 # 任务详情
POST /api/tasks/{id}/assign          # 手动分配任务
```

#### 技能系统
```
GET  /api/skills                     # 列出所有技能
GET  /api/skills/match/{task_id}     # 匹配最佳员工
```

#### 预算管理
```
GET  /api/budget/company             # 公司预算概览
GET  /api/budget/agents/{id}         # 员工预算详情
POST /api/agents/report              # 上报任务完成（扣减预算）
```

#### 报告系统
```
GET  /api/reports/daily              # 日报（默认昨天）
GET  /api/reports/weekly             # 周报
GET  /api/reports/recent             # 最近N天汇总
```

#### 系统配置
```
GET  /api/config                     # 获取系统配置
POST /api/config                     # 更新系统配置
```

#### 通知系统
```
GET  /api/notifications              # 获取通知列表
POST /api/notifications/{id}/read    # 标记已读
DELETE /api/notifications/{id}       # 删除通知
```

---

## 🎮 使用流程

### 1. 初始化公司

```bash
# 查看现有 OpenClaw Agents
curl http://localhost:8080/api/agents/openclaw/agents

# 设置 Partner
curl -X POST http://localhost:8080/api/agents/partner/setup \
  -H "Content-Type: application/json" \
  -d '{"openclaw_agent_id": "main", "monthly_budget": 10000}'

# 初始化公司
curl -X POST http://localhost:8080/api/agents/company/init \
  -H "Content-Type: application/json" \
  -d '{"partner_agent_id": "main", "company_name": "星际工作室"}'
```

### 2. 招聘员工

```bash
# Partner 招聘员工
curl -X POST "http://localhost:8080/api/agents/partner/hire?partner_id=main" \
  -H "Content-Type: application/json" \
  -d '{"name": "前端阿强", "agent_id": "frontend-1", "monthly_budget": 3000}'
```

### 3. 创建并分配任务

```bash
# 创建任务
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "重构登录页", "description": "使用React重构", "estimated_cost": 200, "required_skills": ["javascript", "ui-design"]}'

# Partner 自动分配（按预算策略）
curl -X POST "http://localhost:8080/api/agents/partner/assign/{task_id}?partner_id=main&strategy=budget"
```

### 4. 查看仪表板

| 页面 | URL | 功能 |
|------|-----|------|
| Dashboard | http://localhost:3000 | 员工、任务、预算总览 |
| 像素办公室 | http://localhost:3000/pixel-office | 可视化员工状态 |
| 工作日报 | http://localhost:3000/reports | 每日/每周工作汇总 |

---

## ✨ v0.2.0-alpha 新功能

### 🎨 像素办公室
- CSS Grid 布局的 8 工位可视化
- 像素风格 SVG 头像（根据职位自动匹配）
- 实时状态显示（工作中/空闲/离线）
- 预算进度条可视化
- 任务看板状态统计

### 📊 工作日报
- 自动生成每日/每周工作汇总
- 统计：完成任务数、消耗OC币、新建任务、完成率
- 员工表现排名
- 最近7天趋势

### 🎯 员工技能系统
- 8个默认技能（Python、JS、DB、UI等）
- 技能熟练度（0-100）
- 任务-员工自动匹配
- 最佳员工推荐

### 🔔 通知系统
- 任务分配/完成/失败通知
- 预算警告通知
- 任务超时提醒
- 右上角通知中心

### ⚙️ 系统配置面板
- 任务超时时间配置
- Token换算比例
- 预算警告阈值
- 自动分配策略

### 💓 Partner 健康监控
- 心跳检测机制
- 在线/离线状态显示
- 超时自动标记离线

---

## 📚 文档索引

| 文档 | 内容 |
|------|------|
| [PROJECT_STATUS.md](./docs/PROJECT_STATUS.md) | 项目完成状态与发布信息 |
| [PROJECT_REVIEW.md](./docs/PROJECT_REVIEW.md) | 项目Review与优化方案 |
| [ROADMAP.md](./docs/ROADMAP.md) | 未来开发路线图 |
| [TECHNICAL.md](./docs/TECHNICAL.md) | 技术方案详细说明 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本变更记录 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 贡献指南 |
| [archive/](./docs/archive/) | 历史文档归档 |

---

## 🛠️ 开发状态

| 组件 | 状态 | 版本 |
|------|------|------|
| Core Service | ✅ 完成 | v0.2.1 |
| Web Dashboard | ✅ 完成 | v0.2.0 |
| 像素办公室 | ✅ 完成 | v0.2.0 |
| 员工技能系统 | ✅ 完成 | v0.2.0 |
| Partner 自动分配 | ✅ 完成 | v0.2.0 |
| Partner 健康监控 | ✅ 完成 | v0.2.0 |
| 工作日报 | ✅ 完成 | v0.2.0 |
| 通知系统 | ✅ 完成 | v0.2.0 |
| 系统配置面板 | ✅ 完成 | v0.2.0 |
| OPC Bridge Skill | ✅ 完成 | v0.2.0 |
| Docker 部署 | ✅ 完成 | v0.2.0 |
| **结构化日志** | ✅ 完成 | **v0.2.1** |
| **API限流** | ✅ 完成 | **v0.2.1** |
| **输入验证** | ✅ 完成 | **v0.2.1** |

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

---

## 📜 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

*Built with ❤️ for the OpenClaw community*
