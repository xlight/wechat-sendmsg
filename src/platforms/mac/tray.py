#!/usr/bin/env python3
"""
macOS 菜单栏实现 — NSStatusBar (pyobjc)

使用 Apple 原生框架在菜单栏右侧创建一个状态项。
点击菜单项打开管理页面或退出。
"""

import logging

from ..tray import TrayManager, APP_NAME

logger = logging.getLogger(__name__)


class MacTrayManager(TrayManager):
    """macOS 菜单栏图标实现。"""

    def __init__(self, app, host="0.0.0.0", port=8765):
        super().__init__(app, host, port)
        self._status_item = None

    # ── pyobjc 懒加载 ──

    @staticmethod
    def _appkit():
        import AppKit
        return AppKit

    @staticmethod
    def _foundation():
        import Foundation
        return Foundation

    # ── 实现抽象方法 ──

    def _run_loop(self) -> None:
        """主线程运行 NSApplication runloop（阻塞）。"""
        # 先确保 NSApp 已初始化
        NSApp = self._appkit().NSApplication.sharedApplication()
        # 设置为代理应用（不显示 Dock 图标，仅有菜单栏）
        NSApp.setActivationPolicy_(self._appkit().NSApplicationActivationPolicyAccessory)

        self._setup_status_bar()

        logger.info(f"菜单栏图标已启动: http://{self._host}:{self._port}")
        NSApp.run()  # 阻塞

    def _exit_platform(self) -> None:
        """退出 NSApplication。"""
        logger.info("用户请求退出...")
        self.stop()
        if self._status_item is not None:
            from AppKit import NSStatusBar
            NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
        from AppKit import NSApplication
        NSApplication.sharedApplication().terminate_(None)

    # ── macOS 菜单栏 ──

    def _setup_status_bar(self) -> None:
        """创建菜单栏图标和菜单。"""
        from AppKit import (
            NSStatusBar, NSVariableStatusItemLength,
            NSMenu, NSMenuItem, NSImage,
        )

        # 创建状态栏项
        status_bar = NSStatusBar.systemStatusBar()
        self._status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)

        # 创建菜单
        menu = NSMenu.alloc().init()

        status_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"{APP_NAME} - :{self._port}", "", ""
        )
        status_item.setEnabled_(False)
        menu.addItem_(status_item)

        menu.addItem_(NSMenuItem.separatorItem())

        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "打开管理页面", 'openWeb:', ""
        )
        open_item.setTarget_(self)
        menu.addItem_(open_item)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出", 'exitApp:', ""
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self._status_item.setMenu_(menu)

        # 设置图标（始终使用 RGBA PNG 数据）
        if self._icon_image is not None:
            import io
            buf = io.BytesIO()
            # 确保为 RGBA 模式，保存为 PNG
            rgba = self._icon_image.convert('RGBA')
            rgba.save(buf, format='PNG')
            buf.seek(0)
            ns_image = NSImage.alloc().initWithData_(buf.read())
            if ns_image is not None and ns_image.isValid():
                ns_image.setSize_((18, 18))
                self._status_item.button().setImage_(ns_image)

    # ── objc action 回调 ──

    def openWeb_(self, sender) -> None:
        """打开管理页面。"""
        self._on_open_web()

    def exitApp_(self, sender) -> None:
        """退出。"""
        self._exit_platform()
