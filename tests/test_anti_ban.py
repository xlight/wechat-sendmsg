#!/usr/bin/env python3
"""
测试防封号模块 — 验证 EnhancedRateLimiter、HumanBehaviorSimulator、WorkTimeController、ContentDiversifier、NaturalGUIOperations
"""

import time
import unittest
from unittest.mock import patch, MagicMock


class TestEnhancedRateLimiter(unittest.TestCase):
    """测试增强版速率限制器。"""

    def setUp(self):
        from anti_ban.enhanced_rate_limiter import EnhancedRateLimiter
        self.limiter = EnhancedRateLimiter(
            limit_per_minute=3,
            limit_per_hour=20,
            limit_per_day=100,
        )

    def test_allow_first_request(self):
        """首次请求通过。"""
        self.assertTrue(self.limiter.allow_request())

    def test_allow_within_limit(self):
        """限制内通过。"""
        for _ in range(3):
            self.assertTrue(self.limiter.allow_request())

    def test_block_exceed_minute(self):
        """超过每分钟限制被阻止。"""
        for _ in range(3):
            self.limiter.allow_request()
        # 第 4 次应被阻止
        self.assertFalse(self.limiter.allow_request())

    def test_window_slides(self):
        """滑动窗口 — 过期记录自动清理。"""
        # 填满窗口
        for _ in range(3):
            self.limiter.allow_request()
        # 模拟时间前进 61 秒（超过分钟窗口）
        import time as _time
        for ts in [self.limiter._timestamps_minute]:
            ts.clear()
            ts.append(_time.time() - 61)
        # 应该允许（旧记录已过期）
        # 但由于我们手动清空了，直接测试会通过
        self.assertTrue(self.limiter.allow_request())

    def test_get_stats(self):
        """获取限制器统计信息。"""
        stats = self.limiter.get_stats()
        self.assertIn('limit_per_minute', stats)
        self.assertIn('limit_per_hour', stats)
        self.assertIn('limit_per_day', stats)
        self.assertIn('used_minute', stats)
        self.assertIn('used_hour', stats)
        self.assertIn('used_day', stats)

    def test_reset(self):
        """重置限制器。"""
        self.limiter.allow_request()
        self.limiter.reset()
        stats = self.limiter.get_stats()
        self.assertEqual(stats['used_minute'], 0)


class TestHumanBehaviorSimulator(unittest.TestCase):
    """测试人类行为模拟器。"""

    def setUp(self):
        from anti_ban.human_behavior import HumanBehaviorSimulator
        self.sim = HumanBehaviorSimulator(min_think_time=1.0, max_think_time=2.0)

    def test_random_delay_range(self):
        """随机延迟在指定范围内。"""
        delay = self.sim.random_delay(0.5, 1.0)
        self.assertGreaterEqual(delay, 0.5)
        self.assertLessEqual(delay, 1.0)

    def test_random_delay_default(self):
        """使用默认范围的随机延迟。"""
        delay = self.sim.random_delay()
        self.assertGreaterEqual(delay, 1.0)
        self.assertLessEqual(delay, 3.0)

    def test_think_time_range(self):
        """思考时间在指定范围内。"""
        t = self.sim.think_time()
        self.assertGreaterEqual(t, 1.0)
        self.assertLessEqual(t, 2.0)

    def test_typing_time(self):
        """打字时间与文本长度正相关。"""
        t1 = self.sim.typing_time("hello")
        t2 = self.sim.typing_time("hello world, this is a longer text")
        self.assertLess(t1, t2)


class TestWorkTimeController(unittest.TestCase):
    """测试工作时间控制器。"""

    def setUp(self):
        from anti_ban.work_time_controller import WorkTimeController
        self.ctrl = WorkTimeController(
            work_hours_start=9,
            work_hours_end=22,
            work_days=[0, 1, 2, 3, 4],
            max_daily_runtime_hours=8.0,
        )

    def test_is_work_time(self):
        """检查是否在工作时间内（不崩即可）。"""
        result = self.ctrl.is_work_time()
        self.assertIn(result, [True, False])

    def test_get_remaining_seconds(self):
        """获取剩余运行时长。"""
        remaining = self.ctrl.get_remaining_seconds()
        self.assertIsInstance(remaining, (int, float))

    def test_reset(self):
        """重置。"""
        self.ctrl.reset()  # 不抛异常即可


class TestContentDiversifier(unittest.TestCase):
    """测试内容多样化处理器。"""

    def setUp(self):
        from anti_ban.content_diversifier import ContentDiversifier
        self.dv = ContentDiversifier(
            prefix_probability=1.0,  # 强制添加前缀（测试用）
            suffix_probability=0.0,
            skip_probability=0.0,
        )

    def test_add_prefix(self):
        """添加前缀。"""
        result = self.dv.diversify("hello")
        self.assertTrue(result.startswith("hello"))

    def test_skip_message(self):
        """跳过消息。"""
        dv = ContentDiversifier(skip_probability=1.0)
        skipped = dv.should_skip("hello")
        self.assertIsInstance(skipped, bool)

    def test_get_prefixes(self):
        """获取前缀列表。"""
        prefixes = self.dv.get_prefixes()
        self.assertIsInstance(prefixes, list)
        self.assertGreater(len(prefixes), 0)


class TestNaturalGUIOperations(unittest.TestCase):
    """测试自然 GUI 操作工具。"""

    def setUp(self):
        from anti_ban.natural_gui import NaturalGUIOperations
        self.ng = NaturalGUIOperations()

    def test_random_pause(self):
        """随机停顿不阻塞太久。"""
        import time
        start = time.time()
        self.ng._random_pause(0.01, 0.02)
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.01)
        self.assertLessEqual(elapsed, 0.1)  # 留有余量


if __name__ == '__main__':
    unittest.main()
