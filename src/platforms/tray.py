#!/usr/bin/env python3
"""
系统托盘/菜单栏 — 跨平台后台常驻方案

## 架构

```mermaid
flowchart TB
    subgraph 统一入口
        MCP["mcp_server.py --systray"]
        TRAY["platforms/tray.py\\ncreate_tray_manager()"]
    end

    subgraph 平台实现
        WIN["platforms/win/tray.py\\npystray • Windows 系统托盘"]
        MAC["platforms/mac/tray.py\\nNSStatusBar • macOS 菜单栏"]
        LIN["platforms/linux/tray.py\\npystray • Linux AppIndicator"]
    end

    MCP --> TRAY
    TRAY --> WIN & MAC & LIN
```

## 三平台对照

| 维度 | Windows | macOS | Linux |
|------|---------|-------|-------|
| 方案 | pystray | NSStatusBar (pyobjc) | pystray (AppIndicator) |
| 位置 | 任务栏通知区域 | 菜单栏右侧 | 通知区域/面板 |
| 依赖 | pystray（已有） | pyobjc（已有） | pystray + 系统指示器 |
| 现有代码 | `systray_app.py` | 新建 | 新建 |

## 统一菜单

```
微信 MCP 服务器 - 运行中 (:{port})
─────────────────
打开管理页面
─────────────────
退出
```

## 实施步骤

1. ✅ `platforms/tray.py` — TrayManager 抽象基类
2. . `platforms/win/tray.py` — pystray 实现
3. . `platforms/mac/tray.py` — NSStatusBar 实现
4. . `platforms/linux/tray.py` — pystray 实现
5. . `platforms/__init__.py` — 新增 `create_tray_manager()` 工厂
6. . `mcp_server.py` — 从硬编码 `SystrayApp` 改为工厂调用
"""

from abc import ABC, abstractmethod
from typing import Optional
import threading
import webbrowser
import logging
import os

from PIL import Image
from paths import get_assets_dir

logger = logging.getLogger(__name__)
APP_NAME = "微信 MCP 服务器"


class TrayManager(ABC):
    """跨平台系统托盘/菜单栏管理器基类。

    子类必须实现 _run_loop() 和 _exit_platform()。
    """

    def __init__(self, app, host: str = "0.0.0.0", port: int = 8765):
        self._app = app
        self._host = host
        self._port = port
        self._server: Optional[object] = None
        self._server_thread: Optional[threading.Thread] = None
        self._icon_image: Optional[Image.Image] = None

    def run(self) -> None:
        """启动后台常驻（阻塞主线程）。"""
        self._load_icon()
        self._start_server()
        self._run_loop()

    def stop(self) -> None:
        """优雅关闭服务器。"""
        if self._server is not None:
            logger.info("正在停止服务器...")
            self._server.should_exit = True
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=10.0)

    @abstractmethod
    def _run_loop(self) -> None:
        """进入主事件循环（阻塞，直到退出）。"""
        ...

    @abstractmethod
    def _exit_platform(self) -> None:
        """平台特定的退出方式。"""
        ...

    # ── 通用方法 ──

    def _load_icon(self) -> None:
        """加载图标。优先使用 PNG，回退到 ICO 或备用。"""
        # PNG（各平台通用）
        png_path = os.path.join(get_assets_dir(), "icon.png")
        if os.path.isfile(png_path):
            try:
                self._icon_image = Image.open(png_path)
                logger.info(f"已加载图标: {png_path}")
                return
            except Exception as e:
                logger.warning(f"加载 PNG 图标失败: {e}")

        # ICO（Windows 专用）
        ico_path = os.path.join(get_assets_dir(), "icon.ico")
        if os.path.isfile(ico_path):
            try:
                img = Image.open(ico_path)
                # 转为 RGBA PNG，确保不保留 ICO 多帧格式
                rgba = Image.new('RGBA', img.size, (0, 0, 0, 0))
                if img.mode == 'RGBA':
                    rgba = img
                elif 'transparency' in img.info:
                    rgba = img.convert('RGBA')
                else:
                    rgba = img.convert('RGBA')
                self._icon_image = rgba
                logger.info(f"已加载图标: {ico_path}")
                return
            except Exception as e:
                logger.warning(f"加载 ICO 图标失败: {e}")

        self._icon_image = Image.new("RGBA", (64, 64), (7, 193, 96, 255))
        logger.info("使用备用图标（绿色方块）")

    def _start_server(self) -> None:
        """后台线程启动 uvicorn 服务器。"""
        import asyncio
        import uvicorn

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            config = uvicorn.Config(
                app=self._app, host=self._host, port=self._port, log_level="info",
            )
            self._server = uvicorn.Server(config)
            loop.run_until_complete(self._server.serve())

        self._server_thread = threading.Thread(target=run, name="uvicorn", daemon=True)
        self._server_thread.start()
        logger.info(f"后台服务器已启动: http://{self._host}:{self._port}")

    def _on_open_web(self, *args) -> None:
        """打开管理页面。"""
        webbrowser.open(f"http://localhost:{self._port}")

    def _on_exit(self, *args) -> None:
        """退出应用。"""
        logger.info("用户请求退出...")
        self._exit_platform()
