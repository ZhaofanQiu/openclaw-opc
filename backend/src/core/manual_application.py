"""
手册应用模块

负责手册的读取、渲染和应用。
手册是员工执行任务时的重要参考。
"""

import os
from typing import Optional, Dict, List
from dataclasses import dataclass
from utils.logging_config import get_logger

logger = get_logger(__name__)

# 手册存储路径
MANUALS_DIR = "data/manuals"

@dataclass
class Manual:
    """手册数据"""
    id: str
    name: str
    type: str  # task, position, company
    content: str
    file_path: str
    created_at: str

class ManualApplication:
    """
    手册应用类
    
    功能:
    1. 读取手册内容
    2. 根据任务选择相关手册
    3. 渲染手册为 Agent 可读的格式
    """
    
    def __init__(self, manuals_dir: str = MANUALS_DIR):
        self.manuals_dir = manuals_dir
        os.makedirs(manuals_dir, exist_ok=True)
    
    def read_manual(self, manual_path: str) -> Optional[str]:
        """
        读取手册内容
        
        Args:
            manual_path: 手册文件路径（相对或绝对）
        
        Returns:
            手册内容，不存在返回 None
        """
        try:
            # 支持相对路径和绝对路径
            if not os.path.isabs(manual_path):
                full_path = os.path.join(self.manuals_dir, manual_path)
            else:
                full_path = manual_path
            
            if not os.path.exists(full_path):
                logger.warning(f"Manual not found: {full_path}")
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Read manual: {full_path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to read manual {manual_path}: {e}")
            return None
    
    def get_manuals_for_task(self, task_id: str, agent_id: str) -> Dict[str, str]:
        """
        获取任务相关的手册
        
        Returns:
            {
                "task": "任务手册路径",
                "position": "岗位手册路径",
                "company": "公司手册路径"
            }
        """
        manuals = {}
        
        # 任务手册
        task_manual = f"task_{task_id}.md"
        if os.path.exists(os.path.join(self.manuals_dir, task_manual)):
            manuals["task"] = task_manual
        
        # 岗位手册 (根据 agent_id 推断岗位)
        # TODO: 从数据库获取 agent 岗位信息
        position_manual = "position_general.md"
        if os.path.exists(os.path.join(self.manuals_dir, position_manual)):
            manuals["position"] = position_manual
        
        # 公司手册
        company_manual = "company.md"
        if os.path.exists(os.path.join(self.manuals_dir, company_manual)):
            manuals["company"] = company_manual
        
        return manuals
    
    def render_manual_for_agent(self, manual_content: str, 
                               manual_type: str) -> str:
        """
        将手册渲染为 Agent 可读的格式
        
        Args:
            manual_content: 手册原始内容
            manual_type: 手册类型 (task/position/company)
        
        Returns:
            渲染后的内容
        """
        type_names = {
            "task": "任务手册",
            "position": "岗位手册",
            "company": "公司手册"
        }
        
        header = f"## {type_names.get(manual_type, '手册')}\n\n"
        return header + manual_content
    
    def build_manual_context(self, manuals: Dict[str, str]) -> str:
        """
        构建手册上下文（用于发送给 Agent）
        
        Args:
            manuals: {type: content}
        
        Returns:
            合并后的手册上下文
        """
        parts = []
        
        for manual_type, content in manuals.items():
            if content:
                rendered = self.render_manual_for_agent(content, manual_type)
                parts.append(rendered)
        
        return "\n\n".join(parts) if parts else ""
    
    def save_manual(self, manual_id: str, content: str, 
                   manual_type: str = "task") -> str:
        """
        保存手册
        
        Args:
            manual_id: 手册 ID
            content: 手册内容
            manual_type: 手册类型
        
        Returns:
            保存的文件路径
        """
        file_name = f"{manual_type}_{manual_id}.md"
        file_path = os.path.join(self.manuals_dir, file_name)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Saved manual: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save manual: {e}")
            raise

# ============ 便捷函数 ============

def get_manual_content(manual_path: str) -> Optional[str]:
    """便捷函数: 读取手册内容"""
    app = ManualApplication()
    return app.read_manual(manual_path)

def build_task_context(task_id: str, agent_id: str) -> str:
    """便捷函数: 构建任务上下文（包含手册）"""
    app = ManualApplication()
    
    # 获取手册路径
    manuals_info = app.get_manuals_for_task(task_id, agent_id)
    
    # 读取手册内容
    manuals_content = {}
    for manual_type, manual_path in manuals_info.items():
        content = app.read_manual(manual_path)
        if content:
            manuals_content[manual_type] = content
    
    # 构建上下文
    return app.build_manual_context(manuals_content)
