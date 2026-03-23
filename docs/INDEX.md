# OPC 文档索引

> 快速找到你需要的文档

---

## 🚀 快速开始

| 我想... | 看这篇文档 |
|---------|-----------|
| 了解 Agent 配置注意事项 | [`AGENT_CONFIG_NOTES.md`](AGENT_CONFIG_NOTES.md) |
| 了解 Agent 交互最佳实践 | [`AGENT_INTERACTION_BEST_PRACTICES.md`](AGENT_INTERACTION_BEST_PRACTICES.md) ⭐ |
| 了解任务分配设计 | [`TASK_ASSIGNMENT_DESIGN_v2.md`](TASK_ASSIGNMENT_DESIGN_v2.md) ⭐ |
| 了解 Agent 使用策略 | [`AGENT_STRATEGY.md`](AGENT_STRATEGY.md) |
| 了解系统架构 | [`ARCHITECTURE_v2.md`](ARCHITECTURE_v2.md) |

---

## 📚 核心文档（推荐必读）

### ⭐ `AGENT_INTERACTION_BEST_PRACTICES.md`
**最重要的经验总结文档**

包含：
- 三条最重要的经验
- 完整的交互流程
- 常见错误及解决方案
- 调试技巧

**适合**: 所有开发者，特别是刚接触 OPC 的人

---

### ⭐ `AGENT_CONFIG_NOTES.md`
**Agent 配置指南**

包含：
- 为什么不需要 `tools` 和 `skills` 字段
- 正确的配置示例
- 验证方法
- 常见问题

**适合**: 配置 Agent 时参考

---

### ⭐ `TASK_ASSIGNMENT_DESIGN_v2.md`
**任务分配系统设计（实践版）**

包含：
- 实际任务消息格式
- 完整的任务流程
- 后端实现要点
- 调试清单

**适合**: 开发任务分配功能时参考

---

## 📖 其他文档

### 架构设计
- `ARCHITECTURE_v2.md` - v2.0 架构设计
- `DESIGN.md` - 原始设计文档
- `TECHNICAL.md` - 技术细节

### 功能设计
- `AGENT_STRATEGY.md` - Agent 使用策略
- `BUDGET.md` - 预算系统设计
- `EMPLOYEE.md` - 员工系统设计
- `TASK_CHAT_SYSTEM_DESIGN.md` - 任务聊天系统
- `TASK_WORKFLOW_UNIFIED_DESIGN.md` - 工作流设计
- `UI.md` - 界面设计

### API 文档
- `API.md` - API 文档

### 开发指南
- `CONTRIBUTING.md` - 开发贡献指南
- `REFERENCES.md` - 参考资料
- `ROADMAP.md` - 路线图

### 运维文档
- `operations/CPOLAR_SETUP.md` - Cpolar 部署
- `operations/CLOUDFLARE_TUNNEL.md` - Cloudflare 隧道
- `operations/POSTGRESQL_MIGRATION.md` - PostgreSQL 迁移

### 项目文档
- `README.md` - 项目介绍
- `REFACTOR_COMPLETE.md` - 重构完成报告

---

## 🔍 按场景查找

### 场景 1: 配置 Agent 遇到问题

1. 先看 [`AGENT_CONFIG_NOTES.md`](AGENT_CONFIG_NOTES.md)
2. 如果还有问题，看 [`AGENT_INTERACTION_BEST_PRACTICES.md`](AGENT_INTERACTION_BEST_PRACTICES.md) 的"常见问题"部分

### 场景 2: 开发任务分配功能

1. 先看 [`TASK_ASSIGNMENT_DESIGN_v2.md`](TASK_ASSIGNMENT_DESIGN_v2.md)
2. 参考后端实现代码：`backend/src/routers/tasks.py`
3. 回调处理参考：`backend/src/routers/skill_api.py`

### 场景 3: Agent 回调失败

1. 先看 [`AGENT_INTERACTION_BEST_PRACTICES.md`](AGENT_INTERACTION_BEST_PRACTICES.md) 的"常见错误及解决方案"
2. 检查 OPC 服务是否运行：`curl http://localhost:8080/health`
3. 检查回调脚本配置：`cat ~/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py`

### 场景 4: 了解整体架构

1. 先看 [`ARCHITECTURE_v2.md`](ARCHITECTURE_v2.md)
2. 再看 [`DESIGN.md`](DESIGN.md)

---

## ⚠️ 过时文档

以下文档可能包含过时信息，仅供参考：

- `TASK_ASSIGNMENT_DESIGN.md` - 旧版任务分配设计（未经验证）
- `ARCHITECTURE.md` - 旧版架构设计（重构前）

**推荐查看对应的 `_v2.md` 版本**，这些是基于实践验证的最新文档。

---

## 📝 文档更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-03-23 | 创建 `AGENT_INTERACTION_BEST_PRACTICES.md`，总结闭环测试经验 |
| 2026-03-23 | 更新 `AGENT_CONFIG_NOTES.md`，添加实践经验 |
| 2026-03-23 | 创建 `TASK_ASSIGNMENT_DESIGN_v2.md`，基于实践修订 |
| 2026-03-23 | 更新 `AGENT_STRATEGY.md`，添加实践经验 |
| 2026-03-23 | 创建 `DEPLOYMENT.md` - 新用户部署指南 |
| 2026-03-23 | **修复**: 更新 `skills/opc-bridge-v2/` 为 v2 版本（原目录为旧版本）|
| 2026-03-23 | 创建本文档索引 |

---

## 💡 建议

1. **新手入门**: 先读 `AGENT_INTERACTION_BEST_PRACTICES.md`
2. **配置 Agent**: 参考 `AGENT_CONFIG_NOTES.md`
3. **开发功能**: 参考对应的 `_v2.md` 设计文档
4. **遇到问题**: 先在 `AGENT_INTERACTION_BEST_PRACTICES.md` 的"常见错误"部分查找

---

**最后更新**: 2026-03-23  
**维护者**: OPC 开发团队
