# macOS 使用指南

## 安装

### 1. 安装依赖

```bash
cd wechat-sendmsg
pip install -r requirements.txt
```

> macOS 会自动安装 `pyobjc` 依赖（Apple 原生框架绑定），用于操作微信窗口和剪贴板。

### 2. 确保微信已登录

打开 macOS 微信并登录你的账号。

### 3. 启动服务器

```bash
# 方式一：stdio 模式（供 MCP 客户端连接）
python src/mcp_server.py

# 方式二：HTTP 模式（自带 Web 管理页面）
python src/mcp_server.py --transport streamable-http --port 8765
```

## 首次使用配置

### 辅助功能权限

macOS 微信 MCP 服务器使用 `ScriptingBridge` 和 `NSWorkspace` 来查找和激活微信窗口。
这些 API 通常不需要额外权限即可工作。

如果遇到窗口激活问题，请检查：
- **系统设置 → 隐私与安全性 → 辅助功能** — 确保终端应用已授权

### 配置快捷键（可选）

默认使用 API 方式激活微信窗口（自动查找并激活）。
你也可以配置快捷键方式来激活：

1. 打开 macOS **系统设置 → 键盘 → 键盘快捷键 → App 快捷键**
2. 点击 `+` 添加：
   - 应用：`微信` 或 `WeChat`
   - 菜单标题：打开主窗口（需确认微信中的准确菜单名）
   - 键盘快捷键：例如 `⌘⇧W` (Cmd+Shift+W)
3. 修改 `data/config.json` 中的 `wechat_hotkey` 为 `command+shift+w`

> 或者不配置快捷键，使用默认的 API 激活方式（推荐）。

## 发送消息

```bash
# 通过 HTTP API 发送
curl -X POST http://localhost:8765/api/v1/messages/send \
  -H "Content-Type: application/json" \
  -d '{"contact_name": "文件传输助手", "message": "Hello from macOS!"}'

# 通过 MCP 工具发送
# 在 MCP 客户端中调用 send_wechat_message 工具
```

## 与 Windows 的差异

| 功能 | Windows | macOS |
|------|---------|-------|
| 窗口查找 | win32gui.EnumWindows | NSWorkspace (pyobjc) |
| 窗口激活 | SetForegroundWindow | activateWithOptions_ |
| 托盘恢复 | 模拟双击托盘图标 | Dock 激活（无托盘） |
| 搜索快捷键 | Ctrl+F | Cmd+F |
| 发送快捷键 | Alt+S / Enter | Cmd+Enter |
| 剪贴板 | win32clipboard | NSPasteboard |
| 系统托盘 | 支持 | 不支持（使用菜单栏） |

## 已知限制

1. **macOS 微信版本**：仅支持 macOS 微信 4.0+（当前所有 macOS 微信均为 4.x）
2. **输入框定位**：通过屏幕坐标点击，窗口位置变化可能需要调整坐标
3. **无系统托盘**：macOS 微信没有系统托盘图标，窗口最小化到 Dock
4. **辅助功能权限**：极少数场景可能需要 Accessibility 权限
