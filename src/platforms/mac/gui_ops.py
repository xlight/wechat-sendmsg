#!/usr/bin/env python3
"""
macOS GUI 操作与剪贴板实现

包含：
- MacGUIOperations: pyautogui + NSPasteboard 的 GUI 操作
- MacClipboard:     NSPasteboard 剪贴板实现

关键差异：
- 搜索: Cmd+F（Windows 为 Ctrl+F）
- 发送: Cmd+Enter（Windows 为 Alt+S）
- 剪贴板: NSPasteboard（Windows 为 win32clipboard）
"""

import logging
import time
import random
from typing import Optional

# ⚠️ pyautogui 使用懒加载
_pyautogui = None

from ..base import GUIOperations

logger = logging.getLogger(__name__)


def _get_pg():
    global _pyautogui
    if _pyautogui is None:
        import pyautogui as _pyautogui
    return _pyautogui


class MacGUIOperations(GUIOperations):
    """macOS 平台的 GUI 操作实现。"""

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)

    def search_contact(self, contact_name: str) -> bool:
        """搜索联系人：Cmd+F → 粘贴名称 → Enter。"""
        try:
            self._logger.debug(f"搜索联系人: {contact_name}")
            pg = _get_pg()
            pg.hotkey('command', 'f')
            self._pause(0.4, 0.8)
            pg.hotkey('command', 'a')
            self._pause(0.1, 0.2)
            pg.press('delete')
            self._pause(0.15, 0.3)

            from ..clipboard import Clipboard
            cb = Clipboard()
            original = cb.set_and_paste(contact_name)
            self._pause(0.3, 0.6)
            pg.press('enter')
            self._pause(0.5, 1.0)
            cb.restore(original)

            self._logger.debug(f"搜索成功: {contact_name}")
            return True
        except Exception as e:
            self._logger.error(f"搜索联系人失败: {e}")
            return False

    def send_text(self, message: str) -> bool:
        """发送消息：点击输入框 → 粘贴 → Cmd+Enter。"""
        try:
            if not self.click_input_box():
                self._pause(0.8, 1.5)
                if not self.click_input_box():
                    return False
            self._pause(0.3, 0.6)

            pg = _get_pg()
            pg.hotkey('command', 'a')
            self._pause(0.1, 0.2)
            pg.press('delete')
            self._pause(0.15, 0.3)

            from ..clipboard import Clipboard
            cb = Clipboard()
            original = cb.set_and_paste(message)
            self._pause(0.4, 0.8)
            pg.hotkey('command', 'enter')
            self._pause(0.5, 1.0)
            cb.restore(original)

            self._logger.debug("消息发送成功")
            return True
        except Exception as e:
            self._logger.error(f"发送消息失败: {e}")
            return False

    def click_input_box(self) -> bool:
        """点击聊天输入框（屏幕坐标）。"""
        try:
            pg = _get_pg()
            sw, sh = pg.size()
            positions = [
                (sw // 2, sh - 80),
                (sw // 2, sh - 100),
                (sw // 3, sh - 100),
                (sw * 2 // 3, sh - 100),
                (sw // 2, sh - 120),
            ]
            for x, y in positions:
                try:
                    pg.click(x, y)
                    self._pause(0.2, 0.4)
                    return True
                except Exception:
                    continue

            self._logger.warning("尝试 Tab 切换焦点")
            pg.press('tab')
            self._pause(0.2, 0.4)
            pg.press('tab')
            self._pause(0.2, 0.4)
            return False
        except Exception as e:
            self._logger.error(f"点击输入框失败: {e}")
            return False

    def set_clipboard(self, text: str) -> Optional[str]:
        from ..clipboard import Clipboard
        return Clipboard().set_and_paste(text)

    def restore_clipboard(self, original_data: Optional[str]) -> None:
        from ..clipboard import Clipboard
        Clipboard().restore(original_data)

    def _pause(self, min_s: float = 0.05, max_s: float = 0.15) -> None:
        time.sleep(random.uniform(min_s, max_s))


class MacClipboard:
    """macOS NSPasteboard 剪贴板实现（供 platform.clipboard.Clipboard 调用）。"""

    @staticmethod
    def _pb():
        from AppKit import NSPasteboard, NSPasteboardTypeString
        return NSPasteboard, NSPasteboardTypeString

    def backup(self) -> Optional[str]:
        try:
            NSPb, NSType = self._pb()
            pb = NSPb.generalPasteboard()
            return pb.stringForType_(NSType)
        except Exception:
            return None

    def set_and_paste(self, text: str) -> Optional[str]:
        original = self.backup()
        try:
            NSPb, NSType = self._pb()
            pb = NSPb.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(text, NSType)
            time.sleep(0.1)
            pg = _get_pg()
            pg.hotkey('command', 'v')
            return original
        except Exception as e:
            logger.error(f"剪贴板设置失败: {e}")
            return None

    def restore(self, original_data: Optional[str]) -> None:
        if original_data is None:
            return
        try:
            NSPb, NSType = self._pb()
            pb = NSPb.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(original_data, NSType)
        except Exception:
            pass
