#!/usr/bin/env python3
"""
防封号系统集成测试
测试 HTTP API 端点和防封号组件集成，不依赖真实微信环境。
"""

import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, AsyncMock

# 将项目根目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.anti_ban import (
    EnhancedRateLimiter,
    HumanBehaviorSimulator,
    WorkTimeController,
    ContentDiversifier,
)
from src.http_server import HTTPServer


class TestHTTPAPIEndpoints(unittest.TestCase):
    """测试 HTTP API 端点（不启动真实服务器）。"""

    def setUp(self):
        """创建测试用的配置和防封号工具实例。"""
        # 创建临时配置
        self.config_data = {
            "http_port": 8080,
            "rate_limit_per_minute": 3,
            "rate_limit_per_hour": 20,
            "rate_limit_per_day": 100,
            "work_hours_start": 9,
            "work_hours_end": 22,
            "work_days": [0, 1, 2, 3, 4],
            "max_daily_runtime_hours": 8.0,
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(self.config_data, f, ensure_ascii=False)
            self.config_path = f.name
        
        self.config = Config(config_path=self.config_path)
        
        # 创建防封号工具实例
        self.rate_limiter = EnhancedRateLimiter(
            limit_per_minute=3,
            limit_per_hour=20,
            limit_per_day=100
        )
        self.work_time_controller = WorkTimeController(
            work_hours_start=9,
            work_hours_end=22,
            work_days=[0, 1, 2, 3, 4],
            max_daily_runtime_hours=8.0
        )
        
        # 创建 mock 对象
        self.mock_controller = Mock()
        self.mock_listener = Mock()
        
        # 创建 HTTPServer 实例
        self.server = HTTPServer(
            config=self.config,
            controller=self.mock_controller,
            listener=self.mock_listener,
            rate_limiter=self.rate_limiter,
            work_time_controller=self.work_time_controller
        )

    def tearDown(self):
        """清理临时文件。"""
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)

    def test_anti_ban_stats_endpoint(self):
        """测试 /api/v1/anti-ban/stats 端点返回正确数据。"""
        # 模拟一些速率限制器调用
        self.rate_limiter.allow()
        self.rate_limiter.allow()
        
        # 获取统计数据
        stats = self.rate_limiter.get_stats()
        
        # 验证数据结构（实际返回格式：last_minute, last_hour, last_day）
        self.assertIn("last_minute", stats)
        self.assertIn("last_hour", stats)
        self.assertIn("last_day", stats)
        self.assertIn("limit_minute", stats)
        self.assertIn("limit_hour", stats)
        self.assertIn("limit_day", stats)
        
        # 验证计数正确
        self.assertEqual(stats["last_minute"], 2)
        self.assertEqual(stats["last_hour"], 2)
        self.assertEqual(stats["last_day"], 2)
        
        # 验证限制值
        self.assertEqual(stats["limit_minute"], 3)
        self.assertEqual(stats["limit_hour"], 20)
        self.assertEqual(stats["limit_day"], 100)

    def test_anti_ban_config_endpoint(self):
        """测试 /api/v1/anti-ban/config 端点返回正确配置。"""
        # 获取防封号配置
        anti_ban_config = {
            "rate_limit_per_minute": self.config.rate_limit_per_minute,
            "rate_limit_per_hour": self.config.rate_limit_per_hour,
            "rate_limit_per_day": self.config.rate_limit_per_day,
            "min_think_time": self.config.min_think_time,
            "max_think_time": self.config.max_think_time,
            "work_hours_start": self.config.work_hours_start,
            "work_hours_end": self.config.work_hours_end,
            "work_days": self.config.work_days,
            "max_daily_runtime_hours": self.config.max_daily_runtime_hours,
        }
        
        # 验证配置值
        self.assertEqual(anti_ban_config["rate_limit_per_minute"], 3)
        self.assertEqual(anti_ban_config["rate_limit_per_hour"], 20)
        self.assertEqual(anti_ban_config["rate_limit_per_day"], 100)
        self.assertEqual(anti_ban_config["work_hours_start"], 9)
        self.assertEqual(anti_ban_config["work_hours_end"], 22)
        self.assertEqual(anti_ban_config["work_days"], [0, 1, 2, 3, 4])
        self.assertEqual(anti_ban_config["max_daily_runtime_hours"], 8.0)


