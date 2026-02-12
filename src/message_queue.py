#!/usr/bin/env python3
"""
消息队列模块
基于 SQLite 的本地持久化消息队列，包含存储层（MessageQueue）和消费层（QueueWorker）。
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MessageQueue:
    """消息队列存储层，基于 SQLite 实现持久化消息管理。"""

    def __init__(self, db_path: str, max_retries: int = 3):
        """初始化消息队列。

        Args:
            db_path: SQLite 数据库文件路径
            max_retries: 默认最大重试次数
        """
        self._db_path = db_path
        self._max_retries = max_retries
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库：创建目录、数据库文件和表结构。"""
        db_dir = os.path.dirname(self._db_path)
        if db_dir and not os.path.isdir(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"已创建数据库目录: {db_dir}")

        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_name    TEXT    NOT NULL,
                    message         TEXT    NOT NULL,
                    status          TEXT    NOT NULL DEFAULT 'pending',
                    mode            TEXT    NOT NULL DEFAULT 'queue',
                    priority        INTEGER NOT NULL DEFAULT 5,
                    scheduled_at    TEXT    NOT NULL,
                    created_at      TEXT    NOT NULL,
                    updated_at      TEXT    NOT NULL,
                    retry_count     INTEGER NOT NULL DEFAULT 0,
                    max_retries     INTEGER NOT NULL DEFAULT 3,
                    error_message   TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_status_priority_scheduled
                    ON messages (status, priority, scheduled_at)
            """)
            conn.commit()
            logger.info(f"消息队列数据库已初始化: {self._db_path}")
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        """获取数据库连接。"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def enqueue(
        self,
        contact_name: str,
        message: str,
        mode: str = "queue",
        priority: int = 5,
        delay_seconds: float = 0.0,
    ) -> int:
        """消息入队。

        Args:
            contact_name: 联系人名称
            message: 消息内容
            mode: 发送模式（queue/sync）
            priority: 优先级（0-10，数值越小优先级越高，默认 5）
            delay_seconds: 延迟发送秒数（0 表示立即）

        Returns:
            消息 ID
        """
        now = datetime.now()
        scheduled_at = now + timedelta(seconds=delay_seconds) if delay_seconds > 0 else now
        now_str = now.isoformat()
        scheduled_str = scheduled_at.isoformat()

        conn = self._connect()
        try:
            cursor = conn.execute(
                """
                INSERT INTO messages
                    (contact_name, message, status, mode, priority,
                     scheduled_at, created_at, updated_at, retry_count, max_retries)
                VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, 0, ?)
                """,
                (contact_name, message, mode, priority,
                 scheduled_str, now_str, now_str, self._max_retries),
            )
            conn.commit()
            msg_id = cursor.lastrowid
            logger.info(
                f"消息已入队: id={msg_id}, contact={contact_name}, "
                f"priority={priority}, mode={mode}, scheduled_at={scheduled_str}"
            )
            return msg_id
        finally:
            conn.close()

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """取出下一条待执行消息。

        查询 status=pending 且 scheduled_at <= 当前时间的消息，
        按 priority ASC, scheduled_at ASC, id ASC 排序取第一条，
        将其 status 更新为 processing。

        Returns:
            消息记录字典，无可执行消息时返回 None
        """
        now_str = datetime.now().isoformat()

        conn = self._connect()
        try:
            # 查询 + 更新在同一事务中
            row = conn.execute(
                """
                SELECT * FROM messages
                WHERE status = 'pending' AND scheduled_at <= ?
                ORDER BY priority ASC, scheduled_at ASC, id ASC
                LIMIT 1
                """,
                (now_str,),
            ).fetchone()

            if row is None:
                return None

            msg = dict(row)
            conn.execute(
                "UPDATE messages SET status = 'processing', updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), msg["id"]),
            )
            conn.commit()
            msg["status"] = "processing"
            logger.debug(f"消息已出队: id={msg['id']}, contact={msg['contact_name']}")
            return msg
        finally:
            conn.close()

    def update_status(
        self,
        message_id: int,
        status: str,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> None:
        """更新消息状态。

        Args:
            message_id: 消息 ID
            status: 新状态
            error_message: 失败原因（可选）
            retry_count: 更新后的重试次数（可选）
        """
        now_str = datetime.now().isoformat()

        conn = self._connect()
        try:
            if retry_count is not None and error_message is not None:
                conn.execute(
                    """
                    UPDATE messages
                    SET status = ?, updated_at = ?, error_message = ?, retry_count = ?
                    WHERE id = ?
                    """,
                    (status, now_str, error_message, retry_count, message_id),
                )
            elif error_message is not None:
                conn.execute(
                    """
                    UPDATE messages
                    SET status = ?, updated_at = ?, error_message = ?
                    WHERE id = ?
                    """,
                    (status, now_str, error_message, message_id),
                )
            elif retry_count is not None:
                conn.execute(
                    """
                    UPDATE messages
                    SET status = ?, updated_at = ?, retry_count = ?
                    WHERE id = ?
                    """,
                    (status, now_str, retry_count, message_id),
                )
            else:
                conn.execute(
                    "UPDATE messages SET status = ?, updated_at = ? WHERE id = ?",
                    (status, now_str, message_id),
                )
            conn.commit()
            logger.debug(f"消息状态已更新: id={message_id}, status={status}")
        finally:
            conn.close()

    def get_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        """按 ID 查询单条消息完整信息。

        Args:
            message_id: 消息 ID

        Returns:
            消息记录字典，不存在时返回 None
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM messages WHERE id = ?", (message_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_messages(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """分页列表查询。

        Args:
            status: 状态筛选（可选）
            limit: 每页数量
            offset: 偏移量

        Returns:
            (消息列表, 总数)
        """
        conn = self._connect()
        try:
            if status:
                rows = conn.execute(
                    """
                    SELECT * FROM messages WHERE status = ?
                    ORDER BY priority ASC, scheduled_at DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status, limit, offset),
                ).fetchall()
                total = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE status = ?", (status,)
                ).fetchone()[0]
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    ORDER BY created_at DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
                total = conn.execute(
                    "SELECT COUNT(*) FROM messages"
                ).fetchone()[0]

            return [dict(r) for r in rows], total
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, int]:
        """返回各状态的消息计数。

        Returns:
            各状态计数字典
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM messages
                GROUP BY status
                """
            ).fetchall()
            stats = {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
            }
            for row in rows:
                stats[row["status"]] = row["count"]
            stats["total"] = sum(stats.values())
            return stats
        finally:
            conn.close()

    def cancel_message(self, message_id: int) -> Dict[str, Any]:
        """取消待发送消息。

        Args:
            message_id: 消息 ID

        Returns:
            操作结果字典 {"ok": bool, "error": str (可选)}
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT status FROM messages WHERE id = ?", (message_id,)
            ).fetchone()

            if row is None:
                return {"ok": False, "error": f"消息不存在: id={message_id}"}

            if row["status"] != "pending":
                return {
                    "ok": False,
                    "error": f"只能取消待发送状态的消息，当前状态: {row['status']}",
                }

            conn.execute(
                "UPDATE messages SET status = 'cancelled', updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), message_id),
            )
            conn.commit()
            logger.info(f"消息已取消: id={message_id}")
            return {"ok": True}
        finally:
            conn.close()

    def retry_message(self, message_id: int) -> Dict[str, Any]:
        """手动重试失败消息。

        Args:
            message_id: 消息 ID

        Returns:
            操作结果字典 {"ok": bool, "error": str (可选)}
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT status FROM messages WHERE id = ?", (message_id,)
            ).fetchone()

            if row is None:
                return {"ok": False, "error": f"消息不存在: id={message_id}"}

            if row["status"] != "failed":
                return {
                    "ok": False,
                    "error": f"只能重试失败状态的消息，当前状态: {row['status']}",
                }

            conn.execute(
                """
                UPDATE messages
                SET status = 'pending', retry_count = 0,
                    updated_at = ?, error_message = NULL
                WHERE id = ?
                """,
                (datetime.now().isoformat(), message_id),
            )
            conn.commit()
            logger.info(f"消息已重置为待发送: id={message_id}")
            return {"ok": True}
        finally:
            conn.close()

    def recover(self) -> int:
        """进程重启恢复：将所有 processing 状态的消息重置为 pending。

        Returns:
            恢复的消息数量
        """
        conn = self._connect()
        try:
            cursor = conn.execute(
                """
                UPDATE messages
                SET status = 'pending', updated_at = ?
                WHERE status = 'processing'
                """,
                (datetime.now().isoformat(),),
            )
            conn.commit()
            count = cursor.rowcount
            if count > 0:
                logger.warning(f"已恢复 {count} 条 processing 状态的消息为 pending")
            return count
        finally:
            conn.close()


