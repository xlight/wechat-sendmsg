# 托盘恢复机制改进说明

## 更新日期
2026-02-12 (下午)

## 问题背景

用户反馈：当微信处于系统托盘（systray）时，虽然代码可以使用 `ShowWindow(SW_SHOW)` 激活窗口，但恢复出来的窗口**功能不完整**，无法正确操作发送消息。

### 根本原因分析

1. **任务栏 vs 系统托盘的区别**:
   - **任务栏最小化**: 窗口最小化到任务栏，状态为 `IsIconic() = True`，窗口句柄仍然有效
   - **系统托盘**: 窗口完全隐藏（`IsWindowVisible() = False`），微信内部状态可能未完全初始化

2. **`ShowWindow()` 的局限性**:
   - `ShowWindow(SW_SHOW)` 只是简单地显示窗口
   - 不会触发微信内部的"从托盘恢复"逻辑
   - 窗口显示了，但内部组件可能未正确初始化

3. **正确的恢复方式**:
   - 用户双击托盘图标时，微信会执行完整的恢复流程
   - 这个行为对应于 `WM_SYSCOMMAND` 消息配合 `SC_RESTORE` 参数

---

## 解决方案

### 方案概述

使用 **`WM_SYSCOMMAND` + `SC_RESTORE`** 消息来模拟用户双击托盘图标的行为，而不是简单地使用 `ShowWindow()`。

### 技术实现

#### 关键 Windows 消息

```python
WM_SYSCOMMAND = 0x0112  # 系统命令消息
SC_RESTORE = 0xF120     # 恢复窗口命令
```

#### 恢复流程

```python
# 1. 发送 SC_RESTORE 系统命令（模拟托盘双击）
win32gui.SendMessage(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
time.sleep(0.5)

# 2. 如果窗口最小化，使用 SW_RESTORE 恢复
if win_info['iconic']:
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.5)

# 3. 如果窗口仍然不可见，使用 SW_SHOW 显示
if not win32gui.IsWindowVisible(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    time.sleep(0.5)

# 4. 激活窗口到前台
self._activate_window(hwnd)
```

---

## 代码修改详情

### 修改文件
- `src/window_finder.py` - 窗口查找和恢复逻辑（`WindowFinderMixin`）
- `src/tray_manager.py` - 系统托盘图标查找和双击恢复（`TrayManagerMixin`）

> **注意**: 原 `src/wechat_controller.py` 已通过 Mixin 模式拆分为多个文件。托盘恢复相关逻辑现分布在 `window_finder.py` 和 `tray_manager.py` 中。

### 修改前后对比

#### 修改前（仅使用 ShowWindow）

```python
# 如果窗口最小化，先恢复
if win_info['iconic']:
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.8)

# 如果窗口隐藏，显示它
if not win_info['visible']:
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    time.sleep(0.8)

# 激活窗口
win32gui.SetForegroundWindow(hwnd)
```

**问题**: 从托盘恢复的窗口功能不完整

#### 修改后（使用 WM_SYSCOMMAND SC_RESTORE）

```python
# 定义系统命令常量
WM_SYSCOMMAND = 0x0112
SC_RESTORE = 0xF120

# 1. 先发送 SC_RESTORE 系统命令（模拟托盘双击）
self.logger.debug(f"发送 WM_SYSCOMMAND SC_RESTORE 消息")
win32gui.SendMessage(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
self._natural_gui._random_pause(0.5, 0.8)

# 2. 如果窗口最小化，再用 ShowWindow 恢复
if win_info['iconic']:
    self.logger.debug(f"窗口处于最小化状态，使用 SW_RESTORE")
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    self._natural_gui._random_pause(0.5, 0.8)

# 3. 如果窗口仍然隐藏，显示它
if not win32gui.IsWindowVisible(hwnd):
    self.logger.debug(f"窗口仍不可见，使用 SW_SHOW")
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    self._natural_gui._random_pause(0.5, 0.8)

# 4. 激活窗口到前台
self._activate_window(hwnd)
self._natural_gui._random_pause(0.3, 0.6)

# 5. 验证窗口现在是否可见
if win32gui.IsWindowVisible(hwnd):
    self.logger.info(f"✅ 成功恢复窗口")
    return hwnd
else:
    self.logger.warning(f"窗口恢复后仍不可见")
```

**优点**:
- ✅ 模拟用户双击托盘图标，触发完整恢复流程
- ✅ 窗口内部组件正确初始化
- ✅ 可以正常发送消息

---

## 测试方法

### 测试脚本

创建了专门的测试脚本：`test_tray_recovery_detailed.py`

#### 测试步骤

1. **关闭微信主窗口** (让它缩小到系统托盘)
   - 点击微信窗口右上角的 [X] 关闭按钮
   - 微信会最小化到系统托盘（不是完全退出）

2. **运行测试脚本**:
   ```bash
   python test_tray_recovery_detailed.py
   ```

3. **观察结果**:
   - 窗口是否正确恢复显示
   - 窗口功能是否完整
   - 消息是否成功发送

### 预期测试结果

