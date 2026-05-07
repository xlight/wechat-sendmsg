#!/usr/bin/env python3
"""
GUI 操作模块
处理剪贴板操作、输入框交互、联系人搜索和消息发送等 GUI 自动化功能。
"""

import logging
import time
from contextlib import contextmanager
from typing import Iterator, Optional, Protocol


class _NaturalGUIProtocol(Protocol):
    """自然 GUI 操作协议，声明 Mixin 依赖的方法。"""

    def natural_click(self, x: int, y: int) -> None:
        """自然点击指定位置。"""
        ...

    def _random_pause(self, min_sec: float = 0.1, max_sec: float = 0.3) -> None:
        """随机暂停。"""
        ...


class _WindowFinderProtocol(Protocol):
    """窗口查找协议，声明 Mixin 依赖的方法。"""

    def _find_wechat_window(self) -> Optional[int]:
        """查找微信窗口。"""
        ...


class _ClipboardManager:
    """Windows 剪贴板操作管理器。

    封装剪贴板的打开、读取、写入操作，提供重试机制和上下文管理器。
    Windows 剪贴板是全局资源，可能被其他进程锁定，因此需要重试机制。
    """

    MAX_RETRIES = 8
    RETRY_DELAY = 0.15  # 秒

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @contextmanager
    def _open(self) -> Iterator[None]:
        """上下文管理器：安全打开和关闭剪贴板。"""
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            yield
        finally:
            win32clipboard.CloseClipboard()

    def _retry(self, func, *args, **kwargs):
        """执行剪贴板操作，带重试机制。

        处理 ERROR_ACCESS_DENIED (5) 错误，该错误表示剪贴板被其他进程锁定。
        """
        ERROR_ACCESS_DENIED = 5
        last_err = None

        for attempt in range(self.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_err = e
                if getattr(e, 'winerror', None) == ERROR_ACCESS_DENIED:
                    delay = self.RETRY_DELAY * (attempt + 1)
                    self._logger.debug(f"剪贴板被锁定，重试 {attempt + 1}/{self.MAX_RETRIES}...")
                    time.sleep(delay)
                    continue
                raise

        if last_err is not None:
            raise last_err
        raise RuntimeError("剪贴板操作失败：未知错误")

    def backup(self) -> Optional[str]:
        """备份当前剪贴板内容。

        Returns:
            原剪贴板文本内容，失败返回 None
        """
        import win32clipboard

        def _do_backup() -> Optional[str]:
            with self._open():
                try:
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return data if isinstance(data, str) else None
                except Exception:
                    return None

        try:
            return self._retry(_do_backup)
        except Exception as e:
            self._logger.warning(f"备份剪贴板失败: {e}")
            return None

    def restore(self, content: Optional[str]) -> bool:
        """恢复剪贴板内容。

        Args:
            content: 要恢复的文本内容

        Returns:
            成功返回 True
        """
        import win32clipboard

        if not content:
            return True

        def _do_restore() -> None:
            with self._open():
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(content, win32clipboard.CF_UNICODETEXT)

        try:
            self._retry(_do_restore)
            return True
        except Exception as e:
            self._logger.warning(f"恢复剪贴板失败: {e}")
            return False

    def set_text(self, text: str) -> bool:
        """设置剪贴板文本内容。

        Args:
            text: 要设置的文本

        Returns:
            成功返回 True
        """
        import win32clipboard

        def _do_set() -> None:
            with self._open():
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)

        try:
            self._retry(_do_set)
            return True
        except Exception as e:
            self._logger.error(f"设置剪贴板失败: {e}")
            return False

    def get_text(self) -> Optional[str]:
        """获取剪贴板文本内容。

        Returns:
            剪贴板文本，失败返回 None
        """
        import win32clipboard

        def _do_get() -> Optional[str]:
            with self._open():
                try:
                    return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                except Exception:
                    return None

        try:
            return self._retry(_do_get)
        except Exception as e:
            self._logger.warning(f"获取剪贴板失败: {e}")
            return None


