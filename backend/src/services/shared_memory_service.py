"""
Shared Memory Service for v0.4.0

管理公司级共享记忆
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from models import Agent, MemoryAccessLog, SharedMemory
from models.shared_memory import MemoryCategory, MemoryScope
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SharedMemoryService:
    """Service for managing shared company memories."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_memory(
        self,
        agent_id: str,
        title: str,
        content: str,
        category: str = MemoryCategory.GENERAL.value,
        scope: str = MemoryScope.COMPANY.value,
        tags: List[str] = None,
        importance: int = 3,
        expires_hours: int = None,
    ) -> SharedMemory:
        """
        Create a new shared memory.
        
        Args:
            agent_id: Creator agent ID
            title: Memory title
            content: Memory content
            category: Memory category
            scope: Memory scope
            tags: List of tags
            importance: Importance level (1-5)
            expires_hours: Expiration time in hours
        
        Returns:
            Created memory
        """
        # Verify agent exists (optional)
        if agent_id:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise ValueError(f"Agent '{agent_id}' not found")
        
        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        memory = SharedMemory(
            id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            title=title,
            content=content,
            category=category,
            scope=scope,
            tags=",".join(tags or []),
            importance=importance,
            expires_at=expires_at,
        )
        
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        
        # Log access
        self._log_access(memory.id, agent_id, "write")
        
        logger.info(
            "memory_created",
            memory_id=memory.id,
            agent_id=agent_id,
            category=category,
        )
        
        return memory
    
    def get_memory(
        self,
        memory_id: str,
        agent_id: str = None,
    ) -> Optional[SharedMemory]:
        """
        Get a memory by ID.
        
        Args:
            memory_id: Memory ID
            agent_id: Agent accessing (for logging)
        
        Returns:
            Memory or None
        """
        memory = self.db.query(SharedMemory).filter(
            SharedMemory.id == memory_id
        ).first()
        
        if memory and not memory.is_expired:
            # Increment access count
            memory.access_count = (memory.access_count or 0) + 1
            self.db.commit()
            
            # Log access
            self._log_access(memory_id, agent_id, "read")
        
        return memory
    
    def update_memory(
        self,
        memory_id: str,
        agent_id: str,
        title: str = None,
        content: str = None,
        category: str = None,
        tags: List[str] = None,
        importance: int = None,
    ) -> SharedMemory:
        """
        Update a memory.
        
        Args:
            memory_id: Memory ID
            agent_id: Agent making the update
            title: New title
            content: New content
            category: New category
            tags: New tags
            importance: New importance
        
        Returns:
            Updated memory
        """
        memory = self.db.query(SharedMemory).filter(
            SharedMemory.id == memory_id
        ).first()
        
        if not memory:
            raise ValueError(f"Memory '{memory_id}' not found")
        
        # Check permission (only creator or Partner can update)
        if memory.agent_id and memory.agent_id != agent_id:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            from models.agent import PositionLevel
            if not agent or agent.position_level != PositionLevel.PARTNER.value:
                raise ValueError("Only creator or Partner can update this memory")
        
        if title is not None:
            memory.title = title
        if content is not None:
            memory.content = content
        if category is not None:
            memory.category = category
        if tags is not None:
            memory.tags = ",".join(tags)
        if importance is not None:
            memory.importance = importance
        
        memory.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(memory)
        
        # Log access
        self._log_access(memory_id, agent_id, "write")
        
        logger.info(
            "memory_updated",
            memory_id=memory_id,
            agent_id=agent_id,
        )
        
        return memory
    
    def delete_memory(self, memory_id: str, agent_id: str):
        """
        Delete a memory.
        
        Args:
            memory_id: Memory ID
            agent_id: Agent making the deletion
        """
        memory = self.db.query(SharedMemory).filter(
            SharedMemory.id == memory_id
        ).first()
        
        if not memory:
            raise ValueError(f"Memory '{memory_id}' not found")
        
        # Check permission
        if memory.agent_id and memory.agent_id != agent_id:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            from models.agent import PositionLevel
            if not agent or agent.position_level != PositionLevel.PARTNER.value:
                raise ValueError("Only creator or Partner can delete this memory")
        
        self.db.delete(memory)
        self.db.commit()
        
        logger.info(
            "memory_deleted",
            memory_id=memory_id,
            agent_id=agent_id,
        )
    
    def search_memories(
        self,
        query: str = None,
        category: str = None,
        tags: List[str] = None,
        agent_id: str = None,
        importance_min: int = None,
        scope: str = MemoryScope.COMPANY.value,
        limit: int = 20,
        offset: int = 0,
        agent_id_filter: str = None,
    ) -> List[SharedMemory]:
        """
        Search memories with filters.
        
        Args:
            query: Search query (matches title and content)
            category: Filter by category
            tags: Filter by tags (any match)
            agent_id: Agent accessing (for logging)
            importance_min: Minimum importance level
            scope: Memory scope
            limit: Result limit
            offset: Result offset
            agent_id_filter: Filter by creator agent
        
        Returns:
            List of memories
        """
        db_query = self.db.query(SharedMemory).filter(
            or_(
                SharedMemory.expires_at == None,
                SharedMemory.expires_at > datetime.utcnow()
            )
        )
        
        # Text search
        if query:
            search_pattern = f"%{query}%"
            db_query = db_query.filter(
                or_(
                    SharedMemory.title.ilike(search_pattern),
                    SharedMemory.content.ilike(search_pattern),
                )
            )
        
        # Category filter
        if category:
            db_query = db_query.filter(SharedMemory.category == category)
        
        # Tag filter
        if tags:
            for tag in tags:
                db_query = db_query.filter(SharedMemory.tags.contains(tag))
        
        # Importance filter
        if importance_min:
            db_query = db_query.filter(SharedMemory.importance >= importance_min)
        
        # Scope filter
        if scope:
            db_query = db_query.filter(SharedMemory.scope == scope)
        
        # Agent filter
        if agent_id_filter:
            db_query = db_query.filter(SharedMemory.agent_id == agent_id_filter)
        
        # Order by importance and creation time
        db_query = db_query.order_by(
            desc(SharedMemory.importance),
            desc(SharedMemory.created_at)
        )
        
        results = db_query.offset(offset).limit(limit).all()
        
        # Log search access
        if agent_id:
            for memory in results[:5]:  # Log top 5 results
                self._log_access(memory.id, agent_id, "search")
        
        return results
    
    def get_recent_memories(
        self,
        category: str = None,
        limit: int = 10,
    ) -> List[SharedMemory]:
        """
        Get recently created memories.
        
        Args:
            category: Filter by category
            limit: Number of results
        
        Returns:
            List of memories
        """
        query = self.db.query(SharedMemory).filter(
            or_(
                SharedMemory.expires_at == None,
                SharedMemory.expires_at > datetime.utcnow()
            )
        )
        
        if category:
            query = query.filter(SharedMemory.category == category)
        
        return query.order_by(desc(SharedMemory.created_at)).limit(limit).all()
    
    def get_popular_memories(
        self,
        limit: int = 10,
    ) -> List[SharedMemory]:
        """
        Get most accessed memories.
        
        Args:
            limit: Number of results
        
        Returns:
            List of memories
        """
        return self.db.query(SharedMemory).filter(
            or_(
                SharedMemory.expires_at == None,
                SharedMemory.expires_at > datetime.utcnow()
            )
        ).order_by(desc(SharedMemory.access_count)).limit(limit).all()
    
    def get_memory_stats(self) -> Dict:
        """
        Get memory statistics.
        
        Returns:
            Statistics dict
        """
        total = self.db.query(SharedMemory).count()
        
        active = self.db.query(SharedMemory).filter(
            or_(
                SharedMemory.expires_at == None,
                SharedMemory.expires_at > datetime.utcnow()
            )
        ).count()
        
        expired = self.db.query(SharedMemory).filter(
            SharedMemory.expires_at <= datetime.utcnow()
        ).count()
        
        # By category
        from sqlalchemy import func
        category_counts = self.db.query(
            SharedMemory.category,
            func.count(SharedMemory.id)
        ).group_by(SharedMemory.category).all()
        
        # Total access
        total_access = self.db.query(func.sum(SharedMemory.access_count)).scalar() or 0
        
        return {
            "total_memories": total,
            "active_memories": active,
            "expired_memories": expired,
            "category_distribution": {cat: count for cat, count in category_counts},
            "total_access_count": int(total_access),
        }
    
    def cleanup_expired_memories(self) -> int:
        """
        Clean up expired memories.
        
        Returns:
            Number of deleted memories
        """
        expired = self.db.query(SharedMemory).filter(
            SharedMemory.expires_at <= datetime.utcnow()
        ).all()
        
        count = len(expired)
        for memory in expired:
            self.db.delete(memory)
        
        if count > 0:
            self.db.commit()
            logger.info("expired_memories_cleaned", count=count)
        
        return count
    
    def get_memories_for_agent_context(
        self,
        agent_id: str,
        task_type: str = None,
        limit: int = 5,
    ) -> List[Dict]:
        """
        Get relevant memories for agent context.
        
        This is used when sending context to OpenClaw Agent.
        
        Args:
            agent_id: Agent ID
            task_type: Type of task for relevance
            limit: Number of memories
        
        Returns:
            List of memory dicts
        """
        # Get recent and popular memories
        recent = self.get_recent_memories(limit=limit)
        
        # If task_type provided, also search for relevant memories
        if task_type:
            relevant = self.search_memories(
                query=task_type,
                limit=limit,
                agent_id=agent_id,
            )
            # Combine and deduplicate
            seen = set()
            combined = []
            for m in relevant + recent:
                if m.id not in seen:
                    seen.add(m.id)
                    combined.append(m)
            recent = combined[:limit]
        
        return [
            {
                "id": m.id,
                "title": m.title,
                "content": m.content,
                "category": m.category,
                "tags": m.tag_list,
                "importance": m.importance,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in recent
        ]
    
    def _log_access(
        self,
        memory_id: str,
        agent_id: str,
        access_type: str,
    ):
        """Log memory access."""
        log = MemoryAccessLog(
            memory_id=memory_id,
            agent_id=agent_id,
            access_type=access_type,
        )
        self.db.add(log)
        self.db.commit()
