#!/usr/bin/env python3
"""
测试 wechat_controller — 验证跨平台控制器的基本逻辑

重要：测试会自动跳过当前平台无法运行的测试。
"""

import sys
import unittest
from unittest.mock import patch, MagicMock


# ── 平台检测 ──


def is_platform(name: str) -> bool:
    return sys.platform == name


def skip_unless_platform(*platforms):
    def decorator(func):
        if sys.platform not in platforms:
            return unittest.skip(f"需要 {platforms} 平台，当前为 {sys.platform}")(func)
        return func
    return decorator


class TestWeChatControllerDarwin(unittest.TestCase):
    """测试 macOS 平台下的控制器。"""

    @classmethod
    def setUpClass(cls):
        if not is_platform('darwin'):
            raise unittest.SkipTest("仅在 macOS 平台运行")

    def setUp(self):
        self._patcher_platform = patch('sys.platform', 'darwin')
        self._patcher_platform.start()

        self._patcher_pyobjc = patch.dict('sys.modules', {
            'AppKit': MagicMock(),
            'ScriptingBridge': MagicMock(),
            'Foundation': MagicMock(),
        })
        self._patcher_pyobjc.start()

        self._patcher_pg = patch('wechat_controller._get_pyautogui', return_value=MagicMock())
        self._patcher_pg.start()

        from wechat_controller import WeChatController
        self._config_mock = MagicMock()
        self._config_mock.wechat_hotkey = ''
        self.controller = WeChatController(config=self._config_mock)

    def tearDown(self):
        self._patcher_pg.stop()
        self._patcher_pyobjc.stop()
        self._patcher_platform.stop()

    def test_send_text_message_sync_no_window(self):
        """没有窗口时返回合理的失败信息。"""
        result = self.controller.send_text_message_sync('test', 'hello')
        self.assertFalse(result['ok'])
        self.assertEqual(result['stage'], 'find_window')

    def test_get_status(self):
        """获取状态信息（不抛异常）。"""
        status = self.controller.get_status()
        self.assertIn('wechat_available', status)

    def test_schedule_message(self):
        """定时消息创建异步任务。"""
        import asyncio

        async def run():
            result = await self.controller.schedule_message('test', 'hello', 0.1)
            self.assertTrue(result)

        asyncio.run(run())

    def test_activate_window_by_hotkey_empty(self):
        """空快捷键不执行激活。"""
        result = self.controller._activate_window_by_hotkey('')
        self.assertIsNone(result)

    def test_activate_window_by_hotkey_key_mapping(self):
        """快捷键名称映射（cmd → command）。"""
        mock_pg = MagicMock()
        with patch('wechat_controller._get_pyautogui', return_value=mock_pg):
            with patch.object(
                self.controller._win_finder, 'find_wechat_window',
                return_value=None
            ):
                result = self.controller._activate_window_by_hotkey('cmd+shift+w')
                self.assertIsNone(result)
                mock_pg.hotkey.assert_called_with('command', 'shift', 'w')

    def test_controller_reports_platform(self):
        """控制器报告平台信息。"""
        self.assertEqual(self.controller._platform, 'darwin')


class TestWeChatControllerWin32(unittest.TestCase):
    """测试 Windows 平台下的控制器。"""

    @classmethod
    def setUpClass(cls):
        if not is_platform('win32'):
            raise unittest.SkipTest("仅在 Windows 平台运行")

    def setUp(self):
        self._patcher_platform = patch('sys.platform', 'win32')
        self._patcher_platform.start()

        from wechat_controller import WeChatController
        self._config_mock = MagicMock()
        self._config_mock.wechat_hotkey = ''
        self.controller = WeChatController(config=self._config_mock)

    def tearDown(self):
        self._patcher_platform.stop()

    def test_win32_platform(self):
        """Windows 平台标识。"""
        self.assertEqual(self.controller._platform, 'win32')


if __name__ == '__main__':
    unittest.main()
