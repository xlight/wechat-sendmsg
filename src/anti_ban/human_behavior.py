#!/usr/bin/env python3
"""
人类行为模拟器
提供随机延迟、思考时间、打字时间计算等人类行为模拟功能。
"""

import random
import asyncio
import time
import logging


class HumanBehaviorSimulator:
    """人类行为模拟工具（随机延迟、思考时间、打字时间）。"""
    
    def __init__(self, min_think_time=3.0, max_think_time=15.0):
        """初始化人类行为模拟器。
        
        Args:
            min_think_time: 最小思考时间（秒，默认 3.0）
            max_think_time: 最大思考时间（秒，默认 15.0）
        """
        self._min_think = min_think_time
        self._max_think = max_think_time
        self.logger = logging.getLogger(__name__)
    
    def random_delay(self, min_sec=1.0, max_sec=3.0) -> float:
        """生成随机延迟时间。
        
        Args:
            min_sec: 最小延迟（秒，默认 1.0）
            max_sec: 最大延迟（秒，默认 3.0）
            
        Returns:
            随机延迟时间（秒）
        """
        return random.uniform(min_sec, max_sec)
    
    def think_time(self, min_sec=None, max_sec=None) -> float:
        """计算思考时间（模拟人类收到消息后的思考过程）。
        
        Args:
            min_sec: 最小思考时间（秒，默认使用构造函数设置的值）
            max_sec: 最大思考时间（秒，默认使用构造函数设置的值）
            
        Returns:
            随机思考时间（秒）
        """
        min_sec = min_sec if min_sec is not None else self._min_think
        max_sec = max_sec if max_sec is not None else self._max_think
        return self.random_delay(min_sec, max_sec)
    
    def typing_time(self, text: str, chars_per_sec=10.0, max_time=10.0) -> float:
        """根据文本长度计算打字时间（添加 ±50% 随机波动）。
        
        Args:
            text: 要输入的文本
            chars_per_sec: 打字速度（字符/秒，默认 10，即每字 0.1 秒）
            max_time: 最大打字时间限制（秒，默认 10）
            
        Returns:
            计算的打字时间（秒）
        """
        base_time = len(text) / chars_per_sec
        # 添加 ±50% 随机波动
        jitter = random.uniform(-0.5, 0.5)
        typing_time = base_time * (1 + jitter)
        return min(typing_time, max_time)
    
    def sleep_random(self, min_sec=1.0, max_sec=3.0):
        """同步随机延迟（阻塞当前线程）。
        
        Args:
            min_sec: 最小延迟（秒，默认 1.0）
            max_sec: 最大延迟（秒，默认 3.0）
        """
        delay = self.random_delay(min_sec, max_sec)
        self.logger.debug(f"同步延迟 {delay:.2f} 秒")
        time.sleep(delay)
    
    async def async_sleep_random(self, min_sec=1.0, max_sec=3.0):
        """异步随机延迟（不阻塞事件循环）。
        
        Args:
            min_sec: 最小延迟（秒，默认 1.0）
            max_sec: 最大延迟（秒，默认 3.0）
        """
        delay = self.random_delay(min_sec, max_sec)
        self.logger.debug(f"异步延迟 {delay:.2f} 秒")
        await asyncio.sleep(delay)
