"""
opc-database: Partner 消息仓库

提供 PartnerMessage 的 CRUD 操作

作者: OpenClaw OPC Team
创建日期: 2026-03-27
版本: 0.4.4
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.partner_message import PartnerMessage


class PartnerMessageRepository(BaseRepository[PartnerMessage]):
    """
    Partner 消息仓库

    提供 Partner 聊天记录的增删改查操作
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, PartnerMessage)

    async def get_recent_messages(
        self,
        partner_id: str,
        limit: int = 20,
        before_id: Optional[str] = None
    ) -> List[PartnerMessage]:
        """
        获取最近聊天记录

        Args:
            partner_id: Partner 员工ID
            limit: 返回消息数量上限
            before_id: 分页游标（可选，用于加载更早的消息）

        Returns:
            消息列表（按时间升序）
        """
        query = (
            select(PartnerMessage)
            .where(PartnerMessage.partner_id == partner_id)
            .order_by(desc(PartnerMessage.created_at))
            .limit(limit)
        )

        if before_id:
            # 获取游标消息的时间
            cursor_msg = await self.get_by_id(before_id)
            if cursor_msg:
                query = query.where(
                    PartnerMessage.created_at < cursor_msg.created_at
                )

        result = await self.session.execute(query)
        # 返回升序列表（旧消息在前）
        return list(reversed(result.scalars().all()))

    async def get_messages_by_date_range(
        self,
        partner_id: str,
        start: datetime,
        end: datetime
    ) -> List[PartnerMessage]:
        """
        按时间范围查询消息

        Args:
            partner_id: Partner 员工ID
            start: 开始时间
            end: 结束时间

        Returns:
            消息列表（按时间升序）
        """
        result = await self.session.execute(
            select(PartnerMessage)
            .where(
                and_(
                    PartnerMessage.partner_id == partner_id,
                    PartnerMessage.created_at >= start,
                    PartnerMessage.created_at <= end
                )
            )
            .order_by(PartnerMessage.created_at)
        )
        return list(result.scalars().all())

    async def get_messages_with_actions(
        self,
        partner_id: str,
        limit: int = 50
    ) -> List[PartnerMessage]:
        """
        获取包含操作指令的消息

        Args:
            partner_id: Partner 员工ID
            limit: 返回数量上限

        Returns:
            包含操作的消息列表
        """
        result = await self.session.execute(
            select(PartnerMessage)
            .where(
                and_(
                    PartnerMessage.partner_id == partner_id,
                    PartnerMessage.has_action == True
                )
            )
            .order_by(desc(PartnerMessage.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def clear_history_before(
        self,
        partner_id: str,
        before: datetime
    ) -> int:
        """
        清理历史记录

        Args:
            partner_id: Partner 员工ID
            before: 清理此时间之前的消息

        Returns:
            删除的消息数量
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(PartnerMessage)
            .where(
                and_(
                    PartnerMessage.partner_id == partner_id,
                    PartnerMessage.created_at < before
                )
            )
        )
        await self.session.flush()
        return result.rowcount

    async def get_message_count(
        self,
        partner_id: str
    ) -> int:
        """
        获取消息总数

        Args:
            partner_id: Partner 员工ID

        Returns:
            消息数量
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count())
            .select_from(PartnerMessage)
            .where(PartnerMessage.partner_id == partner_id)
        )
        return result.scalar_one()

    async def search_messages(
        self,
        partner_id: str,
        keyword: str,
        limit: int = 20
    ) -> List[PartnerMessage]:
        """
        搜索消息内容

        Args:
            partner_id: Partner 员工ID
            keyword: 搜索关键词
            limit: 返回数量上限

        Returns:
            匹配的消息列表
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(PartnerMessage)
            .where(
                and_(
                    PartnerMessage.partner_id == partner_id,
                    PartnerMessage.content.ilike(f"%{keyword}%")
                )
            )
            .order_by(desc(PartnerMessage.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
