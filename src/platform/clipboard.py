#!/usr/bin/env python3
"""
跨平台剪贴板工具

统一三种平台的剪贴板操作接口：
- Windows: win32clipboard（现有）
- macOS:   NSPasteboard (pyobjc)
- Linux:   xclip 命令行 / pyperclip

自动选择当前平台的最佳实现。
"""

import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class Clipboard:
    """跨平台剪贴板操作工具，备份→设置→恢复。"""

    def __init__(self):
        self._platform = sys.platform
        self._impl = self._detect_impl()

    def _detect_impl(self):
        """检测并选择当前平台的剪贴板实现。"""
        if self._platform == "win32":
            from .win.gui_ops import WinClipboard
            return WinClipboard()
        elif self._platform == "darwin":
            from .mac.gui_ops import MacClipboard
            return MacClipboard()
        elif self._platform.startswith("linux"):
            from .linux.gui_ops import LinuxClipboard
            return LinuxClipboard()
        else:
            raise RuntimeError(f"不支持的平台: {self._platform}")

    def backup(self) -> Optional[str]:
        """备份当前剪贴板内容。

        Returns:
            剪贴板文本内容，空或失败返回 None
        """
        return self._impl.backup()

    def set_and_paste(self, text: str) -> Optional[str]:
        """设置剪贴板内容并粘贴到当前焦点。

        Args:
            text: 要设置的文本

        Returns:
            原剪贴板内容（用于后续恢复），失败返回 None
        """
        return self._impl.set_and_paste(text)

    def restore(self, original_data: Optional[str]) -> None:
        """恢复剪贴板内容。

        Args:
            original_data: 之前备份的剪贴板内容
        """
        if original_data is not None:
            self._impl.restore(original_data)
