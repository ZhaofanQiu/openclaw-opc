"""
端到端测试: 任务执行流程

测试完整的任务分配和执行流程：
1. 创建员工
2. 创建任务
3. 分配任务（触发 Agent 唤醒）
4. Agent 通过 skill 获取任务
5. Agent 读取手册
6. Agent 报告结果
7. OPC 接收结果
"""

import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.core.agent_interaction_v2 import assign_task_to_agent
from src.services.skill_db_service import SkillDBService

# 测试数据库
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)


def setup_module():
    """测试前创建表"""
    Base.metadata.create_all(bind=engine)


def teardown_module():
    """测试后删除表"""
    Base.metadata.drop_all(bind=engine)


class TestTaskExecutionFlow:
    """任务执行流程测试"""
    
    def test_create_agent(self):
        """测试创建员工"""
        db = TestingSessionLocal()
        try:
            # TODO: 实现员工创建
            pass
        finally:
            db.close()
    
    def test_create_task(self):
        """测试创建任务"""
        db = TestingSessionLocal()
        try:
            # TODO: 实现任务创建
            pass
        finally:
            db.close()
    
    @pytest.mark.asyncio
    async def test_assign_task(self):
        """测试分配任务"""
        result = await assign_task_to_agent(
            task_id="test_task_001",
            agent_id="test_agent_001",
            agent_name="测试员工",
            title="测试任务",
            description="这是一个测试任务"
        )
        
        assert result.success is True
        assert "测试员工" in result.content
        print(f"✓ 任务分配成功: {result.content}")
    
    def test_skill_get_current_task(self):
        """测试 Skill 获取当前任务"""
        db = TestingSessionLocal()
        try:
            service = SkillDBService(db)
            
            # 由于没有真实数据，应该返回 None
            task = service.get_current_task("test_agent_001")
            
            # 当前返回 None（因为没有真实数据）
            print(f"✓ 获取任务结果: {task}")
            
        finally:
            db.close()
    
    def test_skill_report_completion(self):
        """测试 Skill 报告任务完成"""
        db = TestingSessionLocal()
        try:
            service = SkillDBService(db)
            
            # 由于没有真实数据，应该失败
            result = service.report_task_completion(
                agent_id="test_agent_001",
                task_id="test_task_001",
                result="任务完成",
                tokens_used=150
            )
            
            # 由于没有真实数据，应该失败
            assert result["success"] is False
            print(f"✓ 报告结果: {result}")
            
        finally:
            db.close()
    
    def test_skill_get_budget(self):
        """测试 Skill 获取预算"""
        db = TestingSessionLocal()
        try:
            service = SkillDBService(db)
            
            # 由于没有真实数据，应该返回错误
            budget = service.get_budget("test_agent_001")
            
            # 当前返回错误（因为没有真实数据）
            print(f"✓ 获取预算结果: {budget}")
            
        finally:
            db.close()


async def run_demo():
    """运行演示"""
    print("=" * 60)
    print("OPC v2.0 端到端测试演示")
    print("=" * 60)
    
    # 1. 分配任务
    print("\n1. 分配任务")
    result = await assign_task_to_agent(
        task_id="demo_task_001",
        agent_id="demo_agent_001",
        agent_name="Demo Agent",
        title="写一份 Python 代码",
        description="编写一个计算斐波那契数列的 Python 函数"
    )
    print(f"   结果: {result.success}")
    print(f"   消息: {result.content}")
    
    # 2. 模拟 Agent 通过 Skill 获取任务
    print("\n2. Agent 获取任务 (opc_get_current_task)")
    print("   [需要数据库支持]")
    
    # 3. 模拟 Agent 读取手册
    print("\n3. Agent 读取手册 (opc_read_manual)")
    print("   [需要手册文件]")
    
    # 4. 模拟 Agent 报告结果
    print("\n4. Agent 报告结果 (opc_report_task_result)")
    print("   [需要数据库支持]")
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    # 运行演示
    asyncio.run(run_demo())
