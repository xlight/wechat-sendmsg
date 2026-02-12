#!/usr/bin/env python3
"""
微信控制器
处理微信自动化发送消息功能。
仅支持 NT 架构（WeChat 4.0+）；低于 4.0 的版本直接跳过。

通过 Mixin 模式组合各功能模块：
- TrayManagerMixin: 系统托盘图标查找与恢复
- WindowFinderMixin: 窗口查找、版本检测、窗口激活
- GUIOperationsMixin: 剪贴板操作、输入框交互、联系人搜索、消息发送
"""

import asyncio
import io
import logging
import sys
from typing import Any, Dict, Optional

import pyautogui
import win32gui

try:
    from .tray_manager import TrayManagerMixin
    from .window_finder import WindowFinderMixin
    from .gui_operations import GUIOperationsMixin
    from .anti_ban import NaturalGUIOperations
except ImportError:
    from tray_manager import TrayManagerMixin
    from window_finder import WindowFinderMixin
    from gui_operations import GUIOperationsMixin
    from anti_ban import NaturalGUIOperations


class WeChatController(TrayManagerMixin, WindowFinderMixin, GUIOperationsMixin):
    """微信自动化操作控制器（仅 NT 版本）。

    继承顺序决定 MRO：TrayManagerMixin -> WindowFinderMixin -> GUIOperationsMixin
    - TrayManagerMixin 提供托盘恢复功能，被 WindowFinderMixin 调用
    - WindowFinderMixin 提供窗口查找和激活，被 GUIOperationsMixin 调用
    - GUIOperationsMixin 提供搜索联系人和发送消息功能
    """

    def __init__(self):
        # 设置日志级别为DEBUG
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.3

        self.wechat_version: Optional[str] = None
        self.is_nt_version: bool = False
        self._last_window_kind: Optional[str] = None

        # 初始化自然 GUI 操作工具
        self._natural_gui = NaturalGUIOperations()

        self._detect_wechat_version()

    async def send_text_message(self, contact_name: str, message: str) -> Dict[str, Any]:
        """向指定联系人发送文本消息。"""
        result: Dict[str, Any] = {
            "ok": False,
            "contact_name": contact_name,
            "wechat_version": None,
            "is_nt_framework": False,
            "stage": None,
            "reason": None,
            "retry_used": None,
        }
        try:
            version = self._detect_wechat_version()
            result["wechat_version"] = version
            result["is_nt_framework"] = self.is_nt_version

            if not self.is_nt_version:
                result["stage"] = "version_check"
                result["reason"] = "non_nt_version_skipped"
                return result

            hwnd = self._find_wechat_window()
            if not hwnd:
                result["stage"] = "find_window"
                result["reason"] = "wechat_window_not_found"
                return result

            # 检查窗口大小（添加警告）
            try:
                rect = win32gui.GetWindowRect(hwnd)
                window_width = rect[2] - rect[0]
                window_height = rect[3] - rect[1]

                # 窗口太小的警告阈值
                MIN_WINDOW_WIDTH = 600
                MIN_WINDOW_HEIGHT = 400

                if window_width < MIN_WINDOW_WIDTH or window_height < MIN_WINDOW_HEIGHT:
                    self.logger.warning(
                        f"⚠️ 微信窗口尺寸过小 ({window_width}x{window_height})，"
                        f"建议至少 {MIN_WINDOW_WIDTH}x{MIN_WINDOW_HEIGHT}，"
                        f"可能导致输入框定位失败"
                    )
                    result["window_size"] = f"{window_width}x{window_height}"
                    result["window_warning"] = "window_too_small"
            except Exception as e:
                self.logger.debug(f"检查窗口大小时出错: {e}")

            if not self._activate_window(hwnd):
                result["stage"] = "activate_window"
                result["reason"] = "failed_to_activate_window"
                return result
            if not self._search_contact_nt(contact_name):
                result["stage"] = "search_contact"
                result["reason"] = "search_failed"
                return result
            self.logger.debug("联系人已打开，准备发送消息...")
            if self._send_text_nt(message):
                result["ok"] = True
                result["stage"] = "send_text"
                result["reason"] = None
                return result

            result["stage"] = "send_text"
            result["reason"] = "send_failed"
            return result

        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            result["stage"] = result["stage"] or "exception"
            result["reason"] = str(e)
            return result

    async def schedule_message(self, contact_name: str, message: str, delay_seconds: float) -> bool:
        """安排在延迟后发送消息。"""
        try:
            self.logger.info(f"Scheduling message to {contact_name} in {delay_seconds} seconds")

            async def delayed_send():
                await asyncio.sleep(delay_seconds)
                # 调用异步函数
                try:
                    await self.send_text_message(contact_name, message)
                except Exception as e:
                    self.logger.error(f"Error in delayed send: {e}")

            # 创建异步任务
            asyncio.create_task(delayed_send())

            return True

        except Exception as e:
            self.logger.error(f"Error scheduling message: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取微信控制器的当前状态。"""
        try:
            version = self._detect_wechat_version()
            hwnd = self._find_wechat_window()
            return {
                "wechat_available": hwnd is not None,
                "window_handle": hwnd,
                "wechat_version": version,
                "is_nt_framework": self.is_nt_version,
                "supported": self.is_nt_version,
                "framework_type": "NT framework (4.0+)" if self.is_nt_version else "Legacy (<4.0, skipped)"
            }
        except Exception as e:
            self.logger.error(f"Error checking status: {e}")
            return {
                "wechat_available": False,
                "error": str(e)
            }
