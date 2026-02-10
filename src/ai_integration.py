#!/usr/bin/env python3
"""
AI 服务对接模块
使用 httpx 异步调用 OpenAI 兼容 API（/v1/chat/completions），
支持系统提示词、超时处理、回复截断和 API 密钥检测。
"""

import logging
from typing import Optional

import httpx

from config import Config

logger = logging.getLogger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = "你是一个友好的 AI 助手，请简洁回答问题。"


class AIClient:
    """OpenAI 兼容 API 客户端。"""

    def __init__(self, config: Config):
        self._config = config
        self._check_api_key()

    def _check_api_key(self) -> None:
        """启动时检查 API 密钥是否已配置。"""
        if not self._config.ai_api_key:
            logger.warning("AI 服务 API 密钥未配置，@提及回复将返回提示信息")
        if not self._config.ai_base_url:
            logger.warning("AI 服务 base_url 未配置")

    @property
    def is_configured(self) -> bool:
        """API 密钥和 base_url 是否都已配置。"""
        return bool(self._config.ai_api_key) and bool(self._config.ai_base_url)

    async def chat(self, user_message: str) -> str:
        """向 AI 服务发送消息并返回回复文本。

        Args:
            user_message: 用户发送的消息内容

        Returns:
            AI 回复的文本；出错时返回预设提示消息
        """
        # 密钥未配置
        if not self.is_configured:
            return "AI 服务未配置"

        system_prompt = self._config.system_prompt or DEFAULT_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        url = f"{self._config.ai_base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.ai_api_key}",
        }
        payload = {
            "model": self._config.ai_model,
            "messages": messages,
        }

        try:
            async with httpx.AsyncClient(timeout=self._config.ai_timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            # 提取回复内容
            reply = self._extract_reply(data)
            if reply is None:
                logger.error(f"AI 响应格式异常: {data}")
                return "AI 服务返回了无法解析的响应"

            # 截断过长回复
            reply = self._truncate(reply)
            return reply

        except httpx.TimeoutException:
            logger.error(f"AI 请求超时（{self._config.ai_timeout}s）")
            return "AI 响应超时，请稍后再试"

        except httpx.HTTPStatusError as e:
            logger.error(f"AI 服务返回错误: {e.response.status_code} - {e.response.text}")
            return "AI 服务暂时不可用，请稍后再试"

        except Exception as e:
            logger.error(f"调用 AI 服务时发生异常: {e}")
            return "AI 服务暂时不可用，请稍后再试"

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_reply(data: dict) -> Optional[str]:
        """从 OpenAI 格式的响应中提取回复文本。"""
        try:
            choices = data.get("choices", [])
            if not choices:
                return None
            return choices[0].get("message", {}).get("content", "").strip()
        except (IndexError, AttributeError):
            return None

    def _truncate(self, text: str) -> str:
        """超出 max_reply_chars 时截断并附加提示。"""
        max_chars = self._config.max_reply_chars
        if max_chars > 0 and len(text) > max_chars:
            return text[:max_chars] + "...（回复已截断）"
        return text
