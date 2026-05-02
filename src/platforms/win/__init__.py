#!/usr/bin/env python3
"""
Windows 平台实现入口
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def create_impl(config: object = None) -> Tuple[object, object, object]:
    """创建 Windows 平台的实现。

    Returns:
        (window_finder, gui_operations, clipboard) 元组
    """
    from .window_finder import WinWindowFinder
    from .gui_ops import WinGUIOperations, WinClipboard

    win_finder = WinWindowFinder(config)
    gui_ops = WinGUIOperations(config)
    clipboard = WinClipboard()

    return win_finder, gui_ops, clipboard
