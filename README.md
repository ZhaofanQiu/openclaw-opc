# OpenClaw One-Person Company (OPC)

> 基于 OpenClaw 的多 Agent 协作可视化管理工具
> 将 AI Agent 作为员工管理，构建你的一人公司

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0--alpha-blue)](https://github.com/ZhaofanQiu/openclaw-opc)
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
- 🛡️ **安全第一** - 预算熔断机制，防止 Token 无限消耗

---

## 🚀 快速开始

### 使用 Docker (推荐)

```bash
# 1. 克隆仓库
git clone https://github.com/ZhaofanQiu/openclaw-opc.git
cd openclaw-opc

# 2. 一键启动
chmod +x start.sh
./start.sh

# 3. 打开浏览器访问
# Dashboard: http://localhost:3000
# API Docs:  http://localhost:8080/docs
```

### 手动安装

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 启动 Core Service
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8080

# 3. 打开前端
# 直接打开 web/index.html 或使用任意静态服务器
# 或访问 http://localhost:8080/dashboard/
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
├── web/                  # 前端仪表板 (HTML/CSS/JS)
│   └── index.html
├── skill/                # OPC Bridge Skill
│   └── SKILL.md
├── docs/                 # 文档
│   ├── WEEK1_REPORT.md   # Week 1 完成报告
│   ├── WEEK2_PLAN.md     # Week 2 计划
│   ├── TECHNICAL.md      # 技术方案
│   └── ROADMAP.md        # 路线图
├── docker-compose.yml    # Docker 编排
├── nginx.conf            # Nginx 配置
└── start.sh              # 一键启动脚本
```

---

## 📖 API 文档

启动服务后访问：http://localhost:8080/docs

### 主要端点

```
# OpenClaw 集成
GET  /api/agents/openclaw/agents     # 读取现有 OpenClaw Agents

# Partner 管理
POST /api/agents/partner/setup       # 设置 Partner
POST /api/agents/partner/hire        # Partner 招聘员工
GET  /api/agents/partner/status      # Partner 查看公司状态
POST /api/agents/partner/assign/{id} # Partner 自动分配任务
POST /api/agents/partner/assign-all  # Partner 批量分配任务

# Agent 管理
GET  /api/agents                     # 列出所有员工
POST /api/agents                     # 创建员工
GET  /api/agents/{id}/task           # 查询当前任务
POST /api/agents/report              # 上报任务完成

# 任务管理
GET  /api/tasks                      # 列出任务
POST /api/tasks                      # 创建任务
POST /api/tasks/{id}/assign          # 分配任务

# 预算管理
GET  /api/budget/company             # 公司预算概览
GET  /api/budget/agents/{id}         # 员工预算详情
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
  -d '{"title": "重构登录页", "estimated_cost": 200}'

# Partner 自动分配
curl -X POST "http://localhost:8080/api/agents/partner/assign/{task_id}?partner_id=main"
```

### 4. 查看仪表板

打开浏览器访问 http://localhost:3000 查看实时状态。

---

## 📚 文档索引

| 文档 | 内容 |
|------|------|
| [WEEK1_REPORT.md](./docs/WEEK1_REPORT.md) | Week 1 完成报告 |
| [TECHNICAL.md](./docs/TECHNICAL.md) | 技术方案 |
| [ROADMAP.md](./docs/ROADMAP.md) | 开发路线图 |

---

## 🛠️ 开发状态

| 组件 | 状态 | 版本 |
|------|------|------|
| Core Service | ✅ 完成 | v0.1.0 |
| Web Dashboard | ✅ 完成 | v0.1.0 |
| Partner Auto-Assign | ✅ 完成 | v0.1.0 |
| OPC Bridge Skill | ✅ 完成 | v0.1.0 |
| Docker 部署 | ✅ 完成 | v0.1.0 |
| 像素办公室 | ⏳ Week 3 | - |

---

## 🤝 贡献

欢迎提交 Issue 和 PR！

---

## 📜 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

*Built with ❤️ for the OpenClaw community*
