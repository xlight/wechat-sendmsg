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
