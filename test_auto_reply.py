#!/usr/bin/env python3
"""
自动回复功能测试（模拟模式，不实际操作微信）。
测试 Config、AIClient、MessageListener 的核心逻辑。
"""

import asyncio
import json
import os
import sys
import tempfile
import unittest

# 将 src 目录加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from config import Config, DEFAULTS
from ai_integration import AIClient
from message_listener import MessageListener, MentionMessage


class TestConfig(unittest.TestCase):
    """测试配置管理模块。"""

    def test_defaults(self):
        """缺失配置项时使用默认值。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({}, f)
            path = f.name
        try:
            config = Config(config_path=path)
            self.assertEqual(config.http_port, 8080)
            self.assertEqual(config.poll_interval, 5)
            self.assertEqual(config.monitored_groups, [])
            self.assertEqual(config.max_reply_chars, 1000)
            self.assertEqual(config.ai_timeout, 30)
            self.assertEqual(config.rate_limit_per_minute, 10)
        finally:
            os.unlink(path)

    def test_load_custom_values(self):
        """从配置文件加载自定义值。"""
        custom = {"http_port": 9090, "bot_name": "测试机器人", "monitored_groups": ["群A"]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(custom, f, ensure_ascii=False)
            path = f.name
        try:
            config = Config(config_path=path)
            self.assertEqual(config.http_port, 9090)
            self.assertEqual(config.bot_name, "测试机器人")
            self.assertEqual(config.monitored_groups, ["群A"])
            # 未指定的用默认值
            self.assertEqual(config.ai_timeout, 30)
        finally:
            os.unlink(path)

    def test_create_template_when_missing(self):
        """配置文件不存在时自动创建模板。"""
        path = os.path.join(tempfile.gettempdir(), "test_config_auto_create.json")
        if os.path.exists(path):
            os.unlink(path)
        try:
            config = Config(config_path=path)
            self.assertTrue(os.path.isfile(path))
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["http_port"], 8080)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_mask_secrets(self):
        """API 密钥脱敏显示。"""
        custom = {"ai_api_key": "sk-1234567890abcdef"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(custom, f)
            path = f.name
        try:
            config = Config(config_path=path)
            masked = config.to_dict(mask_secrets=True)
            self.assertNotEqual(masked["ai_api_key"], "sk-1234567890abcdef")
            self.assertIn("****", masked["ai_api_key"])
        finally:
            os.unlink(path)

    def test_update_runtime(self):
        """运行时更新配置。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({}, f)
            path = f.name
        try:
            config = Config(config_path=path)
            config.update({"monitored_groups": ["新群"], "poll_interval": 10})
            self.assertEqual(config.monitored_groups, ["新群"])
            self.assertEqual(config.poll_interval, 10)
        finally:
            os.unlink(path)


class TestAIClient(unittest.TestCase):
    """测试 AI 客户端（不实际调用 API）。"""

    def _make_config(self, **kwargs):
        data = dict(DEFAULTS)
        data.update(kwargs)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            return f.name

    def test_not_configured(self):
        """API 密钥未配置时返回提示。"""
        path = self._make_config()
        try:
            config = Config(config_path=path)
            client = AIClient(config)
            self.assertFalse(client.is_configured)
            result = asyncio.run(client.chat("hello"))
            self.assertEqual(result, "AI 服务未配置")
        finally:
            os.unlink(path)

    def test_truncate(self):
        """回复截断功能。"""
        path = self._make_config(ai_api_key="sk-test", ai_base_url="http://localhost", max_reply_chars=10)
        try:
            config = Config(config_path=path)
            client = AIClient(config)
            result = client._truncate("这是一段超过十个字符的长文本内容")
            self.assertTrue(result.endswith("...（回复已截断）"))
            self.assertTrue(len(result.replace("...（回复已截断）", "")) <= 10)
        finally:
            os.unlink(path)

    def test_extract_reply(self):
        """提取 OpenAI 格式响应中的回复文本。"""
        data = {
            "choices": [{"message": {"content": "你好！"}}]
        }
        result = AIClient._extract_reply(data)
        self.assertEqual(result, "你好！")

    def test_extract_reply_empty(self):
        """空响应返回 None。"""
        self.assertIsNone(AIClient._extract_reply({"choices": []}))
        self.assertIsNone(AIClient._extract_reply({}))


class TestMentionDetection(unittest.TestCase):
    """测试 @ 提及检测逻辑。"""

    def _make_listener(self, bot_name="小助手"):
        data = dict(DEFAULTS)
        data["bot_name"] = bot_name
        data["monitored_groups"] = ["测试群"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            path = f.name
        config = Config(config_path=path)
        # 不需要真正的 controller，只测试解析逻辑
        listener = MessageListener.__new__(MessageListener)
        listener._config = config
        listener._seen_hashes = {}
        return listener, path

    def test_detect_multiline_format(self):
        """检测多行格式的 @ 提及。"""
        listener, path = self._make_listener()
        try:
            chat_text = "张三:\n@小助手 什么是MCP协议\n李四:\n今天天气不错"
            mentions = listener._detect_mentions(chat_text, "测试群")
            self.assertEqual(len(mentions), 1)
            self.assertEqual(mentions[0].sender, "张三")
            self.assertEqual(mentions[0].content, "什么是MCP协议")
        finally:
            os.unlink(path)

    def test_detect_inline_format(self):
        """检测单行格式的 @ 提及。"""
        listener, path = self._make_listener()
        try:
            chat_text = "张三: @小助手 帮我查一下天气"
            mentions = listener._detect_mentions(chat_text, "测试群")
            self.assertEqual(len(mentions), 1)
            self.assertEqual(mentions[0].sender, "张三")
            self.assertEqual(mentions[0].content, "帮我查一下天气")
        finally:
            os.unlink(path)

    def test_no_mention(self):
        """无 @ 提及时返回空列表。"""
        listener, path = self._make_listener()
        try:
            chat_text = "张三:\n今天天气不错\n李四:\n确实"
            mentions = listener._detect_mentions(chat_text, "测试群")
            self.assertEqual(len(mentions), 0)
        finally:
            os.unlink(path)

    def test_dedup(self):
        """消息去重。"""
        listener, path = self._make_listener()
        try:
            m1 = MentionMessage(group_name="群A", sender="张三", content="你好", raw_line="test")
            m2 = MentionMessage(group_name="群A", sender="张三", content="你好", raw_line="test")
            h1 = listener._compute_hash(m1)
            h2 = listener._compute_hash(m2)
            self.assertEqual(h1, h2)

            # 不同内容的消息哈希不同
            m3 = MentionMessage(group_name="群A", sender="张三", content="再见", raw_line="test")
            h3 = listener._compute_hash(m3)
            self.assertNotEqual(h1, h3)
        finally:
            os.unlink(path)


class TestRateLimiter(unittest.TestCase):
    """测试速率限制器。"""

    def test_allow_within_limit(self):
        """在限制内允许调用。"""
        from auto_reply import RateLimiter
        limiter = RateLimiter(max_per_minute=5)
        for _ in range(5):
            self.assertTrue(limiter.allow())

    def test_deny_over_limit(self):
        """超出限制时拒绝。"""
        from auto_reply import RateLimiter
        limiter = RateLimiter(max_per_minute=2)
        self.assertTrue(limiter.allow())
        self.assertTrue(limiter.allow())
        self.assertFalse(limiter.allow())


if __name__ == "__main__":
    unittest.main()
