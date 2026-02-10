#!/usr/bin/env python3
"""
消息监控测试脚本
只测试消息读取和显示，不涉及 AI 和自动回复。
"""

import asyncio
import logging
import sys
import os

# 将 src 目录加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from config import Config
from wechat_controller import WeChatController
from message_listener import MessageListener, MentionMessage

# 启用详细日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def on_mention(mention: MentionMessage):
    """当检测到 @ 提及时的回调函数。"""
    logger.info("=" * 60)
    logger.info("🔔 检测到 @ 提及！")
    logger.info(f"  群聊: {mention.group_name}")
    logger.info(f"  发送者: {mention.sender}")
    logger.info(f"  内容: {mention.content}")
    logger.info(f"  原始行: {mention.raw_line}")
    logger.info("=" * 60)


async def main():
    """主函数：启动消息监听器。"""
    logger.info("=== 消息监控测试工具 ===")
    
    # 加载配置
    config = Config()
    logger.info(f"配置已加载:")
    logger.info(f"  - 监听群: {config.monitored_groups}")
    logger.info(f"  - Bot 名称: {config.bot_name}")
    logger.info(f"  - 轮询间隔: {config.poll_interval}s")
    
    if not config.monitored_groups:
        logger.error("❌ 配置中没有监听的群聊！")
        logger.info("\n请在 config.json 中添加要监听的群聊名称，例如:")
        logger.info('  "monitored_groups": ["chatlog session"]')
        return
    
    if not config.bot_name:
        logger.warning("⚠️  未配置 bot_name，无法检测 @ 提及")
        logger.info("\n请在 config.json 中设置你的微信昵称:")
        logger.info('  "bot_name": "你的微信昵称"')
    
    # 创建控制器
    controller = WeChatController()
    
    # 检查微信状态
    status = controller.get_status()
    logger.info(f"\n微信状态: {status}")
    
    if not status.get("wechat_available"):
        logger.error("❌ 微信窗口未找到！请确保微信已启动。")
        return
    
    # 创建消息监听器
    listener = MessageListener(
        config=config,
        controller=controller,
        on_mention=on_mention,
    )
    
    # 启动监听器
    logger.info("\n🚀 启动消息监听器...")
    await listener.start()
    
    if not listener.running:
        logger.error("❌ 消息监听器未启动（可能是配置问题）")
        return
    
    logger.info("✅ 消息监听器已启动")
    logger.info(f"\n监听中... (按 Ctrl+C 停止)")
    logger.info(f"提示: 在群聊中发送包含 @{config.bot_name} 的消息来测试")
    
    try:
        # 保持运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n\n收到停止信号，正在关闭...")
        await listener.stop()
        logger.info("✅ 已停止")


if __name__ == "__main__":
    asyncio.run(main())
