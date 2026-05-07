# HTTP API 与 MCP Tools 文档

**GitHub地址：https://github.com/xlight/wechat-sendmsg**

本文档详细说明 WeChat SendMsg 项目提供的所有 HTTP API 端点和 MCP Tools，包括请求格式、响应格式、使用示例和注意事项。

---

## 📋 目录

- [服务启动](#服务启动)
- [HTTP API 端点总览](#http-api-端点总览)
- [HTTP API 详解](#http-api-详解)
  - [消息发送](#1-post-apiv1messagessend)
  - [微信状态](#2-get-apiv1status)
  - [队列状态概览](#3-get-apiv1queuestatus)
  - [队列消息列表](#4-get-apiv1queuemessages)
  - [消息详情](#5-get-apiv1queuemessagesid)
  - [取消消息](#6-post-apiv1queuemessagesidcancel)
  - [重试消息](#7-post-apiv1queuemessagesidretry)
  - [防封号统计](#8-get-apiv1anti-banstats)
  - [防封号配置](#9-get-apiv1anti-banconfig)
  - [静态页面](#10-静态页面)
- [MCP Tools 总览](#mcp-tools-总览)
- [MCP Tools 详解](#mcp-tools-详解)
  - [send_wechat_message](#1-send_wechat_message)
  - [schedule_wechat_message](#2-schedule_wechat_message)
  - [get_queue_status](#3-get_queue_status)
  - [get_message_detail](#4-get_message_detail)
  - [cancel_queue_message](#5-cancel_queue_message)
  - [retry_queue_message](#6-retry_queue_message)
- [错误码说明](#错误码说明)
- [消息状态说明](#消息状态说明)

---

## 服务启动

### 启动命令

```bash
# streamable-http 模式（同时提供 HTTP API 和 MCP 端点）
python src/mcp_server.py --transport streamable-http --port 8765

# 系统托盘模式（后台运行）
python src/mcp_server.py --transport streamable-http --systray

# stdio 模式（仅 MCP，适合 AI 助手集成）
python src/mcp_server.py
```

### 可用端点

| 路径 | 类型 |
|------|------|
| `http://host:port/mcp` | MCP Streamable HTTP 端点 |
| `http://host:port/api/v1/*` | REST API 端点 |
| `http://host:port/` | Web 首页 |
| `http://host:port/test` | 测试页面 |
| `http://host:port/queue` | 队列管理页面 |
| `http://host:port/static/*` | 静态资源 |

---

## HTTP API 端点总览

| 端点 | 方法 | 说明 | 需要 Body |
|------|------|------|-----------|
| `/api/v1/messages/send` | POST | 发送消息（支持 queue/sync 模式） | ✅ |
| `/api/v1/status` | GET | 查询微信运行状态 | ❌ |
| `/api/v1/queue/status` | GET | 消息队列状态概览 | ❌ |
| `/api/v1/queue/messages` | GET | 消息列表（支持分页和状态筛选） | ❌ |
| `/api/v1/queue/messages/{id}` | GET | 单条消息详情 | ❌ |
| `/api/v1/queue/messages/{id}/cancel` | POST | 取消待发送消息 | ❌ |
| `/api/v1/queue/messages/{id}/retry` | POST | 重试失败消息 | ❌ |
| `/api/v1/anti-ban/stats` | GET | 防封号统计信息 | ❌ |
| `/api/v1/anti-ban/config` | GET | 防封号配置信息 | ❌ |

### 通用响应格式

所有 API 端点统一返回 JSON，基本格式为：

```json
{
  "ok": true,
  ...
}
```

或失败时：

```json
{
  "ok": false,
  "error": "错误描述"
}
```

---

## HTTP API 详解

### 1. POST `/api/v1/messages/send`

发送微信消息给指定联系人或群组。

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `contact_name` | string | ✅ | - | 联系人或群组名称 |
| `message` | string | ✅ | - | 消息内容 |
| `mode` | string | ❌ | `"queue"` | 发送模式：`queue`（异步入队）或 `sync`（同步立即发送） |
| `priority` | integer | ❌ | `5` | 消息优先级，0-10，数值越小优先级越高 |
| `delay_seconds` | number | ❌ | `0` | 延迟发送秒数（仅 queue 模式有效） |

#### 请求示例

**队列模式（默认）：**

```bash
curl -X POST http://localhost:8765/api/v1/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "contact_name": "文件传输助手",
    "message": "你好，这是一条测试消息！"
  }'
```

**同步模式（立即发送）：**

```bash
curl -X POST http://localhost:8765/api/v1/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "contact_name": "文件传输助手",
    "message": "紧急消息，请立即发送",
    "mode": "sync"
  }'
```

**延迟发送：**

```bash
curl -X POST http://localhost:8765/api/v1/messages/send \
  -H "Content-Type: application/json" \
  -d '{
    "contact_name": "文件传输助手",
    "message": "这是一条定时消息",
    "delay_seconds": 60,
    "priority": 1
  }'
```

#### 响应示例

**成功（queue 模式）：**

```json
{
  "ok": true,
  "mode": "queue",
  "message_id": 42,
  "message": "消息已加入发送队列: id=42"
}
```

**成功（sync 模式）：**

```json
{
  "ok": true,
  "mode": "sync",
  "message": "消息已成功发送（同步模式）"
}
```

**失败：**

```json
{
  "ok": false,
  "mode": "sync",
  "error": "消息发送失败",
  "details": {
    "ok": false,
    "stage": "find_window",
    "reason": "微信窗口未找到"
  }
}
```

**参数校验失败：**

```json
{
  "ok": false,
  "error": "缺少必填参数: contact_name"
}
```

#### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（队列未初始化） |

---

### 2. GET `/api/v1/status`

查询微信运行状态。

#### 请求示例

```bash
curl http://localhost:8765/api/v1/status
```

#### 响应示例

```json
{
  "ok": true,
  "wechat_status": {
    "found": true,
    "running": true,
    "process_count": 1
  }
}
```

---

### 3. GET `/api/v1/queue/status`

获取消息队列的整体状态概览。

#### 请求示例

```bash
curl http://localhost:8765/api/v1/queue/status
```

#### 响应示例

```json
{
  "ok": true,
  "worker_running": true,
  "stats": {
    "pending": 5,
    "processing": 1,
    "completed": 42,
    "failed": 3,
    "cancelled": 2,
    "total": 53
  }
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `worker_running` | boolean | 后台 Worker 是否运行中 |
| `stats.pending` | integer | 待发送消息数 |
| `stats.processing` | integer | 正在发送的消息数 |
| `stats.completed` | integer | 已成功发送的消息数 |
| `stats.failed` | integer | 发送失败的消息数 |
| `stats.cancelled` | integer | 已取消的消息数 |
| `stats.total` | integer | 消息总数 |

---

### 4. GET `/api/v1/queue/messages`

获取消息列表，支持分页和状态筛选。

#### 查询参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `status` | string | ❌ | - | 状态筛选：`pending`、`processing`、`completed`、`failed`、`cancelled` |
| `limit` | integer | ❌ | `20` | 每页数量，最大 100 |
| `offset` | integer | ❌ | `0` | 偏移量 |

#### 请求示例

```bash
# 获取全部消息（默认 20 条）
curl http://localhost:8765/api/v1/queue/messages

# 获取失败消息
curl "http://localhost:8765/api/v1/queue/messages?status=failed"

# 分页：第 2 页，每页 50 条
curl "http://localhost:8765/api/v1/queue/messages?limit=50&offset=50"
```

#### 响应示例

```json
{
  "ok": true,
  "messages": [
    {
      "id": 42,
      "contact_name": "文件传输助手",
      "message": "你好",
      "status": "completed",
      "mode": "queue",
      "priority": 5,
      "retry_count": 0,
      "max_retries": 3,
      "error_message": null,
      "scheduled_at": "2026-05-07T10:00:00",
      "created_at": "2026-05-07T09:59:50",
      "updated_at": "2026-05-07T10:00:02"
    }
  ],
  "total": 53,
  "limit": 20,
  "offset": 0
}
```

---

### 5. GET `/api/v1/queue/messages/{id}`

获取单条消息的详细信息。

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 消息 ID |

#### 请求示例

```bash
curl http://localhost:8765/api/v1/queue/messages/42
```

#### 响应示例

**成功：**

```json
{
  "ok": true,
  "message": {
    "id": 42,
    "contact_name": "文件传输助手",
    "message": "你好，世界！",
    "status": "completed",
    "mode": "queue",
    "priority": 5,
    "retry_count": 0,
    "max_retries": 3,
    "error_message": null,
    "scheduled_at": "2026-05-07T10:00:00",
    "created_at": "2026-05-07T09:59:50",
    "updated_at": "2026-05-07T10:00:02"
  }
}
```

**消息不存在：**

```json
{
  "ok": false,
  "error": "消息不存在: id=999"
}
```

#### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 查询成功 |
| 404 | 消息不存在 |
| 503 | 服务不可用 |

---

### 6. POST `/api/v1/queue/messages/{id}/cancel`

取消一条待发送的消息。

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 消息 ID |

#### 说明

- 仅能取消状态为 `pending` 的消息
- 正在发送中（`processing`）或已完成的消息无法取消

#### 请求示例

```bash
curl -X POST http://localhost:8765/api/v1/queue/messages/42/cancel
```

#### 响应示例

**成功：**

```json
{
  "ok": true,
  "message": "消息已取消: id=42"
}
```

**失败：**

```json
{
  "ok": false,
  "error": "只能取消待发送状态的消息，当前状态: completed"
}
```

---

### 7. POST `/api/v1/queue/messages/{id}/retry`

手动重试一条发送失败的消息。

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | integer | 消息 ID |

#### 说明

- 仅能重试状态为 `failed` 的消息
- 重试后消息状态重置为 `pending`，重试次数清零，错误信息清除

#### 请求示例

```bash
curl -X POST http://localhost:8765/api/v1/queue/messages/42/retry
```

#### 响应示例

**成功：**

```json
{
  "ok": true,
  "message": "消息已重新加入队列: id=42"
}
```

**失败：**

```json
{
  "ok": false,
  "error": "只能重试失败状态的消息，当前状态: pending"
}
```

---

### 8. GET `/api/v1/anti-ban/stats`

获取防封号系统的实时统计信息。

> **注意：** 需要防封号模块已加载（`src/anti_ban/` 目录存在），否则返回 503。

#### 请求示例

```bash
curl http://localhost:8765/api/v1/anti-ban/stats
```

#### 响应示例

```json
{
  "ok": true,
  "rate_limiter": {
    "messages_last_minute": 3,
    "messages_last_hour": 15,
    "messages_today": 42
  },
  "work_time": {
    "is_work_time": true,
    "current_hour": 14,
    "work_hours": "9-22",
    "current_day": 2,
    "work_days": [0, 1, 2, 3, 4]
  },
  "runtime": {
    "current_runtime_seconds": 18000,
    "current_runtime_hours": 5.0,
    "max_daily_hours": 8,
    "remaining_hours": 3.0
  }
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `rate_limiter.messages_last_minute` | integer | 过去 1 分钟发送数量 |
| `rate_limiter.messages_last_hour` | integer | 过去 1 小时发送数量 |
| `rate_limiter.messages_today` | integer | 今天发送数量 |
| `work_time.is_work_time` | boolean | 当前是否在工作时间内 |
| `work_time.current_hour` | integer | 当前小时 |
| `work_time.work_hours` | string | 配置的工作时段 |
| `work_time.current_day` | integer | 当前星期（0=周一） |
| `work_time.work_days` | array | 配置的工作日 |
| `runtime.current_runtime_seconds` | integer | 今天已运行秒数 |
| `runtime.current_runtime_hours` | float | 今天已运行小时数 |
| `runtime.max_daily_hours` | integer | 每日最大运行小时数 |
| `runtime.remaining_hours` | float | 今日剩余可用小时数 |

---

### 9. GET `/api/v1/anti-ban/config`

获取当前防封号系统的配置参数。

#### 请求示例

```bash
curl http://localhost:8765/api/v1/anti-ban/config
```

#### 响应示例

```json
{
  "ok": true,
  "rate_limits": {
    "per_minute": 10,
    "per_hour": 20,
    "per_day": 100
  },
  "human_behavior": {
    "min_think_time": 3.0,
    "max_think_time": 15.0,
    "min_random_delay": 1.0,
    "max_random_delay": 3.0
  },
  "work_time": {
    "hours": "9-22",
    "days": [0, 1, 2, 3, 4],
    "max_daily_runtime_hours": 8.0
  },
  "content_diversification": {
    "prefix_probability": 0.1,
    "suffix_probability": 0.05,
    "skip_probability": 0.2
  },
  "gui_operations": {
    "offset_range": 3,
    "move_duration": "0.1-0.3s",
    "pause": "0.05-0.15s"
  }
}
```

#### 配置说明

| 配置项 | 说明 |
|--------|------|
| `rate_limits.per_minute` | 每分钟最大发送数 |
| `rate_limits.per_hour` | 每小时最大发送数 |
| `rate_limits.per_day` | 每天最大发送数 |
| `human_behavior.min_think_time` | 操作前最小思考时间（秒） |
| `human_behavior.max_think_time` | 操作前最大思考时间（秒） |
| `human_behavior.min_random_delay` | 消息间最小随机延迟（秒） |
| `human_behavior.max_random_delay` | 消息间最大随机延迟（秒） |
| `work_time.hours` | 工作时段范围 |
| `work_time.days` | 工作日（0=周一，6=周日） |
| `work_time.max_daily_runtime_hours` | 每日最大运行时长 |
| `content_diversification.prefix_probability` | 自动添加前缀概率 |
| `content_diversification.suffix_probability` | 自动添加后缀概率 |
| `content_diversification.skip_probability` | 随机跳过概率 |
| `gui_operations.offset_range` | 鼠标偏移范围（像素） |
| `gui_operations.move_duration` | 鼠标移动时长范围 |
| `gui_operations.pause` | 操作停顿时长范围 |

---

### 10. 静态页面

| 路径 | 说明 |
|------|------|
| `GET /` | Web 首页（测试页面） |
| `GET /test` | 功能测试页面 |
| `GET /queue` | 队列管理页面（可视化管理消息队列） |
| `GET /static/*` | 静态资源文件 |

---

## MCP Tools 总览

MCP Tools 通过 MCP 协议（Streamable HTTP 或 stdio）暴露给 AI 助手使用。共 **6 个工具**：

| 工具名 | 说明 | 对应 HTTP API |
|--------|------|---------------|
| `send_wechat_message` | 发送微信消息 | `POST /api/v1/messages/send` |
| `schedule_wechat_message` | 定时发送消息 | `POST /api/v1/messages/send`（带 delay） |
| `get_queue_status` | 队列状态概览 | `GET /api/v1/queue/status` |
| `get_message_detail` | 查看消息详情 | `GET /api/v1/queue/messages/{id}` |
| `cancel_queue_message` | 取消待发送消息 | `POST /api/v1/queue/messages/{id}/cancel` |
| `retry_queue_message` | 重试失败消息 | `POST /api/v1/queue/messages/{id}/retry` |

---

## MCP Tools 详解

### 1. `send_wechat_message`

向微信联系人或群组发送文本消息。

#### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `contact_name` | string | ✅ | - | 联系人或群组名称 |
| `message` | string | ✅ | - | 消息内容 |
| `mode` | string | ❌ | `"queue"` | 发送模式：`queue`（异步入队）或 `sync`（同步立即发送） |
| `priority` | integer | ❌ | `5` | 优先级 0-10，数值越小优先级越高 |

#### 返回值

字符串，包含发送结果描述。

#### 使用示例

```
send_wechat_message(
  contact_name="文件传输助手",
  message="你好，这是来自 AI 的消息！",
  mode="queue",
  priority=5
)
```

**返回值示例：**

```
消息已加入发送队列: id=42, 联系人=文件传输助手, 优先级=5
```

---

### 2. `schedule_wechat_message`

安排在延迟后发送微信消息。

#### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `contact_name` | string | ✅ | - | 联系人或群组名称 |
| `message` | string | ✅ | - | 消息内容 |
| `delay_seconds` | float | ✅ | - | 发送前的延迟秒数 |
| `priority` | integer | ❌ | `5` | 优先级 0-10 |

#### 返回值

字符串，包含安排结果描述。

#### 使用示例

```
schedule_wechat_message(
  contact_name="文件传输助手",
  message="这是一条定时消息",
  delay_seconds=300,
  priority=3
)
```

**返回值示例：**

```
消息已安排在 300 秒后发送给 文件传输助手: id=43, 优先级=3
```

---

### 3. `get_queue_status`

查看消息队列状态概览。

#### 参数

无。

#### 返回值

字符串，包含队列各状态的消息计数。

#### 使用示例

```
get_queue_status()
```

**返回值示例：**

```
=== 消息队列状态 ===
Worker 状态: 运行中
待发送 (pending): 5
发送中 (processing): 1
已完成 (completed): 42
已失败 (failed): 3
已取消 (cancelled): 2
总计: 53
```

---

### 4. `get_message_detail`

查看指定消息的详细信息。

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message_id` | integer | ✅ | 消息 ID |

#### 返回值

字符串，包含消息详细信息。

#### 使用示例

```
get_message_detail(message_id=42)
```

**返回值示例：**

```
=== 消息详情 (ID: 42) ===
联系人: 文件传输助手
消息内容: 你好，世界！
状态: completed
模式: queue
优先级: 5
重试次数: 0/3
创建时间: 2026-05-07T09:59:50
计划时间: 2026-05-07T10:00:00
更新时间: 2026-05-07T10:00:02
```

---

### 5. `cancel_queue_message`

取消待发送的消息。

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message_id` | integer | ✅ | 要取消的消息 ID |

#### 返回值

字符串，包含取消结果。

#### 使用示例

```
cancel_queue_message(message_id=42)
```

**返回值示例：**

```
消息已取消: id=42
```

---

### 6. `retry_queue_message`

重试失败的消息。

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message_id` | integer | ✅ | 要重试的消息 ID |

#### 返回值

字符串，包含重试结果。

#### 使用示例

```
retry_queue_message(message_id=42)
```

**返回值示例：**

```
消息已重新加入队列: id=42
```

---

## 错误码说明

| HTTP 状态码 | 说明 | 常见原因 |
|-------------|------|----------|
| 200 | 成功 | 请求已正常处理 |
| 400 | 请求参数错误 | 缺少必填参数、参数类型错误、mode/priority 值无效 |
| 404 | 资源不存在 | 消息 ID 不存在 |
| 500 | 服务器内部错误 | 发送过程异常、微信窗口未找到、GUI 操作失败 |
| 503 | 服务不可用 | 消息队列未初始化、防封号模块未加载 |

---

## 消息状态说明

消息队列中的消息具有以下状态：

| 状态 | 说明 | 可操作 |
|------|------|--------|
| `pending` | 待发送 | 可取消 |
| `processing` | 正在发送 | 不可操作 |
| `completed` | 已成功发送 | 不可操作 |
| `failed` | 发送失败（重试耗尽） | 可重试 |
| `cancelled` | 已取消 | 不可操作 |

### 状态流转

```
pending ──→ processing ──→ completed
   │            │
   │            └──→ pending (自动重试，retry_count < max_retries)
   │
   └──→ failed (重试耗尽) ──→ pending (手动 retry)
   
pending ──→ cancelled (手动 cancel)
```

---

## 附录：配置参数参考

配置文件位于 `data/config.json`，所有配置项如下：

```json
{
  "http_port": 8080,
  "rate_limit_per_minute": 10,
  "rate_limit_per_hour": 20,
  "rate_limit_per_day": 100,
  "min_think_time": 3.0,
  "max_think_time": 15.0,
  "min_random_delay": 1.0,
  "max_random_delay": 3.0,
  "work_hours_start": 9,
  "work_hours_end": 22,
  "work_days": [0, 1, 2, 3, 4],
  "max_daily_runtime_hours": 8.0,
  "prefix_probability": 0.1,
  "suffix_probability": 0.05,
  "random_skip_probability": 0.2,
  "wechat_hotkey": "ctrl+alt+w",
  "gui_offset_range": 3,
  "gui_move_duration_min": 0.1,
  "gui_move_duration_max": 0.3,
  "gui_pause_min": 0.05,
  "gui_pause_max": 0.15,
  "queue_db_path": "",
  "queue_max_retries": 3,
  "queue_poll_interval": 1.0,
  "mac_wechat_hotkey": "command+shift+w",
  "mac_send_shortcut": "command+enter"
}
```

详细配置说明请参考 [QUICK_START.md](QUICK_START.md) 中的配置部分。

---

*本文档最后更新：2026年5月*
