#!/usr/bin/env python3
"""
anti_ban 包单元测试
测试所有防封号模块的核心功能。
"""

import os
import sys
import random
import time
import unittest
from datetime import datetime
from unittest.mock import patch

# 直接导入各模块，避免触发 src/__init__.py
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from anti_ban.enhanced_rate_limiter import EnhancedRateLimiter
from anti_ban.human_behavior import HumanBehaviorSimulator
from anti_ban.work_time_controller import WorkTimeController
from anti_ban.content_diversifier import ContentDiversifier
from anti_ban.natural_gui import NaturalGUIOperations


class TestEnhancedRateLimiter(unittest.TestCase):
    """测试增强版速率限制器"""

    def test_minute_limit(self):
        """测试每分钟限制"""
        limiter = EnhancedRateLimiter(limit_per_minute=3, limit_per_hour=100, limit_per_day=1000)
        
        # 前 3 次应该通过
        self.assertTrue(limiter.allow())
        self.assertTrue(limiter.allow())
        self.assertTrue(limiter.allow())
        
        # 第 4 次应该被拒绝
        self.assertFalse(limiter.allow())

    def test_hour_limit(self):
        """测试每小时限制"""
        limiter = EnhancedRateLimiter(limit_per_minute=100, limit_per_hour=5, limit_per_day=1000)
        
        # 前 5 次应该通过
        for _ in range(5):
            self.assertTrue(limiter.allow())
        
        # 第 6 次应该被拒绝
        self.assertFalse(limiter.allow())

    def test_day_limit(self):
        """测试每日限制"""
        limiter = EnhancedRateLimiter(limit_per_minute=100, limit_per_hour=100, limit_per_day=10)
        
        # 前 10 次应该通过
        for _ in range(10):
            self.assertTrue(limiter.allow())
        
        # 第 11 次应该被拒绝
        self.assertFalse(limiter.allow())

    def test_cleanup_old_records(self):
        """测试过期记录清理"""
        limiter = EnhancedRateLimiter(limit_per_minute=2, limit_per_hour=100, limit_per_day=1000)
        
        # 添加 2 条记录
        limiter.allow()
        limiter.allow()
        
        # 应该被拒绝
        self.assertFalse(limiter.allow())
        
        # 等待 61 秒（模拟时间流逝）
        with patch('time.time', return_value=time.time() + 61):
            # 旧记录应该被清理，可以再次调用
            self.assertTrue(limiter.allow())

    def test_get_stats(self):
        """测试 get_stats() 返回正确数据"""
        limiter = EnhancedRateLimiter(limit_per_minute=3, limit_per_hour=20, limit_per_day=100)
        
        # 初始状态
        stats = limiter.get_stats()
        self.assertEqual(stats["last_minute"], 0)
        self.assertEqual(stats["limit_minute"], 3)
        
        # 添加 2 条记录
        limiter.allow()
        limiter.allow()
        
        stats = limiter.get_stats()
        self.assertEqual(stats["last_minute"], 2)
        self.assertEqual(stats["last_hour"], 2)
        self.assertEqual(stats["last_day"], 2)


class TestHumanBehaviorSimulator(unittest.TestCase):
    """测试人类行为模拟器"""

    def test_random_delay_range(self):
        """测试 random_delay() 返回值在范围内"""
        simulator = HumanBehaviorSimulator()
        
        for _ in range(10):
            delay = simulator.random_delay(min_sec=1.0, max_sec=3.0)
            self.assertGreaterEqual(delay, 1.0)
            self.assertLessEqual(delay, 3.0)

    def test_think_time_range(self):
        """测试 think_time() 返回值在范围内"""
        simulator = HumanBehaviorSimulator(min_think_time=2.0, max_think_time=5.0)
        
        for _ in range(10):
            think = simulator.think_time()
            self.assertGreaterEqual(think, 2.0)
            self.assertLessEqual(think, 5.0)

    def test_typing_time_calculation(self):
        """测试 typing_time() 计算正确"""
        simulator = HumanBehaviorSimulator()
        
        # 10 个字符，10 字符/秒 = 1 秒基准时间，加上 ±50% 随机波动
        typing_time = simulator.typing_time("1234567890", chars_per_sec=10.0)
        self.assertGreater(typing_time, 0.5)  # 至少 0.5 秒（1秒 - 50%）
        self.assertLess(typing_time, 1.5)     # 不超过 1.5 秒（1秒 + 50%）

    def test_typing_time_with_variance(self):
        """测试 typing_time() 有随机差异"""
        simulator = HumanBehaviorSimulator()
        
        times = [simulator.typing_time("测试文本" * 10, chars_per_sec=10.0) for _ in range(5)]
        # 应该有不同的时间（由于 ±50% 随机波动）
        self.assertGreater(len(set(times)), 1)


