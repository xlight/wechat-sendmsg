#!/usr/bin/env python3
"""
微信 MCP 服务器
使用官方 MCP Python SDK (FastMCP) 实现，支持 stdio 和 Streamable HTTP 传输。
Streamable HTTP 模式下同时提供 HTTP API 端点和 MCP 端点（统一 Starlette 应用）。
"""

import argparse
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

# 确保可以导入同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from wechat_controller import WeChatController

# ── 日志配置 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── 全局单例 ──
config = Config()
controller = WeChatController(config=config)

# ── 防封号模块（可选） ──
rate_limiter = None
work_time_controller = None

try:
    from anti_ban.enhanced_rate_limiter import EnhancedRateLimiter
    from anti_ban.work_time_controller import WorkTimeController

    rate_limiter = EnhancedRateLimiter(
        limit_per_minute=config.rate_limit_per_minute,
        limit_per_hour=config.rate_limit_per_hour,
        limit_per_day=config.rate_limit_per_day,
    )
    work_time_controller = WorkTimeController(
        work_hours_start=config.work_hours_start,
        work_hours_end=config.work_hours_end,
        work_days=config.work_days,
        max_daily_runtime_hours=config.max_daily_runtime_hours,
    )
    logger.info("防封号模块已加载")
except ImportError:
    logger.warning("防封号模块未加载，相关端点将不可用")


# ==============================================================================
# MCP 服务器 — 工具注册
# ==============================================================================

mcp = FastMCP(
    "wechat-mcp-server",
    instructions="微信消息发送 MCP 服务器，支持向联系人或群组发送文本消息。",
    streamable_http_path="/",  # Mount 到 /mcp 后最终路径为 /mcp
)


@mcp.tool()
async def send_wechat_message(contact_name: str, message: str) -> str:
    """向微信联系人或群组发送文本消息。

    Args:
        contact_name: 要发送消息的微信联系人或群组名称
        message: 要发送的文本消息内容
    """
    result = await controller.send_text_message(contact_name, message)

    if isinstance(result, dict) and result.get("ok"):
        return f"消息已成功发送给 {contact_name}"

    # 构建失败描述
    if isinstance(result, dict):
        stage = result.get("stage", "unknown")
        reason = result.get("reason", "unknown")
        version = result.get("wechat_version")
        is_nt = result.get("is_nt_framework")
        return (
            f"消息发送失败: stage={stage}, reason={reason}, "
            f"wechat_version={version}, nt={is_nt}"
        )

    return "消息发送失败: 未知错误"


@mcp.tool()
async def schedule_wechat_message(
    contact_name: str, message: str, delay_seconds: float
) -> str:
    """安排在延迟后发送微信消息。

    Args:
        contact_name: 要发送消息的微信联系人或群组名称
        message: 要发送的文本消息内容
        delay_seconds: 发送消息前的延迟秒数
    """
    success = await controller.schedule_message(contact_name, message, delay_seconds)

    if success:
        return f"消息已安排在 {delay_seconds} 秒后发送给 {contact_name}"
    return "消息安排失败"


# ==============================================================================
# HTTP API 端点（Starlette 路由）
# ==============================================================================


async def handle_send_message(request: Request) -> JSONResponse:
    """处理发送消息请求 — POST /api/v1/messages/send"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"ok": False, "error": "无效的 JSON 请求体"}, status_code=400
        )

    contact_name = body.get("contact_name")
    message = body.get("message")

    if not contact_name:
        return JSONResponse(
            {"ok": False, "error": "缺少必填参数: contact_name"}, status_code=400
        )
    if not message:
        return JSONResponse(
            {"ok": False, "error": "缺少必填参数: message"}, status_code=400
        )

    try:
        result = await controller.send_text_message(contact_name, message)
        if result.get("ok"):
            return JSONResponse({"ok": True, "message": "Message sent successfully"})
        return JSONResponse(
            {"ok": False, "error": "Failed to send message", "details": result},
            status_code=500,
        )
    except Exception as e:
        logger.error("发送消息时出错", exc_info=True)
        return JSONResponse(
            {"ok": False, "error": f"Internal error: {e}"}, status_code=500
        )


async def handle_status(request: Request) -> JSONResponse:
    """处理状态查询请求 — GET /api/v1/status"""
    wechat_status = controller.get_status()
    return JSONResponse({"ok": True, "wechat_status": wechat_status})


async def handle_anti_ban_stats(request: Request) -> JSONResponse:
    """处理防封号统计查询请求 — GET /api/v1/anti-ban/stats"""
    if not rate_limiter or not work_time_controller:
        return JSONResponse(
            {"ok": False, "error": "Anti-ban tools not initialized"}, status_code=503
        )

    rate_stats = rate_limiter.get_stats()
    is_work_time = work_time_controller.is_work_time()
    runtime = work_time_controller.get_runtime()
    max_runtime = config.max_daily_runtime_hours * 3600

    return JSONResponse({
        "ok": True,
        "rate_limiter": rate_stats,
        "work_time": {
            "is_work_time": is_work_time,
            "current_hour": datetime.now().hour,
            "work_hours": f"{config.work_hours_start}-{config.work_hours_end}",
            "current_day": datetime.now().weekday(),
            "work_days": config.work_days,
        },
        "runtime": {
            "current_runtime_seconds": runtime,
            "current_runtime_hours": runtime / 3600,
            "max_daily_hours": config.max_daily_runtime_hours,
            "remaining_hours": max((max_runtime - runtime) / 3600, 0),
        },
    })


async def handle_anti_ban_config(request: Request) -> JSONResponse:
    """处理防封号配置查询请求 — GET /api/v1/anti-ban/config"""
    return JSONResponse({
        "ok": True,
        "rate_limits": {
            "per_minute": config.rate_limit_per_minute,
            "per_hour": config.rate_limit_per_hour,
            "per_day": config.rate_limit_per_day,
        },
        "human_behavior": {
            "min_think_time": config.min_think_time,
            "max_think_time": config.max_think_time,
            "min_random_delay": config.min_random_delay,
            "max_random_delay": config.max_random_delay,
        },
        "work_time": {
            "hours": f"{config.work_hours_start}-{config.work_hours_end}",
            "days": config.work_days,
            "max_daily_runtime_hours": config.max_daily_runtime_hours,
        },
        "content_diversification": {
            "prefix_probability": config.prefix_probability,
            "suffix_probability": config.suffix_probability,
            "skip_probability": config.random_skip_probability,
        },
        "gui_operations": {
            "offset_range": config.gui_offset_range,
            "move_duration": (
                f"{config.gui_move_duration_min}-{config.gui_move_duration_max}s"
            ),
            "pause": f"{config.gui_pause_min}-{config.gui_pause_max}s",
        },
    })


async def handle_index(request: Request) -> FileResponse:
    """根路径返回 index.html — GET /"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(base_dir, "static", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return JSONResponse({"error": "index.html not found"}, status_code=404)


