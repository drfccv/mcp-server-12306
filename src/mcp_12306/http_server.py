"""MCP Server 12306 — Streamable HTTP 传输层（mcp SDK v2 原生实现）

基于 mcp SDK 的 low-level Server + ``streamable_http_app()`` 构建，
同一 Server 实例（``server.py``）同时服务 stdio 与 HTTP 两种传输。
SDK 自动协商协议版本：2025 握手时代（2024-11-05 ~ 2025-11-25）与
2026-07-28 现代协议，无需手工处理 JSON-RPC。

业务逻辑全部委托给 services.ticket_service 共享模块。
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from datetime import datetime

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
import uvicorn

from mcp.server.transport_security import TransportSecuritySettings
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION

from .services.ticket_service import (
    SERVER_NAME,
    SERVER_VERSION,
    MCP_TOOLS,
    station_service,
    settings,
    logger,
)
from .server import server

#: MCP Streamable HTTP 端点路径
MCP_ENDPOINT = "/mcp"

def _build_transport_security() -> TransportSecuritySettings | None:
    """根据绑定地址决定 DNS-rebinding 防护策略。

    - 绑定 localhost 时返回 None，交由 SDK 自动启用防护（默认即安全）。
    - 绑定 0.0.0.0 等非 localhost 地址时保持与旧版一致的可达性
      （不校验 Host/Origin）；生产环境建议将 ``server_host`` 配置为
      具体主机名，并在此显式配置 allowed_hosts / allowed_origins。
    """
    if settings.server_host in ("127.0.0.1", "localhost", "::1"):
        return None
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


def _active_sessions() -> int:
    """当前活跃的 MCP 会话数。

    防御式读取 SDK 内部会话表，仅统计未终止的 transport
    （DELETE 终止后的 transport 会被 SDK 保留在表中但已失效）。
    """
    manager = getattr(server, "session_manager", None)
    instances = getattr(manager, "_server_instances", None)
    if not instances:
        return 0
    return sum(1 for t in instances.values() if not getattr(t, "is_terminated", True))


async def root_info(_request: Request) -> JSONResponse:
    """服务信息（含协议版本能力）。"""
    return JSONResponse(
        {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "status": "running",
            "mcp_endpoint": MCP_ENDPOINT,
            "protocol_versions": {
                "handshake": LATEST_HANDSHAKE_VERSION,
                "modern": LATEST_MODERN_VERSION,
            },
            "transport": "Streamable HTTP (mcp SDK v2)",
            "stations_loaded": len(station_service.stations),
            "tools": [tool["name"] for tool in MCP_TOOLS],
            "active_sessions": _active_sessions(),
        }
    )


async def health(_request: Request) -> JSONResponse:
    """健康检查。"""
    return JSONResponse(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "stations": len(station_service.stations),
            "active_sessions": _active_sessions(),
        }
    )


async def schema_tools(_request: Request) -> JSONResponse:
    """工具 JSON Schema（兼容旧版 /schema/tools 端点）。"""
    return JSONResponse(
        {
            "tools": MCP_TOOLS,
            "schema_version": "http://json-schema.org/draft-07/schema#",
        }
    )


@contextlib.asynccontextmanager
async def lifespan(_app: Starlette) -> AsyncIterator[None]:
    """宿主应用生命周期：加载车站数据 + 启动 MCP 会话管理器。

    注意：MCP 子应用被 Mount 后其自带 lifespan 不会运行，必须由
    宿主应用进入 ``server.session_manager.run()``。
    """
    logger.info("启动12306 MCP服务器 (Streamable HTTP)...")
    logger.info(
        f"协议版本: 握手 {LATEST_HANDSHAKE_VERSION} / 现代 {LATEST_MODERN_VERSION}"
    )
    logger.info("正在加载车站数据...")
    await station_service.load_stations()
    logger.info(f"已加载 {len(station_service.stations)} 个车站")
    try:
        async with server.session_manager.run():
            yield
    finally:
        logger.info("MCP服务器已关闭")


# MCP 子应用：SDK 原生实现，双协议时代自动协商
mcp_app = server.streamable_http_app(
    streamable_http_path=MCP_ENDPOINT,
    transport_security=_build_transport_security(),
    debug=settings.debug,
)

# 宿主应用：自定义端点在前，Mount("/") 兜底 MCP 端点（Starlette 按序匹配）
app = Starlette(
    routes=[
        Route("/", root_info, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Route("/schema/tools", schema_tools, methods=["GET"]),
        Mount("/", app=mcp_app),
    ],
    lifespan=lifespan,
)

# CORS：浏览器客户端需能发送 Mcp-* 请求头并读取 Mcp-Session-Id 响应头
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


async def main_server() -> None:
    """以 uvicorn 运行 HTTP 服务器。"""
    logger.info(
        f"MCP端点: http://{settings.server_host}:{settings.server_port}{MCP_ENDPOINT}"
    )
    logger.info(f"健康检查: http://{settings.server_host}:{settings.server_port}/health")

    config = uvicorn.Config(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
    )
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()


def main() -> None:
    """HTTP 模式 CLI 入口。"""
    asyncio.run(main_server())


if __name__ == "__main__":
    main()
