"""
opc-core: 主应用

FastAPI 应用创建和配置

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

    # 静态文件服务 (Dashboard)
    ui_dist_path = Path(__file__).parent.parent.parent.parent / "opc-ui" / "dist"
    if ui_dist_path.exists():
        # Dashboard SPA - 所有路由返回 index.html
        from fastapi.responses import FileResponse
        
        # 根路径
        @app.get("/dashboard", response_class=FileResponse)
        async def serve_dashboard_root():
            """Dashboard 根路径"""
            return FileResponse(str(ui_dist_path / "index.html"))
        
        # 子路径 - SPA fallback
        @app.get("/dashboard/{path:path}", response_class=FileResponse)
        async def serve_dashboard_path(path: str):
            """Dashboard 子路径 - 返回 index.html 让前端路由处理"""
            # 排除 API 路径和静态资源
            if path.startswith("api/") or path.startswith("assets/"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Not Found")
            return FileResponse(str(ui_dist_path / "index.html"))
        
        # Assets 静态文件（支持绝对路径引用）
        app.mount("/assets", StaticFiles(directory=str(ui_dist_path / "assets")), name="assets")
        
        # Favicon
        @app.get("/favicon.svg")
        async def favicon():
            return FileResponse(str(ui_dist_path / "favicon.svg"))

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
