# WeChat MCP Server

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/1052666/WeChat-MCP-Server?style=social)
![GitHub forks](https://img.shields.io/github/forks/1052666/WeChat-MCP-Server?style=social)
![GitHub license](https://img.shields.io/github/license/1052666/WeChat-MCP-Server)
![Python version](https://img.shields.io/badge/python-3.10%2B-blue)

**一个HTTP API驱动的微信消息发送工具，支持MCP协议集成，专为AI助手和自动化任务设计**

[快速开始](#-安装和配置) • [功能特点](#-功能特点) • [使用方法](#-使用方法) • [API文档](#️-可用工具) • [贡献指南](#-贡献)

</div>

---

## 📋 目录

- [什么是 MCP？](#-什么是-mcp)
- [功能特点](#-功能特点)
- [项目结构](#-项目结构)
- [安装和配置](#-安装和配置)
- [可用工具](#️-可用工具)
- [使用方法](#-使用方法)
- [HTTP API](#-http-api)
- [自动化任务与消息报备](#-自动化任务与消息报备)
- [MCP协议实现](#-mcp协议实现)
- [技术架构](#️-技术架构)
- [注意事项](#️-注意事项)
- [故障排除](#-故障排除)
- [开发和扩展](#-开发和扩展)
- [支持我们](#-支持我们)
- [免责声明](#️-重要免责声明)
- [许可证](#-许可证)
- [贡献](#-贡献)
- [项目统计](#-项目统计)

---

## 🤖 什么是 MCP？

> **Model Context Protocol (MCP)** 是一个开放标准协议，用于连接AI助手与各种数据源和工具。它就像是AI应用的USB-C接口，提供了标准化的方式来连接AI模型与外部系统。

## 💻 兼容性

- ✅ **微信版本** - 完全支持微信 4.0 以上的 NT 框架版本（传统版本已不再支持）
- ✅ **操作系统** - 支持 Windows 10/11 系统
- ✅ **AI助手** - 兼容 Claude、ChatGPT 等支持 MCP 协议的 AI 助手

## ✨ 功能特点

- ✅ **MCP标准兼容** - 基于官方 MCP Python SDK (FastMCP) 实现，完全符合 MCP 2024-11-05 规范
- ✅ **双传输模式** - 支持 stdio 和 Streamable HTTP 两种 MCP 传输模式
- ✅ **HTTP API** - 提供 RESTful API 接口，与 MCP 端点共享同一端口（Starlette 统一应用）
- ✅ **微信消息发送** - 支持发送文本消息到微信联系人或群聊
- ✅ **本地持久化消息队列** - SQLite 驱动的消息队列，支持优先级（0-10）、定时发送、自动重试、崩溃恢复
  - **双发送模式**: 队列模式（异步入队，后台 worker 消费）和同步模式（暂停队列，立即执行）
  - **队列管理**: 通过 MCP 工具和 HTTP API 查看状态、取消待发送、重试失败消息
  - **Web 管理界面**: `/queue` 页面可视化管理队列（筛选、分页、自动刷新）
- ✅ **定时发送** - 支持延迟发送消息功能
- ✅ **NT 框架支持** - 完全支持微信 4.0 以上的 NT 框架版本
- ✅ **智能版本检测** - 自动检测微信版本并适配相应的操作方式
- ✅ **快捷键窗口激活** - 优先通过全局快捷键激活微信窗口（需在微信设置中配置），失败时自动回退到 Win32 API
- ✅ **系统托盘恢复** - 微信最小化到托盘时自动恢复窗口
- ✅ **剪贴板输入技术** - 使用剪贴板输入，完全避免输入法状态影响
- ✅ **多种发送方式** - 支持Enter、Ctrl+Enter、Alt+S等多种发送快捷键
- ✅ **异步处理** - 异步处理，不阻塞 AI 助手或调用方
- ✅ **完整日志** - 完整的错误处理和日志记录
- ✅ **防封号保护系统** - 多层防护机制降低账号封禁风险
  - 增强版速率限制（分钟/小时/天三级限制）
  - 人类行为模拟（随机思考时间、打字速度）
  - 工作时间控制（仅在指定时段和日期运行）
  - 内容多样化（智能添加前缀/后缀、随机跳过）
  - 自然 GUI 操作（随机鼠标偏移、缓慢移动）

## 🔴 不再包含的功能

**v2.0.0 起，以下功能已移除：**
- ❌ 群聊消息监听和自动回复
- ❌ AI 服务集成（OpenAI 兼容 API）
- ❌ 配置管理 API 端点

**原因：** 这些功能依赖于不可靠的消息读取机制（需要使用 `Ctrl+A` 选择文本，但在微信中不生效），且增加了项目复杂度。

**替代方案：** 如需监听微信消息，建议使用专用的微信消息监听服务（如 [chatlog](https://github.com/LC044/WeChatMsg)），然后通过本项目的 HTTP API 发送回复消息。

## 📁 项目结构

```
WeChat-MCP-Server/
├── 📂 src/
│   ├── 📄 __init__.py               # 包初始化
│   ├── 📄 mcp_server.py             # MCP 服务器 + HTTP API（FastMCP + Starlette 统一应用）
│   ├── 📄 wechat_controller.py      # 微信自动化控制器（主入口）
│   ├── 📄 window_finder.py          # 窗口查找与版本检测 Mixin
│   ├── 📄 tray_manager.py           # 系统托盘管理 Mixin
│   ├── 📄 gui_operations.py         # GUI 操作（输入、搜索、发送）Mixin
│   ├── 📄 config.py                 # 配置管理模块
│   ├── 📄 message_queue.py          # 消息队列 + 后台 Worker（SQLite 持久化）
│   └── 📂 anti_ban/                 # 防封号保护系统
│       ├── 📄 __init__.py           # 防封号包初始化
│       ├── 📄 enhanced_rate_limiter.py    # 增强版速率限制器
│       ├── 📄 human_behavior.py     # 人类行为模拟器
│       ├── 📄 work_time_controller.py     # 工作时间控制器
│       ├── 📄 content_diversifier.py      # 内容多样化器
│       └── 📄 natural_gui.py        # 自然 GUI 操作
├── 📂 examples/
│   └── 📄 mcp_client_example.py     # MCP 客户端使用示例（支持 stdio / streamable-http）
├── 📂 docs/
│   ├── 📄 QUICK_START.md            # 快速开始指南
│   └── 📄 AVOID_BAN.md              # 防封号指南
├── 📂 static/
│   ├── 📄 index.html                # Web 首页
│   ├── 📄 test.html                 # 测试页面
│   └── 📄 queue.html                # 队列管理页面
├── 📂 支持我们/
│   ├── 🖼️ 1.jpg                     # 支付宝收款码
│   └── 🖼️ 2.jpg                     # 微信赞赏码
├── 📂 data/
│   ├── 📄 config.json                # 配置文件（运行时自动生成）
│   ├── 📄 config.conservative.json   # 保守模式配置模板
│   ├── 📄 config.moderate.json       # 中等模式配置模板
│   ├── 📄 config.aggressive.json     # 激进模式配置模板
│   └── 📄 messages.db               # 消息队列数据库（运行时自动生成）
├── 📄 requirements.txt              # 依赖包列表
├── 📄 LICENSE                       # 许可证文件
└── 📄 README.md                     # 项目说明文档
```

## 🚀 安装和配置

### 1️⃣ 安装依赖

```bash
# 克隆项目
git clone https://github.com/1052666/WeChat-MCP-Server.git
cd WeChat-MCP-Server

# 安装依赖（需要 Python 3.10+）
pip install -r requirements.txt
```

### 2️⃣ 确保微信已启动并登录

> ⚠️ **重要提醒**
> 
> 在使用前，请确保：
> - ✅ 微信客户端已安装并正在运行
> - ✅ 已成功登录微信账号
> - ✅ 微信窗口可见（最小化到托盘时会自动恢复）




### 3️⃣ 配置AI助手

将此MCP服务器添加到您的AI助手配置中。以 **Claude Desktop** 为例：

```json
{
  "mcpServers": {
    "wechat": {
      "command": "python",
      "args": ["C:/path/to/WeChat-MCP-Server/src/mcp_server.py"],
      "env": {}
    }
  }
}
```

> **注意**: 请将 `C:/path/to/WeChat-MCP-Server` 替换为您实际的项目路径

## 🛠️ 可用工具

### 📤 send_wechat_message

发送文本消息到指定的微信联系人或群组。支持队列模式（异步入队）和同步模式（立即执行）。

**参数：**

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `contact_name` | `string` | ✅ | 联系人或群组名称 |
| `message` | `string` | ✅ | 要发送的文本消息 |
| `mode` | `string` | ❌ | 发送模式：`"queue"`（默认，异步入队）或 `"sync"`（同步立即发送） |
| `priority` | `integer` | ❌ | 优先级 0-10，数值越小越优先，默认 5 |

**示例：**
```json
{
  "name": "send_wechat_message",
  "arguments": {
    "contact_name": "文件传输助手",
    "message": "Hello from AI assistant!",
    "mode": "queue",
    "priority": 3
  }
}
```

### ⏰ schedule_wechat_message

安排在指定延迟后发送消息。

**参数：**

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `contact_name` | `string` | ✅ | 联系人或群组名称 |
| `message` | `string` | ✅ | 要发送的文本消息 |
| `delay_seconds` | `number` | ✅ | 延迟发送的秒数 |
| `priority` | `integer` | ❌ | 优先级 0-10，数值越小越优先，默认 5 |

**示例：**
```json
{
  "name": "schedule_wechat_message",
  "arguments": {
    "contact_name": "文件传输助手",
    "message": "This is a scheduled message!",
    "delay_seconds": 30,
    "priority": 5
  }
}
```

### 📊 get_queue_status

查看消息队列状态概览，包含各状态消息计数和 worker 运行状态。

**参数：** 无

**示例：**
```json
{
  "name": "get_queue_status",
  "arguments": {}
}
```

### 🔍 get_message_detail

查看指定消息的详细信息。

**参数：**

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message_id` | `integer` | ✅ | 消息 ID |

**示例：**
```json
{
  "name": "get_message_detail",
  "arguments": {
    "message_id": 42
  }
}
```

### ❌ cancel_queue_message

取消一条待发送（pending）的消息。

**参数：**

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message_id` | `integer` | ✅ | 消息 ID |

**示例：**
```json
{
  "name": "cancel_queue_message",
  "arguments": {
    "message_id": 42
  }
}
```

### 🔄 retry_queue_message

重试一条失败（failed）的消息，将其状态重置为 pending，retry_count 清零。

**参数：**

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `message_id` | `integer` | ✅ | 消息 ID |

**示例：**
```json
{
  "name": "retry_queue_message",
  "arguments": {
    "message_id": 42
  }
}
```

## 💡 使用方法

### 🤖 在AI助手中使用

配置完成后，您可以直接在AI助手中使用自然语言请求：

> 💬 **示例对话**
> 
> - "帮我给张三发个微信消息说'会议推迟到下午3点'"
> - "10分钟后提醒我开会，发到工作群"
> - "给文件传输助手发送今天的工作总结"

### 🧪 直接测试

运行示例客户端进行测试：

```bash
# stdio 模式（自动启动服务器子进程）
cd examples
python mcp_client_example.py

# streamable-http 模式（需先启动服务器）
python mcp_client_example.py --transport streamable-http --url http://localhost:8765/mcp
```

## 📡 HTTP API

### 启动服务器

MCP 服务器和 HTTP API 运行在同一个 Starlette 应用中（统一端口）：

```bash
# 启动 streamable-http 模式（MCP + HTTP API 统一服务器）
python src/mcp_server.py --transport streamable-http

# 指定端口和监听地址
python src/mcp_server.py --transport streamable-http --port 8765 --host 0.0.0.0

# stdio 模式（仅 MCP，无 HTTP API）
python src/mcp_server.py
```

streamable-http 模式下可用的端点：
- **MCP 端点**: `http://localhost:8765/mcp` — Streamable HTTP MCP 协议
- **HTTP API**: `http://localhost:8765/api/v1/...` — RESTful API
- **Web 页面**: `http://localhost:8765/` — 首页 / `http://localhost:8765/test` — 测试页面 / `http://localhost:8765/queue` — 队列管理

### 配置文件

首次运行时会在 `data/` 目录自动创建 `config.json` 模板文件。主要配置项：

```json
{
  "http_port": 8080,
  "queue_db_path": "data/messages.db",
  "queue_max_retries": 3,
  "queue_poll_interval": 1.0,
  "rate_limit_per_minute": 10,
  "rate_limit_per_hour": 20,
  "rate_limit_per_day": 100,
  "min_think_time": 3.0,
  "max_think_time": 15.0,
  "work_hours_start": 9,
  "work_hours_end": 22,
  "work_days": [0, 1, 2, 3, 4],
  "max_daily_runtime_hours": 8.0,
  "wechat_hotkey": "ctrl+alt+w"
}
```

> **队列配置说明:**
> - **`queue_db_path`** — SQLite 数据库文件路径，默认 `data/messages.db`，首次启动自动创建
> - **`queue_max_retries`** — 消息发送失败后最大重试次数，默认 3；设为 0 禁用重试
> - **`queue_poll_interval`** — 队列 worker 轮询间隔（秒），默认 1.0
>
> **`wechat_hotkey`** — 用于激活微信窗口的全局快捷键，需在微信「设置 → 快捷键」中配置相同的组合键。快捷键激活失败时会自动回退到 Win32 API 方式。

详细的防封号配置说明请参考 [docs/AVOID_BAN.md](docs/AVOID_BAN.md)。

### API 端点

#### 发送消息

```
POST /api/v1/messages/send
Content-Type: application/json

{
  "contact_name": "文件传输助手",
  "message": "Hello from HTTP API!",
  "mode": "queue",
  "priority": 5
}
```

**参数说明：**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `contact_name` | `string` | ✅ | 联系人或群组名称 |
| `message` | `string` | ✅ | 消息内容 |
| `mode` | `string` | ❌ | `"queue"`（默认，异步入队）或 `"sync"`（同步立即发送） |
| `priority` | `integer` | ❌ | 优先级 0-10，默认 5，数值越小越优先 |
| `delay_seconds` | `number` | ❌ | 延迟发送秒数（仅队列模式有效） |

**队列模式响应 (200):**
```json
{
  "ok": true,
  "message_id": 123,
  "mode": "queue"
}
```

**同步模式响应 (200):**
```json
{
  "ok": true,
  "mode": "sync"
}
```

#### 查询状态

```
GET /api/v1/status
```

**响应 (200):**
```json
{
  "ok": true,
  "wechat_status": {
    "running": true,
    "version": "4.0.x",
    "window_found": true
  }
}
```

#### 查询防封号统计

```
GET /api/v1/anti-ban/stats
```

**响应 (200):**
```json
{
  "ok": true,
  "rate_limiter": {
    "last_minute": 2,
    "last_hour": 15,
    "last_day": 87,
    "limit_minute": 10,
    "limit_hour": 20,
    "limit_day": 100
  },
  "work_time": {
    "is_work_time": true,
    "current_hour": 14,
    "work_hours": "9-22",
    "current_day": 1,
    "work_days": [0, 1, 2, 3, 4]
  },
  "runtime": {
    "current_runtime_seconds": 7234,
    "current_runtime_hours": 2.01,
    "max_daily_hours": 8.0,
    "remaining_hours": 5.99
  }
}
```

#### 查询防封号配置

```
GET /api/v1/anti-ban/config
```

返回当前防封号相关配置的详细信息。

#### 队列状态概览

```
GET /api/v1/queue/status
```

**响应 (200):**
```json
{
  "ok": true,
  "stats": {
    "pending": 5,
    "processing": 1,
    "completed": 42,
    "failed": 2,
    "cancelled": 0
  },
  "worker_running": true
}
```

#### 队列消息列表

```
GET /api/v1/queue/messages?status=pending&limit=20&offset=0
```

**查询参数：**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| `status` | `string` | 按状态筛选：pending/processing/completed/failed/cancelled |
| `limit` | `integer` | 每页数量，默认 20 |
| `offset` | `integer` | 偏移量，默认 0 |

**响应 (200):**
```json
{
  "ok": true,
  "messages": [...],
  "total": 50
}
```

#### 消息详情

```
GET /api/v1/queue/messages/{id}
```

返回指定 ID 的消息完整信息。

#### 取消消息

```
POST /api/v1/queue/messages/{id}/cancel
```

仅允许取消 status=pending 的消息。

**响应 (200):**
```json
{
  "ok": true
}
```

#### 重试消息

```
POST /api/v1/queue/messages/{id}/retry
```

仅允许重试 status=failed 的消息，将其重置为 pending，retry_count 清零。

**响应 (200):**
```json
{
  "ok": true
}
```

## 🔄 自动化任务与消息报备

### 🚀 使用Cloud Code自动化工作流

试想一下，您可以使用Cloud Code等自动化工具完成各种任务，并通过微信自动发送报备消息：

#### 📊 自动化场景示例

1. **代码部署通知**
   - 当CI/CD流程完成时，自动向开发团队群发送部署状态
   - 包含构建结果、测试覆盖率和部署环境信息

2. **监控报警集成**
   - 将服务器监控报警直接推送到运维群
   - 系统负载、异常状态实时通知到责任人

3. **数据处理完成通知**
   - 大型数据处理任务完成后自动通知数据分析师
   - 包含处理时间、数据量和结果摘要

4. **定时报表推送**
   - 每日/每周自动生成业务报表并发送给管理层
   - 销售数据、用户增长等关键指标自动汇总

#### 💻 实现示例

```python
# 示例：通过 HTTP API 发送微信通知
import requests

def send_deployment_notification(status, details):
    """通过 HTTP API 发送部署通知到微信群"""
    payload = {
        "contact_name": "技术团队群",
        "message": f"部署状态: {status}\n详情: {details}",
        "mode": "queue",
        "priority": 1
    }
    
    response = requests.post(
        "http://localhost:8765/api/v1/messages/send",
        json=payload,
    )
    return response.json()

# 在 CI/CD 流程中调用
if __name__ == "__main__":
    send_deployment_notification("成功", "版本v2.1.0已部署到生产环境")
```

## 🔧 MCP协议实现

本服务器基于 [官方 MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (FastMCP) 实现，支持以下传输模式：

| 传输模式 | 命令 | 说明 |
|---------|------|------|
| `stdio` (默认) | `python src/mcp_server.py` | 通过标准输入/输出通信，适配 Claude Desktop 等 AI 助手 |
| `streamable-http` | `python src/mcp_server.py --transport streamable-http` | HTTP 长连接，MCP + HTTP API 统一端口 |

MCP 协议版本: **2024-11-05**

SDK 自动处理的协议功能：
- `initialize` / `notifications/initialized` 握手
- `tools/list` / `tools/call` 工具调用
- `ping` / `pong` 心跳
- 会话管理 (`Mcp-Session-Id`)
- JSON-RPC 2.0 消息序列化

### 📡 JSON-RPC 消息格式

<details>
<summary>点击查看详细的消息格式示例</summary>

**请求示例：**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "send_wechat_message",
    "arguments": {
      "contact_name": "文件传输助手",
      "message": "Hello World!"
    }
  },
  "id": 1
}
```

**响应示例：**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Successfully sent message to 文件传输助手: Hello World!"
      }
    ]
  },
  "id": 1
}
```

</details>

## 🏗️ 技术架构

### 🖥️ MCP服务器 (mcp_server.py)
- 基于官方 MCP Python SDK (FastMCP) 实现
- 支持 stdio 和 Streamable HTTP 双传输模式
- Streamable HTTP 模式下与 HTTP API 共享同一 Starlette 应用和端口
- 使用 `@mcp.tool()` 装饰器注册工具
- CORS 中间件暴露 `Mcp-Session-Id` 响应头

### 📱 微信控制器 (wechat_controller.py)

采用 **Mixin 模式**拆分为 4 个模块，降低单文件复杂度：

- **wechat_controller.py** - 主控制器入口，组合各 Mixin，提供 `send_text_message`、`schedule_message`、`get_status` 等公开 API
- **window_finder.py** - `WindowFinderMixin`：微信版本检测、窗口查找、快捷键激活（`_activate_window_by_hotkey`）、Win32 API 激活（`_activate_window`）、微信窗口判定（`_is_wechat_window`）、修饰键释放
- **tray_manager.py** - `TrayManagerMixin`：系统托盘图标查找（跨进程 TBBUTTON 结构读取）、双击恢复（PostMessage 回调）
- **gui_operations.py** - `GUIOperationsMixin`：输入框定位与点击、剪贴板输入与保护、联系人搜索、消息发送

**技术特性:**
- **🆕 NT 框架支持**: 完全支持微信 4.0 及以上版本
- **🔍 智能版本检测**: 通过进程信息自动检测微信版本
- **🎯 多窗口类型识别**: 支持 Qt 框架窗口类名模式匹配
- **📌 系统托盘恢复**: 微信最小化到托盘时，通过跨进程内存读取定位托盘图标并模拟双击恢复
- **🛡️ Edge 浏览器误识别防护**: 仅允许属于 WeChat 进程的窗口参与窗口匹配

#### 🎯 智能输入技术
- **智能定位**: 自适应不同窗口大小的输入框位置检测
- **剪贴板输入**: 使用Windows剪贴板API实现文本输入，完全避免输入法干扰
- **焦点验证**: 通过测试字符输入验证输入框焦点状态
- **剪贴板保护**: 自动备份和恢复用户原始剪贴板内容
- **多重发送**: 支持Enter、Ctrl+Enter、Alt+S等多种发送快捷键备选方案

## ⚠️ 注意事项

### 🖥️ 系统要求
- **操作系统**: Windows 系统
- **微信版本**: 微信 4.0 及以上 NT 框架版本（传统版本已不再支持）
- **Python版本**: Python 3.10+（MCP SDK 要求）

### 🔐 权限要求
- 需要屏幕控制权限（pyautogui）

### 📝 使用限制
> ⚠️ **重要提醒**
> 
> - 使用期间请勿手动操作微信窗口
> - 确保微信窗口未被其他窗口完全遮挡
> - 微信最小化到托盘时系统会自动恢复窗口
> - 建议先向"文件传输助手"测试

### 🛡️ 安全考虑
- 本工具仅用于自动化个人微信操作
- 请遵守微信使用条款
- 不建议用于大量消息发送

## 🔍 故障排除

<details>
<summary>📋 常见问题解决方案</summary>

### ❌ 找不到微信窗口
- ✅ 确保微信已启动并登录
- ✅ 检查微信窗口是否可见
- ✅ 尝试重启微信

### ❌ 消息发送失败
- ✅ 检查联系人名称是否正确
- ✅ 确保联系人在最近聊天列表中
- ✅ 验证微信窗口是否处于活动状态

### ❌ 输入法相关问题
- ✅ **已解决**: 本项目使用剪贴板输入技术，完全避免输入法状态影响
- ✅ 支持任何输入法状态下的中文、英文、表情符号输入
- ✅ 自动保护用户剪贴板内容，使用后自动恢复

### ❌ 输入框定位失败
- ✅ **已优化**: 智能输入框定位系统自适应不同窗口大小
- ✅ 支持多种微信界面布局和分辨率
- ✅ 自动尝试多个可能的输入框位置

### ❌ MCP连接问题
- ✅ 检查Python环境和依赖包
- ✅ 验证MCP配置文件路径
- ✅ 查看服务器日志输出

</details>

### 📊 日志调试

服务器会输出详细的日志信息，包括：
- ✅ 请求处理状态
- ✅ 微信操作结果
- ✅ 错误信息和堆栈跟踪

## 🚧 开发和扩展

### ➕ 添加新工具

1. 在 `src/mcp_server.py` 中使用 `@mcp.tool()` 装饰器注册新工具函数
2. 如需新的微信操作，在对应的 Mixin 模块中实现底层功能（GUI 操作在 `gui_operations.py`，窗口查找在 `window_finder.py`）
3. 更新配置文件和文档

### 🌐 支持其他平台

当前版本仅支持Windows系统。要支持其他平台，需要：
- 替换win32gui相关代码
- 适配不同系统的窗口管理
- 调整键盘快捷键映射

### 🗺️ 后续开发计划

- [x] ~~智能输入框定位~~ ✅ **已完成**
- [x] ~~剪贴板输入技术~~ ✅ **已完成**
- [x] ~~多种发送方式支持~~ ✅ **已完成**
- [x] ~~输入法兼容性问题~~ ✅ **已完成**
- [x] ~~HTTP RESTful API~~ ✅ **已完成**
- [x] ~~防封号保护系统~~ ✅ **已完成**
- [x] ~~本地持久化消息队列~~ ✅ **已完成**
- [ ] 支持macOS和Linux系统
- [ ] 增加更多微信操作功能（如图片、视频等）


## 💖 支持我们

如果您觉得这个项目对您有帮助，请考虑：

- ⭐ 给项目点个Star
- 🔄 分享给您的朋友
- 💰 考虑捐赠以支持项目维护和发展

### 💳 捐赠方式

如果您愿意支持项目的持续发展，可以通过以下方式进行捐赠：

<div align="center">

**支付宝收款码**

<img src="支持我们/1.jpg" alt="支付宝收款码" width="200"/>

**微信赞赏码**

<img src="支持我们/2.jpg" alt="微信赞赏码" width="200"/>

</div>

您的每一份支持都是我们持续改进和维护项目的动力！❤️

---

## ⚠️ 重要免责声明

> **🚨 严重警告**
> 
> 本项目涉及微信自动化操作，存在重大风险。使用前请充分评估风险并自行承担所有后果。

<details>
<summary>📋 点击查看完整免责声明</summary>

### 🏷️ 项目性质声明
1. **纯技术研究**: 本项目仅为技术研究和学习目的而创建，用于演示MCP协议的实现
2. **非官方工具**: 本项目与腾讯公司、微信官方无任何关联，未经微信官方授权或认可
3. **实验性质**: 本项目为实验性代码，不保证稳定性、安全性或可靠性

### ⚠️ 使用风险警告
1. **账号风险**: 使用任何微信自动化工具都可能导致账号被限制、封禁或永久注销
2. **数据风险**: 可能导致聊天记录丢失、联系人信息泄露或其他数据安全问题
3. **系统风险**: 可能对您的计算机系统造成不稳定或安全漏洞
4. **法律风险**: 在某些地区或情况下，使用此类工具可能违反相关法律法规
5. **隐私风险**: 可能涉及个人隐私信息的处理和传输

### 📱 微信相关免责
1. **违反服务条款**: 使用本项目可能违反微信用户服务协议和使用条款
2. **功能失效**: 微信更新可能随时导致本项目功能完全失效
3. **官方制裁**: 腾讯公司有权对使用自动化工具的账号采取任何措施
4. **无官方支持**: 微信官方不会为使用本项目产生的任何问题提供技术支持

### 🔴 完全免责条款

**开发者、贡献者、分发者在任何情况下均不承担任何责任，包括但不限于：**

#### 直接责任免除
- 微信账号被封禁、限制或注销
- 个人数据丢失、泄露或被滥用
- 计算机系统损坏或数据损坏
- 消息发送错误或失败
- 隐私信息泄露
- 经济损失或商业损失

#### 间接责任免除
- 因使用本项目导致的任何第三方损失
- 因项目缺陷导致的连带损失
- 因违反法律法规产生的法律后果
- 因违反平台规则产生的处罚
- 任何形式的精神损失或名誉损失

#### 法律责任免除
- 违反当地法律法规的责任
- 违反微信服务条款的责任
- 侵犯他人权益的责任
- 数据保护法规违规的责任
- 任何民事、刑事或行政责任

### 📋 使用条件
**使用本项目即表示您：**
1. 已完全理解并接受上述所有风险和免责条款
2. 同意自行承担使用本项目的所有风险和后果
3. 承诺不会因使用本项目产生的任何问题追究开发者责任
4. 理解开发者有权随时停止项目维护而无需承担任何责任
5. 同意在发生任何争议时，开发者均不承担任何责任

### ⛔ 禁止使用声明
**以下情况严禁使用本项目：**
- 批量发送广告或垃圾信息
- 骚扰他人或恶意使用
- 违反当地法律法规的用途
- 侵犯他人权益的行为
- 违反微信服务条款的行为

### 💼 商业使用警告
**虽然MIT许可证允许商业使用，但我们强烈建议：**
- 商业使用前请充分评估法律风险
- 确保遵守所在地区的相关法律法规
- 遵守微信平台的商业使用政策
- 建议咨询法律专业人士的意见
- 商业使用产生的所有风险由使用者自行承担

**如果您不同意上述任何条款，请立即停止下载、安装或使用本项目。继续使用即视为完全同意并接受所有免责条款。**

</details>

---

## 📄 许可证

本项目采用 **MIT License** 开源许可证。

<details>
<summary>📋 许可证详情</summary>

MIT许可证允许：
- ✅ **商业使用** (⚠️ 需评估风险)
- ✅ 修改代码
- ✅ 分发代码
- ✅ 私人使用

但需要：
- 📋 保留版权声明
- 📋 保留许可证声明

**重要提醒**: 
- ✅ MIT许可证在法律上允许商业使用
- ⚠️ 但商业使用微信自动化工具存在较高风险
- 🔍 建议商业使用前咨询法律专业人士
- 📋 所有商业使用风险由使用者自行承担

</details>

## 🤝 贡献

我们欢迎所有形式的贡献！

### 🐛 报告问题
- 使用 [Issues](https://github.com/1052666/WeChat-MCP-Server/issues) 报告bug
- 提供详细的错误信息和复现步骤

## 📞 联系我们

如果您有任何问题、建议或合作意向，欢迎通过以下方式联系我们：

- **微信号**: 13115979196
- **GitHub**: [提交Issue](https://github.com/1052666/WeChat-MCP-Server/issues)

我们会尽快回复您的咨询！

### 💡 功能建议
- 在 [Issues](https://github.com/1052666/WeChat-MCP-Server/issues) 中提出新功能建议
- 详细描述功能需求和使用场景

### 🔧 代码贡献
1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📈 项目统计

### ⭐ Star 增长趋势

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=1052666/WeChat-MCP-Server&type=Date)](https://star-history.com/#1052666/WeChat-MCP-Server&Date)

</div>

### 📊 项目数据

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/1052666/WeChat-MCP-Server?style=social)
![GitHub forks](https://img.shields.io/github/forks/1052666/WeChat-MCP-Server?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/1052666/WeChat-MCP-Server?style=social)

![GitHub issues](https://img.shields.io/github/issues/1052666/WeChat-MCP-Server)
![GitHub pull requests](https://img.shields.io/github/issues-pr/1052666/WeChat-MCP-Server)
![GitHub last commit](https://img.shields.io/github/last-commit/1052666/WeChat-MCP-Server)

![GitHub repo size](https://img.shields.io/github/repo-size/1052666/WeChat-MCP-Server)
![GitHub code size](https://img.shields.io/github/languages/code-size/1052666/WeChat-MCP-Server)
![GitHub top language](https://img.shields.io/github/languages/top/1052666/WeChat-MCP-Server)

</div>

---

<div align="center">

**感谢您使用 WeChat MCP Server！**

如果这个项目对您有帮助，请考虑给我们一个 ⭐

[回到顶部](#weChat-mcp-server)

</div>
