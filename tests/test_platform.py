#!/usr/bin/env python3
"""
测试平台抽象层 — 验证三平台代码的语法、导入和工厂函数

重要：测试会自动跳过当前平台无法运行的测试。
"""

import sys
import unittest
from unittest.mock import patch, MagicMock


# ── 平台检测辅助 ──

def is_platform(platform_name: str) -> bool:
    """检测当前是否为指定平台。"""
    return sys.platform == platform_name


def skip_unless_platform(*platforms: str):
    """装饰器：只在指定平台上运行测试。"""
    def decorator(func):
        if sys.platform not in platforms:
            return unittest.skip(f"需要 {platforms} 平台，当前为 {sys.platform}")(func)
        return func
    return decorator


def _can_import_windows():
    """检查能否导入 Windows 特有的模块。"""
    try:
        import importlib
        mod = importlib.import_module('gui_operations')
        return True
    except Exception:
        return False


def _can_import_macos():
    """检查能否导入 macOS 特有的模块。"""
    try:
        import importlib
        mod = importlib.import_module('platform.mac.window_finder')
        return True
    except Exception:
        return False


def _can_import_linux():
    """检查能否导入 Linux 特有的模块。"""
    try:
        import importlib
        mod = importlib.import_module('platform.linux.window_finder')
        return True
    except Exception:
        return False


class TestPlatformAbstractBase(unittest.TestCase):
    """测试抽象基类 — 在所有平台上都运行。"""

    def test_import_base_classes(self):
        """抽象基类可正常导入。"""
        from platform.base import WindowFinder, GUIOperations
        self.assertTrue(hasattr(WindowFinder, 'find_wechat_window'))
        self.assertTrue(hasattr(WindowFinder, 'activate_window'))
        self.assertTrue(hasattr(WindowFinder, 'restore_window'))
        self.assertTrue(hasattr(WindowFinder, 'is_wechat_available'))
        self.assertTrue(hasattr(WindowFinder, 'get_status'))
        self.assertTrue(hasattr(WindowFinder, 'detect_wechat_version'))
        self.assertTrue(hasattr(GUIOperations, 'search_contact'))
        self.assertTrue(hasattr(GUIOperations, 'send_text'))
        self.assertTrue(hasattr(GUIOperations, 'click_input_box'))
        self.assertTrue(hasattr(GUIOperations, 'set_clipboard'))
        self.assertTrue(hasattr(GUIOperations, 'restore_clipboard'))

    def test_abstract_class_cannot_instantiate(self):
        """抽象基类不能直接实例化。"""
        from platform.base import WindowFinder, GUIOperations
        with self.assertRaises(TypeError):
            WindowFinder()
        with self.assertRaises(TypeError):
            GUIOperations()


class TestPlatformFactory(unittest.TestCase):
    """测试平台工厂函数。每个平台的测试仅在该平台可导入时运行。"""

    def setUp(self):
        # 清理缓存的模块导入
        for mod in list(sys.modules.keys()):
            if 'platform' in mod and mod != 'platform':
                del sys.modules[mod]

    @skip_unless_platform('win32')
    @patch('sys.platform', 'win32')
    def test_platform_win32(self):
        """Windows 平台返回 WinWindowFinder + WinGUIOperations + WinClipboard。"""
        from platform import create_platform_impl
        finder, gui, clip = create_platform_impl()
        self.assertEqual(type(finder).__name__, 'WinWindowFinder')
        self.assertEqual(type(gui).__name__, 'WinGUIOperations')
        self.assertEqual(type(clip).__name__, 'WinClipboard')

    @skip_unless_platform('darwin')
    @patch.dict('sys.modules', {
        'AppKit': MagicMock(),
        'ScriptingBridge': MagicMock(),
        'Foundation': MagicMock(),
    })
    @patch('sys.platform', 'darwin')
    def test_platform_darwin(self):
        """macOS 平台返回 MacWindowFinder + MacGUIOperations + MacClipboard。"""
        from platform import create_platform_impl
        finder, gui, clip = create_platform_impl()
        self.assertEqual(type(finder).__name__, 'MacWindowFinder')
        self.assertEqual(type(gui).__name__, 'MacGUIOperations')
        self.assertEqual(type(clip).__name__, 'MacClipboard')

    @skip_unless_platform('linux')
    @patch('sys.platform', 'linux')
    def test_platform_linux(self):
        """Linux 平台返回 LinuxWindowFinder + LinuxGUIOperations + LinuxClipboard。"""
        from platform import create_platform_impl
        finder, gui, clip = create_platform_impl()
        self.assertEqual(type(finder).__name__, 'LinuxWindowFinder')
        self.assertEqual(type(gui).__name__, 'LinuxGUIOperations')
        self.assertEqual(type(clip).__name__, 'LinuxClipboard')

    def test_platform_unsupported(self):
        """不支持的平台抛出 RuntimeError。"""
        from platform import create_platform_impl
        with patch('sys.platform', 'freebsd'):
            with self.assertRaises(RuntimeError):
                create_platform_impl()


class TestPlatformClipboard(unittest.TestCase):
    """测试跨平台剪贴板代理。仅在对应平台可导入时运行。"""

    @skip_unless_platform('win32')
    @patch('sys.platform', 'win32')
    def test_clipboard_proxy_win32(self):
        """Windows 剪贴板代理。"""
        from platform.clipboard import Clipboard
        clip = Clipboard()
        clip._platform = 'win32'
        impl = clip._get_impl()
        self.assertEqual(type(impl).__name__, 'WinClipboard')

    @patch('sys.platform', 'darwin')
    @patch.dict('sys.modules', {
        'AppKit': MagicMock(),
    })
    def test_clipboard_proxy_darwin(self):
        """macOS 剪贴板代理。"""
        if not is_platform('darwin'):
            self.skipTest("仅在 macOS 平台运行")
        from platform.clipboard import Clipboard
        clip = Clipboard()
        clip._platform = 'darwin'
        impl = clip._get_impl()
        self.assertEqual(type(impl).__name__, 'MacClipboard')

    @patch('sys.platform', 'linux')
    def test_clipboard_proxy_linux(self):
        """Linux 剪贴板代理。"""
        if not is_platform('linux'):
            self.skipTest("仅在 Linux 平台运行")
        from platform.clipboard import Clipboard
        clip = Clipboard()
        clip._platform = 'linux'
        impl = clip._get_impl()
        self.assertEqual(type(impl).__name__, 'LinuxClipboard')


if __name__ == '__main__':
    unittest.main()
