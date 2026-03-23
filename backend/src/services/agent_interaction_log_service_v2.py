"""
Agent Interaction Log Service (v2.0)

Agent交互日志服务 - 简化版
记录所有与OpenClaw Agent的交互
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AgentInteractionLog:
    """Agent交互日志模型（内存存储）"""
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        interaction_type: str,  # 'message', 'cli', 'api', 'callback'
        direction: str,  # 'outgoing', 'incoming'
        content: str,
        response: str = None,
        metadata: Dict = None,
        duration_ms: int = None,
        success: bool = True,
        error_message: str = None
    ):
        self.id = str(uuid.uuid4())[:12]
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.interaction_type = interaction_type
        self.direction = direction
        self.content = content
        self.response = response
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.duration_ms = duration_ms
        self.success = success
        self.error_message = error_message
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "interaction_type": self.interaction_type,
            "direction": self.direction,
            "content": self.content,
            "response": self.response,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
        }


class AgentInteractionLogService:
    """Agent交互日志服务（简化版 - 内存存储）"""
    
    # 内存缓存（最近2000条）
    _logs: List[AgentInteractionLog] = []
    _max_logs = 2000
    
    @classmethod
    def log(cls,
            agent_id: str,
            agent_name: str,
            interaction_type: str,
            direction: str,
            content: str,
            response: str = None,
            metadata: Dict = None,
            duration_ms: int = None,
            success: bool = True,
            error_message: str = None) -> AgentInteractionLog:
        """记录一次交互"""
        log = AgentInteractionLog(
            agent_id=agent_id,
            agent_name=agent_name,
            interaction_type=interaction_type,
            direction=direction,
            content=content,
            response=response,
            metadata=metadata,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message
        )
        
        # 添加到内存缓存（新日志在前）
        cls._logs.insert(0, log)
        
        # 限制内存缓存大小
        if len(cls._logs) > cls._max_logs:
            cls._logs = cls._logs[:cls._max_logs]
        
        # WebSocket 推送
        try:
            import asyncio
            from core.websocket_manager import notify_log_created
            # 尝试获取事件循环，如果失败则忽略
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(notify_log_created(log.to_dict()))
            except RuntimeError:
                pass  # 没有运行的事件循环，跳过
        except Exception:
            pass  # WebSocket 失败不影响主流程
        
        # 记录到系统日志
        logger.info(
            f"Agent交互: {agent_name} ({agent_id}) - {interaction_type} {direction} - "
            f"{'成功' if success else '失败'} - {duration_ms or 0}ms"
        )
        
        return log
    
    @classmethod
    def get_logs(cls,
                 agent_id: Optional[str] = None,
                 interaction_type: Optional[str] = None,
                 direction: Optional[str] = None,
                 limit: int = 100,
                 offset: int = 0) -> Dict:
        """获取日志列表"""
        # 筛选
        logs = cls._logs
        
        if agent_id:
            logs = [log for log in logs if log.agent_id == agent_id]
        
        if interaction_type:
            logs = [log for log in logs if log.interaction_type == interaction_type]
        
        if direction:
            logs = [log for log in logs if log.direction == direction]
        
        total = len(logs)
        
        # 分页
        logs = logs[offset:offset + limit]
        
        return {
            "logs": [log.to_dict() for log in logs],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    @classmethod
    def get_stats(cls) -> Dict:
        """获取统计信息"""
        if not cls._logs:
            return {
                "total_logs": 0,
                "agents": [],
                "types": {},
                "success_rate": 0
            }
        
        # 统计Agent
        agent_map = {}
        for log in cls._logs:
            if log.agent_id not in agent_map:
                agent_map[log.agent_id] = {
                    "agent_id": log.agent_id,
                    "agent_name": log.agent_name,
                    "count": 0
                }
            agent_map[log.agent_id]["count"] += 1
        
        # 统计类型
        types = {}
        for log in cls._logs:
            types[log.interaction_type] = types.get(log.interaction_type, 0) + 1
        
        # 计算成功率
        success_count = sum(1 for log in cls._logs if log.success)
        success_rate = round(success_count / len(cls._logs) * 100, 1)
        
        return {
            "total_logs": len(cls._logs),
            "agents": list(agent_map.values()),
            "types": types,
            "success_rate": success_rate
        }
    
    @classmethod
    def clear_logs(cls, agent_id: Optional[str] = None) -> int:
        """清空日志"""
        if agent_id:
            # 只清空指定Agent的日志
            original_count = len(cls._logs)
            cls._logs = [log for log in cls._logs if log.agent_id != agent_id]
            cleared = original_count - len(cls._logs)
        else:
            # 清空所有
            cleared = len(cls._logs)
            cls._logs = []
        
        logger.info(f"Cleared {cleared} agent interaction logs")
        return cleared
    
    @classmethod
    def get_log_by_id(cls, log_id: str) -> Optional[AgentInteractionLog]:
        """根据ID获取日志"""
        for log in cls._logs:
            if log.id == log_id:
                return log
        return None


# 便捷函数
def log_agent_interaction(agent_id: str,
                          agent_name: str,
                          interaction_type: str,
                          direction: str,
                          content: str,
                          response: str = None,
                          metadata: Dict = None,
                          duration_ms: int = None,
                          success: bool = True,
                          error_message: str = None) -> AgentInteractionLog:
    """记录Agent交互"""
    return AgentInteractionLogService.log(
        agent_id=agent_id,
        agent_name=agent_name,
        interaction_type=interaction_type,
        direction=direction,
        content=content,
        response=response,
        metadata=metadata,
        duration_ms=duration_ms,
        success=success,
        error_message=error_message
    )