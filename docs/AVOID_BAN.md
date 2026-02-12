# 如何避免测试账号被封

## 🎉 防封号保护系统已集成

**从 v2.0 开始，项目内置了全面的防封号保护系统。** 以下所有建议已通过 `anti_ban` 包自动实现：

### 内置防护功能

✅ **增强版速率限制** - 三级限制（分钟/小时/天），基于滑动窗口算法  
✅ **人类行为模拟** - 随机思考时间（3-8秒）、打字速度模拟、随机延迟  
✅ **工作时间控制** - 仅在指定时段（默认 9:00-18:00）和工作日运行  
✅ **内容多样化** - 智能添加随机前缀/后缀，自动跳过简单问候语  
✅ **自然 GUI 操作** - 随机鼠标偏移、缓慢移动、随机暂停、交替使用快捷键  

### 快速配置

所有防封号功能通过 `data/config.json` 集中配置，无需修改代码：

```json
{
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

### 监控防封号状态

通过 HTTP API 实时监控防封号系统状态：

```bash
# 查询当前统计信息
curl http://localhost:8080/api/v1/anti-ban/stats

# 查询防封号配置
curl http://localhost:8080/api/v1/anti-ban/config
```

### 预设配置模板

| 模式 | 适用场景 | 每日回复上限 | 风险等级 |
|------|----------|--------------|----------|
| **保守** | 新注册账号、高价值账号 | 30 次 | 🟢 低 |
| **中等** | 已养成的测试账号 | 100 次 | 🟡 中等 |
| **激进** | 低价值小号、短期测试 | 200 次 | 🔴 高 |

**保守模式配置**（推荐新账号）：
```json
{
  "rate_limit_per_minute": 1,
  "rate_limit_per_hour": 10,
  "rate_limit_per_day": 30,
  "min_think_time": 5.0,
  "max_think_time": 15.0,
  "work_hours_start": 10,
  "work_hours_end": 21,
  "max_daily_runtime_hours": 3,
  "random_skip_probability": 0.3
}
```

**中等模式配置**（默认）：
```json
{
  "rate_limit_per_minute": 3,
  "rate_limit_per_hour": 20,
  "rate_limit_per_day": 100,
  "min_think_time": 3.0,
  "max_think_time": 8.0,
  "work_hours_start": 9,
  "work_hours_end": 18,
  "max_daily_runtime_hours": 8,
  "random_skip_probability": 0.1
}
```

**激进模式配置**（仅测试）：
```json
{
  "rate_limit_per_minute": 5,
  "rate_limit_per_hour": 40,
  "rate_limit_per_day": 200,
  "min_think_time": 1.0,
  "max_think_time": 4.0,
  "work_hours_start": 0,
  "work_hours_end": 23,
  "max_daily_runtime_hours": 24,
  "random_skip_probability": 0.05
}
```

### 如何根据账号调整配置

1. **新注册账号** → 使用**保守模式**，运行 1-2 周后逐步提高限制
2. **已养成测试账号** → 使用**中等模式**（默认配置）
3. **临时测试小号** → 可使用**激进模式**，但账号可能很快被封

### 常见问题 FAQ

**Q: 使用防封号系统就不会被封了吗？**  
A: **否**。任何自动化行为都有被检测风险，防封号系统只能**降低风险**，无法保证100%安全。

**Q: 为什么还是被封了？**  
A: 可能原因：账号太新、群聊活跃度过高、配置过于激进、微信算法升级等。建议降低配置并更换账号。

**Q: 可以在多个群同时使用吗？**  
A: 可以，但建议新账号只监控 1-2 个小群，已养成的账号不超过 5 个群。

**Q: 如何查看防封号系统是否正常工作？**  
A: 观察日志中的 "模拟思考时间"、"随机跳过" 等提示，或通过 API 查询统计数据。

---

## ⚠️ 重要声明

**使用任何微信自动化工具都存在账号被封的风险。本文档仅提供降低风险的建议，无法保证账号安全。**

- 微信官方明确禁止使用自动化工具
- 即使采取所有预防措施，账号仍可能被检测并封禁
- **强烈建议仅在测试账号或小号上使用**
- **切勿在重要账号上使用自动化工具**

## 风控检测原理

微信的风控系统可能通过以下方式检测自动化行为：

### 1. 行为模式检测
- 操作时间间隔过于规律（如每隔 5 秒精确执行）
- 鼠标移动轨迹过于直线或重复
- 键盘输入速度异常（过快或过慢）
- 24/7 不间断在线和操作

### 2. 操作频率检测
- 短时间内发送大量消息
- 频繁切换聊天窗口
- 消息发送速率异常

### 3. 技术特征检测
- 检测到剪贴板频繁操作
- 识别 GUI 自动化工具的特征
- 检测进程中的可疑程序（pyautogui 等）
- 窗口标题或进程名称异常

### 4. 内容特征检测
- 发送重复或模板化内容
- 回复速度异常（收到消息立即回复）
- 回复内容与上下文不符

## 降低风险的核心策略

### 策略一：使用测试账号

**永远不要在主账号上使用自动化工具**

1. **注册新的微信账号**
   - 使用独立的手机号注册
   - 完成实名认证（提高账号权重）
   - 正常使用 1-2 周后再启用自动化

2. **养号操作**
   ```
   - 添加 10-20 个好友
   - 加入 3-5 个群聊
   - 每天手动发送一些正常消息
   - 使用朋友圈、视频号等功能
   - 绑定银行卡（少量充值，提高账号信任度）
   ```

3. **账号隔离**
   - 测试账号和主账号不要互加好友
   - 不要在同一设备上频繁切换登录
   - 使用独立的测试环境

### 策略二：模拟人类行为

**让自动化操作看起来更像真人**

#### 1. 添加随机延迟

在 `src/gui_operations.py` 中添加随机等待时间：

```python
import random
import time

