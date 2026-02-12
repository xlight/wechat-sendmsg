# WeChat MCP Server - 代码库指南

本文档为 AI 编码代理提供有关此代码库的关键信息。

## 使用中文
- 所有文档、注释和字符串均使用中文
- LLM 输出也应使用中文
- 代码注释、docstring、日志信息必须使用中文

## 项目概述

这是一个 HTTP API 驱动的微信消息发送工具，支持 MCP (Model Context Protocol) 协议集成，专为 AI 助手和自动化任务设计。它使用 Python 实现，通过 pyautogui 和 win32gui 进行微信窗口自动化操作。

**核心技术栈:**
- Python 3.10+
- 官方 MCP Python SDK (FastMCP) + Starlette
- MCP 协议 (2024-11-05)
- Windows GUI 自动化 (pyautogui, win32gui, pywin32)
- Uvicorn ASGI 服务器

**主要功能模块:**
- MCP 服务器 + HTTP API (src/mcp_server.py) — FastMCP + Starlette 统一应用
- 消息队列 + 后台 Worker (src/message_queue.py) — SQLite 持久化，优先级，重试，崩溃恢复
- 微信控制器 (src/wechat_controller.py) - 主入口，组合 Mixin
  - 窗口查找 Mixin (src/window_finder.py)
  - 系统托盘管理 Mixin (src/tray_manager.py)
  - GUI 操作 Mixin (src/gui_operations.py)
- 配置管理 (src/config.py)
- 路径工具 (src/paths.py) — 兼容源码模式和 Nuitka 编译模式
- 系统托盘应用 (src/systray_app.py) — pystray 托盘图标 + 后台 uvicorn
- 防封号保护系统 (src/anti_ban/)

## 项目结构

```
chatwe-automate/
├── src/
│   ├── __init__.py               # 包初始化
│   ├── mcp_server.py             # MCP 服务器 + HTTP API（FastMCP + Starlette 统一应用）
│   ├── wechat_controller.py      # 微信自动化控制器（主入口，组合 Mixin）
│   ├── window_finder.py          # WindowFinderMixin: 版本检测、窗口查找、快捷键激活、Win32 API 激活
│   ├── tray_manager.py           # TrayManagerMixin: 系统托盘图标查找与双击恢复
│   ├── gui_operations.py         # GUIOperationsMixin: 输入框定位、剪贴板输入、搜索联系人、发送
│   ├── config.py                 # 配置管理模块
│   ├── message_queue.py          # MessageQueue + QueueWorker: SQLite 持久化消息队列与后台消费 Worker
│   ├── paths.py                  # 路径工具模块（兼容源码/编译模式）
│   ├── systray_app.py            # 系统托盘应用模块（pystray + 后台 uvicorn）
│   └── anti_ban/                 # 防封号保护系统
├── examples/
│   └── mcp_client_example.py     # MCP 客户端示例（支持 stdio / streamable-http）
├── docs/
│   ├── QUICK_START.md            # 快速开始指南
│   ├── AVOID_BAN.md              # 防封号指南
│   ├── ANTI_BAN_GUIDE.md         # 防封号保护系统详细指南
│   ├── TRAY_RECOVERY_IMPROVEMENT.md  # 托盘恢复机制说明
│   └── WINDOW_DETECTION_FIXES.md     # 窗口检测修复说明
├── static/
│   ├── index.html                # Web 首页
│   ├── test.html                 # 测试页面
│   └── queue.html                # 队列管理页面
├── assets/
│   └── icon.ico                  # 应用图标（托盘图标 + 编译 exe 图标）
├── openspec/                     # OpenSpec 规范目录
│   ├── specs/                    # 主规范
│   └── changes/                  # 变更记录
├── data/
│   ├── config.json                   # 配置文件（运行时自动生成）
│   ├── config.conservative.json      # 保守模式配置模板
│   ├── config.moderate.json          # 中等模式配置模板
│   ├── config.aggressive.json        # 激进模式配置模板
│   └── messages.db                   # 消息队列数据库（运行时自动生成）
├── build.py                      # Nuitka 编译构建脚本
├── test_server.py                # MCP 服务器测试脚本
├── test_send_chinese.py          # 中文发送测试
├── requirements.txt              # Python 依赖
├── AGENTS.md                     # 本文档
└── README.md                     # 项目说明
```

## 构建/测试命令

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行测试

**运行所有单元测试 (unittest):**
```bash
python -m unittest discover -s . -p "test_*.py"
```

