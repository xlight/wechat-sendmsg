# 防封号保护系统使用指南

## 📖 目录

- [系统概述](#系统概述)
- [核心模块介绍](#核心模块介绍)
- [快速开始](#快速开始)
- [配置详解](#配置详解)
- [API 接口](#api-接口)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)
- [开发者指南](#开发者指南)

---

## 系统概述

### 什么是防封号保护系统？

防封号保护系统是一套集成在微信自动化工具中的多层防护机制，通过模拟人类行为、控制操作频率、多样化内容等方式，**降低**微信账号被检测为自动化工具的风险。

⚠️ **重要提示**：
- 本系统只能**降低风险**，无法**100% 保证**账号安全
- 任何自动化行为都违反微信服务协议
- **强烈建议仅在测试账号上使用**

### 系统架构

```
┌─────────────────────────────────────────────────┐
│           防封号保护系统 (anti_ban)              │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐   │
│  │ 速率限制         │  │ 人类行为模拟      │   │
│  │ RateLimiter      │  │ HumanBehavior    │   │
│  │ • 每分钟限制     │  │ • 思考时间        │   │
│  │ • 每小时限制     │  │ • 打字速度        │   │
│  │ • 每日限制       │  │ • 随机延迟        │   │
│  └──────────────────┘  └──────────────────┘   │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐   │
│  │ 工作时间控制      │  │ 内容多样化        │   │
│  │ WorkTimeCtrl     │  │ Diversifier      │   │
│  │ • 工作时段        │  │ • 随机前缀        │   │
│  │ • 工作日          │  │ • 随机后缀        │   │
│  │ • 运行时长        │  │ • 智能跳过        │   │
│  └──────────────────┘  └──────────────────┘   │
│                                                 │
│  ┌──────────────────┐                          │
│  │ 自然 GUI 操作     │                          │
│  │ NaturalGUI       │                          │
│  │ • 随机偏移        │                          │
│  │ • 缓慢移动        │                          │
│  │ • 安全剪贴板      │                          │
│  └──────────────────┘                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 防护层级

| 层级 | 防护机制 | 作用 |
|------|----------|------|
| **L1** | 速率限制 | 防止短时间内频繁操作 |
| **L2** | 工作时间控制 | 避免 24/7 不间断运行 |
| **L3** | 人类行为模拟 | 模拟真人操作的随机性 |
| **L4** | 内容多样化 | 避免发送重复模板内容 |
| **L5** | 自然 GUI 操作 | 降低 GUI 自动化特征 |

---

## 核心模块介绍

### 1. EnhancedRateLimiter - 增强版速率限制器

**功能**：三级速率限制，基于滑动窗口算法。

**特点**：
- ✅ 分钟级限制（默认 3 次/分钟）
- ✅ 小时级限制（默认 20 次/小时）
- ✅ 每日限制（默认 100 次/天）
- ✅ 自动清理过期记录
- ✅ 实时统计查询

**代码示例**：
```python
from src.anti_ban import EnhancedRateLimiter

# 创建速率限制器
limiter = EnhancedRateLimiter(
    limit_per_minute=3,
    limit_per_hour=20,
    limit_per_day=100
)

# 检查是否允许操作
if limiter.allow():
    print("允许操作")
    # 执行 AI 调用或消息发送
else:
    print("速率超限，跳过操作")

# 查询统计信息
stats = limiter.get_stats()
print(f"最近一分钟: {stats['last_minute']}/{stats['limit_minute']}")
print(f"最近一小时: {stats['last_hour']}/{stats['limit_hour']}")
print(f"最近一天: {stats['last_day']}/{stats['limit_day']}")
```

**配置项**：
```json
{
  "rate_limit_per_minute": 3,
  "rate_limit_per_hour": 20,
  "rate_limit_per_day": 100
}
```

---

### 2. HumanBehaviorSimulator - 人类行为模拟器

**功能**：模拟真人操作的思考时间、打字速度、随机延迟。

**特点**：
- ✅ 随机思考时间（3-8 秒可配置）
- ✅ 打字速度模拟（根据文本长度计算）
- ✅ 随机延迟（0.5-2 秒可配置）
- ✅ 支持同步和异步等待

**代码示例**：
```python
from src.anti_ban import HumanBehaviorSimulator
import asyncio

# 创建行为模拟器
simulator = HumanBehaviorSimulator(
    min_think_time=3.0,
    max_think_time=8.0,
    min_delay=0.5,
    max_delay=2.0
)

# 异步场景：模拟思考时间
async def process_message():
    think_time = simulator.think_time()
    print(f"思考时间: {think_time:.2f}秒")
    await simulator.async_sleep_random(think_time, think_time)
    
    # 调用 AI 服务...
    
    # 模拟打字时间
    reply = "这是 AI 的回复内容"
    typing_time = simulator.typing_time(reply)
    print(f"打字时间: {typing_time:.2f}秒")
    await simulator.async_sleep_random(typing_time * 0.8, typing_time * 1.2)

# 同步场景：随机延迟
delay = simulator.random_delay()
print(f"随机延迟: {delay:.2f}秒")
simulator.sleep_random(delay, delay)
```

**配置项**：
```json
{
  "min_think_time": 3.0,
  "max_think_time": 8.0,
  "min_random_delay": 0.5,
  "max_random_delay": 2.0
}
```

---

### 3. WorkTimeController - 工作时间控制器

**功能**：限制自动化工具仅在指定时段和日期运行。

**特点**：
- ✅ 工作时段控制（如 9:00-18:00）
- ✅ 工作日控制（如周一到周五）
- ✅ 每日运行时长限制（如最多 8 小时）
- ✅ 自动跨日重置

**代码示例**：
```python
from src.anti_ban import WorkTimeController

# 创建工作时间控制器
controller = WorkTimeController(
    work_hours_start=9,      # 早上 9 点开始
    work_hours_end=18,       # 下午 6 点结束
    work_days=[0, 1, 2, 3, 4],  # 周一到周五（0=周一, 6=周日）
    max_daily_runtime_hours=8.0  # 每天最多运行 8 小时
)

# 检查当前是否在工作时间
if not controller.is_work_time():
    print("当前不在工作时间，停止处理")
    return

# 检查是否超过每日运行时长
if not controller.should_continue_running():
    print("已达到每日运行时长限制，停止服务")
    shutdown()

# 查询运行时长
runtime = controller.get_runtime()
print(f"今日已运行: {runtime/3600:.1f} 小时")
```

**配置项**：
```json
{
  "work_hours_start": 9,
  "work_hours_end": 18,
  "work_days": [0, 1, 2, 3, 4],
  "max_daily_runtime_hours": 8.0
}
```

---

### 4. ContentDiversifier - 内容多样化器

**功能**：为 AI 回复添加随机前缀/后缀，智能跳过简单问候语。

**特点**：
- ✅ 随机前缀（30% 概率）
- ✅ 随机后缀（20% 概率）
- ✅ 智能跳过问候语（10% 概率）
- ✅ 避免内容完全重复

**代码示例**：
```python
from src.anti_ban import ContentDiversifier

# 创建内容多样化器
diversifier = ContentDiversifier(
    prefix_probability=0.3,   # 30% 概率添加前缀
    suffix_probability=0.2,   # 20% 概率添加后缀
    skip_probability=0.1      # 10% 概率跳过问候语
)

# 检查是否应该跳过（问候语）
if diversifier.should_skip("你好"):
    print("跳过简单问候")
    return

# 多样化内容
original = "这是 AI 的回复"
diversified = diversifier.diversify(original)
print(f"原始: {original}")
print(f"多样化后: {diversified}")
# 可能输出: "嗯，这是 AI 的回复 😊"
```

**配置项**：
```json
{
  "prefix_probability": 0.3,
  "suffix_probability": 0.2,
  "random_skip_probability": 0.1
}
```

**内置前缀/后缀列表**：
```python
# 前缀
["嗯", "好的", "明白", "收到", "了解", "让我想想", "这个问题"]

# 后缀
["😊", "👌", "💪", "🙏", "😄", "👍"]
```

---

### 5. NaturalGUIOperations - 自然 GUI 操作

**功能**：让 GUI 操作看起来更像真人。

**特点**：
- ✅ 随机位置偏移（±5 像素）
- ✅ 缓慢鼠标移动（0.3-0.8 秒）
- ✅ 随机暂停（0.1-0.3 秒）
- ✅ 安全剪贴板操作（自动备份和恢复）
- ✅ 交替使用快捷键（Ctrl+V / Shift+Insert）

**代码示例**：
```python
from src.anti_ban import NaturalGUIOperations

# 创建自然 GUI 操作器
gui = NaturalGUIOperations(
    offset_range=5,
    move_duration_min=0.3,
    move_duration_max=0.8,
    pause_min=0.1,
    pause_max=0.3
)

# 获取随机偏移后的坐标
x, y = 100, 200
new_x, new_y = gui.add_random_offset(x, y)
print(f"原始坐标: ({x}, {y})")
print(f"偏移后: ({new_x}, {new_y})")

# 获取缓慢移动时长
duration = gui.slow_move_duration()
print(f"移动时长: {duration:.2f}秒")

# 获取随机暂停时间
pause = gui.random_pause()
print(f"暂停时间: {pause:.2f}秒")

# 安全粘贴（自动备份剪贴板）
text = "要粘贴的文本"
success = gui.safe_paste_text(text)
```

**配置项**：
```json
{
  "gui_offset_range": 5,
  "gui_move_duration_min": 0.3,
  "gui_move_duration_max": 0.8,
  "gui_pause_min": 0.1,
  "gui_pause_max": 0.3
}
```

---

## 快速开始

### 方式一：使用预设配置模板（推荐）

项目提供三种预设配置，直接复制即可使用：

```bash
# 1. 保守模式（新账号/高价值账号）
cp config.conservative.json config.json

# 2. 中等模式（已养成的测试账号）- 推荐
cp config.moderate.json config.json

# 3. 激进模式（临时测试小号）
cp config.aggressive.json config.json
```

### 方式二：手动配置

编辑 `config.json`，添加防封号配置项：

```json
{
  "http_port": 8080,
  "poll_interval": 30,
  "monitored_groups": ["测试群"],
  "bot_name": "你的昵称",
  
  "ai_base_url": "https://api.openai.com/v1",
  "ai_api_key": "sk-...",
  "ai_model": "gpt-3.5-turbo",
  
  "// 防封号配置": "以下为防封号相关配置",
  "rate_limit_per_minute": 3,
  "rate_limit_per_hour": 20,
  "rate_limit_per_day": 100,
  "min_think_time": 3.0,
  "max_think_time": 8.0,
  "work_hours_start": 9,
  "work_hours_end": 18,
  "work_days": [0, 1, 2, 3, 4],
  "max_daily_runtime_hours": 8.0,
  "prefix_probability": 0.3,
  "suffix_probability": 0.2,
  "random_skip_probability": 0.1
}
```

### 启动服务

```bash
python src/auto_reply.py
```

观察日志输出，应该能看到防封号系统的工作提示：

```
2026-02-11 14:30:15 - 正在启动自动回复服务...
2026-02-11 14:30:15 - 微信状态: NT框架
2026-02-11 14:30:15 - HTTP 服务器已启动: http://0.0.0.0:8080
2026-02-11 14:30:15 - 消息监听器已启动
2026-02-11 14:30:45 - 处理 @ 提及 - 群: 测试群, 发送者: 张三
2026-02-11 14:30:45 - 模拟思考时间: 5.34秒
2026-02-11 14:30:50 - AI 回复已生成
2026-02-11 14:30:50 - 内容多样化: 添加前缀
2026-02-11 14:30:52 - 成功发送消息
```

---

## 配置详解

### 配置模板对比

| 配置项 | 保守模式 | 中等模式（默认） | 激进模式 |
|--------|----------|------------------|----------|
| **每分钟限制** | 1 次 | 3 次 | 5 次 |
| **每小时限制** | 10 次 | 20 次 | 40 次 |
| **每日限制** | 30 次 | 100 次 | 200 次 |
| **思考时间** | 5-15秒 | 3-8秒 | 1-4秒 |
| **工作时段** | 10:00-21:00 | 09:00-18:00 | 00:00-23:00 |
| **工作日** | 周二到周五 | 周一到周五 | 全周 |
| **每日运行时长** | 3 小时 | 8 小时 | 24 小时 |
| **跳过概率** | 30% | 10% | 5% |
| **风险等级** | 🟢 低 | 🟡 中等 | 🔴 高 |

### 配置项详细说明

#### 速率限制配置

```json
{
  "rate_limit_per_minute": 3,   // 每分钟最多 3 次 AI 调用
  "rate_limit_per_hour": 20,    // 每小时最多 20 次
  "rate_limit_per_day": 100     // 每天最多 100 次
}
```

**调整建议**：
- 新账号：1/10/30
- 测试账号：3/20/100
- 小号：5/40/200

#### 人类行为配置

```json
{
  "min_think_time": 3.0,        // 最小思考时间（秒）
  "max_think_time": 8.0,        // 最大思考时间（秒）
  "min_random_delay": 0.5,      // 最小随机延迟（秒）
  "max_random_delay": 2.0       // 最大随机延迟（秒）
}
```

**调整建议**：
- 快速响应场景：1-4 秒
- 正常场景：3-8 秒
- 深思熟虑场景：5-15 秒

#### 工作时间配置

```json
{
  "work_hours_start": 9,        // 工作时段开始（小时，0-23）
  "work_hours_end": 18,         // 工作时段结束（小时，0-23）
  "work_days": [0, 1, 2, 3, 4], // 工作日（0=周一, 6=周日）
  "max_daily_runtime_hours": 8.0 // 每日最大运行时长（小时）
}
```

**调整建议**：
- 上班时间：9-18，周一到周五
- 全天候：0-23，全周
- 夜间模式：22-6，全周

#### 内容多样化配置

```json
{
  "prefix_probability": 0.3,    // 添加前缀的概率（0-1）
  "suffix_probability": 0.2,    // 添加后缀的概率（0-1）
  "random_skip_probability": 0.1 // 跳过问候语的概率（0-1）
}
```

**调整建议**：
- 高多样化：0.5/0.4/0.3
- 中等多样化：0.3/0.2/0.1
- 低多样化：0.1/0.05/0.05

#### GUI 操作配置

```json
{
  "gui_offset_range": 5,        // 随机偏移范围（像素）
  "gui_move_duration_min": 0.3, // 最小移动时长（秒）
  "gui_move_duration_max": 0.8, // 最大移动时长（秒）
  "gui_pause_min": 0.1,         // 最小暂停时间（秒）
  "gui_pause_max": 0.3          // 最大暂停时间（秒）
}
```

**调整建议**：一般不需要修改，保持默认值即可。

---

## API 接口

### 1. 查询防封号统计

**端点**：`GET /api/v1/anti-ban/stats`

**请求示例**：
```bash
curl http://localhost:8080/api/v1/anti-ban/stats
```

**响应示例**：
```json
{
  "ok": true,
  "rate_limiter": {
    "last_minute": 2,
    "last_hour": 15,
    "last_day": 87,
    "limit_minute": 3,
    "limit_hour": 20,
    "limit_day": 100
  },
  "work_time": {
    "is_work_time": true,
    "current_hour": 14,
    "work_hours": "9-18",
    "current_day": 1,
    "work_days": [0, 1, 2, 3, 4]
  },
  "runtime": {
    "current_runtime_seconds": 7234,
    "current_runtime_hours": 2.01,
    "max_daily_hours": 8,
    "remaining_hours": 5.99
  }
}
```

**字段说明**：
- `rate_limiter` - 速率限制器统计
  - `last_minute/hour/day` - 最近时段的调用次数
  - `limit_minute/hour/day` - 对应的限制值
- `work_time` - 工作时间状态
  - `is_work_time` - 当前是否在工作时间
  - `current_hour` - 当前小时（0-23）
  - `current_day` - 当前星期几（0=周一, 6=周日）
- `runtime` - 运行时长统计
  - `current_runtime_seconds/hours` - 今日已运行时长
  - `remaining_hours` - 今日剩余可运行时长

### 2. 查询防封号配置

**端点**：`GET /api/v1/anti-ban/config`

**请求示例**：
```bash
curl http://localhost:8080/api/v1/anti-ban/config
```

**响应示例**：
```json
{
  "ok": true,
  "rate_limits": {
    "per_minute": 3,
    "per_hour": 20,
    "per_day": 100
  },
  "human_behavior": {
    "min_think_time": 3.0,
    "max_think_time": 8.0,
    "min_random_delay": 0.5,
    "max_random_delay": 2.0
  },
  "work_time": {
    "hours": "9-18",
    "days": [0, 1, 2, 3, 4],
    "max_daily_runtime_hours": 8
  },
  "content_diversification": {
    "prefix_probability": 0.3,
    "suffix_probability": 0.2,
    "skip_probability": 0.1
  },
  "gui_operations": {
    "offset_range": 5,
    "move_duration": "0.3-0.8s",
    "pause": "0.1-0.3s"
  }
}
```

### 3. 动态更新配置

**端点**：`PUT /api/v1/config`

**请求示例**：
```bash
curl -X PUT http://localhost:8080/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "rate_limit_per_minute": 5,
    "min_think_time": 5.0,
    "max_think_time": 10.0
  }'
```

**响应示例**：
```json
{
  "ok": true,
  "message": "Configuration updated",
  "config": { ... }
}
```

---

## 最佳实践

### 1. 账号养号策略

**新账号（0-2 周）**：
```json
{
  "rate_limit_per_minute": 1,
  "rate_limit_per_day": 30,
  "work_hours_start": 10,
  "work_hours_end": 21,
  "max_daily_runtime_hours": 3,
  "random_skip_probability": 0.3
}
```

**已养成账号（2 周+）**：
```json
{
  "rate_limit_per_minute": 3,
  "rate_limit_per_day": 100,
  "work_hours_start": 9,
  "work_hours_end": 18,
  "max_daily_runtime_hours": 8,
  "random_skip_probability": 0.1
}
```

### 2. 逐步提升策略

```
第 1 周：每天运行 1 小时，每天最多回复 10 次
第 2 周：每天运行 2 小时，每天最多回复 20 次
第 3 周：每天运行 4 小时，每天最多回复 50 次
第 4 周：如无异常，使用中等模式配置
```

### 3. 监控和调整

**每日检查清单**：
- [ ] 查询防封号统计 API
- [ ] 检查账号是否收到微信安全提示
- [ ] 观察速率限制是否触发
- [ ] 检查每日运行时长
- [ ] 手动登录微信进行正常聊天

**监控脚本示例**：
```bash
#!/bin/bash
# 每小时检查一次防封号状态

while true; do
  echo "=== $(date) ==="
  curl -s http://localhost:8080/api/v1/anti-ban/stats | jq '.rate_limiter, .runtime'
  echo ""
  sleep 3600
done
```

### 4. 应急响应

**发现异常时**：
1. 立即停止自动化服务（Ctrl+C）
2. 检查微信账号状态
3. 降低配置（切换到保守模式）
4. 观察 1-2 天后再重启

**账号被限制时**：
1. 停止所有自动化操作至少 1 周
2. 正常使用微信其他功能
3. 联系微信客服说明情况（不提及自动化）
4. 考虑更换账号

---

## 故障排查

### 问题 1：防封号功能没有生效

**症状**：日志中没有"思考时间"、"随机跳过"等提示

**排查步骤**：
1. 检查配置文件是否包含防封号配置项
   ```bash
   grep "rate_limit_per_minute" config.json
   ```

2. 检查模块是否正确导入
   ```python
   python -c "from src.anti_ban import EnhancedRateLimiter; print('OK')"
   ```

3. 查看详细日志
   ```bash
   python src/auto_reply.py 2>&1 | grep -i "anti\|rate\|think"
   ```

### 问题 2：速率限制过于严格

**症状**：频繁看到"速率超限"日志

**解决方案**：
1. 查询当前统计
   ```bash
   curl http://localhost:8080/api/v1/anti-ban/stats
   ```

2. 动态调整限制
   ```bash
   curl -X PUT http://localhost:8080/api/v1/config \
     -H "Content-Type: application/json" \
     -d '{"rate_limit_per_minute": 5}'
   ```

3. 或修改配置文件并重启服务

### 问题 3：工作时间外仍在运行

**症状**：非工作时间仍然在处理消息

**排查步骤**：
1. 检查配置
   ```bash
   curl http://localhost:8080/api/v1/anti-ban/config | jq '.work_time'
   ```

2. 检查系统时间是否正确
   ```bash
   date
   ```

3. 检查 `work_days` 配置（0=周一, 6=周日）

### 问题 4：依赖导入失败

**症状**：`ModuleNotFoundError: No module named 'pyautogui'`

**解决方案**：
```bash
# 安装所有依赖
pip install -r requirements.txt

# 或单独安装
pip install pyautogui pywin32 pygetwindow
```

---

## 开发者指南

### 自定义防封号策略

#### 示例：添加自定义前缀库

```python
# 修改 src/anti_ban/content_diversifier.py

class ContentDiversifier:
    def __init__(self, ...):
        # 自定义前缀库
        self._custom_prefixes = [
            "让我看看",
            "稍等",
            "嗯嗯",
            "好嘞",
            "马上"
        ]
        
        # 使用自定义前缀
        self._prefixes = self._custom_prefixes
```

#### 示例：添加周末特殊处理

```python
# 修改 src/anti_ban/work_time_controller.py

def is_work_time(self) -> bool:
    now = datetime.now()
    
    # 周末降低活跃度
    if now.weekday() >= 5:  # 周六、周日
        # 仅在中午和晚上活跃
        if now.hour not in [12, 13, 18, 19, 20]:
            return False
    
    # 原有逻辑...
    return True
```

### 集成到其他项目

#### 1. 安装 anti_ban 包

```bash
# 方式一：复制到项目
cp -r src/anti_ban your_project/

# 方式二：创建 Python 包
cd src
pip install -e .
```

#### 2. 基础用法

```python
from anti_ban import (
    EnhancedRateLimiter,
    HumanBehaviorSimulator,
    WorkTimeController,
    ContentDiversifier
)

# 创建实例
rate_limiter = EnhancedRateLimiter()
human_behavior = HumanBehaviorSimulator()
work_time = WorkTimeController()
diversifier = ContentDiversifier()

# 在你的业务逻辑中使用
async def process_request(request):
    # 1. 工作时间检查
    if not work_time.is_work_time():
        return "非工作时间"
    
    # 2. 速率限制
    if not rate_limiter.allow():
        return "速率超限"
    
    # 3. 思考延迟
    think_time = human_behavior.think_time()
    await asyncio.sleep(think_time)
    
    # 4. 处理请求
    response = await call_ai(request)
    
    # 5. 内容多样化
    response = diversifier.diversify(response)
    
    return response
```

### 单元测试

运行防封号模块的单元测试：

```bash
# 运行所有测试
python -m unittest test_anti_ban -v

# 运行特定测试类
python -m unittest test_anti_ban.TestEnhancedRateLimiter -v

# 运行特定测试方法
python -m unittest test_anti_ban.TestEnhancedRateLimiter.test_minute_limit
```

### 性能优化

#### 速率限制器优化

```python
# 使用更高效的数据结构
from collections import deque

# deque 的 popleft() 是 O(1) 操作
self._timestamps_minute = deque(maxlen=limit_per_minute)
```

#### 减少配置文件读取

```python
# 缓存配置对象，避免重复创建
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

---

## 常见问题 FAQ

**Q1: 使用防封号系统就不会被封了吗？**

A: **否**。防封号系统只能降低风险，无法 100% 保证安全。任何自动化行为都有被检测的可能。

**Q2: 可以同时监控多个群吗？**

A: 可以，但建议：
- 新账号：1-2 个小群
- 测试账号：3-5 个群
- 避免监控超过 100 人的大群

**Q3: 配置模板可以混合使用吗？**

A: 可以。你可以从模板开始，然后根据实际情况调整个别配置项。

**Q4: 为什么有时候不回复消息？**

A: 可能原因：
1. 触发了速率限制
2. 不在工作时间
3. 随机跳过了该消息（概率性）
4. 超过了每日运行时长

**Q5: 如何查看防封号系统是否正常工作？**

A: 三种方式：
1. 观察日志中的"思考时间"、"随机跳过"提示
2. 调用 `/api/v1/anti-ban/stats` API
3. 观察回复速度是否有随机性

**Q6: 可以在运行中修改配置吗？**

A: 可以通过 `PUT /api/v1/config` API 动态修改，部分配置需要重启服务才能生效。

**Q7: 防封号系统会影响性能吗？**

A: 影响极小。主要开销是：
- 思考延迟（故意添加的等待时间）
- 剪贴板操作（毫秒级）
- 时间戳管理（内存操作，极快）

**Q8: 可以完全禁用防封号功能吗？**

A: 不建议。但你可以设置极端配置：
```json
{
  "rate_limit_per_minute": 9999,
  "min_think_time": 0.1,
  "random_skip_probability": 0.0
}
```

---

## 附录

### A. 配置项速查表

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `rate_limit_per_minute` | int | 3 | 每分钟最大调用次数 |
| `rate_limit_per_hour` | int | 20 | 每小时最大调用次数 |
| `rate_limit_per_day` | int | 100 | 每天最大调用次数 |
| `min_think_time` | float | 3.0 | 最小思考时间（秒） |
| `max_think_time` | float | 8.0 | 最大思考时间（秒） |
| `min_random_delay` | float | 0.5 | 最小随机延迟（秒） |
| `max_random_delay` | float | 2.0 | 最大随机延迟（秒） |
| `work_hours_start` | int | 9 | 工作时段开始（0-23） |
| `work_hours_end` | int | 18 | 工作时段结束（0-23） |
| `work_days` | list | [0,1,2,3,4] | 工作日（0=周一, 6=周日） |
| `max_daily_runtime_hours` | float | 8.0 | 每日最大运行时长（小时） |
| `prefix_probability` | float | 0.3 | 添加前缀概率（0-1） |
| `suffix_probability` | float | 0.2 | 添加后缀概率（0-1） |
| `random_skip_probability` | float | 0.1 | 跳过问候语概率（0-1） |
| `gui_offset_range` | int | 5 | GUI 随机偏移范围（像素） |
| `gui_move_duration_min` | float | 0.3 | GUI 最小移动时长（秒） |
| `gui_move_duration_max` | float | 0.8 | GUI 最大移动时长（秒） |
| `gui_pause_min` | float | 0.1 | GUI 最小暂停时间（秒） |
| `gui_pause_max` | float | 0.3 | GUI 最大暂停时间（秒） |

### B. 日志关键字速查

| 关键字 | 含义 |
|--------|------|
| `模拟思考时间` | 人类行为模拟生效 |
| `速率超限` | 触发速率限制 |
| `不在工作时间` | 工作时间控制生效 |
| `随机跳过` | 内容多样化跳过消息 |
| `内容多样化` | 添加了前缀/后缀 |
| `达到每日运行时长限制` | 超过每日运行时长 |

### C. 相关文档

- [快速开始指南](./QUICK_START.md)
- [避免封号详细指南](./AVOID_BAN.md)
- [项目 README](../README.md)
- [配置模板](../config.*.json)

---

**最后更新**: 2026-02-11  
**文档版本**: v1.0  
**适用系统版本**: WeChat MCP Server v2.0+

如有疑问，请查看 [GitHub Issues](https://github.com/1052666/WeChat-MCP-Server/issues) 或阅读源代码。
