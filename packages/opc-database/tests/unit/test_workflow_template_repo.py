"""
opc-database: 工作流模板仓库测试 (v0.4.2-P2)

测试 WorkflowTemplateRepository 和 WorkflowTemplateRatingRepository

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

import json
import pytest
from datetime import datetime

from opc_database.models import WorkflowTemplate, WorkflowTemplateRating
from opc_database.repositories import (
    WorkflowTemplateRepository,
    WorkflowTemplateRatingRepository,
)


@pytest.fixture
def sample_template_data():
    """示例模板数据"""
    return {
        "id": "tmpl-test001",
        "name": "测试模板",
        "description": "测试描述",
        "steps_config": '[{"employee_id": "emp-1", "title": "步骤1"}]',
        "category": "general",
        "tags": '["test"]',
        "created_by": "user-1",
        "is_public": True,
    }


@pytest.fixture
def sample_rating_data():
    """示例评分数据"""
    return {
        "id": "rate-test001",
        "template_id": "tmpl-test001",
        "user_id": "user-1",
        "rating": 5,
        "comment": "很好",
    }


class TestWorkflowTemplateRepository:
    """工作流模板仓库测试"""
    
    @pytest.mark.asyncio
    async def test_create_template(self, db_session, sample_template_data):
        """测试创建模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        template = WorkflowTemplate(**sample_template_data)
        result = await repo.create(template)
        
        assert result.id == sample_template_data["id"]
        assert result.name == sample_template_data["name"]
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session, sample_template_data):
        """测试通过ID获取"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 先创建
        template = WorkflowTemplate(**sample_template_data)
        await repo.create(template)
        
        # 再获取
        result = await repo.get_by_id(sample_template_data["id"])
        
        assert result is not None
        assert result.name == sample_template_data["name"]
    
    @pytest.mark.asyncio
    async def test_get_by_category(self, db_session, sample_template_data):
        """测试按分类获取"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建不同分类的模板
        template1 = WorkflowTemplate(**sample_template_data)
        template2 = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "category": "development"}
        )
        
        await repo.create(template1)
        await repo.create(template2)
        
        # 获取 general 分类
        results = await repo.get_by_category("general")
        
        assert len(results) == 1
        assert results[0].category == "general"
    
    @pytest.mark.asyncio
    async def test_get_public_templates(self, db_session, sample_template_data):
        """测试获取公开模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建公开和私有模板
        public_template = WorkflowTemplate(**sample_template_data)
        private_template = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "is_public": False}
        )
        
        await repo.create(public_template)
        await repo.create(private_template)
        
        # 获取公开模板
        results = await repo.get_public_templates()
        
        assert len(results) == 1
        assert results[0].is_public is True
    
    @pytest.mark.asyncio
    async def test_get_user_templates(self, db_session, sample_template_data):
        """测试获取用户模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建不同用户的模板
        user1_template = WorkflowTemplate(**sample_template_data)
        user2_template = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "created_by": "user-2"}
        )
        
        await repo.create(user1_template)
        await repo.create(user2_template)
        
        # 获取 user-1 的模板
        results = await repo.get_user_templates("user-1")
        
        assert len(results) == 1
        assert results[0].created_by == "user-1"
    
    @pytest.mark.asyncio
    async def test_get_system_templates(self, db_session, sample_template_data):
        """测试获取系统模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建系统和用户模板
        system_template = WorkflowTemplate(
            **{**sample_template_data, "is_system": True}
        )
        user_template = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "is_system": False}
        )
        
        await repo.create(system_template)
        await repo.create(user_template)
        
        # 获取系统模板
        results = await repo.get_system_templates()
        
        assert len(results) == 1
        assert results[0].is_system is True
    
    @pytest.mark.asyncio
    async def test_search(self, db_session, sample_template_data):
        """测试搜索功能"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建模板
        template1 = WorkflowTemplate(**sample_template_data)
        template2 = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "name": "另一个模板"}
        )
        
        await repo.create(template1)
        await repo.create(template2)
        
        # 搜索
        results = await repo.search("测试")
        
        assert len(results) >= 1
        assert any("测试" in t.name for t in results)
    
    @pytest.mark.asyncio
    async def test_get_popular(self, db_session, sample_template_data):
        """测试获取热门模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建不同使用次数的模板
        template1 = WorkflowTemplate(
            **{**sample_template_data, "usage_count": 100}
        )
        template2 = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "usage_count": 10}
        )
        
        await repo.create(template1)
        await repo.create(template2)
        
        # 获取热门
        results = await repo.get_popular(limit=10)
        
        # 按使用次数排序，第一个是 100
        if len(results) >= 2:
            assert results[0].usage_count >= results[1].usage_count
    
    @pytest.mark.asyncio
    async def test_get_top_rated(self, db_session, sample_template_data):
        """测试获取高评分模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建不同评分的模板（需要有足够的评分数）
        template1 = WorkflowTemplate(
            **{**sample_template_data, "avg_rating": 5.0, "rating_count": 5}
        )
        template2 = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "avg_rating": 3.0, "rating_count": 5}
        )
        
        await repo.create(template1)
        await repo.create(template2)
        
        # 获取高评分
        results = await repo.get_top_rated(limit=10)
        
        if len(results) >= 2:
            assert results[0].avg_rating >= results[1].avg_rating
    
    @pytest.mark.asyncio
    async def test_get_categories(self, db_session, sample_template_data):
        """测试获取所有分类"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建不同分类的模板
        template1 = WorkflowTemplate(**sample_template_data)
        template2 = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "category": "development"}
        )
        
        await repo.create(template1)
        await repo.create(template2)
        
        # 获取分类
        categories = await repo.get_categories()
        
        assert "general" in categories
        assert "development" in categories
    
    @pytest.mark.asyncio
    async def test_get_all_tags(self, db_session, sample_template_data):
        """测试获取所有标签"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建不同标签的模板
        template1 = WorkflowTemplate(
            **{**sample_template_data, "tags": '["python", "async"]'}
        )
        template2 = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "tags": '["python", "test"]'}
        )
        
        await repo.create(template1)
        await repo.create(template2)
        
        # 获取标签
        tags = await repo.get_all_tags()
        
        assert "python" in tags
        assert "async" in tags
        assert "test" in tags
    
    @pytest.mark.asyncio
    async def test_get_forked_templates(self, db_session, sample_template_data):
        """测试获取Fork的子模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建父模板和子模板
        parent_template = WorkflowTemplate(**sample_template_data)
        child_template = WorkflowTemplate(
            **{**sample_template_data, "id": "tmpl-test002", "parent_template_id": "tmpl-test001"}
        )
        
        await repo.create(parent_template)
        await repo.create(child_template)
        
        # 获取Fork的子模板
        results = await repo.get_forked_templates("tmpl-test001")
        
        assert len(results) == 1
        assert results[0].parent_template_id == "tmpl-test001"
    
    @pytest.mark.asyncio
    async def test_update_template(self, db_session, sample_template_data):
        """测试更新模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建
        template = WorkflowTemplate(**sample_template_data)
        await repo.create(template)
        
        # 更新
        template.name = "更新后的名称"
        template.usage_count = 10
        result = await repo.update(template)
        
        assert result.name == "更新后的名称"
        assert result.usage_count == 10
    
    @pytest.mark.asyncio
    async def test_delete_template(self, db_session, sample_template_data):
        """测试删除模板"""
        repo = WorkflowTemplateRepository(db_session)
        
        # 创建
        template = WorkflowTemplate(**sample_template_data)
        await repo.create(template)
        
        # 删除
        await repo.delete(template)
        
        # 验证删除
        result = await repo.get_by_id(sample_template_data["id"])
        assert result is None


