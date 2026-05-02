#!/usr/bin/env python3
"""
Windows GUI 操作实现 — 适配 BaseGUIOperations 接口

封装现有的 gui_operations.py 中的功能，
保持与原始代码兼容，不修改现有实现。
"""

import logging
from typing import Optional

from .base import BaseGUIOperations

try:
    from ..gui_operations import GUIOperationsMixin
except ImportError:
    from gui_operations import GUIOperationsMixin

logger = logging.getLogger(__name__)


class WinGUIOperations(BaseGUIOperations, GUIOperationsMixin):
    """Windows 平台的 GUI 操作实现。

    通过 Mixin 继承复用现有的 GUIOperationsMixin。
    作为适配器，将现有接口映射到 BaseGUIOperations 的抽象接口。
    """

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)

    def search_contact(self, contact_name: str) -> bool:
        return self._search_contact_nt(contact_name)

    def send_text(self, message: str) -> bool:
        return self._send_text_nt(message)

    def click_input_box(self) -> bool:
        return self._find_and_click_input_box()

    def set_clipboard(self, text: str) -> Optional[str]:
        return self._set_clipboard_and_paste(text)

    def restore_clipboard(self, original_data: Optional[str]) -> None:
        self._restore_clipboard(original_data)
