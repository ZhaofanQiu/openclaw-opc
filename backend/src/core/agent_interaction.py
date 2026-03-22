"""
核心 Agent 交互模块 (重构关键)
实现纯文本 + 模板的三维度控制
"""

import json
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# ============ 数据模型 ============

@dataclass
class AgentContext:
    """Agent 执行上下文"""
    agent_id: str
    agent_name: str
    task_id: str
    task_title: str
    task_description: str
    
    # 三维度控制
    bridge_skill: str = ""           # Bridge Skill 内容
    task_manual_path: str = ""       # 任务手册路径
    position_manual_path: str = ""   # 岗位手册路径
    company_manual_path: str = ""    # 公司手册路径
    
    # 数据库接口
    db_read: Optional[Callable] = None
    db_write: Optional[Callable] = None

@dataclass
class InteractionResult:
    """交互结果"""
    success: bool
    content: str
    tokens_used: int = 0
    error: Optional[str] = None

# ============ 文本模板 ============

TEMPLATES = {
    "wake_up": """# OPC 员工唤醒

你是 {agent_name}，是 OpenClaw OPC 的一名员工。

## 基本规范
{bridge_skill}

## 岗位手册
请阅读: {position_manual_path}

## 当前状态
你现在处于待命状态，等待任务分配。

请回复确认你已准备就绪。
""",

    "execute_task": """# 任务执行

## 任务信息
- 任务ID: {task_id}
- 标题: {task_title}
- 描述: {task_description}

## 行为规范 (Bridge Skill)
{bridge_skill}

## 参考资料
- 任务手册: {task_manual_path}
- 岗位手册: {position_manual_path}
- 公司手册: {company_manual_path}

## 执行要求
1. 先阅读相关手册了解规范
2. 根据任务描述执行操作
3. 如需使用工具，请明确说明
4. 完成后报告结果

请开始执行任务。
""",

    "generate_avatar": """# 生成头像

请为 {agent_name} 生成一个像素风格的头像。

要求:
1. 64x64 像素
2. 风格: 办公职场主题
3. 颜色: 暖色调
4. 元素: 体现 {position_level} 级别员工特征

请生成头像并描述设计思路。
""",

    "read_manual": """# 阅读手册

请阅读以下手册并总结要点:

手册路径: {manual_path}

请在后续工作中遵循手册规范。
""",
}

# ============ 核心交互类 ============

class AgentInteraction:
    """
    Agent 交互核心类
    
    设计理念:
    1. 纯文本交互 - 利用 Agent 的理解能力
    2. 模板化 - 不同场景使用不同模板
    3. 三维度控制 - Skill + Manual + Message
    """
    
    def __init__(self, openclaw_client=None):
        self.openclaw = openclaw_client
        self.templates = TEMPLATES
        
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """渲染文本模板"""
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        return template.format(**context)
    
    def build_context(self, 
                     agent_id: str,
                     task_id: str,
                     bridge_skill: str = "",
                     task_manual: str = "",
                     position_manual: str = "",
                     company_manual: str = "") -> str:
        """
        构建三维度控制上下文
        
        返回给 Agent 的完整文本，包含:
        1. Bridge Skill (行为规范)
        2. 手册内容 (经验沉淀)
        3. 任务描述 (本次目标)
        """
        parts = []
        
        # Bridge Skill (行为规范)
        if bridge_skill:
            parts.append(f"## 行为规范\n{bridge_skill}\n")
        
        # 手册 (经验沉淀)
        manuals = []
        if task_manual:
            manuals.append(f"- 任务手册: {task_manual}")
        if position_manual:
            manuals.append(f"- 岗位手册: {position_manual}")
        if company_manual:
            manuals.append(f"- 公司手册: {company_manual}")
        
        if manuals:
            parts.append(f"## 参考手册\n" + "\n".join(manuals) + "\n")
        
        return "\n".join(parts)
    
    async def send_message(self, 
                          session_id: str,
                          message: str) -> InteractionResult:
        """
        发送消息给 Agent
        
        这是核心方法，实际调用 OpenClaw API
        """
        try:
            # TODO: 调用实际的 OpenClaw sessions_send
            # result = await sessions_send(session_id, message)
            
            logger.info(f"Sending message to {session_id}")
            
            return InteractionResult(
                success=True,
                content="消息已发送",
                tokens_used=0
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return InteractionResult(
                success=False,
                content="",
                error=str(e)
            )
    
    async def receive_response(self,
                              session_id: str,
                              timeout: int = 300) -> InteractionResult:
        """
        接收 Agent 响应
        
        轮询或 WebSocket 接收回复
        """
        try:
            # TODO: 实现轮询或 WebSocket 接收
            logger.info(f"Waiting for response from {session_id}")
            
            return InteractionResult(
                success=True,
                content="Agent 响应内容",
                tokens_used=0
            )
        except Exception as e:
            logger.error(f"Failed to receive response: {e}")
            return InteractionResult(
                success=False,
                content="",
                error=str(e)
            )
    
    async def wake_up(self, agent_context: AgentContext) -> InteractionResult:
        """唤醒 Agent"""
        message = self.render_template("wake_up", {
            "agent_name": agent_context.agent_name,
            "bridge_skill": agent_context.bridge_skill,
            "position_manual_path": agent_context.position_manual_path
        })
        
        # TODO: 创建 session 并发送
        return await self.send_message("session_id", message)
    
    async def execute_task(self, 
                          agent_context: AgentContext) -> InteractionResult:
        """执行任务"""
        # 构建三维度上下文
        context = self.build_context(
            agent_id=agent_context.agent_id,
            task_id=agent_context.task_id,
            bridge_skill=agent_context.bridge_skill,
            task_manual=agent_context.task_manual_path,
            position_manual=agent_context.position_manual_path,
            company_manual=agent_context.company_manual_path
        )
        
        # 渲染任务执行模板
        message = self.render_template("execute_task", {
            "task_id": agent_context.task_id,
            "task_title": agent_context.task_title,
            "task_description": agent_context.task_description,
            "bridge_skill": agent_context.bridge_skill,
            "task_manual_path": agent_context.task_manual_path,
            "position_manual_path": agent_context.position_manual_path,
            "company_manual_path": agent_context.company_manual_path
        })
        
        # 发送并接收响应
        result = await self.send_message(agent_context.agent_id, message)
        if result.success:
            return await self.receive_response(agent_context.agent_id)
        
        return result

# ============ 便捷函数 ============

async def interact_with_agent(
    agent_id: str,
    message: str,
    bridge_skill: str = "",
    manuals: Dict[str, str] = None
) -> InteractionResult:
    """
    便捷函数: 与 Agent 交互
    
    这是上层服务调用的主要接口
    """
    interaction = AgentInteraction()
    
    # 构建上下文
    context_parts = []
    if bridge_skill:
        context_parts.append(f"## 行为规范\n{bridge_skill}")
    
    if manuals:
        for name, path in manuals.items():
            context_parts.append(f"## {name}\n{path}")
    
    full_message = "\n\n".join(context_parts) + "\n\n## 任务\n" + message
    
    return await interaction.send_message(agent_id, full_message)