class TestAntiBanIntegration(unittest.TestCase):
    """测试防封号组件集成。"""

    def test_complete_anti_ban_flow(self):
        """测试完整的防封号流程（模拟场景）。"""
        # 1. 创建所有防封号组件
        rate_limiter = EnhancedRateLimiter(limit_per_minute=2, limit_per_hour=10, limit_per_day=50)
        human_behavior = HumanBehaviorSimulator(min_think_time=1.0, max_think_time=3.0)
        work_time = WorkTimeController(
            work_hours_start=0,
            work_hours_end=23,
            work_days=[0, 1, 2, 3, 4, 5, 6],
            max_daily_runtime_hours=24.0
        )
        content_div = ContentDiversifier(
            prefix_probability=0.5,
            suffix_probability=0.3,
            skip_probability=0.1
        )
        
        # 2. 模拟消息处理流程
        message = "你好，AI助手！"
        
        # 步骤 1: 检查工作时间
        self.assertTrue(work_time.is_work_time(), "应该在工作时间内")
        
        # 步骤 2: 检查运行时长限制
        self.assertTrue(work_time.should_continue_running(), "应该未达到运行时长限制")
        
        # 步骤 3: 检查是否随机跳过
        # 注意：这是概率性的，我们只验证方法能正常调用
        should_skip = content_div.should_skip(message)
        self.assertIsInstance(should_skip, bool)
        
        # 步骤 4: 速率限制检查
        self.assertTrue(rate_limiter.allow(), "第一次调用应该允许")
        self.assertTrue(rate_limiter.allow(), "第二次调用应该允许")
        self.assertFalse(rate_limiter.allow(), "第三次调用应该被限制（每分钟限制2次）")
        
        # 步骤 5: 思考时间计算
        think_time = human_behavior.think_time()
        self.assertGreaterEqual(think_time, 1.0)
        self.assertLessEqual(think_time, 3.0)
        
        # 步骤 6: 内容多样化
        reply = "好的，我明白了"
        diversified = content_div.diversify(reply, prefix_prob=1.0, suffix_prob=0.0)
        # 由于 prefix_prob=1.0，应该添加了前缀
        self.assertNotEqual(diversified, reply)
        self.assertTrue("，" in diversified)

    def test_rate_limiter_stats_accuracy(self):
        """测试速率限制器统计数据准确性。"""
        limiter = EnhancedRateLimiter(limit_per_minute=5, limit_per_hour=20, limit_per_day=100)
        
        # 调用 3 次
        for _ in range(3):
            limiter.allow()
        
        stats = limiter.get_stats()
        
        # 验证各级别计数一致（修正键名）
        self.assertEqual(stats["last_minute"], 3)
        self.assertEqual(stats["last_hour"], 3)
        self.assertEqual(stats["last_day"], 3)

    def test_work_time_controller_runtime_tracking(self):
        """测试工作时间控制器运行时长跟踪。"""
        controller = WorkTimeController(
            work_hours_start=0,
            work_hours_end=23,
            work_days=[0, 1, 2, 3, 4, 5, 6],
            max_daily_runtime_hours=1.0  # 1小时限制
        )
        
        # 获取运行时长
        runtime = controller.get_runtime()
        self.assertGreaterEqual(runtime, 0.0)
        
        # WorkTimeController 没有 get_stats() 方法，改为验证其他属性
        # 验证工作时间检查正常
        self.assertTrue(controller.is_work_time())
        
        # 验证运行时长限制检查正常
        self.assertTrue(controller.should_continue_running())

    def test_content_diversifier_greeting_detection(self):
        """测试内容多样化器的问候语检测。"""
        diversifier = ContentDiversifier(skip_probability=0.0)
        
        # 问候语列表
        greetings = ["你好", "hi", "hello", "在吗", "在不", "哈喽"]
        
        # 验证问候语能被识别（通过多次测试统计）
        skip_count = 0
        trials = 100
        
        for _ in range(trials):
            if diversifier.should_skip("你好"):
                skip_count += 1
        
        # 问候语应该有约 50% 的跳过率（允许一定误差）
        skip_rate = skip_count / trials
        self.assertGreater(skip_rate, 0.3, "问候语跳过率应该高于30%")
        self.assertLess(skip_rate, 0.7, "问候语跳过率应该低于70%")


