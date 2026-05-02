#!/usr/bin/env python3
"""
测试消息队列 — 验证 MessageQueue 和 QueueWorker
"""

import os
import json
import unittest
import tempfile
import sqlite3
import time
from unittest.mock import patch, MagicMock, PropertyMock
from typing import Dict, Any


def _create_temp_db():
    """创建临时数据库，返回 (db_path, cleanup_func)。"""
    tmpdir = tempfile.mkdtemp(prefix='wechat_test_queue_')
    db_path = os.path.join(tmpdir, 'messages.db')

    def cleanup():
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    return db_path, cleanup


class TestMessageQueue(unittest.TestCase):
    """测试 MessageQueue 存储层。"""

    def setUp(self):
        self.db_path, self.cleanup = _create_temp_db()
        from message_queue import MessageQueue
        self.queue = MessageQueue(db_path=self.db_path)

    def tearDown(self):
        self.cleanup()

    def test_enqueue(self):
        """入队 — 返回消息 ID。"""
        msg_id = self.queue.enqueue('test_contact', 'hello', mode='queue', priority=5)
        self.assertIsNotNone(msg_id)
        self.assertIsInstance(msg_id, int)
        self.assertGreater(msg_id, 0)

    def test_enqueue_with_delay(self):
        """入队（延迟）。"""
        msg_id = self.queue.enqueue('test', 'delayed msg', mode='queue',
                                     priority=5, delay_seconds=10)
        msg = self.queue.get_message(msg_id)
        self.assertIsNotNone(msg)
        self.assertEqual(msg['status'], 'pending')

    def test_enqueue_and_dequeue(self):
        """入队后出队。"""
        self.queue.enqueue('contact', 'content', mode='queue', priority=1)
        dequeued = self.queue.dequeue()
        self.assertIsNotNone(dequeued)
        self.assertEqual(dequeued['contact_name'], 'contact')
        self.assertEqual(dequeued['message'], 'content')

    def test_dequeue_empty(self):
        """空队列出队返回 None。"""
        msg = self.queue.dequeue()
        self.assertIsNone(msg)

    def test_update_status(self):
        """更新消息状态。"""
        msg_id = self.queue.enqueue('c', 'm', mode='queue', priority=5)
        self.queue.update_status(msg_id, 'processing')  # 返回 None
        msg = self.queue.get_message(msg_id)
        self.assertEqual(msg['status'], 'processing')

    def test_get_message_not_found(self):
        """获取不存在的消息。"""
        msg = self.queue.get_message(99999)
        self.assertIsNone(msg)

    def test_get_stats(self):
        """获取队列统计信息。"""
        self.queue.enqueue('c1', 'm1', mode='queue', priority=5)
        self.queue.enqueue('c2', 'm2', mode='queue', priority=5)
        stats = self.queue.get_stats()
        self.assertEqual(stats['pending'], 2)
        self.assertGreaterEqual(stats['total'], 2)

    def test_cancel_message(self):
        """取消消息。"""
        msg_id = self.queue.enqueue('c', 'm', mode='queue', priority=5)
        result = self.queue.cancel_message(msg_id)
        self.assertTrue(result['ok'])
        msg = self.queue.get_message(msg_id)
        self.assertEqual(msg['status'], 'cancelled')

    def test_retry_message(self):
        """重试失败的消息。"""
        msg_id = self.queue.enqueue('c', 'm', mode='queue', priority=5)
        self.queue.update_status(msg_id, 'failed')
        result = self.queue.retry_message(msg_id)
        self.assertTrue(result['ok'])

    def test_list_messages_pagination(self):
        """列出消息（分页）。list_messages 返回 (list, total)。"""
        # 用干净数据库测试分页
        db2, clean2 = _create_temp_db()
        from message_queue import MessageQueue
        q = MessageQueue(db_path=db2)
        for i in range(5):
            q.enqueue(f'c{i}', f'm{i}', mode='queue', priority=5)
        msgs, total = q.list_messages(limit=3, offset=0)
        self.assertEqual(len(msgs), 3)
        self.assertEqual(total, 5)
        msgs2, total2 = q.list_messages(limit=3, offset=3)
        self.assertEqual(len(msgs2), 2)
        clean2()

    def test_recover(self):
        """恢复中断的消息。"""
        msg_id = self.queue.enqueue('c', 'm', mode='queue', priority=5)
        self.queue.update_status(msg_id, 'processing')
        from message_queue import MessageQueue
        q2 = MessageQueue(db_path=self.db_path)
        recovered = q2.recover()
        self.assertGreaterEqual(recovered, 0)


class TestQueueWorker(unittest.TestCase):
    """测试 QueueWorker。"""

    def setUp(self):
        self.db_path, self.cleanup = _create_temp_db()
        from message_queue import MessageQueue, QueueWorker
        self.queue = MessageQueue(db_path=self.db_path)
        self.worker = QueueWorker(
            queue=self.queue,
            controller=MagicMock(),
            poll_interval=0.01,
        )

    def tearDown(self):
        self.cleanup()

    def test_worker_start_stop(self):
        """Worker 启停。"""
        import asyncio
        async def run():
            await self.worker.start()
            self.assertTrue(self.worker.is_running)
            await self.worker.stop()
            self.assertFalse(self.worker.is_running)

        asyncio.run(run())

    def test_execute_sync_success(self):
        """执行同步发送成功。"""
        import asyncio
        async def run():
            self.worker._controller.send_text_message_sync.return_value = {'ok': True}
            result = await self.worker.execute_sync('contact', 'hello')
            self.assertTrue(result['ok'])

        asyncio.run(run())

    def test_execute_sync_fail(self):
        """执行同步发送失败。"""
        import asyncio
        async def run():
            self.worker._controller.send_text_message_sync.return_value = {
                'ok': False, 'stage': 'send_text', 'reason': 'test_error'
            }
            result = await self.worker.execute_sync('contact', 'hello')
            self.assertFalse(result['ok'])

        asyncio.run(run())

    def test_worker_pause_resume(self):
        """Worker 暂停与恢复（不抛异常）。"""
        self.worker.pause()
        self.worker.resume()


if __name__ == '__main__':
    unittest.main()