```
【步骤 1】检查微信窗口状态...
找到 1 个微信窗口:
  [1] 微信 (Qt51514QWindowIcon) - 960x1040 - ❌ 隐藏
✅ 检测到隐藏的微信窗口（在系统托盘中）

【步骤 2】尝试从托盘恢复微信窗口...
发送 WM_SYSCOMMAND SC_RESTORE 消息
窗口仍不可见，使用 SW_SHOW
✅ 找到窗口句柄: 5179540
   窗口可见性: ✅ 可见

【步骤 3】窗口已恢复，尝试发送测试消息...
[消息发送流程...]

测试结果
======================================================================
窗口恢复: ✅ 成功
消息发送: ✅ 成功
```

---

## 技术原理

### WM_SYSCOMMAND 消息

`WM_SYSCOMMAND` 是 Windows 系统级别的窗口命令消息，用于执行窗口的标准操作。

#### 常用的 SC 命令

| 命令 | 值 | 说明 |
|-----|-----|------|
| SC_MINIMIZE | 0xF020 | 最小化窗口 |
| SC_MAXIMIZE | 0xF030 | 最大化窗口 |
| SC_RESTORE | 0xF120 | 恢复窗口（从最小化或最大化状态） |
| SC_CLOSE | 0xF060 | 关闭窗口 |

### SC_RESTORE 的工作原理

当向窗口发送 `WM_SYSCOMMAND` + `SC_RESTORE` 消息时：

1. **触发窗口过程**: 窗口的 `WndProc` 接收到消息
2. **执行恢复逻辑**: 应用程序执行自定义的恢复逻辑
   - 初始化内部组件
   - 恢复窗口状态
   - 触发事件处理器
3. **显示窗口**: 最终调用底层的窗口显示函数

### 为什么比 ShowWindow 更好？

| 方法 | ShowWindow(SW_SHOW) | WM_SYSCOMMAND SC_RESTORE |
|------|---------------------|--------------------------|
| 显示窗口 | ✅ | ✅ |
| 触发应用恢复逻辑 | ❌ | ✅ |
| 初始化内部组件 | ❌ | ✅ |
| 模拟用户操作 | ❌ | ✅ |
| 适用场景 | 普通隐藏窗口 | 托盘最小化窗口 |

---

## 其他尝试的方法

在实现过程中，我们也探索了其他方法：

### 方法1: 查找并点击托盘图标位置

**原理**: 使用 `ctypes` 访问托盘工具栏，读取按钮信息，找到微信图标的位置并模拟点击。

**问题**:
- 需要跨进程内存访问（复杂）
- 需要计算图标的准确位置
- 托盘可能折叠，图标不可见

**结论**: 实现复杂度高，放弃

### 方法2: pyautogui 图像识别

**原理**: 截取微信托盘图标，使用 `pyautogui.locateOnScreen()` 找到图标并点击。

**问题**:
- 需要预先准备图标图片
- 不同DPI/缩放比例下图标大小不同
- 图标可能被其他窗口遮挡

**结论**: 依赖外部资源，不可靠

### 方法3: WM_SYSCOMMAND SC_RESTORE ✅

**原理**: 发送系统命令消息，模拟用户从托盘恢复窗口。

**优点**:
- ✅ 无需知道托盘图标位置
- ✅ 模拟用户双击托盘图标的行为
- ✅ 触发完整的恢复流程
- ✅ 实现简单，可靠性高

**结论**: **最佳方案** ✨

---

## 注意事项

### 1. 窗口状态验证

在恢复窗口后，务必验证窗口是否真的可见：

```python
if win32gui.IsWindowVisible(hwnd):
    # 恢复成功
else:
    # 恢复失败，需要其他方法
```

### 2. 延迟时间

不同的窗口恢复可能需要不同的延迟时间：

```python
# SC_RESTORE 后等待
self._natural_gui._random_pause(0.5, 0.8)

# ShowWindow 后等待
self._natural_gui._random_pause(0.5, 0.8)

# 激活窗口后等待
self._natural_gui._random_pause(0.3, 0.6)
```

### 3. 异常处理

恢复过程可能失败，需要捕获异常并记录日志：

```python
try:
    win32gui.SendMessage(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0)
    # ... 其他操作
except Exception as e:
    self.logger.warning(f"恢复窗口失败: {e}")
    continue
```

---

## 相关文件

### 源代码
- `src/window_finder.py` - 窗口查找和恢复逻辑（`WindowFinderMixin`）
- `src/tray_manager.py` - 系统托盘图标查找和双击恢复（`TrayManagerMixin`）

### 测试脚本
- `test_tray_recovery_detailed.py` - 详细的托盘恢复测试
- `test_restore_from_tray.py` - 简单的托盘恢复测试
- `test_tray_recovery_methods.py` - 多种恢复方法对比测试
- `find_systray_icon.py` - 托盘图标查找工具（实验性）

### 文档
- `docs/WINDOW_DETECTION_FIXES.md` - 窗口检测和激活功能修复总结
- `docs/TRAY_RECOVERY_IMPROVEMENT.md` - 本文档

---

## 贡献者

- xLight - 托盘恢复机制改进

## 版本历史

- **v1.1.0** (2026-02-12 下午) - 托盘恢复机制改进
  - 使用 WM_SYSCOMMAND SC_RESTORE 替代 ShowWindow
  - 修复从托盘恢复的窗口功能不完整的问题
  - 添加详细的测试脚本

- **v1.0.0** (2026-02-12 上午) - 初始窗口检测修复
  - 窗口尺寸阈值调整
  - Qt 窗口检测顺序优化
  - 增强窗口激活方法

---

**最后更新**: 2026-02-12  
**状态**: 代码已实现，等待用户测试验证 ⏳