class TestWorkflowTemplateRatingRepository:
    """模板评分仓库测试"""
    
    @pytest.mark.asyncio
    async def test_create_rating(self, db_session, sample_rating_data):
        """测试创建评分"""
        repo = WorkflowTemplateRatingRepository(db_session)
        
        rating = WorkflowTemplateRating(**sample_rating_data)
        result = await repo.create(rating)
        
        assert result.id == sample_rating_data["id"]
        assert result.rating == 5
    
    @pytest.mark.asyncio
    async def test_get_by_template(self, db_session, sample_rating_data):
        """测试获取模板的所有评分"""
        repo = WorkflowTemplateRatingRepository(db_session)
        
        # 创建多个评分
        rating1 = WorkflowTemplateRating(**sample_rating_data)
        rating2 = WorkflowTemplateRating(
            **{**sample_rating_data, "id": "rate-test002", "user_id": "user-2"}
        )
        
        await repo.create(rating1)
        await repo.create(rating2)
        
        # 获取评分
        results = await repo.get_by_template("tmpl-test001")
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_get_by_user(self, db_session, sample_rating_data):
        """测试获取用户的所有评分"""
        repo = WorkflowTemplateRatingRepository(db_session)
        
        # 创建评分
        rating = WorkflowTemplateRating(**sample_rating_data)
        await repo.create(rating)
        
        # 获取用户评分
        results = await repo.get_by_user("user-1")
        
        assert len(results) == 1
        assert results[0].user_id == "user-1"
    
    @pytest.mark.asyncio
    async def test_get_user_rating(self, db_session, sample_rating_data):
        """测试获取用户对特定模板的评分"""
        repo = WorkflowTemplateRatingRepository(db_session)
        
        # 创建评分
        rating = WorkflowTemplateRating(**sample_rating_data)
        await repo.create(rating)
        
        # 获取用户评分
        result = await repo.get_user_rating("tmpl-test001", "user-1")
        
        assert result is not None
        assert result.rating == 5
    
    @pytest.mark.asyncio
    async def test_get_user_rating_not_found(self, db_session, sample_rating_data):
        """测试获取不存在的评分"""
        repo = WorkflowTemplateRatingRepository(db_session)
        
        result = await repo.get_user_rating("tmpl-test001", "user-999")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_rating_stats(self, db_session, sample_rating_data):
        """测试获取评分统计"""
        repo = WorkflowTemplateRatingRepository(db_session)
        
        # 创建多个评分
        rating1 = WorkflowTemplateRating(**sample_rating_data)
        rating2 = WorkflowTemplateRating(
            **{**sample_rating_data, "id": "rate-test002", "user_id": "user-2", "rating": 3}
        )
        
        await repo.create(rating1)
        await repo.create(rating2)
        
        # 获取统计
        stats = await repo.get_rating_stats("tmpl-test001")
        
        assert stats["count"] == 2
        assert stats["average"] == 4.0  # (5 + 3) / 2