**运行单个测试文件:**
```bash
# 测试 MCP 服务器 (不实际发送消息)
python test_server.py

# 测试中文消息发送 (需要微信运行)
python test_send_chinese.py
```

**运行特定测试类或方法:**
```bash
# 运行单个异步测试函数
python -c "from test_server import test_mcp_server; import asyncio; asyncio.run(test_mcp_server())"
```

### 运行服务器

**启动 MCP 服务器 (stdio 模式，默认):**
```bash
python src/mcp_server.py
```

**启动统一服务器 (streamable-http 模式，MCP + HTTP API):**
```bash
python src/mcp_server.py --transport streamable-http --port 8765
```

**启动系统托盘模式（后台运行，托盘图标管理）:**
```bash
python src/mcp_server.py --transport streamable-http --systray
```

**编译构建（Nuitka 编译为独立 exe）:**
```bash
# 单文件 exe（默认 onefile 模式）
python build.py

# 目录模式（调试用）
python build.py --standalone
```

**手动测试客户端:**
```bash
cd examples
# stdio 模式
python mcp_client_example.py
# streamable-http 模式
python mcp_client_example.py --transport streamable-http --url http://localhost:8765/mcp
```

### 代码检查

目前项目没有配置 linter/formatter，建议运行时使用:
```bash
# 检查 Python 语法错误
python -m py_compile src/*.py

# 建议的 linter (需要安装)
pylint src/*.py
flake8 src/*.py
mypy src/*.py --ignore-missing-imports
```

## 代码风格指南

### 通用原则

1. **编码风格**: 严格遵循 PEP 8 Python 编码规范
2. **字符编码**: 所有文件使用 UTF-8 编码，文件头声明 `#!/usr/bin/env python3`
3. **行长度**: 建议不超过 120 字符
4. **缩进**: 使用 4 个空格 (不使用 Tab)
5. **空行**: 类定义间 2 个空行，方法定义间 1 个空行
6. **文件头**: 每个文件开头必须有模块 docstring 说明文件功能

### 文件头模板

```python
#!/usr/bin/env python3
"""
模块名称
简要描述模块功能和用途。
"""
```

### 导入规范

**导入顺序 (PEP 8):**
```python
#!/usr/bin/env python3
"""模块 docstring"""

# 1. 标准库导入（按字母顺序）
import asyncio
import json
import logging
import sys
from typing import Any, Dict, Optional

# 2. 第三方库导入（按字母顺序）
import aiohttp
import httpx
import psutil
import pyautogui
import win32gui

# 3. 本地应用/库导入（按字母顺序）
from ai_integration import AIClient
from config import Config
from wechat_controller import WeChatController
```

**导入风格:**
- 优先使用 `from module import Class, function` 而非 `import module`
- 类型提示导入放在同组的第一行：`from typing import Any, Dict, List, Optional`
- 每行一个导入，除非是相关的多个类型
- 避免使用 `import *`

### 命名约定

**类名**: PascalCase
```python
class MCPServer:
class WeChatController:
class JSONRPCRequest:
class RateLimiter:
```

**函数/方法名**: snake_case
```python
def send_text_message():
def _handle_initialize():  # 私有方法使用单下划线前缀
async def handle_request():  # 异步方法也使用 snake_case
```

**变量名**: snake_case
```python
contact_name = "文件传输助手"
wechat_version = "4.0.0"
is_nt_version = True
user_message = "Hello"
```

**常量名**: UPPER_SNAKE_CASE（模块级常量）
```python
DEFAULTS = {...}  # 配置默认值
DEFAULT_SYSTEM_PROMPT = "你是一个友好的 AI 助手"
MAX_RETRY_COUNT = 3
```

**私有成员**: 单下划线前缀
```python
self._config = config
self._ai_client = AIClient()
def _extract_reply(self, data: dict) -> Optional[str]:
```

### 类型注解

**必须使用类型注解:**
```python
def send_text_message(self, contact_name: str, message: str) -> Dict[str, Any]:
async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
def _find_wechat_window(self) -> Optional[int]:
```

**复杂类型使用 typing 模块:**
```python
from typing import Any, Dict, List, Optional, Union, Deque

# 函数签名示例
def _register_tools(self) -> None:
async def _execute_send_message(
    self, 
    arguments: Dict[str, Any], 
    request_id: Optional[Union[str, int]]
) -> Dict[str, Any]:

# 属性类型注解
self.wechat_version: Optional[str] = None
self._timestamps: Deque[float] = deque()
```

### 文档字符串

