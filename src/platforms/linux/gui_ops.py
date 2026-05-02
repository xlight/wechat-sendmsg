#!/usr/bin/env python3
"""
Linux GUI 操作与剪贴板实现

包含：
- LinuxGUIOperations: pyautogui + xclip 的 GUI 操作
- LinuxClipboard:     xclip 命令行的剪贴板实现

依赖外部工具：
- xclip: 命令行剪贴板工具
- xdotool: GUI 操作（键盘/鼠标）

快捷键与 Windows 一致：
- 搜索: Ctrl+F
- 发送: Alt+S → Enter（回退）
"""

import logging
import time
import random
import subprocess
import shutil
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


class LinuxGUIOperations(GUIOperations):
    """Linux 平台的 GUI 操作实现。"""

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._has_xclip = shutil.which('xclip') is not None

    def search_contact(self, contact_name: str) -> bool:
        """搜索联系人：Ctrl+F → 粘贴名称 → Enter。"""
        try:
            self._logger.debug(f"搜索联系人: {contact_name}")
            pg = _get_pg()
            pg.hotkey('ctrl', 'f')
            self._pause(0.4, 0.8)
            pg.hotkey('ctrl', 'a')
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
        """发送消息：点击输入框 → 粘贴 → Alt+S 发送。"""
        try:
            if not self.click_input_box():
                self._pause(0.8, 1.5)
                if not self.click_input_box():
                    return False
            self._pause(0.3, 0.6)

            pg = _get_pg()
            pg.hotkey('ctrl', 'a')
            self._pause(0.1, 0.2)
            pg.press('delete')
            self._pause(0.15, 0.3)

            from ..clipboard import Clipboard
            cb = Clipboard()
            original = cb.set_and_paste(message)
            self._pause(0.4, 0.8)

            # 发送：优先 Alt+S，回退 Enter
            try:
                pg.hotkey('alt', 's')
            except Exception:
                pg.press('enter')

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


class LinuxClipboard:
    """Linux xclip 剪贴板实现（供 platform.clipboard.Clipboard 调用）。"""

    def __init__(self):
        self._has_xclip = shutil.which('xclip') is not None
        if not self._has_xclip:
            logger.warning("未找到 xclip，剪贴板操作将受限。请安装：sudo apt install xclip")

    @staticmethod
    def _xclip_read() -> Optional[str]:
        """读取当前剪贴板内容。"""
        try:
            r = subprocess.run(
                ['xclip', '-selection', 'c', '-o'],
                capture_output=True, text=True, timeout=3,
            )
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None

    @staticmethod
    def _xclip_write(text: str) -> bool:
        """写入剪贴板内容。"""
        try:
            subprocess.run(
                ['xclip', '-selection', 'c'],
                input=text, text=True, timeout=3,
            )
            return True
        except Exception:
            return False

    def backup(self) -> Optional[str]:
        if not self._has_xclip:
            return None
        return self._xclip_read()

    def set_and_paste(self, text: str) -> Optional[str]:
        original = self.backup()
        if not self._has_xclip:
            return None
        if not self._xclip_write(text):
            return None
        time.sleep(0.1)
        pg = _get_pg()
        pg.hotkey('ctrl', 'v')
        return original

    def restore(self, original_data: Optional[str]) -> None:
        if original_data is None or not self._has_xclip:
            return
        self._xclip_write(original_data)
