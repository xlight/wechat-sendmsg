#!/usr/bin/env python3
"""
跨平台剪贴板工具

统一三种平台的剪贴板操作接口。
自动选择当前平台的最佳实现，所有平台特有导入使用懒加载。
"""

import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class Clipboard:
    """跨平台剪贴板操作工具，备份→设置→恢复。

    重要：不导入任何平台特有模块，全部使用懒加载。
    """

    def __init__(self):
        self._platform = sys.platform
        self._impl = None

    def _get_impl(self):
        """获取平台对应的剪贴板实现（懒加载）。"""
        if self._impl is not None:
            return self._impl

        if self._platform == "win32":
            from .win.gui_ops import WinClipboard
            self._impl = WinClipboard()
        elif self._platform == "darwin":
            from .mac.gui_ops import MacClipboard
            self._impl = MacClipboard()
        elif self._platform.startswith("linux"):
            from .linux.gui_ops import LinuxClipboard
            self._impl = LinuxClipboard()
        else:
            raise RuntimeError(f"不支持的平台: {self._platform}")

        return self._impl

    def backup(self) -> Optional[str]:
        """备份当前剪贴板内容。"""
        return self._get_impl().backup()

    def set_and_paste(self, text: str) -> Optional[str]:
        """设置剪贴板内容并粘贴到当前焦点。"""
        return self._get_impl().set_and_paste(text)

    def restore(self, original_data: Optional[str]) -> None:
        """恢复剪贴板内容。"""
        if original_data is not None:
            self._get_impl().restore(original_data)
