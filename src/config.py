#!/usr/bin/env python3
"""
配置管理模块
从 config.json 加载配置，缺失项使用默认值，配置文件不存在时创建模板。
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 默认配置值
DEFAULTS: Dict[str, Any] = {
    "http_port": 8080,
    "poll_interval": 5,
    "monitored_groups": [],
    "bot_name": "",
    "ai_base_url": "",
    "ai_api_key": "",
    "ai_model": "gpt-3.5-turbo",
    "system_prompt": "",
    "max_reply_chars": 1000,
    "ai_timeout": 30,
    "rate_limit_per_minute": 10,
}

# 配置文件默认路径（项目根目录下）
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


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
    def poll_interval(self) -> int:
        return int(self._data.get("poll_interval", DEFAULTS["poll_interval"]))

    @property
    def monitored_groups(self) -> List[str]:
        return list(self._data.get("monitored_groups", DEFAULTS["monitored_groups"]))

    @property
    def bot_name(self) -> str:
        return str(self._data.get("bot_name", DEFAULTS["bot_name"]))

    @property
    def ai_base_url(self) -> str:
        return str(self._data.get("ai_base_url", DEFAULTS["ai_base_url"]))

    @property
    def ai_api_key(self) -> str:
        return str(self._data.get("ai_api_key", DEFAULTS["ai_api_key"]))

    @property
    def ai_model(self) -> str:
        return str(self._data.get("ai_model", DEFAULTS["ai_model"]))

    @property
    def system_prompt(self) -> str:
        return str(self._data.get("system_prompt", DEFAULTS["system_prompt"]))

    @property
    def max_reply_chars(self) -> int:
        return int(self._data.get("max_reply_chars", DEFAULTS["max_reply_chars"]))

    @property
    def ai_timeout(self) -> int:
        return int(self._data.get("ai_timeout", DEFAULTS["ai_timeout"]))

    @property
    def rate_limit_per_minute(self) -> int:
        return int(self._data.get("rate_limit_per_minute", DEFAULTS["rate_limit_per_minute"]))

    # ------------------------------------------------------------------
    # 序列化 / 反序列化
    # ------------------------------------------------------------------
    def to_dict(self, mask_secrets: bool = False) -> Dict[str, Any]:
        """返回配置字典。mask_secrets=True 时对 api_key 脱敏。"""
        data = dict(self._data)
        if mask_secrets and data.get("ai_api_key"):
            key = data["ai_api_key"]
            if len(key) > 8:
                data["ai_api_key"] = f"{key[:3]}****{key[-4:]}"
            else:
                data["ai_api_key"] = "****"
        return data

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
        """创建包含默认值的 config.json 模板文件。"""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(DEFAULTS, f, ensure_ascii=False, indent=2)
            logger.info(f"已创建配置模板: {self._path}")
        except Exception as e:
            logger.error(f"创建配置模板失败: {e}")
