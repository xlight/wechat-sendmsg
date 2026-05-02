#!/usr/bin/env python3
"""
测试平台抽象层 — 验证三平台代码的语法、导入和工厂函数

重要：测试会自动跳过当前平台无法运行的测试。
"""

import sys
import unittest
from unittest.mock import patch, MagicMock


def skip_unless_platform(*platforms: str):
    """装饰器：只在指定平台上运行测试。"""
    def decorator(func):
        if sys.platform not in platforms:
            return unittest.skip(f"需要 {platforms} 平台，当前为 {sys.platform}")(func)
        return func
    return decorator


class TestPlatformAbstractBase(unittest.TestCase):
    """测试抽象基类 — 所有平台通用。"""

    def test_import_base_classes(self):
        from platforms.base import WindowFinder, GUIOperations
        for cls in [WindowFinder, GUIOperations]:
            self.assertTrue(cls)

    def test_abstract_class_cannot_instantiate(self):
        from platforms.base import WindowFinder, GUIOperations
        with self.assertRaises(TypeError):
            WindowFinder()
        with self.assertRaises(TypeError):
            GUIOperations()


class TestPlatformFactory(unittest.TestCase):
    """测试平台工厂函数。"""

    def setUp(self):
        for mod in list(sys.modules.keys()):
            if 'platforms' in mod:
                del sys.modules[mod]

    @skip_unless_platform('win32')
    @patch('sys.platform', 'win32')
    def test_platform_win32(self):
        from platforms import create_platform_impl
        f, g, c = create_platform_impl()
        self.assertEqual(type(f).__name__, 'WinWindowFinder')
        self.assertEqual(type(g).__name__, 'WinGUIOperations')
        self.assertEqual(type(c).__name__, 'WinClipboard')

    @skip_unless_platform('darwin')
    @patch.dict('sys.modules', {
        'AppKit': MagicMock(), 'ScriptingBridge': MagicMock(), 'Foundation': MagicMock(),
    })
    @patch('sys.platform', 'darwin')
    def test_platform_darwin(self):
        from platforms import create_platform_impl
        f, g, c = create_platform_impl()
        self.assertEqual(type(f).__name__, 'MacWindowFinder')
        self.assertEqual(type(g).__name__, 'MacGUIOperations')
        self.assertEqual(type(c).__name__, 'MacClipboard')

    @skip_unless_platform('linux')
    @patch('sys.platform', 'linux')
    def test_platform_linux(self):
        from platforms import create_platform_impl
        f, g, c = create_platform_impl()
        self.assertEqual(type(f).__name__, 'LinuxWindowFinder')
        self.assertEqual(type(g).__name__, 'LinuxGUIOperations')
        self.assertEqual(type(c).__name__, 'LinuxClipboard')

    def test_platform_unsupported(self):
        from platforms import create_platform_impl
        with patch('sys.platform', 'freebsd'):
            with self.assertRaises(RuntimeError):
                create_platform_impl()


class TestPlatformClipboard(unittest.TestCase):
    """测试跨平台剪贴板代理。"""

    @skip_unless_platform('win32')
    @patch('sys.platform', 'win32')
    def test_clipboard_proxy_win32(self):
        from platforms.clipboard import Clipboard
        c = Clipboard()
        c._platform = 'win32'
        self.assertEqual(type(c._get_impl()).__name__, 'WinClipboard')

    @skip_unless_platform('darwin')
    @patch.dict('sys.modules', {'AppKit': MagicMock()})
    @patch('sys.platform', 'darwin')
    def test_clipboard_proxy_darwin(self):
        from platforms.clipboard import Clipboard
        c = Clipboard()
        c._platform = 'darwin'
        self.assertEqual(type(c._get_impl()).__name__, 'MacClipboard')

    @skip_unless_platform('linux')
    @patch('sys.platform', 'linux')
    def test_clipboard_proxy_linux(self):
        from platforms.clipboard import Clipboard
        c = Clipboard()
        c._platform = 'linux'
        self.assertEqual(type(c._get_impl()).__name__, 'LinuxClipboard')


if __name__ == '__main__':
    unittest.main()
