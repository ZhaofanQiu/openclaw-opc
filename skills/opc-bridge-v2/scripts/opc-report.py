#!/usr/bin/env python3
"""
OPC Bridge - 报告任务完成
用法: python3 opc-report.py <task_id> <token_used> [result_summary]
"""

import sys
import os
import json
import urllib.request
import urllib.error

OPC_CORE_URL = os.getenv("OPC_CORE_URL", "http://10.188.153.187:8080")

def report_task(task_id: str, token_used: int, result_summary: str = ""):
    """报告任务完成到 OPC"""
    agent_id = os.getenv("OPC_AGENT_ID", os.getenv("USER", "unknown"))
    
    url = f"{OPC_CORE_URL}/api/skill/tasks/{task_id}/report"
    data = {
        "agent_id": agent_id,
        "result": result_summary or f"任务 {task_id} 完成",
        "tokens_used": token_used
    }
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result.get("success", False)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 opc-report.py <task_id> <token_used> [result_summary]", file=sys.stderr)
        print("Example: python3 opc-report.py task_abc123 500 '任务完成'")
        sys.exit(1)
    
    task_id = sys.argv[1]
    token_used = int(sys.argv[2])
    result_summary = sys.argv[3] if len(sys.argv) > 3 else ""
    
    success = report_task(task_id, token_used, result_summary)
    sys.exit(0 if success else 1)
