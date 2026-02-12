#!/usr/bin/env python3
"""
系统托盘应用模块
以 Windows 系统托盘图标形式运行微信 MCP 服务器，后台线程运行 uvicorn HTTP 服务器。
"""

import asyncio
import logging
import os
import threading
import webbrowser
from typing import Any, Optional

import pystray
import uvicorn
from PIL import Image
from starlette.applications import Starlette

from paths import get_assets_dir

logger = logging.getLogger(__name__)

# 应用名称
APP_NAME = "微信 MCP 服务器"


class SystrayApp:
    """系统托盘应用，管理托盘图标和后台 uvicorn 服务器。

    主线程运行 pystray 消息循环（Win32 消息泵），
    后台 daemon 线程运行 uvicorn 服务器。
    """

    def __init__(
        self,
        app: Starlette,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        """初始化系统托盘应用。

        Args:
            app: Starlette ASGI 应用实例
            host: HTTP 服务器监听地址
            port: HTTP 服务器监听端口
        """
        self._app = app
        self._host = host
        self._port = port
        self._icon: Optional[pystray.Icon] = None
        self._server: Optional[uvicorn.Server] = None
        self._server_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # 图标加载
    # ------------------------------------------------------------------

    def _load_icon(self) -> Image.Image:
        """加载托盘图标。

        优先从 assets/icon.ico 加载，不存在时使用 Pillow 动态生成备用图标。

        Returns:
            PIL Image 对象
        """
        icon_path = os.path.join(get_assets_dir(), "icon.ico")

        if os.path.isfile(icon_path):
            try:
                img = Image.open(icon_path)
                logger.info(f"已加载托盘图标: {icon_path}")
                return img
            except Exception as e:
                logger.warning(f"加载图标文件失败: {e}，使用备用图标")

        # 备用图标：绿色方块
        logger.info("使用 Pillow 生成备用托盘图标")
        img = Image.new("RGBA", (64, 64), (7, 193, 96, 255))
        return img

    # ------------------------------------------------------------------
    # 托盘菜单
    # ------------------------------------------------------------------

    def _create_menu(self) -> pystray.Menu:
        """创建托盘右键菜单。

        菜单项：
        1. 状态信息行（灰色不可点击）
        2. 打开管理页面
        3. 分隔线
        4. 退出

        Returns:
            pystray.Menu 实例
        """
        return pystray.Menu(
            pystray.MenuItem(
                f"{APP_NAME} - 运行中 (:{self._port})",
                action=None,
                enabled=False,
            ),
            pystray.MenuItem(
                "打开管理页面",
                self._on_open_web,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "退出",
                self._on_exit,
            ),
        )

    # ------------------------------------------------------------------
    # 菜单回调
    # ------------------------------------------------------------------

    def _on_open_web(self, icon: Any, item: Any) -> None:
        """点击"打开管理页面"：在默认浏览器中打开 Web UI。"""
        url = f"http://localhost:{self._port}"
        logger.info(f"打开管理页面: {url}")
        webbrowser.open(url)

    def _on_exit(self, icon: Any, item: Any) -> None:
        """点击"退出"：触发优雅关闭流程。"""
        logger.info("用户请求退出...")
        self._shutdown()

    # ------------------------------------------------------------------
    # 服务器线程
    # ------------------------------------------------------------------

    def _run_server(self) -> None:
        """在后台线程中运行 uvicorn 服务器。

        创建独立的 asyncio 事件循环，运行 uvicorn.Server.serve()。
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            config = uvicorn.Config(
                app=self._app,
                host=self._host,
                port=self._port,
                log_level="info",
            )
            self._server = uvicorn.Server(config)

            logger.info(f"uvicorn 服务器启动中: http://{self._host}:{self._port}")
            loop.run_until_complete(self._server.serve())
        except Exception as e:
            logger.error(f"uvicorn 服务器异常: {e}", exc_info=True)
        finally:
            logger.info("uvicorn 服务器线程已结束")

    # ------------------------------------------------------------------
    # 优雅关闭
    # ------------------------------------------------------------------

    def _shutdown(self) -> None:
        """优雅关闭：通知 uvicorn 停止 → 移除托盘图标 → 退出程序。"""
        # 1. 通知 uvicorn 关闭
        if self._server is not None:
            logger.info("正在关闭 uvicorn 服务器...")
            self._server.should_exit = True

        # 2. 等待服务器线程结束（最多 10 秒）
        if self._server_thread is not None and self._server_thread.is_alive():
            self._server_thread.join(timeout=10.0)
            if self._server_thread.is_alive():
                logger.warning("uvicorn 服务器线程关闭超时")

        # 3. 移除托盘图标
        if self._icon is not None:
            logger.info("正在移除托盘图标...")
            self._icon.stop()

    # ------------------------------------------------------------------
    # 入口方法
    # ------------------------------------------------------------------

    def run(self) -> None:
        """启动系统托盘应用。

        1. 启动后台 daemon 线程运行 uvicorn 服务器
        2. 主线程运行 pystray 托盘消息循环（阻塞直到退出）
        """
        # 启动服务器后台线程
        self._server_thread = threading.Thread(
            target=self._run_server,
            name="uvicorn-server",
            daemon=True,
        )
        self._server_thread.start()
        logger.info("uvicorn 服务器后台线程已启动")

        # 创建并运行托盘图标（主线程阻塞）
        icon_image = self._load_icon()
        self._icon = pystray.Icon(
            name="wechat-mcp-server",
            icon=icon_image,
            title=APP_NAME,
            menu=self._create_menu(),
        )

        logger.info(f"系统托盘应用已启动，服务地址: http://{self._host}:{self._port}")
        self._icon.run()

        # pystray.Icon.run() 返回后，程序退出
        logger.info("系统托盘应用已退出")
