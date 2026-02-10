# 快速开始指南

## 目录

- [MCP 服务器快速部署](#mcp-服务器快速部署)
- [自动回复功能快速部署](#自动回复功能快速部署)

---

## MCP 服务器快速部署

### 步骤1: 环境准备

1. **确保Python环境**
   ```bash
   python --version  # 需要Python 3.7+
   ```

2. **安装依赖包**
   ```bash
   cd WeChat-MCP-Server
   pip install -r requirements.txt
   ```

3. **启动微信并登录**
   - 打开微信客户端
   - 确保已登录
   - 保持微信窗口可见

### 步骤2: 测试MCP服务器

运行测试脚本验证功能：

```bash
cd examples
python mcp_client_example.py
```

如果看到类似输出，说明服务器工作正常：
```
MCP Server started
Initialize response: {'jsonrpc': '2.0', 'result': {...}, 'id': 1}
Tools list: {'jsonrpc': '2.0', 'result': {'tools': [...]}, 'id': 2}
```

### 步骤3: 配置AI助手

#### 对于Claude Desktop:

1. 打开Claude Desktop配置文件：
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. 添加MCP服务器配置：
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

3. 重启Claude Desktop

#### 对于其他AI助手:

参考各自的MCP配置文档，使用相同的服务器路径和参数。

### 步骤4: 开始使用

在AI助手中尝试以下命令：

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

### 常见问题快速解决

#### 问题1: 找不到微信窗口
**解决方案:**
- 确保微信已启动
- 检查微信窗口是否可见
- 尝试点击微信窗口使其获得焦点

#### 问题2: 联系人找不到
**解决方案:**
- 确保联系人名称完全正确
- 先手动搜索一次该联系人
- 使用"文件传输助手"进行测试

#### 问题3: MCP连接失败
**解决方案:**
- 检查Python路径是否正确
- 验证依赖包是否安装完整
- 查看AI助手的错误日志

### 高级配置

#### 自定义快捷键
如果微信使用了不同的快捷键，可以修改 `wechat_controller.py` 中的快捷键设置。

#### 日志级别调整
在 `mcp_server.py` 中修改日志级别：
```python
logging.basicConfig(level=logging.DEBUG)  # 更详细的日志
```

#### 添加更多联系人
建议在微信中将常用联系人置顶，这样搜索会更快更准确。

---

## 自动回复功能快速部署

### 功能介绍

自动回复功能可以：
- 监听指定微信群聊中的 `@你的昵称` 提及
- 将消息发送给 AI（支持 OpenAI 兼容 API）
- 自动将 AI 回复发送到群聊
- 提供 HTTP API 用于外部集成

### 步骤1: 配置自动回复

1. **编辑配置文件**
   
   编辑项目根目录的 `config.json`（首次运行会自动创建）：
   
   ```json
   {
     "http_port": 8080,
     "poll_interval": 5,
     "monitored_groups": ["你要监听的群聊名称"],
     "bot_name": "你的微信昵称",
     "ai_base_url": "https://api.openai.com",
     "ai_api_key": "sk-your-api-key-here",
     "ai_model": "gpt-3.5-turbo",
     "system_prompt": "你是一个友好的助手，请简洁回答问题。",
     "max_reply_chars": 1000,
     "ai_timeout": 30,
     "rate_limit_per_minute": 10
   }
   ```

2. **配置项说明**
   
   | 配置项 | 必填 | 说明 |
   |--------|------|------|
   | `monitored_groups` | ✅ | 要监听的群聊名称列表（必须精确匹配） |
   | `bot_name` | ✅ | 你的微信昵称（用于检测 @提及） |
   | `ai_base_url` | ✅ | OpenAI 兼容 API 地址 |
   | `ai_api_key` | ✅ | API 密钥 |
   | `ai_model` | - | AI 模型名称（默认 gpt-3.5-turbo） |
   | `poll_interval` | - | 轮询间隔秒数（默认 5 秒） |
   | `rate_limit_per_minute` | - | 每分钟最大 AI 调用次数（默认 10） |

### 步骤2: 启动自动回复服务

```bash
python src/auto_reply.py
```

启动后你会看到：
```
2026-02-10 15:30:00 - 配置已加载: config.json
2026-02-10 15:30:00 - HTTP 服务器启动在 0.0.0.0:8080
2026-02-10 15:30:00 - 消息监听器已启动，监听群聊: ['测试群']
2026-02-10 15:30:00 - 自动回复服务运行中...
```

### 步骤3: 测试自动回复

1. **在微信群聊中测试**
   
   在配置的群聊中发送消息：
   ```
   @你的微信昵称 什么是 MCP 协议？
   ```
   
   机器人会自动调用 AI 分析并回复。

2. **通过 HTTP API 发送消息**
   
   ```bash
   curl -X POST http://localhost:8080/api/v1/messages/send \
     -H "Content-Type: application/json" \
     -d '{"contact_name": "文件传输助手", "message": "Hello from API!"}'
   ```

3. **查询服务状态**
   
   ```bash
   curl http://localhost:8080/api/v1/status
   ```

### 步骤4: 停止服务

按 `Ctrl+C` 优雅停止服务：
```
^C收到停止信号，正在关闭服务...
消息监听器已停止
HTTP 服务器已停止
自动回复服务已完全关闭
```

### 常见问题快速解决

#### 问题1: 提示 "AI 服务未配置"
**解决方案:**
- 检查 `config.json` 中 `ai_api_key` 和 `ai_base_url` 是否已填写
- 确保 API 密钥有效且未过期
- 验证 `ai_base_url` 格式正确（如 `https://api.openai.com`）

#### 问题2: 无法检测到 @ 提及
**解决方案:**
- 确保 `bot_name` 与你的微信昵称完全一致
- 检查 `monitored_groups` 中的群聊名称是否精确匹配
- 确保微信窗口可见且未最小化
- 在群聊中手动打开一次聊天窗口

#### 问题3: HTTP API 无法访问
**解决方案:**
- 检查 `http_port` 是否被其他程序占用
- 确认防火墙未阻止该端口
- 验证服务是否成功启动（查看日志）

#### 问题4: AI 响应超时
**解决方案:**
- 增加 `ai_timeout` 配置值（如改为 60 秒）
- 检查网络连接是否正常
- 验证 AI 服务 API 是否可用

#### 问题5: 触发速率限制
**解决方案:**
- 调整 `rate_limit_per_minute` 配置
- 等待 1 分钟后限制会自动重置
- 检查是否有恶意刷屏行为

### 运行测试

运行单元测试验证功能：

```bash
python test_auto_reply.py
```

成功输出：
```
...............
----------------------------------------------------------------------
Ran 15 tests in 2.5s

OK
```

### HTTP API 参考

#### 发送消息
```bash
POST /api/v1/messages/send
Content-Type: application/json

{
  "contact_name": "联系人名称",
  "message": "消息内容"
}
```

#### 查询状态
```bash
GET /api/v1/status
```

#### 查询配置
```bash
GET /api/v1/config
```

#### 更新配置
```bash
PUT /api/v1/config
Content-Type: application/json

{
  "poll_interval": 10,
  "rate_limit_per_minute": 20
}
```

### 高级配置

#### 自定义系统提示词

编辑 `config.json`：
```json
{
  "system_prompt": "你是一个技术专家，擅长解答编程问题。请用简洁专业的语言回答。"
}
```

#### 限制回复长度

```json
{
  "max_reply_chars": 500
}
```

超出长度的回复会被截断并附加 "...（回复已截断）"。

#### 监听多个群聊

```json
{
  "monitored_groups": ["技术交流群", "项目讨论群", "客服支持群"]
}
```

#### 调整轮询频率

```json
{
  "poll_interval": 3
}
```

**注意**: 过短的轮询间隔可能增加系统负载，建议不低于 3 秒。

---

### 下一步

- 阅读完整的 [README.md](../README.md) 了解更多功能
- 查看 README 中的 [自动回复功能章节](../README.md#-自动回复功能) 了解详细文档
- 探索 HTTP API 进行自定义集成

### 获得帮助

如果遇到问题：
1. 检查日志输出（启用 DEBUG 级别查看详细信息）
2. 运行测试脚本 `python test_auto_reply.py` 验证环境
3. 查看 README 中的常见问题解答
4. 提交 Issue 到项目仓库