"""
opc-openclaw: 测试工具函数

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import json
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock

import httpx
import respx


class MockOpenClawServer:
    """Mock OpenClaw 服务器，用于测试"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.responses: Dict[str, Any] = {}
        self.call_history: list = []
    
    def add_response(self, method: str, path: str, response: Dict[str, Any], status: int = 200):
        """添加预设响应"""
        key = f"{method.upper()}:{path}"
        self.responses[key] = {
            "status": status,
            "json": response
        }
    
    def get_mock_response(self, method: str, path: str) -> tuple:
        """获取 Mock 响应"""
        key = f"{method.upper()}:{path}"
        if key in self.responses:
            resp = self.responses[key]
            return resp["status"], resp["json"]
        return 404, {"error": "Not found"}
    
    @respx.mock
    def setup_mock_routes(self):
        """设置 Mock 路由"""
        # Agent 列表
        respx.get(f"{self.base_url}/agents").mock(
            return_value=httpx.Response(200, json={
                "agents": [
                    {"id": "agent_1", "name": "Agent 1", "status": "online"},
                    {"id": "agent_2", "name": "Agent 2", "status": "offline"},
                ]
            })
        )
        
        # 创建会话
        respx.post(f"{self.base_url}/sessions").mock(
            return_value=httpx.Response(200, json={
                "session_key": "sess_test123",
                "status": "ok"
            })
        )
        
        # 发送消息
        respx.post(f"{self.base_url}/sessions/send").mock(
            return_value=httpx.Response(200, json={
                "status": "ok",
                "response": {
                    "text": "收到消息",
                    "payloads": [{"text": "收到消息"}]
                }
            })
        )


def create_mock_agent_response(
    agent_id: str = "agent_test",
    name: str = "Test Agent",
    status: str = "online",
    model: str = "kimi-coding"
) -> Dict[str, Any]:
    """创建 Mock Agent 响应"""
    return {
        "id": agent_id,
        "name": name,
        "status": status,
        "model": model
    }


def create_mock_session_response(
    session_key: str = "sess_test123",
    text: str = "Mock response",
    input_tokens: int = 100,
    output_tokens: int = 50
) -> Dict[str, Any]:
    """创建 Mock 会话响应"""
    return {
        "session_key": session_key,
        "status": "ok",
        "response": {
            "text": text,
            "payloads": [{"text": text}]
        },
        "meta": {
            "agentMeta": {
                "usage": {
                    "input": input_tokens,
                    "output": output_tokens
                }
            }
        }
    }
