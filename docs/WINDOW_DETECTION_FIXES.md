# WeChat 窗口检测和激活功能修复总结

**GitHub地址：https://github.com/xlight/wechat-sendmsg**

## 修复日期
2026-02-12

## 问题概述

修复了 `chatwe-automate` 项目中 WeChat 窗口检测和激活的三个关键问题：

1. **窗口尺寸检测阈值过高** - 半屏窗口被误识别为联系人列表窗口
2. **系统托盘恢复失败** - 隐藏的主窗口无法被检测和恢复
3. **窗口激活限制** - Windows 安全策略阻止后台进程激活窗口

---

## 修复详情

### 修复 #1: 窗口尺寸检测阈值

**文件**: `src/window_finder.py`（`WindowFinderMixin`）  
**影响**: 主窗口检测逻辑

**问题描述**:
- 原始阈值: `width >= 1000 AND height >= 700`
- 用户半屏窗口: `960x1040`
- 结果: 主窗口被拒绝，误识别为联系人列表窗口

**解决方案**:
```python
# 修改前
if width >= 1000 and height >= 700:

# 修改后
if width >= 800 or height >= 800:
```

**测试结果**:
| 窗口尺寸 | 宽度 | 高度 | 检测结果 |
|---------|------|------|---------|
| 1936x1056 | 1936 | 1056 | ✅ 主窗口 |
| 960x1040 | 960 | 1040 | ✅ 主窗口（修复后）|
| 506x183 | 506 | 183 | ❌ 联系人列表（正确）|

---

### 修复 #2: 系统托盘窗口检测

**文件**: `src/window_finder.py`（`WindowFinderMixin`）  
**影响**: 隐藏窗口检测逻辑

**问题描述**:
当 WeChat 主窗口缩小到系统托盘时：
- 主窗口（`960x1040`）`visible=0`（隐藏）
- 小联系人列表窗口（`506x183`）`visible=1`（可见）
- 旧逻辑跳过所有不可见窗口，导致找到错误的窗口

**原始检测顺序（错误）**:
```python
1. 检查 Chrome 窗口（不检查可见性）✓
2. 跳过所有不可见窗口 ✗  ← Qt 主窗口在这里被跳过！
3. 检查 Qt 窗口（只检查可见的）✗
```

**修复后的检测顺序（正确）**:
```python
1. 检查 Chrome 窗口（不检查可见性）✓
2. 检查 Qt 窗口（不检查可见性）✓  ← 移到前面！
3. 跳过其他不可见窗口 ✓
```

**关键代码更改**:
```python
# 第 234-267 行: Qt 窗口检测（移到可见性检查之前）
elif window_class == "Qt51514QWindowIcon" and window_text == "微信":
    width = rect[2] - rect[0]
    height = rect[3] - rect[1]
    
    # Qt 主窗口判断（>= 800x800，不检查可见性）
    if width >= 800 or height >= 800:
        logger.debug(f"找到主窗口（Qt大窗口）: hwnd={hwnd}, size={width}x{height}, visible={is_visible}")
        main_windows.append({
            'hwnd': hwnd,
            'class': window_class,
            'text': window_text,
            'rect': rect,
            'is_visible': is_visible,
            'width': width,
            'height': height
        })
    # Qt 小窗口（联系人列表）只在可见时添加
    elif is_visible:
        logger.debug(f"找到联系人列表窗口（Qt小窗口）: hwnd={hwnd}, size={width}x{height}")
        contact_list_windows.append({...})
```

**测试结果（托盘状态）**:
```
找到主窗口（Qt大窗口）: hwnd=2297010, size=960x1040, visible=0 ✅
窗口统计 - 主窗口: 1 ✅
尝试恢复Qt主窗口: hwnd=2297010 ✅
ShowWindow(SW_SHOW) ✅
SetForegroundWindow ✅
✅ 成功恢复Qt主窗口 ✅
消息发送成功 ✅
```

---

### 修复 #3: 增强窗口激活方法

**文件**: `src/window_finder.py`（`WindowFinderMixin`）  
**影响**: `_activate_window()` 方法

