"""
opc-core: Partner 服务

Partner 员工业务逻辑服务

作者: OpenClaw OPC Team
创建日期: 2026-03-27
版本: 0.4.4
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from opc_database.models import PositionLevel
from opc_database.repositories import EmployeeRepository, PartnerMessageRepository
from opc_openclaw import CLIMessenger


class PartnerNotFoundError(Exception):
    """Partner 员工不存在"""
    pass


class PartnerChatError(Exception):
    """Partner 对话错误"""
    pass


@dataclass
class ChatResult:
    """对话结果"""
    reply: str
    action_executed: Optional[str] = None
    action_result: Optional[Dict[str, Any]] = None


@dataclass
class ParsedAction:
    """解析后的操作指令"""
    action: str
    params: Dict[str, Any]
    is_valid: bool
    raw_text: str


class PartnerService:
    """
    Partner 业务逻辑服务
    
    处理用户与 Partner 员工的对话和智能辅助功能
    """
    
    # Partner 系统提示词
    SYSTEM_PROMPT = """你是 OpenClaw OPC 的 Partner（合伙人），是用户的智能管理助手。

## 你的职责
1. 帮助用户快速完成管理任务
2. 通过对话理解用户需求并执行操作
3. 在辅助决策时提供专业的预算评估

## OC 币与 Token 换算策略
- 1 OC币 ≈ 1000 Tokens（经验换算）
- 任务成本预估参考：
  * 简单任务（研究、查询）：50-100 OC币 ≈ 5万-10万 Tokens
  * 中等任务（分析、写作）：100-300 OC币 ≈ 10万-30万 Tokens
  * 复杂任务（代码开发、多步骤分析）：300-800 OC币 ≈ 30万-80万 Tokens
  * 工作流任务：每个步骤按上述标准累加
- 创建任务时必须给出合理的成本预估

## 操作指令格式
当你需要执行操作时，在回复末尾使用：

---OPC-ACTION---
{
    "action": "create_task",
    "params": {
        "title": "任务标题",
        "description": "任务描述",
        "employee_id": "emp_xxx",
        "estimated_cost": 100
    }
}
---END-ACTION---

支持的操作：
- create_task: 创建任务
- create_workflow: 创建工作流
- write_employee_manual: 编写员工手册
- write_task_manual: 编写任务手册
- update_company_manual: 更新公司手册
- get_company_status: 获取公司状态

