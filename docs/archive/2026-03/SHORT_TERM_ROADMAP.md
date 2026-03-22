# OPC 系统短期功能推进计划

## 概述

本文档提供 OPC 系统在短期（2-4 周）内可实现的优先级功能推进计划，聚焦快速交付可用功能。

---

## Week 1: 认证与基础完善

### 目标
建立用户认证体系，修复硬编码问题，使系统具备基本的多用户支持能力。

### 任务清单

#### Day 1-2: 用户认证实现
- [ ] **JWT 认证中间件**
  - 文件: `src/utils/jwt_auth.py`
  - 功能: Token 生成、验证、刷新
  - 输出: 可复用的认证依赖

- [ ] **API Key 认证增强**
  - 文件: `src/utils/api_auth.py`
  - 功能: API Key 关联用户身份
  - 输出: 当前用户上下文

#### Day 3: 替换硬编码用户 ID
- [ ] **任务分配认证**
  - 文件: `src/services/task_service.py:107`
  - 修改: `assigner_id` 从认证获取

- [ ] **消息发送认证**
  - 文件: `src/routers/communication.py:75,119`
  - 修改: `sender_id` 从认证获取

- [ ] **结算评价认证**
  - 文件: `src/services/task_step_service.py`
  - 修改: `settled_by` 从认证获取

#### Day 4: 用户上下文传递
- [ ] **请求上下文中间件**
  - 文件: `src/middleware/context.py` (新建)
  - 功能: 在请求生命周期内存储当前用户

- [ ] **服务层用户获取**
  - 文件: `src/utils/current_user.py` (新建)
  - 功能: 全局获取当前登录用户

#### Day 5: 集成测试
- [ ] **认证流程测试**
  - 创建测试用户
  - 测试 Token 认证
  - 测试 API Key 认证
  - 验证用户隔离

### 交付物
- [ ] JWT 认证系统
- [ ] 用户上下文机制
- [ ] 零硬编码用户 ID
- [ ] 认证测试用例

---

## Week 2: 手册系统 MVP

### 目标
实现手册模板引擎，为 Agent 提供基本的任务行为规范。

### 任务清单

#### Day 1: 手册模型设计
- [ ] **手册数据模型**
  - 文件: `src/models/task_manual.py` (新建)
  - 字段: task_id, template_id, content, constraints, expected_output

- [ ] **手册模板表**
  - 文件: 更新 `src/models/__init__.py`
  - 预置: 5 个基础模板

#### Day 2-3: 模板引擎
- [ ] **模板引擎核心**
  - 文件: `src/services/manual_template_engine.py` (新建)
  - 功能: Jinja2 模板渲染
  - 支持: 变量替换、条件渲染、循环

- [ ] **预置模板**
  - 文件: `src/templates/manuals/` (新建目录)
  - 模板:
    - `code_review.j2` - 代码审查
    - `research.j2` - 研究调研
    - `writing.j2` - 内容创作
    - `data_analysis.j2` - 数据分析
    - `generic.j2` - 通用任务

#### Day 4: 手册生成服务
- [ ] **手册生成器**
  - 文件: `src/services/manual_service.py` (新建)
  - 功能: 根据任务选择模板并生成手册

- [ ] **任务分配集成**
  - 文件: `src/services/task_service.py`
  - 修改: 分配时自动生成手册

#### Day 5: 前端展示
- [ ] **手册预览组件**
  - 文件: `web/components/task-manual.js` (新建)
  - 功能: 在任务详情页展示手册

### 交付物
- [ ] 手册模板引擎
- [ ] 5 个预置模板
- [ ] 自动生成手册
- [ ] 前端手册展示

---

## Week 3: Skill 框架基础

### 目标
建立 Skill 注册和执行框架，为 Agent 提供可扩展的能力。

### 任务清单

#### Day 1-2: Skill 注册机制
- [ ] **Skill 装饰器**
  - 文件: `src/skills/decorator.py` (新建)
  - 功能: `@skill(name, description, permissions)`

- [ ] **Skill 注册表**
  - 文件: `src/skills/registry.py` (新建)
  - 功能: 自动发现、注册、查询 Skill

- [ ] **内置 Skills**
  - 文件: `src/skills/builtins/` (新建目录)
  - Skills:
    - `file_read` - 读取文件
    - `file_write` - 写入文件
    - `http_request` - HTTP 请求
    - `memory_search` - 记忆搜索

#### Day 3: Skill 执行器
- [ ] **执行器核心**
  - 文件: `src/skills/executor.py` (新建)
  - 功能: 权限检查、参数验证、执行、日志

- [ ] **执行上下文**
  - 文件: `src/skills/context.py` (新建)
  - 功能: 传递 Agent ID、任务 ID、用户权限

#### Day 4: Agent Skill 绑定
- [ ] **Skill 分配**
  - 文件: `src/services/skill_service.py`
  - 功能: 为员工分配可用 Skills

