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
                            time.sleep(0.5)
                        # 如果窗口隐藏，显示它
                        if not win_info['visible']:
                            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                            time.sleep(0.5)
                        # 激活窗口
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.3)
                        
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
                    pyautogui.click(int(click_x), int(click_y))
                    time.sleep(0.4)
                    pyautogui.typewrite('a')
                    time.sleep(0.1)
                    pyautogui.press('backspace')
                    time.sleep(0.1)
                    return True
                except Exception:
                    continue

            self.logger.error("All input box positions failed")
            return False
        except Exception as e:
            self.logger.error(f"Failed to locate input box: {e}")
            return False

    def _paste_text_via_clipboard(self, text: str) -> Optional[str]:
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

        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.12)
        pyautogui.press('delete')
        time.sleep(0.25)

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

        time.sleep(0.25)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.6)
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
        try:
            original_data = self._paste_text_via_clipboard(text)
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
            time.sleep(1.0)
            
            # 清空搜索框
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.press('delete')
            time.sleep(0.2)

            # 输入联系人名称
            original_data = self._paste_text_via_clipboard(contact_name)

            # 回车打开聊天
            pyautogui.press('enter')
            time.sleep(1.0)
            
            # 关闭搜索框（按 Escape 关闭搜索框，不会关闭聊天窗口）
            pyautogui.press('escape')
            time.sleep(0.3)

            self.logger.debug(f"成功搜索并打开: {contact_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to search contact in NT: {e}")
            return False
        finally:
            self._restore_clipboard(original_data)

    def _send_text_nt(self, message: str) -> bool:
        try:
            if not self._find_and_click_input_box():
                # 尝试再次寻找
                time.sleep(0.5)
                if not self._find_and_click_input_box():
                    return False

            original_data = self._paste_text_via_clipboard(message)

            try:
                pyautogui.press('enter')
                time.sleep(0.6)
                # 尝试恢复剪贴板，但失败不影响发送结果
                try:
                    self._restore_clipboard(original_data)
                except Exception:
                    pass
                return True
            except Exception:
                try:
                    pyautogui.hotkey('ctrl', 'enter')
                    time.sleep(0.6)
                    # 尝试恢复剪贴板，但失败不影响发送结果
                    try:
                        self._restore_clipboard(original_data)
                    except Exception:
                        pass
                    return True
                except Exception:
                    try:
                        pyautogui.hotkey('alt', 's')
                        time.sleep(0.6)
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
    
    def read_chat_messages(self, group_name: str) -> Optional[str]:
        """通过 GUI 自动化读取指定群聊的可见消息文本。

        流程：搜索并切换到目标群聊 → 选中聊天区域 → 复制到剪贴板 → 返回文本。

        Args:
            group_name: 目标群聊名称

        Returns:
            聊天记录文本，失败时返回 None
        """
        try:
            hwnd = self._find_wechat_window()
            if not hwnd:
                self.logger.error("微信窗口未找到，无法读取消息（检查微信是否在运行且未最小化）")
                return None

            # 检查窗口是否可见
            if not win32gui.IsWindowVisible(hwnd):
                self.logger.error("微信窗口不可见，无法读取消息")
                return None

            # 暂时注释掉窗口激活（避免后台窗口问题）
            # if not self._activate_window(hwnd):
            #     self.logger.error("无法激活微信窗口（可能被其他窗口覆盖）")
            #     return None

            # # 等待窗口激活稳定
            # time.sleep(0.5)

            # # 再次验证窗口句柄
            # hwnd_check = self._find_wechat_window()
            # if not hwnd_check or hwnd_check != hwnd:
            #     self.logger.error("微信窗口句柄在激活后发生变化")
            #     return None

            # 搜索并切换到目标群聊
            self.logger.debug(f"开始搜索群聊: {group_name}")
            if not self._search_contact_nt(group_name):
                self.logger.error(f"无法切换到群聊: {group_name}（检查群聊名称是否精确匹配）")
                return None

            time.sleep(0.8)

            # 二次确认焦点
            if win32gui.GetForegroundWindow() != hwnd:
                self.logger.warning("微信未获得焦点，但继续尝试读取消息")
                # return None  # 不直接返回，尝试继续

            # 定位聊天记录区域并选中内容
            rect = win32gui.GetWindowRect(hwnd)
            window_left, window_top, window_right, window_bottom = rect
            window_width = window_right - window_left
            window_height = window_bottom - window_top

            # 点击聊天记录区域中央（输入框上方）
            chat_center_x = window_left + window_width // 2
            chat_center_y = window_top + int(window_height * 0.45)
            pyautogui.click(int(chat_center_x), int(chat_center_y))
            time.sleep(0.4)

            # 备份剪贴板
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

            # 全选聊天记录并复制
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.4)

            # 从剪贴板读取内容
            chat_text: Optional[str] = None
            win32clipboard.OpenClipboard()
            try:
                try:
                    chat_text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                except Exception:
                    chat_text = None
            finally:
                win32clipboard.CloseClipboard()

            # 恢复剪贴板
            self._restore_clipboard(original_data)

            # 取消选中 - 点击输入框而不是按 Escape（避免关闭窗口）
            input_box_x = window_left + window_width // 2
            input_box_y = window_bottom - 80
            pyautogui.click(int(input_box_x), int(input_box_y))
            time.sleep(0.2)

            if not chat_text:
                self.logger.warning(f"未能从群聊 {group_name} 读取到消息")
                return None

            self.logger.debug(f"成功读取群聊消息，共 {len(chat_text)} 字符")
            return chat_text

        except Exception as e:
            self.logger.error(f"读取群聊消息时出错: {e}")
            return None

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