async def handle_test_page(request: Request) -> FileResponse:
    """测试页面 — GET /test"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_path = os.path.join(base_dir, "static", "test.html")
    if os.path.isfile(test_path):
        return FileResponse(test_path, media_type="text/html")
    return JSONResponse({"error": "test.html not found"}, status_code=404)


# ==============================================================================
# 统一 Starlette 应用（HTTP API + MCP Streamable HTTP）
# ==============================================================================


def create_starlette_app() -> Starlette:
    """创建统一的 Starlette ASGI 应用。

    包含：
    - MCP Streamable HTTP 端点 (/mcp)
    - HTTP API 端点 (/api/v1/*)
    - 静态文件服务 (/static/*)
    - 根路径和测试页面
    """
    # 获取 MCP 的 streamable HTTP ASGI 子应用
    mcp_app = mcp.streamable_http_app()

    # 从 mcp_app 中提取 StreamableHTTPASGIApp 端点
    # mcp_app 内部有一个 Route("/", endpoint=StreamableHTTPASGIApp)
    # 我们直接将它注册到顶层的 /mcp 路由，避免 Mount 导致的 307 重定向
    mcp_endpoint = mcp_app.routes[0].endpoint

    # 项目根目录下的 static 文件夹
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, "static")

    # 构建路由
    routes = [
        # MCP Streamable HTTP 端点 — 直接注册避免 Mount 的尾斜杠重定向
        Route("/mcp", endpoint=mcp_endpoint),
        # HTTP API 端点
        Route("/api/v1/messages/send", handle_send_message, methods=["POST"]),
        Route("/api/v1/status", handle_status, methods=["GET"]),
        Route("/api/v1/anti-ban/stats", handle_anti_ban_stats, methods=["GET"]),
        Route("/api/v1/anti-ban/config", handle_anti_ban_config, methods=["GET"]),
        # 页面路由
        Route("/", handle_index, methods=["GET"]),
        Route("/test", handle_test_page, methods=["GET"]),
    ]

    # 静态文件服务（如果目录存在）
    if os.path.isdir(static_dir):
        routes.append(Mount("/static", app=StaticFiles(directory=static_dir)))

    @asynccontextmanager
    async def lifespan(app: Starlette):
        """管理 MCP session_manager 的生命周期。"""
        async with mcp.session_manager.run():
            logger.info("MCP session manager 已启动")
            yield
        logger.info("MCP session manager 已关闭")

    # CORS 中间件
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
            allow_headers=["*"],
            expose_headers=["Mcp-Session-Id"],
        ),
    ]

    app = Starlette(
        routes=routes,
        middleware=middleware,
        lifespan=lifespan,
    )

    return app


# ==============================================================================
# 入口点
# ==============================================================================


def main():
    """主入口点：解析命令行参数，选择传输模式启动服务器。"""
    parser = argparse.ArgumentParser(description="微信 MCP 服务器")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="传输模式 (默认: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP 服务器端口 (默认: 配置文件中的 http_port)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="HTTP 服务器监听地址 (默认: 0.0.0.0)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        # stdio 模式：仅 MCP 功能，通过标准输入/输出通信
        logger.info("以 stdio 传输模式启动 MCP 服务器")
        mcp.run(transport="stdio")

    elif args.transport == "streamable-http":
        # HTTP 模式：统一 Starlette 应用（MCP + HTTP API）
        import uvicorn

        port = args.port or config.http_port
        host = args.host

        logger.info(f"以 streamable-http 模式启动统一服务器: http://{host}:{port}")
        logger.info("可用端点:")
        logger.info(f"  MCP:  http://{host}:{port}/mcp")
        logger.info(f"  API:  http://{host}:{port}/api/v1/...")
        logger.info(f"  Web:  http://{host}:{port}/")

        app = create_starlette_app()
        uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
