"""
手册服务层

管理任务手册的生成、存储和检索
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.manual_template_engine import (
    ManualTemplateEngine,
    TaskManual,
    template_engine,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ManualService:
    """
    手册服务
    
    负责：
    - 根据任务生成手册
    - 存储手册到任务记录
    - 检索手册内容
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.template_engine = template_engine
    
    def generate_manual_for_task(
        self,
        task_id: str,
        task_title: str,
        task_description: str,
        template_id: Optional[str] = None,
        **kwargs
    ) -> TaskManual:
        """
        为任务生成手册
        
        Args:
            task_id: 任务 ID
            task_title: 任务标题
            task_description: 任务描述
            template_id: 指定模板 ID，None 则自动选择
            **kwargs: 额外参数
        
        Returns:
            TaskManual 对象
        """
        manual = self.template_engine.generate_manual(
            task_id=task_id,
            task_title=task_title,
            task_description=task_description,
            template_id=template_id,
            **kwargs
        )
        
        logger.info(
            "Manual generated for task",
            task_id=task_id,
            template_id=manual.template_id,
        )
        
        return manual
    
    def auto_generate_for_task(self, task) -> TaskManual:
        """
        根据任务对象自动生成手册
        
        Args:
            task: Task 模型对象
        
        Returns:
            TaskManual 对象
        """
        # 从任务描述提取额外信息
        kwargs = self._extract_task_context(task)
        
        return self.generate_manual_for_task(
            task_id=task.id,
            task_title=task.title,
            task_description=task.description or "",
            template_id=None,  # 自动选择
            **kwargs
        )
    
    def _extract_task_context(self, task) -> Dict[str, Any]:
        """
        从任务对象提取上下文信息
        
        Args:
            task: Task 对象
        
        Returns:
            参数字典
        """
        context = {
            "estimated_hours": self._estimate_hours(task),
            "constraints": self._extract_constraints(task),
            "expected_output": self._infer_expected_output(task),
        }
        
        # 尝试从描述中提取更多信息
        desc = (task.description or "").lower()
        
        if "文件" in desc or "file" in desc:
            context["files_list"] = self._extract_files_from_description(task.description)
        
        if "数据" in desc or "分析" in desc:
            context["data_sources"] = "从任务描述中提取的数据源"
        
        return context
    
    def _estimate_hours(self, task) -> str:
        """估算任务所需时间"""
        # 基于预算估算时间 (假设 1 OC币 ≈ 100 tokens ≈ 5 分钟)
        if hasattr(task, 'estimated_cost') and task.estimated_cost:
            minutes = task.estimated_cost * 5
            hours = max(1, round(minutes / 60))
            return f"{hours}-{hours+2}"
        return "2-4"
    
    def _extract_constraints(self, task) -> List[str]:
        """提取任务约束"""
        constraints = ["遵守公司规范"]
        
        if hasattr(task, 'priority'):
            if task.priority == "high":
                constraints.append("高优先级，需要尽快完成")
            elif task.priority == "urgent":
                constraints.append("紧急任务，优先处理")
        
        if hasattr(task, 'deadline') and task.deadline:
            constraints.append(f"截止日期: {task.deadline}")
        
        return constraints
    
    def _infer_expected_output(self, task) -> str:
        """推断预期输出"""
        title = (task.title or "").lower()
        desc = (task.description or "").lower()
        
        if "报告" in title or "report" in title:
            return "一份完整的报告文档"
        elif "代码" in title or "code" in title:
            return "可运行的代码和说明文档"
        elif "设计" in title or "design" in title:
            return "设计文档和相关资源"
        elif "分析" in title or "analysis" in title:
            return "分析结果和数据可视化"
        else:
            return "完成任务目标所需的交付物"
    
    def _extract_files_from_description(self, description: str) -> str:
        """从描述中提取文件列表"""
        # 简单实现：返回描述的前 200 字符作为上下文
        if description:
            return description[:200] + "..." if len(description) > 200 else description
        return "请参考任务描述中的文件信息"
    
    def list_available_templates(self) -> List[Dict[str, str]]:
        """列出所有可用模板"""
        return self.template_engine.list_templates()
    
    def get_template_content(self, template_id: str) -> Optional[str]:
        """获取模板内容（用于预览）"""
        template = self.template_engine.get_template(template_id)
        if template:
            return template.template_text
        return None
    
    def preview_manual(
        self,
        task_title: str,
        task_description: str,
        template_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        预览手册内容（不保存）
        
        Args:
            task_title: 任务标题
            task_description: 任务描述
            template_id: 模板 ID
            **kwargs: 额外参数
        
        Returns:
            手册内容字符串
        """
        manual = self.template_engine.generate_manual(
            task_id="preview",
            task_title=task_title,
            task_description=task_description,
            template_id=template_id,
            **kwargs
        )
        return manual.content


# 便捷函数
def generate_task_manual(task, db: Session) -> TaskManual:
    """
    为任务生成手册的便捷函数
    
    Args:
        task: Task 对象
        db: 数据库会话
    
    Returns:
        TaskManual
    """
    service = ManualService(db)
    return service.auto_generate_for_task(task)


def get_manual_service(db: Session) -> ManualService:
    """获取手册服务实例"""
    return ManualService(db)
