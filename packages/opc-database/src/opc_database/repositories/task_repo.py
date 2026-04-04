"""
opc-database: 任务仓库

提供任务相关的数据访问操作

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#TaskRepository
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task, TaskMessage, TaskStatus
from .base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """
    任务数据仓库

    封装所有任务相关的数据库操作
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Task)

    async def get_by_employee(
        self, employee_id: str, status: Optional[TaskStatus] = None, limit: int = 100
    ) -> List[Task]:
        """
        获取员工的任务列表

        Args:
            employee_id: 员工ID
            status: 可选的状态筛选
            limit: 数量限制

        Returns:
            任务列表
        """
        query = select(Task).where(Task.assigned_to == employee_id)

        if status:
            query = query.where(Task.status == status.value)

        query = query.order_by(desc(Task.created_at)).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(self, status: TaskStatus, limit: int = 100) -> List[Task]:
        """
        根据状态获取任务

        Args:
            status: 任务状态
            limit: 数量限制

        Returns:
            任务列表
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.status == status.value)
            .order_by(desc(Task.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_tasks(self, limit: int = 100) -> List[Task]:
        """获取待分配任务"""
        return await self.get_by_status(TaskStatus.PENDING, limit)

    async def get_in_progress_tasks(self, limit: int = 100) -> List[Task]:
        """获取进行中任务"""
        return await self.get_by_status(TaskStatus.IN_PROGRESS, limit)

    async def assign_task(
        self, task_id: str, employee_id: str, assigned_by: Optional[str] = None
    ) -> Optional[Task]:
        """
        分配任务给员工

        Args:
            task_id: 任务ID
            employee_id: 员工ID
            assigned_by: 分配者ID

        Returns:
            更新后的任务或None
        """
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.assigned_to = employee_id
        task.assigned_by = assigned_by
        task.status = TaskStatus.ASSIGNED.value
        task.assigned_at = datetime.utcnow()

        await self.session.flush()
        return task

    async def start_task(
        self, task_id: str, session_key: Optional[str] = None
    ) -> Optional[Task]:
        """
        开始执行任务

        Args:
            task_id: 任务ID
            session_key: OpenClaw会话ID

        Returns:
            更新后的任务或None
        """
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.status = TaskStatus.IN_PROGRESS.value
        task.started_at = datetime.utcnow()
        if session_key:
            task.session_key = session_key

        await self.session.flush()
        return task

    async def complete_task(
        self,
        task_id: str,
        result: str,
        actual_cost: float = 0.0,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> Optional[Task]:
        """
        完成任务

        Args:
            task_id: 任务ID
            result: 执行结果
            actual_cost: 实际成本
            tokens_input: 输入token数
            tokens_output: 输出token数

        Returns:
            更新后的任务或None
        """
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.status = TaskStatus.COMPLETED.value
        task.result = result
        task.actual_cost = actual_cost
        task.tokens_input = tokens_input
        task.tokens_output = tokens_output
        task.completed_at = datetime.utcnow()

        await self.session.flush()
        return task

    async def fail_task(self, task_id: str, reason: str) -> Optional[Task]:
        """
        标记任务失败

        Args:
            task_id: 任务ID
            reason: 失败原因

        Returns:
            更新后的任务或None
        """
        task = await self.get_by_id(task_id)
        if not task:
            return None

        task.status = TaskStatus.FAILED.value
        task.result = f"失败: {reason}"
        task.completed_at = datetime.utcnow()

        await self.session.flush()
        return task

    async def request_rework(self, task_id: str, feedback: str) -> Optional[Task]:
        """
        请求返工

        Args:
            task_id: 任务ID
            feedback: 返工反馈

        Returns:
            更新后的任务或None
        """
        task = await self.get_by_id(task_id)
        if not task:
            return None

        if not task.can_rework():
            return None

        task.rework_count += 1
        task.status = TaskStatus.IN_PROGRESS.value
        task.feedback = feedback
        # 清除完成时间，重新执行
        task.completed_at = None

        await self.session.flush()
        return task

    async def get_task_stats(self) -> dict:
        """
        获取任务统计

        Returns:
            统计字典，包含前端期望的字段
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(
                func.count().label("total"),
                func.sum(Task.estimated_cost).label("total_estimated"),
                func.sum(Task.actual_cost).label("total_actual"),
            )
        )
        row = result.one()

        # 按状态统计
        status_result = await self.session.execute(
            select(Task.status, func.count().label("count")).group_by(Task.status)
        )
        status_counts = {row.status: row.count for row in status_result.all()}

        # 兼容前端期望的字段名
        total_tasks = row.total or 0
        completed_tasks = status_counts.get(TaskStatus.COMPLETED.value, 0)
        failed_tasks = status_counts.get(TaskStatus.FAILED.value, 0)
        in_progress_tasks = status_counts.get(TaskStatus.IN_PROGRESS.value, 0)
        pending_tasks = status_counts.get(TaskStatus.PENDING.value, 0)

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "pending_tasks": pending_tasks,
            "total_estimated_cost": float(row.total_estimated or 0),
            "total_actual_cost": float(row.total_actual or 0),
            "status_counts": status_counts,
            # 计算完成率
            "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
        }

    # ========== v0.4.2 新增：工作流相关方法 ==========

    async def get_by_workflow(self, workflow_id: str) -> List[Task]:
        """
        获取工作流的所有任务

        Args:
            workflow_id: 工作流ID

        Returns:
            按 step_index 排序的任务列表
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.workflow_id == workflow_id)
            .order_by(Task.step_index)
        )
        return list(result.scalars().all())

    async def get_workflow_head(self, workflow_id: str) -> Optional[Task]:
        """
        获取工作流的第一个任务

        Args:
            workflow_id: 工作流ID

        Returns:
            第一步任务或None
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.workflow_id == workflow_id)
            .where(Task.step_index == 0)
        )
        return result.scalar_one_or_none()

    async def get_next_task(self, task_id: str) -> Optional[Task]:
        """
        获取下一个任务

        Args:
            task_id: 当前任务ID

        Returns:
            下一个任务或None
        """
        # 通过 next_task_id 查找
        current = await self.get_by_id(task_id)
        if current and current.next_task_id:
            return await self.get_by_id(current.next_task_id)
        return None

    async def get_prev_task(self, task_id: str) -> Optional[Task]:
        """
        获取上一个任务

        Args:
            task_id: 当前任务ID

        Returns:
            上一个任务或None
        """
        # 通过 depends_on 查找
        current = await self.get_by_id(task_id)
        if current and current.depends_on:
            return await self.get_by_id(current.depends_on)
        return None

    async def update_task_chain(
        self, task_id: str, next_task_id: Optional[str] = None, depends_on: Optional[str] = None
    ) -> Optional[Task]:
        """
        更新任务链关系

        Args:
            task_id: 任务ID
            next_task_id: 下一个任务ID
            depends_on: 依赖的上一个任务ID

        Returns:
            更新后的任务
        """
        task = await self.get_by_id(task_id)
        if not task:
            return None

        if next_task_id is not None:
            task.next_task_id = next_task_id
        if depends_on is not None:
            task.depends_on = depends_on

        await self.session.flush()
        return task

    async def get_reworkable_tasks(self, workflow_id: str, from_step: int) -> List[Task]:
        """
        获取可以返工的目标任务（上游步骤）

        Args:
            workflow_id: 工作流ID
            from_step: 当前步骤索引

        Returns:
            可以返工的上游任务列表
        """
        result = await self.session.execute(
            select(Task)
            .where(Task.workflow_id == workflow_id)
            .where(Task.step_index < from_step)
            .where(Task.can_rework())
            .order_by(Task.step_index)
        )
        return list(result.scalars().all())

    async def get_workflow_tasks_in_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Task]:
        """
        获取指定时间范围内的工作流任务

        Args:
            start_date: 开始时间（包含），可选
            end_date: 结束时间（包含），可选

        Returns:
            工作流任务列表（workflow_id 不为空）
        """
        from sqlalchemy import and_

        query = select(Task).where(Task.workflow_id.isnot(None))

        conditions = []
        if start_date is not None:
            conditions.append(Task.created_at >= start_date)
        if end_date is not None:
            conditions.append(Task.created_at <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return list(result.scalars().all())


class TaskMessageRepository(BaseRepository[TaskMessage]):
    """任务消息仓库"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, TaskMessage)

    async def get_by_task(
        self, task_id: str, limit: int = 100, offset: int = 0
    ) -> List[TaskMessage]:
        """
        获取任务的消息列表

        Args:
            task_id: 任务ID
            limit: 数量限制
            offset: 偏移量

        Returns:
            消息列表
        """
        result = await self.session.execute(
            select(TaskMessage)
            .where(TaskMessage.task_id == task_id)
            .order_by(TaskMessage.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        task_id: str,
        sender_type: str,
        content: str,
        sender_id: Optional[str] = None,
        message_type: str = "text",
    ) -> TaskMessage:
        """
        添加消息

        Args:
            task_id: 任务ID
            sender_type: 发送者类型 (user/agent/system)
            content: 消息内容
            sender_id: 发送者ID
            message_type: 消息类型

        Returns:
            创建的消息
        """
        import uuid

        message = TaskMessage(
            id=str(uuid.uuid4()),
            task_id=task_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
        )

        return await self.create(message)
