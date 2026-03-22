"""
Agent 交互核心模块 (v2 - Skill 集成版)

实现双向交互:
1. OPC → Agent: 通过 sessions_send 发送任务
2. Agent → OPC: 通过 opc-bridge skill 调用 API

三维度控制:
- Bridge Skill: 提供基础能力方法
- Manual: 提供经验指导（Agent 主动读取）
- Message: 提供任务描述
"""

import json
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from src.utils.logging_config import get_logger
from src.core.openclaw_client import (
    spawn_agent_session,
    send_to_agent,
    get_agent_response
)

logger = get_logger(__name__)

# ============ 数据模型 ============

@dataclass
class TaskContext:
    """任务上下文"""
    task_id: str
    title: str
    description: str
    agent_id: str
    agent_name: str

@dataclass
class InteractionResult:
    """交互结果"""
    success: bool
    content: str
    tokens_used: int = 0
    error: Optional[str] = None

# ============ 核心交互类 ============

class AgentInteractionV2:
    """
    Agent 交互核心类 (v2)
    
    设计思路:
    1. OPC 通过 sessions_send 发送任务消息
    2. Agent 通过 opc-bridge skill 获取更多信息
    3. Agent 执行后通过 skill 报告结果
    
    三维度控制:
    - Bridge Skill: 提供 opc_* 方法供 Agent 调用
    - Manual: Agent 通过 opc_read_manual() 读取
    - Message: OPC 发送的任务描述
    """
    
    def __init__(self, openclaw_client=None):
        self.openclaw = openclaw_client
        self.opc_core_url = "http://localhost:8080"
        
    def build_task_message(self, context: TaskContext) -> str:
        """
        构建发送给 Agent 的任务消息
        
        这个消息包含：
        1. 身份确认
        2. 任务描述
        3. 可用的 skill 方法提示
        """
        return f"""# 任务分配

## 身份确认
你是 {context.agent_name}，是 OpenClaw OPC 的一名员工。

## 任务信息
- 任务ID: {context.task_id}
- 标题: {context.title}
- 描述: {context.description}

## 执行指南

1. **先阅读手册**（如果需要）:
   ```
   opc_read_manual(manual_type="task", manual_id="{context.task_id}")
   ```

2. **执行任务**:
   根据任务描述和手册规范执行。

3. **报告结果**:
   ```
   opc_report_task_result(
       task_id="{context.task_id}",
       result="任务完成描述",
       tokens_used=实际消耗的token数
   )
   ```

4. **可用工具**:
   - `opc_get_budget()` - 查询预算
   - `opc_db_read(table, query)` - 读取数据
   - `opc_db_write(table, data)` - 写入数据

请开始执行任务。
"""
    
    async def assign_task(self, context: TaskContext) -> InteractionResult:
        """
        分配任务给 Agent
        
        流程:
        1. 构建任务消息
        2. 通过 sessions_spawn 创建会话
        3. 发送任务消息给 Agent
        4. Agent 收到后通过 skill 获取详细信息并执行
        """
        try:
            message = self.build_task_message(context)
            
            # 1. 创建 Agent 会话
            session_key = await spawn_agent_session(
                agent_id=context.agent_id,
                task_id=context.task_id,
                message=message
            )
            
            if not session_key:
                return InteractionResult(
                    success=False,
                    content="",
                    error="Failed to spawn agent session"
                )
            
            logger.info(f"Task {context.task_id} assigned to {context.agent_id}, session: {session_key}")
            
            return InteractionResult(
                success=True,
                content=f"任务已分配给 {context.agent_name} (会话: {session_key})",
                tokens_used=len(message) // 4  # 粗略估计
            )
            
        except Exception as e:
            logger.error(f"Failed to assign task: {e}")
            return InteractionResult(
                success=False,
                content="",
                error=str(e)
            )
    
    async def get_task_result(self, task_id: str, timeout: int = 300) -> InteractionResult:
        """
        获取任务执行结果
        
        Agent 通过 opc_report_task_result() 报告结果后，
        OPC 从数据库或消息队列获取结果
        """
        try:
            # TODO: 从数据库查询任务状态
            # 任务状态由 opc-bridge skill 的 opc_report_task_result 更新
            
            logger.info(f"Waiting for task {task_id} result")
            
            return InteractionResult(
                success=True,
                content="等待 Agent 完成",
                tokens_used=0
            )
            
        except Exception as e:
            logger.error(f"Failed to get task result: {e}")
            return InteractionResult(
                success=False,
                content="",
                error=str(e)
            )

# ============ Skill API 实现 ============

class SkillAPIHandler:
    """
    处理 opc-bridge skill 的 API 调用
    
    Agent 调用 skill 方法时，实际调用这些接口
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
    
    def handle_get_current_task(self, agent_id: str) -> Dict:
        """处理 opc_get_current_task() 调用"""
        # TODO: 从数据库查询分配给该 agent 的任务
        return {
            "has_task": True,
            "task": {
                "id": "task_123",
                "title": "示例任务",
                "description": "任务描述"
            }
        }
    
    def handle_report_task_result(self, 
                                 agent_id: str,
                                 task_id: str,
                                 result: str,
                                 tokens_used: int) -> Dict:
        """处理 opc_report_task_result() 调用"""
        # TODO: 更新任务状态，计算成本，更新预算
        return {
            "success": True,
            "cost": tokens_used / 100,  # 假设 100 tokens = 1 OC币
            "remaining_budget": 900
        }
    
    def handle_read_manual(self,
                          agent_id: str,
                          manual_type: str,
                          manual_id: str) -> Dict:
        """处理 opc_read_manual() 调用"""
        # TODO: 读取手册文件
        return {
            "content": "手册内容",
            "constraints": ["约束1", "约束2"]
        }
    
    def handle_db_read(self,
                      agent_id: str,
                      table: str,
                      query: Dict) -> Dict:
        """处理 opc_db_read() 调用"""
        # TODO: 查询数据库（带权限检查）
        return {
            "data": [],
            "count": 0
        }
    
    def handle_db_write(self,
                       agent_id: str,
                       table: str,
                       data: Dict) -> Dict:
        """处理 opc_db_write() 调用"""
        # TODO: 写入数据库（带权限检查）
        return {
            "success": True,
            "id": "record_123"
        }
    
    def handle_get_budget(self, agent_id: str) -> Dict:
        """处理 opc_get_budget() 调用"""
        # TODO: 查询预算
        return {
            "monthly_budget": 1000,
            "used_budget": 100,
            "remaining_budget": 900,
            "mood": "😊"
        }

# ============ 便捷函数 ============

async def assign_task_to_agent(
    task_id: str,
    agent_id: str,
    agent_name: str,
    title: str,
    description: str
) -> InteractionResult:
    """便捷函数: 分配任务"""
    interaction = AgentInteractionV2()
    context = TaskContext(
        task_id=task_id,
        agent_id=agent_id,
        agent_name=agent_name,
        title=title,
        description=description
    )
    return await interaction.assign_task(context)
