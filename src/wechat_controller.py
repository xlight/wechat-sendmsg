#!/usr/bin/env python3
"""
微信控制器
处理微信自动化发送消息功能。跨平台支持 Windows 和 macOS。

通过平台抽象层 (platform/) 自动选择当前系统的具体实现：
- Windows: WinWindowFinder + WinGUIOperations（复用现有 Mixin）
- macOS: MacWindowFinder + MacGUIOperations（pyobjc + NSPasteboard）

两种激活窗口方式（按优先级）：
1. 快捷键激活（需在微信设置中配置）
2. API 查找并激活窗口
"""

import asyncio
import io
import logging
import sys
from typing import Any, Dict, Optional

import pyautogui

try:
    from .config import Config
    from .platform import create_platform_impl
    from .anti_ban import NaturalGUIOperations
except ImportError:
    from config import Config
    from platform import create_platform_impl
    from anti_ban import NaturalGUIOperations


class WeChatController:
    """跨平台微信自动化操作控制器。

    通过平台抽象层组合窗口查找和 GUI 操作组件：
    - window_finder: 窗口查找、激活、版本检测（平台相关）
    - gui_ops: 搜索联系人、发送消息、剪贴板操作（平台相关）
    """

    def __init__(self, config: Optional[Config] = None):
        # 设置日志
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.3

        # 加载配置
        self._config: Config = config or Config()

        # 初始化自然 GUI 操作工具（跨平台，仅用于 Windows，macOS 忽略）
        self._natural_gui = NaturalGUIOperations()

        # ── 平台抽象层 ──
        self._win_finder, self._gui_ops = create_platform_impl(self._config)
        self._platform = sys.platform

        # ── 兼容属性（供现有代码引用） ──
        self.wechat_version: Optional[str] = None
        self.is_nt_version: bool = True  # macOS 微信均为 4.x+，Windows 由 _win_finder 决定
        self._last_window_kind: Optional[str] = None

        # 检测版本
        self._detect_wechat_version()

    # ==================== 公共接口 ====================

    def send_text_message_sync(self, contact_name: str, message: str) -> Dict[str, Any]:
        """向指定联系人发送文本消息（同步版本）。

        该方法为纯同步方法，供 QueueWorker 通过 run_in_executor 调用。

        激活窗口的优先级：
        1. 通过配置的快捷键激活微信窗口
        2. 快捷键失败时回退到平台 API 查找并激活窗口
        """
        result: Dict[str, Any] = {
            "ok": False,
            "contact_name": contact_name,
            "wechat_version": None,
            "is_nt_framework": False,
            "stage": None,
            "reason": None,
            "retry_used": None,
            "activation_method": None,
        }
        try:
            version = self._detect_wechat_version()
            result["wechat_version"] = version

            if self._platform == "win32":
                result["is_nt_framework"] = self.is_nt_version
                if not self.is_nt_version:
                    result["stage"] = "version_check"
                    result["reason"] = "non_nt_version_skipped"
                    return result
            else:
                result["is_nt_framework"] = True

            # ── 窗口激活：优先使用快捷键 ──
            window_id = None
            hotkey = self._config.wechat_hotkey
            window_id = self._activate_window_by_hotkey(hotkey)

            if window_id:
                result["activation_method"] = "hotkey"
                self.logger.info(f"快捷键 [{hotkey}] 激活成功，window_id={window_id}")
            else:
                # 快捷键失败，回退到平台 API
                self.logger.info("快捷键激活失败，回退到平台 API 方式")
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

            # ── 搜索联系人并发送消息 ──
            if not self._gui_ops.search_contact(contact_name):
                result["stage"] = "search_contact"
                result["reason"] = "search_failed"
                return result

            self.logger.debug("联系人已打开，准备发送消息...")
            if self._gui_ops.send_text(message):
                result["ok"] = True
                result["stage"] = "send_text"
                result["reason"] = None
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
        """向指定联系人发送文本消息（异步封装）。

        内部调用 send_text_message_sync()，保持向后兼容。
        """
        return self.send_text_message_sync(contact_name, message)

    async def schedule_message(self, contact_name: str, message: str, delay_seconds: float) -> bool:
        """安排在延迟后发送消息。"""
        try:
            self.logger.info(f"计划在 {delay_seconds} 秒后发送消息给 {contact_name}")

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
        """获取微信控制器的当前状态。"""
        try:
            return self._win_finder.get_status()
        except Exception as e:
            self.logger.error(f"获取状态失败: {e}")
            return {"wechat_available": False, "error": str(e)}

    # ==================== 内部方法 ====================

    def _detect_wechat_version(self) -> Optional[str]:
        """检测微信版本号。

        Returns:
            版本号字符串，检测失败返回 None
        """
        version = self._win_finder.detect_wechat_version()
        self.wechat_version = version
        if hasattr(self._win_finder, 'is_nt_version'):
            self.is_nt_version = self._win_finder.is_nt_version
        return version

    def _activate_window_by_hotkey(self, hotkey: str = "ctrl+alt+w") -> Optional[int]:
        """通过快捷键激活微信窗口。

        跨平台通用实现，依赖 pyautogui.hotkey()。
        Windows 上快捷键需在微信设置中配置；macOS 上使用系统级快捷键。

        Args:
            hotkey: 快捷键字符串，如 'ctrl+alt+w'，'+' 分隔

        Returns:
            窗口标识符（Windows hwnd / macOS PID），失败返回 None
        """
        if not hotkey:
            self.logger.warning("快捷键配置为空")
            return None

        try:
            keys = [k.strip().lower() for k in hotkey.split('+')]
            self.logger.info(f"尝试通过快捷键 [{hotkey}] 激活微信窗口...")

            # 将 macOS 的 command 键映射到 pyautogui
            normalized_keys = []
            for k in keys:
                if k in ('cmd', 'command', '⌘'):
                    normalized_keys.append('command')
                elif k in ('opt', 'option', 'alt', '⌥'):
                    normalized_keys.append('alt')
                elif k in ('ctrl', 'control', '^'):
                    normalized_keys.append('ctrl')
                elif k in ('shift', '⇧'):
                    normalized_keys.append('shift')
                else:
                    normalized_keys.append(k)

            pyautogui.hotkey(*normalized_keys)

            # 等待窗口激活
            import time
            time.sleep(0.5)

            # 检查窗口是否已激活
            window_id = self._win_finder.find_wechat_window()
            if window_id:
                self.logger.info(f"快捷键 [{hotkey}] 激活微信窗口成功")
                return window_id

            self.logger.debug("快捷键激活后未检测到微信窗口")
            return None

        except Exception as e:
            self.logger.debug(f"快捷键激活微信窗口出错: {e}")
            return None
