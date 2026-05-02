#!/usr/bin/env python3
"""
Windows GUI 操作与剪贴板实现

包含：
- WinGUIOperations:  封装现有 GUIOperationsMixin
- WinClipboard:      win32clipboard 剪贴板实现
"""

import logging
from typing import Optional

import pyautogui
import win32clipboard as w32cb

from ...gui_operations import GUIOperationsMixin
from ..base import GUIOperations

logger = logging.getLogger(__name__)


class WinGUIOperations(GUIOperations, GUIOperationsMixin):
    """Windows 平台的 GUI 操作实现。"""

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)

        # 初始化自然 GUI 操作（GUIOperationsMixin 依赖）
        from ...anti_ban.natural_gui import NaturalGUIOperations
        self._natural_gui = NaturalGUIOperations()

    def search_contact(self, contact_name: str) -> bool:
        return self._search_contact_nt(contact_name)

    def send_text(self, message: str) -> bool:
        return self._send_text_nt(message)

    def click_input_box(self) -> bool:
        return self._find_and_click_input_box()

    def set_clipboard(self, text: str) -> Optional[str]:
        return self._set_clipboard_and_paste(text)

    def restore_clipboard(self, original_data: Optional[str]) -> None:
        self._restore_clipboard(original_data)


class WinClipboard:
    """Windows 剪贴板实现（供 platform.clipboard.Clipboard 调用）。"""

    def backup(self) -> Optional[str]:
        """备份当前剪贴板内容。"""
        try:
            w32cb.OpenClipboard()
            try:
                data = w32cb.GetClipboardData(w32cb.CF_UNICODETEXT)
                return str(data) if data else None
            except Exception:
                return None
            finally:
                w32cb.CloseClipboard()
        except Exception:
            return None

    def set_and_paste(self, text: str) -> Optional[str]:
        """设置剪贴板 → Cmd+V 粘贴 → 返回原内容。"""
        original = self.backup()

        try:
            w32cb.OpenClipboard()
            try:
                w32cb.EmptyClipboard()
                w32cb.SetClipboardText(text, w32cb.CF_UNICODETEXT)
            finally:
                w32cb.CloseClipboard()
        except Exception as e:
            logger.error(f"设置剪贴板失败: {e}")
            return None

        pyautogui.hotkey('ctrl', 'v')
        return original

    def restore(self, original_data: Optional[str]) -> None:
        """恢复剪贴板内容。"""
        if original_data is None:
            return
        try:
            w32cb.OpenClipboard()
            try:
                w32cb.EmptyClipboard()
                w32cb.SetClipboardText(original_data, w32cb.CF_UNICODETEXT)
            finally:
                w32cb.CloseClipboard()
        except Exception:
            pass
