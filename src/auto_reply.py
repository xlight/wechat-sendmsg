#!/usr/bin/env python3
"""
自动回复编排器
串联 MessageListener -> AIClient -> WeChatController 的完整流程。
支持速率限制、AI 调用失败降级回复、优雅停止。
"""

import asyncio
import logging
import signal
import sys
import time
from collections import deque
from typing import Deque, Optional

from ai_integration import AIClient
from config import Config
from http_server import HTTPServer
from message_listener import MentionMessage, MessageListener, gui_lock
from wechat_controller import WeChatController

logger = logging.getLogger(__name__)


class RateLimiter:
    """基于滑动窗口的速率限制器。"""

    def __init__(self, max_per_minute: int):
        self._max = max_per_minute
        self._timestamps: Deque[float] = deque()

    def allow(self) -> bool:
        """检查当前是否允许一次调用。"""
        now = time.time()
        # 清理 1 分钟前的记录
        while self._timestamps and now - self._timestamps[0] > 60:
            self._timestamps.popleft()
        if len(self._timestamps) >= self._max:
            return False
        self._timestamps.append(now)
        return True


class AutoReplyOrchestrator:
    """自动回复编排器，串联监听、AI 分析、回复发送。"""

    def __init__(self, config: Config):
        self._config = config
        self._controller = WeChatController()
        self._ai_client = AIClient(config)
        self._rate_limiter = RateLimiter(config.rate_limit_per_minute)

        # 消息监听器（注册 @ 提及回调）
        self._listener = MessageListener(
            config=config,
            controller=self._controller,
            on_mention=self._handle_mention,
        )

        # HTTP 服务器
        self._http_server = HTTPServer(
            config=config,
            controller=self._controller,
            listener=self._listener,
            ai_configured=self._ai_client.is_configured,
        )

        self._shutting_down = False

    async def _handle_mention(self, mention: MentionMessage) -> None:
        """处理 @ 提及消息：调用 AI -> 发送回复。"""
        logger.info(f"处理 @ 提及 - 群: {mention.group_name}, 发送者: {mention.sender}")

        # 速率限制检查
        if not self._rate_limiter.allow():
            logger.warning("AI 调用速率超限，发送限流提示")
            await self._send_reply(mention.group_name, "请求过于频繁，请稍后再试")
            return

        # 调用 AI 服务
        try:
            reply = await self._ai_client.chat(mention.content)
        except Exception as e:
            logger.error(f"AI 调用异常: {e}")
            reply = "抱歉，AI 服务暂时不可用"

        # 发送回复到群聊
        await self._send_reply(mention.group_name, reply)

    async def _send_reply(self, group_name: str, message: str) -> None:
        """通过 GUI 互斥锁发送回复到群聊。"""
        try:
            async with gui_lock:
                result = await self._controller.send_text_message(group_name, message)
            if result.get("ok"):
                logger.info(f"回复已发送到群聊: {group_name}")
            else:
                logger.error(f"回复发送失败: {result}")
        except Exception as e:
            logger.error(f"发送回复时出错: {e}")

    async def start(self) -> None:
        """启动所有组件。"""
        logger.info("正在启动自动回复服务...")

        # 检查微信状态
        status = self._controller.get_status()
        if not status.get("wechat_available"):
            logger.error("微信未运行，消息监听器不会启动（HTTP API 仍可用）")
        else:
            logger.info(f"微信状态: {status.get('framework_type')}")

        # 启动 HTTP 服务器
        await self._http_server.start()

        # 启动消息监听器（微信可用时）
        if status.get("wechat_available") and status.get("supported"):
            await self._listener.start()
        else:
            logger.warning("微信不可用或版本不支持，跳过消息监听器启动")

        logger.info("自动回复服务已启动")

    async def stop(self) -> None:
        """优雅停止所有组件。"""
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("正在停止自动回复服务...")

        # 先停止监听器（不再产生新任务）
        await self._listener.stop()

        # 再停止 HTTP 服务器
        await self._http_server.stop()

        logger.info("自动回复服务已停止")


async def main() -> None:
    """统一启动入口。"""
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,  # 改为 DEBUG 查看详细日志
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    config = Config()
    orchestrator = AutoReplyOrchestrator(config)

    # 注册信号处理（优雅停止）
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("收到停止信号")
        stop_event.set()

    # Windows 上 signal 处理有限制，使用兼容方式
    if sys.platform == "win32":
        # Windows 不支持 loop.add_signal_handler，使用 signal 模块
        signal.signal(signal.SIGINT, lambda s, f: _signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: _signal_handler())
    else:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    await orchestrator.start()

    # 等待停止信号
    await stop_event.wait()

    await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
