"""
Skill Growth Service for v0.4.0

管理员工技能经验值和成长系统
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import Agent, AgentSkillGrowth, Skill, SkillGrowthHistory, Task, TaskPriority
from src.models.skill_growth import SKILL_GROWTH_CONFIG
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SkillGrowthService:
    """Service for managing skill growth and experience."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_skill_growth(
        self,
        agent_id: str,
        skill_id: str,
    ) -> AgentSkillGrowth:
        """
        Get or create skill growth record for an agent.
        
        Args:
            agent_id: Agent ID
            skill_id: Skill ID
        
        Returns:
            AgentSkillGrowth record
        """
        growth = self.db.query(AgentSkillGrowth).filter(
            AgentSkillGrowth.agent_id == agent_id,
            AgentSkillGrowth.skill_id == skill_id
        ).first()
        
        if not growth:
            # Verify agent and skill exist
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            skill = self.db.query(Skill).filter(Skill.id == skill_id).first()
            
            if not agent:
                raise ValueError(f"Agent '{agent_id}' not found")
            if not skill:
                raise ValueError(f"Skill '{skill_id}' not found")
            
            growth = AgentSkillGrowth(
                agent_id=agent_id,
                skill_id=skill_id,
                level=1,
                experience=0,
                experience_to_next=SKILL_GROWTH_CONFIG["base_exp_to_level"],
            )
            self.db.add(growth)
            self.db.commit()
            self.db.refresh(growth)
            
            logger.info(
                "skill_growth_created",
                agent_id=agent_id,
                skill_id=skill_id,
                skill_name=skill.name,
            )
        
        return growth
    
    def add_experience(
        self,
        agent_id: str,
        skill_id: str,
        experience: int,
        reason: str = "",
        task_id: str = None,
    ) -> Dict:
        """
        Add experience to an agent's skill.
        
        Args:
            agent_id: Agent ID
            skill_id: Skill ID
            experience: Experience points to add
            reason: Reason for the experience gain
            task_id: Optional related task ID
        
        Returns:
            Dict with growth details including level up info
        """
        growth = self.get_or_create_skill_growth(agent_id, skill_id)
        
        # Record level before
        level_before = growth.level
        
        # Add experience
        growth.experience += experience
        growth.total_experience_earned += experience
        growth.last_improved_at = datetime.utcnow()
        
        # Check for level up
        level_ups = 0
        while growth.experience >= growth.experience_to_next and growth.level < SKILL_GROWTH_CONFIG["max_level"]:
            growth.experience -= growth.experience_to_next
            growth.level += 1
            level_ups += 1
            growth.experience_to_next = growth.calculate_exp_to_next()
        
        # Cap at max level
        if growth.level >= SKILL_GROWTH_CONFIG["max_level"]:
            growth.level = SKILL_GROWTH_CONFIG["max_level"]
            growth.experience = 0
            growth.experience_to_next = 0
        
        # Record history
        history = SkillGrowthHistory(
            agent_id=agent_id,
            skill_id=skill_id,
            task_id=task_id,
            experience_gained=experience,
            level_before=level_before,
            level_after=growth.level,
            reason=reason or "Experience gained",
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(growth)
        
        result = {
            "agent_id": agent_id,
            "skill_id": skill_id,
            "experience_gained": experience,
            "level_before": level_before,
            "level_after": growth.level,
            "level_ups": level_ups,
            "current_experience": growth.experience,
            "experience_to_next": growth.experience_to_next,
            "progress_percentage": growth.progress_percentage,
            "is_max_level": growth.is_max_level,
        }
        
        if level_ups > 0:
            logger.info(
                "skill_level_up",
                agent_id=agent_id,
                skill_id=skill_id,
                level_ups=level_ups,
                new_level=growth.level,
            )
        
        return result
    
    def calculate_task_completion_exp(
        self,
        task: Task,
        skill_match: bool = False,
        streak_count: int = 0,
        efficiency_ratio: float = 1.0,
    ) -> int:
        """
        Calculate experience points for completing a task.
        
        Args:
            task: Completed task
            skill_match: Whether the task used the agent's primary skill
            streak_count: Current completion streak
            efficiency_ratio: Actual cost / Estimated cost (lower is better)
        
        Returns:
            Experience points
        """
        config = SKILL_GROWTH_CONFIG
        
        # Base experience
        base_exp = config["base_task_completion_exp"]
        
        # Difficulty multiplier
        difficulty = task.priority or "normal"
        multiplier = config["difficulty_multiplier"].get(difficulty, 1.0)
        
        total_exp = int(base_exp * multiplier)
        bonuses = []
        
        # Skill match bonus
        if skill_match:
            total_exp += config["skill_match_bonus"]
            bonuses.append(f"skill_match:+{config['skill_match_bonus']}")
        
        # Efficiency bonus
        efficiency_config = config["efficiency_bonus"]
        if efficiency_ratio <= efficiency_config["excellent"]["threshold"]:
            total_exp += efficiency_config["excellent"]["bonus"]
            bonuses.append(f"efficiency_excellent:+{efficiency_config['excellent']['bonus']}")
        elif efficiency_ratio <= efficiency_config["good"]["threshold"]:
            total_exp += efficiency_config["good"]["bonus"]
            bonuses.append(f"efficiency_good:+{efficiency_config['good']['bonus']}")
        
        # Streak bonus
        if config["streak_bonus"]["enabled"] and streak_count > 0:
            streak_bonus = min(
                streak_count * config["streak_bonus"]["bonus_per_streak"],
                config["streak_bonus"]["max_streak_bonus"]
            )
            total_exp += streak_bonus
            bonuses.append(f"streak:+{streak_bonus}")
        
        return total_exp
    
    def award_task_completion_exp(
        self,
        agent_id: str,
        task: Task,
    ) -> List[Dict]:
        """
        Award experience for task completion.
        
        Awards experience to all skills required by the task.
        
        Args:
            agent_id: Agent who completed the task
            task: Completed task
        
        Returns:
            List of growth results for each skill
        """
        results = []
        
        # Get task skill requirements
        skill_requirements = task.skill_requirements
        
        if not skill_requirements:
            # If no specific skills, award general experience
            # Find a general skill or use a default
            general_skill = self.db.query(Skill).filter(Skill.category == "general").first()
            if general_skill:
                exp = self.calculate_task_completion_exp(task)
                result = self.add_experience(
                    agent_id=agent_id,
                    skill_id=general_skill.id,
                    experience=exp,
                    reason=f"Completed task '{task.title}'",
                    task_id=task.id,
                )
                results.append(result)
        else:
            # Award experience for each required skill
            for req in skill_requirements:
                skill_match = True  # Task used this skill
                exp = self.calculate_task_completion_exp(
                    task=task,
                    skill_match=skill_match,
                )
                
                result = self.add_experience(
                    agent_id=agent_id,
                    skill_id=req.skill_id,
                    experience=exp,
                    reason=f"Completed task '{task.title}' - {req.skill.name}",
                    task_id=task.id,
                )
                results.append(result)
                
                # Update task count
                growth = self.get_or_create_skill_growth(agent_id, req.skill_id)
                growth.total_tasks_completed += 1
                self.db.commit()
        
        return results
    
    def get_agent_skills(self, agent_id: str) -> List[Dict]:
        """
        Get all skill growth data for an agent.
        
        Args:
            agent_id: Agent ID
        
        Returns:
            List of skill growth data
        """
        growth_records = self.db.query(AgentSkillGrowth).filter(
            AgentSkillGrowth.agent_id == agent_id
        ).all()
        
        return [
            {
                "skill_id": g.skill_id,
                "skill_name": g.skill.name,
                "skill_category": g.skill.category,
                "skill_icon": g.skill.icon,
                "level": g.level,
                "experience": g.experience,
                "experience_to_next": g.experience_to_next,
                "progress_percentage": g.progress_percentage,
                "total_tasks_completed": g.total_tasks_completed,
                "total_experience_earned": g.total_experience_earned,
                "is_max_level": g.is_max_level,
            }
            for g in growth_records
        ]
    
    def get_skill_details(
        self,
        agent_id: str,
        skill_id: str,
    ) -> Optional[Dict]:
        """
        Get detailed skill growth data for an agent.
        
        Args:
            agent_id: Agent ID
            skill_id: Skill ID
        
        Returns:
            Skill growth details or None
        """
        growth = self.db.query(AgentSkillGrowth).filter(
            AgentSkillGrowth.agent_id == agent_id,
            AgentSkillGrowth.skill_id == skill_id
        ).first()
        
        if not growth:
            return None
        
        # Get recent history
        recent_history = self.db.query(SkillGrowthHistory).filter(
            SkillGrowthHistory.agent_id == agent_id,
            SkillGrowthHistory.skill_id == skill_id
        ).order_by(SkillGrowthHistory.created_at.desc()).limit(10).all()
        
        return {
            "skill_id": growth.skill_id,
            "skill_name": growth.skill.name,
            "skill_description": growth.skill.description,
            "skill_category": growth.skill.category,
            "skill_icon": growth.skill.icon,
            "level": growth.level,
            "experience": growth.experience,
            "experience_to_next": growth.experience_to_next,
            "progress_percentage": growth.progress_percentage,
            "total_tasks_completed": growth.total_tasks_completed,
            "total_experience_earned": growth.total_experience_earned,
            "first_acquired_at": growth.first_acquired_at.isoformat() if growth.first_acquired_at else None,
            "last_improved_at": growth.last_improved_at.isoformat() if growth.last_improved_at else None,
            "is_max_level": growth.is_max_level,
            "recent_history": [
                {
                    "experience_gained": h.experience_gained,
                    "level_before": h.level_before,
                    "level_after": h.level_after,
                    "reason": h.reason,
                    "task_id": h.task_id,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in recent_history
            ],
        }
    
    def get_skill_leaderboard(
        self,
        skill_id: str = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get skill leaderboard.
        
        Args:
            skill_id: Filter by specific skill, or None for overall
            limit: Number of results
        
        Returns:
            Leaderboard list
        """
        if skill_id:
            # Specific skill leaderboard
            records = self.db.query(AgentSkillGrowth).filter(
                AgentSkillGrowth.skill_id == skill_id
            ).order_by(
                AgentSkillGrowth.level.desc(),
                AgentSkillGrowth.experience.desc()
            ).limit(limit).all()
            
            return [
                {
                    "rank": i + 1,
                    "agent_id": r.agent_id,
                    "agent_name": r.agent.name,
                    "agent_emoji": r.agent.emoji,
                    "level": r.level,
                    "experience": r.experience,
                    "total_experience_earned": r.total_experience_earned,
                    "total_tasks_completed": r.total_tasks_completed,
                }
                for i, r in enumerate(records)
            ]
        else:
            # Overall leaderboard (sum of all skills)
            from sqlalchemy import func
            
            results = self.db.query(
                AgentSkillGrowth.agent_id,
                func.sum(AgentSkillGrowth.level).label("total_level"),
                func.sum(AgentSkillGrowth.total_experience_earned).label("total_exp"),
            ).group_by(
                AgentSkillGrowth.agent_id
            ).order_by(
                func.sum(AgentSkillGrowth.level).desc()
            ).limit(limit).all()
            
            leaderboard = []
            for i, (agent_id, total_level, total_exp) in enumerate(results):
                agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    leaderboard.append({
                        "rank": i + 1,
                        "agent_id": agent_id,
                        "agent_name": agent.name,
                        "agent_emoji": agent.emoji,
                        "total_level": int(total_level) if total_level else 0,
                        "total_experience": int(total_exp) if total_exp else 0,
                    })
            
            return leaderboard
    
    def get_growth_stats(self) -> Dict:
        """
        Get overall skill growth statistics.
        
        Returns:
            Statistics dict
        """
        from sqlalchemy import func
        
        total_records = self.db.query(AgentSkillGrowth).count()
        
        avg_level = self.db.query(func.avg(AgentSkillGrowth.level)).scalar() or 0
        max_level = self.db.query(func.max(AgentSkillGrowth.level)).scalar() or 0
        
        total_exp = self.db.query(func.sum(AgentSkillGrowth.total_experience_earned)).scalar() or 0
        total_tasks = self.db.query(func.sum(AgentSkillGrowth.total_tasks_completed)).scalar() or 0
        
        # Max level count
        max_level_count = self.db.query(AgentSkillGrowth).filter(
            AgentSkillGrowth.level >= SKILL_GROWTH_CONFIG["max_level"]
        ).count()
        
        return {
            "total_skill_records": total_records,
            "average_level": round(avg_level, 2),
            "highest_level": max_level,
            "max_level_count": max_level_count,
            "total_experience_earned": int(total_exp),
            "total_tasks_completed": int(total_tasks),
        }
