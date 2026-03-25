"""
opc-core: 工作流模板服务测试 (v0.4.2-P2)

测试 WorkflowTemplateService

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from opc_database.models import WorkflowTemplate, WorkflowTemplateRating
from opc_core.services import (
    TemplateCreateRequest,
    WorkflowTemplateService,
)


@pytest.fixture
def mock_template_repo():
    """模拟模板仓库"""
    return AsyncMock()


@pytest.fixture
def mock_rating_repo():
    """模拟评分仓库"""
    return AsyncMock()


@pytest.fixture
def mock_workflow_service():
    """模拟工作流服务"""
    return AsyncMock()


@pytest.fixture
def template_service(mock_template_repo, mock_rating_repo, mock_workflow_service):
    """模板服务实例"""
    return WorkflowTemplateService(
        mock_template_repo,
        mock_rating_repo,
        mock_workflow_service,
    )


class TestWorkflowTemplateService:
    """工作流模板服务测试"""
    
    @pytest.mark.asyncio
    async def test_create_template(self, template_service, mock_template_repo):
        """测试创建模板"""
        # 设置模拟返回值
        mock_template_repo.create.return_value = WorkflowTemplate(
            id="tmpl-test001",
            name="测试模板",
            description="描述",
            category="general",
        )
        
        request = TemplateCreateRequest(
            name="测试模板",
            description="描述",
            steps_config=[{"employee_id": "emp-1", "title": "步骤1"}],
            category="general",
            tags=["test"],
            created_by="user-1",
            is_public=True,
        )
        
        result = await template_service.create_template(request)
        
        assert result.name == "测试模板"
        assert result.category == "general"
        mock_template_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_template(self, template_service, mock_template_repo):
        """测试获取模板"""
        mock_template_repo.get_by_id.return_value = WorkflowTemplate(
            id="tmpl-test001",
            name="测试模板",
        )
        
        result = await template_service.get_template("tmpl-test001")
        
        assert result is not None
        assert result.name == "测试模板"
        mock_template_repo.get_by_id.assert_called_once_with("tmpl-test001")
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self, template_service, mock_template_repo):
        """测试获取不存在的模板"""
        mock_template_repo.get_by_id.return_value = None
        
        result = await template_service.get_template("tmpl-notfound")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_template(self, template_service, mock_template_repo):
        """测试更新模板"""
        template = WorkflowTemplate(
            id="tmpl-test001",
            name="原名称",
            description="原描述",
            created_by="user-1",
        )
        
        mock_template_repo.get_by_id.return_value = template
        mock_template_repo.update.return_value = template
        
        result = await template_service.update_template(
            "tmpl-test001",
            {"name": "新名称"},
            "user-1"
        )
        
        assert result is not None
        assert result.name == "新名称"
    
    @pytest.mark.asyncio
    async def test_update_template_permission_error(self, template_service, mock_template_repo):
        """测试更新模板权限错误"""
        template = WorkflowTemplate(
            id="tmpl-test001",
            name="测试",
            created_by="user-1",
        )
        
        mock_template_repo.get_by_id.return_value = template
        
        with pytest.raises(PermissionError):
            await template_service.update_template(
                "tmpl-test001",
                {"name": "新名称"},
                "user-2"  # 不同的用户
            )
    
    @pytest.mark.asyncio
    async def test_delete_template(self, template_service, mock_template_repo):
        """测试删除模板"""
        template = WorkflowTemplate(
            id="tmpl-test001",
            name="测试",
            created_by="user-1",
        )
        
        mock_template_repo.get_by_id.return_value = template
        mock_template_repo.get_forked_templates.return_value = []
        
        result = await template_service.delete_template("tmpl-test001", "user-1")
        
        assert result is True
        mock_template_repo.delete.assert_called_once_with(template)
    
    @pytest.mark.asyncio
    async def test_list_templates(self, template_service, mock_template_repo):
        """测试获取模板列表"""
        mock_template_repo.get_public_templates.return_value = [
            WorkflowTemplate(id="tmpl-1", name="模板1"),
        ]
        mock_template_repo.get_system_templates.return_value = [
            WorkflowTemplate(id="tmpl-2", name="模板2"),
        ]
        mock_template_repo.get_categories.return_value = ["general", "dev"]
        
        result = await template_service.list_templates()
        
        assert result.total >= 0
        assert isinstance(result.categories, list)
    
    @pytest.mark.asyncio
    async def test_search_templates(self, template_service, mock_template_repo):
        """测试搜索模板"""
        mock_template_repo.search.return_value = [
            WorkflowTemplate(id="tmpl-1", name="测试模板"),
        ]
        
        result = await template_service.search_templates("测试")
        
        assert len(result) >= 0
        mock_template_repo.search.assert_called_once_with("测试", 50)
    
    @pytest.mark.asyncio
    async def test_create_workflow_from_template(self, template_service, mock_template_repo, mock_workflow_service):
        """测试从模板创建工作流"""
        template = WorkflowTemplate(
            id="tmpl-test001",
            name="测试模板",
            description="描述",
            steps_config=json.dumps([
                {"employee_id": "emp-1", "title": "步骤1", "estimated_cost": 0.5},
            ]),
        )
        
        mock_template_repo.get_by_id.return_value = template
        mock_workflow_service.create_workflow.return_value = {
            "workflow_id": "wf-001",
            "status": "created",
        }
        
        result = await template_service.create_workflow_from_template(
            "tmpl-test001",
            {"input": "data"},
            "user-1",
        )
        
        assert result["workflow_id"] == "wf-001"
        mock_template_repo.update.assert_called_once()  # 更新使用次数
    
    @pytest.mark.asyncio
    async def test_fork_template(self, template_service, mock_template_repo):
        """测试Fork模板"""
        parent = WorkflowTemplate(
            id="tmpl-parent",
            name="父模板",
            description="父描述",
            steps_config=json.dumps([{"title": "步骤1"}]),
            category="general",
            tags='["test"]',
        )
        
        mock_template_repo.get_by_id.return_value = parent
        mock_template_repo.create.return_value = WorkflowTemplate(
            id="tmpl-child",
            name="Fork模板",
            parent_template_id="tmpl-parent",
        )
        
        result = await template_service.fork_template(
            "tmpl-parent",
            "Fork模板",
            "user-1",
        )
        
        assert result.parent_template_id == "tmpl-parent"
        mock_template_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_template_new(self, template_service, mock_template_repo, mock_rating_repo):
        """测试新评分"""
        template = WorkflowTemplate(
            id="tmpl-test001",
            name="测试",
            avg_rating=0,
            rating_count=0,
        )
        
        mock_template_repo.get_by_id.return_value = template
        mock_rating_repo.get_user_rating.return_value = None
        mock_rating_repo.get_rating_stats.return_value = {"count": 1, "average": 5.0}
        
        await template_service.rate_template("tmpl-test001", "user-1", 5, "非常好")
        
        mock_rating_repo.create.assert_called_once()
        mock_template_repo.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_template_update(self, template_service, mock_template_repo, mock_rating_repo):
        """测试更新评分"""
        template = WorkflowTemplate(
            id="tmpl-test001",
            name="测试",
            avg_rating=4.0,
            rating_count=10,
        )
        
        existing_rating = WorkflowTemplateRating(
            id="rate-001",
            template_id="tmpl-test001",
            user_id="user-1",
            rating=4,
        )
        
        mock_template_repo.get_by_id.return_value = template
        mock_rating_repo.get_user_rating.return_value = existing_rating
        mock_rating_repo.get_rating_stats.return_value = {"count": 10, "average": 4.1}
        
        await template_service.rate_template("tmpl-test001", "user-1", 5, "更新了")
        
        mock_rating_repo.update.assert_called_once()
        assert existing_rating.rating == 5
    
    @pytest.mark.asyncio
    async def test_rate_template_invalid_rating(self, template_service):
        """测试无效评分值"""
        with pytest.raises(ValueError):
            await template_service.rate_template("tmpl-001", "user-1", 6, "评论")
        
        with pytest.raises(ValueError):
            await template_service.rate_template("tmpl-001", "user-1", 0, "评论")
    
    @pytest.mark.asyncio
    async def test_get_template_ratings(self, template_service, mock_rating_repo):
        """测试获取模板评分列表"""
        mock_rating_repo.get_by_template.return_value = [
            WorkflowTemplateRating(
                id="rate-1",
                template_id="tmpl-001",
                user_id="user-1",
                rating=5,
                comment="很好",
            )
        ]
        mock_rating_repo.get_rating_stats.return_value = {"count": 1, "average": 5.0}
        
        result = await template_service.get_template_ratings("tmpl-001")
        
        assert len(result["ratings"]) == 1
        assert result["stats"]["average"] == 5.0
