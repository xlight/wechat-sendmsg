#!/usr/bin/env python3
"""
Linux 系统托盘实现 — pystray (AppIndicator / StatusNotifierItem)

使用 pystray 自动适配 GTK AppIndicator (X11) 或 StatusNotifierItem (Wayland)。
需要系统安装：
  # Ubuntu/Debian (X11)
  sudo apt install gir1.2-appindicator3-0.1
  
  # Ubuntu/Debian (Wayland)
  sudo apt install gir1.2-ayatanaappindicator3-0.1

如果 pystray 无法创建托盘图标，回退到静默后台模式（仅终端运行）。
"""

import logging
from typing import Any

from ..tray import TrayManager, APP_NAME

logger = logging.getLogger(__name__)


class LinuxTrayManager(TrayManager):
    """Linux 系统托盘/指示器实现。"""

    def __init__(self, app, host="0.0.0.0", port=8765):
        super().__init__(app, host, port)
        self._icon: Any = None

    def _run_loop(self) -> None:
        """主线程运行 pystray 图标（阻塞）。"""
        import pystray

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
        logger.info(f"系统指示器已启动: http://{self._host}:{self._port}")
        self._icon.run()

    def _exit_platform(self) -> None:
        """停止 pystray 图标。"""
        logger.info("用户请求退出...")
        self.stop()
        if self._icon is not None:
            self._icon.stop()
