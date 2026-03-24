# Phase 2: OpenClaw 层详细规划

**版本**: v0.4.1  
**目标**: 封装 OpenClaw 交互，提供 Agent 调用与管理能力  
**核心原则**: 主动对话、Skill 约束、手册先行、纯文本通信

---

## 一、设计约束确认

### 1.1 硬性约束（必须遵守）

| # | 约束 | 实现方式 |
|---|------|----------|
| 1 | **Skill 规范行为** | 通过 `opc-bridge` Skill（**无版本号**）安装在 OpenClaw 中 |
| 2 | **Skill 使用方式** | 消息中指定使用 opc-bridge skill，Agent 可直接调用 skill 函数 |
| 3 | **主动对话模式** | 使用 `sessions_spawn` 发送消息并等待回复，**禁止**使用 Cron 或心跳让 Agent 自行运行 |
| 4 | **手册先行** | 任务消息中明确引导 Agent 先读取手册（**使用绝对路径**） |
| 5 | **结果文件列表** | 任务报告时通过 `result_files` 参数传递结果文件路径列表 |
| 6 | **纯文本通信** | 通过 OpenClaw CLI (`openclaw agent --message "..."`) 发送纯文本消息 |
| 7 | **Config 管理 Agent** | Agent 列表通过读取 `~/.openclaw/config` 获取，增删通过修改 Config 实现 |
| 8 | **Agent 命名规范** | 所有可读取/创建的 Agent ID 必须以 `opc_` 开头 |
| 9 | **Gateway 重启确认** | 修改 Config 后重启 OpenClaw Gateway 需要**用户确认** |
| 10 | **手册路径格式** | 使用**绝对路径**，防止 Agent 找不到文件 |
| 11 | **任务超时** | 默认 **15 分钟 (900 秒)**，可配置 |

### 1.2 模块边界

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenClaw Layer                          │
│                   (packages/opc-openclaw)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Client     │  │  Interaction │  │    Skill     │       │
│  │   客户端      │  │    交互层     │  │   Skill定义  │       │
│  │              │  │              │  │   + 脚本     │       │
│  │ - Base       │  │ - Messenger  │  │              │       │
│  │ - Sessions   │  │ - TaskCaller │  │ - SKILL.md   │       │
│  │ - Agents     │  │ - ConfigMgr  │  │ - 报告脚本    │       │
│  │              │  │              │  │ - 检查脚本    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘                │
│                           │                                  │
│                    ┌──────────────┐                          │
│                    │  AgentManager │  ← 对外暴露的接口         │
│                    │   管理层      │                          │
│                    └──────────────┘                          │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │   OpenClaw     │
                    │   Gateway      │
                    └────────────────┘
```

---

## 二、当前代码状态（✅ 已修复）

### 2.1 修复内容（2026-03-24）

**核心问题**: Messenger 使用 HTTP API 而非 CLI  
**修复方案**: 全面改为 CLI 方式

| 变更 | 原实现 | 新实现 |
|------|--------|--------|
| Messenger | `httpx.post("/api/sessions/spawn")` | `subprocess.run(["openclaw", "agent", ...])` |
| AgentClient | `httpx.get("/api/agents")` | `subprocess.run(["openclaw", "agents", "list"])` |
| SessionClient | HTTP API 客户端 | **已删除** |
| BaseClient | HTTP 基础类 | **已删除** |
| OpenClawAPIError | HTTP 异常 | **已删除** |

### 2.2 当前文件结构

```
packages/opc-openclaw/src/opc_openclaw/
├── __init__.py              # ✅ 更新导出
├── client/
│   ├── __init__.py          # ✅ CLIAgentClient
│   └── agents.py            # ✅ CLI 方式获取 Agent 列表
├── agent/
│   ├── __init__.py          # ✅ 导出 AgentState
│   ├── manager.py           # ✅ 使用 CLIAgentClient
│   ├── lifecycle.py         # ✅ 添加 opc_ 命名规范验证
│   └── binding.py           # ✅ 保留
├── interaction/
│   ├── __init__.py          # ✅ CLIMessenger
│   └── messenger.py         # ✅ CLI 消息发送
└── skill/
    ├── __init__.py
    ├── definition.py        # ✅ name=opc-bridge
    └── installer.py         # ⭐ 待开发
