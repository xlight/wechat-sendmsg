#!/usr/bin/env python3
"""
macOS 窗口查找与激活实现

使用 pyobjc (Apple 原生框架绑定) 来操作微信窗口：
- 窗口查找: NSWorkspace 枚举运行中的应用
- 窗口激活: NSApplication.activateWithOptions()
- Dock 恢复: 通过激活应用实现（macOS 无系统托盘）
- 版本检测: 通过 NSBundle 读取 Info.plist

⚠️ 需要「辅助功能」(Accessibility) 权限：
  首次运行时，系统会弹窗请求授权。
  如果已拒绝，请前往：系统设置 → 隐私与安全性 → 辅助功能 → 允许终端/应用
"""

import logging
import time
from typing import Optional, Dict, Any, List

from .base import BaseWindowFinder

logger = logging.getLogger(__name__)


class MacWindowFinder(BaseWindowFinder):
    """macOS 平台的微信窗口查找与激活实现。

    通过 pyobjc (Apple 原生框架绑定) 操作微信，
    不需要 Accessibility API 即可完成基本操作（激活、恢复），
    但高级功能（获取窗口位置）需要 Accessibility 权限。
    """

    # 微信进程名称（中英文）
    WECHAT_APP_NAMES = ['微信', 'WeChat']

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)
        self.wechat_version: Optional[str] = None
        self._last_pid: Optional[int] = None

    # ── pyobjc 懒加载 ──────────────────────────────────────────────

    @staticmethod
    def _get_ns_appkit():
        """懒加载 AppKit 框架。"""
        import AppKit
        return AppKit

    @staticmethod
    def _get_ns_workspace():
        """懒加载 NSWorkspace。"""
        from AppKit import NSWorkspace
        return NSWorkspace

    @staticmethod
    def _get_sbapplication():
        """懒加载 ScriptingBridge。"""
        from ScriptingBridge import SBApplication
        return SBApplication

    # ── 公共接口 ──────────────────────────────────────────────────────

    def detect_wechat_version(self) -> Optional[str]:
        """通过 NSBundle 读取微信的版本号。"""
        try:
            workspace = self._get_ns_workspace().sharedWorkspace()
            for app in workspace.runningApplications():
                if app.localizedName() in self.WECHAT_APP_NAMES:
                    bundle_url = app.bundleURL()
                    if not bundle_url:
                        continue
                    from Foundation import NSBundle
                    bundle = NSBundle.bundleWithURL_(bundle_url)
                    version = bundle.objectForInfoDictionaryKey_("CFBundleShortVersionString")
                    if version:
                        self.wechat_version = str(version)
                        self._logger.info(f"检测到 macOS 微信版本: {self.wechat_version}")
                        return self.wechat_version
            return None
        except Exception as e:
            self._logger.error(f"检测微信版本失败: {e}")
            return None

    def find_wechat_window(self) -> Optional[int]:
        """查找微信进程，返回 PID。

        Returns:
            微信进程的 PID，未找到返回 None
        """
        self._last_pid = None
        try:
            workspace = self._get_ns_workspace().sharedWorkspace()
            for app in workspace.runningApplications():
                name = app.localizedName()
                if name in self.WECHAT_APP_NAMES:
                    pid = app.processIdentifier()
                    self._logger.info(f"找到微信进程: {name}, pid={pid}")
                    self._last_pid = pid
                    return pid

            self._logger.warning("未找到微信进程，请确保微信已启动")
            return None
        except Exception as e:
            self._logger.error(f"查找微信窗口失败: {e}")
            return None

    def activate_window(self, window_id: int) -> bool:
        """激活微信窗口（恢复并置前）。

        macOS 上通过 NSApplication.activateWithOptions_ 实现，
        会自动将应用窗口提到最前并从 Dock 恢复。

        Args:
            window_id: 微信进程 PID

        Returns:
            激活成功返回 True
        """
        try:
            SBApplication = self._get_sbapplication()
            app = SBApplication.applicationWithProcessIdentifier_(window_id)
            if app is None:
                self._logger.error(f"无法获取 PID={window_id} 的应用对象")
                return False

            # 激活应用（NSApplicationActivateIgnoringOtherApps = 0x01）
            NSAppKit = self._get_ns_appkit()
            app.activateWithOptions_(NSAppKit.NSApplicationActivateIgnoringOtherApps)

            # 等待窗口激活
            time.sleep(0.5)

            self._logger.info(f"微信窗口激活成功: pid={window_id}")
            self._last_pid = window_id
            return True
        except Exception as e:
            self._logger.error(f"激活微信窗口失败: {e}")
            return False

    def restore_window(self) -> Optional[int]:
        """从后台恢复微信窗口。

        macOS 上没有系统托盘概念，直接激活微信即可从 Dock 恢复。
        如果微信窗口已关闭（红点关窗），尝试通过 Dock 图标恢复。

        Returns:
            恢复后的 PID，失败返回 None
        """
        pid = self._last_pid or self.find_wechat_window()
        if pid is None:
            self._logger.warning("微信未运行，无法恢复")
            return None

        if self.activate_window(pid):
            return pid

        # 尝试通过 LaunchServices 打开（如果微信在后台但窗口被关闭）
        try:
            from AppKit import NSWorkspace
            workspace = NSWorkspace.sharedWorkspace()
            for app in workspace.runningApplications():
                if app.localizedName() in self.WECHAT_APP_NAMES:
                    # 尝试强制激活
                    app.activateWithOptions_(
                        self._get_ns_appkit().NSApplicationActivateIgnoringOtherApps
                    )
                    time.sleep(1.0)
                    pid = app.processIdentifier()
                    self._logger.info(f"通过 Dock 恢复微信成功: pid={pid}")
                    self._last_pid = pid
                    return pid
        except Exception as e:
            self._logger.error(f"Dock 恢复失败: {e}")

        return None

    def is_wechat_available(self) -> bool:
        """检查微信是否正在运行。"""
        pid = self.find_wechat_window()
        return pid is not None

    def get_status(self) -> Dict[str, Any]:
        """获取微信状态信息。"""
        pid = self.find_wechat_window()
        version = self.detect_wechat_version()
        return {
            "wechat_available": pid is not None,
            "pid": pid,
            "wechat_version": version,
            "is_nt_framework": True,  # macOS 微信均为 4.x+
            "supported": True,
            "platform": "macos",
            "framework_type": "Cocoa (macOS)",
        }