## 正常回复
如果只是对话，直接回复即可，无需添加 OPC-ACTION 块。
"""
    
    def __init__(
        self,
        message_repo: PartnerMessageRepository,
        employee_repo: EmployeeRepository,
        messenger: Optional[CLIMessenger] = None
    ):
        self.message_repo = message_repo
        self.employee_repo = employee_repo
        self.messenger = messenger or CLIMessenger()
    
    async def chat(self, user_message: str) -> ChatResult:
        """
        与 Partner 对话
        
        流程：
        1. 查找 Partner 员工
        2. 获取历史记录
        3. 构建消息（系统提示 + 历史 + 用户输入）
        4. 发送给 Agent
        5. 解析回复
        6. 执行操作（如有）
        7. 保存记录
        
        Args:
            user_message: 用户输入消息
            
        Returns:
            ChatResult: 对话结果
            
        Raises:
            PartnerNotFoundError: 未找到 Partner 员工
            PartnerChatError: 对话过程中出错
        """
        # 1. 查找 Partner
        partner = await self._get_partner_employee()
        if not partner:
            raise PartnerNotFoundError("未找到 Partner 员工，请先创建")
        
        if not partner.openclaw_agent_id:
            raise PartnerChatError("Partner 员工未绑定 OpenClaw Agent")
        
        # 2. 获取历史记录
        history = await self.message_repo.get_recent_messages(
            partner.id, limit=10
        )
        
        # 3. 构建完整消息
        full_message = self._build_chat_message(
            history=history,
            user_message=user_message
        )
        
        # 4. 发送给 Agent
        try:
            response = await self.messenger.send(
                agent_id=partner.openclaw_agent_id,
                message=full_message,
                timeout=60
            )
            
            if not response.success:
                raise PartnerChatError(f"Agent 响应失败: {response.error}")
                
        except Exception as e:
            raise PartnerChatError(f"发送消息失败: {str(e)}")
        
        # 5. 保存用户消息
        from opc_database.models import PartnerMessage
        import uuid
        
        user_msg = PartnerMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            partner_id=partner.id,
            role="user",
            content=user_message
        )
        await self.message_repo.create(user_msg)
        
        # 6. 解析回复
        reply_content = response.content
        action = self._parse_action(reply_content)
        
        # 7. 执行操作
        action_result = None
        if action and action.is_valid:
            action_result = await self._execute_action(action)
            # 移除操作指令，只保留可读部分给用户
            reply_content = self._remove_action_block(reply_content)
            reply_content += f"\n\n✅ 已执行: {action.action}"
        
        # 8. 保存 Partner 回复
        partner_msg = PartnerMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            partner_id=partner.id,
            role="partner",
            content=response.content,
            has_action=bool(action) and action.is_valid,
            action_type=action.action if action and action.is_valid else None,
            action_params=action.params if action and action.is_valid else None,
            action_result=action_result
        )
        await self.message_repo.create(partner_msg)
        
        return ChatResult(
            reply=reply_content,
            action_executed=action.action if action and action.is_valid else None,
            action_result=action_result
        )
    
    async def get_chat_history(
        self,
        partner_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取聊天历史
        
        Args:
            partner_id: Partner 员工ID
            limit: 返回消息数量
            
        Returns:
            消息列表
        """
        messages = await self.message_repo.get_recent_messages(
            partner_id=partner_id,
            limit=limit
        )
        return [msg.to_dict() for msg in messages]
    
    async def clear_chat_history(self, partner_id: str) -> int:
        """
        清空聊天历史
        
        Args:
            partner_id: Partner 员工ID
            
        Returns:
            删除的消息数量
        """
        # 删除该 Partner 的所有消息
        from opc_database.models import PartnerMessage
        from sqlalchemy import delete, and_
        
        result = await self.message_repo.session.execute(
            delete(PartnerMessage).where(
                PartnerMessage.partner_id == partner_id
            )
        )
        await self.message_repo.session.flush()
        return result.rowcount
    
    async def _get_partner_employee(self):
        """获取 Partner 员工（position_level = 5）"""
        return await self.employee_repo.get_by_position_level(
            PositionLevel.PARTNER.value
        )
    
    def _build_chat_message(
        self,
        history: List[Any],
        user_message: str
    ) -> str:
        """
        构建聊天消息
        
        Args:
            history: 历史消息列表
            user_message: 用户当前输入
            
        Returns:
            完整的消息文本
        """
        sections = [self.SYSTEM_PROMPT]
        
        # 添加历史记录
        if history:
            sections.append("\n## 对话历史")
            for msg in history:
                role_name = "用户" if msg.role == "user" else "Partner"
                sections.append(f"{role_name}: {msg.content}")
        
        # 添加用户输入
        sections.append(f"\n用户: {user_message}")
        sections.append("\nPartner: ")
        
        return "\n\n".join(sections)
    
    def _parse_action(self, text: str) -> Optional[ParsedAction]:
        """
        解析 OPC-ACTION 块
        
        Args:
            text: Agent 回复文本
            
        Returns:
            ParsedAction 或 None
        """
        pattern = r'---OPC-ACTION---\n(.*?)\n---END-ACTION---'
        match = re.search(pattern, text, re.DOTALL)
        
        if not match:
            return None
        
        try:
            data = json.loads(match.group(1))
            return ParsedAction(
                action=data.get('action', ''),
                params=data.get('params', {}),
                is_valid=True,
                raw_text=match.group(0)
            )
        except json.JSONDecodeError:
            return ParsedAction(
                action='',
                params={},
                is_valid=False,
                raw_text=match.group(0)
            )
    
    def _remove_action_block(self, text: str) -> str:
        """
        移除操作指令块，保留可读内容
        
        Args:
            text: 原始回复文本
            
        Returns:
            清理后的文本
        """
        pattern = r'\n?---OPC-ACTION---.*?---END-ACTION---\n?'
        return re.sub(pattern, '', text, flags=re.DOTALL).strip()
    
    async def _execute_action(self, action: ParsedAction) -> Dict[str, Any]:
        """
        执行操作指令
        
        Args:
            action: 解析后的操作指令
            
        Returns:
            执行结果
        """
        action_type = action.action
        params = action.params
        
        # 目前只支持查询类操作，创建类操作在 Phase 2 实现
        if action_type == 'get_company_status':
            return await self._get_company_status()
        
        # 其他操作返回提示信息
        supported_actions = {
            'create_task': '创建任务功能将在 Phase 2 实现',
            'create_workflow': '创建工作流功能将在 Phase 2 实现',
            'write_employee_manual': '编写手册功能将在 Phase 2 实现',
            'update_company_manual': '更新手册功能将在 Phase 2 实现',
        }
        
        if action_type in supported_actions:
            return {
                'success': False,
                'message': supported_actions[action_type],
                'note': 'Phase 1 仅支持基础对话和查询'
            }
        
        return {
            'success': False,
            'error': f"未知操作: {action_type}"
        }
    
    async def _get_company_status(self) -> Dict[str, Any]:
        """获取公司状态摘要"""
        # 获取员工统计
        employees = await self.employee_repo.get_all(limit=1000)
        
        # 计算统计信息
        total_budget = sum(e.monthly_budget for e in employees)
        total_used = sum(e.used_budget for e in employees)
        
        return {
            'success': True,
            'employees': {
                'total': len(employees),
                'partner': sum(1 for e in employees if e.position_level == 5),
                'active': sum(1 for e in employees if e.status != 'offline')
            },
            'budget': {
                'total': total_budget,
                'used': total_used,
                'remaining': total_budget - total_used
            }
        }
