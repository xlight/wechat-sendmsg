#!/usr/bin/env python3
"""
系统托盘图标管理器
通过跨进程内存读取和托盘回调消息模拟，实现微信托盘图标的双击恢复功能。
"""

import ctypes
import logging
import struct
import time
import re
from typing import Any, Dict, List, Optional

import psutil
import win32api
import win32gui
import win32process


logger = logging.getLogger(__name__)


class TrayManagerMixin:
    """系统托盘操作 Mixin，提供托盘图标查找和双击模拟功能。

    通过读取 ToolbarWindow32 的 TBBUTTON 结构获取托盘图标的回调参数，
    然后发送与 Windows Shell 双击行为一致的回调消息来恢复窗口。
    """

    # ── 托盘操作相关常量 ──────────────────────────────────────────
    _PROCESS_VM_OPERATION = 0x0008
    _PROCESS_VM_READ = 0x0010
    _PROCESS_VM_WRITE = 0x0020
    _MEM_COMMIT = 0x1000
    _MEM_RESERVE = 0x2000
    _MEM_RELEASE = 0x8000
    _PAGE_READWRITE = 0x04
    _TB_BUTTONCOUNT = 0x0418
    _TB_GETBUTTON = 0x0417
    _TBBUTTON_SIZE_64 = 32  # 64位系统 TBBUTTON 结构大小
    _WM_LBUTTONDBLCLK = 0x0203
    _WECHAT_PROCESS_NAMES = ['Weixin.exe', 'WeChat.exe', 'WeChatAppEx.exe']

    def _get_tray_toolbar_hwnd(self) -> Optional[int]:
        """获取系统托盘主工具栏的窗口句柄。

        遍历路径: Shell_TrayWnd -> TrayNotifyWnd -> SysPager -> ToolbarWindow32
        """
        tray = win32gui.FindWindow("Shell_TrayWnd", None)
        if not tray:
            return None
        notify = win32gui.FindWindowEx(tray, 0, "TrayNotifyWnd", None)
        if not notify:
            return None
        syspager = win32gui.FindWindowEx(notify, 0, "SysPager", None)
        if not syspager:
            return None
        toolbar = win32gui.FindWindowEx(syspager, 0, "ToolbarWindow32", None)
        return toolbar

    def _get_overflow_toolbar_hwnd(self) -> Optional[int]:
        """获取溢出托盘（隐藏图标区域）的工具栏句柄。"""
        overflow = win32gui.FindWindow("NotifyIconOverflowWindow", None)
        if not overflow:
            return None
        toolbar = win32gui.FindWindowEx(overflow, 0, "ToolbarWindow32", None)
        return toolbar

    def _read_tray_buttons(self, toolbar_hwnd: int) -> List[Dict[str, Any]]:
        """读取托盘工具栏中所有按钮的回调信息。

        通过跨进程内存读取 (VirtualAllocEx + ReadProcessMemory) 获取
        每个托盘图标对应的 TBBUTTON 结构中的 dwData 回调数据。

        Args:
            toolbar_hwnd: ToolbarWindow32 的窗口句柄

        Returns:
            按钮信息列表，每项包含 callback_hwnd, callback_uid, callback_msg, process_name, tooltip
        """
        _, toolbar_pid = win32process.GetWindowThreadProcessId(toolbar_hwnd)

        kernel32 = ctypes.windll.kernel32
        h_process = kernel32.OpenProcess(
            self._PROCESS_VM_OPERATION | self._PROCESS_VM_READ | self._PROCESS_VM_WRITE,
            False,
            toolbar_pid
        )
        if not h_process:
            self.logger.error("无法打开托盘进程")
            return []

        try:
            remote_buf = kernel32.VirtualAllocEx(
                h_process, None, 0x1000,
                self._MEM_COMMIT | self._MEM_RESERVE, self._PAGE_READWRITE
            )
            if not remote_buf:
                self.logger.error("无法分配远程内存")
                return []

            try:
                button_count = win32gui.SendMessage(toolbar_hwnd, self._TB_BUTTONCOUNT, 0, 0)
                self.logger.debug(f"托盘按钮数量: {button_count}")

                results: List[Dict[str, Any]] = []
                bytes_read = ctypes.c_size_t()

                for i in range(button_count):
                    # 将按钮数据写入远程缓冲区
                    win32gui.SendMessage(toolbar_hwnd, self._TB_GETBUTTON, i, remote_buf)

                    # 读取 TBBUTTON 结构
                    tb_data = ctypes.create_string_buffer(self._TBBUTTON_SIZE_64)
                    kernel32.ReadProcessMemory(
                        h_process, remote_buf,
                        tb_data, self._TBBUTTON_SIZE_64,
                        ctypes.byref(bytes_read)
                    )

                    # 解析 TBBUTTON (64位):
                    # iBitmap(4) + idCommand(4) + fsState(1) + fsStyle(1) + bReserved(6) + dwData(8) + iString(8)
                    dwData = struct.unpack_from('<Q', tb_data.raw, 16)[0]
                    iString = struct.unpack_from('<Q', tb_data.raw, 24)[0]

                    # 读取 dwData 指向的回调信息:
                    # callback_hwnd(8) + callback_uid(4) + callback_msg(4)
                    callback_hwnd = 0
                    callback_uid = 0
                    callback_msg = 0
                    if dwData:
                        extra_data = ctypes.create_string_buffer(32)
                        kernel32.ReadProcessMemory(
                            h_process, ctypes.c_void_p(dwData),
                            extra_data, 32,
                            ctypes.byref(bytes_read)
                        )
                        callback_hwnd = struct.unpack_from('<Q', extra_data.raw, 0)[0]
                        callback_uid = struct.unpack_from('<I', extra_data.raw, 8)[0]
                        callback_msg = struct.unpack_from('<I', extra_data.raw, 12)[0]

                    # 获取按钮提示文本
                    tooltip = ""
                    if iString and iString != 0xFFFFFFFFFFFFFFFF:
                        tip_buf = ctypes.create_unicode_buffer(256)
                        kernel32.ReadProcessMemory(
                            h_process, ctypes.c_void_p(iString),
                            tip_buf, 512,
                            ctypes.byref(bytes_read)
                        )
                        tooltip = tip_buf.value

                    # 获取回调窗口所属进程名
                    process_name = ""
                    if callback_hwnd:
                        try:
                            _, cb_pid = win32process.GetWindowThreadProcessId(int(callback_hwnd))
                            if cb_pid:
                                proc = psutil.Process(cb_pid)
                                process_name = proc.name()
                        except Exception:
                            pass

                    results.append({
                        'callback_hwnd': callback_hwnd,
                        'callback_uid': callback_uid,
                        'callback_msg': callback_msg,
                        'process_name': process_name,
                        'tooltip': tooltip,
                    })

                return results
            finally:
                kernel32.VirtualFreeEx(h_process, remote_buf, 0, self._MEM_RELEASE)
        finally:
            kernel32.CloseHandle(h_process)

    def _find_wechat_tray_icon(self) -> Optional[Dict[str, Any]]:
        """在系统托盘和溢出托盘中查找微信图标。

        Returns:
            微信图标的回调信息字典，未找到返回 None
        """
        # 在主托盘区域查找
        toolbar = self._get_tray_toolbar_hwnd()
        if toolbar:
            self.logger.debug(f"主托盘工具栏: {toolbar}")
            buttons = self._read_tray_buttons(toolbar)
            for btn in buttons:
                if btn['process_name'] in self._WECHAT_PROCESS_NAMES:
                    self.logger.info(f"在主托盘中找到微信图标 (进程: {btn['process_name']})")
                    return btn
                if '微信' in btn.get('tooltip', '') or 'WeChat' in btn.get('tooltip', ''):
                    self.logger.info(f"在主托盘中找到微信图标 (tooltip: {btn['tooltip']})")
                    return btn

        # 在溢出托盘查找
        overflow_toolbar = self._get_overflow_toolbar_hwnd()
        if overflow_toolbar:
            self.logger.debug(f"溢出托盘工具栏: {overflow_toolbar}")
            buttons = self._read_tray_buttons(overflow_toolbar)
            for btn in buttons:
                if btn['process_name'] in self._WECHAT_PROCESS_NAMES:
                    self.logger.info(f"在溢出托盘中找到微信图标 (进程: {btn['process_name']})")
                    return btn
                if '微信' in btn.get('tooltip', '') or 'WeChat' in btn.get('tooltip', ''):
                    self.logger.info(f"在溢出托盘中找到微信图标 (tooltip: {btn['tooltip']})")
                    return btn

        self.logger.warning("未找到微信托盘图标")
        return None

    def _restore_from_systray(self) -> Optional[int]:
        """通过模拟双击托盘图标恢复微信窗口。

        原理: 向微信的回调窗口发送与 Windows Shell 双击托盘图标相同的回调消息，
        使微信恢复完整功能的主窗口。

        Returns:
            恢复成功返回主窗口句柄，失败返回 None
        """
        icon_info = self._find_wechat_tray_icon()
        if not icon_info:
            self.logger.warning("无法从托盘恢复: 未找到微信托盘图标")
            return None

        callback_hwnd = int(icon_info['callback_hwnd'])
        callback_msg = int(icon_info['callback_msg'])
        callback_uid = int(icon_info['callback_uid'])

        self.logger.info(
            f"模拟双击托盘图标: cb_hwnd={callback_hwnd:#x}, "
            f"cb_msg={callback_msg:#x}, cb_uid={callback_uid}"
        )

        # 发送与 Windows Shell 双击托盘图标相同的回调消息
        win32api.PostMessage(callback_hwnd, callback_msg, callback_uid, self._WM_LBUTTONDBLCLK)

        # 等待窗口恢复并查找主窗口
        for attempt in range(10):
            time.sleep(0.3)
            found_hwnd = self._find_restored_main_window()
            if found_hwnd:
                self.logger.info(f"托盘恢复成功 (第 {attempt + 1} 次检查): hwnd={found_hwnd}")
                return found_hwnd

        self.logger.warning("托盘双击后未检测到可见的微信主窗口")
        return None

    def _find_restored_main_window(self) -> Optional[int]:
        """查找已恢复的可见微信主窗口（仅检查可见窗口）。

        此方法专门用于托盘恢复后的窗口检测，只返回可见的主窗口。
        """
        result: List[int] = []

        def _callback(hwnd: int, _: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            class_name = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            if window_text not in ["微信", "WeChat"]:
                return True

            # 检查是否是微信进程
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                if proc.name() not in self._WECHAT_PROCESS_NAMES:
                    return True
            except Exception:
                return True

            # 检查窗口类型和大小
            if re.match(r"Qt\d+QWindowIcon", class_name) or re.match(r"Qt\d+QWindowOwnDC", class_name):
                rect = win32gui.GetWindowRect(hwnd)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                if width >= 800 or height >= 800:
                    result.append(hwnd)
            elif class_name == "WeChatMainWndForPC":
                result.append(hwnd)

            return True

        win32gui.EnumWindows(_callback, None)
        return result[0] if result else None
