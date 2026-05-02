#!/usr/bin/env python3
"""
Linux 窗口查找与激活实现

依赖外部工具：
- xdotool:  查找窗口、激活窗口、获取窗口信息
- wmctrl:   备用窗口管理工具
- xprop:    读取窗口属性

微信在 Linux 上通常通过 Wine/WeChat4Linux 运行。
支持以下场景：
1. WeChat4Linux（原生 Linux 版，electron 封装）
2. Wine 微信（Windows 微信通过 Wine 运行）
"""

import logging
import subprocess
import time
import shutil
from typing import Optional, Dict, Any, List

from ..base import WindowFinder

logger = logging.getLogger(__name__)


def _run(cmd: List[str], timeout: int = 5) -> Optional[str]:
    """运行外部命令并返回 stdout。"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


class LinuxWindowFinder(WindowFinder):
    """Linux 平台的微信窗口查找与激活。

    使用 xdotool 操作 X11 窗口。
    如果使用 Wayland，xdotool 功能受限，需使用 ydotoold 或 wtype。
    """

    # 微信窗口标题关键词
    WECHAT_TITLES = ['微信', 'WeChat', 'Weixin', 'wechat']

    def __init__(self, config: object = None):
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._check_tools()

    def _check_tools(self) -> None:
        """检查依赖工具是否可用。"""
        self._has_xdotool = shutil.which('xdotool') is not None
        self._has_wmctrl = shutil.which('wmctrl') is not None
        self._has_xprop = shutil.which('xprop') is not None

        if not self._has_xdotool:
            self._logger.warning("未找到 xdotool，窗口操作将受限。请安装：sudo apt install xdotool")

    # ── WindowFinder 接口 ──

    def detect_wechat_version(self) -> Optional[str]:
        """检测微信版本。

        通过读取进程命令行或桌面文件来识别版本。
        """
        # 方式1: 通过 xprop 读取微信窗口的进程 PID
        wid = self.find_wechat_window()
        if wid is None:
            return None

        pid_str = _run(['xdotool', 'getwindowpid', str(wid)])
        if not pid_str:
            return None

        try:
            pid = int(pid_str)
            with open(f'/proc/{pid}/cmdline', 'r') as f:
                cmdline = f.read().replace('\0', ' ').strip()

            # 尝试从命令行提取版本信息
            if 'wechat' in cmdline.lower():
                # 可能是 WeChat4Linux electron 版
                version = _run(['dpkg', '-l', 'wechat'], timeout=3)
                if version:
                    for line in version.split('\n'):
                        if 'wechat' in line.lower():
                            parts = line.split()
                            if len(parts) >= 3:
                                return parts[2]

            # Wine 版：尝试从 .exe 获取
            if '.exe' in cmdline.lower():
                return "wine (WeChat Windows)"

            return f"pid={pid}"
        except Exception:
            return None

    def find_wechat_window(self) -> Optional[int]:
        """查找微信窗口，返回 X11 窗口 ID (WID)。"""
        if not self._has_xdotool:
            self._logger.error("xdotool 未安装，无法查找窗口")
            return None

        # 按窗口标题搜索
        for title in self.WECHAT_TITLES:
            wid = _run(['xdotool', 'search', '--name', title])
            if wid:
                # 可能有多个匹配，取第一个
                wid_first = wid.split('\n')[0].strip()
                if wid_first:
                    self._logger.info(f"找到微信窗口: WID={wid_first}, title={title}")
                    return int(wid_first)

            wid = _run(['xdotool', 'search', '--class', title])
            if wid:
                wid_first = wid.split('\n')[0].strip()
                if wid_first:
                    return int(wid_first)

            # 也搜一下 WeChat (全大写/混合)
            wid = _run(['xdotool', 'search', '--classname', title])
            if wid:
                wid_first = wid.split('\n')[0].strip()
                if wid_first:
                    return int(wid_first)

        self._logger.warning("未找到微信窗口")
        return None

    def activate_window(self, window_id: int) -> bool:
        """激活微信窗口。"""
        if not self._has_xdotool:
            return False

        # 方式1: xdotool windowactivate
        result = _run(['xdotool', 'windowactivate', str(window_id)])
        if result is not None:
            time.sleep(0.3)
            self._logger.info(f"窗口激活成功: WID={window_id}")
            return True

        # 方式2: 备用 windowmap（如果窗口被最小化）
        _run(['xdotool', 'windowmap', str(window_id)])
        time.sleep(0.3)
        result = _run(['xdotool', 'windowactivate', str(window_id)])
        if result is not None:
            return True

        self._logger.error(f"窗口激活失败: WID={window_id}")
        return False

    def restore_window(self) -> Optional[int]:
        """从通知区域恢复微信窗口。"""
        wid = self.find_wechat_window()
        if wid is None:
            return None

        # 尝试 windowmap + activate
        _run(['xdotool', 'windowmap', str(wid)])
        time.sleep(0.3)
        _run(['xdotool', 'windowactivate', str(wid)])
        time.sleep(0.5)

        # 验证是否可见
        info = _run(['xdotool', 'getwindowgeometry', str(wid)])
        if info:
            self._logger.info(f"窗口已恢复: WID={wid}")
            return wid

        return None

    def is_wechat_available(self) -> bool:
        return self.find_wechat_window() is not None

    def get_status(self) -> Dict[str, Any]:
        wid = self.find_wechat_window()
        ver = self.detect_wechat_version()
        return {
            "wechat_available": wid is not None,
            "window_id": wid,
            "wechat_version": ver,
            "platform": "linux",
            "supported": wid is not None,
            "tools": {
                "xdotool": self._has_xdotool,
                "wmctrl": self._has_wmctrl,
            },
        }
