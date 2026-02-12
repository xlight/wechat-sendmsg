#!/usr/bin/env python3
"""
MCP 客户端示例
演示如何使用官方 MCP SDK 与微信 MCP 服务器交互。
支持 stdio 和 streamable-http 两种传输模式。

用法:
    # stdio 模式（默认）— 自动启动服务器子进程
    python mcp_client_example.py

    # streamable-http 模式 — 连接已运行的服务器
    python mcp_client_example.py --transport streamable-http --url http://localhost:8765/mcp
"""

import argparse
import asyncio
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Implementation


async def run_demo(session: ClientSession) -> None:
    """通过已建立的 MCP 会话执行演示操作。"""
    # 初始化会话
    result = await session.initialize()
    print(f"已连接到服务器: {result.serverInfo.name} v{result.serverInfo.version}")
    print(f"协议版本: {result.protocolVersion}")
    print(f"服务器能力: {result.capabilities}")

    # 列出可用工具
    tools = await session.list_tools()
    print(f"\n可用工具 ({len(tools.tools)} 个):")
    for tool in tools.tools:
        print(f"  - {tool.name}: {tool.description}")

    # 示例 1：发送简单消息
    print("\n=== 示例 1: 发送消息 ===")
    send_result = await session.call_tool(
        "send_wechat_message",
        arguments={
            "contact_name": "文件传输助手",
            "message": "来自 MCP 客户端的测试消息！",
        },
    )
    print(f"发送结果: {send_result.content}")

    # 示例 2：安排延迟消息
    print("\n=== 示例 2: 安排延迟消息 ===")
    schedule_result = await session.call_tool(
        "schedule_wechat_message",
        arguments={
            "contact_name": "文件传输助手",
            "message": "这是一条 5 秒后发送的延迟消息！",
            "delay_seconds": 5,
        },
    )
    print(f"安排结果: {schedule_result.content}")

    # 等待延迟消息发送完成
    print("等待延迟消息发送...")
    await asyncio.sleep(6)
    print("演示完成。")


async def demo_stdio() -> None:
    """通过 stdio 传输模式连接服务器并执行演示。"""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["src/mcp_server.py"],
        cwd="..",  # 从 examples/ 目录运行时，项目根目录在上一级
    )

    print("正在以 stdio 模式启动 MCP 服务器...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(
            read_stream,
            write_stream,
            client_info=Implementation(name="wechat-mcp-client", version="2.0.0"),
        ) as session:
            await run_demo(session)


async def demo_streamable_http(url: str) -> None:
    """通过 streamable-http 传输模式连接服务器并执行演示。

    Args:
        url: MCP 端点 URL，例如 http://localhost:8765/mcp
    """
    print(f"正在连接 MCP 服务器: {url}")
    async with streamable_http_client(url) as (read_stream, write_stream, _get_session_id):
        async with ClientSession(
            read_stream,
            write_stream,
            client_info=Implementation(name="wechat-mcp-client", version="2.0.0"),
        ) as session:
            await run_demo(session)


async def main() -> None:
    """主入口函数。"""
    parser = argparse.ArgumentParser(description="微信 MCP 客户端示例")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="传输模式 (默认: stdio)",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8765/mcp",
        help="MCP 服务器 URL (仅 streamable-http 模式，默认: http://localhost:8765/mcp)",
    )

    args = parser.parse_args()

    try:
        if args.transport == "stdio":
            await demo_stdio()
        else:
            await demo_streamable_http(args.url)
    except Exception as e:
        print(f"错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
