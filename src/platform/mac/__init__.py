#!/usr/bin/env python3
"""
macOS 平台实现入口
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def create_impl(config: object = None) -> Tuple[object, object, object]:
    """创建 macOS 平台的实现。

    Returns:
        (window_finder, gui_operations, clipboard) 元组
    """
    from .window_finder import MacWindowFinder
    from .gui_ops import MacGUIOperations, MacClipboard

    win_finder = MacWindowFinder(config)
    gui_ops = MacGUIOperations(config)
    clipboard = MacClipboard()

    return win_finder, gui_ops, clipboard
