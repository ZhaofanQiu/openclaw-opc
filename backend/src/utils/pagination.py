"""
Pagination Utilities
分页工具类
"""

from typing import Generic, TypeVar, List, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session, Query

T = TypeVar('T')


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False
            }
        }


def paginate_query(
    db: Session,
    query: Query,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    对SQLAlchemy查询进行分页
    
    Args:
        db: 数据库会话
        query: SQLAlchemy查询对象
        page: 页码（从1开始）
        page_size: 每页数量
    
    Returns:
        分页结果字典
    """
    # 确保页码有效
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:  # 最大100条
        page_size = 100
    
    # 获取总数
    total = query.count()
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size
    
    # 确保页码不超过总页数
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    # 执行分页查询
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


def paginate_list(items: List[T], page: int = 1, page_size: int = 20) -> PaginatedResponse[T]:
    """
    对Python列表进行分页
    
    Args:
        items: 数据列表
        page: 页码（从1开始）
        page_size: 每页数量
    
    Returns:
        分页响应对象
    """
    # 确保参数有效
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    
    total = len(items)
    total_pages = (total + page_size - 1) // page_size
    
    # 确保页码有效
    if page > total_pages:
        page = max(1, total_pages)
    
    # 切片
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = items[start:end]
    
    return PaginatedResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


class PaginationHelper:
    """分页助手类 - 用于路由处理"""
    
    @staticmethod
    def get_pagination_params(
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100
    ) -> Dict[str, int]:
        """
        获取并验证分页参数
        
        Args:
            page: 页码
            page_size: 每页数量
            max_page_size: 最大每页数量
        
        Returns:
            验证后的分页参数字典
        """
        # 验证页码
        if page < 1:
            page = 1
        
        # 验证每页数量
        if page_size < 1:
            page_size = 20
        if page_size > max_page_size:
            page_size = max_page_size
        
        return {
            "page": page,
            "page_size": page_size
        }
    
    @staticmethod
    def create_response(
        items: List[Any],
        total: int,
        page: int,
        page_size: int
    ) -> Dict[str, Any]:
        """
        创建分页响应
        
        Args:
            items: 当前页数据
            total: 总数量
            page: 当前页码
            page_size: 每页数量
        
        Returns:
            分页响应字典
        """
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "items": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