**问题描述**:
Windows 安全限制阻止后台进程激活窗口，导致：
- `SetForegroundWindow()` 失败
- `BringWindowToTop()` 失败
- 窗口无法获得焦点

**解决方案**:
实现多层激活策略：

```python
# 方法 1: Alt 键模拟（临时释放前台锁定）
pyautogui.press('alt')

# 方法 2: 双重 AttachThreadInput
current_thread_id = win32api.GetCurrentThreadId()
target_thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]

# 附加当前线程到目标线程
win32process.AttachThreadInput(current_thread_id, target_thread_id, True)
# 附加目标线程到当前线程
win32process.AttachThreadInput(target_thread_id, current_thread_id, True)

# 方法 3: BringWindowToTop + SetWindowPos
win32gui.BringWindowToTop(hwnd)
win32gui.SetWindowPos(
    hwnd, win32con.HWND_TOPMOST,
    0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
)
win32gui.SetWindowPos(
    hwnd, win32con.HWND_NOTOPMOST,
    0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
)
```

**测试结果**:
- ✅ 从浏览器切换到 WeChat 成功
- ✅ 从其他应用切换到 WeChat 成功
- ✅ 从托盘恢复后激活成功

---

## 测试覆盖

### 测试场景

| 场景 | 窗口状态 | 测试结果 |
|-----|---------|---------|
| 场景 1 | WeChat 在前台（活动窗口）| ✅ 通过 |
| 场景 2 | WeChat 在后台但可见 | ✅ 通过 |
| 场景 3 | WeChat 在系统托盘（隐藏）| ✅ 通过 |

### 测试脚本

创建了以下测试脚本：

1. **`test_send_message.py`** - 基本消息发送测试
2. **`test_restore_from_tray.py`** - 托盘恢复专项测试
3. **`test_all_scenarios.py`** - 所有场景综合测试
4. **`debug_all_windows.py`** - 窗口状态调试工具
5. **`check_foreground_window.py`** - 前台窗口检查工具

### 测试命令

```bash
# 基本测试（WeChat 必须可见）
python test_send_message.py

# 托盘恢复测试（WeChat 必须在托盘中）
python test_restore_from_tray.py

# 综合测试（所有场景）
python test_all_scenarios.py

# 调试工具
python debug_all_windows.py
python check_foreground_window.py
```

---

## 已知问题和限制

### 问题 #1: HTTP API UTF-8 编码（已修复，待测试）

**状态**: 代码已修复，未完全测试  
**文件**: `src/http_server.py`, 第 405-415 行  
**影响**: 通过 HTTP API 发送消息时的错误处理

**修复**:
```python
except Exception as e:
    # 安全地处理异常消息，避免编码问题
    try:
        error_msg = str(e)
    except:
        error_msg = f"{type(e).__name__}: (encoding error)"
    
    logger.error(f"发送消息时出错", exc_info=True)
    self._send_json_response(
        {"ok": False, "error": f"Internal error: {error_msg}"}, 500
    )
```

**测试方法**:
```bash
# 启动服务器
set PYTHONIOENCODING=utf-8
python src\http_server.py

# 在另一个终端测试
curl -X POST http://localhost:8080/api/v1/messages/send \
  -H "Content-Type: application/json" \
  -d '{"contact_name": "文件传输助手", "message": "HTTP 测试"}'
```

### 问题 #2: 窗口激活从后台进程（已缓解）

**状态**: 多种方法实现，大部分情况有效  
**影响**: 当浏览器或其他应用在前台时，偶尔失败  
**解决方案**: 手动点击 WeChat 窗口作为备选方案

---

## 代码改动汇总

### 修改的文件

1. **`src/window_finder.py`**（`WindowFinderMixin`）
   - 窗口尺寸阈值（`800 OR 800`）
   - Qt 窗口检测顺序调整
   - 增强窗口激活方法
   - 托盘恢复逻辑更新

2. **`src/tray_manager.py`**（`TrayManagerMixin`）
   - 系统托盘图标查找和双击恢复

2. **`src/http_server.py`**
   - 第 405-415 行: 异常处理编码修复

### 新增的测试文件

