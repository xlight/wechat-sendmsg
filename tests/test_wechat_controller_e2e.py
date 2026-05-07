#!/usr/bin/env python3
"""
测试微信控制器端到端流程

验证从激活窗口到发送消息的完整流程。
使用 mock 隔离系统级操作。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

# 确保可以导入 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestWeChatControllerE2E(unittest.TestCase):
    """测试 WeChatController 端到端流程。"""

    def setUp(self):
        """创建 mock 的控制器。"""
        with patch('wechat_controller.create_platform_impl') as mock_create:
            self.mock_win_finder = MagicMock()
            self.mock_gui_ops = MagicMock()
            self.mock_clipboard = MagicMock()

            mock_create.return_value = (
                self.mock_win_finder,
                self.mock_gui_ops,
                self.mock_clipboard,
            )

            from wechat_controller import WeChatController
            self.controller = WeChatController()

    def test_full_send_flow_success(self):
        """完整发送流程：激活窗口 → 搜索联系人 → 发送消息。"""
        # Mock 窗口查找和激活
        self.mock_win_finder.find_wechat_window.return_value = 12345
        self.mock_win_finder.activate_window.return_value = True
        self.mock_win_finder.detect_wechat_version.return_value = "4.0.3.36"

        # Mock 搜索联系人和发送消息
        self.mock_gui_ops.search_contact.return_value = True
        self.mock_gui_ops.send_text.return_value = True

        result = self.controller.send_text_message_sync("测试联系人", "测试消息")

        self.assertTrue(result["ok"])
        self.assertEqual(result["contact_name"], "测试联系人")
        self.assertEqual(result["wechat_version"], "4.0.3.36")
        self.assertEqual(result["stage"], "send_text")

        # 验证调用顺序
        self.mock_win_finder.find_wechat_window.assert_called()
        self.mock_gui_ops.search_contact.assert_called_once_with("测试联系人")
        self.mock_gui_ops.send_text.assert_called_once_with("测试消息")

    def test_send_flow_window_not_found(self):
        """窗口未找到时返回失败。"""
        self.mock_win_finder.find_wechat_window.return_value = None

        result = self.controller.send_text_message_sync("测试联系人", "测试消息")

        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "find_window")
        self.assertEqual(result["reason"], "wechat_window_not_found")

    def test_send_flow_search_failed(self):
        """搜索联系人失败时返回失败。"""
        self.mock_win_finder.find_wechat_window.return_value = 12345
        self.mock_win_finder.activate_window.return_value = True
        self.mock_gui_ops.search_contact.return_value = False

        result = self.controller.send_text_message_sync("测试联系人", "测试消息")

        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "search_contact")
        self.assertEqual(result["reason"], "search_failed")

    def test_send_flow_send_failed(self):
        """发送消息失败时返回失败。"""
        self.mock_win_finder.find_wechat_window.return_value = 12345
        self.mock_win_finder.activate_window.return_value = True
        self.mock_gui_ops.search_contact.return_value = True
        self.mock_gui_ops.send_text.return_value = False

        result = self.controller.send_text_message_sync("测试联系人", "测试消息")

        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "send_text")
        self.assertEqual(result["reason"], "send_failed")

    def test_send_with_hotkey_activation(self):
        """使用快捷键激活窗口。"""
        self.controller._config.wechat_hotkey = "ctrl+alt+w"

        # Mock 快捷键激活成功
        with patch.object(self.controller, '_activate_window_by_hotkey') as mock_hotkey:
            mock_hotkey.return_value = 12345

            self.mock_gui_ops.search_contact.return_value = True
            self.mock_gui_ops.send_text.return_value = True

            result = self.controller.send_text_message_sync("测试联系人", "测试消息")

            self.assertTrue(result["ok"])
            self.assertEqual(result["activation_method"], "hotkey")
            mock_hotkey.assert_called_once_with("ctrl+alt+w")

    def test_send_without_hotkey(self):
        """不使用快捷键时通过 API 激活。"""
        self.controller._config.wechat_hotkey = ""

        self.mock_win_finder.find_wechat_window.return_value = 12345
        self.mock_win_finder.activate_window.return_value = True
        self.mock_gui_ops.search_contact.return_value = True
        self.mock_gui_ops.send_text.return_value = True

        result = self.controller.send_text_message_sync("测试联系人", "测试消息")

        self.assertTrue(result["ok"])
        self.assertEqual(result["activation_method"], "api")

    def test_send_exception_handling(self):
        """异常时返回错误信息。"""
        self.mock_win_finder.find_wechat_window.side_effect = Exception("测试异常")

        result = self.controller.send_text_message_sync("测试联系人", "测试消息")

        self.assertFalse(result["ok"])
        self.assertIn("测试异常", result["reason"])

    def test_get_status_success(self):
        """获取状态成功。"""
        self.mock_win_finder.get_status.return_value = {
            "wechat_available": True,
            "wechat_version": "4.0.3.36",
        }

        status = self.controller.get_status()

        self.assertIn("wechat_available", status)
        self.assertTrue(status["wechat_available"])

    def test_get_status_exception(self):
        """获取状态异常时返回错误。"""
        self.mock_win_finder.get_status.side_effect = Exception("状态获取失败")

        status = self.controller.get_status()

        self.assertFalse(status["wechat_available"])
        self.assertIn("error", status)


class TestWeChatControllerAsync(unittest.TestCase):
    """测试异步接口。"""

    def setUp(self):
        """创建 mock 的控制器。"""
        with patch('wechat_controller.create_platform_impl') as mock_create:
            mock_create.return_value = (MagicMock(), MagicMock(), MagicMock())

            from wechat_controller import WeChatController
            self.controller = WeChatController()

    def test_send_text_message_async(self):
        """异步发送消息调用同步方法。"""
        with patch.object(self.controller, 'send_text_message_sync') as mock_sync:
            mock_sync.return_value = {"ok": True}

            import asyncio
            result = asyncio.run(
                self.controller.send_text_message("test", "hello")
            )

            self.assertTrue(result["ok"])
            mock_sync.assert_called_once_with("test", "hello")

    def test_schedule_message(self):
        """定时消息创建异步任务。"""
        import asyncio

        async def run():
            with patch.object(self.controller, 'send_text_message') as mock_send:
                mock_send.return_value = {"ok": True}
                result = await self.controller.schedule_message("test", "hello", 0.1)
                self.assertTrue(result)

        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
