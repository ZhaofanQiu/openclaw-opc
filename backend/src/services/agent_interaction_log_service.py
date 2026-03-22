"""
Agent Interaction Log Service
Agent交互日志服务 - 记录所有与OpenClaw Agent的交互
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AgentInteractionLog:
    """Agent交互日志模型（内存+数据库混合存储）"""
    
    def __init__(
        self,
        id: str,
        agent_id: str,
        agent_name: str,
        interaction_type: str,  # 'message', 'cli', 'api', 'session_send'
        direction: str,  # 'outgoing', 'incoming'
        content: str,
        response: str = None,
        metadata: Dict = None,
        timestamp: datetime = None,
        duration_ms: int = None,
        success: bool = True,
        error_message: str = None
    ):
        self.id = id or str(uuid.uuid4())[:12]
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.interaction_type = interaction_type
        self.direction = direction
        self.content = content
        self.response = response
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.utcnow()
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
    """Agent交互日志服务"""
    
    # 内存缓存（最近1000条）
    _memory_logs: List[AgentInteractionLog] = []
    _max_memory_logs = 1000
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def log_interaction(
        self,
        agent_id: str,
        agent_name: str,
        interaction_type: str,
        direction: str,
        content: str,
        response: str = None,
        metadata: Dict = None,
        duration_ms: int = None,
        success: bool = True,
        error_message: str = None
    ) -> AgentInteractionLog:
        """
        记录一次交互
        
        Args:
            agent_id: Agent ID
            agent_name: Agent名称
            interaction_type: 交互类型 (message/cli/api/session_send)
            direction: 方向 (outgoing/incoming)
            content: 发送/接收的内容
            response: 回复内容（outgoing时）
            metadata: 额外元数据
            duration_ms: 耗时（毫秒）
            success: 是否成功
            error_message: 错误信息
        """
        log = AgentInteractionLog(
            id=str(uuid.uuid4())[:12],
            agent_id=agent_id,
            agent_name=agent_name,
            interaction_type=interaction_type,
            direction=direction,
            content=content,
            response=response,
            metadata=metadata or {},
            duration_ms=duration_ms,
            success=success,
            error_message=error_message
        )
        
        # 添加到内存缓存
        AgentInteractionLogService._memory_logs.insert(0, log)
        
        # 限制内存缓存大小
        if len(AgentInteractionLogService._memory_logs) > self._max_memory_logs:
            AgentInteractionLogService._memory_logs = \
                AgentInteractionLogService._memory_logs[:self._max_memory_logs]
        
        # 记录到系统日志
        logger.info(
            "agent_interaction",
            log_id=log.id,
            agent_id=agent_id,
            agent_name=agent_name,
            interaction_type=interaction_type,
            direction=direction,
            content_preview=content[:200] if content else None,
            success=success,
            duration_ms=duration_ms
        )
        
        return log
    
    def get_logs(
        self,
        agent_id: Optional[str] = None,
        interaction_type: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        获取交互日志
        
        Args:
            agent_id: 筛选特定Agent
            interaction_type: 筛选交互类型
            direction: 筛选方向
            limit: 返回数量
            offset: 偏移量
        """
        logs = AgentInteractionLogService._memory_logs
        
        # 应用筛选
        if agent_id:
            logs = [log for log in logs if log.agent_id == agent_id]
        
        if interaction_type:
            logs = [log for log in logs if log.interaction_type == interaction_type]
        
        if direction:
            logs = [log for log in logs if log.direction == direction]
        
        # 分页
        total = len(logs)
        paginated_logs = logs[offset:offset + limit]
        
        return {
            "logs": [log.to_dict() for log in paginated_logs],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def clear_logs(self, agent_id: Optional[str] = None) -> int:
        """
        清空日志
        
        Args:
            agent_id: 如果指定，只清空该Agent的日志
        
        Returns:
            清空的日志数量
        """
        if agent_id:
            original_count = len(AgentInteractionLogService._memory_logs)
            AgentInteractionLogService._memory_logs = [
                log for log in AgentInteractionLogService._memory_logs
                if log.agent_id != agent_id
            ]
            cleared_count = original_count - len(AgentInteractionLogService._memory_logs)
        else:
            cleared_count = len(AgentInteractionLogService._memory_logs)
            AgentInteractionLogService._memory_logs = []
        
        logger.info(
            "agent_logs_cleared",
            agent_id=agent_id,
            cleared_count=cleared_count
        )
        
        return cleared_count
    
    def get_stats(self) -> Dict:
        """获取日志统计信息"""
        logs = AgentInteractionLogService._memory_logs
        
        if not logs:
            return {
                "total_logs": 0,
                "agents": [],
                "types": {},
                "success_rate": 0
            }
        
        # Agent统计
        agent_ids = set(log.agent_id for log in logs)
        agents = []
        for agent_id in agent_ids:
            agent_logs = [log for log in logs if log.agent_id == agent_id]
            agents.append({
                "agent_id": agent_id,
                "agent_name": agent_logs[0].agent_name if agent_logs else "Unknown",
                "log_count": len(agent_logs)
            })
        
        # 类型统计
        types = {}
        for log in logs:
            types[log.interaction_type] = types.get(log.interaction_type, 0) + 1
        
        # 成功率
        success_count = sum(1 for log in logs if log.success)
        success_rate = (success_count / len(logs)) * 100 if logs else 0
        
        return {
            "total_logs": len(logs),
            "agents": sorted(agents, key=lambda x: x["log_count"], reverse=True),
            "types": types,
            "success_rate": round(success_rate, 2)
        }
    
    def export_logs(self, format: str = "json") -> str:
        """导出日志"""
        logs = [log.to_dict() for log in AgentInteractionLogService._memory_logs]
        
        if format == "json":
            return json.dumps(logs, indent=2, ensure_ascii=False)
        elif format == "txt":
            lines = []
            for log in logs:
                lines.append(f"[{log['timestamp']}] {log['agent_name']} ({log['interaction_type']})")
                lines.append(f"  Direction: {log['direction']}")
                lines.append(f"  Content: {log['content'][:500]}")
                if log['response']:
                    lines.append(f"  Response: {log['response'][:500]}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


# 装饰器用于自动记录交互
def log_agent_interaction(
    interaction_type: str = "api",
    log_request: bool = True,
    log_response: bool = True
):
    """
    装饰器 - 自动记录Agent交互
    
    用法:
        @log_agent_interaction(interaction_type="session_send")
        def send_message_to_agent(agent_id: str, message: str):
            # ...
            return response
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 获取agent_id（假设第一个参数或kwargs中）
            agent_id = kwargs.get('agent_id') or (args[0] if args else 'unknown')
            
            # 记录请求
            content = str(args[1]) if len(args) > 1 else str(kwargs)
            
            service = AgentInteractionLogService()
            start_time = datetime.utcnow()
            
            try:
                # 执行原函数
                response = func(*args, **kwargs)
                
                # 计算耗时
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # 记录成功
                service.log_interaction(
                    agent_id=agent_id,
                    agent_name=agent_id,  # 可以从其他地方获取名称
                    interaction_type=interaction_type,
                    direction="outgoing",
                    content=content[:2000] if log_request else "[请求已省略]",
                    response=str(response)[:2000] if log_response and response else None,
                    duration_ms=duration_ms,
                    success=True
                )
                
                return response
            
            except Exception as e:
                # 计算耗时
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # 记录失败
                service.log_interaction(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    interaction_type=interaction_type,
                    direction="outgoing",
                    content=content[:2000] if log_request else "[请求已省略]",
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e)
                )
                
                raise
        
        return wrapper
    return decorator
