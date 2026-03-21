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
    tokens_input: Optional[int] = None,
    tokens_output: Optional[int] = None,
    session_key: Optional[str] = None,
    is_exact: bool = False,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Report task completion to OPC Core Service.
    
    This function should be called by an Agent after completing a task.
    It reports token usage and triggers budget updates.
    
    Args:
        task_id: The ID of the completed task
        token_used: Number of tokens consumed (total, for backward compatibility)
        result_summary: Brief description of the work done
        status: "completed" or "failed"
        tokens_input: Actual input tokens consumed (for exact tracking)
        tokens_output: Actual output tokens consumed (for exact tracking)
        session_key: OpenClaw session identifier (for exact tracking)
        is_exact: True if token values are exact from session_status
        agent_id: Optional agent ID (auto-detected if not provided)
    
    Returns:
        Response from Core Service including:
        - success: True/False
        - cost: OC币 consumed
        - remaining_budget: Updated budget
        - fused: True if budget exceeded (task failed)
        - is_exact: Whether exact token tracking was recorded
    """
    # Get agent_id from environment if not provided
    # In OpenClaw, this could be set via session context
    if agent_id is None:
        agent_id = os.getenv("OPC_AGENT_ID", "unknown")
    
    payload = {
        "agent_id": agent_id,
        "task_id": task_id,
        "token_used": token_used,
        "result_summary": result_summary,
        "status": status,
        "is_exact": is_exact,
    }
    
    # Add exact tracking fields if provided
    if tokens_input is not None:
        payload["tokens_input"] = tokens_input
    if tokens_output is not None:
        payload["tokens_output"] = tokens_output
    if session_key is not None:
        payload["session_key"] = session_key
    
    response = _make_request(
        "POST",
        "/api/agents/report",
        data=payload
    )
    
    if response["success"]:
        return response["data"]
    else:
        return {
            "success": False,
            "error": response.get("error", "Unknown error"),
            "status_code": response.get("status_code")
        }


def opc_report_exact(
    task_id: str,
    tokens_input: int,
    tokens_output: int,
    session_key: str,
    result_summary: str = "",
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Report task completion with exact token consumption from session_status.
    
    This is a convenience wrapper that automatically sets is_exact=True
    and calculates total tokens from input + output.
    
    Args:
        task_id: The ID of the completed task
        tokens_input: Actual input tokens consumed
        tokens_output: Actual output tokens consumed
        session_key: OpenClaw session identifier
        result_summary: Brief description of work done
        agent_id: Optional agent ID
    
    Returns:
        Response from Core Service
    
    Example:
        ```python
        # Get exact token consumption from session_status
        result = opc_report_exact(
            task_id="abc123",
            tokens_input=850,
            tokens_output=673,
            session_key="session_abc123",
            result_summary="完成了登录页重构"
        )
        
        if result["success"]:
            print(f"精确报告成功，消耗 {result['cost']} OC币")
        ```
    """
    total_tokens = tokens_input + tokens_output
    
    return opc_report(
        task_id=task_id,
        token_used=total_tokens,
        result_summary=result_summary,
        status="completed",
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        session_key=session_key,
        is_exact=True,
        agent_id=agent_id
    )


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


def report_exact(
    task_id: str,
    tokens_input: int,
    tokens_output: int,
    session_key: str,
    result_summary: str = ""
) -> Dict[str, Any]:
    """Alias for opc_report_exact()"""
    return opc_report_exact(task_id, tokens_input, tokens_output, session_key, result_summary)


def check_task() -> Dict[str, Any]:
    """Alias for opc_check_task()"""
    return opc_check_task()


def get_budget() -> Dict[str, Any]:
    """Alias for opc_get_budget()"""
    return opc_get_budget()
