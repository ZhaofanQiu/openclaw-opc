# OpenClaw OPC v0.4.3 员工界面修复报告

**修复日期**: 2026-03-26  
**Git Commit**: `3dee799`

---

## 🐛 修复的问题

### 1. 输入栏黑色字体辨识度太低 ✅

**问题**: 雇佣新员工页面的输入框没有明确设置文本颜色，在某些主题下难以辨认。

**修复**: 在 `EmployeeCreateModal.vue` 中为输入框和选择框添加明确的文本颜色：
```css
.form-group input, .form-group select {
  color: var(--text-primary, #333);
}
```

---

### 2. 职位选择应该是下拉栏 ✅

**问题**: 职位选择使用文本输入，但后端 API 实际期望的是 `position_level` (整数 1-5)。

**修复**: 改为下拉选择，映射到职位等级：

| 等级 | 职位名称 |
|------|----------|
| 1 | 实习生 |
| 2 | 专员 |
| 3 | 资深 |
| 4 | 专家 |
| 5 | 合伙人 |

**代码更改**:
- 前端表单字段从 `position_title` 改为 `position_level`
- 使用 `<select>` 下拉选择替代文本输入
- 添加了下拉选择器的样式

---

### 3. 绑定 Agent 500 错误 ✅

**问题原因**:
1. 前端使用模拟数据，而非从后端获取真实 Agent 列表
2. 后端绑定 API 调用 `openclaw` CLI 验证 Agent，CLI 不可用会导致 500 错误

**修复**:

**前端** (`AgentBindModal.vue`):
- 从真实 API `/employees/openclaw/available` 获取可用 Agent 列表
- 添加错误状态显示
- 改进错误提示信息

**后端** (`employees.py`):
- 添加 Agent 重复绑定检查
- 添加 `FileNotFoundError` 处理（CLI 不存在）
- 添加通用异常处理，避免 500 错误
- 支持通过环境变量 `OPC_ALLOW_FORCE_BIND=true` 在测试环境中强制绑定

---

## 📁 修改文件

```
packages/opc-ui/src/components/employees/EmployeeCreateModal.vue
packages/opc-ui/src/components/employees/AgentBindModal.vue
packages/opc-core/src/opc_core/api/employees.py
```

---

## 🚀 如何测试

1. 重新部署前端:
```bash
cd packages/opc-ui
npm run build
```

2. 重启后端服务

3. 测试员工创建:
   - 打开雇佣员工弹窗
   - 确认职位是下拉选择（实习生/专员/资深/专家/合伙人）
   - 输入框文字应清晰可见

4. 测试 Agent 绑定:
   - 创建员工后点击"绑定 Agent"
   - 应显示从 OpenClaw 配置读取的真实 Agent 列表
   - 如果 CLI 不可用，会显示友好错误提示

---

## ⚠️ 已知限制

- Agent 绑定仍需要 OpenClaw CLI 可用，或设置 `OPC_ALLOW_FORCE_BIND=true` 环境变量
- 如果 `~/.openclaw/openclaw.json` 中没有配置 Agent，列表将为空
