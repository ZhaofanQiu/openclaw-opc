"""
OPC Bridge - Connect OpenClaw Agents to OPC Core Service

This module provides functions for Agents to communicate with the OPC Core Service.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

# Core Service URL (configurable via environment variable)
OPC_CORE_URL = os.getenv("OPC_CORE_URL", "http://localhost:8080")


def _make_request(
    method: str,
    path: str,
    data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Make HTTP request to OPC Core Service.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g., /api/agents/report)
        data: JSON data for POST requests
    
    Returns:
        Response dictionary
    """
    url = f"{OPC_CORE_URL}{path}"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=json_data,
                headers=headers,
                method=method
            )
        else:
            req = urllib.request.Request(url, headers=headers, method=method)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            return {
                "success": True,
                "status_code": response.status,
                "data": json.loads(response.read().decode('utf-8'))
            }
    except urllib.error.HTTPError as e:
        return {
            "success": False,
            "status_code": e.code,
            "error": e.read().decode('utf-8')
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def opc_report(
    task_id: str,
    token_used: int,
    result_summary: str = "",
    status: str = "completed",
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Report task completion to OPC Core Service.
    
    This function should be called by an Agent after completing a task.
    It reports token usage and triggers budget updates.
    
    Args:
        task_id: The ID of the completed task
        token_used: Number of tokens consumed
        result_summary: Brief description of the work done
        status: "completed" or "failed"
        agent_id: Optional agent ID (auto-detected if not provided)
    
    Returns:
        Response from Core Service including:
        - success: True/False
        - cost: OC币 consumed
        - remaining_budget: Updated budget
        - fused: True if budget exceeded (task failed)
    
    Example:
        ```python
        result = opc_report(
            task_id="abc123",
            token_used=1500,
            result_summary="完成了登录页重构",
            status="completed"
        )
        
        if result["success"]:
            print(f"任务完成，消耗 {result['cost']} OC币")
        elif result.get("fused"):
            print(f"预算熔断: {result['message']}")
        ```
    """
    # Get agent_id from environment if not provided
    # In OpenClaw, this could be set via session context
    if agent_id is None:
        agent_id = os.getenv("OPC_AGENT_ID", "unknown")
    
    response = _make_request(
        "POST",
        "/api/agents/report",
        data={
            "agent_id": agent_id,
            "task_id": task_id,
            "token_used": token_used,
            "result_summary": result_summary,
            "status": status
        }
    )
    
    if response["success"]:
        return response["data"]
    else:
        return {
            "success": False,
            "error": response.get("error", "Unknown error"),
            "status_code": response.get("status_code")
        }


def opc_check_task(agent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Check for assigned tasks from OPC Core Service.
    
    This function should be called by an Agent to see if there's
    a pending task assigned to it.
    
    Args:
        agent_id: Optional agent ID (auto-detected if not provided)
    
    Returns:
        Response from Core Service:
        - has_task: True/False
        - task: Task details if has_task is True
    
    Example:
        ```python
        result = opc_check_task()
        
        if result["has_task"]:
            task = result["task"]
            print(f"新任务: {task['title']}")
            print(f"描述: {task['description']}")
            print(f"预算: {task['estimated_cost']} OC币")
        else:
            print("暂无任务")
        ```
    """
    if agent_id is None:
        agent_id = os.getenv("OPC_AGENT_ID", "unknown")
    
    response = _make_request(
        "GET",
        f"/api/agents/{agent_id}/task"
    )
    
    if response["success"]:
        return response["data"]
    else:
        return {
            "has_task": False,
            "error": response.get("error", "Unknown error")
        }


def opc_get_budget(agent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get current budget status from OPC Core Service.
    
    Args:
        agent_id: Optional agent ID
    
    Returns:
        Budget information including:
        - monthly_budget: Total monthly budget
        - used_budget: Amount used
        - remaining_budget: Amount remaining
        - mood_emoji: Current mood based on budget
    """
    if agent_id is None:
        agent_id = os.getenv("OPC_AGENT_ID", "unknown")
    
    response = _make_request(
        "GET",
        f"/api/budget/agents/{agent_id}"
    )
    
    if response["success"]:
        return response["data"]
    else:
        return {
            "error": response.get("error", "Unknown error")
        }


# Convenience aliases for OpenClaw Skill naming convention
def report_task(
    task_id: str,
    token_used: int,
    result_summary: str = "",
    status: str = "completed"
) -> Dict[str, Any]:
    """Alias for opc_report()"""
    return opc_report(task_id, token_used, result_summary, status)


def check_task() -> Dict[str, Any]:
    """Alias for opc_check_task()"""
    return opc_check_task()


def get_budget() -> Dict[str, Any]:
    """Alias for opc_get_budget()"""
    return opc_get_budget()