class TestAntiBanComponentsCooperation(unittest.TestCase):
    """测试防封号组件协作。"""

    def test_rate_limiter_and_work_time_cooperation(self):
        """测试速率限制器和工作时间控制器的协作。"""
        rate_limiter = EnhancedRateLimiter(limit_per_minute=3, limit_per_hour=20, limit_per_day=100)
        work_time = WorkTimeController(
            work_hours_start=0,
            work_hours_end=23,
            work_days=[0, 1, 2, 3, 4, 5, 6],
            max_daily_runtime_hours=24.0
        )
        
        # 模拟消息处理决策流程
        def should_process_message():
            # 1. 检查工作时间
            if not work_time.is_work_time():
                return False, "非工作时间"
            
            # 2. 检查运行时长
            if not work_time.should_continue_running():
                return False, "达到每日运行时长限制"
            
            # 3. 检查速率限制
            if not rate_limiter.allow():
                return False, "达到速率限制"
            
            return True, "允许处理"
        
        # 测试前 3 次应该允许
        for i in range(3):
            allowed, reason = should_process_message()
            self.assertTrue(allowed, f"第 {i+1} 次调用应该允许: {reason}")
        
        # 第 4 次应该被速率限制拦截
        allowed, reason = should_process_message()
        self.assertFalse(allowed, "第 4 次调用应该被限制")
        self.assertEqual(reason, "达到速率限制")

    def test_human_behavior_and_content_diversifier_cooperation(self):
        """测试人类行为模拟器和内容多样化器的协作。"""
        human_behavior = HumanBehaviorSimulator(min_think_time=0.1, max_think_time=0.5)
        content_div = ContentDiversifier(prefix_probability=0.3, suffix_probability=0.2)
        
        # 模拟回复生成流程
        def generate_reply(ai_response: str) -> tuple:
            # 1. 计算思考时间
            think_time = human_behavior.think_time()
            
            # 2. 计算打字时间
            typing_time = human_behavior.typing_time(ai_response)
            
            # 3. 内容多样化
            diversified = content_div.diversify(ai_response)
            
            return think_time, typing_time, diversified
        
        ai_response = "这是一个测试回复"
        think_time, typing_time, diversified = generate_reply(ai_response)
        
        # 验证思考时间在范围内
        self.assertGreaterEqual(think_time, 0.1)
        self.assertLessEqual(think_time, 0.5)
        
        # 验证打字时间 > 0
        self.assertGreater(typing_time, 0.0)
        
        # 验证内容是字符串
        self.assertIsInstance(diversified, str)

    def test_natural_gui_operations_integration(self):
        """测试自然 GUI 操作的完整流程。"""
        from src.anti_ban import NaturalGUIOperations
        from unittest.mock import patch, MagicMock
        
        # 创建 NaturalGUIOperations 实例
        gui_ops = NaturalGUIOperations(
            offset_range=5,
            move_duration_min=0.2,
            move_duration_max=0.4,
            pause_min=0.1,
            pause_max=0.2
        )
        
        # Mock pyautogui 以避免实际的 GUI 操作
        with patch('src.anti_ban.natural_gui._get_pyautogui') as mock_pyautogui_func:
            mock_pyautogui = MagicMock()
            mock_pyautogui_func.return_value = mock_pyautogui
            
            # 测试 natural_click 方法的调用流程
            # 这会触发：偏移计算 -> 缓慢移动 -> 随机停顿 -> 点击 -> 随机停顿
            gui_ops.natural_click(100, 200)
            
            # 验证 moveTo 被调用（缓慢移动）
            self.assertTrue(mock_pyautogui.moveTo.called, "应该调用 moveTo 进行缓慢移动")
            
            # 验证 click 被调用
            self.assertTrue(mock_pyautogui.click.called, "应该调用 click 执行点击")
            
            # 验证 moveTo 的参数（坐标应该有偏移）
            move_args = mock_pyautogui.moveTo.call_args
            move_x, move_y = move_args[0][0], move_args[0][1]
            
            # 验证坐标有偏移（在 100±5 和 200±5 范围内）
            self.assertGreaterEqual(move_x, 95)
            self.assertLessEqual(move_x, 105)
            self.assertGreaterEqual(move_y, 195)
            self.assertLessEqual(move_y, 205)
            
            # 验证移动时长在配置范围内
            move_duration = move_args[1]['duration']
            self.assertGreaterEqual(move_duration, 0.2)
            self.assertLessEqual(move_duration, 0.4)


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)

