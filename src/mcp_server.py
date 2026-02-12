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
from message_queue import MessageQueue, QueueWorker
from paths import get_base_dir, get_static_dir
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

# ── 全局消息队列引用（在 lifespan 中赋值） ──
_message_queue: Optional[MessageQueue] = None
_queue_worker: Optional[QueueWorker] = None


@mcp.tool()
async def send_wechat_message(
    contact_name: str,
    message: str,
    mode: str = "queue",
    priority: int = 5,
) -> str:
    """向微信联系人或群组发送文本消息。

    Args:
        contact_name: 要发送消息的微信联系人或群组名称
        message: 要发送的文本消息内容
        mode: 发送模式，'queue'（默认，异步入队）或 'sync'（同步立即发送）
        priority: 消息优先级，0-10，数值越小优先级越高，默认 5
    """
    global _message_queue, _queue_worker

    # 优先级范围校验
    priority = max(0, min(10, priority))

    # 队列模式：如果队列可用，将消息入队
    if mode == "queue" and _message_queue is not None:
        msg_id = _message_queue.enqueue(
            contact_name=contact_name,
            message=message,
            mode="queue",
            priority=priority,
        )
        return f"消息已加入发送队列: id={msg_id}, 联系人={contact_name}, 优先级={priority}"

    # 同步模式：暂停 worker，立即执行
    if mode == "sync" and _queue_worker is not None:
        result = await _queue_worker.execute_sync(contact_name, message)
        if isinstance(result, dict) and result.get("ok"):
            return f"消息已成功发送给 {contact_name}（同步模式）"
        if isinstance(result, dict):
            stage = result.get("stage", "unknown")
            reason = result.get("reason", "unknown")
            return f"消息发送失败（同步模式）: stage={stage}, reason={reason}"
        return "消息发送失败（同步模式）: 未知错误"

    # 回退：直接调用控制器（队列不可用时的兼容路径）
    result = await controller.send_text_message(contact_name, message)

    if isinstance(result, dict) and result.get("ok"):
        return f"消息已成功发送给 {contact_name}"

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
    contact_name: str,
    message: str,
    delay_seconds: float,
    priority: int = 5,
) -> str:
    """安排在延迟后发送微信消息。

    Args:
        contact_name: 要发送消息的微信联系人或群组名称
        message: 要发送的文本消息内容
        delay_seconds: 发送消息前的延迟秒数
        priority: 消息优先级，0-10，数值越小优先级越高，默认 5
    """
    global _message_queue

    priority = max(0, min(10, priority))

    # 如果队列可用，使用队列的延迟入队
    if _message_queue is not None:
        msg_id = _message_queue.enqueue(
            contact_name=contact_name,
            message=message,
            mode="queue",
            priority=priority,
            delay_seconds=delay_seconds,
        )
        return (
            f"消息已安排在 {delay_seconds} 秒后发送给 {contact_name}: "
            f"id={msg_id}, 优先级={priority}"
        )

    # 回退：使用旧的 asyncio 方式
    success = await controller.schedule_message(contact_name, message, delay_seconds)
    if success:
        return f"消息已安排在 {delay_seconds} 秒后发送给 {contact_name}"
    return "消息安排失败"


@mcp.tool()
async def get_queue_status() -> str:
    """查看消息队列状态概览。"""
    global _message_queue, _queue_worker

    if _message_queue is None:
        return "消息队列未初始化"

    stats = _message_queue.get_stats()
    worker_status = "运行中" if (_queue_worker and _queue_worker.is_running) else "已停止"

    lines = [
        "=== 消息队列状态 ===",
        f"Worker 状态: {worker_status}",
        f"待发送 (pending): {stats['pending']}",
        f"发送中 (processing): {stats['processing']}",
        f"已完成 (completed): {stats['completed']}",
        f"已失败 (failed): {stats['failed']}",
        f"已取消 (cancelled): {stats['cancelled']}",
        f"总计: {stats['total']}",
    ]
    return "\n".join(lines)


@mcp.tool()
async def get_message_detail(message_id: int) -> str:
    """查看指定消息的详细信息。

    Args:
        message_id: 消息 ID
    """
    global _message_queue

    if _message_queue is None:
        return "消息队列未初始化"

    msg = _message_queue.get_message(message_id)
    if msg is None:
        return f"消息不存在: id={message_id}"

    lines = [
        f"=== 消息详情 (ID: {msg['id']}) ===",
        f"联系人: {msg['contact_name']}",
        f"消息内容: {msg['message']}",
        f"状态: {msg['status']}",
        f"模式: {msg['mode']}",
        f"优先级: {msg['priority']}",
        f"重试次数: {msg['retry_count']}/{msg['max_retries']}",
        f"创建时间: {msg['created_at']}",
        f"计划时间: {msg['scheduled_at']}",
        f"更新时间: {msg['updated_at']}",
    ]
    if msg.get("error_message"):
        lines.append(f"错误信息: {msg['error_message']}")
    return "\n".join(lines)


