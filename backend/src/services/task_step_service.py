"""
TaskStep Service - 任务步骤核心服务
处理任务分配、聊天消息、完成/返工流转
"""

import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from models import TaskStep, TaskStepMessage, TaskStepStatus, TaskMessageType, Task, TaskStatus
from services.notification_service import NotificationService
from utils.logging_config import get_logger
from utils.current_user import get_user_id_safe

logger = get_logger(__name__)


class TaskStepService:
    """任务步骤服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification = NotificationService(db)
    
    # ============ 查询方法 ============
    
    def get_step(self, step_id: str) -> Optional[TaskStep]:
        """获取任务步骤"""
        return self.db.query(TaskStep).filter(TaskStep.id == step_id).first()
    
    def get_task_steps(self, task_id: str) -> List[TaskStep]:
        """获取任务的所有步骤"""
        return self.db.query(TaskStep).filter(
            TaskStep.task_id == task_id
        ).order_by(TaskStep.step_index).all()
    
    def get_step_messages(self, step_id: str, limit: int = 100) -> List[TaskStepMessage]:
        """获取步骤的聊天记录"""
        return self.db.query(TaskStepMessage).filter(
            TaskStepMessage.step_id == step_id
        ).order_by(TaskStepMessage.created_at).limit(limit).all()
    
    def get_agent_steps(self, agent_id: str, status: Optional[str] = None, limit: int = 50) -> List[TaskStep]:
        """获取员工的任务步骤列表"""
        query = self.db.query(TaskStep).filter(TaskStep.executor_id == agent_id)
        if status:
            query = query.filter(TaskStep.status == status)
        return query.order_by(TaskStep.created_at.desc()).limit(limit).all()
    
    # ============ 创建步骤 ============
    
    def create_step(
        self,
        task_id: str,
        step_index: int,
        step_name: str,
        assigner_id: str,
        assigner_type: str,
        assigner_name: str,
        executor_id: str,
        step_description: str = "",
        input_context: Optional[Dict] = None,
        budget_tokens: int = 1000,
        prev_step_id: Optional[str] = None,
        next_step_id: Optional[str] = None,
    ) -> TaskStep:
        """
        创建任务步骤
        
        Args:
            task_id: 任务ID
            step_index: 步骤序号
            step_name: 步骤名称
            assigner_id: 分配者ID
            assigner_type: "user" | "agent"
            assigner_name: 分配者名称
            executor_id: 执行员工ID
            step_description: 步骤描述
            input_context: 输入上下文（上一步输出+返工反馈）
            budget_tokens: Token预算
            prev_step_id: 上一步ID
            next_step_id: 下一步ID
        """
        step = TaskStep(
            id=f"step_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            step_index=step_index,
            step_name=step_name,
            step_description=step_description,
            assigner_id=assigner_id,
            assigner_type=assigner_type,
            assigner_name=assigner_name,
            executor_id=executor_id,
            status=TaskStepStatus.PENDING.value,
            prev_step_id=prev_step_id,
            next_step_id=next_step_id,
            input_context=json.dumps(input_context) if input_context else "{}",
            budget_tokens=budget_tokens,
        )
        
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        
        logger.info(f"Created task step: {step.id} for task {task_id}")
        return step
    
    # ============ 分配任务 ============
    
    def assign_step(
        self,
        step_id: str,
        assignment_content: str,
        sender_type: str = "user",
        sender_id: str = "system",
        sender_name: str = "系统",
    ) -> TaskStepMessage:
        """
        分配任务给员工（创建第一条消息）
        """
        step = self.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        # 更新步骤状态
        step.status = TaskStepStatus.ASSIGNED.value
        step.assigned_at = datetime.utcnow()
        
        # 创建分配消息
        message = TaskStepMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            step_id=step_id,
            sender_id=sender_id,
            sender_type=sender_type,
            sender_name=sender_name,
            content=assignment_content,
            message_type=TaskMessageType.ASSIGNMENT.value,
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        # 发送通知给员工
        self._notify_agent_new_task(step)
        
        logger.info(f"Assigned step {step_id} to agent {step.executor_id}")
        return message
    
    # ============ 消息交互 ============
    
    def add_message(
        self,
        step_id: str,
        sender_id: str,
        sender_type: str,
        sender_name: str,
        content: str,
        message_type: str = TaskMessageType.REPLY.value,
        attachments: Optional[List[Dict]] = None,
    ) -> TaskStepMessage:
        """
        添加消息到聊天记录
        """
        step = self.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        message = TaskStepMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            step_id=step_id,
            sender_id=sender_id,
            sender_type=sender_type,
            sender_name=sender_name,
            content=content,
            message_type=message_type,
            attachments=json.dumps(attachments) if attachments else "[]",
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        # 发送通知给另一方
        self._notify_new_message(step, message)
        
        return message
    
    def mark_messages_read(self, step_id: str, reader_id: str) -> int:
        """
        标记消息为已读
        """
        messages = self.db.query(TaskStepMessage).filter(
            TaskStepMessage.step_id == step_id,
            TaskStepMessage.sender_id != reader_id,  # 不标记自己发的消息
            TaskStepMessage.is_read == False
        ).all()
        
        count = 0
        for msg in messages:
            msg.is_read = True
            msg.read_at = datetime.utcnow()
            count += 1
        
        self.db.commit()
        return count
    
    def get_unread_count(self, step_id: str, reader_id: str) -> int:
        """获取未读消息数"""
        return self.db.query(TaskStepMessage).filter(
            TaskStepMessage.step_id == step_id,
            TaskStepMessage.sender_id != reader_id,
            TaskStepMessage.is_read == False
        ).count()
    
    # ============ 状态流转 ============
    
    def start_execution(self, step_id: str) -> TaskStep:
        """
        员工开始执行任务
        """
        step = self.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        if step.status not in [TaskStepStatus.ASSIGNED.value, TaskStepStatus.REWORK.value]:
            raise ValueError(f"Cannot start step with status: {step.status}")
        
        step.status = TaskStepStatus.IN_PROGRESS.value
        step.started_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(step)
        
        # 更新任务状态
        self._update_task_status(step.task_id)
        
        logger.info(f"Step {step_id} started execution")
        return step
    
    def complete_step(
        self,
        step_id: str,
        result_summary: str,
        output_result: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        员工完成任务步骤
        
        Returns:
            {"step": TaskStep, "next_step": TaskStep|None, "is_final": bool}
        """
        step = self.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        if step.status != TaskStepStatus.IN_PROGRESS.value:
            raise ValueError(f"Cannot complete step with status: {step.status}")
        
        # 更新步骤状态
        step.status = TaskStepStatus.COMPLETED.value
        step.completed_at = datetime.utcnow()
        step.output_result = json.dumps(output_result) if output_result else "{}"
        
        # 添加完成消息
        message = TaskStepMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            step_id=step_id,
            sender_id=step.executor_id,
            sender_type="agent",
            sender_name="员工",  # 需要查询实际名称
            content=result_summary,
            message_type=TaskMessageType.COMPLETION.value,
        )
        self.db.add(message)
        self.db.commit()
        
        # 检查是否有下一步
        is_final = not step.next_step_id
        next_step = None
        
        if step.next_step_id:
            # 推进到下一步
            next_step = self._advance_to_next_step(step)
        else:
            # 最后一步完成，通知任务发布者
            self._notify_task_completed(step)
        
        self.db.refresh(step)
        
        logger.info(f"Step {step_id} completed, final={is_final}")
        return {
            "step": step,
            "next_step": next_step,
            "is_final": is_final,
        }
    
    def request_rework(
        self,
        step_id: str,
        rework_reason: str,
        suggestions: str = "",
        requester_id: str = "",
        requester_type: str = "agent",
    ) -> TaskStep:
        """
        请求返工（退回上一步）
        """
        step = self.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        if not step.prev_step_id:
            raise ValueError("Cannot rework first step")
        
        prev_step = self.get_step(step.prev_step_id)
        if not prev_step:
            raise ValueError(f"Previous step {step.prev_step_id} not found")
        
        # 检查返工次数
        if prev_step.rework_count >= prev_step.max_rework:
            raise ValueError(f"Max rework count reached for step {prev_step.id}")
        
        # 当前步骤状态变为等待返工
        step.status = TaskStepStatus.WAITING_REWORK.value
        
        # 上一步状态变为返工
        prev_step.status = TaskStepStatus.REWORK.value
        prev_step.rework_count += 1
        
        # 添加返工消息到上一步
        rework_message = f"【返工通知】\n原因：{rework_reason}"
        if suggestions:
            rework_message += f"\n建议：{suggestions}"
        
        message = TaskStepMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            step_id=prev_step.id,
            sender_id=requester_id,
            sender_type=requester_type,
            sender_name="系统" if requester_type == "system" else requester_id[:8],
            content=rework_message,
            message_type=TaskMessageType.REWORK_NOTICE.value,
        )
        self.db.add(message)
        self.db.commit()
        
        # 通知上一步员工
        self._notify_agent_rework(prev_step, rework_reason)
        
        logger.info(f"Step {step_id} requested rework to {prev_step.id}")
        return prev_step
    
    def fail_step(
        self,
        step_id: str,
        fail_reason: str,
        error_details: str = "",
    ) -> TaskStep:
        """
        员工报告任务失败
        """
        step = self.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        step.status = TaskStepStatus.FAILED.value
        step.failed_at = datetime.utcnow()
        
        # 添加失败消息
        content = f"【任务失败】\n原因：{fail_reason}"
        if error_details:
            content += f"\n详情：{error_details}"
        
        message = TaskStepMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            step_id=step_id,
            sender_id=step.executor_id,
            sender_type="agent",
            sender_name="员工",
            content=content,
            message_type=TaskMessageType.FAILURE.value,
        )
        self.db.add(message)
        self.db.commit()
        
        # 通知任务发布者
        self._notify_task_failed(step, fail_reason)
        
        logger.info(f"Step {step_id} marked as failed")
        return step
    
    # ============ 评价结算 ============
    
    def settle_step(
        self,
        step_id: str,
        score: int,
        feedback: str = "",
        settled_by: str = "",
        bonus_tokens: int = 0,
    ) -> TaskStep:
        """
        发布者评价并结算任务
        """
        step = self.get_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")
        
        if step.status != TaskStepStatus.COMPLETED.value:
            raise ValueError(f"Cannot settle step with status: {step.status}")
        
        step.score = max(1, min(5, score))  # 1-5分
        step.feedback = feedback
        step.settled = True
        step.settled_at = datetime.utcnow()
        step.settled_by = settled_by or get_user_id_safe(fallback="system")
        
        # 如果是最终步骤，重置员工状态为 idle
        if not step.next_step_id:
            from models import Agent, AgentStatus, Task, TaskStatus
            
            # 获取执行员工
            agent = self.db.query(Agent).filter(Agent.id == step.executor_id).first()
            if agent:
                agent.status = AgentStatus.IDLE.value
                agent.current_task_id = None
                logger.info(f"Agent {agent.name} status reset to idle")
            
            # 更新任务状态为已完成
            task = self.db.query(Task).filter(Task.id == step.task_id).first()
            if task:
                task.status = TaskStatus.COMPLETED.value
                task.completed_at = datetime.utcnow()
                logger.info(f"Task {task.id} marked as completed")
        
        self.db.commit()
        self.db.refresh(step)
        
        # TODO: 更新员工预算、技能成长
        
        logger.info(f"Step {step_id} settled with score {score}")
        return step
    
    # ============ 内部方法 ============
    
    def _advance_to_next_step(self, current_step: TaskStep) -> Optional[TaskStep]:
        """推进到下一步"""
        if not current_step.next_step_id:
            return None
        
        next_step = self.get_step(current_step.next_step_id)
        if not next_step:
            return None
        
        # 传递输出作为下一步的输入
        output = json.loads(current_step.output_result) if current_step.output_result else {}
        next_step.input_context = json.dumps({
            "previous_output": output,
            "from_step": current_step.id,
            "from_step_name": current_step.step_name,
        })
        
        # 更新下一步状态为已分配
        next_step.status = TaskStepStatus.ASSIGNED.value
        next_step.assigned_at = datetime.utcnow()
        
        self.db.commit()
        
        # 通知下一个员工
        self._notify_agent_new_task(next_step)
        
        return next_step
    
    def _update_task_status(self, task_id: str):
        """更新任务整体状态"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return
        
        steps = self.get_task_steps(task_id)
        if not steps:
            return
        
        # 检查所有步骤状态
        all_completed = all(s.status == TaskStepStatus.COMPLETED.value for s in steps)
        any_failed = any(s.status == TaskStepStatus.FAILED.value for s in steps)
        any_in_progress = any(s.status == TaskStepStatus.IN_PROGRESS.value for s in steps)
        
        if all_completed:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()
        elif any_failed:
            task.status = TaskStatus.FAILED.value
        elif any_in_progress:
            task.status = TaskStatus.IN_PROGRESS.value
        
        self.db.commit()
    
    # ============ 通知方法 ============
    
    def _notify_agent_new_task(self, step: TaskStep):
        """通知员工有新任务"""
        try:
            self.notification.send_notification(
                agent_id=step.executor_id,
                type_="task_assigned",
                title=f"新任务：{step.step_name}",
                message=f"您有一个新任务需要处理",
                task_id=step.task_id,
            )
        except Exception as e:
            logger.error(f"Failed to notify agent {step.executor_id}: {e}")
    
    def _notify_new_message(self, step: TaskStep, message: TaskStepMessage):
        """通知有新消息"""
        try:
            # 确定接收者
            if message.sender_type == "agent":
                # 员工发的消息，通知分配者
                recipient_id = step.assigner_id
            else:
                # 分配者发的消息，通知员工
                recipient_id = step.executor_id
            
            self.notification.send_notification(
                agent_id=recipient_id,
                type_="task_message",
                title=f"任务新消息：{step.step_name}",
                message=message.content[:100] + "..." if len(message.content) > 100 else message.content,
                task_id=step.task_id,
            )
        except Exception as e:
            logger.error(f"Failed to notify new message: {e}")
    
    def _notify_task_completed(self, step: TaskStep):
        """通知任务完成"""
        try:
            self.notification.send_notification(
                agent_id=step.assigner_id,
                type_="task_completed",
                title=f"任务完成：{step.step_name}",
                message=f"步骤 '{step.step_name}' 已完成，请查看并评价",
                task_id=step.task_id,
            )
        except Exception as e:
            logger.error(f"Failed to notify task completion: {e}")
    
    def _notify_task_failed(self, step: TaskStep, reason: str):
        """通知任务失败"""
        try:
            self.notification.send_notification(
                agent_id=step.assigner_id,
                type_="task_failed",
                title=f"任务失败：{step.step_name}",
                message=f"原因：{reason}",
                task_id=step.task_id,
            )
        except Exception as e:
            logger.error(f"Failed to notify task failure: {e}")
    
    def _notify_agent_rework(self, step: TaskStep, reason: str):
        """通知员工返工"""
        try:
            self.notification.send_notification(
                agent_id=step.executor_id,
                type_="task_rework",
                title=f"任务返工：{step.step_name}",
                message=f"原因：{reason}",
                task_id=step.task_id,
            )
        except Exception as e:
            logger.error(f"Failed to notify rework: {e}")
