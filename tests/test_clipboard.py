#!/usr/bin/env python3
"""
测试剪贴板操作 — 跨平台剪贴板代理和 _ClipboardManager

由于剪贴板操作依赖系统环境，使用 mock 隔离测试。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 确保可以导入 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestClipboardProxy(unittest.TestCase):
    """测试跨平台剪贴板代理 (platforms.clipboard.Clipboard)。"""

    @patch('platforms.clipboard.sys')
    def test_win32_platform(self, mock_sys):
        """Windows 平台选择 WinClipboard。"""
        mock_sys.platform = 'win32'
        from platforms.clipboard import Clipboard

        with patch('platforms.clipboard.Clipboard._get_impl') as mock_get:
            mock_impl = MagicMock()
            mock_impl.backup.return_value = "test"
            mock_get.return_value = mock_impl

            clip = Clipboard()
            result = clip.backup()
            self.assertEqual(result, "test")

    @patch('platforms.clipboard.sys')
    def test_darwin_platform(self, mock_sys):
        """macOS 平台选择 MacClipboard。"""
        mock_sys.platform = 'darwin'
        from platforms.clipboard import Clipboard

        with patch('platforms.clipboard.Clipboard._get_impl') as mock_get:
            mock_impl = MagicMock()
            mock_impl.backup.return_value = "mac test"
            mock_get.return_value = mock_impl

            clip = Clipboard()
            result = clip.backup()
            self.assertEqual(result, "mac test")

    @patch('platforms.clipboard.sys')
    def test_linux_platform(self, mock_sys):
        """Linux 平台选择 LinuxClipboard。"""
        mock_sys.platform = 'linux'
        from platforms.clipboard import Clipboard

        with patch('platforms.clipboard.Clipboard._get_impl') as mock_get:
            mock_impl = MagicMock()
            mock_impl.backup.return_value = "linux test"
            mock_get.return_value = mock_impl

            clip = Clipboard()
            result = clip.backup()
            self.assertEqual(result, "linux test")

    def test_unsupported_platform(self):
        """不支持的平台抛出异常。"""
        from platforms.clipboard import Clipboard

        clip = Clipboard()
        clip._platform = "unsupported"

        with self.assertRaises(RuntimeError):
            clip._get_impl()


class TestClipboardManager(unittest.TestCase):
    """测试 _ClipboardManager (gui_operations.py)。"""

    def setUp(self):
        """创建 _ClipboardManager 实例。"""
        import logging
        from gui_operations import _ClipboardManager

        self.logger = logging.getLogger('test')
        self.cm = _ClipboardManager(self.logger)

    @patch('gui_operations.win32clipboard', create=True)
    def test_backup_success(self, mock_cb):
        """成功备份剪贴板内容。"""
        mock_cb.OpenClipboard = MagicMock()
        mock_cb.CloseClipboard = MagicMock()
        mock_cb.GetClipboardData = MagicMock(return_value="test content")
        mock_cb.CF_UNICODETEXT = 13

        result = self.cm.backup()
        self.assertEqual(result, "test content")

    @patch('gui_operations.win32clipboard', create=True)
    def test_backup_empty(self, mock_cb):
        """空剪贴板备份返回 None。"""
        mock_cb.OpenClipboard = MagicMock()
        mock_cb.CloseClipboard = MagicMock()
        mock_cb.GetClipboardData = MagicMock(side_effect=Exception("no data"))
        mock_cb.CF_UNICODETEXT = 13

        result = self.cm.backup()
        self.assertIsNone(result)

    @patch('gui_operations.win32clipboard', create=True)
    def test_restore_success(self, mock_cb):
        """成功恢复剪贴板内容。"""
        mock_cb.OpenClipboard = MagicMock()
        mock_cb.CloseClipboard = MagicMock()
        mock_cb.EmptyClipboard = MagicMock()
        mock_cb.SetClipboardText = MagicMock()
        mock_cb.CF_UNICODETEXT = 13

        result = self.cm.restore("test content")
        self.assertTrue(result)

    @patch('gui_operations.win32clipboard', create=True)
    def test_restore_none(self, mock_cb):
        """恢复 None 内容不执行操作。"""
        result = self.cm.restore(None)
        self.assertTrue(result)
        mock_cb.OpenClipboard.assert_not_called()

    @patch('gui_operations.win32clipboard', create=True)
    def test_set_text_success(self, mock_cb):
        """成功设置剪贴板文本。"""
        mock_cb.OpenClipboard = MagicMock()
        mock_cb.CloseClipboard = MagicMock()
        mock_cb.EmptyClipboard = MagicMock()
        mock_cb.SetClipboardText = MagicMock()
        mock_cb.CF_UNICODETEXT = 13

        result = self.cm.set_text("new text")
        self.assertTrue(result)

    @patch('gui_operations.win32clipboard', create=True)
    def test_get_text_success(self, mock_cb):
        """成功获取剪贴板文本。"""
        mock_cb.OpenClipboard = MagicMock()
        mock_cb.CloseClipboard = MagicMock()
        mock_cb.GetClipboardData = MagicMock(return_value="current text")
        mock_cb.CF_UNICODETEXT = 13

        result = self.cm.get_text()
        self.assertEqual(result, "current text")

    @patch('gui_operations.win32clipboard', create=True)
    @patch('gui_operations.time')
    def test_retry_on_access_denied(self, mock_time, mock_cb):
        """剪贴板被锁定时自动重试。"""
        import ctypes

        # 模拟 ERROR_ACCESS_DENIED
        error = OSError("Access denied")
        error.winerror = 5

        mock_cb.OpenClipboard = MagicMock()
        mock_cb.CloseClipboard = MagicMock()
        mock_cb.GetClipboardData = MagicMock(side_effect=[error, error, "success"])
        mock_cb.CF_UNICODETEXT = 13

        result = self.cm.get_text()
        self.assertEqual(result, "success")
        # 验证重试了 2 次（第 3 次成功）
        self.assertEqual(mock_cb.GetClipboardData.call_count, 3)


class TestGUIOperationsClipboard(unittest.TestCase):
    """测试 GUIOperationsMixin 的剪贴板相关方法。"""

    def setUp(self):
        """创建 mock 的 GUIOperationsMixin 实例。"""
        from gui_operations import GUIOperationsMixin

        class TestOps(GUIOperationsMixin):
            def __init__(self):
                import logging
                self.logger = logging.getLogger('test')
                self._natural_gui = MagicMock()
                self._natural_gui._random_pause = MagicMock()

        self.ops = TestOps()

    @patch('gui_operations.win32clipboard', create=True)
    def test_set_clipboard_and_paste(self, mock_cb):
        """设置剪贴板并粘贴。"""
        import pyautogui

        mock_cb.OpenClipboard = MagicMock()
        mock_cb.CloseClipboard = MagicMock()
        mock_cb.EmptyClipboard = MagicMock()
        mock_cb.SetClipboardText = MagicMock()
        mock_cb.GetClipboardData = MagicMock(return_value="test")
        mock_cb.CF_UNICODETEXT = 13

        with patch('pyautogui.keyDown') as mock_kd, \
             patch('pyautogui.press') as mock_press, \
             patch('pyautogui.keyUp') as mock_ku:

            result = self.ops._set_clipboard_and_paste("test text")
            self.assertIsNotNone(result)

    @patch('gui_operations.win32clipboard', create=True)
    def test_restore_clipboard(self, mock_cb):
        """恢复剪贴板内容。"""
        mock_cb.OpenClipboard = MagicMock()
        mock_cb.CloseClipboard = MagicMock()
        mock_cb.EmptyClipboard = MagicMock()
        mock_cb.SetClipboardText = MagicMock()
        mock_cb.CF_UNICODETEXT = 13

        self.ops._restore_clipboard("original content")
        mock_cb.SetClipboardText.assert_called_once_with(
            "original content", mock_cb.CF_UNICODETEXT
        )

    def test_restore_clipboard_none(self):
        """恢复 None 内容不执行操作。"""
        # 应该不抛异常
        self.ops._restore_clipboard(None)


if __name__ == '__main__':
    unittest.main()
