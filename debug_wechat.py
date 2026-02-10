#!/usr/bin/env python3
"""
微信窗口调试脚本
用于诊断微信窗口查找、恢复和读取消息的问题。
"""

import logging
import sys
import os

# 将 src 目录加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from config import Config
from wechat_controller import WeChatController
import psutil

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """调试微信窗口和消息读取。"""
    logger.info("=== 微信窗口调试工具 ===")
    
    # 步骤 0: 检查微信进程
    logger.info("\n--- 步骤 0: 检查微信进程 ---")
    wechat_processes = []
    for proc in psutil.process_iter(['name', 'pid']):
        name = proc.info.get('name') or ""
        if 'wechat' in name.lower():
            wechat_processes.append(proc.info)
            logger.info(f"✅ 找到微信进程: {proc.info['name']} (PID: {proc.info['pid']})")
    
    if not wechat_processes:
        logger.error("❌ 微信进程未运行！请先启动微信。")
        return
    
    logger.info(f"共找到 {len(wechat_processes)} 个微信进程")
    
    # 加载配置
    config = Config()
    logger.info(f"\n配置已加载:")
    logger.info(f"  - 监听群: {config.monitored_groups}")
    logger.info(f"  - Bot 名称: {config.bot_name}")
    
    # 创建控制器
    controller = WeChatController()
    
    # 检查微信状态
    logger.info("\n--- 步骤 1: 检查微信窗口状态 ---")
    status = controller.get_status()
    logger.info(f"微信状态: {status}")
    
    if not status.get("wechat_available"):
        logger.warning("⚠️  微信进程在运行，但未找到窗口")
        logger.info("\n可能的原因:")
        logger.info("  1. 微信只在系统托盘运行（没有打开主窗口）")
        logger.info("  2. 微信窗口被最小化到托盘")
        logger.info("\n已尝试自动恢复窗口，如果仍然失败，请:")
        logger.info("  - 手动点击系统托盘的微信图标打开主窗口")
        logger.info("  - 确保微信窗口可见且未最小化")
        return
    
    logger.info("✅ 微信窗口已找到")
    
    # 测试读取消息
    if not config.monitored_groups:
        logger.warning("\n⚠️  配置中没有监听的群聊，跳过消息读取测试")
        logger.info("\n请在 config.json 中添加要监听的群聊名称，例如:")
        logger.info('  "monitored_groups": ["你的群聊名称"]')
        logger.info("\n提示: 群聊名称必须与微信中显示的完全一致（区分大小写和空格）")
        return
    
    logger.info(f"\n--- 步骤 2: 测试读取群聊消息 ---")
    for group_name in config.monitored_groups:
        logger.info(f"\n尝试读取群聊: {group_name}")
        logger.info("提示: 请保持微信窗口可见，不要操作键盘鼠标...")
        
        import time
        time.sleep(2)  # 给用户 2 秒准备时间
        
        chat_text = controller.read_chat_messages(group_name)
        
        if chat_text:
            logger.info(f"✅ 成功读取消息，共 {len(chat_text)} 字符")
            logger.info(f"消息预览（前 200 字符）:")
            logger.info("-" * 60)
            logger.info(chat_text[:200])
            logger.info("-" * 60)
        else:
            logger.error(f"❌ 无法读取群聊 {group_name} 的消息")
            logger.info("\n可能的原因:")
            logger.info("1. 群聊名称不精确匹配（区分大小写和空格）")
            logger.info("2. 微信窗口在操作过程中被最小化或失去焦点")
            logger.info("3. 群聊不在最近聊天列表中（微信搜索找不到）")
            logger.info("\n建议:")
            logger.info("- 在微信中手动搜索并打开该群聊")
            logger.info("- 确认群聊名称与配置文件中完全一致")
            logger.info("- 将群聊置顶，确保它在聊天列表顶部")
    
    logger.info("\n=== 调试完成 ===")


if __name__ == "__main__":
    main()
