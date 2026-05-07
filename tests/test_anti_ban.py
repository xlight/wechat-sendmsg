#!/usr/bin/env python3
"""
测试防封号模块 — 验证 EnhancedRateLimiter、HumanBehaviorSimulator、WorkTimeController、ContentDiversifier、NaturalGUIOperations

注意：测试基于 anti_ban/ 模块的真实 API（见 __init__.py 中的导出）
"""

import time
import unittest


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
        self.assertTrue(self.limiter.allow())

    def test_allow_within_limit(self):
        """限制内通过。"""
        for _ in range(3):
            self.assertTrue(self.limiter.allow())

    def test_block_exceed_minute(self):
        """超过每分钟限制被阻止。"""
        for _ in range(3):
            self.limiter.allow()
        # 第 4 次应被阻止
        self.assertFalse(self.limiter.allow())

    def test_window_slides(self):
        """滑动窗口 — 过期记录自动清理。"""
        for _ in range(3):
            self.limiter.allow()
        import time as _time
        # 模拟时间前进 61 秒
        self.limiter._timestamps_minute.clear()
        self.limiter._timestamps_minute.append(_time.time() - 61)
        # 旧记录已过期，应允许
        self.assertTrue(self.limiter.allow())

    def test_get_stats(self):
        """获取限制器统计信息。"""
        stats = self.limiter.get_stats()
        self.assertIn('limit_minute', stats)
        self.assertIn('limit_hour', stats)
        self.assertIn('limit_day', stats)
        self.assertIn('last_minute', stats)

    def test_reset(self):
        """重置限制器。"""
        self.limiter.allow()
        # 手动重置
        self.limiter._timestamps_minute.clear()
        self.limiter._timestamps_hour.clear()
        self.limiter._timestamps_day.clear()
        stats = self.limiter.get_stats()
        self.assertEqual(stats['last_minute'], 0)


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

    def test_get_runtime(self):
        """获取累计运行时长。"""
        runtime = self.ctrl.get_runtime()
        self.assertIsInstance(runtime, (int, float))
        self.assertGreater(runtime, 0)

    def test_should_continue_running(self):
        """检查是否应继续运行。"""
        result = self.ctrl.should_continue_running()
        self.assertIn(result, [True, False])


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
        """强制添加前缀后的文本包含原文。"""
        result = self.dv.add_prefix("hello")
        # add_prefix 返回 "前缀，hello"，所以原文应包含在结果中
        self.assertIn("hello", result)

    def test_skip_message(self):
        """跳过消息。"""
        from anti_ban.content_diversifier import ContentDiversifier
        dv = ContentDiversifier(skip_probability=1.0)
        skipped = dv.should_skip("hello")
        self.assertIsInstance(skipped, bool)


class TestNaturalGUIOperations(unittest.TestCase):
    """测试自然 GUI 操作工具。"""

    def setUp(self):
        from anti_ban.natural_gui import NaturalGUIOperations
        self.ng = NaturalGUIOperations()

    def test_random_pause(self):
        """随机停顿不阻塞太久。"""
        start = time.time()
        self.ng._random_pause(0.01, 0.02)
        elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.01)
        self.assertLessEqual(elapsed, 0.1)


if __name__ == '__main__':
    unittest.main()
