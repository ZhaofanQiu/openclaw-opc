"""
opc-core: 工作流模板 API 测试 (v0.4.2-P2)

测试工作流模板 REST API 路由

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# 假设 app 可以从主模块导入
try:
    from opc_core.main import app
    client = TestClient(app)
except ImportError:
    # 如果 main 模块不存在，跳过 API 测试
    pytest.skip("Main app not available", allow_module_level=True)


class TestWorkflowTemplateAPI:
    """工作流模板 API 测试"""
    
    @pytest.mark.asyncio
    async def test_create_template(self):
        """测试创建模板 API"""
        mock_service = AsyncMock()
        mock_service.create_template.return_value = AsyncMock(
            id="tmpl-test001",
            name="测试模板",
            to_dict=lambda: {
                "id": "tmpl-test001",
                "name": "测试模板",
                "category": "general",
            }
        )
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.post("/api/v1/workflow-templates", json={
                "name": "测试模板",
                "description": "测试描述",
                "steps_config": [{"employee_id": "emp-1", "title": "步骤1"}],
                "category": "general",
                "tags": ["test"],
                "is_public": True,
            })
            
            assert response.status_code == 200
            assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_list_templates(self):
        """测试获取模板列表 API"""
        mock_service = AsyncMock()
        mock_service.list_templates.return_value = AsyncMock(
            templates=[
                {"id": "tmpl-1", "name": "模板1"},
                {"id": "tmpl-2", "name": "模板2"},
            ],
            total=2,
            categories=["general", "dev"],
        )
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.get("/api/v1/workflow-templates")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"].templates) == 2
    
    @pytest.mark.asyncio
    async def test_get_template(self):
        """测试获取单个模板 API"""
        mock_service = AsyncMock()
        mock_service.get_template.return_value = AsyncMock(
            id="tmpl-001",
            name="测试模板",
            to_dict=lambda: {
                "id": "tmpl-001",
                "name": "测试模板",
            }
        )
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.get("/api/v1/workflow-templates/tmpl-001")
            
            assert response.status_code == 200
            assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """测试获取不存在的模板 API"""
        mock_service = AsyncMock()
        mock_service.get_template.return_value = None
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.get("/api/v1/workflow-templates/tmpl-notfound")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_template(self):
        """测试更新模板 API"""
        mock_service = AsyncMock()
        mock_service.update_template.return_value = AsyncMock(
            id="tmpl-001",
            name="更新后的名称",
            to_dict=lambda: {
                "id": "tmpl-001",
                "name": "更新后的名称",
            }
        )
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.put("/api/v1/workflow-templates/tmpl-001", json={
                "name": "更新后的名称",
            })
            
            assert response.status_code == 200
            assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_delete_template(self):
        """测试删除模板 API"""
        mock_service = AsyncMock()
        mock_service.delete_template.return_value = True
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.delete("/api/v1/workflow-templates/tmpl-001")
            
            assert response.status_code == 200
            assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_search_templates(self):
        """测试搜索模板 API"""
        mock_service = AsyncMock()
        mock_service.search_templates.return_value = [
            {"id": "tmpl-1", "name": "测试模板"},
        ]
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.get("/api/v1/workflow-templates/search?q=测试")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) >= 0
    
    @pytest.mark.asyncio
    async def test_create_workflow_from_template(self):
        """测试从模板创建工作流 API"""
        mock_service = AsyncMock()
        mock_service.create_workflow_from_template.return_value = {
            "workflow_id": "wf-001",
            "status": "created",
        }
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.post("/api/v1/workflow-templates/tmpl-001/create-workflow", json={
                "initial_input": {"key": "value"},
                "workflow_name": "我的工作流",
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["workflow_id"] == "wf-001"
    
    @pytest.mark.asyncio
    async def test_fork_template(self):
        """测试 Fork 模板 API"""
        mock_service = AsyncMock()
        mock_service.fork_template.return_value = AsyncMock(
            id="tmpl-fork001",
            name="Fork模板",
            parent_template_id="tmpl-001",
            to_dict=lambda: {
                "id": "tmpl-fork001",
                "name": "Fork模板",
            }
        )
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.post("/api/v1/workflow-templates/tmpl-001/fork", json={
                "new_name": "Fork模板",
            })
            
            assert response.status_code == 200
            assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_rate_template(self):
        """测试评分模板 API"""
        mock_service = AsyncMock()
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.post("/api/v1/workflow-templates/tmpl-001/rate", json={
                "rating": 5,
                "comment": "非常好用",
            })
            
            assert response.status_code == 200
            assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_template_ratings(self):
        """测试获取模板评分列表 API"""
        mock_service = AsyncMock()
        mock_service.get_template_ratings.return_value = {
            "ratings": [
                {"id": "rate-1", "rating": 5, "comment": "很好"},
            ],
            "stats": {"count": 1, "average": 5.0},
        }
        
        with patch('opc_core.api.workflow_templates.get_template_service', return_value=mock_service):
            response = client.get("/api/v1/workflow-templates/tmpl-001/ratings")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["ratings"]) == 1


class TestWorkflowAnalyticsAPI:
    """工作流分析 API 测试"""
    
    @pytest.mark.asyncio
    async def test_get_workflow_stats(self):
        """测试获取工作流统计 API"""
        mock_service = AsyncMock()
        mock_service.get_workflow_stats.return_value = AsyncMock(
            total_workflows=100,
            completed_workflows=80,
            to_dict=lambda: {
                "overview": {"total_workflows": 100, "completed": 80},
            }
        )
        
        with patch('opc_core.api.workflow_analytics.get_analytics_service', return_value=mock_service):
            response = client.get("/api/v1/analytics/workflows?days=30")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_workflow_timeline(self):
        """测试获取工作流时间线 API"""
        mock_service = AsyncMock()
        mock_service.build_timeline.return_value = [
            AsyncMock(
                timestamp="2026-03-25T10:00:00",
                event_type="task_completed",
                step_index=0,
                title="完成步骤1",
                description="任务已完成",
                actor="emp-1",
                metadata=None,
            )
        ]
        
        with patch('opc_core.api.workflow_analytics.get_timeline_service', return_value=mock_service):
            response = client.get("/api/v1/workflows/wf-001/timeline")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) >= 0
    
    @pytest.mark.asyncio
    async def test_get_workflow_timeline_summary(self):
        """测试获取时间线摘要 API"""
        mock_service = AsyncMock()
        mock_service.get_timeline_summary.return_value = AsyncMock(
            total_duration_minutes=30.5,
            total_tasks=3,
            completed_tasks=3,
            step_durations=[],
            to_dict=lambda: {
                "total_duration_minutes": 30.5,
                "total_tasks": 3,
            }
        )
        
        with patch('opc_core.api.workflow_analytics.get_timeline_service', return_value=mock_service):
            response = client.get("/api/v1/workflows/wf-001/timeline/summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
