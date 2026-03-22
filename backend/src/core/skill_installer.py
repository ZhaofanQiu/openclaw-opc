"""
opc-bridge Skill 安装器

在一键部署时自动安装 skill 到用户的 OpenClaw
"""

import os
import shutil
from pathlib import Path
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Skill 内容
SKILL_NAME = "opc-bridge"
SKILL_VERSION = "2.0.0"

SKILL_MANIFEST = """name: opc-bridge
description: OPC (One-Person Company) 员工基础能力 Skill
version: 2.0.0
author: OpenClaw OPC Team

config:
  opc_core_url: "http://localhost:8080"
  api_key: "${OPC_API_KEY}"
  
permissions:
  - http_request
  - file_read
  - file_write

dependencies: []
"""

SKILL_MAIN = '''#!/usr/bin/env python3
"""
opc-bridge Skill 主程序

提供 OPC 员工的基础能力：
- 任务管理
- 手册读取
- 数据库操作
- 预算查询
"""

import os
import json
import requests
from typing import Dict, Any, Optional

class OPCBridge:
    """OPC Bridge Skill 实现"""
    
    def __init__(self):
        self.core_url = os.getenv("OPC_CORE_URL", "http://localhost:8080")
        self.api_key = os.getenv("OPC_API_KEY", "")
        self.agent_id = os.getenv("OPC_AGENT_ID", "")
        
    def _call_api(self, method: str, endpoint: str, data: dict = None) -> dict:
        """调用 OPC API"""
        url = f"{self.core_url}/api{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, params=data)
            else:
                resp = requests.post(url, headers=headers, json=data)
            
            return resp.json() if resp.status_code == 200 else {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}
    
    # ============ 任务管理 ============
    
    def opc_get_current_task(self) -> dict:
        """获取当前任务"""
        return self._call_api("GET", f"/agents/{self.agent_id}/current-task")
    
    def opc_report_task_result(self, task_id: str, result: str, tokens_used: int) -> dict:
        """报告任务结果"""
        return self._call_api("POST", f"/tasks/{task_id}/report", {
            "agent_id": self.agent_id,
            "result": result,
            "tokens_used": tokens_used
        })
    
    # ============ 手册读取 ============
    
    def opc_read_manual(self, manual_type: str, manual_id: str) -> dict:
        """读取手册"""
        return self._call_api("GET", f"/manuals/{manual_type}/{manual_id}")
    
    # ============ 数据库操作 ============
    
    def opc_db_read(self, table: str, query: dict = None) -> dict:
        """读取数据库"""
        return self._call_api("POST", "/db/read", {
            "agent_id": self.agent_id,
            "table": table,
            "query": query or {}
        })
    
    def opc_db_write(self, table: str, data: dict) -> dict:
        """写入数据库"""
        return self._call_api("POST", "/db/write", {
            "agent_id": self.agent_id,
            "table": table,
            "data": data
        })
    
    # ============ 预算查询 ============
    
    def opc_get_budget(self) -> dict:
        """获取预算"""
        return self._call_api("GET", f"/agents/{self.agent_id}/budget")


# 全局实例
_bridge = None

def get_bridge() -> OPCBridge:
    """获取 Bridge 实例"""
    global _bridge
    if _bridge is None:
        _bridge = OPCBridge()
    return _bridge

# 便捷导出
opc_get_current_task = lambda: get_bridge().opc_get_current_task()
opc_report_task_result = lambda **kwargs: get_bridge().opc_report_task_result(**kwargs)
opc_read_manual = lambda **kwargs: get_bridge().opc_read_manual(**kwargs)
opc_db_read = lambda **kwargs: get_bridge().opc_db_read(**kwargs)
opc_db_write = lambda **kwargs: get_bridge().opc_db_write(**kwargs)
opc_get_budget = lambda: get_bridge().opc_get_budget()
'''

SKILL_INSTRUCTIONS = '''# OPC Bridge Skill

你是 OpenClaw OPC 的员工，可以使用以下能力：

## 任务管理
- `opc_get_current_task()` - 获取当前任务
- `opc_report_task_result(task_id, result, tokens_used)` - 报告结果

## 手册读取
- `opc_read_manual(manual_type, manual_id)` - 读取手册
  - manual_type: "task" | "position" | "company"

## 数据库操作
- `opc_db_read(table, query)` - 读取数据
- `opc_db_write(table, data)` - 写入数据

## 预算查询
- `opc_get_budget()` - 查询预算

## 执行流程
1. 调用 opc_get_current_task() 获取任务
2. 调用 opc_read_manual() 读取相关手册
3. 执行任务
4. 调用 opc_report_task_result() 报告结果
'''


class SkillInstaller:
    """Skill 安装器"""
    
    def __init__(self, openclaw_skills_dir: Optional[str] = None):
        """
        初始化安装器
        
        Args:
            openclaw_skills_dir: OpenClaw skills 目录，
                                默认 ~/.openclaw/skills/
        """
        if openclaw_skills_dir:
            self.skills_dir = Path(openclaw_skills_dir)
        else:
            self.skills_dir = Path.home() / ".openclaw" / "skills"
        
        self.skill_dir = self.skills_dir / SKILL_NAME
        
    def install(self, opc_api_key: str = "") -> bool:
        """
        安装 opc-bridge skill
        
        Args:
            opc_api_key: OPC Core Service API Key
            
        Returns:
            是否安装成功
        """
        try:
            logger.info(f"Installing {SKILL_NAME} skill...")
            
            # 创建 skill 目录
            self.skill_dir.mkdir(parents=True, exist_ok=True)
            
            # 写入 manifest.yaml
            manifest = SKILL_MANIFEST.replace("${OPC_API_KEY}", opc_api_key)
            (self.skill_dir / "manifest.yaml").write_text(manifest, encoding="utf-8")
            
            # 写入 skill.py
            (self.skill_dir / "skill.py").write_text(SKILL_MAIN, encoding="utf-8")
            
            # 写入 instructions.md
            (self.skill_dir / "instructions.md").write_text(SKILL_INSTRUCTIONS, encoding="utf-8")
            
            # 设置环境变量示例
            env_example = f"""# OPC Bridge Skill 环境变量
OPC_CORE_URL=http://localhost:8080
OPC_API_KEY={opc_api_key}
"""
            (self.skill_dir / ".env.example").write_text(env_example, encoding="utf-8")
            
            logger.info(f"✓ {SKILL_NAME} skill installed to {self.skill_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install skill: {e}")
            return False
    
    def uninstall(self) -> bool:
        """卸载 skill"""
        try:
            if self.skill_dir.exists():
                shutil.rmtree(self.skill_dir)
                logger.info(f"✓ {SKILL_NAME} skill uninstalled")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall skill: {e}")
            return False
    
    def is_installed(self) -> bool:
        """检查是否已安装"""
        return (self.skill_dir / "manifest.yaml").exists()
    
    def update(self, opc_api_key: str = "") -> bool:
        """更新 skill"""
        logger.info(f"Updating {SKILL_NAME} skill...")
        self.uninstall()
        return self.install(opc_api_key)


# ============ 便捷函数 ============

def install_skill(opc_api_key: str = "", openclaw_dir: Optional[str] = None) -> bool:
    """便捷函数: 安装 skill"""
    installer = SkillInstaller(openclaw_dir)
    return installer.install(opc_api_key)

def check_skill_installed(openclaw_dir: Optional[str] = None) -> bool:
    """便捷函数: 检查 skill 是否已安装"""
    installer = SkillInstaller(openclaw_dir)
    return installer.is_installed()
