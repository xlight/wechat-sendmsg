# 快速开始指南

**GitHub地址：https://github.com/xlight/wechat-sendmsg**

## 目录

- [环境准备](#环境准备)
- [MCP 服务器部署（stdio 模式）](#mcp-服务器部署stdio-模式)
- [统一服务器部署（streamable-http 模式）](#统一服务器部署streamable-http-模式)
- [系统托盘模式部署](#系统托盘模式部署)
- [编译构建（独立 exe）](#编译构建独立-exe)

---

## 环境准备

1. **确保 Python 环境**
   ```bash
   python --version  # 需要 Python 3.10+（MCP SDK 要求）
   ```

2. **安装依赖包**
   ```bash
   cd wechat-sendmsg
   pip install -r requirements.txt
   ```

3. **启动微信并登录**
   - 打开微信客户端（需要 4.0 及以上 NT 框架版本）
   - 确保已登录
   - 保持微信窗口可见（最小化到托盘时会自动恢复）

4. **（推荐）配置微信快捷键**
   - 打开微信「设置 → 快捷键」
   - 设置「打开微信」快捷键为 `Ctrl+Alt+W`（与 `data/config.json` 中 `wechat_hotkey` 一致）
   - 配置后系统会优先通过快捷键激活微信窗口，未配置时自动回退到 Win32 API 方式

---

## MCP 服务器部署（stdio 模式）

stdio 模式通过标准输入/输出与 AI 助手通信，适合集成到 Claude Desktop 等工具。

### 步骤1: 测试 MCP 服务器

运行示例客户端验证功能：

```bash
cd examples
python mcp_client_example.py
```

如果看到类似输出，说明服务器工作正常：
```
正在以 stdio 模式启动 MCP 服务器...
已连接到服务器: wechat-sendmsg v2.0.0
协议版本: 2024-11-05
可用工具 (6 个):
  - send_wechat_message: 向微信联系人或群组发送文本消息。
  - schedule_wechat_message: 安排在延迟后发送微信消息。
  - get_queue_status: 查看消息队列状态概览。
  - get_message_detail: 查看指定消息的详细信息。
  - cancel_queue_message: 取消待发送的消息。
  - retry_queue_message: 重试失败的消息。
```

### 步骤2: 配置 AI 助手

#### 对于 Claude Desktop:

1. 打开 Claude Desktop 配置文件：
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. 添加 MCP 服务器配置：
   ```json
   {
     "mcpServers": {
       "wechat": {
         "command": "python",
         "args": ["C:/path/to/wechat-sendmsg/src/mcp_server.py"],
         "env": {}
       }
     }
   }
   ```

3. 重启 Claude Desktop

#### 对于其他 AI 助手:

参考各自的 MCP 配置文档，使用相同的服务器路径和参数。

### 步骤3: 开始使用

在 AI 助手中尝试以下命令：

1. **发送简单消息**
   ```
   "帮我给文件传输助手发个消息：Hello from AI!"
   ```

2. **发送定时消息**
   ```
   "10秒后给文件传输助手发消息：这是一条定时消息"
   ```

3. **发送给特定联系人**
   ```
   "给张三发微信：明天的会议改到下午3点"
   ```

---

## 统一服务器部署（streamable-http 模式）

streamable-http 模式在同一个端口上同时提供 MCP 端点和 HTTP API，适合自动化脚本和外部系统集成。

### 步骤1: 配置服务器

编辑 `data/config.json`（首次运行会自动创建）：

```json
{
  "http_port": 8765,
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
  "max_daily_runtime_hours": 8.0
}
```

### 步骤2: 启动服务器

```bash
python src/mcp_server.py --transport streamable-http
```

可选参数：
```bash
# 指定端口（默认读取 data/config.json 中的 http_port）
python src/mcp_server.py --transport streamable-http --port 8765

# 指定监听地址
python src/mcp_server.py --transport streamable-http --host 127.0.0.1
```

启动后你会看到：
```
以 streamable-http 模式启动统一服务器: http://0.0.0.0:8765
可用端点:
  MCP:   http://0.0.0.0:8765/mcp
  API:   http://0.0.0.0:8765/api/v1/...
  Queue: http://0.0.0.0:8765/queue
  Web:   http://0.0.0.0:8765/
```

### 步骤3: 测试

1. **通过 MCP 客户端测试**
   ```bash
   cd examples
   python mcp_client_example.py --transport streamable-http --url http://localhost:8765/mcp
   ```

2. **通过 HTTP API 发送消息**
   ```bash
   # 队列模式（默认，异步入队）
   curl -X POST http://localhost:8765/api/v1/messages/send \
     -H "Content-Type: application/json" \
     -d '{"contact_name": "文件传输助手", "message": "Hello from HTTP API!"}'

   # 同步模式（立即发送）
   curl -X POST http://localhost:8765/api/v1/messages/send \
     -H "Content-Type: application/json" \
     -d '{"contact_name": "文件传输助手", "message": "紧急消息", "mode": "sync"}'
   ```

3. **查询状态**
   ```bash
   curl http://localhost:8765/api/v1/status
   ```

4. **查询防封号统计**
   ```bash
   curl http://localhost:8765/api/v1/anti-ban/stats
   ```

5. **查询队列状态**
   ```bash
   curl http://localhost:8765/api/v1/queue/status
   ```

6. **打开队列管理页面**

   在浏览器中访问 `http://localhost:8765/queue`

### 可用端点一览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/mcp` | POST | MCP Streamable HTTP 端点 |
| `/api/v1/messages/send` | POST | 发送消息（支持 queue/sync 模式） |
| `/api/v1/status` | GET | 查询微信状态 |
| `/api/v1/queue/status` | GET | 队列状态概览 |
| `/api/v1/queue/messages` | GET | 队列消息列表（支持 status/limit/offset 查询） |
| `/api/v1/queue/messages/{id}` | GET | 消息详情 |
| `/api/v1/queue/messages/{id}/cancel` | POST | 取消待发送消息 |
| `/api/v1/queue/messages/{id}/retry` | POST | 重试失败消息 |
| `/api/v1/anti-ban/stats` | GET | 防封号统计 |
| `/api/v1/anti-ban/config` | GET | 防封号配置 |
| `/` | GET | Web 首页 |
| `/test` | GET | 测试页面 |
| `/queue` | GET | 队列管理页面 |
| `/static/*` | GET | 静态文件 |

---

## 系统托盘模式部署

系统托盘模式将服务器作为后台应用运行，通过系统托盘图标进行管理，适合长期运行场景。

### 启动托盘模式

```bash
python src/mcp_server.py --transport streamable-http --systray
```

启动后：
- 系统托盘区域会出现微信 MCP 服务器图标
- HTTP API 和 MCP 端点在后台正常运行
- 右键点击托盘图标可查看状态、打开管理页面或退出

### 托盘菜单功能

| 菜单项 | 说明 |
|--------|------|
| 微信 MCP 服务器 - 运行中 | 状态信息（灰色，不可点击） |
| 端口: 8765 | 当前监听端口（灰色，不可点击） |
| 打开管理页面 | 在浏览器中打开 Web 管理界面 |
| 退出 | 优雅关闭服务器并退出程序 |

---

## 编译构建（独立 exe）

通过 Nuitka 将项目编译为独立的 `.exe` 可执行文件，无需 Python 环境即可运行。

### 步骤1: 安装编译工具

```bash
# 安装 Nuitka
pip install nuitka

# 确保有 C 编译器（推荐 MSVC，安装 Visual Studio Build Tools）
```

### 步骤2: 执行编译

```bash
# 编译为单文件 exe（默认）
python build.py

# 或编译为目录模式（速度快，适合调试）
python build.py --standalone
```

编译完成后，输出文件位于 `dist/` 目录。

### 步骤3: 运行编译版本

```bash
# 直接双击 exe 或命令行启动
dist/wechat-sendmsg.exe
```

编译后的 exe 会自动以系统托盘模式运行，使用 streamable-http 传输模式。配置文件和数据库存放在 exe 同级的 `data/` 目录中。

---

## 常见问题快速解决

#### 找不到微信窗口
- 确保微信已启动并登录
- 检查微信窗口是否可见
- 微信最小化到托盘时系统会自动恢复
- 确保微信版本为 4.0 及以上 NT 框架版本

#### 联系人找不到
- 确保联系人名称完全正确
- 先手动在微信中搜索一次该联系人
- 使用"文件传输助手"进行测试

#### MCP 连接失败
- 检查 Python 版本是否为 3.10+
- 验证依赖包是否安装完整（`pip install -r requirements.txt`）
- 查看 AI 助手的错误日志

## 高级配置

### 自定义快捷键
在 `data/config.json` 中配置微信激活快捷键：
```json
{
  "wechat_hotkey": "ctrl+alt+w"
}
```
需要在微信「设置 → 快捷键」中配置相同的组合键。

### 日志级别调整
修改 `src/mcp_server.py` 中的日志级别：
```python
logging.basicConfig(level=logging.DEBUG)  # 更详细的日志
```

### 防封号配置
详见 [AVOID_BAN.md](AVOID_BAN.md)。

---

### 下一步

- 阅读完整的 [README.md](../README.md) 了解更多功能
- 查看 [HTTP API 文档](../README.md#-http-api) 了解所有端点
- 探索防封号保护系统的高级功能

### 获得帮助

如果遇到问题：
1. 检查日志输出（启用 DEBUG 级别查看详细信息）
2. 查看 README 中的常见问题解答
3. 提交 Issue 到项目仓库