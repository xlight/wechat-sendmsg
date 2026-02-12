#!/usr/bin/env python3
"""
微信窗口查找与激活
负责枚举微信窗口、区分窗口类型、从托盘/最小化状态恢复窗口，以及将窗口激活到前台。
"""

import ctypes
import logging
import re
import time
from typing import Any, List, Optional

import psutil
import pyautogui
import win32api
import win32con
import win32gui
import win32process

logger = logging.getLogger(__name__)


class WindowFinderMixin:
    """窗口查找与激活 Mixin。

    提供 _find_wechat_window() 和 _activate_window() 两个核心方法，
    依赖 TrayManagerMixin 的 _restore_from_systray() 实现托盘恢复。
    """

    def _detect_wechat_version(self) -> Optional[str]:
        """检测微信版本号并判断是否为 NT 框架。"""
        try:
            window_hwnd = self._find_wechat_window()
            window_is_nt = self._last_window_kind == "nt" and window_hwnd is not None

            target_procs = []
            if window_hwnd:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(window_hwnd)
                    if pid:
                        target_procs.append(psutil.Process(pid))
                except Exception as e:
                    self.logger.warning(f"无法通过窗口句柄获取微信进程: {e}")

            if not target_procs:
                target_procs = list(psutil.process_iter(['name', 'exe']))

            proc_list = list(target_procs)

            for proc in proc_list:
                try:
                    info = getattr(proc, "info", None)
                    if info is not None:
                        name = info.get('name') or ""
                        exe = info.get('exe')
                    else:
                        name = proc.name() or ""
                        exe = proc.exe()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                lower_name = name.lower()
                if 'wechatappex' in lower_name:
                    continue
                if 'weixin' not in lower_name:
                    continue

                if not exe:
                    continue

                version_info = win32api.GetFileVersionInfo(exe, "\\")
                version = f"{version_info['FileVersionMS'] >> 16}.{version_info['FileVersionMS'] & 0xFFFF}.{version_info['FileVersionLS'] >> 16}.{version_info['FileVersionLS'] & 0xFFFF}"
                self.wechat_version = version

                try:
                    major_version = int(version.split('.')[0])
                except Exception:
                    major_version = 0

                self.is_nt_version = window_is_nt or major_version >= 4
                if self.is_nt_version and major_version >= 4:
                    self.logger.info(f"Detected WeChat NT framework version: {version}")
                elif self.is_nt_version and window_is_nt:
                    self.logger.info(f"Detected WeChat NT framework window (file version: {version})")
                else:
                    self.logger.info(f"Detected WeChat legacy version (<4.0): {version} (will be skipped)")
                return version

            for proc in proc_list:
                try:
                    info = getattr(proc, "info", None)
                    if info is not None:
                        name = info.get('name') or ""
                        exe = info.get('exe')
                    else:
                        name = proc.name() or ""
                        exe = proc.exe()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                lower_name = name.lower()
                if 'wechatappex' in lower_name:
                    continue
                if 'wechat' not in lower_name:
                    continue

                if not exe:
                    continue

                version_info = win32api.GetFileVersionInfo(exe, "\\")
                version = f"{version_info['FileVersionMS'] >> 16}.{version_info['FileVersionMS'] & 0xFFFF}.{version_info['FileVersionLS'] >> 16}.{version_info['FileVersionLS'] & 0xFFFF}"
                self.wechat_version = version

                try:
                    major_version = int(version.split('.')[0])
                except Exception:
                    major_version = 0

                self.is_nt_version = window_is_nt or major_version >= 4
                if self.is_nt_version and major_version >= 4:
                    self.logger.info(f"Detected WeChat NT framework version: {version}")
                elif self.is_nt_version and window_is_nt:
                    self.logger.info(f"Detected WeChat NT framework window (file version: {version})")
                else:
                    self.logger.info(f"Detected WeChat legacy version (<4.0): {version} (will be skipped)")
                return version

            self.logger.warning("Could not detect WeChat process/version")
            self.wechat_version = None
            self.is_nt_version = window_is_nt
            return None
        except Exception as e:
            self.logger.error(f"Error detecting WeChat version: {e}")
            self.wechat_version = None
            self.is_nt_version = False
            return None

    def _find_wechat_window(self) -> Optional[int]:
        """查找微信主窗口，严格排除悬浮聊天窗口。"""

        # 首先检查微信进程是否在运行
        wechat_process_running = False
        for proc in psutil.process_iter(['name']):
            name = proc.info.get('name') or ""
            lower_name = name.lower()
            if 'wechat' in lower_name or 'weixin' in lower_name:
                wechat_process_running = True
                self.logger.debug(f"检测到微信进程: {name}")
                break

        if not wechat_process_running:
            self.logger.warning("微信进程未运行")
            return None

        visible_main_windows = []  # 可见或最小化的主窗口（最高优先级）
        hidden_main_windows = []  # 不可见的主窗口（可能在托盘中，需要恢复）
        chrome_windows = []  # Chrome 主窗口（新增，用于新版微信）
        contact_list_windows = []  # 联系人列表窗口（次优先级）
        chat_windows = []  # 聊天窗口（低优先级，尽量避免）
        all_wechat_windows = []  # 所有微信窗口（用于调试）

        def enum_windows_callback(hwnd, _):
            class_name = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            is_visible = win32gui.IsWindowVisible(hwnd)

            # 检查是否是微信进程的窗口
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                process_name = process.name().lower()
                is_wechat_process = 'wechat' in process_name or 'weixin' in process_name
            except Exception:
                is_wechat_process = False

            # 记录所有可能的微信窗口（仅微信进程或微信专属类名，排除非微信进程中包含 WeChat 文本的窗口）
            if is_wechat_process or "WeChat" in class_name:
                rect = win32gui.GetWindowRect(hwnd)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                all_wechat_windows.append({
                    'hwnd': hwnd,
                    'class': class_name,
                    'text': window_text,
                    'visible': is_visible,
                    'iconic': win32gui.IsIconic(hwnd),
                    'size': (width, height),
                    'area': width * height
                })

            # 【次优先级】Qt 窗口（可能是主窗口或联系人列表窗口，根据大小区分）- 不论可见性
            if re.match(r"Qt\d+QWindowIcon", class_name) or re.match(r"Qt\d+QWindowOwnDC", class_name):
                # 标题只有"微信"或"WeChat"，没有聊天对象名称
                if window_text in ["微信", "WeChat"]:
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]

                    # 根据窗口大小区分主窗口和联系人列表窗口
                    # 主窗口通常很大（宽或高至少有一个>=800），联系人列表窗口较小（宽高都<800）
                    if width >= 800 or height >= 800:
                        if is_visible or win32gui.IsIconic(hwnd):
                            self.logger.debug(f"找到主窗口（Qt大窗口）: hwnd={hwnd}, size={width}x{height}, visible={is_visible}")
                            visible_main_windows.append(hwnd)
                        else:
                            self.logger.debug(f"找到隐藏主窗口（可能在托盘中）: hwnd={hwnd}, size={width}x{height}")
                            hidden_main_windows.append(hwnd)
                    else:
                        # 小窗口只在可见时添加
                        if is_visible:
                            self.logger.debug(f"找到联系人列表窗口（Qt小窗口）: hwnd={hwnd}, size={width}x{height}")
                            contact_list_windows.append(hwnd)
                    return True
                # 标题包含聊天对象名称，这是聊天窗口
                elif "微信" in window_text or "WeChat" in window_text:
                    if is_visible:  # 聊天窗口只在可见时添加
                        self.logger.debug(f"找到聊天窗口: hwnd={hwnd}, class={class_name}, text={window_text}")
                        chat_windows.append(hwnd)
                    return True

            # 跳过其他不可见窗口
            if not is_visible:
                return True

            # 【低优先级】ChatWnd 类名（聊天悬浮窗，尽量避免）
            if class_name == "ChatWnd":
                self.logger.debug(f"找到聊天悬浮窗（跳过）: hwnd={hwnd}, class={class_name}, text={window_text}")
                chat_windows.append(hwnd)
                return True

            # 其他包含"微信"的窗口（必须是微信进程的窗口）
            if is_wechat_process and ("微信" in window_text or "WeChat" in window_text):
                self.logger.debug(f"找到其他微信窗口: hwnd={hwnd}, class={class_name}, text={window_text}")
                chat_windows.append(hwnd)

            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        self.logger.debug(f"窗口统计 - 可见主窗口: {len(visible_main_windows)}, 隐藏主窗口: {len(hidden_main_windows)}, Chrome窗口: {len(chrome_windows)}, 联系人列表: {len(contact_list_windows)}, 聊天窗口: {len(chat_windows)}")

        # 【优先级 1】返回可见/最小化的主窗口
        if visible_main_windows:
            self._last_window_kind = "nt"
            self.logger.info(f"找到主窗口: hwnd={visible_main_windows[0]}")
            return visible_main_windows[0]

        # 【优先级 2】返回 Chrome 主窗口（新版微信 4.0+）
        if chrome_windows:
            # chrome_windows 是 (hwnd, area) 元组列表，按面积降序排序，选择最大的
            chrome_windows.sort(key=lambda x: x[1], reverse=True)
            hwnd = chrome_windows[0][0]

            # Chrome 窗口可能是不可见的，需要先显示
            if not win32gui.IsWindowVisible(hwnd):
                self.logger.info(f"Chrome 主窗口不可见，正在显示: hwnd={hwnd}")
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    self._natural_gui._random_pause(0.5, 1.0)
                except Exception as e:
                    self.logger.error(f"显示窗口失败: {e}")

            self._last_window_kind = "nt"
            self.logger.info(f"找到 Chrome 主窗口: hwnd={hwnd}")
            return hwnd

        # 【优先级 3】返回联系人列表窗口（降级为备用方案）
        if contact_list_windows:
            self._last_window_kind = "nt"
            self.logger.warning(f"未找到主窗口，使用联系人列表窗口: hwnd={contact_list_windows[0]}")
            return contact_list_windows[0]

        # 【优先级 4】如果只有聊天窗口，发出警告但仍然返回
        if chat_windows:
            self._last_window_kind = "nt"
            self.logger.warning(f"仅找到聊天窗口，建议打开微信主窗口: hwnd={chat_windows[0]}")
            return chat_windows[0]

        # 如果没有可见窗口，尝试通过托盘双击恢复微信主窗口
        if hidden_main_windows:
            self.logger.info(f"发现 {len(hidden_main_windows)} 个隐藏主窗口（可能在托盘中），尝试托盘恢复")
        if all_wechat_windows:
            self.logger.info(f"未找到可见微信窗口，发现 {len(all_wechat_windows)} 个微信窗口（可能在托盘中）")
            for win_info in all_wechat_windows:
                self.logger.debug(f"  - hwnd={win_info['hwnd']}, class={win_info['class']}, "
                                f"text={win_info['text']}, visible={win_info['visible']}, "
                                f"iconic={win_info['iconic']}")

        # 【首选方案】通过模拟双击托盘图标恢复（已验证可靠）
        self.logger.info("尝试通过模拟双击托盘图标恢复微信窗口...")
        restored_hwnd = self._restore_from_systray()
        if restored_hwnd:
            self._last_window_kind = "nt"
            # 激活恢复后的窗口
            self._activate_window(restored_hwnd)
            return restored_hwnd

        # 【备用方案】如果托盘图标未找到，尝试 ShowWindow 恢复最小化窗口
        if all_wechat_windows:
            for win_info in all_wechat_windows:
                if not win_info['iconic']:
                    continue
                hwnd = win_info['hwnd']
                self.logger.info(f"尝试通过 ShowWindow 恢复最小化窗口: hwnd={hwnd}")
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    self._natural_gui._random_pause(0.5, 0.8)
                    if win32gui.IsWindowVisible(hwnd):
                        self._activate_window(hwnd)
                        self._last_window_kind = "nt"
                        self.logger.info(f"通过 ShowWindow 成功恢复窗口: hwnd={hwnd}")
                        return hwnd
                except Exception as e:
                    self.logger.warning(f"ShowWindow 恢复失败: {e}")
                    continue

        self._last_window_kind = None
        self.logger.warning("微信进程在运行，但无法找到或恢复微信主窗口（请手动打开微信主窗口）")
        return None

    def _ensure_modifiers_released(self) -> None:
        """确保所有修饰键都已释放。"""
        keys = [0x10, 0x11, 0x12]  # Shift, Ctrl, Alt
        for key in keys:
            if ctypes.windll.user32.GetKeyState(key) & 0x8000:
                ctypes.windll.user32.keybd_event(key, 0, 0x0002, 0)  # Key up

    def _activate_window_by_hotkey(self, hotkey: str = "ctrl+alt+w") -> Optional[int]:
        """通过快捷键激活微信窗口。

        需要用户在微信「设置 → 快捷键」中配置对应的快捷键。
        成功时返回微信窗口句柄，失败时返回 None。

        Args:
            hotkey: 快捷键字符串，格式如 'ctrl+alt+w'，用 '+' 分隔各按键

        Returns:
            微信窗口句柄，或 None（激活失败）
        """
        try:
            # 解析快捷键字符串为按键列表
            keys: List[str] = [k.strip().lower() for k in hotkey.split('+')]
            if not keys:
                self.logger.warning("快捷键配置为空")
                return None

            self.logger.info(f"尝试通过快捷键 [{hotkey}] 激活微信窗口...")

            # 确保修饰键已释放，避免与快捷键冲突
            self._ensure_modifiers_released()

            # 按下快捷键
            pyautogui.hotkey(*keys)

            # 等待窗口激活（微信窗口切换可能有延迟）
            self._natural_gui._random_pause(0.5, 1.0)

            # 检查前台窗口是否为微信
            foreground_hwnd = win32gui.GetForegroundWindow()
            if not foreground_hwnd:
                self.logger.debug("快捷键按下后无前台窗口")
                return None

            if self._is_wechat_window(foreground_hwnd):
                self.logger.info(f"快捷键激活微信窗口成功: hwnd={foreground_hwnd}")
                self._last_window_kind = "nt"
                return foreground_hwnd

            # 可能有延迟，再等一会儿重试检查
            self._natural_gui._random_pause(0.3, 0.5)
            foreground_hwnd = win32gui.GetForegroundWindow()
            if foreground_hwnd and self._is_wechat_window(foreground_hwnd):
                self.logger.info(f"快捷键激活微信窗口成功（第二次检查）: hwnd={foreground_hwnd}")
                self._last_window_kind = "nt"
                return foreground_hwnd

            self.logger.debug("快捷键按下后前台窗口不是微信，快捷键激活失败")
            return None

        except Exception as e:
            self.logger.debug(f"快捷键激活微信窗口出错: {e}")
            return None

    def _is_wechat_window(self, hwnd: int) -> bool:
        """判断指定窗口是否为微信窗口。

        通过检查窗口所属进程名称来判断，避免误判其他程序的窗口。

        Args:
            hwnd: 窗口句柄

        Returns:
            True 表示是微信窗口
        """
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid:
                return False
            proc = psutil.Process(pid)
            process_name = proc.name().lower()
            return 'wechat' in process_name or 'weixin' in process_name
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            return False

    def _activate_window(self, hwnd: int) -> bool:
        """激活微信窗口，支持从最小化/隐藏状态恢复。"""
        try:
            self._ensure_modifiers_released()

            # 1. 检查窗口是否存在且有效
            if not win32gui.IsWindow(hwnd):
                self.logger.error("窗口句柄无效")
                return False

            # 2. 如果窗口最小化，先恢复
            if win32gui.IsIconic(hwnd):
                self.logger.debug("窗口已最小化，正在恢复...")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                self._natural_gui._random_pause(0.4, 0.7)

            # 3. 如果窗口不可见，显示它
            if not win32gui.IsWindowVisible(hwnd):
                self.logger.debug("窗口不可见，正在显示...")
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                self._natural_gui._random_pause(0.4, 0.7)

            # 4. 尝试标准置顶
            try:
                win32gui.SetForegroundWindow(hwnd)
                self._natural_gui._random_pause(0.15, 0.3)
            except Exception as e:
                self.logger.debug(f"标准置顶失败: {e}")

            # 5. 检查是否已经置顶
            if win32gui.GetForegroundWindow() == hwnd:
                self.logger.debug("窗口已成功激活")
                return True

            # 6. 如果标准置顶失败，使用多种方法绕过 Foreground Lock
            try:
                from ctypes import windll

                # 6.1 先尝试模拟 Alt 按键（这会临时解除前台锁定）
                try:
                    self.logger.debug("尝试模拟 Alt 键解除前台锁定...")
                    windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt down
                    windll.user32.keybd_event(0x12, 0, 0x0002, 0)  # Alt up
                    self._natural_gui._random_pause(0.05, 0.1)
                    win32gui.SetForegroundWindow(hwnd)
                except Exception as e:
                    self.logger.debug(f"Alt 键方法失败: {e}")

                # 6.2 使用 AttachThreadInput 方法
                foreground_hwnd = win32gui.GetForegroundWindow()
                if foreground_hwnd != 0 and foreground_hwnd != hwnd:
                    foreground_thread_id = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
                    target_thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]
                    current_thread_id = windll.kernel32.GetCurrentThreadId()

                    self.logger.debug("使用 AttachThreadInput 方法激活窗口...")
                    # 方法 1: 附加当前线程到前台线程
                    try:
                        windll.user32.AttachThreadInput(current_thread_id, foreground_thread_id, True)
                        win32gui.SetForegroundWindow(hwnd)
                        win32gui.SetFocus(hwnd)
                        windll.user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)
                    except Exception as e:
                        self.logger.debug(f"AttachThreadInput (方法1) 失败: {e}")

                    # 方法 2: 附加目标线程到前台线程
                    try:
                        windll.user32.AttachThreadInput(target_thread_id, foreground_thread_id, True)
                        win32gui.SetForegroundWindow(hwnd)
                        win32gui.SetFocus(hwnd)
                        windll.user32.AttachThreadInput(target_thread_id, foreground_thread_id, False)
                    except Exception as e:
                        self.logger.debug(f"AttachThreadInput (方法2) 失败: {e}")

                # 6.3 使用 BringWindowToTop 和 SetWindowPos
                try:
                    win32gui.BringWindowToTop(hwnd)
                    # HWND_TOPMOST = -1, SWP_NOMOVE | SWP_NOSIZE = 0x0003
                    windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0003)
                    self._natural_gui._random_pause(0.05, 0.1)
                    # HWND_NOTOPMOST = -2
                    windll.user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0003)
                    win32gui.SetForegroundWindow(hwnd)
                except Exception as e:
                    self.logger.debug(f"BringWindowToTop 方法失败: {e}")
            except Exception as e:
                self.logger.debug(f"高级激活方法失败: {e}")

            # 7. 等待并验证置顶结果
            self._natural_gui._random_pause(0.2, 0.4)
            for _ in range(5):  # 最多重试 5 次
                if win32gui.GetForegroundWindow() == hwnd:
                    self.logger.debug("窗口激活成功")
                    return True
                self._natural_gui._random_pause(0.08, 0.15)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass

            # 8. 最终检查
            if win32gui.GetForegroundWindow() != hwnd:
                self.logger.error("无法将微信窗口置于前台，操作中止（防止误操作其他窗口）")
                return False

            return True
        except Exception as e:
            self.logger.error(f"Failed to activate window: {e}")
            return False
