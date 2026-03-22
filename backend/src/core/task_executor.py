"""
任务执行器 (重构后)

整合三维度控制，实现真正的 Agent 任务执行。
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from src.core.agent_interaction import AgentInteraction, AgentContext, interact_with_agent
from src.core.bridge_skill import get_bridge_skill, get_bridge_skill_summary
from src.core.manual_application import build_task_context, ManualApplication
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

class TaskExecutor:
    """
    任务执行器
    
    核心职责:
    1. 构建三维度控制上下文
    2. 调用 Agent 执行任务
    3. 处理执行结果
    4. 更新任务状态
    
    三维度控制:
    1. Bridge Skill - 基本行为规范
    2. Manual - 任务/岗位/公司手册
    3. Message - 本次任务描述
    """
    
    def __init__(self):
        self.interaction = AgentInteraction()
        self.manual_app = ManualApplication()
        self.bridge_skill = get_bridge_skill()
        self.bridge_skill_summary = get_bridge_skill_summary()
    
    async def execute(self,
                     task_id: str,
                     agent_id: str,
                     agent_name: str,
                     task_title: str,
                     task_description: str,
                     session_id: Optional[str] = None) -> TaskExecutionResult:
        """
        执行任务
        
        这是核心方法，整合三维度控制执行 Agent 任务。
        """
        try:
            logger.info(f"Executing task {task_id} with agent {agent_id}")
            
            # 1. 构建上下文
            context = await self._build_context(
                task_id=task_id,
                agent_id=agent_id,
                agent_name=agent_name,
                task_title=task_title,
                task_description=task_description
            )
            
            # 2. 发送任务给 Agent
            result = await self._send_to_agent(context, session_id)
            
            if not result.success:
                return TaskExecutionResult(
                    success=False,
                    output="",
                    tokens_used=result.tokens_used,
                    error=result.error
                )
            
            # 3. 解析结果
            parsed = self._parse_result(result.content)
            
            return TaskExecutionResult(
                success=True,
                output=parsed.get("output", result.content),
                tokens_used=result.tokens_used,
                needs_rework=parsed.get("needs_rework", False),
                rework_reason=parsed.get("rework_reason")
            )
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return TaskExecutionResult(
                success=False,
                output="",
                tokens_used=0,
                error=str(e)
            )
    
    async def _build_context(self,
                            task_id: str,
                            agent_id: str,
                            agent_name: str,
                            task_title: str,
                            task_description: str) -> AgentContext:
        """构建执行上下文"""
        
        # 获取手册路径
        manuals = self.manual_app.get_manuals_for_task(task_id, agent_id)
        
        return AgentContext(
            agent_id=agent_id,
            agent_name=agent_name,
            task_id=task_id,
            task_title=task_title,
            task_description=task_description,
            bridge_skill=self.bridge_skill_summary,
            task_manual_path=manuals.get("task", ""),
            position_manual_path=manuals.get("position", ""),
            company_manual_path=manuals.get("company", "")
        )
    
    async def _send_to_agent(self,
                           context: AgentContext,
                           session_id: Optional[str]) -> Any:
        """
        发送任务给 Agent
        
        这里实际调用 OpenClaw API
        """
        # 读取手册内容
        manuals_content = {}
        if context.task_manual_path:
            manuals_content["任务手册"] = self.manual_app.read_manual(context.task_manual_path) or ""
        if context.position_manual_path:
            manuals_content["岗位手册"] = self.manual_app.read_manual(context.position_manual_path) or ""
        if context.company_manual_path:
            manuals_content["公司手册"] = self.manual_app.read_manual(context.company_manual_path) or ""
        
        # 构建消息
        message_parts = []
        
        # Bridge Skill (行为规范)
        message_parts.append(f"# 行为规范\n{context.bridge_skill}")
        
        # 手册 (经验沉淀)
        for name, content in manuals_content.items():
            if content:
                message_parts.append(f"# {name}\n{content}")
        
        # 任务描述 (本次目标)
        message_parts.append(f"# 任务\n## {context.task_title}\n\n{context.task_description}")
        
        full_message = "\n\n---\n\n".join(message_parts)
        
        logger.info(f"Sending task to agent {context.agent_id}")
        
        # 实际调用
        # TODO: 替换为真实的 OpenClaw API 调用
        # result = await interact_with_agent(
        #     agent_id=context.agent_id,
        #     message=full_message,
        #     bridge_skill=context.bridge_skill,
        #     manuals=manuals_content
        # )
        
        # 临时模拟
        return type('Result', (), {
            'success': True,
            'content': f'任务 {context.task_id} 已执行完成',
            'tokens_used': 100
        })()
    
    def _parse_result(self, content: str) -> Dict[str, Any]:
        """解析 Agent 返回的结果"""
        # TODO: 实现更智能的结果解析
        return {
            "output": content,
            "needs_rework": False,
            "rework_reason": None
        }
    
    async def wake_up_agent(self, 
                          agent_id: str,
                          agent_name: str,
                          position_level: int) -> TaskExecutionResult:
        """唤醒 Agent"""
        message = f"""# OPC 员工唤醒

你是 {agent_name}，是 OpenClaw OPC 的一名员工。

## 基本规范
{self.bridge_skill_summary}

## 当前状态
你现在处于待命状态，等待任务分配。

请回复确认你已准备就绪，并简单介绍你自己。
"""
        
        # TODO: 实际调用 OpenClaw
        logger.info(f"Waking up agent {agent_id}")
        
        return TaskExecutionResult(
            success=True,
            output=f"Agent {agent_name} 已唤醒",
            tokens_used=50
        )

# ============ 便捷函数 ============

async def execute_task(task_id: str,
                      agent_id: str,
                      agent_name: str,
                      task_title: str,
                      task_description: str) -> TaskExecutionResult:
    """便捷函数: 执行任务"""
    executor = TaskExecutor()
    return await executor.execute(
        task_id=task_id,
        agent_id=agent_id,
        agent_name=agent_name,
        task_title=task_title,
        task_description=task_description
    )
