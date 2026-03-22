"""
任务执行器 (v2 - Skill 集成版)

整合三维度控制，使用 opc-bridge skill 实现 Agent 交互。
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from src.core.agent_interaction_v2 import AgentInteractionV2, TaskContext, assign_task_to_agent
from src.core.skill_definition import get_skill_definition
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class TaskExecutionResult:
    """任务执行结果"""
    success: bool
    output: str
    tokens_used: int
    error: Optional[str] = None
    needs_rework: bool = False
    rework_reason: Optional[str] = None

class TaskExecutorV2:
    """
    任务执行器 (v2)
    
    执行流程:
    1. OPC 通过 sessions_send 发送任务消息给 Agent
    2. Agent 通过 opc-bridge skill 获取更多信息
       - opc_get_current_task() - 获取任务详情
       - opc_read_manual() - 读取手册
       - opc_db_read() - 读取数据
    3. Agent 执行任务
    4. Agent 通过 opc_report_task_result() 报告结果
    5. OPC 接收结果，更新状态
    
    三维度控制:
    - Bridge Skill: 提供 opc_* 方法
    - Manual: Agent 主动读取
    - Message: OPC 发送的任务描述
    """
    
    def __init__(self):
        self.interaction = AgentInteractionV2()
        self.skill_def = get_skill_definition()
    
    async def execute(self,
                     task_id: str,
                     agent_id: str,
                     agent_name: str,
                     title: str,
                     description: str) -> TaskExecutionResult:
        """
        执行任务
        
        这是核心方法，通过 opc-bridge skill 实现 Agent 任务执行。
        """
        try:
            logger.info(f"Executing task {task_id} with agent {agent_id}")
            
            # 1. 分配任务给 Agent
            assign_result = await assign_task_to_agent(
                task_id=task_id,
                agent_id=agent_id,
                agent_name=agent_name,
                title=title,
                description=description
            )
            
            if not assign_result.success:
                return TaskExecutionResult(
                    success=False,
                    output="",
                    tokens_used=0,
                    error=f"Failed to assign task: {assign_result.error}"
                )
            
            # 2. 等待 Agent 完成（通过 opc_report_task_result）
            # 这里是一个异步等待过程
            # Agent 通过 skill 调用 opc_report_task_result() 来报告完成
            
            logger.info(f"Waiting for agent {agent_id} to complete task {task_id}")
            
            # TODO: 实现等待机制
            # 可以通过以下方式：
            # a. 轮询数据库检查任务状态
            # b. WebSocket 实时推送
            # c. 消息队列
            
            return TaskExecutionResult(
                success=True,
                output=f"任务已分配给 {agent_name}，等待执行完成",
                tokens_used=assign_result.tokens_used
            )
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return TaskExecutionResult(
                success=False,
                output="",
                tokens_used=0,
                error=str(e)
            )
    
    async def handle_task_report(self,
                                task_id: str,
                                agent_id: str,
                                result: str,
                                tokens_used: int) -> Dict[str, Any]:
        """
        处理 Agent 通过 skill 报告的任务结果
        
        这个方法由 opc-bridge skill 的 opc_report_task_result() 调用
        """
        try:
            logger.info(f"Received task report from {agent_id} for {task_id}")
            
            # TODO: 
            # 1. 验证 Agent 身份
            # 2. 更新任务状态
            # 3. 计算成本
            # 4. 更新预算
            # 5. 触发后续流程（如下一步任务）
            
            cost = tokens_used / 100  # 假设 100 tokens = 1 OC币
            
            return {
                "success": True,
                "cost": cost,
                "remaining_budget": 900,  # TODO: 从数据库查询
                "message": "任务结果已记录"
            }
            
        except Exception as e:
            logger.error(f"Failed to handle task report: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# ============ 便捷函数 ============

async def execute_task(task_id: str,
                      agent_id: str,
                      agent_name: str,
                      title: str,
                      description: str) -> TaskExecutionResult:
    """便捷函数: 执行任务"""
    executor = TaskExecutorV2()
    return await executor.execute(
        task_id=task_id,
        agent_id=agent_id,
        agent_name=agent_name,
        title=title,
        description=description
    )

def get_skill_for_install() -> str:
    """获取用于安装的 skill 定义"""
    return get_skill_definition()
