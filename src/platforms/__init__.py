#!/usr/bin/env python3
"""
平台抽象层入口 — 平台检测与工厂函数

根据 sys.platform 返回当前平台的实现实例。
支持：Windows (win32) / macOS (darwin) / Linux (linux)
"""

import logging
import sys
from typing import Tuple

logger = logging.getLogger(__name__)


def create_platform_impl(config: object = None) -> Tuple[object, object, object]:
    """创建当前平台的三件套实现。

    Returns:
        (window_finder, gui_operations, clipboard) 元组

    Raises:
        RuntimeError: 不支持的平台
    """
    platform = sys.platform

    if platform == "win32":
        logger.info("检测到 Windows 平台")
        from .win import create_impl as create
        return create(config)

    elif platform == "darwin":
        logger.info("检测到 macOS 平台")
        from .mac import create_impl as create
        return create(config)

    elif platform.startswith("linux"):
        logger.info("检测到 Linux 平台")
        from .linux import create_impl as create
        return create(config)

    else:
        raise RuntimeError(f"不支持的操作系统平台: {platform}")


def create_tray_manager(app, host: str = "0.0.0.0", port: int = 8765):
    """创建当前平台的系统托盘/菜单栏管理器。

    Args:
        app: Starlette ASGI 应用实例
        host: 服务器监听地址
        port: 服务器端口

    Returns:
        TrayManager 实例
    """
    platform = sys.platform

    if platform == "win32":
        logger.info("创建 Windows 系统托盘")
        from .win.tray import WinTrayManager
        return WinTrayManager(app, host, port)

    elif platform == "darwin":
        logger.info("创建 macOS 菜单栏图标")
        from .mac.tray import MacTrayManager
        return MacTrayManager(app, host, port)

    elif platform.startswith("linux"):
        logger.info("创建 Linux 系统指示器")
        from .linux.tray import LinuxTrayManager
        return LinuxTrayManager(app, host, port)

    else:
        raise RuntimeError(f"不支持的操作系统平台: {platform}")
