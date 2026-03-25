"""
opc-core: 主应用

FastAPI 应用创建和配置

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：初始化数据库
    关闭时：清理资源
    """
    # 启动
    from opc_database import init_db

    await init_db()

    yield

    # 关闭
    # 清理资源（如果有）


def create_app(
    title: str = "OpenClaw OPC API", version: str = "0.4.0", **kwargs
) -> FastAPI:
    """
    创建 FastAPI 应用

    Returns:
        FastAPI: 配置好的应用实例
    """
    app = FastAPI(
        title=title,
        version=version,
        description="OpenClaw OPC - One-Person Company Management API",
        lifespan=lifespan,
        **kwargs
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应配置具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 API 路由
    app.include_router(api_router)

    # 健康检查 (API 版本)
    @app.get("/api/v1/health")
    async def api_health_check():
        """API 健康检查端点"""
        return {"status": "ok", "version": version}

    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {"status": "ok", "version": version}

    # 根路径
    @app.get("/")
    async def root():
        """API 根路径"""
        return {"name": title, "version": version, "docs": "/docs"}

    return app
