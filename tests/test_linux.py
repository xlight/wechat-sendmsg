#!/usr/bin/env python3
"""
测试 Linux 平台实现 — 验证 LinuxWindowFinder、LinuxGUIOperations、LinuxClipboard
"""

import unittest
from unittest.mock import patch


class FakePopenResult:
    """模拟 subprocess.run 返回结果。"""
    def __init__(self, stdout: str = '', returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = ''


class TestLinuxWindowFinder(unittest.TestCase):
    """测试 LinuxWindowFinder。"""

    def setUp(self):
        self._patcher_which = patch('shutil.which', return_value='/usr/bin/xdotool')
        self._patcher_which.start()

    def tearDown(self):
        self._patcher_which.stop()

    def _create_finder(self):
        from platforms.linux.window_finder import LinuxWindowFinder
        return LinuxWindowFinder()

    @patch('platforms.linux.window_finder._run')
    def test_find_wechat_window_found(self, mock_run):
        """找到微信窗口。"""
        mock_run.return_value = '1234567'
        finder = self._create_finder()
        wid = finder.find_wechat_window()
        self.assertEqual(wid, 1234567)
        mock_run.assert_called()

    @patch('platforms.linux.window_finder._run')
    def test_find_wechat_window_not_found(self, mock_run):
        """未找到微信窗口。"""
        mock_run.return_value = None
        finder = self._create_finder()
        wid = finder.find_wechat_window()
        self.assertIsNone(wid)

    @patch('platforms.linux.window_finder._run')
    def test_activate_window(self, mock_run):
        """激活微信窗口成功。"""
        mock_run.return_value = ''
        finder = self._create_finder()
        result = finder.activate_window(1234567)
        self.assertTrue(result)

    @patch('platforms.linux.window_finder._run')
    def test_activate_window_fail(self, mock_run):
        """激活微信窗口失败。"""
        mock_run.return_value = None
        finder = self._create_finder()
        result = finder.activate_window(1234567)
        self.assertFalse(result)

    def test_get_status(self):
        """获取状态信息。"""
        finder = self._create_finder()
        status = finder.get_status()
        self.assertIn('wechat_available', status)
        self.assertIn('platform', status)
        self.assertEqual(status['platform'], 'linux')
        self.assertIn('tools', status)

    def test_check_tools_missing(self):
        """xdotool 缺失时警告。"""
        with patch('shutil.which', return_value=None):
            finder = self._create_finder()
            self.assertFalse(finder._has_xdotool)
            wid = finder.find_wechat_window()
            self.assertIsNone(wid)

    @patch('platforms.linux.window_finder._run')
    def test_restore_window(self, mock_run):
        """恢复窗口。"""
        mock_run.side_effect = [
            '1234567',
            '',
            '',
            'WID=1234567',
        ]
        finder = self._create_finder()
        wid = finder.restore_window()
        self.assertEqual(wid, 1234567)


class TestLinuxClipboard(unittest.TestCase):
    """测试 LinuxClipboard。"""

    def setUp(self):
        self._patcher_which = patch('shutil.which', return_value='/usr/bin/xclip')
        self._patcher_which.start()

    def tearDown(self):
        self._patcher_which.stop()

    def _create_clip(self):
        from platforms.linux.gui_ops import LinuxClipboard
        return LinuxClipboard()

    @patch('subprocess.run')
    def test_backup(self, mock_run):
        """读取剪贴板内容。"""
        mock_run.return_value = FakePopenResult('hello')
        clip = self._create_clip()
        result = clip.backup()
        self.assertEqual(result, 'hello')

    def test_restore_none(self):
        """恢复 None 不报错。"""
        clip = self._create_clip()
        clip.restore(None)


class TestLinuxGUIOperations(unittest.TestCase):
    """测试 LinuxGUIOperations。"""

    def setUp(self):
        self._patcher_which = patch('shutil.which', return_value='/usr/bin/xclip')
        self._patcher_which.start()

    def tearDown(self):
        self._patcher_which.stop()

    def _create_gui(self):
        from platforms.linux.gui_ops import LinuxGUIOperations
        return LinuxGUIOperations()

    def test_search_contact_fail_no_window(self):
        """没有窗口时搜索失败（不崩溃）。"""
        gui = self._create_gui()
        result = gui.search_contact('test')
        self.assertIsNotNone(result)

    def test_click_input_box(self):
        """点击输入框（不崩溃即可）。"""
        gui = self._create_gui()
        gui.click_input_box()  # 只是确保不崩溃


if __name__ == '__main__':
    unittest.main()
