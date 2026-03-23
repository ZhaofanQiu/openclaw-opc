#!/usr/bin/env python3
"""
OPC Bridge - 查询预算
用法: python3 opc-get-budget.py
"""

import os
import json
import urllib.request

OPC_CORE_URL = os.getenv("OPC_CORE_URL", "http://localhost:8080")
agent_id = os.getenv("OPC_AGENT_ID", os.getenv("USER", "unknown"))

url = f"{OPC_CORE_URL}/api/agents/by-openclaw/{agent_id}"
headers = {"Accept": "application/json"}

try:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f"Agent: {result.get('name')}")
        print(f"Budget: {result.get('used_budget', 0)}/{result.get('monthly_budget', 0)} OC coins")
        print(f"Remaining: {result.get('remaining_budget', 0)} OC coins")
        print(f"Status: {result.get('status')}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}", file=os.sys.stderr)
    exit(1)
