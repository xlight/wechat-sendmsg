#!/usr/bin/env python3
"""
微信消息监听器
异步轮询群聊消息，检测 @bot_name 提及，支持去重和 GUI 操作互斥。
"""

import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass
from typing import Callable, Coroutine, Dict, List, Optional, Set

from config import Config
from wechat_controller import WeChatController

logger = logging.getLogger(__name__)

# 全局 GUI 操作互斥锁，确保消息读取和消息发送不会同时操作 GUI
gui_lock = asyncio.Lock()


@dataclass
class MentionMessage:
    """一条 @ 提及消息。"""
    group_name: str
    sender: str
    content: str
    raw_line: str


class MessageListener:
    """微信消息监听器，轮询检测新消息和 @ 提及。"""

    # 去重窗口（秒）：同一条消息在此窗口内不重复处理
    DEDUP_WINDOW = 300  # 5 分钟

    def __init__(
        self,
        config: Config,
        controller: WeChatController,
        on_mention: Optional[Callable[[MentionMessage], Coroutine]] = None,
    ):
        self._config = config
        self._controller = controller
        self._on_mention = on_mention
        self._running = False
        self._task: Optional[asyncio.Task] = None
        # 去重集合：存储消息哈希
        self._seen_hashes: Dict[str, float] = {}

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """启动轮询循环。"""
        groups = self._config.monitored_groups
        if not groups:
            logger.warning("监控群列表为空，不启动消息轮询")
            return
        if not self._config.bot_name:
            logger.warning("bot_name 未配置，无法检测 @ 提及")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"消息监听器已启动，监控群: {groups}，轮询间隔: {self._config.poll_interval}s")

    async def stop(self) -> None:
        """停止轮询循环。"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("消息监听器已停止")

    # ------------------------------------------------------------------
    # 轮询循环
    # ------------------------------------------------------------------
    async def _poll_loop(self) -> None:
        """按配置间隔轮询每个监控群的新消息。"""
        while self._running:
            try:
                for group_name in self._config.monitored_groups:
                    if not self._running:
                        break
                    await self._poll_group(group_name)
            except Exception as e:
                logger.error(f"轮询过程中出错: {e}")

            # 清理过期的去重记录
            self._cleanup_dedup()

            # 等待下一轮
            try:
                await asyncio.sleep(self._config.poll_interval)
            except asyncio.CancelledError:
                break

    async def _poll_group(self, group_name: str) -> None:
        """轮询单个群聊。"""
        logger.debug(f"开始轮询群聊: {group_name}")
        
        # 获取 GUI 互斥锁后执行读取操作
        async with gui_lock:
            chat_text = await asyncio.get_event_loop().run_in_executor(
                None, self._controller.read_chat_messages, group_name
            )

        if not chat_text:
            logger.debug(f"群聊 {group_name} 未读取到消息")
            return

        logger.info(f"成功从群聊 {group_name} 读取到 {len(chat_text)} 字符")
        
        # 输出最近几条消息预览
        lines = chat_text.strip().split('\n')
        logger.info(f"群聊消息总行数: {len(lines)}")
        
        # 显示最后 10 条消息（或全部消息如果少于 10 条）
        preview_count = min(10, len(lines))
        logger.info(f"最近 {preview_count} 行消息预览:")
        logger.info("-" * 60)
        for line in lines[-preview_count:]:
            logger.info(f"  {line}")
        logger.info("-" * 60)

        # 解析消息并检测 @ 提及
        mentions = self._detect_mentions(chat_text, group_name)
        if mentions:
            logger.info(f"在群聊 {group_name} 中检测到 {len(mentions)} 条 @ 提及")
        else:
            logger.debug(f"群聊 {group_name} 中未检测到 @ 提及")
        
        for mention in mentions:
            msg_hash = self._compute_hash(mention)
            if msg_hash in self._seen_hashes:
                logger.debug(f"跳过重复消息: {mention.sender} - {mention.content[:20]}...")
                continue
            # 标记为已处理
            self._seen_hashes[msg_hash] = time.time()
            logger.info(f"✅ 检测到新的 @ 提及 - 群: {group_name}, 发送者: {mention.sender}, 内容: {mention.content}")
            # 回调
            if self._on_mention:
                try:
                    await self._on_mention(mention)
                except Exception as e:
                    logger.error(f"处理 @ 提及消息时出错: {e}")

    # ------------------------------------------------------------------
    # @ 提及检测
    # ------------------------------------------------------------------
    def _detect_mentions(self, chat_text: str, group_name: str) -> List[MentionMessage]:
        """解析聊天文本，检测 @bot_name 格式的提及。

        微信群聊复制出的文本格式通常为:
            发送者名称:
            消息内容

        或单行格式:
            发送者名称: 消息内容
        """
        bot_name = self._config.bot_name
        if not bot_name:
            return []

        mentions: List[MentionMessage] = []
        lines = chat_text.strip().split("\n")

        # 用于匹配 @bot_name 的正则（名称后可能有空格或直接跟内容）
        at_pattern = re.compile(rf"@{re.escape(bot_name)}\s*(.*)", re.DOTALL)

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 尝试匹配 "发送者名称:" 格式的行
            sender_match = re.match(r"^(.+?)[:：]\s*$", line)
            if sender_match:
                sender = sender_match.group(1).strip()
                # 下一行是消息内容
                if i + 1 < len(lines):
                    msg_line = lines[i + 1].strip()
                    at_match = at_pattern.search(msg_line)
                    if at_match:
                        content = at_match.group(1).strip()
                        if content:
                            mentions.append(MentionMessage(
                                group_name=group_name,
                                sender=sender,
                                content=content,
                                raw_line=msg_line,
                            ))
                    i += 2
                    continue
            else:
                # 单行格式: "发送者: @bot_name 内容"
                inline_match = re.match(r"^(.+?)[:：]\s*(.+)$", line)
                if inline_match:
                    sender = inline_match.group(1).strip()
                    msg_part = inline_match.group(2).strip()
                    at_match = at_pattern.search(msg_part)
                    if at_match:
                        content = at_match.group(1).strip()
                        if content:
                            mentions.append(MentionMessage(
                                group_name=group_name,
                                sender=sender,
                                content=content,
                                raw_line=line,
                            ))
            i += 1

        return mentions

    # ------------------------------------------------------------------
    # 去重
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_hash(mention: MentionMessage) -> str:
        """基于消息内容+发送者的哈希，用于去重。"""
        raw = f"{mention.group_name}|{mention.sender}|{mention.content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cleanup_dedup(self) -> None:
        """清理超出去重时间窗口的记录。"""
        now = time.time()
        expired = [h for h, ts in self._seen_hashes.items() if now - ts > self.DEDUP_WINDOW]
        for h in expired:
            del self._seen_hashes[h]
