# OpenClaw OPC 重构执行计划

**分支**: refactor/core-redesign  
**目标**: 从虚假繁荣到真实可用  
**原则**: Layer 1 跑通前，不碰 Layer 2/3

---

## 当前状态

- 文档已清理：40+ → 14 个核心文档
- Router 备份完成：31 个文件已备份
- 准备开始代码重构

---

## 重构阶段

### Phase 1: 架构重构（2天）

#### Day 1: Router 合并

**目标**: 31 个 router → 12 个 router

**合并计划**:

| 新文件 | 合并来源 | 状态 |
|--------|----------|------|
| `agents.py` | agents + avatars + skills + skill_growth + agent_skill_paths + agent_interaction_logs | ⏳ |
| `tasks.py` | tasks + task_assignment + task_steps + task_dependencies + sub_tasks | ⏳ |
| `workflows.py` | workflows + workflows_optimized + workflow_details + workflow_templates + workflow_extensions | ⏳ |
| `messages.py` | async_messages + notifications + communication | ⏳ |
| `budgets.py` | budget + fuse | ⏳ |
| `manuals.py` | 保持独立 | ✅ |
| `approvals.py` | 保持独立 | ✅ |
| `reports.py` | 保持独立 | ✅ |
| `config.py` | 保持独立 | ✅ |
| `monitor.py` | 保持独立 | ✅ |
| `share.py` | 保持独立 | ✅ |
| `websocket.py` | 保持独立 | ✅ |

**检查点**:
- [ ] 所有 API 端点正常工作
- [ ] 前端页面能正常调用

#### Day 2: Service 合并

**目标**: 35 个 service → 15 个 service

**合并计划**:

| 新文件 | 合并来源 | 状态 |
|--------|----------|------|
| `agent_service.py` | agent_service + agent_lifecycle_service + avatar_service | ⏳ |
| `task_service.py` | task_service + task_step_service + task_execution_service | ⏳ |
| `workflow_service.py` | workflow_*_service (5个) | ⏳ |
| `message_service.py` | notification_service + async_message_service + communication_service | ⏳ |
| `manual_service.py` | 保持独立 | ✅ |
| `budget_service.py` | budget_service + fuse_service | ⏳ |
| `skill_service.py` | skill_service + skill_growth_service | ⏳ |
| `report_service.py` | report_service + exact_token_service | ⏳ |

**检查点**:
- [ ] 所有服务正常初始化
- [ ] 依赖注入正常

---

### Phase 2: 核心层实现（2周）

#### Week 1: Agent 交互闭环

**目标**: 实现真正的 Agent 唤醒和响应

**核心文件**: `core/agent_interaction.py`

**实现内容**:
1. **Agent 唤醒**
   - 调用 OpenClaw `sessions_spawn`
   - 传递任务上下文
   - 接收会话 ID

2. **消息传递**
   - 用户消息 → Agent
   - Agent 回复 → 存储

3. **状态同步**
   - 轮询 Agent 状态
   - 更新任务状态

**检查点**:
- [ ] 创建员工 → 绑定 Agent → 能真实唤醒
- [ ] 发送消息 → Agent 真实收到
- [ ] Agent 回复 → 真实存储到数据库

#### Week 2: 三维度整合

**目标**: Message + Skill + Manual 控制 Agent 行为

**核心文件**:
- `core/skill_framework.py`
- `core/manual_application.py`

**实现内容**:
1. **Skill 框架**
   - Skill 定义格式
   - Skill 加载机制
   - Agent 行为约束

2. **手册应用**
   - 手册读取
   - 约束条件应用
   - 经验注入

3. **三维度整合**
   - Message: 任务上下文
   - Skill: 行为规范
   - Manual: 操作经验
   - 统一控制 Agent 输出

**检查点**:
- [ ] 任务包含完整上下文
- [ ] Agent 按 Skill 规范执行
- [ ] Agent 参考 Manual 内容

---

### Phase 3: 端到端验证（1周）

#### Week 3: 完整流程验证

**目标**: 跑通完整的任务流程

**测试场景**:

```
场景 1: 简单任务
1. 创建员工
2. 创建任务
3. 分配任务
4. Agent 执行
5. 查看结果
6. 完成任务

场景 2: 带手册的任务
1. 创建任务（触发手册生成）
2. 分配任务
3. Agent 参考手册执行
4. 验证手册约束生效

场景 3: 带 Skill 的任务
1. 创建带 Skill 的员工
2. 分配相关任务
3. 验证 Skill 约束生效
```

**检查点**:
- [ ] 所有场景真实可用（非 mock）
- [ ] Token 消耗正确计算
- [ ] 预算熔断正常工作

---

### Phase 4: 功能精简（1周）

#### Week 4: 移除冗余功能

**移除清单**:

| 功能 | 原因 | 处理方式 |
|------|------|----------|
| 复杂工作流引擎 | 过度设计 | 冻结，用简化版 |
| WebSocket 实时通知 | 不需要 | 移除 |
| 多语言支持 | 分散精力 | 冻结，先中文 |
| 社区市场 | 远期功能 | 移除 |
| 像素办公室 V1 | 重复 | 移除 |
| 复杂技能成长 | 未实际影响 | 简化 |
| 员工心情详细计算 | 过于复杂 | 简化 |
| 财务详细报表 | 非核心 | 简化 |

**检查点**:
- [ ] 代码量减少 50%+
- [ ] 功能真实可用

---

### Phase 5: 稳定与文档（1周）

#### Week 5: 文档重写与测试

**文档重写**:
- [ ] README.md - 简洁明了
- [ ] DESIGN.md - 更新为实际设计
- [ ] ARCHITECTURE.md - 新架构图
- [ ] ROADMAP.md - 新路线图
- [ ] API.md - 整理

**测试**:
- [ ] 单元测试覆盖核心逻辑
- [ ] 集成测试覆盖关键流程
- [ ] 端到端测试通过

**检查点**:
- [ ] 文档与代码一致
- [ ] 测试全部通过

---

## 合并检查清单

### Router 合并步骤

对于每个合并：

1. [ ] 创建新文件
2. [ ] 复制路由定义
3. [ ] 统一前缀
4. [ ] 解决冲突
5. [ ] 更新 main.py 注册
6. [ ] 测试所有端点
7. [ ] 删除旧文件

### Service 合并步骤

对于每个合并：

1. [ ] 分析依赖关系
2. [ ] 创建新服务类
3. [ ] 合并业务逻辑
4. [ ] 统一错误处理
5. [ ] 更新 router 引用
6. [ ] 测试服务方法
7. [ ] 删除旧文件

---

## 风险与应对

| 风险 | 可能性 | 影响 | 应对 |
|------|--------|------|------|
| 合并后功能损坏 | 高 | 高 | 每合并一个就测试 |
| 重构时间过长 | 中 | 中 | 严格按阶段执行 |
| Agent 交互难实现 | 中 | 高 | 先 POC 验证 |
| 测试覆盖不足 | 中 | 高 | 强制测试要求 |

---

## 当前进度

- [x] Phase 0: 文档清理
- [ ] Phase 1: 架构重构
  - [ ] Day 1: Router 合并
  - [ ] Day 2: Service 合并
- [ ] Phase 2: 核心层实现
- [ ] Phase 3: 端到端验证
- [ ] Phase 4: 功能精简
- [ ] Phase 5: 稳定与文档

---

**最后更新**: 2026-03-23  
**负责人**: Kimi Claw
