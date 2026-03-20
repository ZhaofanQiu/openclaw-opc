"""
Skill models for employee expertise system.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from src.database import Base


# Association table for agent skills
agent_skills_table = Table(
    "agent_skills",
    Base.metadata,
    Column("agent_id", String, ForeignKey("agents.id")),
    Column("skill_id", String, ForeignKey("skills.id")),
    Column("proficiency", Float, default=0.0),  # 0-100 proficiency level
    Column("acquired_at", DateTime, default=datetime.utcnow),
)


class Skill(Base):
    """Skill/expertise definition."""
    
    __tablename__ = "skills"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    category = Column(String, default="general")  # e.g., "coding", "design", "writing"
    icon = Column(String, default="📚")  # Emoji icon
    
    # Relationships
    agents = relationship("Agent", secondary=agent_skills_table, back_populates="skills")
    
    @classmethod
    def get_default_skills(cls):
        """Get list of default skills for the system."""
        return [
            {
                "id": "python",
                "name": "Python开发",
                "description": "Python编程、脚本开发、数据处理",
                "category": "coding",
                "icon": "🐍",
            },
            {
                "id": "javascript",
                "name": "JavaScript开发",
                "description": "前端开发、Node.js、浏览器脚本",
                "category": "coding",
                "icon": "🟨",
            },
            {
                "id": "database",
                "name": "数据库",
                "description": "SQL、数据库设计、数据管理",
                "category": "coding",
                "icon": "🗄️",
            },
            {
                "id": "ui_design",
                "name": "UI设计",
                "description": "用户界面设计、视觉设计",
                "category": "design",
                "icon": "🎨",
            },
            {
                "id": "writing",
                "name": "内容写作",
                "description": "文档撰写、博客文章、文案",
                "category": "writing",
                "icon": "✍️",
            },
            {
                "id": "testing",
                "name": "测试",
                "description": "软件测试、自动化测试、QA",
                "category": "coding",
                "icon": "🧪",
            },
            {
                "id": "devops",
                "name": "DevOps",
                "description": "CI/CD、部署、运维",
                "category": "coding",
                "icon": "🚀",
            },
            {
                "id": "research",
                "name": "研究",
                "description": "技术调研、竞品分析、资料整理",
                "category": "general",
                "icon": "🔍",
            },
        ]


class TaskSkillRequirement(Base):
    """Skill requirement for a task."""
    
    __tablename__ = "task_skill_requirements"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False)
    
    # Required proficiency (0-100), 0 means "nice to have"
    required_proficiency = Column(Float, default=50.0)
    
    # Weight of this skill in task (1-10)
    weight = Column(Integer, default=5)
    
    # Relationships
    task = relationship("Task", back_populates="skill_requirements")
    skill = relationship("Skill")
