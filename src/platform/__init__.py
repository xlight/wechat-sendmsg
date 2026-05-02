#!/usr/bin/env python3
"""
平台抽象层 — 根据运行平台自动选择对应的实现

使用方式：
    from platform import create_platform_impl
    win_finder, gui_ops = create_platform_impl(config)
"""

import logging
import sys
from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseWindowFinder, BaseGUIOperations
    from ..config import Config

logger = logging.getLogger(__name__)


def create_platform_impl(config: Optional[object] = None) -> Tuple[object, object]:
    """根据当前平台创建对应的窗口查找和 GUI 操作实现。

    Returns:
        (window_finder, gui_operations) 元组

    Raises:
        RuntimeError: 不支持的平台
    """
    platform = sys.platform

    if platform == "win32":
        logger.info("检测到 Windows 平台，加载 Windows 实现")
        from .win_finder import WinWindowFinder
        from .win_gui import WinGUIOperations
        return WinWindowFinder(config), WinGUIOperations(config)

    elif platform == "darwin":
        logger.info("检测到 macOS 平台，加载 macOS 实现")
        from .mac_finder import MacWindowFinder
        from .mac_gui import MacGUIOperations
        return MacWindowFinder(config), MacGUIOperations(config)

    else:
        raise RuntimeError(f"不支持的平台: {platform}（仅支持 Windows 和 macOS）")


__all__ = ["create_platform_impl"]
