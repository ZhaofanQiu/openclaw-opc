# 开发路线图 (Roadmap) - 技术方案确认版

## 版本规划

### v0.1.0-alpha (种子期)
**目标:** 证明概念可行，能完整跑通任务流程
**时间:** 4 周 (务实评估)

#### Week 1: 骨架 + 技术验证

**核心目标**: 验证 OpenClaw 集成方案可行

**Day 1-2: Core Service 骨架**
- [x] FastAPI 项目初始化
- [ ] SQLite 数据库 + SQLAlchemy
- [ ] 模型: Employee, Task
- [ ] API: POST /api/agents/report (接收 Agent 上报)
- [ ] API: GET /api/tasks (查询待办任务)
- [ ] 测试: curl 能调通

**Day 3-4: OPC Bridge Skill**
- [ ] Skill 目录结构 `~/.openclaw/skills/opc-bridge/`
- [ ] SKILL.md 定义
- [ ] 实现 report_to_core() 函数
- [ ] 测试: Agent 能调用 Skill 发送 HTTP

**Day 5-7: Partner Agent 配置 + 验证**
- [ ] 配置 Partner Agent (tools.allow)
- [ ] 配置 Employee Agent
- [ ] 验证 Agent 能查询任务
- [ ] 验证 Agent 能上报完成
- [ ] 完整流程: 创建任务 → Agent 执行 → 上报 → 预算扣减

**Week 1 里程碑**:
- [ ] Agent 能连接到 Core Service
- [ ] 任务能分配给 Agent
- [ ] Agent 完成能上报到 Core
- [ ] 预算余额正确更新

---

#### Week 2: 预算与熔断

**核心目标**: 预算追踪和熔断机制可靠

**Day 8-10: 预算核心**
- [ ] 预算余额实时计算
- [ ] 任务预估成本
- [ ] 实际消耗追踪
- [ ] 预算不足时拒绝任务分配

**Day 11-12: 熔断机制**
- [ ] 80% 警告 (UI + Partner 通知)
- [ ] 100% 暂停 (硬停止)
- [ ] 熔断后人工恢复流程
- [ ] 熔断事件记录

**Day 13-14: 测试与修复**
- [ ] 模拟高消耗任务
- [ ] 验证熔断触发
- [ ] 边界情况处理

**Week 2 里程碑**:
- [ ] 预算消耗实时可见
- [ ] 熔断机制可靠触发
- [ ] 用户能在 UI 看到预算状态

---

#### Week 3: 员工管理与游戏化基础

**核心目标**: 能创建员工，氛围系统基础

**Day 15-17: 员工 CRUD**
- [ ] 创建员工 API
- [ ] 员工列表/详情 API
- [ ] Partner 初始化流程
- [ ] 员工配置生成 (workspace, SOUL.md)

**Day 18-19: 简单 UI**
- [ ] 员工列表页面
- [ ] 创建员工表单
- [ ] 任务列表页面
- [ ] 预算仪表盘 (简化版)

**Day 20-21: 氛围系统基础**
- [ ] 心情 = 预算比例映射
- [ ] 简单心情显示
- [ ] 工作日报生成

**Week 3 里程碑**:
- [ ] 能在 UI 创建员工
- [ ] 员工有心情显示
- [ ] Partner 初始化流程完整

---

#### Week 4: 收尾与演示

**核心目标**: 能给别人演示完整流程

**Day 22-24: 流程完善**
- [ ] 待处理收件箱 (简化版)
- [ ] 错误处理
- [ ] 数据持久化

**Day 25-26: 部署**
- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] README 完善

**Day 27-28: 测试与演示准备**
- [ ] 完整流程测试
- [ ] 修复明显 Bug
- [ ] 准备演示脚本

**Week 4 里程碑**:
- [ ] Docker 一键启动
- [ ] 能完整演示: 创建公司 → 招聘 → 分配任务 → 预算消耗
- [ ] 发布 v0.1.0-alpha

---

### v0.2.0-beta (成长期)
**目标:** 日常可用，游戏化完整
**时间:** 6-8 周

- [ ] 工作手册系统 (L1/L2/L3)
- [ ] 技能熟练度追踪
- [ ] 员工成长系统 (等级/经验值)
- [ ] 任务系统完善 (类型/优先级)
- [ ] 留言板系统
- [ ] 像素办公室 V1 (静态可视化)

---

### v1.0.0 (正式版)
**目标:** 生产就绪
**时间:** 2-3 个月

- [ ] 员工退休与传承
- [ ] 项目复盘报告
- [ ] 事件系统 (自动触发)
- [ ] 像素办公室 V2 (动画)
- [ ] 移动端适配
- [ ] 完整文档
- [ ] 社区发布

---

## 技术方案确认

### OpenClaw 集成 (已验证可行)

**方案**: Partner Agent + OPC Bridge Skill

```
Core Service ← HTTP → OPC Bridge Skill ← 安装在 → Agent
                    ↑
            Partner Agent 协调
```

**Key Points**:
1. 每个 Agent 安装 `opc-bridge` Skill
2. Skill 提供 `report_to_core()` 函数
3. Partner Agent 负责协调任务分配
4. Core Service 通过 HTTP 接收上报

---

## 当前 Sprint (Week 1)

### 本周任务

**我 (开发)**:
- [x] 分析 OpenClaw 文档，确认技术方案
- [ ] Day 1: Core Service FastAPI 骨架
- [ ] Day 2: 数据库 + API 基础
- [ ] Day 3-4: OPC Bridge Skill
- [ ] Day 5-7: Partner Agent 配置

**你 (产品/测试)**:
- [ ] 提供配置好的 OpenClaw 机器用于测试
- [ ] 确认 Employee Agent 配置 (名字、岗位)
- [ ] 测试任务流程

### 需要确认

1. 你的 Partner Agent 叫什么名字？
2. 第一个 Employee Agent 叫什么名字？什么岗位？
3. 测试机器的 SSH 访问方式？

---

## 技术债务

| 项 | 当前方案 | 未来优化 | 优先级 |
|---|---------|---------|--------|
| 数据库 | SQLite | PostgreSQL (多用户) | 中 |
| 通信 | HTTP POST | WebSocket / SSE | 中 |
| 像素办公室 | Week 3 不做 | V1 静态 / V2 动画 | 低 |
| 熔断精度 | 任务级 | Token 级精确追踪 | 低 |

---

*Last Updated: 2026-03-21 - 技术方案确认*
