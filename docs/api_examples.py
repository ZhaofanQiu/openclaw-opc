#!/usr/bin/env python3
"""
OpenClaw OPC API Python 示例
演示如何使用 Python 调用 OPC API
"""

import os
import sys
import json
from typing import Optional, Dict, Any

# 需要安装 requests: pip install requests
try:
    import requests
except ImportError:
    print("请先安装 requests: pip install requests")
    sys.exit(1)


class OPCClient:
    """OpenClaw OPC API 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("OPC_API_KEY", "your-api-key")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"请求失败: {e}")
            print(f"响应: {response.text}")
            raise
    
    def health_check(self) -> Dict:
        """健康检查"""
        return self._request("GET", "/health")
    
    # ===== 员工管理 =====
    
    def setup_partner(self, monthly_budget: float = 10000) -> Dict:
        """设置 Partner"""
        return self._request(
            "POST",
            "/api/agents/partner/setup-auto",
            json={"monthly_budget": monthly_budget}
        )
    
    def hire_employee(
        self,
        partner_id: str,
        name: str,
        emoji: str = "🧑‍💻",
        monthly_budget: float = 2000,
        position_title: str = None
    ) -> Dict:
        """雇佣员工"""
        data = {
            "name": name,
            "emoji": emoji,
            "monthly_budget": monthly_budget,
            "position_title": position_title
        }
        return self._request(
            "POST",
            f"/api/agents/partner/hire?partner_id={partner_id}",
            json=data
        )
    
    def list_agents(self) -> list:
        """列出所有员工"""
        return self._request("GET", "/api/agents")
    
    def get_agent(self, agent_id: str) -> Dict:
        """获取员工详情"""
        return self._request("GET", f"/api/agents/{agent_id}")
    
    def bind_agent(self, employee_id: str, agent_id: str) -> Dict:
        """绑定 Agent"""
        return self._request(
            "POST",
            "/api/agents/binding/bind",
            json={"employee_id": employee_id, "agent_id": agent_id}
        )
    
    # ===== 任务管理 =====
    
    def create_task(
        self,
        title: str,
        description: str,
        agent_id: str,
        estimated_cost: float = 100
    ) -> Dict:
        """创建任务"""
        return self._request(
            "POST",
            "/api/tasks",
            json={
                "title": title,
                "description": description,
                "agent_id": agent_id,
                "estimated_cost": estimated_cost
            }
        )
    
    def list_tasks(self) -> list:
        """列出任务"""
        return self._request("GET", "/api/tasks")
    
    def get_task(self, task_id: str) -> Dict:
        """获取任务详情"""
        return self._request("GET", f"/api/tasks/{task_id}")
    
    def complete_task(self, task_id: str, result: str = "") -> Dict:
        """完成任务"""
        return self._request(
            "POST",
            f"/api/tasks/{task_id}/complete",
            json={"result": result}
        )
    
    # ===== 工作流管理 =====
    
    def create_workflow(
        self,
        title: str,
        description: str,
        created_by: str,
        total_budget: float,
        template_id: str = None
    ) -> Dict:
        """创建工作流"""
        data = {
            "title": title,
            "description": description,
            "total_budget": total_budget,
            "template_id": template_id
        }
        return self._request(
            "POST",
            f"/api/workflows?created_by={created_by}",
            json=data
        )
    
    def list_workflows(self) -> list:
        """列出工作流"""
        return self._request("GET", "/api/workflows")
    
    def get_workflow(self, workflow_id: str) -> Dict:
        """获取工作流详情"""
        return self._request("GET", f"/api/workflows/{workflow_id}")
    
    def start_workflow(self, workflow_id: str) -> Dict:
        """启动工作流"""
        return self._request("POST", f"/api/workflows/{workflow_id}/start")
    
    def get_workflow_steps(self, workflow_id: str) -> list:
        """获取工作流步骤"""
        return self._request("GET", f"/api/workflows/{workflow_id}/steps")
    
    # ===== 预算管理 =====
    
    def get_budget_summary(self) -> Dict:
        """获取预算汇总"""
        return self._request("GET", "/api/budget/summary")
    
    def get_agent_budgets(self) -> list:
        """获取员工预算详情"""
        return self._request("GET", "/api/budget/agents")
    
    # ===== 技能成长 =====
    
    def get_skill_paths(self) -> list:
        """获取成长路径定义"""
        return self._request("GET", "/api/agent-skill-paths/paths")
    
    def get_agent_skill_path(self, agent_id: str) -> Dict:
        """获取员工成长路径"""
        return self._request("GET", f"/api/agent-skill-paths/agent/{agent_id}")
    
    # ===== Partner 功能 =====
    
    def wake_partner(self, partner_id: str) -> Dict:
        """唤醒 Partner"""
        return self._request(
            "POST",
            f"/api/agents/partner/wake?partner_id={partner_id}"
        )
    
    def sleep_partner(self, partner_id: str) -> Dict:
        """让 Partner 休眠"""
        return self._request(
            "POST",
            f"/api/agents/partner/sleep?partner_id={partner_id}"
        )
    
    def chat_with_partner(self, partner_id: str, message: str) -> Dict:
        """与 Partner 对话"""
        return self._request(
            "POST",
            f"/api/agents/partner/chat?partner_id={partner_id}",
            json={"message": message}
        )
    
    def get_company_summary(self, partner_id: str) -> Dict:
        """获取公司状态摘要"""
        return self._request(
            "GET",
            f"/api/agents/partner/summary?partner_id={partner_id}"
        )


def demo():
    """演示完整的工作流程"""
    
    print("=" * 50)
    print("OpenClaw OPC API Python 示例")
    print("=" * 50)
    print()
    
    # 创建客户端
    client = OPCClient()
    
    # 1. 健康检查
    print("1. 健康检查...")
    health = client.health_check()
    print(f"   状态: {health['status']}")
    print()
    
    # 2. 设置 Partner
    print("2. 设置 Partner...")
    partner_data = client.setup_partner(monthly_budget=10000)
    print(f"   成功: {partner_data.get('success')}")
    
    partner = partner_data.get("partner", {})
    partner_id = partner.get("id")
    print(f"   Partner ID: {partner_id}")
    print(f"   名称: {partner.get('name')}")
    print()
    
    if not partner_id:
        print("错误: 无法获取 Partner ID")
        return
    
    # 3. 雇佣员工
    print("3. 雇佣员工...")
    employee_data = client.hire_employee(
        partner_id=partner_id,
        name="开发助手",
        emoji="👨‍💻",
        monthly_budget=3000,
        position_title="全栈开发"
    )
    print(f"   成功: {employee_data.get('success')}")
    
    employee = employee_data.get("employee", {})
    employee_id = employee.get("id")
    print(f"   Employee ID: {employee_id}")
    print(f"   名称: {employee.get('name')}")
    print()
    
    if not employee_id:
        print("错误: 无法获取 Employee ID")
        return
    
    # 4. 列出所有员工
    print("4. 列出所有员工...")
    agents = client.list_agents()
    print(f"   共有 {len(agents)} 名员工")
    for agent in agents[:3]:  # 只显示前3个
        print(f"   - {agent.get('emoji', '🧑‍💻')} {agent.get('name')} ({agent.get('position_title')})")
    print()
    
    # 5. 创建任务
    print("5. 创建任务...")
    task_data = client.create_task(
        title="开发用户登录功能",
        description="实现基于JWT的用户认证系统，包含注册、登录、token刷新功能",
        agent_id=employee_id,
        estimated_cost=500
    )
    print(f"   成功: {task_data.get('success')}")
    
    task = task_data.get("task", {})
    task_id = task.get("id")
    print(f"   Task ID: {task_id}")
    print(f"   标题: {task.get('title')}")
    print(f"   预估成本: {task.get('estimated_cost')} OC币")
    print()
    
    # 6. 创建工作流
    print("6. 创建工作流...")
    workflow_data = client.create_workflow(
        title="Web应用开发项目",
        description="开发一个完整的Web应用，包含前端和后端",
        created_by=partner_id,
        total_budget=5000
    )
    print(f"   成功: {workflow_data.get('success')}")
    
    workflow = workflow_data.get("workflow", {})
    workflow_id = workflow.get("id")
    print(f"   Workflow ID: {workflow_id}")
    print(f"   标题: {workflow.get('title')}")
    print(f"   总预算: {workflow.get('total_budget')} OC币")
    print()
    
    # 7. 获取预算汇总
    print("7. 获取预算汇总...")
    budget = client.get_budget_summary()
    summary = budget.get("summary", {})
    print(f"   总预算: {summary.get('total_budget')} OC币")
    print(f"   已使用: {summary.get('used_budget')} OC币")
    print(f"   剩余: {summary.get('remaining_budget')} OC币")
    print(f"   使用率: {summary.get('usage_percentage', 0):.1f}%")
    print()
    
    # 8. 唤醒 Partner
    print("8. 唤醒 Partner...")
    wake_data = client.wake_partner(partner_id)
    print(f"   状态: {wake_data.get('status')}")
    print()
    
    # 9. 获取公司摘要
    print("9. 获取公司状态...")
    summary = client.get_company_summary(partner_id)
    print(f"   员工数: {summary.get('total_agents')}")
    print(f"   在线: {summary.get('online_agents')}")
    print(f"   待办任务: {summary.get('pending_tasks')}")
    print()
    
    # 10. 获取员工成长路径
    print("10. 获取员工成长路径...")
    try:
        skill_path = client.get_agent_skill_path(employee_id)
        recommended = skill_path.get("recommended_path", {})
        print(f"   推荐路径: {recommended.get('name')}")
        print(f"   当前阶段: {skill_path.get('current_stage')}")
    except Exception as e:
        print(f"   (暂无成长路径数据)")
    print()
    
    print("=" * 50)
    print("演示完成!")
    print("=" * 50)
    print()
    print("关键 ID (请保存):")
    print(f"  Partner ID:   {partner_id}")
    print(f"  Employee ID:  {employee_id}")
    print(f"  Task ID:      {task_id}")
    print(f"  Workflow ID:  {workflow_id}")
    print()


if __name__ == "__main__":
    try:
        demo()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
