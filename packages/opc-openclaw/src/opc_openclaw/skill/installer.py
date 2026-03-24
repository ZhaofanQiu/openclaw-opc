"""
opc-openclaw: Skill 安装器 (v0.4.1)

安装 opc-bridge skill 到 ~/.openclaw/skills/

v0.4.1 变更:
- 使用 CLI 模式通信
- Agent 通过回复中的结构化数据报告结果
- 文档指引为主，脚本为可选辅助工具

作者: OpenClaw OPC Team
版本: 0.4.1
"""

import shutil
from pathlib import Path
from typing import Tuple


class SkillInstaller:
    """
    Skill 安装器

    将 opc-bridge skill 安装到用户的 OpenClaw 环境：
    ~/.openclaw/skills/opc-bridge/
    """

    SKILL_NAME = "opc-bridge"
    SKILL_DIR = Path.home() / ".openclaw" / "skills" / SKILL_NAME

    # SKILL.md 内容 (v0.4.1 - CLI模式)
    SKILL_MD = '''---
name: opc-bridge
description: Connect OpenClaw Agents to OPC Core Service for budget tracking and task management
version: 0.4.1
---

# OPC Bridge Skill v0.4.1

你是 OpenClaw OPC（一人公司操作系统）的一名员工。

## 核心身份

- 你是一名虚拟员工，受雇于 OpenClaw OPC
- 你有自己的岗位、技能和预算
- 你需要通过完成任务来为公司创造价值

## 任务执行规范

### 1. 接收任务时

任务消息会包含：
- **任务ID** (task_id)
- **任务标题和描述**
- **手册路径**（使用绝对路径读取）
- **预算信息**（本月预算、已使用、剩余）

### 2. 必须遵循的流程

1. **先读手册** - 使用绝对路径读取指定的手册文件
2. **执行任务** - 高效使用 Token，注意预算限制
3. **报告结果** - 在回复中包含任务报告

### 3. 任务报告格式（关键）

**任务完成后，必须在回复末尾包含以下格式的报告：**

```
---OPC-REPORT---
task_id: <任务ID>
status: completed|failed|needs_revision
tokens_used: <数字>
summary: <任务完成总结，单行文本>
result_files: <逗号分隔的文件路径，可选>
---END-REPORT---
```

**示例：**
```
我已经完成了代码审查任务，发现了3个潜在问题...

---OPC-REPORT---
task_id: task-001
status: completed
tokens_used: 523
summary: 代码审查完成，发现3个问题并已修复
result_files: /home/user/reports/review-001.md
---END-REPORT---
```

**注意事项：**
- 标记必须严格匹配 `---OPC-REPORT---` 和 `---END-REPORT---`
- `status` 必须是 `completed`、`failed` 或 `needs_revision` 之一
- `tokens_used` 必须是数字
- `result_files` 可以是多个文件路径，用逗号分隔

### 4. 预算意识

- 注意 Token 消耗，任务消息中会提供预算信息
- 如果预估成本超过剩余预算，提前说明
- 复杂任务可申请拆分

### 5. 约束

- 只能访问分配给你的数据
- 不能修改系统配置
- 不能访问其他员工私有数据
- Token 使用受预算限制
- **必须**在回复中包含 OPC-REPORT 格式的报告
'''

    def __init__(self, skill_dir: Path = None):
        """
        初始化

        Args:
            skill_dir: Skill 安装目录，默认 ~/.openclaw/skills/opc-bridge
        """
        self.skill_dir = skill_dir or self.SKILL_DIR

    def is_installed(self) -> bool:
        """
        检查 Skill 是否已安装

        Returns:
            是否已安装
        """
        skill_md = self.skill_dir / "SKILL.md"
        return skill_md.exists()

    def install(self) -> Tuple[bool, str]:
        """
        安装 Skill

        Returns:
            (success, message)
        """
        try:
            # 创建目录
            self.skill_dir.mkdir(parents=True, exist_ok=True)

            # 写入 SKILL.md
            skill_md_path = self.skill_dir / "SKILL.md"
            with open(skill_md_path, "w", encoding="utf-8") as f:
                f.write(self.SKILL_MD)

            return True, f'Skill "{self.SKILL_NAME}" v0.4.1 installed to {self.skill_dir}'

        except Exception as e:
            return False, f"Failed to install skill: {e}"

    def uninstall(self) -> Tuple[bool, str]:
        """
        卸载 Skill

        Returns:
            (success, message)
        """
        try:
            if self.skill_dir.exists():
                shutil.rmtree(self.skill_dir)
                return True, f'Skill "{self.SKILL_NAME}" uninstalled'
            return True, f'Skill "{self.SKILL_NAME}" is not installed'
        except Exception as e:
            return False, f"Failed to uninstall skill: {e}"

    def reinstall(self) -> Tuple[bool, str]:
        """
        重新安装 Skill

        Returns:
            (success, message)
        """
        self.uninstall()
        return self.install()

    def get_version(self) -> str:
        """
        获取已安装 Skill 的版本

        Returns:
            版本号，未安装返回 ""
        """
        skill_md_path = self.skill_dir / "SKILL.md"
        if not skill_md_path.exists():
            return ""
        
        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()
                # 查找 version: x.x.x
                import re
                match = re.search(r'version:\s*(\d+\.\d+\.\d+)', content)
                if match:
                    return match.group(1)
        except Exception:
            pass
        
        return "unknown"


__all__ = ["SkillInstaller"]