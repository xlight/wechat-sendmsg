#!/usr/bin/env python3
"""
Windows 窗口查找实现 — 封装现有 WindowFinderMixin + TrayManagerMixin

作为适配器，将现有的 Mixin 类映射到 platform.base.WindowFinder 抽象接口。
不修改现有 Mixin 代码。
"""

import logging
from typing import Optional, Dict, Any

# 使用 sys.path 导入或绝对导入，避免相对导入在测试环境中出错
try:
    from window_finder import WindowFinderMixin
    from tray_manager import TrayManagerMixin
except ImportError:
    # 当从 tests/ 运行时，window_finder 已经在 sys.path（src/）
    import importlib
    WindowFinderMixin = importlib.import_module('window_finder').WindowFinderMixin
    TrayManagerMixin = importlib.import_module('tray_manager').TrayManagerMixin

from ..base import WindowFinder

logger = logging.getLogger(__name__)


class WinWindowFinder(WindowFinder, TrayManagerMixin, WindowFinderMixin):
    """Windows 平台的窗口查找实现。

    多继承复用现有 Mixin，对外暴露统一的 WindowFinder 接口。
    """

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)
        self.logger = self._logger  # 兼容 WindowFinderMixin 使用的 self.logger

        # 初始化自然 GUI 操作（WindowFinderMixin 和 GUIOperationsMixin 依赖）
        try:
            from anti_ban.natural_gui import NaturalGUIOperations
            self._natural_gui = NaturalGUIOperations()
        except ImportError:
            self._natural_gui = None

    # ── WindowFinder 接口实现 ──

    def detect_wechat_version(self) -> Optional[str]:
        return self._detect_wechat_version()

    def find_wechat_window(self) -> Optional[int]:
        return self._find_wechat_window()

    def activate_window(self, window_id: int) -> bool:
        return self._activate_window(window_id)

    def restore_window(self) -> Optional[int]:
        return self._restore_from_systray()

    def is_wechat_available(self) -> bool:
        return self.find_wechat_window() is not None

    def get_status(self) -> Dict[str, Any]:
        hwnd = self.find_wechat_window()
        version = self.detect_wechat_version()
        return {
            "wechat_available": hwnd is not None,
            "window_handle": hwnd,
            "wechat_version": version,
            "is_nt_framework": getattr(self, 'is_nt_version', False),
            "supported": getattr(self, 'is_nt_version', False),
            "platform": "windows",
            "framework_type": "NT (4.0+)" if getattr(self, 'is_nt_version', False) else "Legacy (<4.0)",
        }
