"""
Skill service for employee expertise and task matching.
"""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import Agent, Skill, Task, TaskSkillRequirement


class SkillService:
    """Skill management and task-agent matching service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Skill Management
    
    def get_or_create_skill(self, skill_id: str, name: str = None, 
                            description: str = None, category: str = "general",
                            icon: str = "📚") -> Skill:
        """Get existing skill or create new one."""
        skill = self.db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            skill = Skill(
                id=skill_id,
                name=name or skill_id,
                description=description or "",
                category=category,
                icon=icon,
            )
            self.db.add(skill)
            self.db.commit()
            self.db.refresh(skill)
        return skill
    
    def initialize_default_skills(self) -> List[Skill]:
        """Initialize system with default skills."""
        default_skills = Skill.get_default_skills()
        created = []
        
        for skill_data in default_skills:
            skill = self.get_or_create_skill(**skill_data)
            created.append(skill)
        
        return created
    
    def list_skills(self, category: str = None) -> List[Skill]:
        """List all skills with optional category filter."""
        query = self.db.query(Skill)
        if category:
            query = query.filter(Skill.category == category)
        return query.all()
    
    # Agent Skills
    
    def assign_skill_to_agent(self, agent_id: str, skill_id: str, 
                              proficiency: float = 50.0) -> bool:
        """
        Assign a skill to an agent with proficiency level.
        
        Args:
            agent_id: Agent's internal ID
            skill_id: Skill ID
            proficiency: Proficiency level 0-100
        
        Returns:
            True if successful
        """
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return False
        
        skill = self.db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            return False
        
        # Check if skill already assigned
        existing = self.db.execute(
            "SELECT * FROM agent_skills WHERE agent_id = :agent_id AND skill_id = :skill_id",
            {"agent_id": agent_id, "skill_id": skill_id}
        ).fetchone()
        
        if existing:
            # Update proficiency
            self.db.execute(
                "UPDATE agent_skills SET proficiency = :proficiency WHERE agent_id = :agent_id AND skill_id = :skill_id",
                {"agent_id": agent_id, "skill_id": skill_id, "proficiency": proficiency}
            )
        else:
            # Insert new
            from datetime import datetime
            self.db.execute(
                "INSERT INTO agent_skills (agent_id, skill_id, proficiency, acquired_at) VALUES (:agent_id, :skill_id, :proficiency, :acquired_at)",
                {"agent_id": agent_id, "skill_id": skill_id, "proficiency": proficiency, "acquired_at": datetime.utcnow()}
            )
        
        self.db.commit()
        return True
    
    def get_agent_skills(self, agent_id: str) -> List[Dict]:
        """Get all skills for an agent with proficiency."""
        result = self.db.execute(
            """
            SELECT s.id, s.name, s.description, s.category, s.icon, a.proficiency 
            FROM skills s 
            JOIN agent_skills a ON s.id = a.skill_id 
            WHERE a.agent_id = :agent_id
            ORDER BY a.proficiency DESC
            """,
            {"agent_id": agent_id}
        ).fetchall()
        
        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "category": row.category,
                "icon": row.icon,
                "proficiency": row.proficiency,
            }
            for row in result
        ]
    
    # Task Skill Requirements
    
    def set_task_skill_requirement(self, task_id: str, skill_id: str,
                                   required_proficiency: float = 50.0,
                                   weight: int = 5) -> TaskSkillRequirement:
        """Set a skill requirement for a task."""
        # Check if requirement already exists
        req = self.db.query(TaskSkillRequirement).filter(
            TaskSkillRequirement.task_id == task_id,
            TaskSkillRequirement.skill_id == skill_id
        ).first()
        
        if req:
            req.required_proficiency = required_proficiency
            req.weight = weight
        else:
            req = TaskSkillRequirement(
                task_id=task_id,
                skill_id=skill_id,
                required_proficiency=required_proficiency,
                weight=weight,
            )
            self.db.add(req)
        
        self.db.commit()
        self.db.refresh(req)
        return req
    
    def get_task_skill_requirements(self, task_id: str) -> List[Dict]:
        """Get all skill requirements for a task."""
        reqs = self.db.query(TaskSkillRequirement).filter(
            TaskSkillRequirement.task_id == task_id
        ).all()
        
        return [
            {
                "skill_id": req.skill_id,
                "skill_name": req.skill.name,
                "skill_icon": req.skill.icon,
                "required_proficiency": req.required_proficiency,
                "weight": req.weight,
            }
            for req in reqs
        ]
    
    # Skill Matching
    
    def calculate_agent_task_match_score(self, agent_id: str, task_id: str) -> Dict:
        """
        Calculate how well an agent matches a task based on skills.
        
        Returns:
            Dict with score (0-100), matched_skills, missing_skills
        """
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return {"score": 0, "matched_skills": [], "missing_skills": [], "reason": "Agent not found"}
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"score": 0, "matched_skills": [], "missing_skills": [], "reason": "Task not found"}
        
        # Get task requirements
        requirements = self.get_task_skill_requirements(task_id)
        if not requirements:
            # No specific requirements, any agent can do it
            return {"score": 100, "matched_skills": [], "missing_skills": [], "reason": "No skill requirements"}
        
        # Get agent skills
        agent_skills = {s["id"]: s["proficiency"] for s in self.get_agent_skills(agent_id)}
        
        matched_skills = []
        missing_skills = []
        total_weight = sum(r["weight"] for r in requirements)
        weighted_score = 0
        
        for req in requirements:
            skill_id = req["skill_id"]
            required = req["required_proficiency"]
            weight = req["weight"]
            
            if skill_id in agent_skills:
                agent_prof = agent_skills[skill_id]
                if agent_prof >= required:
                    # Meets or exceeds requirement
                    match_ratio = min(agent_prof / required, 1.5)  # Cap at 1.5x for overqualified
                    weighted_score += weight * match_ratio
                    matched_skills.append({
                        "skill_id": skill_id,
                        "skill_name": req["skill_name"],
                        "required": required,
                        "actual": agent_prof,
                    })
                else:
                    # Has skill but not proficient enough
                    match_ratio = agent_prof / required
                    weighted_score += weight * match_ratio * 0.5  # Partial credit
                    missing_skills.append({
                        "skill_id": skill_id,
                        "skill_name": req["skill_name"],
                        "required": required,
                        "actual": agent_prof,
                        "gap": required - agent_prof,
                    })
            else:
                # Doesn't have skill
                missing_skills.append({
                    "skill_id": skill_id,
                    "skill_name": req["skill_name"],
                    "required": required,
                    "actual": 0,
                    "gap": required,
                })
        
        # Calculate final score (0-100)
        score = (weighted_score / total_weight) * 100 if total_weight > 0 else 100
        score = min(score, 100)  # Cap at 100
        
        return {
            "score": round(score, 1),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "total_requirements": len(requirements),
            "met_requirements": len(matched_skills),
        }
    
    def find_best_agent_for_task(self, task_id: str, available_only: bool = True) -> Optional[Dict]:
        """
        Find the best available agent for a task based on skill match.
        
        Returns:
            Dict with agent info and match details, or None if no suitable agent
        """
        from models import AgentStatus
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        # Get candidate agents
        query = self.db.query(Agent)
        if available_only:
            query = query.filter(Agent.status == AgentStatus.IDLE.value)
        
        # Check budget
        query = query.filter(Agent.monthly_budget - Agent.used_budget >= task.estimated_cost)
        
        candidates = query.all()
        if not candidates:
            return None
        
        # Score each candidate
        scored_candidates = []
        for agent in candidates:
            match = self.calculate_agent_task_match_score(agent.id, task_id)
            scored_candidates.append({
                "agent": agent,
                "match": match,
            })
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x["match"]["score"], reverse=True)
        
        best = scored_candidates[0]
        return {
            "agent_id": best["agent"].id,
            "agent_name": best["agent"].name,
            "agent_emoji": best["agent"].emoji,
            "match_score": best["match"]["score"],
            "matched_skills": best["match"]["matched_skills"],
            "missing_skills": best["match"]["missing_skills"],
        }