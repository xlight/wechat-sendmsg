#!/usr/bin/env python3
"""
跨平台微信控制器

通过 src/platform 抽象层自动适配当前操作系统。
对外统一暴露 send_text_message_sync / send_text_message / get_status 接口。
"""

import asyncio
import io
import logging
import sys
from typing import Any, Dict, Optional

# ⚠️ pyautogui 延迟导入 — 在 macOS Python 3.13 上直接导入
# 会因 rubicon-objc 的兼容性问题崩溃。只在用到时再导入。
_pyautogui = None

# 优先尝试相对导入（作为包子模块时），回退到绝对导入（PYTHONPATH=src 时）
try:
    from .config import Config
    from .platforms import create_platform_impl
except ImportError:
    from config import Config
    from platforms import create_platform_impl


def _get_pyautogui():
    """懒加载 pyautogui。"""
    global _pyautogui
    if _pyautogui is None:
        import pyautogui as _pyautogui
    return _pyautogui


class WeChatController:
    """跨平台微信自动化操作控制器。

    组合平台抽象层的三件套：
    - _win_finder:  窗口查找、激活、版本检测
    - _gui_ops:     搜索联系人、发送消息、输入框点击
    - _clipboard:   剪贴板备份/恢复/粘贴
    """

    def __init__(self, config: Optional[Config] = None):
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # 安全包装 stdout（在测试环境中可能已关闭或被重定向）
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except (ValueError, AttributeError):
            pass

        self._init_pyautogui()

        self._config: Config = config or Config()
        self._platform = sys.platform

        # 通过抽象层创建平台相关的实现
        self._win_finder, self._gui_ops, self._clipboard = create_platform_impl(self._config)

        self.wechat_version: Optional[str] = None
        self.is_nt_version: bool = self._platform != "win32"

        self._detect_wechat_version()

    def _init_pyautogui(self):
        """安全初始化 pyautogui。"""
        try:
            pg = _get_pyautogui()
            pg.FAILSAFE = True
            pg.PAUSE = 0.3
        except Exception as e:
            self.logger.warning(f"pyautogui 初始化失败（在非 GUI 环境下正常）: {e}")

    # ==================== 公共接口 ====================

    def send_text_message_sync(self, contact_name: str, message: str) -> Dict[str, Any]:
        """向指定联系人发送文本消息（同步版本）。"""
        result: Dict[str, Any] = {
            "ok": False,
            "contact_name": contact_name,
            "wechat_version": None,
            "stage": None,
            "reason": None,
            "activation_method": None,
        }
        try:
            version = self._detect_wechat_version()
            result["wechat_version"] = version

            window_id = None
            hotkey = self._config.wechat_hotkey

            if hotkey:
                window_id = self._activate_window_by_hotkey(hotkey)

            if window_id:
                result["activation_method"] = "hotkey"
                self.logger.info(f"快捷键 [{hotkey}] 激活成功")
            else:
                window_id = self._win_finder.find_wechat_window()
                if not window_id:
                    result["stage"] = "find_window"
                    result["reason"] = "wechat_window_not_found"
                    return result

                if not self._win_finder.activate_window(window_id):
                    result["stage"] = "activate_window"
                    result["reason"] = "failed_to_activate_window"
                    return result
                result["activation_method"] = "api"

            if not self._gui_ops.search_contact(contact_name):
                result["stage"] = "search_contact"
                result["reason"] = "search_failed"
                return result

            self.logger.debug("联系人已打开，准备发送消息...")
            if self._gui_ops.send_text(message):
                result["ok"] = True
                result["stage"] = "send_text"
                return result

            result["stage"] = "send_text"
            result["reason"] = "send_failed"
            return result

        except Exception as e:
            self.logger.error(f"发送消息出错: {e}")
            result["stage"] = result["stage"] or "exception"
            result["reason"] = str(e)
            return result

    async def send_text_message(self, contact_name: str, message: str) -> Dict[str, Any]:
        """异步发送消息。"""
        return self.send_text_message_sync(contact_name, message)

    async def schedule_message(self, contact_name: str, message: str, delay_seconds: float) -> bool:
        """安排延迟发送。"""
        try:
            self.logger.info(f"计划 {delay_seconds}s 后发送给 {contact_name}")

            async def delayed_send():
                await asyncio.sleep(delay_seconds)
                try:
                    await self.send_text_message(contact_name, message)
                except Exception as e:
                    self.logger.error(f"延迟发送出错: {e}")

            asyncio.create_task(delayed_send())
            return True
        except Exception as e:
            self.logger.error(f"计划消息失败: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取微信控制器状态。"""
        try:
            return self._win_finder.get_status()
        except Exception as e:
            self.logger.error(f"获取状态失败: {e}")
            return {"wechat_available": False, "error": str(e)}

    # ==================== 内部方法 ====================

    def _detect_wechat_version(self) -> Optional[str]:
        """检测微信版本。"""
        version = self._win_finder.detect_wechat_version()
        self.wechat_version = version
        if hasattr(self._win_finder, 'is_nt_version'):
            self.is_nt_version = self._win_finder.is_nt_version
        return version

    def _activate_window_by_hotkey(self, hotkey: str) -> Optional[int]:
        """通过快捷键激活微信窗口。"""
        if not hotkey:
            return None

        try:
            keys = [k.strip().lower() for k in hotkey.split('+')]

            mapping = {
                'cmd': 'command', 'command': 'command', '⌘': 'command',
                'opt': 'alt', 'option': 'alt', '⌥': 'alt',
                'ctrl': 'ctrl', 'control': 'ctrl', '^': 'ctrl',
                'shift': 'shift', '⇧': 'shift',
            }
            normalized = [mapping.get(k, k) for k in keys]

            self.logger.info(f"尝试快捷键 [{hotkey}] 激活...")
            pg = _get_pyautogui()
            pg.hotkey(*normalized)
            import time
            time.sleep(0.5)

            window_id = self._win_finder.find_wechat_window()
            if window_id:
                self.logger.info(f"快捷键激活成功")
                return window_id

            self.logger.debug("快捷键激活后未检测到微信窗口")
            return None

        except Exception as e:
            self.logger.debug(f"快捷键激活失败: {e}")
            return None