class GUIOperationsMixin:
    """GUI 操作 Mixin，提供剪贴板、输入框、搜索和发送功能。

    依赖 WindowFinderMixin 的 _find_wechat_window() 方法。
    依赖 self._natural_gui (NaturalGUIOperations) 实例。
    """

    # 类型声明（由其他 Mixin 提供）
    logger: logging.Logger
    _natural_gui: _NaturalGUIProtocol

    # 输入框位置候选（相对于窗口的偏移比例）
    _INPUT_BOX_POSITIONS = [
        (0.5, 80),    # 中间偏下
        (0.5, 120),   # 中间更下
        (0.33, 100),  # 左侧 1/3
        (0.67, 100),  # 右侧 2/3
    ]

    @property
    def _clipboard(self) -> _ClipboardManager:
        """懒加载剪贴板管理器。"""
        if not hasattr(self, '_clipboard_instance'):
            self._clipboard_instance = _ClipboardManager(self.logger)
        return self._clipboard_instance

    def _find_and_click_input_box(self) -> bool:
        """查找并点击微信聊天输入框。

        Returns:
            成功点击返回 True，失败返回 False
        """
        import pyautogui
        import win32gui

        try:
            hwnd = self._find_wechat_window()
            if not hwnd:
                self.logger.error("未找到微信窗口")
                return False

            self.logger.debug(f"微信窗口句柄: {hwnd}")
            rect = win32gui.GetWindowRect(hwnd)
            window_left, window_top, window_right, window_bottom = rect
            window_width = window_right - window_left

            # 尝试多个候选位置
            for x_ratio, y_offset in self._INPUT_BOX_POSITIONS:
                click_x = int(window_left + window_width * x_ratio)
                click_y = window_bottom - y_offset

                try:
                    self._natural_gui.natural_click(click_x, click_y)
                    self.logger.debug(f"点击输入框位置: ({click_x}, {click_y})")
                    return True
                except Exception:
                    continue

            # 回退：使用屏幕中央偏下位置
            screen_width, screen_height = pyautogui.size()
            fallback_x = screen_width // 2
            fallback_y = int(screen_height * 0.85)

            try:
                self._natural_gui.natural_click(fallback_x, fallback_y)
                self.logger.debug(f"使用回退位置: ({fallback_x}, {fallback_y})")
                return True
            except Exception:
                self.logger.error("所有输入框位置均失败")
                return False

        except Exception as e:
            self.logger.error(f"查找输入框失败: {e}")
            return False

    def _set_clipboard_and_paste(self, text: str) -> Optional[str]:
        """设置剪贴板内容并执行粘贴操作。

        Args:
            text: 要粘贴的文本内容

        Returns:
            原剪贴板内容（用于后续恢复），失败返回 None
        """
        # 1. 备份原剪贴板
        original_data = self._clipboard.backup()

        # 2. 设置新内容
        if not self._clipboard.set_text(text):
            return original_data

        # 3. 等待剪贴板稳定
        self._natural_gui._random_pause(0.08, 0.15)

        # 4. 验证剪贴板内容
        verify = self._clipboard.get_text()
        if verify != text:
            self.logger.warning(f"剪贴板验证不一致！期望: {text[:20]}, 实际: {str(verify)[:20]}")
        else:
            self.logger.debug(f"剪贴板设置成功: {text[:20]}...")

        # 5. 等待后执行粘贴
        self._natural_gui._random_pause(0.15, 0.25)
        self._execute_paste()

        # 6. 等待粘贴完成
        self._natural_gui._random_pause(0.4, 0.7)
        self.logger.debug("粘贴操作完成")

        return original_data

    def _execute_paste(self) -> None:
        """执行 Ctrl+V 粘贴操作。"""
        import pyautogui

        self.logger.debug("执行粘贴操作 (Ctrl+V)...")
        pyautogui.keyDown('ctrl')
        self._natural_gui._random_pause(0.03, 0.08)
        pyautogui.press('v')
        self._natural_gui._random_pause(0.03, 0.08)
        pyautogui.keyUp('ctrl')

    def _restore_clipboard(self, original_data: Optional[str]) -> None:
        """恢复剪贴板内容。"""
        if original_data:
            self._clipboard.restore(original_data)

    def _input_text_via_clipboard(self, text: str) -> bool:
        """清空当前输入框并通过剪贴板输入文本。

        Args:
            text: 要输入的文本

        Returns:
            成功返回 True，失败返回 False
        """
        try:
            # 清空当前输入框
            self._clear_input_box()

            # 粘贴文本
            original_data = self._set_clipboard_and_paste(text)

            # 恢复剪贴板
            self._restore_clipboard(original_data)
            return True
        except Exception as e:
            self.logger.error(f"通过剪贴板输入文本失败: {e}")
            return False

    def _clear_input_box(self) -> None:
        """清空当前输入框内容。"""
        import pyautogui

        pyautogui.hotkey('ctrl', 'a')
        self._natural_gui._random_pause()
        pyautogui.press('delete')
        self._natural_gui._random_pause(0.15, 0.35)

    def _search_contact_nt(self, contact_name: str) -> bool:
        """搜索联系人/群聊并打开聊天窗口（NT 框架）。

        Args:
            contact_name: 联系人名称或群聊名称

        Returns:
            成功返回 True，失败返回 False
        """
        import pyautogui
        import win32gui

        # 验证微信窗口焦点
        hwnd = self._find_wechat_window()
        if not hwnd or win32gui.GetForegroundWindow() != hwnd:
            self.logger.error("微信未获得焦点，中止搜索")
            return False

        original_data: Optional[str] = None
        try:
            # 打开搜索框
            self._open_search_box()

            # 清空搜索框
            self._clear_input_box()

            # 输入联系人名称
            original_data = self._set_clipboard_and_paste(contact_name)
            self.logger.debug(f"输入联系人名称: {contact_name}")
            self._natural_gui._random_pause(0.3, 0.6)

            # 回车打开聊天
            pyautogui.press('enter')
            self._natural_gui._random_pause(0.5, 1.0)

            self.logger.debug(f"成功搜索并打开: {contact_name}")
            return True
        except Exception as e:
            self.logger.error(f"搜索联系人失败: {e}")
            return False
        finally:
            self._restore_clipboard(original_data)

    def _open_search_box(self) -> None:
        """打开搜索框 (Ctrl+F)。"""
        import pyautogui

        pyautogui.hotkey('ctrl', 'f')
        self.logger.debug("打开搜索框 (Ctrl+F)")
        self._natural_gui._random_pause(0.5, 1.0)

    def _send_text_nt(self, message: str) -> bool:
        """发送文本消息（NT 框架）。

        发送优先级：Alt+S（主要） > Enter（备用） > Ctrl+Enter（备用）

        Args:
            message: 要发送的消息内容

        Returns:
            成功返回 True，失败返回 False
        """
        self.logger.debug(f"准备发送消息: {message[:20]}...")

        try:
            # 1. 查找并点击输入框（带重试）
            if not self._click_input_box_with_retry():
                return False

            # 2. 清空输入框
            self._clear_input_box()

            # 3. 粘贴消息内容
            original_data = self._set_clipboard_and_paste(message)
            self.logger.debug("文本输入完成，准备发送...")
            self._natural_gui._random_pause(0.4, 0.8)

            # 4. 发送消息
            success = self._try_send_message()

            # 5. 恢复剪贴板
            self._restore_clipboard(original_data)
            self.logger.debug("剪贴板已恢复")

            return success
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False

    def _click_input_box_with_retry(self) -> bool:
        """查找并点击输入框（带重试）。

        Returns:
            成功返回 True
        """
        if self._find_and_click_input_box():
            self.logger.debug("输入框已点击")
            self._natural_gui._random_pause(0.3, 0.6)
            return True

        # 等待后重试
        self.logger.warning("输入框未找到，等待后重试...")
        self._natural_gui._random_pause(0.8, 1.5)

        if self._find_and_click_input_box():
            self.logger.debug("输入框已点击（重试成功）")
            self._natural_gui._random_pause(0.3, 0.6)
            return True

        self.logger.error("输入框查找失败，发送中止")
        return False

    def _try_send_message(self) -> bool:
        """尝试发送消息，按优先级尝试不同快捷键。

        优先级：Alt+S > Enter > Ctrl+Enter

        Returns:
            成功返回 True，全部失败返回 False
        """
        import pyautogui

        send_methods = [
            ('alt', 's', "Alt+S"),
            ('enter', None, "Enter"),
            ('ctrl+enter', None, "Ctrl+Enter"),
        ]

        for method in send_methods:
            try:
                if len(method) == 3 and method[0] == 'alt':
                    pyautogui.hotkey(method[0], method[1])
                elif method[0] == 'enter':
                    pyautogui.press('enter')
                else:
                    pyautogui.hotkey('ctrl', 'enter')

                self.logger.debug(f"按下 {method[2]} 键发送消息")
                self._natural_gui._random_pause(0.5, 1.0)
                return True
            except Exception as e:
                self.logger.warning(f"{method[2]} 发送失败: {e}")
                continue

        self.logger.error("所有发送方式均失败")
        return False
