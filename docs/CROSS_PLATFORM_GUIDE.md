# 跨平台使用指南

## 系统要求

| 平台 | 最低要求 | 推荐 |
|------|---------|------|
| **Windows** | 微信 4.0+, Python 3.10+ | Windows 10/11 |
| **macOS** | 微信 4.0+, Python 3.10+ | macOS 13+ |
| **Linux** | WeChat4Linux/Wine微信, Python 3.10+ | Ubuntu 22.04+ (X11) |

## 安装

### 1. 安装 Python 依赖

```bash
cd wechat-sendmsg

# 你的平台会自动安装对应依赖（Windows/macOS/Linux）
pip install -r requirements.txt
```

### 2. Linux 额外系统依赖

如果使用 Linux，需要额外安装：

```bash
# Ubuntu/Debian
sudo apt install xdotool wmctrl xclip

# Arch Linux
sudo pacman -S xdotool wmctrl xclip

# Fedora
sudo dnf install xdotool wmctrl xclip
```

### 3. 确保微信已启动并登录

| 平台 | 说明 |
|------|------|
| **Windows** | 微信 4.0+ 已登录 |
| **macOS** | 微信已登录 |
| **Linux** | WeChat4Linux 或 Wine 微信已登录 |

## 启动服务器

```bash
# stdio 模式（供 MCP 客户端连接）
python src/mcp_server.py

# HTTP 模式（自带 Web 管理页面）
python src/mcp_server.py --transport streamable-http --port 8765
```

## 发送消息

```bash
curl -X POST http://localhost:8765/api/v1/messages/send \
  -H "Content-Type: application/json" \
  -d '{"contact_name": "文件传输助手", "message": "你好！"}'
```

## 平台差异

### 快捷键

| 操作 | Windows | macOS | Linux |
|------|---------|-------|-------|
| 搜索联系人 | Ctrl+F | Cmd+F | Ctrl+F |
| 发送消息 | Alt+S → Enter | Cmd+Enter | Alt+S → Enter |
| 全选 | Ctrl+A | Cmd+A | Ctrl+A |
| 粘贴 | Ctrl+V | Cmd+V | Ctrl+V |

### 窗口管理

| 功能 | Windows | macOS | Linux |
|------|---------|-------|-------|
| 窗口查找 | win32gui.EnumWindows | NSWorkspace | xdotool |
| 窗口激活 | SetForegroundWindow | NSApplication.activate | xdotool windowactivate |
| 恢复窗口 | 系统托盘双击 | Dock 激活 | xdotool windowmap |
| 工具依赖 | 内置 | pyobjc | xdotool/wmctrl |

### 剪贴板

| 平台 | 实现 |
|------|------|
| **Windows** | win32clipboard (API) |
| **macOS** | NSPasteboard (pyobjc) |
| **Linux** | xclip (命令行) / pyperclip |

### Wayland 注意事项

Linux 上如果使用 Wayland（非 X11），`xdotool` 功能受限。建议：

1. 使用 X11 会话，或
2. 安装 `ydotoold` 作为 xdotool 替代
3. 微信窗口需保持可见

## 配置

编辑 `data/config.json`：

```json
{
  "http_port": 8765,
  "wechat_hotkey": "ctrl+alt+w"
}
```

`wechat_hotkey` 可为空字符串（使用 API 方式激活，推荐），
或设置为微信设置的全局快捷键。

## 测试连接

```bash
# macOS
python test_status.py

# 或通过 API
curl http://localhost:8765/api/v1/status
```
