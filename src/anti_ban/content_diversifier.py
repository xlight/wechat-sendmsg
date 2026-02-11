#!/usr/bin/env python3
"""
内容多样化处理器
提供随机前后缀添加、智能跳过消息等内容多样化功能。
"""

import random
import logging
from typing import List, Optional


class ContentDiversifier:
    """内容多样化处理器（添加随机前后缀、智能跳过消息）。"""
    
    # 默认前缀列表
    DEFAULT_PREFIXES = ["嗯", "好的", "明白", "收到", "了解", "好", "OK", "嗯嗯"]
    
    # 默认 emoji 后缀列表
    DEFAULT_SUFFIXES = ["😊", "👌", "💪", "🙏", "😄", "👍"]
    
    # 问候语关键词列表
    GREETING_KEYWORDS = ["你好", "hi", "hello", "在吗", "在不", "哈喽", "hey"]
    
    def __init__(self, prefix_probability=0.1, suffix_probability=0.05, skip_probability=0.2):
        """初始化内容多样化处理器。
        
        Args:
            prefix_probability: 添加前缀的概率（0.0-1.0，默认 0.1）
            suffix_probability: 添加后缀的概率（0.0-1.0，默认 0.05）
            skip_probability: 跳过消息的概率（0.0-1.0，默认 0.2）
        """
        self._prefix_prob = prefix_probability
        self._suffix_prob = suffix_probability
        self._skip_prob = skip_probability
        self.logger = logging.getLogger(__name__)
    
    def add_prefix(self, text: str, probability: Optional[float] = None, 
                   prefixes: Optional[List[str]] = None) -> str:
        """以指定概率为文本添加随机前缀。
        
        Args:
            text: 原始文本
            probability: 添加前缀的概率（None 使用默认值）
            prefixes: 自定义前缀列表（None 使用默认列表）
            
        Returns:
            添加前缀后的文本（或原始文本）
        """
        probability = probability if probability is not None else self._prefix_prob
        if random.random() < probability:
            prefix_list = prefixes or self.DEFAULT_PREFIXES
            prefix = random.choice(prefix_list)
            return f"{prefix}，{text}"
        return text
    
    def add_suffix(self, text: str, probability: Optional[float] = None, 
                   suffixes: Optional[List[str]] = None) -> str:
        """以指定概率为文本添加随机后缀。
        
        Args:
            text: 原始文本
            probability: 添加后缀的概率（None 使用默认值）
            suffixes: 自定义后缀列表（None 使用默认列表）
            
        Returns:
            添加后缀后的文本（或原始文本）
        """
        probability = probability if probability is not None else self._suffix_prob
        if random.random() < probability:
            suffix_list = suffixes or self.DEFAULT_SUFFIXES
            suffix = random.choice(suffix_list)
            return f"{text} {suffix}"
        return text
    
    def should_skip(self, message: str, skip_probability: Optional[float] = None) -> bool:
        """根据消息内容和概率决定是否跳过消息。
        
        对于问候语消息，跳过概率提高到 50%。
        
        Args:
            message: 消息内容
            skip_probability: 跳过概率（None 使用默认值）
            
        Returns:
            True 如果应该跳过，False 如果应该处理
        """
        skip_prob = skip_probability if skip_probability is not None else self._skip_prob
        
        # 检查是否是问候语，问候语跳过概率更高
        message_lower = message.lower()
        is_greeting = any(keyword in message_lower for keyword in self.GREETING_KEYWORDS)
        
        if is_greeting:
            skip_prob = 0.5  # 问候语 50% 跳过
            if random.random() < skip_prob:
                self.logger.info(f"随机跳过问候语消息: {message[:20]}...")
                return True
        else:
            if random.random() < skip_prob:
                self.logger.info(f"随机跳过普通消息: {message[:20]}...")
                return True
        
        return False
    
    def diversify(self, text: str, prefix_prob: Optional[float] = None, 
                  suffix_prob: Optional[float] = None) -> str:
        """对文本应用所有多样化处理（前缀 + 后缀）。
        
        Args:
            text: 原始文本
            prefix_prob: 添加前缀的概率（None 使用默认值）
            suffix_prob: 添加后缀的概率（None 使用默认值）
            
        Returns:
            多样化处理后的文本
        """
        text = self.add_prefix(text, prefix_prob)
        text = self.add_suffix(text, suffix_prob)
        return text
