#!/usr/bin/env python3
"""
测试平台抽象层 — 验证三平台代码的语法、导入和工厂函数
"""

import sys
import unittest
from unittest.mock import patch, MagicMock


class TestPlatformAbstractBase(unittest.TestCase):
    """测试抽象基类 — 验证接口定义和类型安全性。"""

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


@patch.dict('sys.modules', {
    'AppKit': MagicMock(),
    'ScriptingBridge': MagicMock(),
    'Foundation': MagicMock(),
})
class TestPlatformFactory(unittest.TestCase):
    """测试平台工厂函数 — 验证 create_platform_impl 的分派逻辑。"""

    def setUp(self):
        # 清理缓存的模块导入
        for mod in list(sys.modules.keys()):
            if 'platform' in mod:
                del sys.modules[mod]

    def test_platform_win32(self):
        """Windows 平台返回 WinWindowFinder + WinGUIOperations + WinClipboard。"""
        with patch('sys.platform', 'win32'):
            from platform import create_platform_impl
            finder, gui, clip = create_platform_impl()
            self.assertEqual(type(finder).__name__, 'WinWindowFinder')
            self.assertEqual(type(gui).__name__, 'WinGUIOperations')
            self.assertEqual(type(clip).__name__, 'WinClipboard')

    def test_platform_darwin(self):
        """macOS 平台返回 MacWindowFinder + MacGUIOperations + MacClipboard。"""
        with patch('sys.platform', 'darwin'):
            from platform import create_platform_impl
            finder, gui, clip = create_platform_impl()
            self.assertEqual(type(finder).__name__, 'MacWindowFinder')
            self.assertEqual(type(gui).__name__, 'MacGUIOperations')
            self.assertEqual(type(clip).__name__, 'MacClipboard')

    def test_platform_linux(self):
        """Linux 平台返回 LinuxWindowFinder + LinuxGUIOperations + LinuxClipboard。"""
        with patch('sys.platform', 'linux'):
            from platform import create_platform_impl
            finder, gui, clip = create_platform_impl()
            self.assertEqual(type(finder).__name__, 'LinuxWindowFinder')
            self.assertEqual(type(gui).__name__, 'LinuxGUIOperations')
            self.assertEqual(type(clip).__name__, 'LinuxClipboard')

    def test_platform_unsupported(self):
        """不支持的平台抛出 RuntimeError。"""
        with patch('sys.platform', 'freebsd'):
            from platform import create_platform_impl
            with self.assertRaises(RuntimeError):
                create_platform_impl()


class TestPlatformClipboard(unittest.TestCase):
    """测试跨平台剪贴板代理 — 验证代理分派逻辑。"""

    def test_clipboard_proxy_win32(self):
        """Windows 剪贴板代理。"""
        from platform.clipboard import Clipboard
        clip = Clipboard()

        # 验证代理到 WinClipboard
        with patch('sys.platform', 'win32'):
            clip._platform = 'win32'
            impl = clip._detect_impl()
            self.assertEqual(type(impl).__name__, 'WinClipboard')

    def test_clipboard_proxy_darwin(self):
        """macOS 剪贴板代理。"""
        from platform.clipboard import Clipboard
        clip = Clipboard()

        with patch('sys.platform', 'darwin'):
            clip._platform = 'darwin'
            impl = clip._detect_impl()
            self.assertEqual(type(impl).__name__, 'MacClipboard')

    def test_clipboard_proxy_linux(self):
        """Linux 剪贴板代理。"""
        from platform.clipboard import Clipboard
        clip = Clipboard()

        with patch('sys.platform', 'linux'):
            clip._platform = 'linux'
            impl = clip._detect_impl()
            self.assertEqual(type(impl).__name__, 'LinuxClipboard')


if __name__ == '__main__':
    unittest.main()
