"""
opc-database: 工作流模板模型测试 (v0.4.2-P2)

测试 WorkflowTemplate 和 WorkflowTemplateRating 模型

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

import json

from opc_database.models.workflow_template import WorkflowTemplate, WorkflowTemplateRating


class TestWorkflowTemplate:
    """工作流模板模型测试"""
    
    def test_template_creation(self):
        """测试模板创建"""
        steps_json = '[{"employee_id": "emp-1", "title": "步骤1", "estimated_cost": 0.5},' \
                     '{"employee_id": "emp-2", "title": "步骤2", "estimated_cost": 1.0}]'
        
        template = WorkflowTemplate(
            id="tmpl-test001",
            name="测试模板",
            description="这是一个测试模板",
            steps_config=steps_json,
            category="general",
            tags='["test", "demo"]',
            usage_count=0,
            avg_rating=0.0,
            rating_count=0,
            version=1,
            parent_template_id=None,
            created_by="user-1",
            is_system=False,
            is_public=True,
        )
        
        assert template.id == "tmpl-test001"
        assert template.name == "测试模板"
        assert template.category == "general"
        assert template.version == 1
        assert template.is_public is True
    
    def test_get_steps_config(self):
        """测试获取步骤配置"""
        steps = [
            {"employee_id": "emp-1", "title": "步骤1", "estimated_cost": 0.5},
            {"employee_id": "emp-2", "title": "步骤2", "estimated_cost": 1.0}
        ]
        
        template = WorkflowTemplate(
            id="tmpl-test002",
            name="测试",
            steps_config=json.dumps(steps),
        )
        
        result = template.get_steps_config()
        assert len(result) == 2
        assert result[0]["title"] == "步骤1"
        assert result[1]["estimated_cost"] == 1.0
    
    def test_get_steps_config_empty(self):
        """测试空步骤配置"""
        template = WorkflowTemplate(
            id="tmpl-test003",
            name="测试",
            steps_config="",
        )
        
        result = template.get_steps_config()
        assert result == []
    
    def test_set_steps_config(self):
        """测试设置步骤配置"""
        template = WorkflowTemplate(
            id="tmpl-test004",
            name="测试",
        )
        
        steps = [
            {"employee_id": "emp-1", "title": "步骤1"},
            {"employee_id": "emp-2", "title": "步骤2"},
        ]
        
        template.set_steps_config(steps)
        
        assert template.steps_config is not None
        parsed = json.loads(template.steps_config)
        assert len(parsed) == 2
    
    def test_get_tags(self):
        """测试获取标签"""
        template = WorkflowTemplate(
            id="tmpl-test005",
            name="测试",
            tags='["tag1", "tag2", "tag3"]',
        )
        
        tags = template.get_tags()
        assert tags == ["tag1", "tag2", "tag3"]
    
    def test_set_tags(self):
        """测试设置标签"""
        template = WorkflowTemplate(
            id="tmpl-test006",
            name="测试",
        )
        
        template.set_tags(["python", "async", "test"])
        
        assert template.tags == '["python", "async", "test"]'
    
    def test_increment_usage(self):
        """测试增加使用次数"""
        template = WorkflowTemplate(
            id="tmpl-test007",
            name="测试",
            usage_count=5,
        )
        
        template.increment_usage()
        assert template.usage_count == 6
        
        # 再调用一次
        template.increment_usage()
        assert template.usage_count == 7
    
    def test_update_rating(self):
        """测试更新评分（添加新评分）"""
        template = WorkflowTemplate(
            id="tmpl-test008",
            name="测试",
            avg_rating=4.0,
            rating_count=10,
        )
        
        # 添加一个新评分 5.0，平均分应该是 (4.0*10 + 5.0) / 11 = 4.09
        template.update_rating(5.0)
        
        # 计算期望的平均值
        expected_avg = (4.0 * 10 + 5.0) / 11
        assert abs(template.avg_rating - expected_avg) < 0.01
        assert template.rating_count == 11
    
    def test_to_dict(self):
        """测试序列化为字典"""
        steps = [{"employee_id": "emp-1", "title": "步骤1"}]
        template = WorkflowTemplate(
            id="tmpl-test009",
            name="测试模板",
            description="描述",
            steps_config=json.dumps(steps),
            category="test",
            tags='["tag1"]',
            usage_count=10,
            avg_rating=4.5,
            rating_count=5,
            version=2,
            is_public=True,
            is_system=False,
        )
        
        result = template.to_dict()
        
        assert result["id"] == "tmpl-test009"
        assert result["name"] == "测试模板"
        assert result["category"] == "test"
        assert result["usage_count"] == 10
        assert result["avg_rating"] == 4.5
        assert isinstance(result["steps_config"], list)
        assert isinstance(result["tags"], list)


class TestWorkflowTemplateRating:
    """模板评分模型测试"""
    
    def test_rating_creation(self):
        """测试评分创建"""
        rating = WorkflowTemplateRating(
            id="rate-test001",
            template_id="tmpl-001",
            user_id="user-1",
            rating=5,
            comment="非常好用的模板",
        )
        
        assert rating.id == "rate-test001"
        assert rating.template_id == "tmpl-001"
        assert rating.rating == 5
        assert rating.comment == "非常好用的模板"
    
    def test_rating_validation(self):
        """测试评分值范围"""
        # 正常评分
        rating = WorkflowTemplateRating(
            id="rate-test002",
            template_id="tmpl-001",
            user_id="user-1",
            rating=3,
        )
        assert rating.rating == 3
    
    def test_to_dict(self):
        """测试序列化为字典"""
        rating = WorkflowTemplateRating(
            id="rate-test003",
            template_id="tmpl-001",
            user_id="user-1",
            rating=4,
            comment="不错",
        )
        
        result = rating.to_dict()
        
        assert result["id"] == "rate-test003"
        assert result["rating"] == 4
        assert result["comment"] == "不错"
        assert "created_at" in result
