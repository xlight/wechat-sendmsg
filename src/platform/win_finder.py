#!/usr/bin/env python3
"""
Windows 窗口查找实现 — 适配 BaseWindowFinder 接口

封装现有的 window_finder.py 和 tray_manager.py 中的功能，
保持与原始代码兼容，不修改现有实现。
"""

import logging
from typing import Optional, Dict, Any

try:
    from ..window_finder import WindowFinderMixin
    from ..tray_manager import TrayManagerMixin
except ImportError:
    from window_finder import WindowFinderMixin
    from tray_manager import TrayManagerMixin

from .base import BaseWindowFinder

logger = logging.getLogger(__name__)


class WinWindowFinder(BaseWindowFinder, TrayManagerMixin, WindowFinderMixin):
    """Windows 平台的微信窗口查找与激活。

    通过 Mixin 继承复用现有的 WindowFinderMixin 和 TrayManagerMixin。
    作为适配器，将现有接口映射到 BaseWindowFinder 的抽象接口。
    """

    def __init__(self, config: object = None):
        # TrayManagerMixin 和 WindowFinderMixin 不需要 __init__
        # 它们的 __init__ 由 WeChatController 完成
        self._config = config
        self._logger = logging.getLogger(__name__)

    def detect_wechat_version(self) -> Optional[str]:
        return self._detect_wechat_version()

    def find_wechat_window(self) -> Optional[int]:
        return self._find_wechat_window()

    def activate_window(self, window_id: int) -> bool:
        return self._activate_window(window_id)

    def restore_window(self) -> Optional[int]:
        return self._restore_from_systray()

    def is_wechat_available(self) -> bool:
        pid = self.find_wechat_window()
        return pid is not None

    def get_status(self) -> Dict[str, Any]:
        hwnd = self.find_wechat_window()
        version = self.detect_wechat_version()
        return {
            "wechat_available": hwnd is not None,
            "window_handle": hwnd,
            "wechat_version": version,
            "is_nt_framework": self.is_nt_version,
            "supported": self.is_nt_version,
            "platform": "windows",
            "framework_type": "NT framework (4.0+)" if self.is_nt_version else "Legacy (<4.0)",
        }
