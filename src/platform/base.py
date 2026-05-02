#!/usr/bin/env python3
"""
平台抽象基类 — 所有平台实现的统一接口

每个平台必须实现三个抽象类：
- WindowFinder:  窗口查找、激活、版本检测
- GUIOperations: 搜索联系人、发送消息、剪贴板操作
- TrayManager:   系统托盘/指示器管理（可选，非 GUI 模式可跳过）
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class WindowFinder(ABC):
    """窗口查找与激活的抽象接口。"""

    @abstractmethod
    def detect_wechat_version(self) -> Optional[str]:
        """检测微信版本号。

        Returns:
            版本号字符串如 "4.0.0.26"，失败返回 None
        """
        ...

    @abstractmethod
    def find_wechat_window(self) -> Optional[int]:
        """查找微信主窗口标识符。

        Returns:
            Windows 为 hwnd，macOS/Linux 为 PID 或 X11 WID，未找到返回 None
        """
        ...

    @abstractmethod
    def activate_window(self, window_id: int) -> bool:
        """激活微信窗口（从最小化/后台恢复并置前）。

        Args:
            window_id: 窗口标识符

        Returns:
            激活成功返回 True
        """
        ...

    @abstractmethod
    def restore_window(self) -> Optional[int]:
        """从系统托盘/Dock/通知区域恢复微信窗口。

        Returns:
            恢复后的窗口标识符，失败返回 None
        """
        ...

    @abstractmethod
    def is_wechat_available(self) -> bool:
        """检查微信是否正在运行。"""
        ...

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取微信当前状态信息（版本、窗口可用性等）。"""
        ...


class GUIOperations(ABC):
    """GUI 操作的抽象接口。"""

    @abstractmethod
    def search_contact(self, contact_name: str) -> bool:
        """搜索联系人/群聊并打开聊天窗口。

        Args:
            contact_name: 联系人名称

        Returns:
            成功进入聊天窗口返回 True
        """
        ...

    @abstractmethod
    def send_text(self, message: str) -> bool:
        """发送文本消息（假设已进入聊天窗口）。

        Args:
            message: 消息内容

        Returns:
            发送成功返回 True
        """
        ...

    @abstractmethod
    def click_input_box(self) -> bool:
        """点击聊天输入框以获取焦点。

        Returns:
            成功返回 True
        """
        ...

    @abstractmethod
    def set_clipboard(self, text: str) -> Optional[str]:
        """设置剪贴板内容并粘贴到当前焦点。

        Args:
            text: 要设置并粘贴的文本

        Returns:
            原剪贴板内容（用于恢复），失败返回 None
        """
        ...

    @abstractmethod
    def restore_clipboard(self, original_data: Optional[str]) -> None:
        """恢复剪贴板内容。"""
        ...
