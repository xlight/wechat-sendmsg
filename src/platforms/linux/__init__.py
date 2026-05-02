#!/usr/bin/env python3
"""
Linux 平台实现入口
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def create_impl(config: object = None) -> Tuple[object, object, object]:
    """创建 Linux 平台的实现。

    Returns:
        (window_finder, gui_operations, clipboard) 元组
    """
    from .window_finder import LinuxWindowFinder
    from .gui_ops import LinuxGUIOperations, LinuxClipboard

    win_finder = LinuxWindowFinder(config)
    gui_ops = LinuxGUIOperations(config)
    clipboard = LinuxClipboard()

    return win_finder, gui_ops, clipboard