@mcp.tool()
async def cancel_queue_message(message_id: int) -> str:
    """取消待发送的消息。

    Args:
        message_id: 要取消的消息 ID
    """
    global _message_queue

    if _message_queue is None:
        return "消息队列未初始化"

    result = _message_queue.cancel_message(message_id)
    if result["ok"]:
        return f"消息已取消: id={message_id}"
    return f"取消失败: {result['error']}"


@mcp.tool()
async def retry_queue_message(message_id: int) -> str:
    """重试失败的消息。

    Args:
        message_id: 要重试的消息 ID
    """
    global _message_queue

    if _message_queue is None:
        return "消息队列未初始化"

    result = _message_queue.retry_message(message_id)
    if result["ok"]:
        return f"消息已重新加入队列: id={message_id}"
    return f"重试失败: {result['error']}"


# ==============================================================================
# HTTP API 端点（Starlette 路由）
# ==============================================================================


async def handle_send_message(request: Request) -> JSONResponse:
    """处理发送消息请求 — POST /api/v1/messages/send

    支持 mode（queue/sync）和 priority（0-10）参数。
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"ok": False, "error": "无效的 JSON 请求体"}, status_code=400
        )

    contact_name = body.get("contact_name")
    message = body.get("message")
    mode = body.get("mode", "queue")
    priority = body.get("priority", 5)

    if not contact_name:
        return JSONResponse(
            {"ok": False, "error": "缺少必填参数: contact_name"}, status_code=400
        )
    if not message:
        return JSONResponse(
            {"ok": False, "error": "缺少必填参数: message"}, status_code=400
        )
    if mode not in ("queue", "sync"):
        return JSONResponse(
            {"ok": False, "error": "mode 参数无效，只支持 'queue' 或 'sync'"}, status_code=400
        )
    if not isinstance(priority, int) or priority < 0 or priority > 10:
        return JSONResponse(
            {"ok": False, "error": "priority 参数无效，需为 0-10 的整数"}, status_code=400
        )

    try:
        mq: Optional[MessageQueue] = getattr(request.app.state, "message_queue", None)
        worker: Optional[QueueWorker] = getattr(request.app.state, "queue_worker", None)

        # 队列模式
        if mode == "queue" and mq is not None:
            delay_seconds = body.get("delay_seconds", 0.0)
            msg_id = mq.enqueue(
                contact_name=contact_name,
                message=message,
                mode="queue",
                priority=priority,
                delay_seconds=float(delay_seconds),
            )
            return JSONResponse({
                "ok": True,
                "mode": "queue",
                "message_id": msg_id,
                "message": f"消息已加入发送队列: id={msg_id}",
            })

        # 同步模式
        if mode == "sync" and worker is not None:
            result = await worker.execute_sync(contact_name, message)
            if isinstance(result, dict) and result.get("ok"):
                return JSONResponse({
                    "ok": True,
                    "mode": "sync",
                    "message": "消息已成功发送（同步模式）",
                })
            return JSONResponse(
                {"ok": False, "mode": "sync", "error": "消息发送失败", "details": result},
                status_code=500,
            )

        # 回退：直接调用控制器
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


async def handle_queue_status(request: Request) -> JSONResponse:
    """队列状态概览 — GET /api/v1/queue/status"""
    mq: Optional[MessageQueue] = getattr(request.app.state, "message_queue", None)
    worker: Optional[QueueWorker] = getattr(request.app.state, "queue_worker", None)

    if mq is None:
        return JSONResponse(
            {"ok": False, "error": "消息队列未初始化"}, status_code=503
        )

    stats = mq.get_stats()
    return JSONResponse({
        "ok": True,
        "worker_running": worker.is_running if worker else False,
        "stats": stats,
    })


async def handle_queue_messages(request: Request) -> JSONResponse:
    """消息列表 — GET /api/v1/queue/messages"""
    mq: Optional[MessageQueue] = getattr(request.app.state, "message_queue", None)

    if mq is None:
        return JSONResponse(
            {"ok": False, "error": "消息队列未初始化"}, status_code=503
        )

    status = request.query_params.get("status")
    limit = int(request.query_params.get("limit", "20"))
    offset = int(request.query_params.get("offset", "0"))

    # 限制最大分页大小
    limit = min(limit, 100)

    messages, total = mq.list_messages(status=status, limit=limit, offset=offset)
    return JSONResponse({
        "ok": True,
        "messages": messages,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


async def handle_queue_message_detail(request: Request) -> JSONResponse:
    """单条消息详情 — GET /api/v1/queue/messages/{id}"""
    mq: Optional[MessageQueue] = getattr(request.app.state, "message_queue", None)

    if mq is None:
        return JSONResponse(
            {"ok": False, "error": "消息队列未初始化"}, status_code=503
        )

    message_id = int(request.path_params["id"])
    msg = mq.get_message(message_id)

    if msg is None:
        return JSONResponse(
            {"ok": False, "error": f"消息不存在: id={message_id}"}, status_code=404
        )

    return JSONResponse({"ok": True, "message": msg})


async def handle_queue_cancel(request: Request) -> JSONResponse:
    """取消消息 — POST /api/v1/queue/messages/{id}/cancel"""
    mq: Optional[MessageQueue] = getattr(request.app.state, "message_queue", None)

    if mq is None:
        return JSONResponse(
            {"ok": False, "error": "消息队列未初始化"}, status_code=503
        )

    message_id = int(request.path_params["id"])
    result = mq.cancel_message(message_id)

    if result["ok"]:
        return JSONResponse({"ok": True, "message": f"消息已取消: id={message_id}"})
    return JSONResponse({"ok": False, "error": result["error"]}, status_code=400)


async def handle_queue_retry(request: Request) -> JSONResponse:
    """重试消息 — POST /api/v1/queue/messages/{id}/retry"""
    mq: Optional[MessageQueue] = getattr(request.app.state, "message_queue", None)

    if mq is None:
        return JSONResponse(
            {"ok": False, "error": "消息队列未初始化"}, status_code=503
        )

    message_id = int(request.path_params["id"])
    result = mq.retry_message(message_id)

    if result["ok"]:
        return JSONResponse({"ok": True, "message": f"消息已重新加入队列: id={message_id}"})
    return JSONResponse({"ok": False, "error": result["error"]}, status_code=400)


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
    index_path = os.path.join(get_static_dir(), "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return JSONResponse({"error": "index.html not found"}, status_code=404)


async def handle_test_page(request: Request) -> FileResponse:
    """测试页面 — GET /test"""
    test_path = os.path.join(get_static_dir(), "test.html")
    if os.path.isfile(test_path):
        return FileResponse(test_path, media_type="text/html")
    return JSONResponse({"error": "test.html not found"}, status_code=404)


async def handle_queue_page(request: Request) -> FileResponse:
    """队列管理页面 — GET /queue"""
    queue_path = os.path.join(get_static_dir(), "queue.html")
    if os.path.isfile(queue_path):
        return FileResponse(queue_path, media_type="text/html")
    return JSONResponse({"error": "queue.html not found"}, status_code=404)


# ==============================================================================
# 统一 Starlette 应用（HTTP API + MCP Streamable HTTP）
# ==============================================================================


def create_starlette_app() -> Starlette:
    """创建统一的 Starlette ASGI 应用。

    包含：
    - MCP Streamable HTTP 端点 (/mcp)
    - HTTP API 端点 (/api/v1/*)
    - 队列管理 API (/api/v1/queue/*)
    - 静态文件服务 (/static/*)
    - 根路径、测试页面和队列管理页面
    """
    # 获取 MCP 的 streamable HTTP ASGI 子应用
    mcp_app = mcp.streamable_http_app()

    # 从 mcp_app 中提取 StreamableHTTPASGIApp 端点
    # mcp_app 内部有一个 Route("/", endpoint=StreamableHTTPASGIApp)
    # 我们直接将它注册到顶层的 /mcp 路由，避免 Mount 导致的 307 重定向
    mcp_endpoint = mcp_app.routes[0].endpoint

    # 项目根目录下的 static 文件夹
    static_dir = get_static_dir()

    # 构建路由
    routes = [
        # MCP Streamable HTTP 端点 — 直接注册避免 Mount 的尾斜杠重定向
        Route("/mcp", endpoint=mcp_endpoint),
        # HTTP API 端点 — 消息发送
        Route("/api/v1/messages/send", handle_send_message, methods=["POST"]),
        # HTTP API 端点 — 队列管理
        Route("/api/v1/queue/status", handle_queue_status, methods=["GET"]),
        Route("/api/v1/queue/messages", handle_queue_messages, methods=["GET"]),
        Route("/api/v1/queue/messages/{id:int}", handle_queue_message_detail, methods=["GET"]),
        Route("/api/v1/queue/messages/{id:int}/cancel", handle_queue_cancel, methods=["POST"]),
        Route("/api/v1/queue/messages/{id:int}/retry", handle_queue_retry, methods=["POST"]),
        # HTTP API 端点 — 状态与配置
        Route("/api/v1/status", handle_status, methods=["GET"]),
        Route("/api/v1/anti-ban/stats", handle_anti_ban_stats, methods=["GET"]),
        Route("/api/v1/anti-ban/config", handle_anti_ban_config, methods=["GET"]),
        # 页面路由
        Route("/", handle_index, methods=["GET"]),
        Route("/test", handle_test_page, methods=["GET"]),
        Route("/queue", handle_queue_page, methods=["GET"]),
    ]

    # 静态文件服务（如果目录存在）
    if os.path.isdir(static_dir):
        routes.append(Mount("/static", app=StaticFiles(directory=static_dir)))

    @asynccontextmanager
    async def lifespan(app: Starlette):
        """管理 MCP session_manager 和消息队列 Worker 的生命周期。"""
        global _message_queue, _queue_worker

        async with mcp.session_manager.run():
            logger.info("MCP session manager 已启动")

            # 初始化消息队列
            message_queue = MessageQueue(
                db_path=config.queue_db_path,
                max_retries=config.queue_max_retries,
            )
            recovered = message_queue.recover()
            if recovered > 0:
                logger.info(f"已恢复 {recovered} 条中断的消息")

            # 启动 worker
            worker = QueueWorker(
                queue=message_queue,
                controller=controller,
                poll_interval=config.queue_poll_interval,
            )
            await worker.start()

            # 挂到 app.state 供路由处理函数访问
            app.state.message_queue = message_queue
            app.state.queue_worker = worker

            # 同步更新全局引用，供 MCP 工具访问
            _message_queue = message_queue
            _queue_worker = worker

            logger.info("消息队列和 Worker 已启动")
            yield

            # 清理
            await worker.stop()
            _message_queue = None
            _queue_worker = None
            logger.info("消息队列 Worker 已停止")

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
    """主入口点：解析命令行参数，选择传输模式启动服务器。

    运行模式：
    - python src/mcp_server.py                                    → stdio 模式
    - python src/mcp_server.py --transport streamable-http        → 控制台 HTTP 模式
    - python src/mcp_server.py --transport streamable-http --systray → 托盘 + HTTP 模式
    - 编译后的 .exe（无参数）                                      → 托盘 + HTTP 模式
    """
    # 检测编译模式
    compiled = "__compiled__" in dir()

    parser = argparse.ArgumentParser(description="微信 MCP 服务器")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="streamable-http" if compiled else "stdio",
        help="传输模式 (默认: 编译模式为 streamable-http，源码模式为 stdio)",
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
    parser.add_argument(
        "--systray",
        action="store_true",
        default=compiled,  # 编译模式下默认启用系统托盘
        help="以系统托盘模式运行 (默认: 编译模式自动启用)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        # stdio 模式：仅 MCP 功能，通过标准输入/输出通信
        # stdio 模式不支持托盘，忽略 --systray 参数
        if args.systray and not compiled:
            logger.warning("stdio 模式不支持系统托盘，忽略 --systray 参数")
        logger.info("以 stdio 传输模式启动 MCP 服务器")
        mcp.run(transport="stdio")

    elif args.transport == "streamable-http":
        import uvicorn

        port = args.port or config.http_port
        host = args.host

        logger.info(f"以 streamable-http 模式启动统一服务器: http://{host}:{port}")
        logger.info("可用端点:")
        logger.info(f"  MCP:    http://{host}:{port}/mcp")
        logger.info(f"  API:    http://{host}:{port}/api/v1/...")
        logger.info(f"  Queue:  http://{host}:{port}/api/v1/queue/...")
        logger.info(f"  Web:    http://{host}:{port}/")
        logger.info(f"  队列管理: http://{host}:{port}/queue")

        app = create_starlette_app()

        if args.systray:
            # 系统托盘模式：后台线程运行 uvicorn，主线程运行托盘图标
            from systray_app import SystrayApp

            logger.info("以系统托盘模式启动...")
            systray = SystrayApp(app=app, host=host, port=port)
            systray.run()
        else:
            # 控制台模式：uvicorn 直接阻塞主线程
            uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