def _human_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """模拟人类操作的随机延迟"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)

# 在关键操作前后调用
def send_text_message(self, contact_name: str, message: str):
    self._human_delay(0.5, 1.5)  # 操作前延迟
    # ... 执行发送操作
    self._human_delay(1.0, 3.0)  # 操作后延迟
```

#### 2. 随机化操作时间

修改 `data/config.json` 配置：

```json
{
  "poll_interval": 30,  // 基础轮询间隔（秒）
  "poll_interval_random": 20,  // 随机偏移范围（秒）
  "rate_limit_per_minute": 3,  // 每分钟最多 3 次操作
  "rate_limit_per_hour": 20  // 每小时最多 20 次操作
}
```

以下示例展示了随机轮询间隔的原理（供自定义开发参考）：

```python
import random

# 示例：随机轮询间隔（概念参考）
async def poll_loop():
    """带随机间隔的轮询循环"""
    while not stop_event.is_set():
        try:
            await poll_messages()
        except Exception as e:
            logger.error(f"轮询出错: {e}")
        
        # 随机轮询间隔
        base_interval = 30  # 基础间隔（秒）
        random_offset = random.uniform(-10, 10)
        actual_interval = max(5, base_interval + random_offset)
        
        await asyncio.sleep(actual_interval)
```

#### 3. 避免立即回复

以下示例展示了消息处理中如何添加延迟（供自定义开发参考）：

```python
async def handle_incoming_message(content: str, sender: str) -> None:
    """处理收到的消息（概念参考）"""
    
    # 模拟思考时间：3-15 秒的随机延迟
    think_time = random.uniform(3, 15)
    logger.info(f"模拟思考时间: {think_time:.1f}秒")
    await asyncio.sleep(think_time)
    
    # 速率限制检查
    if not rate_limiter.allow():
        logger.warning("速率超限，跳过此消息")
        return
    
    # 调用 AI 服务
    reply = await ai_client.chat(content)
    
    # 模拟打字时间：根据回复长度计算
    typing_time = len(reply) * 0.1  # 每字 0.1 秒
    typing_time = min(typing_time, 10)  # 最多 10 秒
    typing_time = random.uniform(typing_time * 0.5, typing_time * 1.5)
    await asyncio.sleep(typing_time)
    
    # 发送回复
    await send_reply(sender, reply)
```

### 策略三：严格控制使用频率

#### 1. 多层速率限制

创建增强版速率限制器 `src/rate_limiter.py`：

```python
#!/usr/bin/env python3
"""
增强版速率限制器
支持分钟级、小时级、每日限制。
"""

import logging
import time
from collections import deque
from typing import Deque

logger = logging.getLogger(__name__)


class EnhancedRateLimiter:
    """多级速率限制器"""

    def __init__(
        self,
        per_minute: int = 3,
        per_hour: int = 20,
        per_day: int = 100
    ):
        self._per_minute = per_minute
        self._per_hour = per_hour
        self._per_day = per_day
        
        self._minute_timestamps: Deque[float] = deque()
        self._hour_timestamps: Deque[float] = deque()
        self._day_timestamps: Deque[float] = deque()

    def allow(self) -> bool:
        """检查当前是否允许一次调用"""
        now = time.time()
        
        # 清理过期记录
        self._cleanup(now)
        
        # 检查各级限制
        if len(self._minute_timestamps) >= self._per_minute:
            logger.warning(f"达到每分钟限制 ({self._per_minute})")
            return False
        
        if len(self._hour_timestamps) >= self._per_hour:
            logger.warning(f"达到每小时限制 ({self._per_hour})")
            return False
        
        if len(self._day_timestamps) >= self._per_day:
            logger.warning(f"达到每日限制 ({self._per_day})")
            return False
        
        # 记录时间戳
        self._minute_timestamps.append(now)
        self._hour_timestamps.append(now)
        self._day_timestamps.append(now)
        
        return True

    def _cleanup(self, now: float) -> None:
        """清理过期的时间戳"""
        # 清理 1 分钟前的记录
        while self._minute_timestamps and now - self._minute_timestamps[0] > 60:
            self._minute_timestamps.popleft()
        
        # 清理 1 小时前的记录
        while self._hour_timestamps and now - self._hour_timestamps[0] > 3600:
            self._hour_timestamps.popleft()
        
        # 清理 1 天前的记录
        while self._day_timestamps and now - self._day_timestamps[0] > 86400:
            self._day_timestamps.popleft()

    def get_stats(self) -> dict:
        """获取当前使用统计"""
        return {
            "last_minute": len(self._minute_timestamps),
            "last_hour": len(self._hour_timestamps),
            "last_day": len(self._day_timestamps),
            "limit_minute": self._per_minute,
            "limit_hour": self._per_hour,
            "limit_day": self._per_day
        }
```

#### 2. 推荐的速率限制配置

```json
{
  "rate_limit_per_minute": 2,   // 每分钟最多 2 次
  "rate_limit_per_hour": 15,    // 每小时最多 15 次
  "rate_limit_per_day": 50      // 每天最多 50 次
}
```

**更保守的配置（强烈推荐）：**
```json
{
  "rate_limit_per_minute": 1,   // 每分钟最多 1 次
  "rate_limit_per_hour": 10,    // 每小时最多 10 次
  "rate_limit_per_day": 30      // 每天最多 30 次
}
```

### 策略四：限制运行时间

**避免 24/7 不间断运行**

#### 1. 添加工作时间限制

以下示例展示了工作时间控制的原理（v2.0 中已由 `anti_ban.WorkTimeController` 内置实现）：

```python
import datetime

class WorkTimeChecker:
    """工作时间检查器（概念参考）"""
    
    def __init__(self):
        # 工作时间配置（仅在这些时段运行）
        self._work_hours_start = 9   # 早上 9 点
        self._work_hours_end = 22    # 晚上 10 点
        self._work_days = [0, 1, 2, 3, 4]  # 周一到周五
    
    def is_work_time(self) -> bool:
        """检查当前是否在工作时间内"""
        now = datetime.datetime.now()
        
        # 检查星期几
        if now.weekday() not in self._work_days:
            return False
        
        # 检查时间段
        current_hour = now.hour
        if current_hour < self._work_hours_start or current_hour >= self._work_hours_end:
            return False
        
        return True
```

#### 2. 添加每日运行时长限制

以下示例展示了每日运行时长限制的原理（v2.0 中已由 `anti_ban.WorkTimeController` 内置实现）：

```python
class DailyRuntimeLimiter:
    """每日运行时长限制器（概念参考）"""
    
    def __init__(self):
        self._daily_runtime_limit = 4 * 3600  # 每天最多运行 4 小时
        self._daily_runtime = 0
        self._last_reset_date = datetime.date.today()
    
    async def run(self):
        """主运行循环"""
        start_time = time.time()
        
        while not self._shutting_down:
            # 检查每日运行时长
            current_date = datetime.date.today()
            if current_date != self._last_reset_date:
                self._daily_runtime = 0
                self._last_reset_date = current_date
                logger.info("每日运行时长已重置")
            
            if self._daily_runtime >= self._daily_runtime_limit:
                logger.warning("已达到每日运行时长限制，停止服务")
                break
            
            # ... 运行服务
            await asyncio.sleep(60)
            
            # 更新运行时长
            self._daily_runtime = time.time() - start_time
```

### 策略五：内容多样化

**避免发送模板化、重复的内容**

#### 1. 添加内容变化

```python
import random

class AIClient:
    async def chat(self, user_message: str) -> str:
        """调用 AI 并添加内容多样性"""
        
        # 调用 AI 获取回复
        reply = await self._call_ai_api(user_message)
        
        # 随机添加前缀（10% 概率）
        if random.random() < 0.1:
            prefixes = ["嗯", "好的", "明白", "收到", "了解"]
            reply = f"{random.choice(prefixes)}，{reply}"
        
        # 随机添加后缀（5% 概率）
        if random.random() < 0.05:
            suffixes = ["😊", "👌", "💪", "🙏"]
            reply = f"{reply} {random.choice(suffixes)}"
        
        return reply
```

#### 2. 避免对所有消息都回复

以下示例展示了消息跳过的原理（v2.0 中已由 `anti_ban.ContentDiversifier` 内置实现）：

```python
async def handle_message(content: str) -> None:
    """消息处理（概念参考）"""
    
    # 随机跳过 20% 的消息（模拟人类可能错过或忽略消息）
    if random.random() < 0.2:
        logger.info("随机跳过此消息（模拟人类行为）")
        return
    
    # 对于简单的问候语，随机跳过 50%
    greetings = ["你好", "hi", "hello", "在吗", "在不"]
    if any(g in content.lower() for g in greetings):
        if random.random() < 0.5:
            logger.info("跳过简单问候（模拟人类可能不回复）")
            return
    
    # ... 正常处理逻辑
```

### 策略六：监控群组选择

**谨慎选择监控的群聊**

#### 1. 限制监控群组数量

```json
{
  "monitored_groups": [
    "测试群1"  // 仅监控 1-2 个测试群
  ]
}
```

#### 2. 选择低活跃度群组

- 避免监控消息频繁的大群（>100 人）
- 选择每天消息量 <50 条的小群
- 优先选择私人测试群

#### 3. 定期轮换群组

```python
# 每周更换监控的群组，避免在同一群长期活跃
# 建议手动配置，不要自动化
```

### 策略七：技术层面优化

#### 1. 减少 GUI 操作特征

以下示例展示了自然 GUI 操作的原理（v2.0 中已由 `anti_ban.NaturalGUIOperations` 和 `src/gui_operations.py` 内置实现）：

```python
class NaturalClick:
    """自然点击模拟（概念参考）"""
    
    def click_position(self, x: int, y: int):
        """模拟更自然的鼠标点击"""
        # 添加位置随机偏移（±3 像素）
        x_offset = random.randint(-3, 3)
        y_offset = random.randint(-3, 3)
        
        # 使用缓慢移动而非瞬间跳转
        pyautogui.moveTo(x + x_offset, y + y_offset, duration=random.uniform(0.1, 0.3))
        
        # 随机停顿
        time.sleep(random.uniform(0.05, 0.15))
        
        # 点击
        pyautogui.click()
```

#### 2. 保护剪贴板操作

以下示例展示了安全剪贴板操作的原理（v2.0 中已由 `src/gui_operations.py` 中的 `_set_clipboard_and_paste` 和 `_restore_clipboard` 内置实现）：

```python
def paste_text_safe(text: str):
    """更安全的剪贴板粘贴（概念参考）"""
    # 备份剪贴板
    old_clipboard = self._get_clipboard()
    
    try:
        # 设置剪贴板
        self._set_clipboard(text)
        
        # 随机延迟
        time.sleep(random.uniform(0.1, 0.3))
        
        # 粘贴（使用 Shift+Insert 而非 Ctrl+V，更少见）
        if random.random() < 0.5:
            pyautogui.hotkey('ctrl', 'v')
        else:
            pyautogui.hotkey('shift', 'insert')
        
    finally:
        # 延迟恢复剪贴板（500-1000ms）
        time.sleep(random.uniform(0.5, 1.0))
        self._set_clipboard(old_clipboard)
```

#### 3. 避免进程特征

- 修改 Python 脚本的进程名称
- 不要在脚本名称中包含 "bot"、"auto"、"wechat" 等关键词
- 使用虚拟环境运行

## 实战配置示例

### 极度保守配置（推荐新账号）

`data/config.json`:
```json
{
  "http_port": 8080,
  "rate_limit_per_minute": 1,
  "rate_limit_per_hour": 8,
  "rate_limit_per_day": 30,
  "random_skip_probability": 0.3,
  "min_think_time": 5,
  "max_think_time": 20,
  "work_hours_start": 10,
  "work_hours_end": 21,
  "work_days": [0, 1, 2, 3, 4],
  "max_daily_runtime_hours": 3
}
```

### 使用建议

1. **逐步测试**
   ```
   第 1 周：每天运行 30 分钟，每天最多回复 5 次
   第 2 周：每天运行 1 小时，每天最多回复 10 次
   第 3 周：每天运行 2 小时，每天最多回复 20 次
   第 4 周：如无异常，逐步增加到正常配置
   ```

2. **监控账号状态**
   - 每天检查账号是否正常
   - 注意是否收到微信安全提示
   - 定期手动登录，进行正常聊天

3. **紧急停止机制**
   ```python
   # 如果检测到异常，立即停止
   if self._detect_abnormal():
       logger.error("检测到异常，立即停止所有自动化操作！")
       self.shutdown()
   ```

## 被封后的处理

### 1. 临时限制（几小时到几天）
- 停止所有自动化操作
- 等待自动解封
- 解封后降低使用频率

### 2. 功能限制（无法发消息、加好友等）
- 停止使用自动化工具至少 1 个月
- 正常使用微信其他功能
- 联系微信客服说明情况（不要提及自动化）

### 3. 永久封禁
- 该账号无法恢复
- 放弃该账号
- 重新注册新账号，更谨慎地使用

## 最佳实践检查清单

使用前请确认：

- [ ] 使用的是测试账号或小号，不是主账号
- [ ] 账号已正常使用 1-2 周以上
- [ ] 已添加随机延迟逻辑
- [ ] 已配置多层速率限制
- [ ] 已限制每日运行时间和时长
- [ ] 已设置工作时间窗口
- [ ] 仅监控 1-2 个低活跃度测试群
- [ ] AI 回复内容多样化
- [ ] 配置了随机跳过消息的概率
- [ ] 准备好账号被封的心理预期
- [ ] 已阅读并理解项目的免责声明

## 最后的忠告

**没有任何方法可以 100% 避免被封。**

即使采取了所有预防措施，微信仍可能检测到自动化行为并封禁账号。请务必：

1. **只在测试账号上使用**
2. **接受账号可能被封的风险**
3. **不要依赖自动化工具处理重要事务**
4. **定期备份重要聊天记录**
5. **保持对微信政策的敬畏之心**

如果您无法承受账号被封的后果，**请不要使用本工具**。

---

**祝您使用顺利，但请务必谨慎！**
