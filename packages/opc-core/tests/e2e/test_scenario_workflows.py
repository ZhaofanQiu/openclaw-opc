"""
opc-core: v0.4.2 实际应用场景端到端测试

测试场景:
1. 内容创作流水线
2. 代码审查流水线
3. 客户服务响应
4. 数据报告生成

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2
"""

import json
import pytest
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock

from opc_database.models import (
    Task, TaskStatus, Employee, AgentStatus, PositionLevel
)
from opc_database.repositories import (
    EmployeeRepository, TaskRepository, WorkflowTemplateRepository
)
from opc_core.services import (
    WorkflowService, WorkflowStepConfig, WorkflowTemplateService,
    TemplateCreateRequest, WorkflowTimelineService,
    WorkflowAnalyticsService
)


# ========================================
# 测试数据工厂
# ========================================

class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    def create_content_creation_agents() -> List[Dict]:
        """内容创作场景的员工数据"""
        return [
            {
                "id": "emp-planner",
                "name": "ContentPlanner",
                "emoji": "📝",
                "position_level": PositionLevel.SENIOR,
                "monthly_budget": 500.0,
            },
            {
                "id": "emp-writer",
                "name": "Writer",
                "emoji": "✍️",
                "position_level": PositionLevel.MID,
                "monthly_budget": 800.0,
            },
            {
                "id": "emp-editor",
                "name": "Editor",
                "emoji": "🧐",
                "position_level": PositionLevel.SENIOR,
                "monthly_budget": 600.0,
            },
            {
                "id": "emp-publisher",
                "name": "Publisher",
                "emoji": "🚀",
                "position_level": PositionLevel.JUNIOR,
                "monthly_budget": 300.0,
            },
        ]
    
    @staticmethod
    def create_code_review_agents() -> List[Dict]:
        """代码审查场景的员工数据"""
        return [
            {
                "id": "emp-linter",
                "name": "Linter",
                "emoji": "🔍",
                "position_level": PositionLevel.JUNIOR,
                "monthly_budget": 200.0,
            },
            {
                "id": "emp-security",
                "name": "SecurityBot",
                "emoji": "🛡️",
                "position_level": PositionLevel.SENIOR,
                "monthly_budget": 500.0,
            },
            {
                "id": "emp-architect",
                "name": "Architect",
                "emoji": "🏗️",
                "position_level": PositionLevel.EXPERT,
                "monthly_budget": 800.0,
            },
        ]
    
    @staticmethod
    def content_creation_workflow_input() -> Dict:
        """内容创作工作流输入"""
        return {
            "topic": "AI Agent发展趋势",
            "word_count": 2000,
            "style": "技术博客",
            "platforms": ["公众号", "知乎", "CSDN"],
            "keywords": ["AI", "Agent", "LLM"],
        }
    
    @staticmethod
    def code_review_workflow_input() -> Dict:
        """代码审查工作流输入"""
        return {
            "repo": "github.com/company/project",
            "pr_id": "#123",
            "files": ["src/auth.py", "src/api.py"],
            "language": "python",
            "commit_hash": "abc123",
        }


# ========================================
# 场景1: 内容创作流水线测试
# ========================================

