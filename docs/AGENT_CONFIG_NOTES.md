# Agent 配置注意事项

> **核心结论**: Agent 配置不需要 `tools` 和 `skills` 字段！
>
> **经验来源**: 2026-03-23 闭环测试实践
>
> **相关文档**: `AGENT_INTERACTION_BEST_PRACTICES.md`

---

## ⚠️ 重要结论

### 错误示例 ❌

```json
{
  "id": "实习生小刘-e8bc",
  "name": "实习生小刘",
  "workspace": "/root/.openclaw/workspace-xxx",
  "agentDir": "/root/.openclaw/agents/xxx",
  "tools": {
    "allow": ["group:fs", "opc-bridge"]
  },
  "skills": ["opc-bridge"]
}
```

**问题**:
- `tools.allow` 会**限制** Agent 只能使用列出的工具
- 导致 `exec`, `web_search` 等重要工具不可用
- `skills` 字段在 agent 配置中无效

### 正确示例 ✅

```json
{
  "id": "opc_partner",
  "name": "OPC Partner Assistant",
  "workspace": "/root/.openclaw/agents/opc_partner/agent/workspace",
  "agentDir": "/root/.openclaw/agents/opc_partner/agent"
}
```

**优点**:
- 使用 OpenClaw 默认完整工具集
- Agent 拥有所有必要工具权限
- 配置简洁清晰

---

## 为什么不需要这些字段？

### 1. OpenClaw 默认提供完整工具集

默认工具包括：
- **文件**: `read`, `write`, `edit`
- **Shell**: `exec`, `process`
- **Web**: `web_search`, `web_fetch`, `browser`
- **会话**: `sessions_list`, `sessions_send`, `sessions_spawn`
- **其他**: `message`, `cron`, `memory_search`

### 2. Skill 通过文件系统提供

```
~/.openclaw/skills/
├── opc-bridge-v2/
│   ├── SKILL.md           # Skill 定义文档
│   └── scripts/
│       └── opc-report.py  # 可执行脚本
```

Agent 通过 `read` 工具读取 SKILL.md 获取能力指导，不需要在配置中注册。

### 3. 添加这些字段反而可能限制能力

| 配置 | `exec` 可用 | `web_search` 可用 | 结果 |
|------|-------------|-------------------|------|
| 无额外字段 | ✅ | ✅ | 正常 |
| `tools.allow: ["group:fs"]` | ❌ | ❌ | 受限 |
| `tools.allow: ["exec"]` | ✅ | ❌ | 部分受限 |

---

## 正确的 Skill 使用方式

### 1. 确保 Skill 已安装

```bash
# 检查 skill 是否存在
ls ~/.openclaw/skills/opc-bridge-v2/

# 如果不存在，安装 skill
cd /root/.openclaw/workspace/openclaw-opc/backend/src
python3 -m core.skill_installer
```

### 2. 在任务消息中告知 Agent 使用 Skill

```markdown
# 任务分配

## 任务信息
- 任务ID: task_xxx
- 标题: 测试任务

## 执行步骤

1. **读取 opc-bridge skill 手册**：
   路径：`~/.openclaw/skills/opc-bridge-v2/SKILL.md`

2. **理解手册内容**：
   手册中包含回调脚本的用法说明

3. **完成任务后报告结果**：
   执行：`python3 ~/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py 
          task_xxx 50 "任务完成结果"`
```

### 3. Agent 实际执行流程

```
Agent 收到任务消息
    ↓
使用 read 工具读取 SKILL.md
    ↓
理解 skill 提供的功能
    ↓
使用 exec 执行具体任务
    ↓
使用 exec 执行回调脚本
    ↓
报告任务完成
```

---

## 验证 Agent 配置

### 测试 1: 基本命令执行

```bash
openclaw agent --agent opc_partner \
  --message "执行命令：echo '配置正确'" \
  --json 2>&1 | tail -20
```

**期望输出**: Agent 返回 `配置正确`

### 测试 2: Skill 手册读取

```bash
openclaw agent --agent opc_partner \
  --message "读取文件：~/.openclaw/skills/opc-bridge-v2/SKILL.md" \
  --json 2>&1 | grep -A5 "opc-report"
```

**期望输出**: 包含 `opc-report.py` 相关说明

### 测试 3: 回调脚本执行

```bash
# 确保 OPC 服务运行中
curl http://localhost:8080/health

# 测试回调脚本
python3 ~/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py \
  task_test 50 "配置测试"
```

**期望输出**: `{"success": true, ...}`

---

## 配置参考

### 最小可用配置

```json
{
  "agents": {
    "list": [
      {
        "id": "my_agent",
        "name": "My Agent",
        "workspace": "/path/to/workspace",
        "agentDir": "/path/to/agent"
      }
    ]
  }
}
```

### 全局工具配置（可选，一般不需要）

```json
{
  "tools": {
    "profile": "full"
  }
}
```

可选 profile:
- `full` - 完整工具集（默认，推荐）
- `coding` - 编码工具集
- `messaging` - 消息工具集

**注意**: 除非有特殊安全需求，否则保持默认 `full` 配置。

---

## 常见问题

### Q: 如何确认我的 Agent 配置正确？

A: 运行上述三个验证测试，全部通过即配置正确。

### Q: 如果我已经添加了 `tools` 字段怎么办？

A: 直接删除该字段，重启 OpenClaw Gateway 即可。

### Q: Agent 可以访问所有工具，会不会有安全风险？

A: Agent 运行在受控环境中，且所有操作都有日志记录。如需限制，可通过 OPC 的预算系统控制成本。

### Q: 为什么我的 Agent 无法执行回调脚本？

A: 检查以下几点：
1. Agent 是否有 `exec` 权限（配置是否正确）
2. 回调脚本路径是否正确
3. OPC 服务地址是否正确（参见 `AGENT_INTERACTION_BEST_PRACTICES.md`）

---

**记录时间**: 2026-03-23  
**最后更新**: 闭环测试成功后  
**相关文档**: 
- `AGENT_INTERACTION_BEST_PRACTICES.md` - Agent 交互最佳实践
- `ARCHITECTURE_v2.md` - 系统架构设计
