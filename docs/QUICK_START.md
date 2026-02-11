# 快速开始指南

## 目录

- [MCP 服务器快速部署](#mcp-服务器快速部署)
- [HTTP API 服务器快速部署](#http-api-服务器快速部署)

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

## HTTP API 服务器快速部署

### 功能介绍

HTTP API 服务器提供 RESTful 接口，用于：
- 发送文本消息到微信联系人或群聊
- 查询微信状态
- 查询防封号统计和配置

### 步骤1: 配置服务器

编辑项目根目录的 `config.json`（首次运行会自动创建）：

```json
{
  "http_port": 8080,
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
python src/http_server.py
```

启动后你会看到：
```
2026-02-11 15:30:00 - HTTP 服务器已启动: http://0.0.0.0:8080
2026-02-11 15:30:00 - 可用端点:
2026-02-11 15:30:00 -   POST /api/v1/messages/send - 发送消息
2026-02-11 15:30:00 -   GET  /api/v1/status - 查询状态
2026-02-11 15:30:00 -   GET  /api/v1/anti-ban/stats - 防封号统计
2026-02-11 15:30:00 -   GET  /api/v1/anti-ban/config - 防封号配置
```

### 步骤3: 测试 API

1. **发送消息**
   
   ```bash
   curl -X POST http://localhost:8080/api/v1/messages/send \
     -H "Content-Type: application/json" \
     -d '{"contact_name": "文件传输助手", "message": "Hello from HTTP API!"}'
   ```
   
   响应：
   ```json
   {
     "ok": true,
     "message": "Message sent successfully"
   }
   ```

2. **查询状态**
   
   ```bash
   curl http://localhost:8080/api/v1/status
   ```
   
   响应：
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

3. **查询防封号统计**
   
   ```bash
   curl http://localhost:8080/api/v1/anti-ban/stats
   ```

### 步骤4: 停止服务

按 `Ctrl+C` 停止服务：
```
^C收到停止信号，正在关闭服务器...
HTTP 服务器已关闭
```

### 常见问题快速解决

#### 问题1: HTTP API 无法访问
**解决方案:**
- 检查 `http_port` 是否被其他程序占用
- 确认防火墙未阻止该端口
- 验证服务是否成功启动（查看日志）

#### 问题2: 找不到微信窗口
**解决方案:**
- 确保微信已启动并登录
- 检查微信窗口是否可见（不能最小化）
- 尝试点击微信窗口使其获得焦点

#### 问题3: 联系人找不到
**解决方案:**
- 确保联系人名称完全正确
- 先手动在微信中搜索一次该联系人
- 使用"文件传输助手"进行测试

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

#### 查询防封号统计
```bash
GET /api/v1/anti-ban/stats
```

#### 查询防封号配置
```bash
GET /api/v1/anti-ban/config
```

### 高级配置

#### 调整速率限制

编辑 `config.json`：
```json
{
  "rate_limit_per_minute": 20,
  "rate_limit_per_hour": 50,
  "rate_limit_per_day": 200
}
```

#### 调整工作时间

```json
{
  "work_hours_start": 8,
  "work_hours_end": 23,
  "work_days": [0, 1, 2, 3, 4, 5, 6],
  "max_daily_runtime_hours": 12.0
}
```

**注意**: 更多防封号配置说明请参考 [docs/AVOID_BAN.md](../docs/AVOID_BAN.md)。

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