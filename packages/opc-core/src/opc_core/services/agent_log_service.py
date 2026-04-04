"""
opc-core: Agent 交互日志服务

记录和管理与 OpenClaw Agent 的交互日志

作者: OpenClaw OPC Team
创建日期: 2026-03-27
版本: 0.4.5
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import desc, func

from opc_database.models import AgentLog
from opc_database import get_session


class AgentLogService:
    """
    Agent 交互日志服务
    
    提供日志记录、查询、统计和清空功能
    
    Phase 1 优化: 使用 asyncio.Lock 避免 SQLite 并发写入冲突
    """
    
    # 写入锁 - 防止 SQLite 并发写入冲突
    _write_lock = asyncio.Lock()
    
    # 内存缓存（最近 100 条，减少数据库查询）
    _memory_cache: List[Dict] = []
    _max_cache = 100
    
    @classmethod
    async def log_outgoing(
        cls,
        agent_id: str,
        agent_name: Optional[str] = None,
        interaction_type: str = "message",
        content: str = "",
        task_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        记录发送给 Agent 的消息
        
        Args:
            agent_id: Agent ID
            agent_name: Agent 名称
            interaction_type: 交互类型
            content: 发送的内容（原始文本）
            task_id: 关联任务ID
            metadata: 额外元数据
            
        Returns:
            log_id: 日志ID，用于后续关联 incoming 记录
        """
        log_id = uuid.uuid4().hex[:16]
        
        # 限制内容长度（防止过大）
        content_truncated = content[:10000] if content else ""
        
        # Phase 1: 使用锁保护写入，避免 SQLite 并发冲突
        async with cls._write_lock:
            async with get_session() as session:
                log = AgentLog(
                    id=log_id,
                    agent_id=agent_id,
                    agent_name=agent_name or agent_id,
                    interaction_type=interaction_type,
                    direction="outgoing",
                    content=content_truncated,
                    task_id=task_id,
                    meta_info=metadata or {}
                )
                session.add(log)
                await session.flush()
        
        # 添加到内存缓存（在锁外执行）
        cls._memory_cache.insert(0, {
            "id": log_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "interaction_type": interaction_type,
            "direction": "outgoing",
            "content_preview": content_truncated[:200],
            "created_at": datetime.utcnow().isoformat()
        })
        
        # 限制缓存大小
        if len(cls._memory_cache) > cls._max_cache:
            cls._memory_cache = cls._memory_cache[:cls._max_cache]
        
        return log_id
    
    @classmethod
    async def log_incoming(
        cls,
        log_id: str,
        response: str = "",
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        tokens_input: int = 0,
        tokens_output: int = 0
    ):
        """
        记录从 Agent 接收的回复
        
        更新之前 outgoing 记录，添加 response 和元数据
        
        Args:
            log_id: 对应的 outgoing 日志ID
            response: Agent 回复内容
            success: 是否成功
            error_message: 错误信息
            duration_ms: 耗时（毫秒）
            tokens_input: 输入token数
            tokens_output: 输出token数
        """
        response_truncated = response[:10000] if response else ""
        
        # Phase 1: 使用锁保护写入，避免 SQLite 并发冲突
        async with cls._write_lock:
            async with get_session() as session:
                # 查询日志
                log = await session.get(AgentLog, log_id)
                if log:
                    log.response = response_truncated
                    
                    # 更新元数据
                    meta = log.meta_info or {}
                    meta.update({
                        "success": success,
                        "duration_ms": duration_ms,
                        "tokens_input": tokens_input,
                        "tokens_output": tokens_output,
                    })
                    if error_message:
                        meta["error_message"] = error_message
                    
                    log.meta_info = meta
                    await session.flush()
    
    @classmethod
    async def get_logs(
        cls,
        agent_id: Optional[str] = None,
        interaction_type: Optional[str] = None,
        direction: Optional[str] = None,
        task_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        查询日志列表
        
        Args:
            agent_id: 按Agent筛选
            interaction_type: 按交互类型筛选
            direction: 按方向筛选 (outgoing/incoming)
            task_id: 按任务ID筛选
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            包含 logs, total, limit, offset 的字典
        """
        async with get_session() as session:
            from sqlalchemy import select, and_
            
            # 构建查询
            query = select(AgentLog)
            
            # 应用筛选条件
            conditions = []
            if agent_id:
                conditions.append(AgentLog.agent_id == agent_id)
            if interaction_type:
                conditions.append(AgentLog.interaction_type == interaction_type)
            if direction:
                conditions.append(AgentLog.direction == direction)
            if task_id:
                conditions.append(AgentLog.task_id == task_id)
            if start_time:
                conditions.append(AgentLog.created_at >= start_time)
            if end_time:
                conditions.append(AgentLog.created_at <= end_time)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # 统计总数
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # 排序和分页
            query = query.order_by(desc(AgentLog.created_at))
            query = query.offset(offset).limit(limit)
            
            result = await session.execute(query)
            logs = result.scalars().all()
            
            return {
                "logs": [log.to_dict() for log in logs],
                "total": total,
                "limit": limit,
                "offset": offset
            }
    
    @classmethod
    async def get_log_by_id(cls, log_id: str) -> Optional[Dict]:
        """获取单条日志详情"""
        async with get_session() as session:
            log = await session.get(AgentLog, log_id)
            return log.to_dict() if log else None
    
    @classmethod
    async def get_stats(
        cls,
        agent_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            agent_id: 按Agent筛选
            hours: 统计最近多少小时
            
        Returns:
            统计信息字典
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with get_session() as session:
            from sqlalchemy import select, func, and_
            
            # 基础查询条件
            conditions = [AgentLog.created_at >= start_time]
            if agent_id:
                conditions.append(AgentLog.agent_id == agent_id)
            
            # 总交互数
            total_query = select(func.count()).where(and_(*conditions))
            total_result = await session.execute(total_query)
            total = total_result.scalar()
            
            # 成功数
            success_query = select(func.count()).where(
                and_(*conditions, AgentLog.metadata["success"].as_boolean().is_(True))
            )
            success_result = await session.execute(success_query)
            success_count = success_result.scalar()
            
            # 涉及Agent列表
            agents_query = select(
                AgentLog.agent_id,
                AgentLog.agent_name,
                func.count().label("count")
            ).where(and_(*conditions)).group_by(
                AgentLog.agent_id,
                AgentLog.agent_name
            ).order_by(desc("count"))
            
            agents_result = await session.execute(agents_query)
            agents = [
                {
                    "agent_id": row.agent_id,
                    "agent_name": row.agent_name,
                    "count": row.count
                }
                for row in agents_result
            ]
            
            # 交互类型分布
            types_query = select(
                AgentLog.interaction_type,
                func.count().label("count")
            ).where(and_(*conditions)).group_by(
                AgentLog.interaction_type
            )
            
            types_result = await session.execute(types_query)
            types = {
                row.interaction_type: row.count
                for row in types_result
            }
            
            # 计算成功率
            success_rate = (success_count / total * 100) if total > 0 else 0
            
            return {
                "total_logs": total,
                "success_count": success_count,
                "success_rate": round(success_rate, 2),
                "agents": agents,
                "types": types,
                "hours": hours
            }
    
    @classmethod
    async def clear_logs(cls, agent_id: Optional[str] = None) -> int:
        """
        清空日志
        
        Args:
            agent_id: 如果指定，只清空该Agent的日志
            
        Returns:
            清空的日志数量
        """
        async with get_session() as session:
            from sqlalchemy import delete
            
            query = delete(AgentLog)
            if agent_id:
                query = query.where(AgentLog.agent_id == agent_id)
            
            result = await session.execute(query)
            await session.flush()
            
            # 清空内存缓存
            if agent_id:
                cls._memory_cache = [
                    log for log in cls._memory_cache
                    if log.get("agent_id") != agent_id
                ]
            else:
                cls._memory_cache = []
            
            return result.rowcount
