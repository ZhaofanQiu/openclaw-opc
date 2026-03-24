"""
BaseClient 测试

使用 respx 进行 HTTP Mock 测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
import respx
from httpx import Response

from opc_openclaw.client.base import BaseClient, OpenClawAPIError


class TestBaseClient:
    """BaseClient 测试类"""
    
    def test_init_with_defaults(self):
        """测试默认初始化"""
        client = BaseClient()
        
        assert client.base_url == "http://localhost:8080"
        assert client.api_key == ""
        assert client.timeout == 30.0
    
    def test_init_with_custom_values(self):
        """测试自定义初始化"""
        client = BaseClient(
            base_url="https://api.example.com",
            api_key="test_key_123",
            timeout=60.0
        )
        
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "test_key_123"
        assert client.timeout == 60.0
    
    @respx.mock
    async def test_get_request(self):
        """测试 GET 请求"""
        # Mock API
        route = respx.get("http://localhost:8080/api/test").mock(
            return_value=Response(200, json={"status": "ok"})
        )
        
        client = BaseClient()
        response = await client.get("/api/test")
        
        assert response["status"] == "ok"
        assert route.called
    
    @respx.mock
    async def test_post_request(self):
        """测试 POST 请求"""
        route = respx.post("http://localhost:8080/api/test").mock(
            return_value=Response(201, json={"id": "123", "created": True})
        )
        
        client = BaseClient()
        response = await client.post("/api/test", json={"name": "test"})
        
        assert response["id"] == "123"
        assert route.called
    
    @respx.mock
    async def test_put_request(self):
        """测试 PUT 请求"""
        route = respx.put("http://localhost:8080/api/test/1").mock(
            return_value=Response(200, json={"updated": True})
        )
        
        client = BaseClient()
        response = await client.put("/api/test/1", json={"name": "updated"})
        
        assert response["updated"] is True
        assert route.called
    
    @respx.mock
    async def test_delete_request(self):
        """测试 DELETE 请求"""
        route = respx.delete("http://localhost:8080/api/test/1").mock(
            return_value=Response(204)
        )
        
        client = BaseClient()
        response = await client.delete("/api/test/1")
        
        assert route.called
    
    @respx.mock
    async def test_request_with_api_key(self):
        """测试带 API Key 的请求"""
        route = respx.get("http://localhost:8080/api/protected").mock(
            return_value=Response(200, json={"access": "granted"})
        )
        
        client = BaseClient(api_key="secret_token")
        await client.get("/api/protected")
        
        # 验证 Authorization 头
        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer secret_token"
    
    @respx.mock
    async def test_http_error_raises_exception(self):
        """测试 HTTP 错误抛出异常"""
        respx.get("http://localhost:8080/api/error").mock(
            return_value=Response(500, json={"error": "Internal Error"})
        )
        
        client = BaseClient()
        
        with pytest.raises(OpenClawAPIError) as exc_info:
            await client.get("/api/error")
        
        assert exc_info.value.status_code == 500
    
    @respx.mock
    async def test_context_manager(self):
        """测试异步上下文管理器"""
        respx.get("http://localhost:8080/api/test").mock(
            return_value=Response(200, json={"status": "ok"})
        )
        
        async with BaseClient() as client:
            response = await client.get("/api/test")
            assert response["status"] == "ok"
