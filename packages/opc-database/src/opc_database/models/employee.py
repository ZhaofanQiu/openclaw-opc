"""
opc-database: 员工模型

定义员工(Agent)相关的数据模型

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#EmployeeModel
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .task import Task


class AgentStatus(str, PyEnum):
    """员工状态枚举"""
    IDLE = "idle"           # 空闲
    WORKING = "working"     # 工作中
    OFFLINE = "offline"     # 离线


class PositionLevel(int, PyEnum):
    """职位等级枚举"""
    INTERN = 1              # 实习生
    SPECIALIST = 2          # 专员
    SENIOR = 3              # 资深
    EXPERT = 4              # 专家
    PARTNER = 5             # 合伙人


class Employee(Base):
    """
    员工模型
    
    对应 OpenClaw 的 Agent 概念，是任务执行的主体
    
    Attributes:
        id: 员工唯一标识 (主键)
        name: 员工姓名
        emoji: 表情符号
        position_level: 职位等级 (1-5)
        openclaw_agent_id: 绑定的 OpenClaw Agent ID
        is_bound: 是否已绑定 ("true" | "false")
        monthly_budget: 月度预算 (OC币)
        used_budget: 已使用预算
        status: 当前状态
        current_task_id: 当前执行任务ID
        completed_tasks: 已完成任务数
    """
    
    __tablename__ = "employees"
    
    # 主键
    id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # 基本信息
    name: Mapped[str] = mapped_column(String, nullable=False)
    emoji: Mapped[str] = mapped_column(String, default="🤖")
    
    # 职位等级
    position_level: Mapped[int] = mapped_column(
        Integer, 
        default=PositionLevel.INTERN.value
    )
    
    # OpenClaw 绑定
    openclaw_agent_id: Mapped[Optional[str]] = mapped_column(
        String, 
        unique=True, 
        nullable=True
    )
    is_bound: Mapped[str] = mapped_column(String, default="false")
    
    # 预算管理
    monthly_budget: Mapped[float] = mapped_column(Float, default=1000.0)
    used_budget: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 工作状态
    status: Mapped[str] = mapped_column(
        String, 
        default=AgentStatus.IDLE.value
    )
    current_task_id: Mapped[Optional[str]] = mapped_column(
        String, 
        ForeignKey("tasks.id"),
        nullable=True
    )
    
    # 统计
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    
    # 关联关系
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="assignee",
        foreign_keys="Task.assigned_to"
    )
    
    @property
    def remaining_budget(self) -> float:
        """剩余预算"""
        return self.monthly_budget - self.used_budget
    
    @property
    def budget_percentage(self) -> float:
        """预算剩余百分比 (0-100)"""
        if self.monthly_budget <= 0:
            return 0.0
        return (self.remaining_budget / self.monthly_budget) * 100
    
    @property
    def mood_emoji(self) -> str:
        """
        根据预算情况返回心情表情
        
        Returns:
            😊 (>60%) / 😐 (>30%) / 😔 (>10%) / 🚨 (≤10%)
        """
        pct = self.budget_percentage
        if pct > 60:
            return "😊"
        elif pct > 30:
            return "😐"
        elif pct > 10:
            return "😔"
        else:
            return "🚨"
    
    def can_accept_task(self, estimated_cost: float = 0.0) -> bool:
        """
        检查是否能接受新任务
        
        Args:
            estimated_cost: 预估任务成本
            
        Returns:
            预算充足且状态允许时返回 True
        """
        if self.status == AgentStatus.OFFLINE.value:
            return False
        if self.remaining_budget < estimated_cost:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            包含员工完整信息的字典
        """
        base = super().to_dict()
        base.update({
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "position_level": self.position_level,
            "position_name": self._get_position_name(),
            "status": self.status,
            "monthly_budget": self.monthly_budget,
            "used_budget": self.used_budget,
            "remaining_budget": self.remaining_budget,
            "budget_percentage": self.budget_percentage,
            "mood": self.mood_emoji,
            "openclaw_agent_id": self.openclaw_agent_id,
            "is_bound": self.is_bound == "true",
            "current_task_id": self.current_task_id,
            "completed_tasks": self.completed_tasks,
        })
        return base
    
    def _get_position_name(self) -> str:
        """获取职位名称"""
        names = {
            PositionLevel.INTERN.value: "实习生",
            PositionLevel.SPECIALIST.value: "专员",
            PositionLevel.SENIOR.value: "资深",
            PositionLevel.EXPERT.value: "专家",
            PositionLevel.PARTNER.value: "合伙人",
        }
        return names.get(self.position_level, "未知")


class EmployeeSkill(Base):
    """
    员工技能模型
    
    记录员工的技能熟练度
    """
    
    __tablename__ = "employee_skills"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    employee_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("employees.id"),
        nullable=False
    )
    skill_name: Mapped[str] = mapped_column(String, nullable=False)
    proficiency: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    experience_points: Mapped[int] = mapped_column(Integer, default=0)
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "id": self.id,
            "employee_id": self.employee_id,
            "skill_name": self.skill_name,
            "proficiency": self.proficiency,
            "experience_points": self.experience_points,
        })
        return base