class QueueWorker:
    """队列消费 Worker，后台异步轮询并串行执行消息发送。"""

    def __init__(
        self,
        queue: MessageQueue,
        controller: Any,
        poll_interval: float = 1.0,
    ):
        """初始化队列消费 Worker。

        Args:
            queue: MessageQueue 实例
            controller: WeChatController 实例
            poll_interval: 轮询间隔（秒）
        """
        self._queue = queue
        self._controller = controller
        self._poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._current_send_task: Optional[asyncio.Task] = None
        self._resume_event = asyncio.Event()
        self._resume_event.set()  # 默认运行中

    @property
    def is_running(self) -> bool:
        """Worker 是否正在运行。"""
        return self._running

    async def start(self) -> None:
        """启动后台消费循环。"""
        if self._running:
            logger.warning("队列 Worker 已在运行中")
            return
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("队列 Worker 已启动")

    async def stop(self) -> None:
        """停止消费循环，等待当前任务完成。"""
        if not self._running:
            return
        self._running = False
        self._resume_event.set()  # 确保不卡在 pause 状态
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("队列 Worker 停止超时，强制取消")
                self._task.cancel()
            self._task = None
        logger.info("队列 Worker 已停止")

    def pause(self) -> None:
        """暂停消费循环（同步模式用）。"""
        self._resume_event.clear()
        logger.debug("队列 Worker 已暂停")

    def resume(self) -> None:
        """恢复消费循环。"""
        self._resume_event.set()
        logger.debug("队列 Worker 已恢复")

    async def execute_sync(
        self, contact_name: str, message: str
    ) -> Dict[str, Any]:
        """同步模式执行：暂停 worker → 等待当前任务 → 执行发送 → 恢复 worker。

        Args:
            contact_name: 联系人名称
            message: 消息内容

        Returns:
            发送结果字典
        """
        # 1. 暂停 worker 后续任务
        self.pause()

        try:
            # 2. 等待当前正在执行的任务完成
            if self._current_send_task and not self._current_send_task.done():
                logger.info("同步模式：等待当前任务完成...")
                try:
                    await asyncio.wait_for(self._current_send_task, timeout=60.0)
                except asyncio.TimeoutError:
                    logger.warning("等待当前任务超时")

            # 3. 立即执行同步请求
            logger.info(f"同步模式执行: contact={contact_name}")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._controller.send_text_message_sync,
                contact_name,
                message,
            )
            return result
        finally:
            # 4. 恢复 worker
            self.resume()

    async def _consume_loop(self) -> None:
        """消费循环核心逻辑。"""
        logger.info("队列消费循环已开始")
        while self._running:
            try:
                # 等待恢复信号（暂停时阻塞）
                await self._resume_event.wait()

                if not self._running:
                    break

                # 轮询取出下一条消息
                msg = self._queue.dequeue()
                if msg is None:
                    await asyncio.sleep(self._poll_interval)
                    continue

                # 在线程池中执行 GUI 发送
                logger.info(
                    f"开始发送消息: id={msg['id']}, contact={msg['contact_name']}, "
                    f"priority={msg['priority']}"
                )
                loop = asyncio.get_event_loop()
                self._current_send_task = asyncio.ensure_future(
                    loop.run_in_executor(
                        None,
                        self._controller.send_text_message_sync,
                        msg["contact_name"],
                        msg["message"],
                    )
                )

                try:
                    result = await self._current_send_task
                except Exception as e:
                    result = {"ok": False, "reason": str(e), "stage": "exception"}
                finally:
                    self._current_send_task = None

                # 根据结果更新状态
                if isinstance(result, dict) and result.get("ok"):
                    self._queue.update_status(msg["id"], "completed")
                    logger.info(f"消息发送成功: id={msg['id']}")
                else:
                    error_msg = "未知错误"
                    if isinstance(result, dict):
                        error_msg = (
                            f"stage={result.get('stage')}, "
                            f"reason={result.get('reason')}"
                        )

                    new_retry_count = msg["retry_count"] + 1
                    if new_retry_count < msg["max_retries"]:
                        # 可重试：回退为 pending
                        self._queue.update_status(
                            msg["id"],
                            "pending",
                            error_message=error_msg,
                            retry_count=new_retry_count,
                        )
                        logger.warning(
                            f"消息发送失败，将重试: id={msg['id']}, "
                            f"retry={new_retry_count}/{msg['max_retries']}, "
                            f"error={error_msg}"
                        )
                    else:
                        # 重试耗尽：标记为 failed
                        self._queue.update_status(
                            msg["id"],
                            "failed",
                            error_message=error_msg,
                            retry_count=new_retry_count,
                        )
                        logger.error(
                            f"消息发送最终失败: id={msg['id']}, error={error_msg}"
                        )

                # 发送间短暂等待，避免过于密集
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                logger.info("队列消费循环被取消")
                break
            except Exception as e:
                logger.error(f"队列消费循环异常: {e}", exc_info=True)
                await asyncio.sleep(self._poll_interval)

        logger.info("队列消费循环已结束")
