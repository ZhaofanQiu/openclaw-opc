# OpenClaw OPC 测试反馈问题分析报告

## 问题汇总

### 1. 用户详情页中剩余预算显示0 OC币，实际是10000
**状态**: 需要进一步调查
**严重程度**: 高

**问题分析**:
- 后端 `Agent.remaining_budget` 是动态计算的属性：`monthly_budget - used_budget`
- `AgentResponse` 模型已包含 `total_budget` 和 `remaining_budget` 字段
- 问题可能出在前端显示逻辑或数据未正确返回

**可能原因**:
1. 前端 `agent-modal-budget` 元素赋值逻辑问题
2. API 返回数据中 `remaining_budget` 字段缺失或为 null
3. 数据类型问题（字符串 vs 数字）

**修复建议**:
```javascript
// 在 openAgentModal 函数中检查
console.log('Agent data:', agent);
document.getElementById('agent-modal-budget').textContent = formatNumber(agent.remaining_budget || 0) + ' OC币';
```

**验证方法**:
1. 打开浏览器开发者工具 (F12)
2. 查看 Network 面板中 `/api/agents/{id}` 的响应
3. 检查 `remaining_budget` 和 `total_budget` 字段值

---

### 2. 已经唤醒partner之后又很快显示需要点击唤醒
**状态**: 设计行为，但可优化
**严重程度**: 中

**问题分析**:
- Partner 有两个状态：
  - `is_online`: 基于心跳检测（60秒内收到心跳为 online）
  - `partnerState` (awake/standby): 用户交互状态，5分钟无交互自动进入 standby
- 问题原因是 `get_partner_state` API 在 300秒（5分钟）无交互后自动将状态改为 standby

**相关代码**:
```python
# backend/src/routers/agents.py:847
if state == "awake" and partner.last_heartbeat:
    delta = datetime.utcnow() - partner.last_heartbeat
    if delta.total_seconds() > 300:  # 5 minutes
        state = "standby"
```

**修复建议**:
1. 延长自动休眠时间至 30 分钟
2. 或添加配置项让用户自定义休眠时间
3. 前端显示更明确的状态提示（"Partner 在线但已进入待机模式"）

---

### 3. 给员工随机生成头像依旧显示失败
**状态**: 已修复（增强错误处理）
**严重程度**: 中

**问题分析**:
- `avatar_service.py` 中的 `regenerate_system_avatar` 方法在生成失败时抛出异常
- 原代码在导入 `Agent` 模型时使用了错误的导入路径：`from src.models import Agent`
- 正确的导入路径应该是：`from src.models.agent import Agent`

**已修复**:
```python
# 修复前
from src.models import Agent  # 错误

# 修复后  
from src.models.agent import Agent  # 正确
```

**还需要的修复**:
- 前端 `generateSystemAvatar` 函数应该添加更详细的错误提示

---

### 4. 点击分配任务，选择员工，点击确认之后要等待较长时间才会有分配成功，请增加读条
**状态**: 已修复
**严重程度**: 低

**已修复**:
- 在 `confirmAssign` 函数中添加了 loading 状态
- 分配按钮在请求期间显示"分配中..."并禁用

```javascript
// 修复后的代码
async function confirmAssign() {
    // ...
    confirmBtn.textContent = '分配中...';
    confirmBtn.disabled = true;
    
    try {
        // API 调用
    } finally {
        confirmBtn.textContent = originalText;
        confirmBtn.disabled = false;
    }
}
```

---

### 5. 分配完任务之后，任务状态显示1条任务已分配，而任务列表显示那一条任务是进行中
**状态**: 设计行为，但 UX 可优化
**严重程度**: 低

**问题分析**:
- 后端任务状态：`pending` -> `assigned` -> `completed`
- 前端显示映射：
  ```javascript
  const statusText = {
      'pending': '待分配',
      'assigned': '进行中',  // 这里将 assigned 显示为"进行中"
      'completed': '已完成',
      'fused': '已熔断'
  };
  ```
- 这不是 bug，而是 UX 设计：
  - "已分配" = 任务已分配给员工，但可能还未开始
  - "进行中" = 任务已发送给 Agent，Agent 可能正在处理

