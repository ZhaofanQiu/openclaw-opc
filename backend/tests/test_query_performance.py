"""
Database Query Performance Tests
数据库查询性能测试
"""

import time
import pytest
from sqlalchemy.orm import Session
from typing import Callable

from src.database import SessionLocal
from src.services.workflow_detail_service import WorkflowDetailService
from src.services.optimized_workflow_query_service import OptimizedWorkflowQueryService


def benchmark_query(func: Callable, *args, **kwargs) -> tuple:
    """
    基准测试函数
    
    Returns:
        (执行时间ms, 结果)
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000  # 转换为毫秒
    return elapsed, result


class TestWorkflowQueryPerformance:
    """工作流查询性能测试"""
    
    @pytest.fixture
    def db(self) -> Session:
        """数据库会话fixture"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def workflow_id(self) -> str:
        """测试工作流ID - 需要在测试数据库中存在"""
        return "test_workflow_001"  # 替换为实际ID
    
    @pytest.fixture
    def agent_id(self) -> str:
        """测试员工ID"""
        return "test_agent_001"  # 替换为实际ID
    
    def test_workflow_detail_performance(self, db: Session, workflow_id: str, agent_id: str):
        """测试工作流详情查询性能对比"""
        
        # 旧服务
        old_service = WorkflowDetailService(db)
        old_time, old_result = benchmark_query(
            old_service.get_workflow_detail, workflow_id, agent_id
        )
        
        # 新服务
        new_service = OptimizedWorkflowQueryService(db)
        new_time, new_result = benchmark_query(
            new_service.get_workflow_detail_optimized, workflow_id, agent_id
        )
        
        # 验证结果一致性
        assert old_result["workflow"]["id"] == new_result["workflow"]["id"]
        assert len(old_result["steps"]) == len(new_result["steps"])
        
        # 性能提升断言
        speedup = old_time / new_time if new_time > 0 else float('inf')
        print(f"\n工作流详情查询性能:")
        print(f"  旧服务: {old_time:.2f}ms")
        print(f"  新服务: {new_time:.2f}ms")
        print(f"  提升: {speedup:.2f}x")
        
        # 新服务应该至少快2倍
        assert speedup >= 2.0, f"性能提升不足: {speedup:.2f}x"
    
    def test_workflow_list_pagination_performance(self, db: Session, agent_id: str):
        """测试工作流列表分页性能"""
        
        service = OptimizedWorkflowQueryService(db)
        
        # 测试不同页码
        for page in [1, 5, 10]:
            elapsed, result = benchmark_query(
                service.get_workflow_list_optimized,
                agent_id=agent_id,
                page=page,
                page_size=20
            )
            
            print(f"\n工作流列表分页 (page={page}):")
            print(f"  耗时: {elapsed:.2f}ms")
            print(f"  返回: {len(result['workflows'])} 条")
            
            # 应该快速返回
            assert elapsed < 100, f"分页查询太慢: {elapsed:.2f}ms"
    
    def test_agent_pending_workflows_performance(self, db: Session, agent_id: str):
        """测试员工待办工作流查询性能"""
        
        service = OptimizedWorkflowQueryService(db)
        
        elapsed, result = benchmark_query(
            service.get_agent_pending_workflows_optimized, agent_id
        )
        
        print(f"\n员工待办工作流查询:")
        print(f"  耗时: {elapsed:.2f}ms")
        print(f"  返回: {len(result)} 条")
        
        # 应该快速返回
        assert elapsed < 50, f"待办查询太慢: {elapsed:.2f}ms"


class TestDatabaseIndexPerformance:
    """数据库索引性能测试"""
    
    @pytest.fixture
    def db(self) -> Session:
        """数据库会话fixture"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def test_index_usage(self, db: Session):
        """测试索引是否被使用"""
        from sqlalchemy import text
        
        # 测试工作流步骤查询是否使用索引
        query = "SELECT * FROM workflow_steps WHERE workflow_id = 'test'"
        
        # SQLite EXPLAIN QUERY PLAN
        result = db.execute(text(f"EXPLAIN QUERY PLAN {query}"))
        plan = result.fetchall()
        
        plan_str = " ".join(str(row) for row in plan)
        print(f"\n查询计划: {plan_str}")
        
        # 验证使用了索引而不是全表扫描
        assert "USING INDEX" in plan_str or "INDEX" in plan_str, \
            f"查询未使用索引: {plan_str}"
    
    def test_query_count_reduction(self, db: Session):
        """测试查询次数减少"""
        from sqlalchemy import event
        
        query_count = [0]
        
        def count_queries(conn, cursor, statement, parameters, context, executemany):
            query_count[0] += 1
        
        # 监听查询事件
        event.listen(db.bind, "before_cursor_execute", count_queries)
        
        try:
            # 旧服务
            old_service = WorkflowDetailService(db)
            query_count[0] = 0
            old_service.get_workflow_detail("test", "test")
            old_count = query_count[0]
            
            # 新服务
            new_service = OptimizedWorkflowQueryService(db)
            query_count[0] = 0
            new_service.get_workflow_detail_optimized("test", "test")
            new_count = query_count[0]
            
            print(f"\n查询次数对比:")
            print(f"  旧服务: {old_count} 次查询")
            print(f"  新服务: {new_count} 次查询")
            print(f"  减少: {old_count - new_count} 次 ({(1 - new_count/old_count)*100:.1f}%)")
            
            # 新服务查询次数应该显著减少
            assert new_count < old_count * 0.5, \
                f"查询次数减少不足: {old_count} -> {new_count}"
        
        finally:
            event.remove(db.bind, "before_cursor_execute", count_queries)


# 手动运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
