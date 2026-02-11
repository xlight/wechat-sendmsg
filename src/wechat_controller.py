#!/usr/bin/env python3
"""
微信控制器
处理微信自动化发送消息功能。
仅支持 NT 架构（WeChat 4.0+）；低于 4.0 的版本直接跳过。
"""

import asyncio
import io
import logging
import sys
import time
from typing import Any, Dict, Optional

import psutil
import pyautogui
import win32api
import win32con
import win32gui
import win32clipboard

try:
    from .anti_ban import NaturalGUIOperations
except ImportError:
    from anti_ban import NaturalGUIOperations

class WeChatController:
    """微信自动化操作控制器（仅 NT 版本）。"""

    def __init__(self):
        # 设置日志级别为DEBUG
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.3

        self.wechat_version: Optional[str] = None
        self.is_nt_version: bool = False
        self._last_window_kind: Optional[str] = None

        # 初始化自然 GUI 操作工具
        self._natural_gui = NaturalGUIOperations()

        self._detect_wechat_version()

    def _detect_wechat_version(self) -> Optional[str]:
        try:
            window_hwnd = self._find_wechat_window()
            window_is_nt = self._last_window_kind == "nt" and window_hwnd is not None

            for proc in psutil.process_iter(['name', 'exe']):
                name = proc.info.get('name') or ""
                if 'wechat' not in name.lower():
                    continue

                exe = proc.info.get('exe')
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
        import re

        # 首先检查微信进程是否在运行
        wechat_process_running = False
        for proc in psutil.process_iter(['name']):
            name = proc.info.get('name') or ""
            if 'wechat' in name.lower():
                wechat_process_running = True
                self.logger.debug(f"检测到微信进程: {name}")
                break

        if not wechat_process_running:
            self.logger.warning("微信进程未运行")
            return None

        main_windows = []  # 主窗口（最高优先级）
        contact_list_windows = []  # 联系人列表窗口（次优先级）
        chat_windows = []  # 聊天窗口（低优先级，尽量避免）
        all_wechat_windows = []  # 所有微信窗口（用于调试）

        def enum_windows_callback(hwnd, _):
            class_name = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            is_visible = win32gui.IsWindowVisible(hwnd)

            # 记录所有可能的微信窗口
            if "WeChat" in class_name or "微信" in window_text or "WeChat" in window_text:
                all_wechat_windows.append({
                    'hwnd': hwnd,
                    'class': class_name,
                    'text': window_text,
                    'visible': is_visible,
                    'iconic': win32gui.IsIconic(hwnd)
                })

            if not is_visible:
                return True

            # 【最高优先级】主窗口类名（微信 NT 框架主窗口）
            if class_name == "WeChatMainWndForPC":
                self.logger.debug(f"找到主窗口: hwnd={hwnd}, class={class_name}, text={window_text}")
                main_windows.append(hwnd)
                return True

            # 【次优先级】联系人列表窗口（通常标题只有"微信"或"WeChat"）
            if re.match(r"Qt\d+QWindowIcon", class_name) or re.match(r"Qt\d+QWindowOwnDC", class_name):
                # 标题只有"微信"或"WeChat"，没有聊天对象名称
                if window_text in ["微信", "WeChat"]:
                    self.logger.debug(f"找到联系人列表窗口: hwnd={hwnd}, class={class_name}, text={window_text}")
                    contact_list_windows.append(hwnd)
                    return True
                # 标题包含聊天对象名称，这是聊天窗口
                elif "微信" in window_text or "WeChat" in window_text:
                    self.logger.debug(f"找到聊天窗口（跳过）: hwnd={hwnd}, class={class_name}, text={window_text}")
                    chat_windows.append(hwnd)
                    return True

            # 【低优先级】ChatWnd 类名（聊天悬浮窗，尽量避免）
            if class_name == "ChatWnd":
                self.logger.debug(f"找到聊天悬浮窗（跳过）: hwnd={hwnd}, class={class_name}, text={window_text}")
                chat_windows.append(hwnd)
                return True

            # 其他包含"微信"的窗口
            if "微信" in window_text or "WeChat" in window_text:
                self.logger.debug(f"找到其他微信窗口: hwnd={hwnd}, class={class_name}, text={window_text}")
                chat_windows.append(hwnd)

            return True

        win32gui.EnumWindows(enum_windows_callback, None)

        self.logger.debug(f"窗口统计 - 主窗口: {len(main_windows)}, 联系人列表: {len(contact_list_windows)}, 聊天窗口: {len(chat_windows)}")

        # 【优先级 1】返回主窗口
        if main_windows:
            self._last_window_kind = "nt"
            self.logger.info(f"✅ 找到主窗口: hwnd={main_windows[0]}")
            return main_windows[0]

        # 【优先级 2】返回联系人列表窗口
        if contact_list_windows:
            self._last_window_kind = "nt"
            self.logger.info(f"✅ 找到联系人列表窗口: hwnd={contact_list_windows[0]}")
            return contact_list_windows[0]

        # 【优先级 3】如果只有聊天窗口，发出警告但仍然返回
        if chat_windows:
            self._last_window_kind = "nt"
            self.logger.warning(f"⚠️  仅找到聊天窗口，建议打开微信主窗口: hwnd={chat_windows[0]}")
            return chat_windows[0]

        # 如果没有可见窗口，尝试从所有窗口中恢复主窗口
        if all_wechat_windows:
            self.logger.info(f"未找到可见微信窗口，发现 {len(all_wechat_windows)} 个微信窗口（可能在托盘中）")
            for win_info in all_wechat_windows:
                self.logger.debug(f"  - hwnd={win_info['hwnd']}, class={win_info['class']}, "
                                f"text={win_info['text']}, visible={win_info['visible']}, "
                                f"iconic={win_info['iconic']}")

                # 优先恢复主窗口
                if win_info['class'] == "WeChatMainWndForPC":
                    hwnd = win_info['hwnd']
                    self.logger.info(f"尝试恢复微信主窗口: hwnd={hwnd}")
                    try:
                        # 如果窗口最小化，先恢复
                        if win_info['iconic']:
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            time.sleep(10.5)
                        # 如果窗口隐藏，显示它
                        if not win_info['visible']:
                            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                            time.sleep(10.5)
                        # 激活窗口
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(10.3)

                        # 验证窗口现在是否可见
                        if win32gui.IsWindowVisible(hwnd):
                            self.logger.info("✅ 成功恢复微信主窗口")
                            self._last_window_kind = "nt"
                            return hwnd
                    except Exception as e:
                        self.logger.warning(f"恢复主窗口失败: {e}")
                        continue

                # 次优先级：恢复联系人列表窗口
                if win_info['text'] in ["微信", "WeChat"] and "Qt" in win_info['class']:
                    hwnd = win_info['hwnd']
                    self.logger.info(f"尝试恢复联系人列表窗口: hwnd={hwnd}")
                    try:
                        if win_info['iconic']:
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            time.sleep(0.5)
                        if not win_info['visible']:
                            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                            time.sleep(0.5)
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.3)

                        if win32gui.IsWindowVisible(hwnd):
                            self.logger.info("✅ 成功恢复联系人列表窗口")
                            self._last_window_kind = "nt"
                            return hwnd
                    except Exception as e:
                        self.logger.warning(f"恢复联系人列表窗口失败: {e}")
                        continue

        self._last_window_kind = None
        self.logger.warning("微信进程在运行，但无法找到或恢复微信主窗口（请手动打开微信主窗口）")
        return None

    def _ensure_modifiers_released(self):
        """确保所有修饰键都已释放"""
        import ctypes
        keys = [0x10, 0x11, 0x12] # Shift, Ctrl, Alt
        for key in keys:
            if ctypes.windll.user32.GetKeyState(key) & 0x8000:
                ctypes.windll.user32.keybd_event(key, 0, 0x0002, 0) # Key up

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
                time.sleep(0.5)

            # 3. 如果窗口不可见，显示它
            if not win32gui.IsWindowVisible(hwnd):
                self.logger.debug("窗口不可见，正在显示...")
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                time.sleep(0.5)

            # 4. 尝试标准置顶
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
            except Exception as e:
                self.logger.debug(f"标准置顶失败: {e}")

            # 5. 检查是否已经置顶
            if win32gui.GetForegroundWindow() == hwnd:
                self.logger.debug("✅ 窗口已成功激活")
                return True

            # 6. 如果标准置顶失败，使用 AttachThreadInput 大法
            # 这是官方推荐的绕过 Foreground Lock 的方法
            try:
                import win32process
                import ctypes
                from ctypes import windll

                foreground_hwnd = win32gui.GetForegroundWindow()
                if foreground_hwnd != 0:
                    foreground_thread_id = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
                    current_thread_id = windll.kernel32.GetCurrentThreadId()

                    if foreground_thread_id != current_thread_id:
                        self.logger.debug("使用 AttachThreadInput 方法激活窗口...")
                        # 附加输入上下文
                        windll.user32.AttachThreadInput(current_thread_id, foreground_thread_id, True)
                        # 再次尝试置顶
                        try:
                            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                            win32gui.SetForegroundWindow(hwnd)
                            win32gui.SetFocus(hwnd)
                        except Exception:
                            pass
                        # 解除附加
                        windll.user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)
            except Exception as e:
                self.logger.debug(f"AttachThreadInput 失败: {e}")

            # 7. 等待并验证置顶结果
            time.sleep(0.3)
            for _ in range(5):  # 最多重试 5 次
                if win32gui.GetForegroundWindow() == hwnd:
                    self.logger.debug("✅ 窗口激活成功")
                    return True
                time.sleep(0.1)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass

            # 8. 最终检查
            if win32gui.GetForegroundWindow() != hwnd:
                self.logger.error("❌ 无法将微信窗口置于前台，操作中止（防止误操作其他窗口）")
                return False

            return True
        except Exception as e:
            self.logger.error(f"Failed to activate window: {e}")
            return False

    def _find_and_click_input_box(self) -> bool:
        try:
            hwnd = self._find_wechat_window()
            self.logger.error(f"寻找输入框，当前微信窗口句柄: {hwnd}")
            if not hwnd:
                self.logger.error("WeChat window not found")
                return False

            rect = win32gui.GetWindowRect(hwnd)
            window_left, window_top, window_right, window_bottom = rect
            window_width = window_right - window_left

            input_positions = [
                (window_left + window_width // 2, window_bottom - 80),
                (window_left + window_width // 2, window_bottom - 120),
                (window_left + window_width // 3, window_bottom - 100),
                (window_left + window_width * 2 // 3, window_bottom - 100),
                (pyautogui.size()[0] // 2, int(pyautogui.size()[1] * 0.85)),
            ]

            for click_x, click_y in input_positions:
                try:
                    # 使用自然点击代替直接点击
                    self._natural_gui.natural_click(int(click_x), int(click_y))
                    self.logger.error(f"尝试点击输入框位置: ({click_x}, {click_y})")
                    time.sleep(5.4)
                    pyautogui.typewrite('a')
                    self.logger.error("输入测试字符 'a' 来验证输入框是否激活")
                    time.sleep(5.1)
                    pyautogui.press('backspace')
                    self.logger.error("删除测试字符 'a'")
                    time.sleep(5.1)
                    return True
                except Exception:
                    continue

            self.logger.error("All input box positions failed")
            return False
        except Exception as e:
            self.logger.error(f"Failed to locate input box: {e}")
            return False

    def _set_clipboard_and_paste(self, text: str) -> Optional[str]:
        """备份剪贴板，设置新内容并粘贴到当前焦点位置。

        注意：此方法不会清空输入框，调用方需要在调用前自行清空。

        Args:
            text: 要粘贴的文本内容

        Returns:
            原剪贴板内容（用于后续恢复），失败返回 None
        """
        # 备份原剪贴板内容
        original_data: Optional[str] = None
        win32clipboard.OpenClipboard()
        try:
            try:
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                if isinstance(data, str):
                    original_data = data
            except Exception:
                original_data = None
        finally:
            win32clipboard.CloseClipboard()

        # 设置新的剪贴板内容
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

        # 验证剪贴板内容是否设置成功
        time.sleep(0.1)
        win32clipboard.OpenClipboard()
        try:
            verify = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            if verify != text:
                self.logger.error(f"剪贴板验证失败！期望: {text[:20]}, 实际: {verify[:20] if verify else 'None'}")
            else:
                self.logger.debug(f"剪贴板设置成功: {text[:20]}...")
        finally:
            win32clipboard.CloseClipboard()

        # 等待剪贴板稳定
        time.sleep(0.2)

        # 执行粘贴操作 - 使用更可靠的方式
        self.logger.debug("执行粘贴操作 (Ctrl+V)...")
        pyautogui.keyDown('ctrl')
        time.sleep(0.05)
        pyautogui.press('v')
        time.sleep(0.05)
        pyautogui.keyUp('ctrl')

        # 等待粘贴完成
        time.sleep(0.5)
        self.logger.debug("粘贴操作完成")
        return original_data

    def _restore_clipboard(self, original_data: Optional[str]) -> None:
        if not original_data:
            return
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_data, win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return

    def _input_text_via_clipboard(self, text: str) -> bool:
        """清空当前输入框并通过剪贴板输入文本。

        此方法会：
        1. 全选并删除当前内容
        2. 通过剪贴板粘贴新文本
        3. 恢复原剪贴板内容

        Args:
            text: 要输入的文本

        Returns:
            成功返回 True，失败返回 False
        """
        try:
            # 清空当前输入框
            pyautogui.hotkey('ctrl', 'a')
            self._natural_gui._random_pause()
            pyautogui.press('delete')
            self._natural_gui._random_pause(0.15, 0.35)

            # 粘贴文本
            original_data = self._set_clipboard_and_paste(text)
            self._restore_clipboard(original_data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to input text via clipboard: {e}")
            return False

    def _search_contact_nt(self, contact_name: str) -> bool:
        """搜索联系人/群聊并打开聊天窗口（NT 框架）。"""
        # Double check focus before typing
        hwnd = self._find_wechat_window()
        if not hwnd or win32gui.GetForegroundWindow() != hwnd:
             self.logger.error("WeChat not focused, aborting search")
             return False

        original_data: Optional[str] = None
        try:
            # 打开搜索框
            pyautogui.hotkey('ctrl', 'f')
            self.logger.error("打开搜索框 (Ctrl+F)")
            time.sleep(3.0)

            # 清空搜索框
            pyautogui.hotkey('ctrl', 'a')
            self.logger.error("全选搜索框内容 (Ctrl+A)")
            time.sleep(2.2)
            pyautogui.press('delete')
            self.logger.error("清空搜索框内容 (Delete)")
            time.sleep(2.2)

            # 输入联系人名称（粘贴）
            original_data = self._set_clipboard_and_paste(contact_name)
            self.logger.error(f"输入联系人名称: {contact_name}")
            time.sleep(5.2)

            # 回车打开聊天
            pyautogui.press('enter')
            time.sleep(5.0)

            # 关闭聊天窗口
            # pyautogui.press('escape')
            # time.sleep(5.3)

            self.logger.debug(f"成功搜索并打开: {contact_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to search contact in NT: {e}")
            return False
        finally:
            self._restore_clipboard(original_data)

    def _send_text_nt(self, message: str) -> bool:
        self.logger.debug(f"准备发送消息: {message[:20]}...")
        try:
            if not self._find_and_click_input_box():
                self.logger.error("输入框未找到，无法发送消息")
                # 尝试再次寻找
                time.sleep(5.5)
                if not self._find_and_click_input_box():
                    self.logger.error("再次尝试寻找输入框失败，发送消息中止")
                    return False
            self.logger.debug("输入框已点击，准备输入消息...")
            time.sleep(5.5)  # 等待输入框稳定

            # 清空输入框（以防有残留内容）
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.press('delete')
            time.sleep(0.3)

            # 粘贴消息内容
            original_data = self._set_clipboard_and_paste(message)
            self.logger.debug("文本输入完成，准备发送...")
            time.sleep(5.5)  # 等待输入稳定
            try:
                pyautogui.press('enter')
                self.logger.debug("按下 Enter 键发送消息")
                time.sleep(5.6)
                # 尝试恢复剪贴板，但失败不影响发送结果
                try:
                    self._restore_clipboard(original_data)
                    self.logger.debug("剪贴板已恢复")
                except Exception:
                    pass
                return True
            except Exception:
                try:
                    pyautogui.hotkey('ctrl', 'enter')
                    self.logger.debug("按下 Ctrl+Enter 键发送消息")
                    time.sleep(5.6)
                    # 尝试恢复剪贴板，但失败不影响发送结果
                    try:
                        self._restore_clipboard(original_data)
                    except Exception:
                        pass
                    return True
                except Exception:
                    try:
                        pyautogui.hotkey('alt', 's')
                        self.logger.debug("按下 Alt+S 键发送消息")
                        time.sleep(10.6)
                        # 尝试恢复剪贴板，但失败不影响发送结果
                        try:
                            self._restore_clipboard(original_data)
                        except Exception:
                            pass
                        return True
                    except Exception:
                        return False
        except Exception as e:
            self.logger.error(f"Failed to send text in NT: {e}")
            return False

    async def send_text_message(self, contact_name: str, message: str) -> Dict[str, Any]:
        """向指定联系人发送文本消息。"""
        result: Dict[str, Any] = {
            "ok": False,
            "contact_name": contact_name,
            "wechat_version": None,
            "is_nt_framework": False,
            "stage": None,
            "reason": None,
            "retry_used": None,
        }
        try:
            version = self._detect_wechat_version()
            result["wechat_version"] = version
            result["is_nt_framework"] = self.is_nt_version

            if not self.is_nt_version:
                result["stage"] = "version_check"
                result["reason"] = "non_nt_version_skipped"
                return result

            hwnd = self._find_wechat_window()
            if not hwnd:
                result["stage"] = "find_window"
                result["reason"] = "wechat_window_not_found"
                return result

            if not self._activate_window(hwnd):
                result["stage"] = "activate_window"
                result["reason"] = "failed_to_activate_window"
                return result
            if not self._search_contact_nt(contact_name):
                result["stage"] = "search_contact"
                result["reason"] = "search_failed"
                return result
            self.logger.debug("联系人已打开，准备发送消息...")
            if self._send_text_nt(message):
                result["ok"] = True
                result["stage"] = "send_text"
                result["reason"] = None
                return result

            result["stage"] = "send_text"
            result["reason"] = "send_failed"
            return result

        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            result["stage"] = result["stage"] or "exception"
            result["reason"] = str(e)
            return result

    async def schedule_message(self, contact_name: str, message: str, delay_seconds: float) -> bool:
        """安排在延迟后发送消息。"""
        try:
            self.logger.info(f"Scheduling message to {contact_name} in {delay_seconds} seconds")

            async def delayed_send():
                await asyncio.sleep(delay_seconds)
                # 调用异步函数
                try:
                    await self.send_text_message(contact_name, message)
                except Exception as e:
                    self.logger.error(f"Error in delayed send: {e}")

            # 创建异步任务
            asyncio.create_task(delayed_send())

            return True

        except Exception as e:
            self.logger.error(f"Error scheduling message: {e}")
            return False


    def get_status(self) -> Dict[str, Any]:
        """获取微信控制器的当前状态。"""
        try:
            version = self._detect_wechat_version()
            hwnd = self._find_wechat_window()
            return {
                "wechat_available": hwnd is not None,
                "window_handle": hwnd,
                "wechat_version": version,
                "is_nt_framework": self.is_nt_version,
                "supported": self.is_nt_version,
                "framework_type": "NT framework (4.0+)" if self.is_nt_version else "Legacy (<4.0, skipped)"
            }
        except Exception as e:
            self.logger.error(f"Error checking status: {e}")
            return {
                "wechat_available": False,
                "error": str(e)
            }