**执行状态细分** (v0.3.0 P0 新增):
- `sent`: 已发送给 Agent
- `acked`: Agent 已接收
- `running`: Agent 正在执行
- `completed`: 已完成

**修复建议**:
统一状态显示，或在 UI 上添加更详细的执行状态徽章。

---

### 6. 分配完任务之后点击悬浮框提示partner唤醒失败了，但页面显示partner在线
**状态**: 需要进一步调查
**严重程度**: 中

**问题分析**:
- Partner 有两种状态：
  1. **在线状态** (`is_online`): 基于心跳，表示 Partner Agent 进程在运行
  2. **唤醒状态** (`partnerState`): 表示 Partner 正在与用户交互

- "在线" ≠ "已唤醒"
- 唤醒失败可能原因：
  1. Partner ID 未正确加载（`PARTNER_ID` 为 null）
  2. `/api/agents/partner/wake` API 调用失败
  3. Partner 员工未绑定到 OpenClaw Agent

**需要检查**:
```javascript
// 浏览器控制台检查
console.log('PARTNER_ID:', PARTNER_ID);
```

**修复建议**:
1. 确保 Partner 员工正确创建并绑定到 OpenClaw Agent
2. 检查 `/api/agents/partner/wake` 的响应错误详情
3. 在 UI 上区分"在线"和"已唤醒"两种状态

---

### 7. 分配完任务之后显示实习生小刘正在工作中，它是否实际运行任务？
**状态**: 设计行为，需要用户理解架构
**严重程度**: 低（文档问题）

**架构说明**:

**任务执行流程**:
1. 用户在 Dashboard 分配任务给员工
2. OPC 后端通过 `sessions_send` 发送任务消息给绑定的 OpenClaw Agent
3. Agent 在 OpenClaw Gateway 中接收消息
4. Agent 实际执行任务（调用工具、处理数据等）
5. Agent 通过 `opc_report()` 回调报告任务完成

**关键概念**:
- OPC Dashboard 中的"工作中"状态只表示任务已分配并发送给 Agent
- 实际任务执行发生在 OpenClaw Gateway 进程中
- 用户需要在 OpenClaw 中查看 Agent 的实际执行状态

**可视化说明**:
```
┌─────────────────┐     分配任务      ┌──────────────────┐
│  OPC Dashboard  │ ────────────────> │  OPC Backend     │
│  (显示"工作中")  │                   │  (发送消息)      │
└─────────────────┘                   └────────┬─────────┘
                                               │
                                               │ sessions_send
                                               ▼
                                      ┌──────────────────┐
                                      │ OpenClaw Gateway │
                                      │ (Agent 实际执行)  │
                                      └──────────────────┘
```

**用户操作**:
1. 在 OPC Dashboard 分配任务
2. 切换到 OpenClaw 查看 Agent 会话
3. 观察 Agent 接收任务并执行
4. 等待 Agent 报告完成（或失败）

**建议**:
- 添加文档说明任务执行架构
- 在 Dashboard 添加链接，方便用户跳转到 OpenClaw 查看 Agent 执行状态

---

## 修复清单

| 问题 | 状态 | 修复文件 | 备注 |
|------|------|----------|------|
| 1. 预算显示0 | 待调查 | - | 需要查看实际 API 响应 |
| 2. Partner 快速休眠 | 设计行为 | - | 可配置休眠时间 |
| 3. 头像生成失败 | 已修复 | avatar_service.py | 修复导入路径 |
| 4. 分配任务无loading | 已修复 | index.html | 添加按钮 loading 状态 |
| 5. 任务状态显示不一致 | UX 设计 | - | 需要统一状态术语 |
| 6. Partner 唤醒失败 | 待调查 | - | 检查 Partner 绑定状态 |
| 7. 任务执行机制 | 文档 | - | 需要用户文档说明 |

## 下一步行动

1. **立即执行**:
   - [ ] 部署已修复的代码（头像生成、分配任务 loading）
   - [ ] 检查 Partner 是否正确绑定到 OpenClaw Agent

2. **需要用户配合**:
   - [ ] 提供问题1的浏览器 Network 面板截图
   - [ ] 提供问题6的浏览器 Console 错误日志

3. **文档改进**:
   - [ ] 编写任务执行架构说明文档
   - [ ] 添加 Partner 状态说明到用户手册