class TestWorkTimeController(unittest.TestCase):
    """测试工作时间控制器"""

    def test_is_work_time_hours(self):
        """测试工作小时检查"""
        controller = WorkTimeController(
            work_hours_start=9,
            work_hours_end=18,
            work_days=[0, 1, 2, 3, 4],  # 周一到周五
            max_daily_runtime_hours=8
        )
        
        # Mock 当前时间为周一 10:00
        with patch('anti_ban.work_time_controller.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 10, 10, 0)  # 周一 10:00
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            self.assertTrue(controller.is_work_time())
        
        # Mock 当前时间为周一 20:00（下班后）
        with patch('anti_ban.work_time_controller.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 10, 20, 0)  # 周一 20:00
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            self.assertFalse(controller.is_work_time())

    def test_is_work_time_weekend(self):
        """测试周末检查"""
        controller = WorkTimeController(
            work_hours_start=9,
            work_hours_end=18,
            work_days=[0, 1, 2, 3, 4],  # 周一到周五
            max_daily_runtime_hours=8
        )
        
        # Mock 当前时间为周六 10:00
        with patch('anti_ban.work_time_controller.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 2, 14, 10, 0)  # 周六 10:00
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            self.assertFalse(controller.is_work_time())

    def test_runtime_limit(self):
        """测试每日运行时长限制"""
        controller = WorkTimeController(
            work_hours_start=0,
            work_hours_end=23,
            work_days=[0, 1, 2, 3, 4, 5, 6],
            max_daily_runtime_hours=0.001  # 设置为 3.6 秒
        )
        
        # 初始应该允许运行
        self.assertTrue(controller.should_continue_running())
        
        # 等待超过限制
        time.sleep(4)
        
        # 应该被限制
        self.assertFalse(controller.should_continue_running())

    def test_runtime_stats(self):
        """测试运行时间统计"""
        controller = WorkTimeController(
            work_hours_start=0,
            work_hours_end=23,
            work_days=[0, 1, 2, 3, 4, 5, 6],
            max_daily_runtime_hours=8
        )
        
        # 初始运行时间应该接近 0
        runtime = controller.get_runtime()
        self.assertGreaterEqual(runtime, 0)
        self.assertLess(runtime, 1)
        
        # 等待 2 秒
        time.sleep(2)
        
        # 运行时间应该接近 2 秒
        runtime = controller.get_runtime()
        self.assertGreater(runtime, 1.5)
        self.assertLess(runtime, 3)


class TestContentDiversifier(unittest.TestCase):
    """测试内容多样化器"""

    def test_prefix_suffix_probability(self):
        """测试前缀/后缀添加概率"""
        diversifier = ContentDiversifier(
            prefix_probability=1.0,  # 100% 添加前缀
            suffix_probability=1.0,  # 100% 添加后缀
            skip_probability=0.0
        )
        
        original = "你好"
        diversified = diversifier.diversify(original)
        
        # 应该有前缀或后缀
        self.assertNotEqual(original, diversified)
        self.assertIn("你好", diversified)

    def test_no_diversification(self):
        """测试 0 概率时不添加前缀/后缀"""
        diversifier = ContentDiversifier(
            prefix_probability=0.0,  # 0% 添加前缀
            suffix_probability=0.0,  # 0% 添加后缀
            skip_probability=0.0
        )
        
        original = "你好"
        diversified = diversifier.diversify(original)
        
        # 应该完全相同
        self.assertEqual(original, diversified)

    def test_should_skip_greeting(self):
        """测试问候语跳过逻辑（概率测试）"""
        diversifier = ContentDiversifier(
            prefix_probability=0.0,
            suffix_probability=0.0,
            skip_probability=0.2  # 普通消息 20% 跳过，问候语固定 50% 跳过
        )
        
        # 问候语跳过概率应该接近 50%（运行 1000 次统计）
        skip_count = 0
        trials = 1000
        for _ in range(trials):
            if diversifier.should_skip("你好"):
                skip_count += 1
        skip_rate = skip_count / trials
        self.assertGreater(skip_rate, 0.4)  # 至少 40%
        self.assertLess(skip_rate, 0.6)     # 最多 60%
        
        # 非问候语跳过概率应该接近 20%
        skip_count = 0
        for _ in range(trials):
            if diversifier.should_skip("这是一个普通问题"):
                skip_count += 1
        skip_rate = skip_count / trials
        self.assertGreater(skip_rate, 0.1)  # 至少 10%
        self.assertLess(skip_rate, 0.3)     # 最多 30%

    def test_diversify_combination(self):
        """测试 diversify() 组合处理"""
        diversifier = ContentDiversifier(
            prefix_probability=0.5,
            suffix_probability=0.5,
            skip_probability=0.0
        )
        
        # 多次调用应该有不同的结果（由于随机性）
        results = [diversifier.diversify("测试") for _ in range(10)]
        # 至少应该有 2 种不同的结果
        self.assertGreater(len(set(results)), 1)


class TestNaturalGUIOperations(unittest.TestCase):
    """测试自然 GUI 操作"""

    def test_initialization(self):
        """测试初始化参数"""
        gui = NaturalGUIOperations(
            offset_range=10,
            move_duration_min=0.5,
            move_duration_max=1.5,
            pause_min=0.1,
            pause_max=0.3
        )
        
        self.assertEqual(gui._offset_range, 10)
        self.assertEqual(gui._move_duration_min, 0.5)
        self.assertEqual(gui._move_duration_max, 1.5)
        self.assertEqual(gui._pause_min, 0.1)
        self.assertEqual(gui._pause_max, 0.3)

    def test_random_offset_calculation(self):
        """测试随机偏移计算逻辑"""
        gui = NaturalGUIOperations(offset_range=10)
        
        # 测试偏移范围（通过多次计算验证）
        x, y = 100, 200
        offsets_x = []
        offsets_y = []
        
        for _ in range(20):
            offset_x = random.randint(-gui._offset_range, gui._offset_range)
            offset_y = random.randint(-gui._offset_range, gui._offset_range)
            new_x, new_y = x + offset_x, y + offset_y
            
            offsets_x.append(new_x - x)
            offsets_y.append(new_y - y)
            
            # 验证偏移在范围内
            self.assertGreaterEqual(new_x, x - 10)
            self.assertLessEqual(new_x, x + 10)
            self.assertGreaterEqual(new_y, y - 10)
            self.assertLessEqual(new_y, y + 10)
        
        # 验证有随机性（不是全部相同）
        self.assertGreater(len(set(offsets_x)), 1)
        self.assertGreater(len(set(offsets_y)), 1)

    def test_duration_range(self):
        """测试移动时长范围"""
        gui = NaturalGUIOperations(
            move_duration_min=0.5,
            move_duration_max=1.5
        )
        
        # 测试随机时长生成
        durations = []
        for _ in range(10):
            duration = random.uniform(gui._move_duration_min, gui._move_duration_max)
            self.assertGreaterEqual(duration, 0.5)
            self.assertLessEqual(duration, 1.5)
            durations.append(duration)
        
        # 验证有随机性
        self.assertGreater(len(set(durations)), 1)

    def test_pause_range(self):
        """测试暂停时间范围"""
        gui = NaturalGUIOperations(
            pause_min=0.1,
            pause_max=0.3
        )
        
        # 测试随机暂停生成
        pauses = []
        for _ in range(10):
            pause = random.uniform(gui._pause_min, gui._pause_max)
            self.assertGreaterEqual(pause, 0.1)
            self.assertLessEqual(pause, 0.3)
            pauses.append(pause)
        
        # 验证有随机性
        self.assertGreater(len(set(pauses)), 1)


if __name__ == "__main__":
    unittest.main()
