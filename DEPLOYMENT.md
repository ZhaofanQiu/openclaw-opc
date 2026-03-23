# OPC 部署指南

> 新用户如何部署 OpenClaw OPC 系统

---

## 📋 前置要求

1. **OpenClaw 已安装并运行**
   ```bash
   # 验证 OpenClaw
   openclaw --version
   openclaw gateway status
   ```

2. **Python 3.8+**
   ```bash
   python3 --version
   ```

3. **Git** (可选，用于克隆仓库)

---

## 🚀 快速部署

### 步骤 1: 克隆仓库

```bash
git clone https://github.com/your-org/openclaw-opc.git
cd openclaw-opc/backend/src
```

### 步骤 2: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 3: 安装 OPC Bridge Skill

```bash
# 方法1: 使用安装脚本
cd ../../skills/opc-bridge-v2
chmod +x install.sh
./install.sh

# 选择 1) From local repository
```

或者手动安装：

```bash
# 方法2: 手动复制
mkdir -p ~/.openclaw/skills
cp -r ../../skills/opc-bridge-v2 ~/.openclaw/skills/
chmod +x ~/.openclaw/skills/opc-bridge-v2/scripts/*.py
```

### 步骤 4: 启动 OPC 服务

```bash
cd backend/src
python3 -m uvicorn main_v2:app --host 0.0.0.0 --port 8080
```

验证服务：
```bash
curl http://localhost:8080/health
# 应返回: {"status":"ok","version":"2.0.0"}
```

### 步骤 5: 配置 Agent

编辑 `~/.openclaw/openclaw.json`，添加 OPC Agent：

```json
{
  "agents": {
    "list": [
      {
        "id": "opc_partner",
        "name": "OPC Partner Assistant",
        "workspace": "/root/.openclaw/agents/opc_partner/workspace",
        "agentDir": "/root/.openclaw/agents/opc_partner"
      }
    ]
  }
}
```

**重要**: 不要添加 `tools` 或 `skills` 字段！

重启 Gateway：
```bash
openclaw gateway restart
```

### 步骤 6: 初始化数据库

OPC 会自动创建 SQLite 数据库和初始数据。

访问 Dashboard：
```
http://localhost:8080/dashboard/
```

---

## ⚙️ 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPC_CORE_URL` | `http://localhost:8080` | OPC Core 服务地址 |
| `OPC_AGENT_ID` | 自动检测 | Agent ID |
| `DATABASE_URL` | `sqlite:///data/opc.db` | 数据库连接 |

### 回调地址配置

如果使用远程部署，需要更新回调脚本中的地址：

编辑 `~/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py`：

```python
# 修改默认地址为实际IP
OPC_CORE_URL = os.getenv("OPC_CORE_URL", "http://YOUR_SERVER_IP:8080")
```

---

## 🧪 验证部署

### 测试 1: Skill 安装

```bash
python3 ~/.openclaw/skills/opc-bridge-v2/scripts/opc-get-budget.py
```

### 测试 2: Agent 连接

```bash
openclaw agent --agent opc_partner --message "echo hello" --json
```

### 测试 3: 完整闭环

1. 访问 Dashboard: `http://localhost:8080/dashboard/`
2. 创建员工并绑定到 `opc_partner`
3. 分配任务
4. 验证任务完成和回调

---

## 🔧 故障排除

### 问题 1: Skill 未找到

**症状**: `No such file or directory: ~/.openclaw/skills/opc-bridge-v2/`

**解决**:
```bash
# 重新安装 skill
cp -r /path/to/openclaw-opc/skills/opc-bridge-v2 ~/.openclaw/skills/
chmod +x ~/.openclaw/skills/opc-bridge-v2/scripts/*.py
```

### 问题 2: 回调失败 Connection refused

**症状**: Agent 报告回调连接失败

**解决**:
1. 确保 OPC 服务在 `0.0.0.0:8080` 监听
2. 更新回调脚本中的 `OPC_CORE_URL` 为实际IP
3. 检查防火墙设置

### 问题 3: Agent 无法执行命令

**症状**: Agent 说没有工具权限

**解决**: 检查 Agent 配置，确保没有 `tools.allow` 字段限制权限

---

## 📁 目录结构

部署后的目录结构：

```
~/.openclaw/
├── openclaw.json          # OpenClaw 配置
├── agents/
│   └── opc_partner/       # Agent 工作空间
│       ├── workspace/
│       └── agent/
└── skills/
    └── opc-bridge-v2/     # OPC Bridge Skill ← 关键
        ├── SKILL.md
        ├── install.sh
        └── scripts/
            ├── opc-report.py
            ├── opc-check-task.py
            └── opc-get-budget.py

openclaw-opc/
├── backend/
│   └── src/
│       ├── main_v2.py     # OPC 服务入口
│       ├── core/          # 核心业务逻辑
│       └── ...
└── skills/
    └── opc-bridge-v2/     # Skill 源代码
```

---

## 📝 更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-03-23 | 修复 skill 目录结构，添加 v2 版本 |

---

**相关文档**:
- `docs/AGENT_INTERACTION_BEST_PRACTICES.md` - Agent 交互最佳实践
- `docs/AGENT_CONFIG_NOTES.md` - Agent 配置指南
- `skills/opc-bridge-v2/SKILL.md` - Skill 使用说明
