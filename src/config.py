#!/usr/bin/env python3
"""
配置管理模块
从 data/config.json 加载配置，缺失项使用默认值，配置文件不存在时创建模板。
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

try:
    from .paths import get_config_path, get_db_path
except ImportError:
    from paths import get_config_path, get_db_path

logger = logging.getLogger(__name__)

# 默认配置值
DEFAULTS: Dict[str, Any] = {
    "http_port": 8080,
    # 防封号配置 - 速率限制
    "rate_limit_per_minute": 10,
    "rate_limit_per_hour": 20,
    "rate_limit_per_day": 100,
    # 防封号配置 - 人类行为模拟
    "min_think_time": 3.0,
    "max_think_time": 15.0,
    "min_random_delay": 1.0,
    "max_random_delay": 3.0,
    # 防封号配置 - 工作时间控制
    "work_hours_start": 9,
    "work_hours_end": 22,
    "work_days": [0, 1, 2, 3, 4],  # 周一到周五
    "max_daily_runtime_hours": 8.0,
    # 防封号配置 - 内容多样化
    "prefix_probability": 0.1,
    "suffix_probability": 0.05,
    "random_skip_probability": 0.2,
    # 微信快捷键配置
    "wechat_hotkey": "ctrl+alt+w",  # 激活微信窗口的快捷键
    # Windows: 需在微信设置中配置快捷键
    # macOS: 可用系统快捷键（如 Cmd+Shift+W），或留空使用 API 方式
    # 防封号配置 - GUI 操作
    "gui_offset_range": 3,
    "gui_move_duration_min": 0.1,
    "gui_move_duration_max": 0.3,
    "gui_pause_min": 0.05,
    "gui_pause_max": 0.15,
    # 消息队列配置
    "queue_db_path": "",  # 空字符串表示使用 paths 模块计算的默认路径
    "queue_max_retries": 3,
    "queue_poll_interval": 1.0,
    # macOS 微信配置
    "mac_wechat_hotkey": "command+shift+w",  # macOS 快捷键（可留空）
    "mac_send_shortcut": "command+enter",    # macOS 发送快捷键（默认 Cmd+Enter）
}

# 配置文件默认路径（通过 paths 模块计算）
_CONFIG_FILE = get_config_path()


class Config:
    """应用配置，支持从 JSON 文件加载和运行时更新。"""

    def __init__(self, config_path: Optional[str] = None):
        self._path: str = config_path or _CONFIG_FILE
        self._data: Dict[str, Any] = dict(DEFAULTS)
        self._load()

    # ------------------------------------------------------------------
    # 属性访问
    # ------------------------------------------------------------------
    @property
    def http_port(self) -> int:
        return int(self._data.get("http_port", DEFAULTS["http_port"]))

    @property
    def rate_limit_per_minute(self) -> int:
        return int(self._data.get("rate_limit_per_minute", DEFAULTS["rate_limit_per_minute"]))

    @property
    def rate_limit_per_hour(self) -> int:
        return int(self._data.get("rate_limit_per_hour", DEFAULTS["rate_limit_per_hour"]))

    @property
    def rate_limit_per_day(self) -> int:
        return int(self._data.get("rate_limit_per_day", DEFAULTS["rate_limit_per_day"]))

    @property
    def min_think_time(self) -> float:
        return float(self._data.get("min_think_time", DEFAULTS["min_think_time"]))

    @property
    def max_think_time(self) -> float:
        return float(self._data.get("max_think_time", DEFAULTS["max_think_time"]))

    @property
    def min_random_delay(self) -> float:
        return float(self._data.get("min_random_delay", DEFAULTS["min_random_delay"]))

    @property
    def max_random_delay(self) -> float:
        return float(self._data.get("max_random_delay", DEFAULTS["max_random_delay"]))

    @property
    def work_hours_start(self) -> int:
        return int(self._data.get("work_hours_start", DEFAULTS["work_hours_start"]))

    @property
    def work_hours_end(self) -> int:
        return int(self._data.get("work_hours_end", DEFAULTS["work_hours_end"]))

    @property
    def work_days(self) -> List[int]:
        return list(self._data.get("work_days", DEFAULTS["work_days"]))

    @property
    def max_daily_runtime_hours(self) -> float:
        return float(self._data.get("max_daily_runtime_hours", DEFAULTS["max_daily_runtime_hours"]))

    @property
    def prefix_probability(self) -> float:
        return float(self._data.get("prefix_probability", DEFAULTS["prefix_probability"]))

    @property
    def suffix_probability(self) -> float:
        return float(self._data.get("suffix_probability", DEFAULTS["suffix_probability"]))

    @property
    def random_skip_probability(self) -> float:
        return float(self._data.get("random_skip_probability", DEFAULTS["random_skip_probability"]))

    @property
    def gui_offset_range(self) -> int:
        return int(self._data.get("gui_offset_range", DEFAULTS["gui_offset_range"]))

    @property
    def gui_move_duration_min(self) -> float:
        return float(self._data.get("gui_move_duration_min", DEFAULTS["gui_move_duration_min"]))

    @property
    def gui_move_duration_max(self) -> float:
        return float(self._data.get("gui_move_duration_max", DEFAULTS["gui_move_duration_max"]))

    @property
    def gui_pause_min(self) -> float:
        return float(self._data.get("gui_pause_min", DEFAULTS["gui_pause_min"]))

    @property
    def gui_pause_max(self) -> float:
        return float(self._data.get("gui_pause_max", DEFAULTS["gui_pause_max"]))

    @property
    def wechat_hotkey(self) -> str:
        """激活微信窗口的快捷键，格式如 'ctrl+alt+w'。"""
        return str(self._data.get("wechat_hotkey", DEFAULTS["wechat_hotkey"]))

    @property
    def queue_db_path(self) -> str:
        """消息队列 SQLite 数据库文件路径。"""
        path = str(self._data.get("queue_db_path", ""))
        if not path:
            return get_db_path()
        return path

    @property
    def queue_max_retries(self) -> int:
        """消息发送失败后最大重试次数。"""
        return int(self._data.get("queue_max_retries", DEFAULTS["queue_max_retries"]))

    @property
    def queue_poll_interval(self) -> float:
        """队列 Worker 轮询间隔（秒）。"""
        return float(self._data.get("queue_poll_interval", DEFAULTS["queue_poll_interval"]))

    @property
    def mac_wechat_hotkey(self) -> str:
        """macOS 激活微信窗口的快捷键。"""
        return str(self._data.get("mac_wechat_hotkey", DEFAULTS["mac_wechat_hotkey"]))

    @property
    def mac_send_shortcut(self) -> str:
        """macOS 发送消息的快捷键（默认 Cmd+Enter）。"""
        return str(self._data.get("mac_send_shortcut", DEFAULTS["mac_send_shortcut"]))

    # ------------------------------------------------------------------
    # 序列化 / 反序列化
    # ------------------------------------------------------------------
    def to_dict(self, mask_secrets: bool = False) -> Dict[str, Any]:
        """返回配置字典。"""
        return dict(self._data)

    def update(self, patch: Dict[str, Any]) -> None:
        """运行时更新配置（不写入文件）。"""
        for key, value in patch.items():
            if key in DEFAULTS:
                self._data[key] = value
            else:
                logger.warning(f"忽略未知配置项: {key}")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _load(self) -> None:
        """从文件加载配置；文件不存在时创建模板。"""
        if not os.path.isfile(self._path):
            logger.info(f"配置文件不存在，正在创建模板: {self._path}")
            self._create_template()
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            # 合并：用户值覆盖默认值
            for key in DEFAULTS:
                if key in user_data:
                    self._data[key] = user_data[key]
            logger.info(f"已加载配置文件: {self._path}")
        except json.JSONDecodeError as e:
            logger.error(f"配置文件 JSON 解析失败: {e}，将使用默认值")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，将使用默认值")

    def _create_template(self) -> None:
        """创建包含默认值的 data/config.json 模板文件。"""
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(DEFAULTS, f, ensure_ascii=False, indent=2)
            logger.info(f"已创建配置模板: {self._path}")
        except Exception as e:
            logger.error(f"创建配置模板失败: {e}")