**使用中文文档字符串 (与项目保持一致):**
```python
def send_text_message(self, contact_name: str, message: str) -> Dict[str, Any]:
    """向指定联系人发送文本消息。"""
    pass

class WeChatController:
    """微信自动化操作控制器（仅 NT 版本）。"""
    pass
```

**复杂函数使用详细文档 (Google 风格):**
```python
async def chat(self, user_message: str) -> str:
    """向 AI 服务发送消息并返回回复文本。

    Args:
        user_message: 用户发送的消息内容

    Returns:
        AI 回复的文本；出错时返回预设提示消息
    """
```

### 错误处理

**使用具体的异常类型:**
```python
try:
    result = await self._controller.send_text_message(contact_name, message)
except httpx.TimeoutException:
    logger.error(f"AI 请求超时（{self._config.ai_timeout}s）")
    return "AI 响应超时，请稍后再试"
except httpx.HTTPStatusError as e:
    logger.error(f"AI 服务返回错误: {e.response.status_code}")
    return "AI 服务暂时不可用"
except Exception as e:
    logger.error(f"执行时出错: {e}")
    return error_response
```

**JSON-RPC 错误格式:**
```python
error = {
    "code": -32601,  # 标准错误代码
    "message": f"方法未找到: {method}"
}
return JSONRPCResponse(error=error, id=request_id).to_dict()
```

### 日志记录

**使用 logging 模块 (不使用 print):**
```python
import logging

logger = logging.getLogger(__name__)  # 模块级 logger

# 类中初始化
self.logger = logging.getLogger(__name__)

# 不同级别的日志
logger.debug("调试信息")
logger.info(f"处理请求: {method}")
logger.warning("找不到微信进程/版本")
logger.error(f"处理请求时出错: {e}")
```

**日志格式 (标准配置):**
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 字符串格式化

**优先使用 f-string (Python 3.6+):**
```python
# 推荐
logger.info(f"处理请求: {method}")
message = f"成功发送消息给 {contact_name}: {text}"

# 避免（过时的格式化方式）
message = "成功发送消息给 %s: %s" % (contact_name, text)
message = "成功发送消息给 {}: {}".format(contact_name, text)
```

### 异步编程

**使用 async/await 模式:**
```python
async def send_text_message(self, contact_name: str, message: str) -> Dict[str, Any]:
    """异步发送消息"""
    result = await self._some_async_operation()
    return result

# 创建异步任务
asyncio.create_task(delayed_send())

# 异步等待
await asyncio.sleep(delay_seconds)

# 异步上下文管理器
async with gui_lock:
    await self._controller.send_text_message(group_name, message)
```

## 特定功能实现指南

### 配置管理模式

使用 `Config` 类加载配置，支持默认值和运行时更新：
```python
from config import Config, DEFAULTS

config = Config()  # 加载 data/config.json，不存在则创建模板
port = config.http_port  # 通过属性访问
config.update({"poll_interval": 10})  # 运行时更新
dict_data = config.to_dict(mask_secrets=True)  # 序列化（脱敏）
```

### 微信自动化要点

1. **仅支持 NT 框架** (微信 4.0+)，低于 4.0 的版本会被跳过
2. **使用剪贴板输入**避免输入法状态问题
3. **窗口焦点验证**：操作前必须确认窗口获得焦点
4. **GUI 互斥锁**：并发场景使用 `gui_lock` 保护 GUI 操作
5. **剪贴板保护**：自动备份和恢复用户剪贴板内容

### 添加新功能

**添加新 MCP 工具:**
1. 在 `src/mcp_server.py` 中使用 `@mcp.tool()` 装饰器注册新工具函数
2. 实现工具逻辑，返回字符串结果（成功描述或错误描述）
3. 如需新的微信操作，在 `WeChatController` 中实现底层功能

**添加新 HTTP API 端点:**
1. 在 `src/mcp_server.py` 中编写 Starlette 异步路由处理函数
2. 在 `create_starlette_app()` 的 `routes` 列表中注册路由
3. 更新 README.md 的 API 文档

## 注意事项

1. **Windows 专用**: 此项目仅支持 Windows 系统
2. **微信版本**: 完全支持微信 4.0+ (NT 框架)，传统版本兼容性有限
3. **运行要求**: 微信必须在运行并已登录
4. **窗口要求**: 微信窗口必须可见或最小化到托盘（支持自动恢复）
5. **并发安全**: GUI 操作必须使用 `gui_lock` 保护
6. **异步优先**: 所有 I/O 操作使用 async/await

## 许可证

MIT License - 允许商业使用但需评估风险
