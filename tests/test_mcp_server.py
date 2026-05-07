#!/usr/bin/env python3
"""
测试 MCP 服务器 — HTTP API 端点和 MCP 工具函数

使用 httpx.AsyncClient 测试 Starlette 应用的 HTTP 端点。
使用 mock 隔离外部依赖（微信控制器、消息队列）。
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.testclient import TestClient


class TestHTTPSendEndpoint(unittest.TestCase):
    """测试 POST /api/v1/messages/send 端点。"""

    def setUp(self):
        """创建测试客户端。"""
        # 延迟导入避免全局初始化问题
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

        # Mock 外部依赖
        with patch('mcp_server.WeChatController') as mock_ctrl, \
             patch('mcp_server.MessageQueue') as mock_mq_cls, \
             patch('mcp_server.QueueWorker') as mock_worker_cls:

            mock_ctrl.return_value.get_status.return_value = {"wechat_available": True}
            mock_ctrl.return_value.send_text_message = AsyncMock(
                return_value={"ok": True, "stage": "send_text"}
            )

            # 设置消息队列 mock
            self.mock_mq = MagicMock()
            self.mock_mq.enqueue.return_value = 1
            self.mock_mq.get_stats.return_value = {
                "pending": 0, "processing": 0, "completed": 0,
                "failed": 0, "cancelled": 0, "total": 0,
            }

            # 重新加载模块以应用 mock
            import importlib
            if 'mcp_server' in sys.modules:
                importlib.reload(sys.modules['mcp_server'])

            from mcp_server import create_app
            self.app = create_app()

            # 注入 mock 到 app state
            self.app.state.message_queue = self.mock_mq
            self.app.state.queue_worker = MagicMock()
            self.app.state.queue_worker.is_running = True

            self.client = TestClient(self.app)

    def test_send_message_queue_mode(self):
        """队列模式发送消息。"""
        response = self.client.post("/api/v1/messages/send", json={
            "contact_name": "测试联系人",
            "message": "测试消息",
            "mode": "queue",
            "priority": 5,
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["mode"], "queue")
        self.assertIn("message_id", data)

    def test_send_message_missing_contact(self):
        """缺少联系人参数。"""
        response = self.client.post("/api/v1/messages/send", json={
            "message": "测试消息",
        })
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("contact_name", data["error"])

    def test_send_message_missing_message(self):
        """缺少消息内容参数。"""
        response = self.client.post("/api/v1/messages/send", json={
            "contact_name": "测试联系人",
        })
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("message", data["error"])

    def test_send_message_invalid_mode(self):
        """无效的发送模式。"""
        response = self.client.post("/api/v1/messages/send", json={
            "contact_name": "测试联系人",
            "message": "测试消息",
            "mode": "invalid",
        })
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("mode", data["error"])

    def test_send_message_invalid_priority(self):
        """无效的优先级。"""
        response = self.client.post("/api/v1/messages/send", json={
            "contact_name": "测试联系人",
            "message": "测试消息",
            "priority": 15,
        })
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("priority", data["error"])

    def test_send_message_invalid_json(self):
        """无效的 JSON 请求体。"""
        response = self.client.post(
            "/api/v1/messages/send",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)


class TestHTTPQueueEndpoints(unittest.TestCase):
    """测试队列相关 HTTP 端点。"""

    def setUp(self):
        """创建测试客户端。"""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

        with patch('mcp_server.WeChatController') as mock_ctrl, \
             patch('mcp_server.MessageQueue') as mock_mq_cls:

            mock_ctrl.return_value.get_status.return_value = {"wechat_available": True}

            self.mock_mq = MagicMock()
            self.mock_mq.get_stats.return_value = {
                "pending": 1, "processing": 0, "completed": 5,
                "failed": 0, "cancelled": 0, "total": 6,
            }
            self.mock_mq.list_messages.return_value = (
                [{"id": 1, "contact_name": "test", "status": "pending"}],
                1,
            )
            self.mock_mq.get_message.return_value = {
                "id": 1, "contact_name": "test", "message": "hello",
                "status": "pending", "mode": "queue", "priority": 5,
                "retry_count": 0, "max_retries": 3,
                "created_at": "2026-01-01T00:00:00",
                "scheduled_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
                "error_message": None,
            }
            self.mock_mq.cancel_message.return_value = {"ok": True}
            self.mock_mq.retry_message.return_value = {"ok": True}

            import importlib
            if 'mcp_server' in sys.modules:
                importlib.reload(sys.modules['mcp_server'])

            from mcp_server import create_app
            self.app = create_app()
            self.app.state.message_queue = self.mock_mq
            self.app.state.queue_worker = MagicMock()
            self.app.state.queue_worker.is_running = True

            self.client = TestClient(self.app)

    def test_queue_status(self):
        """获取队列状态。"""
        response = self.client.get("/api/v1/queue/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("stats", data)
        self.assertEqual(data["stats"]["total"], 6)

    def test_queue_messages_list(self):
        """获取消息列表。"""
        response = self.client.get("/api/v1/queue/messages")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["messages"]), 1)
        self.assertEqual(data["total"], 1)

    def test_queue_messages_with_status_filter(self):
        """按状态过滤消息列表。"""
        response = self.client.get("/api/v1/queue/messages?status=pending")
        self.assertEqual(response.status_code, 200)
        self.mock_mq.list_messages.assert_called_with(
            status="pending", limit=20, offset=0
        )

    def test_queue_message_detail(self):
        """获取单条消息详情。"""
        response = self.client.get("/api/v1/queue/messages/1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["message"]["id"], 1)

    def test_queue_message_detail_not_found(self):
        """消息不存在。"""
        self.mock_mq.get_message.return_value = None
        response = self.client.get("/api/v1/queue/messages/999")
        self.assertEqual(response.status_code, 404)

    def test_cancel_message(self):
        """取消消息。"""
        response = self.client.post("/api/v1/queue/messages/1/cancel")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

    def test_retry_message(self):
        """重试消息。"""
        response = self.client.post("/api/v1/queue/messages/1/retry")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

    def test_queue_not_initialized(self):
        """队列未初始化时返回 503。"""
        self.app.state.message_queue = None
        response = self.client.get("/api/v1/queue/status")
        self.assertEqual(response.status_code, 503)


class TestHTTPStatusEndpoint(unittest.TestCase):
    """测试 GET /api/v1/status 端点。"""

    def setUp(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

        with patch('mcp_server.WeChatController') as mock_ctrl:
            mock_ctrl.return_value.get_status.return_value = {
                "wechat_available": True,
                "wechat_version": "4.0.3.36",
            }

            import importlib
            if 'mcp_server' in sys.modules:
                importlib.reload(sys.modules['mcp_server'])

            from mcp_server import create_app
            self.app = create_app()
            self.app.state.message_queue = MagicMock()
            self.app.state.queue_worker = MagicMock()

            self.client = TestClient(self.app)

    def test_status_endpoint(self):
        """获取状态信息。"""
        response = self.client.get("/api/v1/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("wechat_status", data)


if __name__ == '__main__':
    unittest.main()
