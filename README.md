# OpenClaw One-Person Company (OPC)

> 基于 OpenClaw 的多 Agent 协作可视化管理工具
> 将 AI Agent 作为员工管理，构建你的一人公司

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw](https://img.shields.io/badge/Built%20for-OpenClaw-blue)](https://openclaw.ai)

---

## 🎯 核心理念

**不是让 AI 替代你，而是让 AI 成为你的团队，你当 CEO。**

OpenClaw OPC 是一个数字化的微型公司操作系统，让你能够将多个 OpenClaw Agent 组织成一个协作团队，像管理真实公司一样管理它们。

### 关键特性

- 🏢 **员工化管理** - Agent 拥有职位、技能、成长曲线
- 💰 **预算控制** - Token 消耗转化为虚拟币，实时熔断保护
- 📊 **可视化办公** - 像素风办公室，实时查看员工状态
- 📚 **工作手册** - 员工经验沉淀为可传承的资产
- 🤝 **多 Agent 协作** - 任务分配、协作讨论、代码审查
- 🛡️ **安全第一** - 多层熔断机制，防止 Token 无限消耗

---

## 📁 项目结构

```
openclaw-opc/
├── packages/
│   ├── core/          # 后端服务 (FastAPI + SQLite)
│   ├── ui/            # 前端界面 (React + PixiJS)
│   └── plugin/        # OpenClaw 插件
├── docs/              # 设计文档
├── scripts/           # 辅助脚本
└── docker-compose.yml # 一键启动
```

---

## 🚀 快速开始

### 使用 Docker (推荐)

```bash
# 1. 克隆仓库
git clone https://github.com/ZhaofanQiu/openclaw-opc.git
cd openclaw-opc

# 2. 一键启动
make setup
make dev

# 3. 打开浏览器
open http://localhost:3000
```

### 手动安装

详见 [docs/setup.md](./docs/setup.md)

---

## 📖 文档索引

| 文档 | 内容 |
|------|------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 系统架构设计 |
| [DESIGN.md](./docs/DESIGN.md) | 产品功能设计 |
| [EMPLOYEE.md](./docs/EMPLOYEE.md) | 员工系统设计 |
| [PROJECT.md](./docs/PROJECT.md) | 项目与任务系统 |
| [BUDGET.md](./docs/BUDGET.md) | 预算与熔断机制 |
| [UI.md](./docs/UI.md) | 界面设计规范 |
| [API.md](./docs/API.md) | API 接口文档 |
| [ROADMAP.md](./docs/ROADMAP.md) | 开发路线图 |

---

## 🤝 贡献

欢迎提交 Issue 和 PR！详见 [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📜 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

*Built with ❤️ for the OpenClaw community*
