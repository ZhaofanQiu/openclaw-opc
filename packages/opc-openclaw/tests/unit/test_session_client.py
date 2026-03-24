"""
SessionClient 测试

使用 respx 进行 HTTP Mock 测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
import respx
from httpx import Response

from opc_openclaw.client.sessions import SessionClient


class TestSessionClient:
    """SessionClient 测试类"""
    
    @respx.mock
    async def test_spawn_session(self):
        """测试创建会话"""
        respx.post("http://localhost:8080/api/sessions/spawn").mock(
            return_value=Response(200, json={
                "session_key": "sess_abc123",
                "status": "ok",
                "response": "Task received"
            })
        )
        
        client = SessionClient()
        result = await client.spawn_session(
            agent_id="agent_1",
            message="执行测试任务",
            timeout=300
        )
        
        assert result["session_key"] == "sess_abc123"
        assert result["status"] == "ok"
    
    @respx.mock
    async def test_spawn_session_with_label(self):
        """测试创建带标签的会话"""
        route = respx.post("http://localhost:8080/api/sessions/spawn").mock(
            return_value=Response(200, json={
                "session_key": "sess_abc123",
                "status": "ok"
            })
        )
        
        client = SessionClient()
        await client.spawn_session(
            agent_id="agent_1",
            message="执行任务",
            label="my_task",
            cleanup="delete"
        )
        
        # 验证请求体包含 label
        request_body = route.calls[0].request.content
        assert b"my_task" in request_body
    
    @respx.mock
    async def test_send_message(self):
        """测试发送消息"""
        respx.post("http://localhost:8080/api/sessions/sess_123/send").mock(
            return_value=Response(200, json={
                "response": "Message received",
                "tokens": {"input": 10, "output": 20}
            })
        )
        
        client = SessionClient()
        result = await client.send_message(
            session_key="sess_123",
            message="继续处理"
        )
        
        assert result["response"] == "Message received"
        assert result["tokens"]["input"] == 10
    
    @respx.mock
    async def test_get_session_status(self):
        """测试获取会话状态"""
        respx.get("http://localhost:8080/api/sessions/sess_123/status").mock(
            return_value=Response(200, json={
                "session_key": "sess_123",
                "status": "active",
                "agent_id": "agent_1"
            })
        )
        
        client = SessionClient()
        status = await client.get_session_status("sess_123")
        
        assert status["status"] == "active"
        assert status["agent_id"] == "agent_1"
    
    @respx.mock
    async def test_get_session_messages(self):
        """测试获取会话消息历史"""
        respx.get("http://localhost:8080/api/sessions/sess_123/messages?limit=50").mock(
            return_value=Response(200, json={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there"}
                ]
            })
        )
        
        client = SessionClient()
        messages = await client.get_session_messages("sess_123", limit=50)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
    
    @respx.mock
    async def test_get_session_messages_default_limit(self):
        """测试获取会话消息（默认限制）"""
        route = respx.get("http://localhost:8080/api/sessions/sess_123/messages").mock(
            return_value=Response(200, json={"messages": []})
        )
        
        client = SessionClient()
        await client.get_session_messages("sess_123")
        
        # 验证使用了默认 limit=100
        request = route.calls[0].request
        assert "limit=100" in str(request.url)
    
    @respx.mock
    async def test_close_session_success(self):
        """测试关闭会话成功"""
        respx.post("http://localhost:8080/api/sessions/sess_123/close").mock(
            return_value=Response(200)
        )
        
        client = SessionClient()
        success = await client.close_session("sess_123")
        
        assert success is True
    
    @respx.mock
    async def test_close_session_failure(self):
        """测试关闭会话失败"""
        respx.post("http://localhost:8080/api/sessions/sess_123/close").mock(
            return_value=Response(500)
        )
        
        client = SessionClient()
        success = await client.close_session("sess_123")
        
        assert success is False
