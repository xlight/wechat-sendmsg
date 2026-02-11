#!/usr/bin/env python3
"""
工作时间控制器
限制服务运行时段和每日运行时长，避免 24/7 不间断运行。
"""

from datetime import datetime
import logging


class WorkTimeController:
    """工作时间控制器（限制运行时段和每日运行时长）。"""
    
    def __init__(self, work_hours_start=9, work_hours_end=22, 
                 work_days=None, max_daily_runtime_hours=8.0):
        """初始化工作时间控制器。
        
        Args:
            work_hours_start: 工作时段开始小时（0-23，默认 9）
            work_hours_end: 工作时段结束小时（0-23，默认 22）
            work_days: 工作日列表（0=周一，6=周日，默认 [0,1,2,3,4] 即周一到周五）
            max_daily_runtime_hours: 每日最大运行时长（小时，默认 8.0）
        """
        self._work_start = work_hours_start
        self._work_end = work_hours_end
        self._work_days = work_days if work_days is not None else [0, 1, 2, 3, 4]
        self._max_daily_seconds = max_daily_runtime_hours * 3600
        
        # 记录启动时间和当前日期
        self._start_time = datetime.now()
        self._current_date = self._start_time.date()
        self.logger = logging.getLogger(__name__)
    
    def is_work_time(self) -> bool:
        """检查当前是否在工作时间内。
        
        Returns:
            True 如果在工作时间内，False 否则
        """
        now = datetime.now()
        
        # 检查星期几
        if now.weekday() not in self._work_days:
            self.logger.info(f"当前是非工作日（周{now.weekday()}）")
            return False
        
        # 检查小时范围
        if not (self._work_start <= now.hour < self._work_end):
            self.logger.info(f"当前不在工作时段（{now.hour}点，工作时段 {self._work_start}-{self._work_end}）")
            return False
        
        return True
    
    def should_continue_running(self) -> bool:
        """检查是否应继续运行（基于每日运行时长限制）。
        
        Returns:
            True 如果未达到每日限制，False 如果已达到限制
        """
        self._reset_if_new_day()
        runtime = self.get_runtime()
        
        if runtime >= self._max_daily_seconds:
            self.logger.warning(
                f"达到每日运行时长限制: {runtime/3600:.2f}/{self._max_daily_seconds/3600:.2f}小时"
            )
            return False
        
        return True
    
    def get_runtime(self) -> float:
        """获取当前累计运行时长（秒）。
        
        Returns:
            从启动到当前的累计时长（秒）
        """
        return (datetime.now() - self._start_time).total_seconds()
    
    def _reset_if_new_day(self):
        """日期变化时重置运行时长统计。"""
        now = datetime.now()
        if now.date() != self._current_date:
            self.logger.info(f"日期变化，重置运行时长统计（{self._current_date} -> {now.date()}）")
            self._start_time = now
            self._current_date = now.date()
