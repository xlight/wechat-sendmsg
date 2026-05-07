#!/usr/bin/env python3
"""
测试 MCP 服务器 — HTTP API 端点

使用 Starlette TestClient 测试 HTTP 端点。
使用 mock 隔离外部依赖（微信控制器、消息队列）。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 确保可以导入 src 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from starlette.testclient import TestClient


def _create_test_client(mock_mq=None, mock_worker=None):
    """创建测试客户端，mock 全局依赖。"""
    import importlib

    # Mock 外部依赖
    with patch('mcp_server.controller') as mock_ctrl, \
         patch('mcp_server._message_queue', mock_mq), \
         patch('mcp_server._queue_worker', mock_worker):

        mock_ctrl.get_status.return_value = {"wechat_available": True}
        mock_ctrl.send_text_message = MagicMock(
            return_value={"ok": True, "stage": "send_text"}
        )

        from mcp_server import create_starlette_app
        app = create_starlette_app()

        # 注入 mock 到 app state
        if mock_mq:
            app.state.message_queue = mock_mq
        if mock_worker:
            app.state.queue_worker = mock_worker

        return TestClient(app)


class TestHTTPSendEndpoint(unittest.TestCase):
    """测试 POST /api/v1/messages/send 端点。"""

    def setUp(self):
        """创建测试客户端。"""
        self.mock_mq = MagicMock()
        self.mock_mq.enqueue.return_value = 1

        self.mock_worker = MagicMock()
        self.mock_worker.is_running = True

        self.client = _create_test_client(self.mock_mq, self.mock_worker)

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

        self.mock_worker = MagicMock()
        self.mock_worker.is_running = True

        self.client = _create_test_client(self.mock_mq, self.mock_worker)

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
        client = _create_test_client(None, None)
        response = client.get("/api/v1/queue/status")
        self.assertEqual(response.status_code, 503)


class TestHTTPStatusEndpoint(unittest.TestCase):
    """测试 GET /api/v1/status 端点。"""

    def setUp(self):
        """创建测试客户端。"""
        self.client = _create_test_client()

    def test_status_endpoint(self):
        """获取状态信息。"""
        response = self.client.get("/api/v1/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("wechat_status", data)


if __name__ == '__main__':
    unittest.main()