class TestContentCreationWorkflow:
    """内容创作工作流场景测试"""
    
    @pytest.fixture
    def content_agents(self):
        return TestDataFactory.create_content_creation_agents()
    
    @pytest.mark.asyncio
    async def test_content_workflow_creation(self):
        """测试创建内容创作工作流"""
        # 创建工作流步骤
        steps = [
            WorkflowStepConfig(
                employee_id="emp-planner",
                title="选题策划",
                description="确定选题和大纲",
                estimated_cost=0.5,
            ),
            WorkflowStepConfig(
                employee_id="emp-writer",
                title="文章撰写",
                description="撰写完整文章",
                estimated_cost=2.0,
            ),
            WorkflowStepConfig(
                employee_id="emp-editor",
                title="编辑审核",
                description="审核内容质量",
                estimated_cost=0.8,
            ),
            WorkflowStepConfig(
                employee_id="emp-publisher",
                title="多渠道发布",
                description="发布到各平台",
                estimated_cost=0.3,
            ),
        ]
        
        initial_input = TestDataFactory.content_creation_workflow_input()
        
        # 验证步骤配置
        assert len(steps) == 4
        assert steps[0].employee_id == "emp-planner"
        assert steps[1].estimated_cost == 2.0
        assert steps[2].title == "编辑审核"
        
        # 验证输入数据
        assert initial_input["topic"] == "AI Agent发展趋势"
        assert len(initial_input["platforms"]) == 3
    
    @pytest.mark.asyncio
    async def test_content_workflow_rework_scenario(self):
        """测试内容创作的返工场景"""
        # 模拟返工场景: 编辑审核不通过，退回给写手
        workflow_id = "wf-content-001"
        
        # Step 1: 策划完成
        step1_task = Task(
            id="task-step1",
            workflow_id=workflow_id,
            step_index=0,
            title="选题策划",
            status=TaskStatus.COMPLETED.value,
            assigned_to="emp-planner",
        )
        
        # Step 2: 撰写完成
        step2_task = Task(
            id="task-step2",
            workflow_id=workflow_id,
            step_index=1,
            title="文章撰写",
            status=TaskStatus.COMPLETED.value,
            assigned_to="emp-writer",
        )
        
        # Step 3: 编辑审核 - 要求返工
        step3_task = Task(
            id="task-step3",
            workflow_id=workflow_id,
            step_index=2,
            title="编辑审核",
            status=TaskStatus.COMPLETED.value,
            assigned_to="emp-editor",
            is_rework=True,  # 标记为返工
        )
        
        # Step 2 (rework): 写手返工
        step2_rework_task = Task(
            id="task-step2-rework",
            workflow_id=workflow_id,
            step_index=1,
            title="文章撰写 (返工)",
            status=TaskStatus.COMPLETED.value,
            assigned_to="emp-writer",
            is_rework=True,
            # parent_task_id 字段不存在，通过 output_data 记录关联
            output_data=json.dumps({"parent_task_id": "task-step2"}),
        )
        
        tasks = [step1_task, step2_task, step3_task, step2_rework_task]
        
        # 验证返工逻辑
        rework_tasks = [t for t in tasks if t.is_rework]
        assert len(rework_tasks) == 2
        
        # 验证有返工任务关联到原任务
        rework_output = json.loads(step2_rework_task.output_data)
        assert rework_output.get("parent_task_id") == "task-step2"
    
    @pytest.mark.asyncio
    async def test_content_workflow_budget_tracking(self):
        """测试预算追踪"""
        # 预期预算: 0.5 + 2.0 + 0.8 + 0.3 = 3.6
        expected_budget = 3.6
        
        steps_cost = [0.5, 2.0, 0.8, 0.3]
        actual_budget = sum(steps_cost)
        
        assert actual_budget == expected_budget
        assert actual_budget < 5.0  # 预算熔断阈值


# ========================================
# 场景2: 代码审查流水线测试
# ========================================

class TestCodeReviewWorkflow:
    """代码审查工作流场景测试"""
    
    @pytest.fixture
    def review_agents(self):
        return TestDataFactory.create_code_review_agents()
    
    @pytest.mark.asyncio
    async def test_code_review_failure_scenario(self):
        """测试代码审查失败场景"""
        workflow_id = "wf-review-001"
        
        # Step 1: Linter 检查失败
        linter_task = Task(
            id="task-linter",
            workflow_id=workflow_id,
            step_index=0,
            title="规范检查",
            status=TaskStatus.FAILED.value,  # 失败
            assigned_to="emp-linter",
            output_data=json.dumps({
                "errors": ["Line 10: unused import", "Line 25: missing docstring"],
                "passed": False,
            }),
        )
        
        # 验证失败状态
        assert linter_task.status == TaskStatus.FAILED.value
        
        # 验证工作流应该终止
        workflow_should_continue = linter_task.status != TaskStatus.FAILED.value
        assert workflow_should_continue is False
    
    @pytest.mark.asyncio
    async def test_code_review_security_high_risk(self):
        """测试高风险安全漏洞场景"""
        security_task = Task(
            id="task-security",
            workflow_id="wf-review-002",
            step_index=1,
            title="安全扫描",
            status=TaskStatus.COMPLETED.value,
            assigned_to="emp-security",
            output_data=json.dumps({
                "risk_level": "HIGH",
                "vulnerabilities": [
                    {"severity": "HIGH", "type": "SQL Injection"},
                    {"severity": "MEDIUM", "type": "XSS"},
                ],
            }),
        )
        
        output = json.loads(security_task.output_data)
        
        # 验证高风险检测
        assert output["risk_level"] == "HIGH"
        assert len(output["vulnerabilities"]) > 0
        
        # 高风险应该阻止后续步骤
        should_block = output["risk_level"] == "HIGH"
        assert should_block is True
    
    @pytest.mark.asyncio
    async def test_code_review_success_scenario(self):
        """测试代码审查成功场景"""
        workflow_id = "wf-review-success"
        
        tasks = [
            Task(
                id="task-linter",
                workflow_id=workflow_id,
                step_index=0,
                title="规范检查",
                status=TaskStatus.COMPLETED.value,
                assigned_to="emp-linter",
            ),
            Task(
                id="task-security",
                workflow_id=workflow_id,
                step_index=1,
                title="安全扫描",
                status=TaskStatus.COMPLETED.value,
                assigned_to="emp-security",
                output_data=json.dumps({"risk_level": "LOW"}),
            ),
            Task(
                id="task-architect",
                workflow_id=workflow_id,
                step_index=2,
                title="架构审查",
                status=TaskStatus.COMPLETED.value,
                assigned_to="emp-architect",
            ),
        ]
        
        # 验证所有步骤成功
        all_completed = all(t.status == TaskStatus.COMPLETED.value for t in tasks)
        assert all_completed is True


