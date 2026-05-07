#!/usr/bin/env python3
"""
测试 macOS 平台实现 — 验证 MacWindowFinder、MacGUIOperations、MacClipboard
"""

import unittest
from unittest.mock import patch, MagicMock


# 模拟 pyobjc 框架
APPKIT_MOCK = MagicMock()
APPKIT_MOCK.NSApplicationActivateIgnoringOtherApps = 1


class FakeNSRunningApplication:
    """模拟 NSRunningApplication。"""
    def __init__(self, name='微信', pid=12345):
        self._name = name
        self._pid = pid

    def localizedName(self):
        return self._name

    def processIdentifier(self):
        return self._pid

    def bundleURL(self):
        return MagicMock()

    def activateWithOptions_(self, opts):
        pass


class FakeNSWorkspace:
    """模拟 NSWorkspace。"""
    def __init__(self, apps=None):
        self._apps = apps or [FakeNSRunningApplication()]

    def runningApplications(self):
        return self._apps

    @classmethod
    def sharedWorkspace(cls):
        return cls()


class FakeSBApplication:
    """模拟 SBApplication。"""
    def __init__(self, pid):
        self._pid = pid

    def activateWithOptions_(self, opts):
        pass

    @classmethod
    def applicationWithProcessIdentifier_(cls, pid):
        return cls(pid)


class FakeNSBundle:
    """模拟 NSBundle。"""
    def __init__(self, version='4.1.0'):
        self._version = version

    def objectForInfoDictionaryKey_(self, key):
        if key == "CFBundleShortVersionString":
            return self._version

    @classmethod
    def bundleWithURL_(cls, url):
        return cls()


class FakeNSPasteboardInst:
    """模拟 NSPasteboard — 单例模式确保所有调用共享同一个实例。"""
    _singleton = None

    def __init__(self):
        self._data = None

    def stringForType_(self, t):
        return self._data

    def clearContents(self):
        pass

    def setString_forType_(self, s, t):
        self._data = s

    @classmethod
    def generalPasteboard(cls):
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton


@patch.dict('sys.modules', {
    'AppKit': APPKIT_MOCK,
    'ScriptingBridge': MagicMock(SBApplication=FakeSBApplication),
    'Foundation': MagicMock(NSBundle=FakeNSBundle),
})
class TestMacWindowFinder(unittest.TestCase):
    """测试 MacWindowFinder。"""

    def setUp(self):
        from platforms.mac.window_finder import MacWindowFinder
        self.finder = MacWindowFinder()

    @patch('platforms.mac.window_finder.MacWindowFinder._workspace',
           return_value=FakeNSWorkspace)
    def test_find_wechat_window_found(self, mock_ws):
        """找到微信进程。"""
        pid = self.finder.find_wechat_window()
        self.assertEqual(pid, 12345)

    @patch('platforms.mac.window_finder.MacWindowFinder._workspace',
           return_value=lambda: FakeNSWorkspace([]))
    def test_find_wechat_window_not_found(self, mock_ws):
        """未找到微信进程。"""
        pid = self.finder.find_wechat_window()
        self.assertIsNone(pid)

    def test_is_wechat_available(self):
        """微信可用性检查。"""
        available = self.finder.is_wechat_available()
        self.assertIsNotNone(available)

    @patch('platforms.mac.window_finder.MacWindowFinder._sb',
           return_value=FakeSBApplication)
    def test_activate_window(self, mock_sb):
        """激活微信窗口。"""
        result = self.finder.activate_window(12345)
        self.assertTrue(result)

    def test_get_status(self):
        """获取状态信息。"""
        status = self.finder.get_status()
        self.assertIn('wechat_available', status)
        self.assertIn('platform', status)
        self.assertEqual(status['platform'], 'macos')


class TestMacClipboard(unittest.TestCase):
    """测试 MacClipboard。"""

    def setUp(self):
        FakeNSPasteboardInst._singleton = None

        self._patcher_pg = patch('platforms.mac.gui_ops._get_pg', return_value=MagicMock())
        self._patcher_pg.start()

        pasteboard = FakeNSPasteboardInst
        self._patcher_ns = patch(
            'platforms.mac.gui_ops.MacClipboard._pb',
            return_value=(pasteboard, 'public.utf8-plain-text')
        )
        self._patcher_ns.start()

        from platforms.mac.gui_ops import MacClipboard
        self.clip = MacClipboard()

    def tearDown(self):
        self._patcher_ns.stop()
        self._patcher_pg.stop()

    def test_backup_and_restore(self):
        """剪贴板备份与恢复。"""
        self.clip.set_and_paste('hello')
        backup = self.clip.backup()
        self.assertEqual(backup, 'hello')
        self.clip.restore('world')
        restored = self.clip.backup()
        self.assertEqual(restored, 'world')

    def test_backup_empty(self):
        """空剪贴板备份返回 None。"""
        backup = self.clip.backup()
        self.assertIsNone(backup)

    def test_restore_none(self):
        """恢复 None 不报错。"""
        self.clip.restore(None)


if __name__ == '__main__':
    unittest.main()
