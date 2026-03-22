"""
Skill Growth models for v0.4.0

员工技能经验值和成长系统
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.database import Base


class AgentSkillGrowth(Base):
    """
    Agent skill growth/experience tracking for v0.4.0
    
    记录员工每项技能的等级和经验值
    """
    
    __tablename__ = "agent_skill_growth"
    
    id = Column(Integer, primary_key=True)
    
    # 关联
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False)
    
    # 等级系统
    level = Column(Integer, default=1)  # 当前等级 (1-100)
    experience = Column(Integer, default=0)  # 当前经验值
    experience_to_next = Column(Integer, default=100)  # 升级所需经验
    
    # 统计
    total_tasks_completed = Column(Integer, default=0)  # 完成的相关任务数
    total_experience_earned = Column(Integer, default=0)  # 累计获得经验
    
    # 首次获得和最后更新
    first_acquired_at = Column(DateTime, default=datetime.utcnow)
    last_improved_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    agent = relationship("Agent", back_populates="skill_growth")
    skill = relationship("Skill")
    
    def __repr__(self):
        return f"<AgentSkillGrowth(agent_id={self.agent_id}, skill_id={self.skill_id}, level={self.level})>"
    
    @property
    def progress_percentage(self) -> float:
        """计算当前等级进度百分比。"""
        if self.experience_to_next <= 0:
            return 100.0
        return (self.experience / self.experience_to_next) * 100
    
    @property
    def is_max_level(self) -> bool:
        """检查是否已达最高等级。"""
        return self.level >= 100
    
    def calculate_exp_to_next(self) -> int:
        """
        计算升级到下一级所需经验值。
        经验曲线：每级所需经验 = 基础值 * (1.1 ^ (等级-1))
        """
        import math
        base_exp = 100
        return int(base_exp * (1.1 ** (self.level - 1)))


class SkillGrowthHistory(Base):
    """
    Skill growth history records for v0.4.0
    
    记录每次经验值变动的历史
    """
    
    __tablename__ = "skill_growth_history"
    
    id = Column(Integer, primary_key=True)
    
    # 关联
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)  # 可选，关联任务
    
    # 变动信息
    experience_gained = Column(Integer, nullable=False)  # 获得的经验值（负数为扣除）
    level_before = Column(Integer, nullable=False)  # 变动前等级
    level_after = Column(Integer, nullable=False)  # 变动后等级
    
    # 原因
    reason = Column(Text, default="")  # 获得经验的原因
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    agent = relationship("Agent", back_populates="skill_growth_history")
    skill = relationship("Skill")
    task = relationship("Task")


# 经验值配置
SKILL_GROWTH_CONFIG = {
    # 任务完成基础经验
    "base_task_completion_exp": 50,
    
    # 难度系数
    "difficulty_multiplier": {
        "low": 0.8,
        "normal": 1.0,
        "high": 1.5,
        "urgent": 2.0,
    },
    
    # 预算效率奖励（实际花费/预估预算，越低越好）
    "efficiency_bonus": {
        "excellent": {"threshold": 0.7, "bonus": 20},  # 节省30%以上
        "good": {"threshold": 0.9, "bonus": 10},       # 节省10%以上
    },
    
    # 连续完成奖励
    "streak_bonus": {
        "enabled": True,
        "bonus_per_streak": 5,  # 每连续完成一个任务+5
        "max_streak_bonus": 25,  # 最多+25
    },
    
    # 技能匹配奖励（使用技能对应任务）
    "skill_match_bonus": 15,
    
    # 等级上限
    "max_level": 100,
    
    # 升级基础经验
    "base_exp_to_level": 100,
    
    # 经验曲线指数
    "exp_curve_exponent": 1.1,
}