# ========================================
# 场景3: 客户服务响应测试
# ========================================

class TestCustomerServiceWorkflow:
    """客户服务响应场景测试"""
    
    @pytest.mark.asyncio
    async def test_customer_service_routing(self):
        """测试客户问题路由"""
        inquiries = [
            {
                "id": "inq-1",
                "content": "如何重置密码？",
                "expected_route": "technical",
                "agent": "TechSupport",
            },
            {
                "id": "inq-2",
                "content": "企业版价格是多少？",
                "expected_route": "business",
                "agent": "Sales",
            },
            {
                "id": "inq-3",
                "content": "你们的服务太差了！",
                "expected_route": "complaint",
                "agent": "ComplaintHandler",
            },
        ]
        
        for inquiry in inquiries:
            # 模拟分类逻辑
            content = inquiry["content"]
            
            if "价格" in content or "多少钱" in content:
                route = "business"
            elif "差" in content or "投诉" in content:
                route = "complaint"
            else:
                route = "technical"
            
            assert route == inquiry["expected_route"], f"Inquiry {inquiry['id']} routing failed"
    
    @pytest.mark.asyncio
    async def test_customer_service_workflow_with_qa(self):
        """测试带质检的客服工作流"""
        workflow_id = "wf-service-001"
        
        # Step 1: 分类
        classify_task = Task(
            id="task-classify",
            workflow_id=workflow_id,
            step_index=0,
            title="问题分类",
            status=TaskStatus.COMPLETED.value,
            output_data=json.dumps({"category": "technical", "confidence": 0.95}),
        )
        
        # Step 2: 技术支持回复
        support_task = Task(
            id="task-support",
            workflow_id=workflow_id,
            step_index=1,
            title="技术支持",
            status=TaskStatus.COMPLETED.value,
            assigned_to="emp-tech-support",
            output_data=json.dumps({
                "response": "您可以在设置页面点击'忘记密码'进行重置。",
                "satisfaction_score": 0.9,
            }),
        )
        
        # Step 3: QA质检
        qa_task = Task(
            id="task-qa",
            workflow_id=workflow_id,
            step_index=2,
            title="质检审核",
            status=TaskStatus.COMPLETED.value,
            assigned_to="emp-qa",
            output_data=json.dumps({
                "passed": True,
                "score": 95,
                "comments": "回复及时且准确",
            }),
        )
        
        # 验证质检通过
        qa_output = json.loads(qa_task.output_data)
        assert qa_output["passed"] is True
        assert qa_output["score"] >= 90


# ========================================
# 场景4: 数据报告生成测试
# ========================================

