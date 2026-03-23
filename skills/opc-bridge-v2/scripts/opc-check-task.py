#!/usr/bin/env python3
"""
OPC Bridge - 检查当前任务
用法: python3 opc-check-task.py
"""

import os
import json
import urllib.request

OPC_CORE_URL = os.getenv("OPC_CORE_URL", "http://localhost:8080")
agent_id = os.getenv("OPC_AGENT_ID", os.getenv("USER", "unknown"))

url = f"{OPC_CORE_URL}/api/skill/agents/{agent_id}/current-task"
headers = {"Accept": "application/json"}

try:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode('utf-8'))
        if result.get("id"):
            print(f"当前任务: {result.get('title')}")
            print(f"任务ID: {result.get('id')}")
            print(f"描述: {result.get('description', 'N/A')[:100]}...")
        else:
            print("当前没有分配的任务")
        print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}", file=os.sys.stderr)
    exit(1)
