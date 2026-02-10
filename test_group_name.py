#!/usr/bin/env python3
"""
测试群聊名称的脚本
帮助确认群聊名称是否正确
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from wechat_controller import WeChatController

# 测试的群聊名称列表
test_names = [
    "chatlog session",
    "Chatlog Session",
    "ChatLog Session",
    "CHATLOG SESSION",
    "chatlog  session",  # 两个空格
    "文件传输助手",  # 作为对照组
]

print("=== 群聊名称测试工具 ===")
print("\n将测试以下名称:")
for i, name in enumerate(test_names, 1):
    print(f"{i}. '{name}'")

print("\n请保持微信窗口可见...")
time.sleep(2)

controller = WeChatController()

for name in test_names:
    print(f"\n测试: '{name}'")
    result = controller.read_chat_messages(name)
    if result:
        print(f"  ✅ 成功！这个名称有效，读取到 {len(result)} 字符")
        print(f"  前 100 字符: {result[:100]}")
    else:
        print(f"  ❌ 失败，无法找到或读取该群聊")

print("\n=== 测试完成 ===")
