#!/usr/bin/env python3
"""
HTTP API 服务器
基于 aiohttp 实现 RESTful 接口，提供消息发送、状态查询和配置管理端点。
"""

import logging
from typing import Any, Dict, Optional

from aiohttp import web

from config import Config
from message_listener import MessageListener, gui_lock
from wechat_controller import WeChatController

logger = logging.getLogger(__name__)


class HTTPServer:
    """基于 aiohttp 的 HTTP API 服务器。"""

    def __init__(
        self,
        config: Config,
        controller: WeChatController,
        listener: Optional[MessageListener] = None,
        ai_configured: bool = False,
    ):
        self._config = config
        self._controller = controller
        self._listener = listener
        self._ai_configured = ai_configured
        self._app = web.Application(middlewares=[self._error_middleware])
        self._runner: Optional[web.AppRunner] = None
        self._register_routes()

    # ------------------------------------------------------------------
    # 路由注册
    # ------------------------------------------------------------------
    def _register_routes(self) -> None:
        self._app.router.add_post("/api/v1/messages/send", self._handle_send_message)
        self._app.router.add_get("/api/v1/status", self._handle_status)
        self._app.router.add_get("/api/v1/config", self._handle_get_config)
        self._app.router.add_put("/api/v1/config", self._handle_put_config)

    # ------------------------------------------------------------------
    # 中间件：统一错误处理
    # ------------------------------------------------------------------
    @web.middleware
    async def _error_middleware(self, request: web.Request, handler) -> web.Response:
        try:
            response = await handler(request)
            return response
        except web.HTTPNotFound:
            return web.json_response({"ok": False, "error": "Not found"}, status=404)
        except web.HTTPMethodNotAllowed:
            return web.json_response({"ok": False, "error": "Method not allowed"}, status=405)
        except web.HTTPBadRequest as e:
            return web.json_response({"ok": False, "error": str(e.reason)}, status=400)
        except Exception as e:
            logger.error(f"HTTP 请求处理异常: {e}")
            return web.json_response({"ok": False, "error": "Internal server error"}, status=500)

    # ------------------------------------------------------------------
    # 端点：POST /api/v1/messages/send
    # ------------------------------------------------------------------
    async def _handle_send_message(self, request: web.Request) -> web.Response:
        """发送消息到指定联系人。"""
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"ok": False, "error": "Invalid JSON body"}, status=400
            )

        contact_name = body.get("contact_name")
        message = body.get("message")

        if not contact_name:
            return web.json_response(
                {"ok": False, "error": "Missing required parameter: contact_name"}, status=400
            )
        if not message:
            return web.json_response(
                {"ok": False, "error": "Missing required parameter: message"}, status=400
            )

        # 获取 GUI 互斥锁后发送消息
        async with gui_lock:
            result = await self._controller.send_text_message(contact_name, message)

        if result.get("ok"):
            return web.json_response({"ok": True, "message": "Message sent successfully"})
        else:
            return web.json_response(
                {"ok": False, "error": "Failed to send message", "details": result},
                status=500,
            )

    # ------------------------------------------------------------------
    # 端点：GET /api/v1/status
    # ------------------------------------------------------------------
    async def _handle_status(self, request: web.Request) -> web.Response:
        """返回微信状态和服务运行状态。"""
        wechat_status = self._controller.get_status()
        return web.json_response({
            "ok": True,
            "wechat_status": wechat_status,
            "listener_running": self._listener.running if self._listener else False,
            "ai_configured": self._ai_configured,
        })

    # ------------------------------------------------------------------
    # 端点：GET /api/v1/config
    # ------------------------------------------------------------------
    async def _handle_get_config(self, request: web.Request) -> web.Response:
        """返回当前配置（API 密钥脱敏）。"""
        return web.json_response({
            "ok": True,
            "config": self._config.to_dict(mask_secrets=True),
        })

    # ------------------------------------------------------------------
    # 端点：PUT /api/v1/config
    # ------------------------------------------------------------------
    async def _handle_put_config(self, request: web.Request) -> web.Response:
        """更新运行时配置。"""
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"ok": False, "error": "Invalid JSON body"}, status=400
            )

        self._config.update(body)
        return web.json_response({
            "ok": True,
            "message": "Configuration updated",
            "config": self._config.to_dict(mask_secrets=True),
        })

    # ------------------------------------------------------------------
    # 启动 / 停止
    # ------------------------------------------------------------------
    async def start(self) -> None:
        """启动 HTTP 服务器。"""
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self._config.http_port)
        await site.start()
        logger.info(f"HTTP 服务器已启动: http://0.0.0.0:{self._config.http_port}")

    async def stop(self) -> None:
        """关闭 HTTP 服务器。"""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        logger.info("HTTP 服务器已关闭")
