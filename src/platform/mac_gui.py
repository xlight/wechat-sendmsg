#!/usr/bin/env python3
"""
macOS GUI 操作实现

使用 pyautogui（跨平台）+ NSPasteboard（macOS 剪贴板）实现：
- 搜索联系人: Cmd+F 打开搜索 → 粘贴联系人名 → Enter
- 发送消息: 粘贴内容 → Cmd+Enter 发送
- 剪贴板操作: NSPasteboard 原生 API

与 Windows 的关键差异：
- 搜索快捷键: Cmd+F（非 Ctrl+F）
- 发送快捷键: Cmd+Enter（非 Alt+S）
- 剪贴板: NSPasteboard（非 win32clipboard）
- 输入框点击: 微信底部区域（坐标偏移不同）
"""

import logging
import time
import random
from typing import Optional

import pyautogui

from .base import BaseGUIOperations

logger = logging.getLogger(__name__)


class MacGUIOperations(BaseGUIOperations):
    """macOS 平台的 GUI 操作实现。"""

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)

    # ── NSPasteboard 懒加载 ─────────────────────────────────────────

    @staticmethod
    def _get_pasteboard():
        """懒加载 NSPasteboard。"""
        from AppKit import NSPasteboard, NSPasteboardTypeString
        return NSPasteboard, NSPasteboardTypeString

    # ── 公共接口 ──────────────────────────────────────────────────────

    def search_contact(self, contact_name: str) -> bool:
        """搜索联系人/群聊并打开聊天窗口（macOS 微信）。

        流程：
        1. Cmd+F 打开搜索框
        2. 全选后删除旧内容
        3. 通过剪贴板粘贴联系人名
        4. Enter 进入聊天

        Args:
            contact_name: 联系人名称

        Returns:
            成功进入聊天窗口返回 True
        """
        try:
            self._logger.debug(f"开始搜索联系人: {contact_name}")

            # 1. 打开搜索框 (Cmd+F)
            pyautogui.hotkey('command', 'f')
            self._random_pause(0.4, 0.8)

            # 2. 清空搜索框
            pyautogui.hotkey('command', 'a')
            self._random_pause(0.1, 0.2)
            pyautogui.press('delete')
            self._random_pause(0.15, 0.3)

            # 3. 粘贴联系人名
            original_data = self.set_clipboard(contact_name)
            self._logger.debug(f"已输入联系人名称: {contact_name}")
            self._random_pause(0.3, 0.6)

            # 4. 回车进入聊天
            pyautogui.press('enter')
            self._random_pause(0.5, 1.0)

            self._logger.debug(f"成功搜索并打开联系人: {contact_name}")
            return True

        except Exception as e:
            self._logger.error(f"搜索联系人失败: {e}")
            return False

    def send_text(self, message: str) -> bool:
        """发送文本消息（macOS 微信）。

        流程：
        1. 点击输入框确保焦点
        2. 全选后删除旧内容
        3. 粘贴消息内容
        4. Cmd+Enter 发送
        5. 恢复剪贴板

        Args:
            message: 消息内容

        Returns:
            发送成功返回 True
        """
        try:
            self._logger.debug(f"准备发送消息: {message[:20]}...")

            # 1. 点击输入框
            if not self.click_input_box():
                self._logger.error("输入框未找到，无法发送消息")
                self._random_pause(0.8, 1.5)
                if not self.click_input_box():
                    self._logger.error("再次尝试点击输入框失败")
                    return False

            self._random_pause(0.3, 0.6)

            # 2. 清空输入框
            pyautogui.hotkey('command', 'a')
            self._random_pause(0.1, 0.2)
            pyautogui.press('delete')
            self._random_pause(0.15, 0.3)

            # 3. 粘贴消息
            original_data = self.set_clipboard(message)

            # 4. Cmd+Enter 发送（macOS 微信默认发送快捷键）
            self._random_pause(0.4, 0.8)
            pyautogui.hotkey('command', 'enter')
            self._random_pause(0.5, 1.0)

            # 5. 恢复剪贴板
            self.restore_clipboard(original_data)
            self._logger.debug("消息发送成功")
            return True

        except Exception as e:
            self._logger.error(f"发送消息失败: {e}")
            return False

    def click_input_box(self) -> bool:
        """点击聊天输入框以获取焦点。

        macOS 微信的输入框在窗口底部，使用窗口中心底部坐标。
        如果 pyautogui 无法定位，尝试通过 Tab 键切换焦点。

        Returns:
            成功返回 True
        """
        try:
            screen_width, screen_height = pyautogui.size()

            # 尝试多个可能的输入框位置（从底部中央到偏左/偏右）
            positions = [
                (screen_width // 2, screen_height - 80),           # 底部中央
                (screen_width // 2, screen_height - 100),          # 稍上方
                (screen_width // 3, screen_height - 100),          # 底部偏左
                (screen_width * 2 // 3, screen_height - 100),      # 底部偏右
                (screen_width // 2, screen_height - 120),          # 更上方
            ]

            for x, y in positions:
                try:
                    pyautogui.click(x, y)
                    self._random_pause(0.2, 0.4)
                    self._logger.debug(f"点击输入框位置: ({x}, {y})")
                    return True
                except Exception:
                    continue

            # 备用方案: 尝试 Tab 切换到输入框
            self._logger.warning("坐标点击失败，尝试 Tab 切换焦点")
            pyautogui.press('tab')
            self._random_pause(0.2, 0.4)
            pyautogui.press('tab')
            self._random_pause(0.2, 0.4)

            self._logger.error("所有输入框定位方式均失败")
            return False

        except Exception as e:
            self._logger.error(f"点击输入框失败: {e}")
            return False

    def set_clipboard(self, text: str) -> Optional[str]:
        """使用 NSPasteboard 设置剪贴板内容并粘贴到当前焦点。

        流程：
        1. 备份当前剪贴板
        2. 设置新内容到 NSPasteboard
        3. Cmd+V 粘贴到当前焦点
        4. 返回原剪贴板内容

        Args:
            text: 要设置并粘贴的文本

        Returns:
            原剪贴板内容（用于恢复），失败返回 None
        """
        original_data: Optional[str] = None

        try:
            NSPasteboard, NSPasteboardTypeString = self._get_pasteboard()

            # 1. 备份原剪贴板
            pb = NSPasteboard.generalPasteboard()
            original_data = pb.stringForType_(NSPasteboardTypeString)
            self._logger.debug(f"已备份剪贴板: {original_data[:20] if original_data else '(空)'}...")

            # 2. 清空并设置新内容
            pb.clearContents()
            pb.setString_forType_(text, NSPasteboardTypeString)
            self._logger.debug(f"剪贴板已设置为: {text[:20]}...")

            # 3. 等待剪贴板稳定
            self._random_pause(0.1, 0.2)

            # 4. Cmd+V 粘贴
            pyautogui.hotkey('command', 'v')
            self._random_pause(0.3, 0.5)

            return original_data

        except Exception as e:
            self._logger.error(f"剪贴板操作失败: {e}")
            # 尝试恢复原始内容
            if original_data is not None:
                try:
                    NSPasteboard, NSPasteboardTypeString = self._get_pasteboard()
                    pb = NSPasteboard.generalPasteboard()
                    pb.clearContents()
                    pb.setString_forType_(original_data, NSPasteboardTypeString)
                except Exception:
                    pass
            return None

    def restore_clipboard(self, original_data: Optional[str]) -> None:
        """恢复剪贴板内容。

        Args:
            original_data: 之前备份的剪贴板内容
        """
        if original_data is None:
            return

        try:
            NSPasteboard, NSPasteboardTypeString = self._get_pasteboard()
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(original_data, NSPasteboardTypeString)
            self._logger.debug("剪贴板已恢复")
        except Exception as e:
            self._logger.warning(f"恢复剪贴板失败: {e}")

    # ── 辅助方法 ──────────────────────────────────────────────────────

    def _random_pause(self, min_sec: float = 0.05, max_sec: float = 0.15) -> None:
        """随机停顿，模拟人类操作节奏。"""
        time.sleep(random.uniform(min_sec, max_sec))