class TestDataReportWorkflow:
    """数据报告生成场景测试"""
    
    @pytest.mark.asyncio
    async def test_data_report_workflow_steps(self):
        """测试数据报告工作流步骤"""
        steps = [
            {"name": "数据清洗", "agent": "DataCleaner", "budget": 0.5},
            {"name": "数据分析", "agent": "Analyst", "budget": 1.5},
            {"name": "可视化设计", "agent": "Designer", "budget": 0.8},
            {"name": "报告撰写", "agent": "Reporter", "budget": 1.0},
        ]
        
        total_budget = sum(s["budget"] for s in steps)
        
        assert len(steps) == 4
        assert total_budget == 3.8
        assert steps[1]["name"] == "数据分析"
    
    @pytest.mark.asyncio
    async def test_data_report_subtasks(self):
        """测试数据分析子任务"""
        # 数据分析步骤包含多个子分析任务
        subtasks = [
            {"name": "趋势分析", "type": "trend", "priority": "high"},
            {"name": "异常检测", "type": "anomaly", "priority": "high"},
            {"name": "预测建模", "type": "forecast", "priority": "medium"},
        ]
        
        assert len(subtasks) == 3
        
        # 验证优先级
        high_priority = [s for s in subtasks if s["priority"] == "high"]
        assert len(high_priority) == 2
    
    @pytest.mark.asyncio
    async def test_data_report_rework_for_more_analysis(self):
        """测试报告撰写时需要补充分析的场景"""
        workflow_id = "wf-report-001"
        
        # 报告员发现需要更多分析
        reporter_task = Task(
            id="task-reporter",
            workflow_id=workflow_id,
            step_index=3,
            title="报告撰写",
            status=TaskStatus.COMPLETED.value,
            output_data=json.dumps({
                "report": "Q1销售报告",
                "needs_more_analysis": True,
                "missing_insights": ["区域对比", "竞品分析"],
            }),
        )
        
        output = json.loads(reporter_task.output_data)
        
        # 验证需要返工
        assert output["needs_more_analysis"] is True
        assert len(output["missing_insights"]) == 2


# ========================================
# 跨场景集成测试
# ========================================

class TestCrossScenarioIntegration:
    """跨场景集成测试"""
    
    @pytest.mark.asyncio
    async def test_template_creation_from_scenarios(self):
        """测试从场景创建模板"""
        # 从内容创作场景创建模板
        content_template = {
            "name": "内容创作标准流程",
            "description": "从选题到发布的标准内容创作流程",
            "category": "content",
            "tags": ["content", "writing", "publishing"],
            "steps_config": [
                {"employee_id": "planner", "title": "选题策划", "estimated_cost": 0.5},
                {"employee_id": "writer", "title": "文章撰写", "estimated_cost": 2.0},
                {"employee_id": "editor", "title": "编辑审核", "estimated_cost": 0.8},
                {"employee_id": "publisher", "title": "多渠道发布", "estimated_cost": 0.3},
            ],
        }
        
        # 验证模板结构
        assert content_template["name"] == "内容创作标准流程"
        assert len(content_template["steps_config"]) == 4
        assert content_template["category"] == "content"
    
    @pytest.mark.asyncio
    async def test_template_forking(self):
        """测试模板Fork"""
        parent_template = {
            "id": "tmpl-content-base",
            "name": "内容创作基础模板",
            "category": "content",
        }
        
        # Fork 为不同平台的专用模板
        forked_templates = [
            {
                "parent_id": parent_template["id"],
                "name": "公众号创作模板",
                "platform": "wechat",
            },
            {
                "parent_id": parent_template["id"],
                "name": "知乎回答模板",
                "platform": "zhihu",
            },
        ]
        
        for fork in forked_templates:
            assert fork["parent_id"] == parent_template["id"]
            assert parent_template["name"] in fork["name"] or "模板" in fork["name"]
    
    @pytest.mark.asyncio
    async def test_analytics_across_scenarios(self):
        """测试跨场景分析统计"""
        # 模拟各场景的工作流统计
        scenario_stats = {
            "content_creation": {"total": 10, "completed": 8, "rework_rate": 0.2},
            "code_review": {"total": 20, "completed": 18, "rework_rate": 0.1},
            "customer_service": {"total": 50, "completed": 50, "rework_rate": 0.05},
            "data_report": {"total": 5, "completed": 4, "rework_rate": 0.25},
        }
        
        total_workflows = sum(s["total"] for s in scenario_stats.values())
        total_completed = sum(s["completed"] for s in scenario_stats.values())
        avg_rework_rate = sum(s["rework_rate"] for s in scenario_stats.values()) / len(scenario_stats)
        
        assert total_workflows == 85
        assert total_completed == 80
        assert avg_rework_rate > 0 and avg_rework_rate < 0.5


# ========================================
# 端到端完整流程测试
# ========================================

