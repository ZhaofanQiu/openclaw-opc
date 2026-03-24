"""
opc-openclaw: 基础客户端

OpenClaw HTTP API 客户端基类

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import os
from typing import Any, Dict, Optional

import httpx


class OpenClawAPIError(Exception):
    """OpenClaw API 错误"""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class BaseClient:
    """
    OpenClaw API 基础客户端

    提供通用的 HTTP 请求方法和配置管理
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        初始化客户端

        Args:
            base_url: OpenClaw API 基础URL，默认从环境变量读取
            api_key: API密钥，默认从环境变量读取
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or os.getenv(
            "OPENCLAW_API_URL", "http://localhost:8080"
        )
        self.api_key = api_key or os.getenv("OPENCLAW_API_KEY", "")
        self.timeout = timeout

        # 创建HTTP客户端
        self._client = httpx.AsyncClient(
            base_url=self.base_url, timeout=timeout, headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            method: HTTP方法 (GET/POST/PUT/DELETE)
            path: API路径
            **kwargs: 其他请求参数

        Returns:
            响应数据 (JSON)，空响应返回 {}

        Raises:
            OpenClawAPIError: API调用失败
        """
        try:
            response = await self._client.request(method, path, **kwargs)
            response.raise_for_status()
            # 处理空响应 (如 204 No Content)
            if not response.content:
                return {}
            return response.json()
        except httpx.HTTPStatusError as e:
            raise OpenClawAPIError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                status_code=e.response.status_code,
                response=e.response.json() if e.response.text else None,
            )
        except httpx.RequestError as e:
            raise OpenClawAPIError(f"Request failed: {str(e)}")

    async def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """GET 请求"""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """POST 请求"""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> Dict[str, Any]:
        """PUT 请求"""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """DELETE 请求"""
        return await self.request("DELETE", path, **kwargs)

    async def close(self):
        """关闭客户端连接"""
        await self._client.aclose()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
