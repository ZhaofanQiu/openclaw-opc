"""
opc-database: 基础仓库

提供所有Repository的基类

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    基础Repository类

    提供通用的CRUD操作

    Attributes:
        session: 数据库会话
        model: 模型类
    """

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """
        根据ID获取记录

        Args:
            id: 记录ID

        Returns:
            记录实例或None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """
        获取所有记录（分页）

        Args:
            limit: 每页数量
            offset: 偏移量

        Returns:
            记录列表
        """
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, instance: ModelType) -> ModelType:
        """
        创建记录

        Args:
            instance: 模型实例

        Returns:
            创建的实例
        """
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelType) -> ModelType:
        """
        更新记录

        Args:
            instance: 模型实例

        Returns:
            更新后的实例
        """
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        """
        删除记录

        Args:
            instance: 模型实例
        """
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self) -> int:
        """
        获取记录总数

        Returns:
            记录数量
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