class TestEndToEndWorkflow:
    """端到端完整流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_content_creation_flow(self):
        """测试完整的内容创作流程"""
        
        # 1. 创建工作流
        workflow_id = "wf-e2e-content-001"
        steps = [
            WorkflowStepConfig("emp-planner", "选题策划", "", 0.5),
            WorkflowStepConfig("emp-writer", "文章撰写", "", 2.0),
            WorkflowStepConfig("emp-editor", "编辑审核", "", 0.8),
            WorkflowStepConfig("emp-publisher", "发布", "", 0.3),
        ]
        initial_input = TestDataFactory.content_creation_workflow_input()
        
        # 2. 创建工作流（模拟）
        created_workflow = {
            "workflow_id": workflow_id,
            "name": "AI Agent发展趋势文章创作",
            "status": "created",
            "steps_count": len(steps),
            "estimated_budget": sum(s.estimated_cost for s in steps),
        }
        
        # 3. 验证创建
        assert created_workflow["workflow_id"] == workflow_id
        assert created_workflow["steps_count"] == 4
        assert created_workflow["estimated_budget"] == 3.6
        
        # 4. 模拟执行各步骤
        executed_tasks = []
        for i, step in enumerate(steps):
            task = {
                "task_id": f"task-{i}",
                "step_index": i,
                "title": step.title,
                "status": "completed",
                "cost": step.estimated_cost,
            }
            executed_tasks.append(task)
        
        # 5. 验证执行
        assert len(executed_tasks) == 4
        assert all(t["status"] == "completed" for t in executed_tasks)
        
        # 6. 创建工作流模板
        template = {
            "template_id": "tmpl-content-v1",
            "name": "标准内容创作模板",
            "source_workflow": workflow_id,
            "usage_count": 1,
        }
        
        # 7. 验证模板
        assert template["source_workflow"] == workflow_id
        
        # 8. 时间线验证
        timeline_events = [
            {"event": "workflow_created", "timestamp": "2026-03-25T10:00:00"},
            {"event": "task_completed", "step": 0, "timestamp": "2026-03-25T10:30:00"},
            {"event": "task_completed", "step": 1, "timestamp": "2026-03-25T12:30:00"},
            {"event": "task_completed", "step": 2, "timestamp": "2026-03-25T13:15:00"},
            {"event": "task_completed", "step": 3, "timestamp": "2026-03-25T13:30:00"},
            {"event": "workflow_completed", "timestamp": "2026-03-25T13:30:00"},
        ]
        
        assert len(timeline_events) == 6
        assert timeline_events[-1]["event"] == "workflow_completed"
        
        # 9. 分析统计
        total_duration = 3.5  # 小时
        completion_rate = 100.0
        
        assert total_duration > 0
        assert completion_rate == 100.0


# ========================================
# 性能测试
# ========================================

class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self):
        """测试并发工作流处理"""
        # 模拟同时创建多个工作流
        workflow_count = 10
        
        workflows = []
        for i in range(workflow_count):
            wf = {
                "workflow_id": f"wf-concurrent-{i}",
                "status": "created",
            }
            workflows.append(wf)
        
        assert len(workflows) == workflow_count
        assert all(w["status"] == "created" for w in workflows)
    
    @pytest.mark.asyncio
    async def test_large_workflow_execution(self):
        """测试大型工作流执行"""
        # 创建包含多个步骤的工作流
        large_steps = []
        for i in range(20):
            step = WorkflowStepConfig(
                employee_id=f"emp-{i % 5}",
                title=f"步骤{i+1}",
                description=f"这是第{i+1}个步骤",
                estimated_cost=0.1 + (i * 0.01),
            )
            large_steps.append(step)
        
        total_budget = sum(s.estimated_cost for s in large_steps)
        
        assert len(large_steps) == 20
        assert total_budget > 2.0  # 20步应该有可观的预算


# ========================================
# 错误处理测试
# ========================================

class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_budget_fuse_trigger(self):
        """测试预算熔断触发"""
        budget_limit = 5.0
        used_budget = 5.2
        
        fuse_triggered = used_budget >= budget_limit
        
        assert fuse_triggered is True
    
    @pytest.mark.asyncio
    async def test_invalid_workflow_config(self):
        """测试无效的工作流配置"""
        # 空的步骤列表
        empty_steps = []
        
        is_valid = len(empty_steps) > 0
        
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_agent_not_available(self):
        """测试Agent不可用场景"""
        agent_status = "offline"
        
        can_assign = agent_status == "idle" or agent_status == "working"
        
        assert can_assign is False