- `test_send_message.py` - 基本消息发送测试
- `test_restore_from_tray.py` - 托盘恢复测试
- `test_all_scenarios.py` - 综合场景测试
- `debug_all_windows.py` - 窗口调试工具
- `check_foreground_window.py` - 前台窗口检查

### 新增的文档

- `docs/WINDOW_DETECTION_FIXES.md` - 本文档

---

## 使用建议

### 最佳实践

1. **窗口状态**:
   - WeChat 必须运行并已登录
   - WeChat 可以在前台、后台或托盘中
   - 系统会自动检测并恢复窗口

2. **窗口尺寸**:
   - 支持全屏、半屏等各种尺寸
   - 最小推荐尺寸: 800x800（主窗口）
   - 小于此尺寸可能被识别为联系人列表窗口

3. **并发安全**:
   - 使用 `gui_lock` 保护 GUI 操作
   - 避免并发发送多条消息

### 故障排除

**症状**: 找不到窗口
```bash
# 运行调试脚本
python debug_all_windows.py
```
检查输出中是否有 `微信` 窗口，确认尺寸和可见性。

**症状**: 窗口无法激活
- 手动点击 WeChat 窗口
- 检查是否有安全软件阻止窗口激活

**症状**: 消息发送失败
- 检查 WeChat 版本（需要 4.0+）
- 查看日志中的具体错误阶段
- 确认联系人名称正确

---

## 技术细节

### 窗口类型和优先级

1. **WeChatMainWndForPC** - 传统主窗口（旧版本）
2. **Chrome_WidgetWin_0/1** - Chrome 框架窗口（新版本）
3. **Qt51514QWindowIcon** - Qt 框架窗口（最新版本）
   - 尺寸 >= 800x800: 主窗口
   - 尺寸 < 800x800: 联系人列表窗口

### 窗口检测流程

```
1. 枚举所有 WeChat 进程的窗口
   ├─ WeChatAppEx.exe (新版本)
   └─ WeChat.exe (旧版本)

2. 按类型分类窗口
   ├─ 主窗口 (main_windows)
   ├─ Chrome 窗口 (chrome_windows)
   ├─ 联系人列表窗口 (contact_list_windows)
   └─ 聊天窗口 (chat_windows)

3. 优先级选择
   ├─ 1. 可见的主窗口（最高优先级）
   ├─ 2. 可见的 Chrome 窗口
   ├─ 3. 可见的联系人列表窗口
   └─ 4. 隐藏的主窗口（触发恢复）

4. 窗口恢复（如果隐藏）
   ├─ ShowWindow(SW_SHOW)
   ├─ SetForegroundWindow()
   └─ 验证窗口已显示
```

### 窗口激活策略

```
激活方法（按顺序尝试）:

1. Alt 键模拟
   └─ 目的: 临时释放前台锁定

2. 双重 AttachThreadInput
   ├─ 当前线程 → 目标线程
   └─ 目标线程 → 当前线程

3. SetForegroundWindow
   └─ 标准激活方法

4. BringWindowToTop
   └─ Z轴顺序提升

5. SetWindowPos (TOPMOST → NOTOPMOST)
   ├─ 临时置顶
   └─ 恢复正常层级

6. 最终验证
   └─ GetForegroundWindow() == hwnd
```

---

## 相关资源

### 文档链接

- [快速开始指南](../docs/QUICK_START.md)
- [防封号指南](../docs/AVOID_BAN.md)
- [项目 README](../README.md)

### 代码参考

- **窗口检测**: `src/window_finder.py` - `WindowFinderMixin._find_wechat_window()`
- **窗口激活**: `src/window_finder.py` - `WindowFinderMixin._activate_window()`
- **托盘恢复**: `src/tray_manager.py` - `TrayManagerMixin._find_and_click_tray_icon()`
- **消息发送**: `src/gui_operations.py` - `GUIOperationsMixin._send_text_nt()`

---

## 贡献者

- xLight - 窗口检测和激活功能修复

## 版本历史

- **v1.0.0** (2026-02-12) - 初始修复版本
  - 窗口尺寸阈值调整
  - Qt 窗口检测顺序修复
  - 增强窗口激活方法
  - 托盘恢复功能实现

---

**最后更新**: 2026-02-12  
**状态**: 所有核心功能已修复并测试通过 ✅
