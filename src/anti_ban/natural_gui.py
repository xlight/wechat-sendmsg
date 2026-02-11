#!/usr/bin/env python3
"""
自然 GUI 操作工具
提供随机位置偏移点击、缓慢鼠标移动、安全剪贴板操作等自然化 GUI 操作功能。
"""

import random
import time
import logging

# 延迟导入 GUI 库，避免测试时导入失败
def _get_pyautogui():
    """懒加载 pyautogui"""
    import pyautogui
    return pyautogui

def _get_pyperclip():
    """懒加载 pyperclip"""
    import pyperclip
    return pyperclip


class NaturalGUIOperations:
    """自然 GUI 操作工具（随机位置偏移、缓慢移动、安全剪贴板）。"""
    
    def __init__(self, offset_range=3, move_duration_min=0.1, move_duration_max=0.3,
                 pause_min=0.05, pause_max=0.15):
        """初始化自然 GUI 操作工具。
        
        Args:
            offset_range: 随机位置偏移范围（像素，默认 ±3）
            move_duration_min: 鼠标移动最小时长（秒，默认 0.1）
            move_duration_max: 鼠标移动最大时长（秒，默认 0.3）
            pause_min: 随机停顿最小时长（秒，默认 0.05）
            pause_max: 随机停顿最大时长（秒，默认 0.15）
        """
        self._offset_range = offset_range
        self._move_duration_min = move_duration_min
        self._move_duration_max = move_duration_max
        self._pause_min = pause_min
        self._pause_max = pause_max
        self.logger = logging.getLogger(__name__)
    
    def click_with_offset(self, x: int, y: int, offset_range: int = None) -> tuple:
        """在指定坐标添加随机偏移后执行点击。
        
        Args:
            x: 原始 x 坐标
            y: 原始 y 坐标
            offset_range: 偏移范围（像素，None 使用默认值）
            
        Returns:
            实际点击的坐标 (new_x, new_y)
        """
        offset_range = offset_range or self._offset_range
        offset_x = random.randint(-offset_range, offset_range)
        offset_y = random.randint(-offset_range, offset_range)
        new_x, new_y = x + offset_x, y + offset_y
        self.logger.debug(f"点击偏移: ({x},{y}) -> ({new_x},{new_y})")
        _get_pyautogui().click(new_x, new_y)
        return (new_x, new_y)
    
    def move_with_duration(self, x: int, y: int, duration: float):
        """使用指定时长缓慢移动鼠标到目标位置。
        
        Args:
            x: 目标 x 坐标
            y: 目标 y 坐标
            duration: 移动时长（秒）
        """
        _get_pyautogui().moveTo(x, y, duration=duration)
    
    def move_with_random_duration(self, x: int, y: int, min_duration: float = None, 
                                   max_duration: float = None):
        """使用随机时长缓慢移动鼠标到目标位置。
        
        Args:
            x: 目标 x 坐标
            y: 目标 y 坐标
            min_duration: 最小移动时长（秒，None 使用默认值）
            max_duration: 最大移动时长（秒，None 使用默认值）
        """
        min_duration = min_duration or self._move_duration_min
        max_duration = max_duration or self._move_duration_max
        duration = random.uniform(min_duration, max_duration)
        self.logger.debug(f"随机移动鼠标，耗时 {duration:.2f}s")
        self.move_with_duration(x, y, duration)
    
    def natural_click(self, x: int, y: int, offset_range: int = None,
                      min_duration: float = None, max_duration: float = None):
        """执行自然化点击（组合所有特性）。
        
        包含：随机位置偏移 + 缓慢移动 + 随机停顿 + 点击 + 随机停顿
        
        Args:
            x: 目标 x 坐标
            y: 目标 y 坐标
            offset_range: 偏移范围（像素，None 使用默认值）
            min_duration: 最小移动时长（秒，None 使用默认值）
            max_duration: 最大移动时长（秒，None 使用默认值）
        """
        # 1. 计算随机偏移位置
        offset_range = offset_range or self._offset_range
        offset_x = random.randint(-offset_range, offset_range)
        offset_y = random.randint(-offset_range, offset_range)
        target_x, target_y = x + offset_x, y + offset_y
        
        # 2. 缓慢移动到偏移位置
        self.move_with_random_duration(target_x, target_y, min_duration, max_duration)
        
        # 3. 随机停顿
        self._random_pause()
        
        # 4. 执行点击
        _get_pyautogui().click(target_x, target_y)
        
        # 5. 点击后随机停顿
        self._random_pause()
        
        self.logger.debug(f"自然点击: ({x},{y}) -> ({target_x},{target_y})")
    
    def paste_text_safe(self, text: str):
        """安全剪贴板粘贴（备份和恢复剪贴板）。
        
        Args:
            text: 要粘贴的文本
        """
        pyperclip = _get_pyperclip()
        pyautogui = _get_pyautogui()
        
        # 1. 备份剪贴板
        old_clipboard = pyperclip.paste()
        
        try:
            # 2. 设置新内容
            pyperclip.copy(text)
            time.sleep(0.1)  # 等待剪贴板更新
            
            # 3. 随机选择粘贴快捷键
            if random.random() < 0.5:
                pyautogui.hotkey('ctrl', 'v')
                self.logger.debug("使用 Ctrl+V 粘贴")
            else:
                pyautogui.hotkey('shift', 'insert')
                self.logger.debug("使用 Shift+Insert 粘贴")
            
            # 4. 延迟恢复剪贴板
            time.sleep(random.uniform(0.5, 1.0))
            pyperclip.copy(old_clipboard)
        except Exception as e:
            self.logger.error(f"安全粘贴失败: {e}")
            # 尝试恢复剪贴板
            try:
                pyperclip.copy(old_clipboard)
            except:
                pass
    
    def _random_pause(self, min_sec: float = None, max_sec: float = None):
        """内部随机停顿方法。
        
        Args:
            min_sec: 最小停顿时长（秒，None 使用默认值）
            max_sec: 最大停顿时长（秒，None 使用默认值）
        """
        min_sec = min_sec or self._pause_min
        max_sec = max_sec or self._pause_max
        pause = random.uniform(min_sec, max_sec)
        time.sleep(pause)