- [ ] **权限检查**
  - 文件: `src/skills/executor.py`
  - 功能: 执行前检查 Agent 是否有权限

#### Day 5: 集成测试
- [ ] **Skill 执行测试**
  - 测试文件读取
  - 测试 HTTP 请求
  - 测试权限控制

### 交付物
- [ ] Skill 注册机制
- [ ] 4 个内置 Skills
- [ ] Skill 执行框架
- [ ] 权限控制

---

## Week 4: 通知与状态

### 目标
完善 WebSocket 实时通知和 Agent 状态管理。

### 任务清单

#### Day 1-2: WebSocket 完善
- [ ] **Token 验证**
  - 文件: `src/routers/websocket.py:35`
  - 功能: 连接时验证用户身份

- [ ] **消息持久化**
  - 文件: `src/services/websocket_manager.py`
  - 功能: 用户离线时存储消息

- [ ] **断线重连**
  - 文件: `src/services/websocket_manager.py`
  - 功能: 重连后同步未读消息

#### Day 3: 通知实现
- [ ] **任务通知**
  - 文件: `src/services/task_step_service.py`
  - 实现: `_notify_agent_new_task`
  - 实现: `_notify_new_message`
  - 实现: `_notify_task_completed`

- [ ] **前端通知组件**
  - 文件: `web/components/notification-center.js` (新建)
  - 功能: 实时通知弹窗、未读徽章

#### Day 4: Agent 心跳
- [ ] **心跳协议**
  - 文件: `src/routers/websocket.py`
  - 功能: 定义心跳消息格式

- [ ] **在线状态检测**
  - 文件: `src/services/agent_status_service.py` (新建)
  - 功能: 根据心跳更新在线状态

- [ ] **超时处理**
  - 文件: `src/services/agent_status_service.py`
  - 功能: 超时未心跳标记为离线

#### Day 5: 集成与测试
- [ ] **端到端测试**
  - 任务分配 → WebSocket 通知
  - Agent 回复 → WebSocket 推送
  - 断线重连 → 消息同步

### 交付物
- [ ] WebSocket 认证
- [ ] 实时通知系统
- [ ] Agent 心跳机制
- [ ] 在线状态检测

---

## 关键路径依赖

```
Week 1 (认证)
    │
    ▼
Week 2 (手册) ──────▶ 依赖: 用户认证获取当前用户
    │
    ▼
Week 3 (Skill) ────▶ 依赖: 用户权限检查
    │
    ▼
Week 4 (通知) ─────▶ 依赖: 用户身份用于消息路由
```

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| JWT 实现复杂 | Week 1 延期 | 使用 FastAPI 官方示例，简化实现 |
| 模板引擎学习 | Week 2 延期 | 使用 Jinja2，文档完善 |
| WebSocket 调试困难 | Week 4 延期 | 优先实现轮询 fallback |
| 与现有代码冲突 | 任何阶段 | 每阶段结束进行回归测试 |

---

## 成功标准

### Week 1 完成标准
- [ ] 所有 API 必须通过认证才能访问
- [ ] 没有硬编码的 `"system"` 或 `"user"` 用户 ID
- [ ] 不同用户的任务数据互相隔离

### Week 2 完成标准
- [ ] 每个分配的任务都有对应的手册
- [ ] 手册内容根据任务类型自动选择模板
- [ ] 前端可以查看任务手册

### Week 3 完成标准
- [ ] 可以注册新的 Skill
- [ ] Agent 只能执行被授权的 Skills
- [ ] Skill 执行有完整日志

### Week 4 完成标准
- [ ] 任务分配时 Agent 实时收到通知
- [ ] Agent 回复时用户实时收到通知
- [ ] Agent 在线状态准确反映

---

## 附录

### A. 每日检查清单

```markdown
## Day X 检查清单

### 已完成
- [ ] 任务 1
- [ ] 任务 2

### 进行中
- [ ] 任务 3 (预计今天完成)

### 阻塞
- [ ] 任务 4 (原因: ...)

### 明日计划
1. ...
2. ...
```

### B. 快速启动命令

```bash
# 启动后端
cd backend && source venv/bin/activate && uvicorn src.main:app --reload

# 查看日志
tail -f /tmp/opc_backend.log

# 运行测试
cd backend && pytest tests/

# 数据库检查
cd backend && python3 -c "from src.database import init_db; init_db()"
```

### C. 相关文档

- [Agent 调用机制设计](AGENT_INVOCATION_DESIGN.md)
- [占位函数清单](PLACEHOLDER_FUNCTIONS.md)
- [任务聊天系统设计](TASK_CHAT_SYSTEM_DESIGN.md)

---

*文档版本: v1.0*  
*更新日期: 2026-03-23*  
*计划周期: 4 周*  
*预计工作量: 20 人天*
