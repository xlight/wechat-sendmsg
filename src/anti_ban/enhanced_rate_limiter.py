#!/usr/bin/env python3
"""
增强版多级速率限制器
提供每分钟、每小时、每日三级速率限制功能，使用滑动窗口算法。
"""

from collections import deque
import time
import logging


class EnhancedRateLimiter:
    """增强版多级速率限制器（分钟/小时/天三级限制）。"""
    
    def __init__(self, limit_per_minute=3, limit_per_hour=20, limit_per_day=100):
        """初始化速率限制器。
        
        Args:
            limit_per_minute: 每分钟最大调用次数（默认 3）
            limit_per_hour: 每小时最大调用次数（默认 20）
            limit_per_day: 每日最大调用次数（默认 100）
        """
        self._limit_minute = limit_per_minute
        self._limit_hour = limit_per_hour
        self._limit_day = limit_per_day
        
        # 使用 deque 存储时间戳（自动清理过期记录）
        self._timestamps_minute = deque()
        self._timestamps_hour = deque()
        self._timestamps_day = deque()
        
        self.logger = logging.getLogger(__name__)
    
    def allow(self) -> bool:
        """检查是否允许调用（滑动窗口算法）。
        
        Returns:
            True 如果允许调用，False 如果达到任一级别的限制
        """
        now = time.time()
        self._cleanup_old_records(now)
        
        # 检查三级限制
        if len(self._timestamps_minute) >= self._limit_minute:
            self.logger.warning(f"达到每分钟速率限制: {self._limit_minute}")
            return False
        if len(self._timestamps_hour) >= self._limit_hour:
            self.logger.warning(f"达到每小时速率限制: {self._limit_hour}")
            return False
        if len(self._timestamps_day) >= self._limit_day:
            self.logger.warning(f"达到每日速率限制: {self._limit_day}")
            return False
        
        # 记录时间戳
        self._timestamps_minute.append(now)
        self._timestamps_hour.append(now)
        self._timestamps_day.append(now)
        return True
    
    def _cleanup_old_records(self, now: float):
        """清理过期的时间戳记录。
        
        Args:
            now: 当前时间戳
        """
        # 清理 1 分钟前的记录
        while self._timestamps_minute and now - self._timestamps_minute[0] > 60:
            self._timestamps_minute.popleft()
        # 清理 1 小时前的记录
        while self._timestamps_hour and now - self._timestamps_hour[0] > 3600:
            self._timestamps_hour.popleft()
        # 清理 1 天前的记录
        while self._timestamps_day and now - self._timestamps_day[0] > 86400:
            self._timestamps_day.popleft()
    
    def get_stats(self) -> dict:
        """获取当前使用统计信息。
        
        Returns:
            包含各级别使用情况和限制值的字典
        """
        now = time.time()
        self._cleanup_old_records(now)
        return {
            "last_minute": len(self._timestamps_minute),
            "last_hour": len(self._timestamps_hour),
            "last_day": len(self._timestamps_day),
            "limit_minute": self._limit_minute,
            "limit_hour": self._limit_hour,
            "limit_day": self._limit_day,
        }
