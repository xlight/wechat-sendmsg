#!/usr/bin/env python3
"""
GUI 操作模块
处理剪贴板操作、输入框交互、联系人搜索和消息发送等 GUI 自动化功能。
"""

import logging
from typing import Any, Dict, Optional

import pyautogui
import win32clipboard
import win32gui

logger = logging.getLogger(__name__)


class GUIOperationsMixin:
    """GUI 操作 Mixin，提供剪贴板、输入框、搜索和发送功能。

    依赖 WindowFinderMixin 的 _find_wechat_window() 方法。
    依赖 self._natural_gui (NaturalGUIOperations) 实例。
    """

    def _find_and_click_input_box(self) -> bool:
        """查找并点击微信聊天输入框。"""
        try:
            hwnd = self._find_wechat_window()
            self.logger.error(f"寻找输入框，当前微信窗口句柄: {hwnd}")
            if not hwnd:
                self.logger.error("WeChat window not found")
                return False

            rect = win32gui.GetWindowRect(hwnd)
            window_left, window_top, window_right, window_bottom = rect
            window_width = window_right - window_left

            input_positions = [
                (window_left + window_width // 2, window_bottom - 80),
                (window_left + window_width // 2, window_bottom - 120),
                (window_left + window_width // 3, window_bottom - 100),
                (window_left + window_width * 2 // 3, window_bottom - 100),
                (pyautogui.size()[0] // 2, int(pyautogui.size()[1] * 0.85)),
            ]

            for click_x, click_y in input_positions:
                try:
                    # 使用自然点击代替直接点击
                    self._natural_gui.natural_click(int(click_x), int(click_y))
                    self.logger.error(f"尝试点击输入框位置: ({click_x}, {click_y})")
                    return True
                except Exception:
                    continue

            self.logger.error("All input box positions failed")
            return False
        except Exception as e:
            self.logger.error(f"Failed to locate input box: {e}")
            return False

    def _set_clipboard_and_paste(self, text: str) -> Optional[str]:
        """备份剪贴板，设置新内容并粘贴到当前焦点位置。

        注意：此方法不会清空输入框，调用方需要在调用前自行清空。

        Args:
            text: 要粘贴的文本内容

        Returns:
            原剪贴板内容（用于后续恢复），失败返回 None
        """
        # 备份原剪贴板内容
        original_data: Optional[str] = None
        win32clipboard.OpenClipboard()
        try:
            try:
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                if isinstance(data, str):
                    original_data = data
            except Exception:
                original_data = None
        finally:
            win32clipboard.CloseClipboard()

        # 设置新的剪贴板内容
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

        # 验证剪贴板内容是否设置成功
        self._natural_gui._random_pause(0.08, 0.15)
        win32clipboard.OpenClipboard()
        try:
            verify = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            if verify != text:
                self.logger.error(f"剪贴板验证失败！期望: {text[:20]}, 实际: {verify[:20] if verify else 'None'}")
            else:
                self.logger.debug(f"剪贴板设置成功: {text[:20]}...")
        finally:
            win32clipboard.CloseClipboard()

        # 等待剪贴板稳定
        self._natural_gui._random_pause(0.15, 0.25)

        # 执行粘贴操作 - 使用更可靠的方式
        self.logger.debug("执行粘贴操作 (Ctrl+V)...")
        pyautogui.keyDown('ctrl')
        self._natural_gui._random_pause(0.03, 0.08)
        pyautogui.press('v')
        self._natural_gui._random_pause(0.03, 0.08)
        pyautogui.keyUp('ctrl')

        # 等待粘贴完成
        self._natural_gui._random_pause(0.4, 0.7)
        self.logger.debug("粘贴操作完成")
        return original_data

    def _restore_clipboard(self, original_data: Optional[str]) -> None:
        """恢复剪贴板内容。"""
        if not original_data:
            return
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_data, win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return

    def _input_text_via_clipboard(self, text: str) -> bool:
        """清空当前输入框并通过剪贴板输入文本。

        此方法会：
        1. 全选并删除当前内容
        2. 通过剪贴板粘贴新文本
        3. 恢复原剪贴板内容

        Args:
            text: 要输入的文本

        Returns:
            成功返回 True，失败返回 False
        """
        try:
            # 清空当前输入框
            pyautogui.hotkey('ctrl', 'a')
            self._natural_gui._random_pause()
            pyautogui.press('delete')
            self._natural_gui._random_pause(0.15, 0.35)

            # 粘贴文本
            original_data = self._set_clipboard_and_paste(text)
            self._restore_clipboard(original_data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to input text via clipboard: {e}")
            return False

    def _search_contact_nt(self, contact_name: str) -> bool:
        """搜索联系人/群聊并打开聊天窗口（NT 框架）。"""
        # 验证微信窗口焦点
        hwnd = self._find_wechat_window()
        if not hwnd or win32gui.GetForegroundWindow() != hwnd:
             self.logger.error("WeChat not focused, aborting search")
             return False

        original_data: Optional[str] = None
        try:
            # 打开搜索框
            pyautogui.hotkey('ctrl', 'f')
            self.logger.debug("打开搜索框 (Ctrl+F)")
            self._natural_gui._random_pause(0.5, 1.0)

            # 清空搜索框
            pyautogui.hotkey('ctrl', 'a')
            self.logger.debug("全选搜索框内容 (Ctrl+A)")
            self._natural_gui._random_pause(0.1, 0.3)
            pyautogui.press('delete')
            self.logger.debug("清空搜索框内容 (Delete)")
            self._natural_gui._random_pause(0.15, 0.35)

            # 输入联系人名称（粘贴）
            original_data = self._set_clipboard_and_paste(contact_name)
            self.logger.debug(f"输入联系人名称: {contact_name}")
            self._natural_gui._random_pause(0.3, 0.6)

            # 回车打开聊天
            pyautogui.press('enter')
            self._natural_gui._random_pause(0.5, 1.0)

            self.logger.debug(f"成功搜索并打开: {contact_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to search contact in NT: {e}")
            return False
        finally:
            self._restore_clipboard(original_data)

    def _send_text_nt(self, message: str) -> bool:
        """发送文本消息（NT 框架）。

        按键优先级：Alt+S（主要） > Enter（备用） > Ctrl+Enter（备用）
        """
        self.logger.debug(f"准备发送消息: {message[:20]}...")
        try:
            # 查找并点击输入框
            if not self._find_and_click_input_box():
                self.logger.error("输入框未找到，无法发送消息")
                # 等待后重试
                self._natural_gui._random_pause(0.8, 1.5)
                if not self._find_and_click_input_box():
                    self.logger.error("再次尝试寻找输入框失败，发送消息中止")
                    return False

            self.logger.debug("输入框已点击，准备输入消息...")
            self._natural_gui._random_pause(0.3, 0.6)  # 等待输入框稳定

            # 清空输入框（以防有残留内容）
            pyautogui.hotkey('ctrl', 'a')
            self._natural_gui._random_pause(0.1, 0.2)
            pyautogui.press('delete')
            self._natural_gui._random_pause(0.15, 0.3)

            # 粘贴消息内容
            original_data = self._set_clipboard_and_paste(message)
            self.logger.debug("文本输入完成，准备发送...")
            self._natural_gui._random_pause(0.4, 0.8)  # 等待输入稳定

            # 发送消息 - 优先使用 Alt+S
            try:
                pyautogui.hotkey('alt', 's')
                self.logger.debug("按下 Alt+S 键发送消息")
                self._natural_gui._random_pause(0.5, 1.0)
                self._restore_clipboard(original_data)
                self.logger.debug("剪贴板已恢复")
                return True
            except Exception as e1:
                self.logger.warning(f"Alt+S 发送失败，尝试 Enter: {e1}")
                try:
                    pyautogui.press('enter')
                    self.logger.debug("按下 Enter 键发送消息")
                    self._natural_gui._random_pause(0.5, 1.0)
                    self._restore_clipboard(original_data)
                    return True
                except Exception as e2:
                    self.logger.warning(f"Enter 发送失败，尝试 Ctrl+Enter: {e2}")
                    try:
                        pyautogui.hotkey('ctrl', 'enter')
                        self.logger.debug("按下 Ctrl+Enter 键发送消息")
                        self._natural_gui._random_pause(0.5, 1.0)
                        self._restore_clipboard(original_data)
                        return True
                    except Exception as e3:
                        self.logger.error(f"所有发送方式均失败: {e3}")
                        return False
        except Exception as e:
            self.logger.error(f"Failed to send text in NT: {e}")
            return False
