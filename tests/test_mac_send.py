#!/usr/bin/env python3
"""
macOS 微信发送测试脚本
测试微信进程查找、窗口激活和消息发送功能。

使用方式：
    python test_mac_send.py                    # 测试连接状态
    python test_mac_send.py --send 文件传输助手 "你好"   # 发送消息
"""

import argparse
import logging
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from wechat_controller import WeChatController


def test_status(controller: WeChatController):
    """测试微信连接状态。"""
    print("\n📱 检测微信状态...")
    status = controller.get_status()
    print(f"  可用: {'✅' if status.get('wechat_available') else '❌'}")
    print(f"  平台: {status.get('platform', 'unknown')}")
    print(f"  版本: {status.get('wechat_version', '未知')}")
    print(f"  PID:  {status.get('pid', status.get('window_handle', 'N/A'))}")
    print()

    if status.get('wechat_available'):
        print("✅ 微信运行中，可以发送消息")
        return True
    else:
        print("❌ 微信未运行，请先启动微信")
        return False


def test_send(controller: WeChatController, contact: str, message: str):
    """测试发送消息。"""
    print(f"\n📤 发送消息给 [{contact}]: {message}")
    result = controller.send_text_message_sync(contact, message)

    if result.get("ok"):
        print(f"✅ 发送成功！")
        print(f"   激活方式: {result.get('activation_method', 'unknown')}")
    else:
        print(f"❌ 发送失败")
        print(f"   阶段: {result.get('stage', 'unknown')}")
        print(f"   原因: {result.get('reason', 'unknown')}")
        print(f"   版本: {result.get('wechat_version', 'N/A')}")

    return result.get("ok", False)


def main():
    parser = argparse.ArgumentParser(description="macOS 微信发送测试")
    parser.add_argument("--send", nargs=2, metavar=("联系人", "消息"),
                        help="发送消息测试")
    args = parser.parse_args()

    # 初始化控制器
    controller = WeChatController()

    if args.send:
        contact, message = args.send
        if test_status(controller):
            test_send(controller, contact, message)
    else:
        test_status(controller)

    print("\n✨ 测试完成")


if __name__ == "__main__":
    main()