```

### 2.3 已完成功能

- ✅ `CLIMessenger.send()` - 通过 CLI 发送消息
- ✅ `CLIAgentClient.list_agents()` - 通过 CLI 获取 Agent 列表
- ✅ Agent 命名规范验证（opc_ 开头）
- ✅ 过滤 main/default Agent

### 2.4 待开发功能

| 模块 | 文件 | 功能 | 优先级 | 状态 |
|------|------|------|--------|------|
| Config | `config/manager.py` | 读取/修改 ~/.openclaw/config | P0 | ✅ 已实现 |
| Task | `interaction/task_caller.py` | 任务调用封装 | P0 | ✅ 已实现 |
| Skill | `skill/installer.py` | 安装 opc-bridge skill | P0 | ✅ 已实现 |
| Skill | `skill/scripts/*.py` | 报告/检查/预算脚本 | P0 | ✅ 已实现 |
| Tests | `tests/unit/` | 单元测试 | P1 | ✅ 98 个通过 |
| Docs | `README.md`, `API.md` | 文档更新 | P1 | ✅ 已完成 |

---

## 三、核心接口设计

### 3.1 对外接口（Core 层调用）

```python
# packages/opc-openclaw/src/opc_openclaw/__init__.py

from .agent.manager import AgentManager
from .interaction.task_caller import TaskCaller, TaskAssignment, TaskResponse

__all__ = ["AgentManager", "TaskCaller", "TaskAssignment", "TaskResponse"]
```

### 3.2 AgentManager

```python
class AgentManager:
    """
    OpenClaw Agent 管理器
    
    提供 Agent 发现、验证、绑定的管理能力
    """
    
    async def list_agents(self) -> List[AgentInfo]:
        """
        获取所有可用 Agent 列表
        
        实现：读取 ~/.openclaw/config 文件，解析 agents 配置
        """
        pass
    
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """获取指定 Agent 信息"""
        pass
    
    async def validate_agent(self, agent_id: str) -> bool:
        """
        验证 Agent 是否可用
        
        注意：禁止使用 "main" 或 "default" 进行验证
        """
        pass
    
    async def install_skill(self, agent_id: str) -> bool:
        """
        为 Agent 安装 opc-bridge-v2 Skill
        
        将 Skill 安装到 ~/.openclaw/skills/opc-bridge-v2/
        """
        pass
```

### 3.3 TaskCaller（核心）

```python
@dataclass
class TaskAssignment:
    """任务分配信息"""
    task_id: str
    title: str
    description: str
    agent_id: str                    # OpenClaw Agent ID（必须以 opc_ 开头）
    agent_name: str                  # 员工名称（用于消息）
    employee_id: str                 # OPC 员工ID
    company_manual_path: str         # 公司手册路径
    employee_manual_path: str        # 员工手册路径
    task_manual_path: str            # 任务手册路径
    timeout: int = 900               # 超时时间（秒），默认 15 分钟


@dataclass
class TaskResponse:
    """任务响应"""
    success: bool
    session_key: Optional[str]       # 会话标识，用于后续跟踪
    content: str                     # Agent 回复内容
    tokens_input: int
    tokens_output: int
    error: Optional[str] = None


class TaskCaller:
    """
    任务调用器
    
    封装与 Agent 的任务分配交互
    通过纯文本消息发送任务，引导 Agent 读取手册后执行
    """
    
    async def assign_task(self, assignment: TaskAssignment) -> TaskResponse:
        """
        分配任务给 Agent
        
        消息格式（纯文本）：
        ---
        # 任务分配: {title}
        
        你是 {agent_name}，是 OpenClaw OPC 的一名员工。
        
        ## 📚 执行前必须阅读以下手册
        
        1. **公司手册**: {company_manual_path}
        2. **员工手册**: {employee_manual_path}
        3. **任务手册**: {task_manual_path}
        
        请按顺序阅读，理解你的职责和任务要求。
        
        ## 📝 任务信息
        
        - **任务ID**: {task_id}
        - **标题**: {title}
        - **描述**: {description}
        
        ## ⚠️ 关键要求
        
        1. **先读手册，再执行任务**
        2. **任务完成后，必须报告结果**：
        
        ```bash
        python3 ~/.openclaw/skills/opc-bridge-v2/scripts/opc-report.py \
            {task_id} \
            <实际token消耗> \
            "任务完成总结" \
            --files <结果文件1> <结果文件2> ...
        ```
        
        3. **结果文件**: 将工作成果保存到文件，通过 --files 参数传递路径
        
        立即开始：先阅读手册，然后执行任务！
        ---
        """
        pass
    
    async def check_response(self, session_key: str) -> TaskResponse:
        """检查任务响应（用于异步模式）"""
        pass
```

### 3.4 ConfigManager

```python
class ConfigManager:
    """
    OpenClaw Config 管理器
    
    管理 ~/.openclaw/config 文件的读取和修改
    """
    
    CONFIG_PATH = "~/.openclaw/config"
    AGENT_ID_PREFIX = "opc_"  # Agent ID 必须以此前缀开头
    
    def read_agents(self) -> List[AgentConfig]:
        """
        读取所有 Agent 配置
        
        返回规则：
        1. 必须以 "opc_" 开头
        2. 排除 "main" 和 "default"
        """
        pass
    
    def validate_agent_id(self, agent_id: str) -> bool:
        """
        验证 Agent ID 是否符合命名规范
        
        规则：
        1. 必须以 "opc_" 开头
        2. 不能是 "main" 或 "default"
        3. 只能包含字母、数字、下划线、连字符
        """
        pass
    
    def add_agent(self, agent_id: str, model: str, **kwargs) -> tuple[bool, str]:
        """
        添加新 Agent 到配置
        
        Args:
            agent_id: Agent ID（必须以 opc_ 开头）
            model: 模型名称
            
        Returns:
            (success: bool, message: str)
            message 包含是否需要重启的提示
            
        ⚠️ 修改后需要重启 OpenClaw Gateway 才能生效
        ⚠️ 重启前会请求用户确认
        """
        pass
    
    def remove_agent(self, agent_id: str) -> tuple[bool, str]:
        """
        从配置中移除 Agent
        
        Returns:
            (success: bool, message: str)
            
        ⚠️ 修改后需要重启 OpenClaw Gateway 才能生效
        ⚠️ 重启前会请求用户确认
        """
        pass
    
    def request_restart_gateway(self) -> tuple[bool, str]:
        """
        请求重启 OpenClaw Gateway
        
        ⚠️ 重要：重启会中断所有正在进行的对话！
        
        流程：
        1. 检查是否有活跃的会话
        2. 向用户展示确认提示
        3. 用户确认后才执行重启
        
        Returns:
            (success: bool, message: str)
        """
        pass
    
    async def restart_gateway(self, force: bool = False) -> bool:
        """
        重启 OpenClaw Gateway
        
        Args:
            force: 是否跳过确认（仅用于自动化脚本）
        
        ⚠️ 默认情况下需要用户确认！
        """
        pass
```

---

## 四、Skill 设计

### 4.1 Skill 目录结构

安装到 `~/.openclaw/skills/opc-bridge-v2/`：

```
opc-bridge/
├── SKILL.md              # Skill 说明文档（Agent 可见）
└── scripts/
    ├── opc-report.py     # 任务报告脚本
    ├── opc-check-task.py # 检查当前任务
    └── opc-get-budget.py # 查询预算
```

### 4.2 SKILL.md 内容

```markdown
---
name: opc-bridge
description: OPC (One-Person Company) 员工基础能力
version: 1.0.0
---

# OPC Bridge

你是 OpenClaw OPC 的一名员工。

## 核心能力

### 1. opc_get_current_task()

检查当前分配给你的任务。

**示例**:
```
请使用 opc-bridge skill 的 opc_get_current_task() 查看当前任务
```

### 2. opc_report_task(task_id, tokens_used, result_summary, result_files)

**最重要：任务完成后必须调用！**

报告任务完成到 OPC 系统。

参数：
- `task_id`: 任务ID
- `tokens_used`: 实际消耗的 Token 数
- `result_summary`: 任务完成总结
- `result_files`: 结果文件路径列表（可选）

**示例**:
```
请使用 opc-bridge skill 的 opc_report_task(
    "task_abc123",
    500,
    "代码审查完成，发现3个问题",
    ["/home/user/results/report.md", "/home/user/results/issues.json"]
)
```

### 3. opc_get_budget()

查询你的预算状态。

**示例**:
```
请使用 opc-bridge skill 的 opc_get_budget() 查看预算
```

## 执行规范

1. **收到任务后**：先阅读任务中指定的手册（**使用绝对路径**）
2. **执行任务**：高效使用 Token 预算
3. **报告结果**：完成后立即调用 opc_report_task
4. **结果文件**：工作成果保存为文件，通过 result_files 传递**绝对路径**
```

### 4.3 报告脚本 opc-report.py

```python
#!/usr/bin/env python3
"""
报告任务完成到 OPC

用法: python3 opc-report.py <task_id> <token_used> <result_summary> [--files <path1> <path2> ...]
"""

import sys
import os
import json
import urllib.request
import argparse

OPC_CORE_URL = os.getenv("OPC_CORE_URL", "http://localhost:8000")

def report_task(task_id: str, token_used: int, result_summary: str, result_files: list):
    """报告任务完成"""
    
    url = f"{OPC_CORE_URL}/api/skill/tasks/{task_id}/report"
    data = {
        "agent_id": os.getenv("OPC_AGENT_ID", "unknown"),
        "result": result_summary,
        "tokens_used": token_used,
        "result_files": result_files
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result.get("success", False)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Report OPC task completion")
    parser.add_argument("task_id", help="Task ID")
    parser.add_argument("token_used", type=int, help="Token consumption")
    parser.add_argument("result_summary", help="Result summary")
    parser.add_argument("--files", nargs="*", default=[], help="Result file paths")
    
    args = parser.parse_args()
    
    success = report_task(args.task_id, args.token_used, args.result_summary, args.files)
    sys.exit(0 if success else 1)
```

---

## 五、开发步骤

### Step 1: ConfigManager（第 1 天）

**目标**: 实现 Config 文件读写

**任务**:
1. 实现 `read_agents()` - 读取并解析 YAML，**只返回 opc_ 开头的 Agent**
2. 实现 `validate_agent_id()` - 验证命名规范（opc_ 开头，非 main/default）
3. 实现 `add_agent()` / `remove_agent()` - 返回 (success, message) 元组
4. 实现 `request_restart_gateway()` - **请求用户确认**后重启
5. 实现 `restart_gateway()` - 默认需要确认，force=True 时跳过
6. **测试**: 单元测试覆盖所有方法

**约束检查**:
- ✅ 只读取 opc_ 开头的 Agent
- ✅ 排除 "main" 和 "default" Agent
- ✅ 修改后提示需要重启
- ✅ **重启前必须用户确认**

### Step 2: Skill 安装器（第 1-2 天）

**目标**: Skill 定义和安装脚本

**任务**:
1. 编写 `SKILL.md` 完整内容
2. 编写 `opc-report.py` 脚本（支持 `--files` 参数）
3. 编写 `opc-check-task.py` 和 `opc-get-budget.py`
4. 实现 `SkillInstaller` - 安装 Skill 到 `~/.openclaw/skills/`
5. **测试**: 验证脚本可以独立运行

**约束检查**:
- ✅ Skill 提供手册读取指引
- ✅ 报告脚本支持结果文件列表

### Step 3: Messenger（第 2 天）

**目标**: 纯文本消息发送

**任务**:
1. 实现 `Messenger.send()` - 调用 `openclaw agent --message`
2. 实现响应解析（提取 text、tokens）
3. **测试**: Mock CLI 调用，验证消息格式

**约束检查**:
- ✅ 使用纯文本消息
- ✅ 通过 CLI 发送

### Step 4: TaskCaller（第 3 天）

**目标**: 任务调用封装

**任务**:
1. 实现 `assign_task()` - 构建完整消息
2. 消息包含：手册路径、任务信息、报告指引
3. 实现 `check_response()` - 异步检查
4. **测试**: 验证消息格式符合约束

**约束检查**:
- ✅ 消息引导 Agent 先读手册
- ✅ 明确说明如何报告结果
- ✅ 说明结果文件传递方式

### Step 5: AgentManager 整合（第 4 天）

**目标**: 对外统一接口

**任务**:
1. 整合所有组件到 `AgentManager`
2. 实现 `list_agents()` - **只返回 opc_ 开头的 Agent**，过滤 main/default
3. 实现 `validate_agent()` - 检查命名规范 + 健康检查
4. 实现 `install_skill()` - 为 Agent 安装 Skill
5. **测试**: 35 个单元测试通过

**约束检查**:
- ✅ 只处理 opc_ 开头的 Agent
- ✅ 排除 "main" 和 "default"
- ✅ Gateway 重启需要确认

### Step 6: 集成验证（第 5 天）

**目标**: 与 Core 层联调

**任务**:
1. 编写集成测试脚本
2. 使用测试 Agent（非 main/default）验证完整流程
3. 验证：消息发送 → Agent 收到 → 模拟回调
4. **约束检查**: 全流程符合 7 条约束

---

## 六、测试策略

### 6.1 单元测试（35 个）

```python
# tests/unit/test_config_manager.py
test_read_agents_excludes_main_and_default
test_add_agent_updates_config
test_remove_agent_updates_config
test_restart_gateway_calls_cli

# tests/unit/test_messenger.py
test_send_message_calls_cli
test_send_message_parses_response
test_send_message_handles_error
test_send_message_extracts_tokens

# tests/unit/test_task_caller.py
test_assign_task_builds_correct_message
test_assign_task_includes_manual_paths
test_assign_task_includes_report_instructions
test_assign_task_returns_session_key

# tests/unit/test_skill.py
test_skill_installer_creates_files
test_opc_report_script_exists
test_opc_report_script_accepts_files_arg
test_skill_definition_contains_required_methods

# ... 共 35 个
```

### 6.2 Mock 实现

```python
# tests/mock/openclaw_cli.py

class MockOpenClawCLI:
    """模拟 OpenClaw CLI 行为"""
    
    def run(self, args: List[str]) -> str:
        """模拟 CLI 调用"""
        if "agent" in args and "--message" in args:
            return self._mock_agent_response(args)
        elif "gateway" in args and "restart" in args:
            return '{"status": "ok"}'
        # ...
```

---

## 七、接口契约

### 7.1 与 Core 层的数据契约

```python
# Core 层传入
class TaskAssignmentRequest:
    task_id: str
    title: str
    description: str
    employee_id: str
    openclaw_agent_id: str
    company_manual: str      # 公司手册内容或路径
    employee_manual: str     # 员工手册内容或路径
    task_manual: str         # 任务手册内容或路径

# OpenClaw 层返回
class TaskAssignmentResult:
    success: bool
    session_key: Optional[str]
    response_text: str       # Agent 的即时回复
    tokens_used: int
    error: Optional[str]
```

### 7.2 与 Agent 的消息契约

```
消息格式（纯文本）：

# 任务分配: {title}

你是 {agent_name}，是 OpenClaw OPC 的一名员工。

## 📚 执行前必须阅读以下手册（使用绝对路径）

请先阅读以下手册文件：
1. 公司手册: {company_manual_absolute_path}
2. 员工手册: {employee_manual_absolute_path}
3. 任务手册: {task_manual_absolute_path}

## 📝 任务信息

- **任务ID**: {task_id}
- **标题**: {title}
- **描述**: {description}

## ⚠️ 关键要求

1. **先读手册，再执行任务**（使用上述绝对路径）
2. **使用 opc-bridge skill 报告结果**：

   任务完成后，请使用 opc-bridge skill 的 opc_report_task() 函数报告：
   
   ```
   请使用 opc-bridge skill 的 opc_report_task(
       "{task_id}",
       <实际token消耗>,
       "任务完成总结",
       [<结果文件1的绝对路径>, <结果文件2的绝对路径>, ...]
   )
   ```

3. **结果文件**: 将工作成果保存到文件，使用绝对路径

立即开始：先阅读手册，然后执行任务！
```

### 7.3 Skill API 回调契约

```python
# Agent 通过 Skill 脚本调用
POST /api/skill/tasks/{task_id}/report
{
    "agent_id": "openclaw_agent_id",
    "result": "任务完成总结",
    "tokens_used": 500,
    "result_files": ["./results/file1.md", "./results/file2.json"]
}
```

---

## 八、风险提示

| 风险 | 可能性 | 影响 | 应对 |
|------|--------|------|------|
| OpenClaw CLI 变更 | 低 | 高 | 封装 CLI 调用，统一入口 |
| Config 格式变更 | 低 | 中 | 使用 YAML 解析，预留字段 |
| Agent 不执行报告脚本 | 中 | 高 | 消息中强调必须执行，提供示例 |
| Skill 安装失败 | 低 | 中 | 安装前检查目录权限，提供手动安装指引 |
| Gateway 重启失败 | 低 | 高 | 修改 Config 前备份，提供恢复脚本 |

---

## 九、验收标准

### 9.1 功能验收

- [ ] `AgentManager.list_agents()` **只返回 opc_ 开头的 Agent**，不含 main/default
- [ ] `ConfigManager.validate_agent_id()` 正确验证命名规范
- [ ] `ConfigManager.add_agent()` 拒绝非 opc_ 开头的 Agent ID
- [ ] `ConfigManager.request_restart_gateway()` **请求用户确认**后才重启
- [ ] `ConfigManager.restart_gateway()` 默认需要确认，force=True 可跳过
- [ ] `TaskCaller.assign_task()` 超时默认为 **900 秒（15 分钟）**
- [ ] `TaskCaller.assign_task()` 发送的消息包含**手册绝对路径**
- [ ] `TaskCaller.assign_task()` 消息包含 **opc-bridge skill 函数调用指引**（非 Python 代码路径）
- [ ] `TaskCaller.assign_task()` 消息包含报告脚本调用示例
- [ ] `opc-report.py` 支持 `--files` 参数传递结果文件
- [ ] Skill 安装后 Agent 可以通过脚本调用 OPC API

### 9.2 测试验收

- [ ] 35 个单元测试全部通过
- [ ] Mock 测试覆盖正常和异常场景
- [ ] 集成测试验证完整流程
- [ ] 使用 **opc_test_xxx** 命名的测试 Agent 验证（非 main/default）

### 9.3 约束验收

- [ ] ✅ 通过 Skill 规范 Agent 行为（**opc-bridge**，无版本号）
- [ ] ✅ 消息中使用 **opc-bridge skill 函数**（非 Python 代码路径）
- [ ] ✅ 主动对话模式（sessions_spawn）
- [ ] ✅ 手册先行（消息引导）
- [ ] ✅ 手册以**绝对路径**形式传递
- [ ] ✅ 结果文件列表支持
- [ ] ✅ 纯文本通信（CLI）
- [ ] ✅ Config 管理 Agent
- [ ] ✅ **Agent ID 以 opc_ 开头**
- [ ] ✅ **Gateway 重启需要用户确认**
- [ ] ✅ **不使用 main/default 调试**
- [ ] ✅ **任务超时默认 15 分钟，可配置**

---

## 十、附录：V2 参考代码

### 参考文件位置

```
archive/v2-skills/opc-bridge-v2/
├── SKILL.md              # Skill 文档参考（注意：名称改为 opc-bridge，无版本号）
├── scripts/
│   ├── opc-report.py     # 报告脚本参考
│   ├── opc-check-task.py # 检查任务参考
│   └── opc-get-budget.py # 预算查询参考

archive/v2-backend/src/core/openclaw_client.py
└── assign_task()         # 消息构建参考（需修改为使用 skill 函数和绝对路径）

archive/v2-backend/src/routers/skill_api.py
└── report_task_result()  # 回调处理参考
```

### 当前 opc-openclaw 已有功能

```
packages/opc-openclaw/src/opc_openclaw/
├── client/
│   ├── base.py           # BaseClient - HTTP 基础 ✅
│   ├── sessions.py       # SessionClient - spawn/send ✅
│   └── agents.py         # AgentClient - 列表/健康检查 ✅
├── agent/
│   ├── manager.py        # AgentManager - 高层接口 ✅
│   ├── lifecycle.py      # AgentLifecycle - 生命周期 ✅
│   └── binding.py        # AgentBinding - 绑定验证 ✅
├── interaction/
│   └── messenger.py      # Messenger - 消息发送 ✅
└── skill/
    └── definition.py     # Skill 定义文本 ✅ (name=opc-bridge)
```

### 需新增功能清单

```
packages/opc-openclaw/src/opc_openclaw/
├── interaction/
│   ├── config_manager.py     # ⭐ ConfigManager - 读取/修改 config
│   └── task_caller.py        # ⭐ TaskCaller - 任务调用封装
└── skill/
    ├── installer.py          # ⭐ SkillInstaller - 安装到 ~/.openclaw/
    └── scripts/
        ├── opc-report.py     # ⭐ 任务报告脚本
        ├── opc-check-task.py # ⭐ 检查任务脚本
        └── opc-get-budget.py # ⭐ 查询预算脚本
```

---

**文档版本**: 1.4  
**最后更新**: 2026-03-24  
**状态**: ✅ 核心功能实现完成，待测试和文档
