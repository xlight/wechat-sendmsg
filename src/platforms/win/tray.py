#!/usr/bin/env python3
"""
Windows 系统托盘实现 — pystray

封装现有 src/systray_app.py 的 SystrayApp，适配 TrayManager 接口。
"""

import logging

import pystray

from ..tray import TrayManager, APP_NAME

logger = logging.getLogger(__name__)


class WinTrayManager(TrayManager):
    """Windows 系统托盘实现。"""

    def __init__(self, app, host="0.0.0.0", port=8765):
        super().__init__(app, host, port)
        self._icon: pystray.Icon = None

    def _run_loop(self) -> None:
        """主线程运行 pystray 图标（阻塞）。"""
        menu = pystray.Menu(
            pystray.MenuItem(f"{APP_NAME} - 运行中 (:{self._port})", action=None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("打开管理页面", self._on_open_web),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_exit),
        )

        self._icon = pystray.Icon(
            name="wechat-mcp-server",
            icon=self._icon_image,
            title=APP_NAME,
            menu=menu,
        )
        logger.info(f"系统托盘已启动: http://{self._host}:{self._port}")
        self._icon.run()

    def _exit_platform(self) -> None:
        """停止 pystray 图标并关闭服务器。"""
        self.stop()
        if self._icon is not None:
            self._icon.stop()
