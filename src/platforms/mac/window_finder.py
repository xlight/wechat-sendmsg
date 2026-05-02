#!/usr/bin/env python3
"""
macOS 窗口查找与激活实现

使用 pyobjc（Apple 原生框架绑定）：
- 窗口查找: NSWorkspace 枚举运行中的应用
- 窗口激活: NSApplication.activateWithOptions()
- Dock 恢复: 通过激活应用实现（macOS 无系统托盘）
- 版本检测: 通过 NSBundle 读取 Info.plist
"""

import logging
import time
from typing import Optional, Dict, Any

from ..base import WindowFinder

logger = logging.getLogger(__name__)


class MacWindowFinder(WindowFinder):
    """macOS 平台的微信窗口查找与激活。"""

    WECHAT_APP_NAMES = ['微信', 'WeChat']

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)
        self.wechat_version: Optional[str] = None
        self._last_pid: Optional[int] = None

    # ── pyobjc 懒加载 ──

    @staticmethod
    def _appkit():
        import AppKit
        return AppKit

    @staticmethod
    def _workspace():
        from AppKit import NSWorkspace
        return NSWorkspace

    @staticmethod
    def _sb():
        from ScriptingBridge import SBApplication
        return SBApplication

    # ── WindowFinder 接口 ──

    def detect_wechat_version(self) -> Optional[str]:
        try:
            ws = self._workspace().sharedWorkspace()
            for app in ws.runningApplications():
                if app.localizedName() in self.WECHAT_APP_NAMES:
                    url = app.bundleURL()
                    if not url:
                        continue
                    from Foundation import NSBundle
                    bundle = NSBundle.bundleWithURL_(url)
                    ver = bundle.objectForInfoDictionaryKey_("CFBundleShortVersionString")
                    if ver:
                        self.wechat_version = str(ver)
                        self._logger.info(f"macOS 微信版本: {self.wechat_version}")
                        return self.wechat_version
            return None
        except Exception as e:
            self._logger.error(f"检测版本失败: {e}")
            return None

    def find_wechat_window(self) -> Optional[int]:
        self._last_pid = None
        try:
            ws = self._workspace().sharedWorkspace()
            for app in ws.runningApplications():
                if app.localizedName() in self.WECHAT_APP_NAMES:
                    pid = app.processIdentifier()
                    self._logger.info(f"找到微信进程: pid={pid}")
                    self._last_pid = pid
                    return pid
            self._logger.warning("微信未运行")
            return None
        except Exception as e:
            self._logger.error(f"查找微信失败: {e}")
            return None

    def activate_window(self, window_id: int) -> bool:
        try:
            SBApp = self._sb()
            app = SBApp.applicationWithProcessIdentifier_(window_id)
            if app is None:
                return False
            app.activateWithOptions_(self._appkit().NSApplicationActivateIgnoringOtherApps)
            time.sleep(0.5)
            self._logger.info(f"微信窗口已激活: pid={window_id}")
            return True
        except Exception as e:
            self._logger.error(f"激活窗口失败: {e}")
            return False

    def restore_window(self) -> Optional[int]:
        pid = self._last_pid or self.find_wechat_window()
        if pid is None:
            return None
        if self.activate_window(pid):
            return pid
        # 尝试强制恢复
        try:
            ws = self._workspace().sharedWorkspace()
            for app in ws.runningApplications():
                if app.localizedName() in self.WECHAT_APP_NAMES:
                    app.activateWithOptions_(
                        self._appkit().NSApplicationActivateIgnoringOtherApps
                    )
                    time.sleep(1.0)
                    self._last_pid = app.processIdentifier()
                    return self._last_pid
        except Exception as e:
            self._logger.error(f"Dock 恢复失败: {e}")
        return None

    def is_wechat_available(self) -> bool:
        return self.find_wechat_window() is not None

    def get_status(self) -> Dict[str, Any]:
        pid = self.find_wechat_window()
        ver = self.detect_wechat_version()
        return {
            "wechat_available": pid is not None,
            "pid": pid,
            "wechat_version": ver,
            "platform": "macos",
            "supported": True,
        }
