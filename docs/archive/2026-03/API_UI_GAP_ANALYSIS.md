# OpenClaw OPC - 前后端功能对照表

## 后端API端点清单

### ✅ 前端已实现的功能

| 模块 | API端点 | 前端功能 |
|------|---------|----------|
| **Agents** | GET /api/agents | 员工列表展示 |
| **Agents** | POST /api/agents/auto-create | 自动创建Agent（绑定模态框） |
| **Agents** | GET /api/agents/binding/available | 获取可绑定Agent列表 |
| **Agents** | POST /api/agents/binding/bind | 绑定Agent到员工 |
| **Agents** | GET /api/agents/partner/health | Partner健康状态检查 |
| **Avatars** | GET/POST /api/avatars/{id} | 头像生成、上传、更换 |
| **Budget** | GET /api/budget/company | 公司预算统计卡片 |
| **Budget** | GET /api/budget/comparison | Token精确追踪对比 |
| **Config** | GET/PATCH /api/config | 系统配置面板 |
| **Fuse** | GET /api/fuse/events | 熔断事件列表 |
| **Fuse** | GET /api/fuse/events/pending | 待处理熔断警报 |
| **Monitor** | POST /api/monitor/check | 检查逾期任务 |
| **Monitor** | GET /api/monitor/overdue | 逾期任务列表 |
| **Notifications** | GET /api/notifications | 通知列表（右上角铃铛） |
| **Reports** | GET /api/reports/recent | 7天预算趋势图表 |
| **Share** | POST /api/share/generate | 生成分享链接 |
| **Tasks** | GET /api/tasks | 任务列表展示 |
| **Tasks** | POST /api/tasks | ✅ 新建任务（刚刚添加） |
| **Tasks** | POST /api/tasks/{id}/assign | 手动分配任务按钮 |

---

## ❌ 前端缺失的功能（仅后端API支持）

### 1. API Key管理 (`/api/keys/*`)
**后端端点：**
- GET /api/keys - 列出所有API Key
- POST /api/keys - 创建新API Key
- GET /api/keys/{id} - 获取Key详情
- POST /api/keys/{id}/revoke - 撤销Key
- POST /api/keys/{id}/rotate - 轮转Key
- GET /api/keys/stats - Key使用统计

**前端缺失：** 完整的API Key管理界面

---

### 2. 消息通信中心 (`/api/communication/*`)
**后端端点：**
- POST /api/communication/send - 发送消息
- POST /api/communication/broadcast - 广播消息
- GET /api/communication/inbox/{agent_id} - 查看收件箱
- GET /api/conversation/{agent1_id}/{agent2_id} - 查看对话记录
- POST /api/communication/messages/{id}/deliver - 标记消息已送达

**前端缺失：** 消息发送/收件箱界面

---

### 3. 技能管理 (`/api/skills/*`)
**后端端点：**
- GET /api/skills - 列出所有技能
- POST /api/skills - 创建技能
- GET /api/skills/{id} - 获取技能详情
- PATCH /api/skills/{id} - 更新技能
- DELETE /api/skills/{id} - 删除技能

**前端缺失：** 技能库管理界面

---

### 4. 交易记录 (`/api/budget/transactions`)
**后端端点：**
- GET /api/budget/transactions - 交易记录列表
- POST /api/budget/exact-consumption - 记录精确Token消耗

**前端缺失：** 详细的交易记录查看页面

---

### 5. Partner任务分配 (`/api/agents/partner/*`)
**后端端点：**
- POST /api/agents/partner/assign/{task_id} - Partner分配任务
- POST /api/agents/partner/assign-all - 批量分配任务
- POST /api/agents/partner/hire - Partner雇佣员工

**前端缺失：** Partner专属操作界面

---

### 6. 熔断解决操作 (`/api/fuse/events/{id}/resolve/*`)
**后端端点：**
- POST /api/fuse/events/{id}/resolve/add-budget - 追加预算解决
- POST /api/fuse/events/{id}/resolve/split-task - 拆分任务解决
- POST /api/fuse/events/{id}/resolve/reassign - 重新分配解决
- POST /api/fuse/events/{id}/resolve/pause - 暂停解决

**前端缺失：** 熔断事件解决操作（有按钮但可能未完全对接）

---

### 7. 报告详情 (`/api/reports/*`)
**后端端点：**
- GET /api/reports/summary - 报告摘要
- GET /api/reports/daily - 日报
- GET /api/reports/weekly - 周报

**前端缺失：** 详细报告页面（reports.html部分实现）

---

### 8. 任务技能要求 (`/api/tasks/{id}/requirements`)
**后端端点：**
- GET /api/tasks/{task_id}/requirements - 获取任务技能要求
- POST /api/tasks/{task_id}/requirements - 设置任务技能要求
- GET /api/skills/match/{task_id}/{agent_id} - 匹配度检查
- GET /api/skills/match/{task_id}/best - 最佳匹配员工

**前端缺失：** 任务技能要求展示和匹配度显示

---

## 修复建议优先级

### P0 - 高优先级（核心功能缺失）
1. **深色主题修复** - 表单元素样式统一
2. **交易记录页面** - 查看预算使用明细

### P1 - 中优先级（功能完善）
3. **API Key管理界面** - 系统管理员需要
4. **消息通信中心** - Agent间协作
5. **熔断解决操作完整对接** - 修复现有按钮

### P2 - 低优先级（增强功能）
6. **技能管理界面** - 技能库管理
7. **Partner操作界面** - Partner专属功能
8. **任务技能匹配显示** - 增强任务分配
