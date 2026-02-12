#!/usr/bin/env python3
"""
HTTP API 服务器
基于 Python 标准库实现 RESTful 接口，提供消息发送和状态查询端点。
"""

import asyncio
import json
import logging
import mimetypes
import os
import queue
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs

from config import Config
from wechat_controller import WeChatController

# 导入 MCPServer 类用于 MCP over HTTP
try:
    import sys
    import os
    # 确保可以导入根目录的 mcp_server
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mcp_server import MCPServer
except ImportError as e:
    logging.warning(f"无法导入 MCPServer: {e}，MCP 端点将不可用")
    MCPServer = None

logger = logging.getLogger(__name__)


class WeChatHTTPRequestHandler(BaseHTTPRequestHandler):
    """处理 HTTP 请求的请求处理器。"""
    
    # 类级别的共享属性（在启动时设置）
    controller: WeChatController = None
    config: Config = None
    rate_limiter = None
    work_time_controller = None
    mcp_server = None  # MCP 服务器实例（持久化）
    
    def log_message(self, format: str, *args) -> None:
        """重写日志方法，使用 logging 模块。"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200) -> None:
        """发送 JSON 响应。"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")  # CORS 支持
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    
    def _read_json_body(self) -> Dict[str, Any]:
        """读取 JSON 请求体。"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    
    def _get_mime_type(self, filepath: str) -> str:
        """基于 mimetypes 模块检测 MIME 类型。"""
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type:
            # 为文本类型添加 charset
            if mime_type.startswith("text/") or mime_type == "application/javascript":
                return f"{mime_type}; charset=utf-8"
            return mime_type
        return "application/octet-stream"
    
    def _serve_file(self, filepath: str, mime_type: str = None) -> None:
        """读取文件并发送响应。
        
        Args:
            filepath: 相对于项目根目录的文件路径
            mime_type: MIME 类型（可选，自动检测）
        """
        # 构建绝对路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, filepath)
        
        # 检查文件是否存在
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return
        
        # 自动检测 MIME 类型
        if not mime_type:
            mime_type = self._get_mime_type(full_path)
        
        # 读取文件并发送
        try:
            with open(full_path, "rb") as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        
        except Exception as e:
            logger.error(f"读取文件 {filepath} 时出错: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"500 Internal Server Error")
    
    def _send_sse_event(self, event_type: str, data: str) -> None:
        """格式化并发送 SSE 事件。
        
        Args:
            event_type: 事件类型（如 mcp-response, mcp-error, keepalive）
            data: 事件数据（JSON 字符串或其他）
        """
        message = f"event: {event_type}\ndata: {data}\n\n"
        self.wfile.write(message.encode('utf-8'))
        self.wfile.flush()
    
    def _handle_mcp_sse(self) -> None:
        """处理 MCP Server-Sent Events 端点。"""
        if not MCPServer:
            self.send_response(503)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"MCP Server not available")
            return
        
        # 设置 SSE 响应头
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # 使用共享的 MCP 服务器实例
        mcp_server = self.mcp_server
        if not mcp_server:
            logger.error("MCP Server instance not found")
            return
        
        last_keepalive = time.time()
        
        logger.info("SSE 连接已建立")
        
        try:
            while True:
                # 1. 检查是否有新的 MCP 请求
                try:
                    request = self.server.mcp_request_queue.get(timeout=1)
                    logger.debug(f"SSE 处理 MCP 请求: {request.get('method')}")
                    
                    # 调用 MCP 处理
                    response = asyncio.run(mcp_server.handle_request(request))
                    
                    # 发送响应
                    if 'error' in response:
                        self._send_sse_event('mcp-error', json.dumps(response, ensure_ascii=False))
                    else:
                        self._send_sse_event('mcp-response', json.dumps(response, ensure_ascii=False))
                
                except queue.Empty:
                    pass  # 无请求，继续循环
                
                # 2. 发送心跳（每 30 秒）
                if time.time() - last_keepalive > 30:
                    self._send_sse_event('keepalive', 'ping')
                    last_keepalive = time.time()
        
        except BrokenPipeError:
            logger.info("SSE 客户端断开连接")
        except Exception as e:
            logger.error(f"SSE 连接异常: {e}")
        finally:
            logger.info("SSE 连接已关闭，资源已清理")
    
    def _handle_mcp_sse_post(self) -> None:
        """处理 POST /mcp/sse 请求（接收客户端 MCP 请求并放入队列）。"""
        body = self._read_json_body()
        
        if not body:
            self._send_json_response({"ok": False, "error": "Invalid JSON"}, 400)
            return
        
        # 将请求放入队列
        self.server.mcp_request_queue.put(body)
        logger.debug(f"MCP 请求已加入队列: {body.get('method')}")
        
        # 立即返回 202 Accepted
        self._send_json_response({"ok": True, "status": "accepted"}, 202)
    
    def _handle_mcp_stream(self) -> None:
        """处理 MCP Stream 端点（NDJSON 双向流式通信）。"""
        logger.info("处理 MCP Stream 请求")
        
        # 设置流式响应头
        self.send_response(200)
        self.send_header('Content-Type', 'application/x-ndjson; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # 使用共享的 MCP 服务器实例
        mcp_server = self.mcp_server
        if not mcp_server:
            logger.error("MCP Server instance not found")
            return
        
        try:
            # 读取请求体（Content-Length）
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                lines = body.strip().split('\n')
            else:
                lines = []
                logger.warning("MCP stream 请求无 Content-Length")
            
            # 收集所有响应
            responses = []
            
            # 处理每个 NDJSON 请求
            for line in lines:
                if not line.strip():
                    continue
                
                try:
                    # 逐行解析 JSON-RPC 请求
                    request = json.loads(line)
                    logger.debug(f"Stream 处理 MCP 请求: {request.get('method')}")
                    
                    # 调用 MCP 处理
                    response = asyncio.run(mcp_server.handle_request(request))
                    
                    # 添加到响应列表
                    responses.append(json.dumps(response, ensure_ascii=False))
                
                except json.JSONDecodeError as e:
                    # JSON 解析错误处理
                    logger.error(f"JSON 解析错误: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": f"Parse error: {e}"},
                        "id": None
                    }
                    responses.append(json.dumps(error_response, ensure_ascii=False))
                
                except Exception as e:
                    # MCP 处理错误
                    logger.error(f"MCP 处理错误: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": f"Internal error: {e}"},
                        "id": None
                    }
                    responses.append(json.dumps(error_response, ensure_ascii=False))
            
            # 发送所有响应（NDJSON 格式）
            if responses:
                response_text = '\n'.join(responses) + '\n'
                self.wfile.write(response_text.encode('utf-8'))
                self.wfile.flush()
        
        except BrokenPipeError:
            logger.info("Stream 客户端断开连接")
        except Exception as e:
            logger.error(f"Stream 连接异常: {e}")
        finally:
            logger.info("Stream 连接已关闭")
    
    def _handle_static_file(self) -> None:
        """处理 /static/* 路径的静态文件请求。"""
        # 移除 /static/ 前缀
        requested_path = self.path[8:]  # 去掉 "/static/"
        
        # 规范化路径，移除 .. 等危险字符
        normalized_path = os.path.normpath(requested_path)
        
        # 安全检查：确保路径不包含 .. 且不是绝对路径
        if ".." in normalized_path or os.path.isabs(normalized_path):
            logger.warning(f"拒绝不安全的路径访问: {self.path}")
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"403 Forbidden")
            return
        
        # 构建静态文件路径
        static_file_path = os.path.join("static", normalized_path)
        
        # 提供文件
        self._serve_file(static_file_path)
    
    def do_POST(self) -> None:
        """处理 POST 请求。"""
        try:
            parsed_path = urlparse(self.path)
            logger.debug(f"POST 请求路径: {parsed_path.path}")
            
            if parsed_path.path == "/api/v1/messages/send":
                self._handle_send_message()
            elif parsed_path.path == "/mcp/sse":
                # 接收客户端 MCP 请求，放入队列
                self._handle_mcp_sse_post()
            elif parsed_path.path == "/mcp/stream":
                self._handle_mcp_stream()
            else:
                self._send_json_response({"ok": False, "error": "Not found"}, 404)
        
        except Exception as e:
            logger.error(f"处理 POST 请求时出错: {e}", exc_info=True)
            # 返回详细错误信息以便调试
            import traceback
            error_detail = traceback.format_exc()
            self._send_json_response({
                "ok": False, 
                "error": "Internal server error",
                "detail": str(e),
                "traceback": error_detail
            }, 500)
    
    def do_GET(self) -> None:
        """处理 GET 请求。"""
        try:
            parsed_path = urlparse(self.path)
            
            # 优先级 1: API 端点
            if parsed_path.path == "/api/v1/status":
                self._handle_status()
            elif parsed_path.path == "/api/v1/anti-ban/stats":
                self._handle_anti_ban_stats()
            elif parsed_path.path == "/api/v1/anti-ban/config":
                self._handle_anti_ban_config()
            
            # 优先级 2: MCP 端点
            elif parsed_path.path == "/mcp/sse":
                self._handle_mcp_sse()
            
            # 优先级 3: 静态文件路由
            elif parsed_path.path == "/":
                self._serve_file("static/index.html", "text/html; charset=utf-8")
            elif parsed_path.path == "/test":
                self._serve_file("static/test.html", "text/html; charset=utf-8")
            elif parsed_path.path.startswith("/static/"):
                self._handle_static_file()
            
            else:
                self._send_json_response({"ok": False, "error": "Not found"}, 404)
        
        except Exception as e:
            logger.error(f"处理 GET 请求时出错: {e}")
            self._send_json_response({"ok": False, "error": "Internal server error"}, 500)
    
    def do_OPTIONS(self) -> None:
        """处理 OPTIONS 请求（CORS 预检）。"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def _handle_send_message(self) -> None:
        """处理发送消息请求。"""
        try:
            body = self._read_json_body()
            
            contact_name = body.get("contact_name")
            message = body.get("message")
            
            if not contact_name:
                self._send_json_response(
                    {"ok": False, "error": "Missing required parameter: contact_name"}, 400
                )
                return
            
            if not message:
                self._send_json_response(
                    {"ok": False, "error": "Missing required parameter: message"}, 400
                )
                return
            
            # 发送消息（异步调用）
            import asyncio
            result = asyncio.run(self.controller.send_text_message(contact_name, message))
            
            if result.get("ok"):
                self._send_json_response({"ok": True, "message": "Message sent successfully"})
            else:
                self._send_json_response(
                    {"ok": False, "error": "Failed to send message", "details": result}, 500
                )
        except Exception as e:
            # 安全地处理异常消息，避免编码问题
            try:
                error_msg = str(e)
            except:
                error_msg = f"{type(e).__name__}: (encoding error)"
            
            logger.error(f"发送消息时出错", exc_info=True)
            self._send_json_response(
                {"ok": False, "error": f"Internal error: {error_msg}"}, 500
            )
    
    def _handle_status(self) -> None:
        """处理状态查询请求。"""
        wechat_status = self.controller.get_status()
        self._send_json_response({
            "ok": True,
            "wechat_status": wechat_status
        })
    
    def _handle_anti_ban_stats(self) -> None:
        """处理防封号统计查询请求。"""
        from datetime import datetime
        
        if not self.rate_limiter or not self.work_time_controller:
            self._send_json_response({
                "ok": False,
                "error": "Anti-ban tools not initialized"
            }, 503)
            return
        
        rate_stats = self.rate_limiter.get_stats()
        is_work_time = self.work_time_controller.is_work_time()
        runtime = self.work_time_controller.get_runtime()
        max_runtime = self.config.max_daily_runtime_hours * 3600
        
        self._send_json_response({
            "ok": True,
            "rate_limiter": rate_stats,
            "work_time": {
                "is_work_time": is_work_time,
                "current_hour": datetime.now().hour,
                "work_hours": f"{self.config.work_hours_start}-{self.config.work_hours_end}",
                "current_day": datetime.now().weekday(),
                "work_days": self.config.work_days
            },
            "runtime": {
                "current_runtime_seconds": runtime,
                "current_runtime_hours": runtime / 3600,
                "max_daily_hours": self.config.max_daily_runtime_hours,
                "remaining_hours": max((max_runtime - runtime) / 3600, 0)
            }
        })
    
    def _handle_anti_ban_config(self) -> None:
        """处理防封号配置查询请求。"""
        self._send_json_response({
            "ok": True,
            "rate_limits": {
                "per_minute": self.config.rate_limit_per_minute,
                "per_hour": self.config.rate_limit_per_hour,
                "per_day": self.config.rate_limit_per_day
            },
            "human_behavior": {
                "min_think_time": self.config.min_think_time,
                "max_think_time": self.config.max_think_time,
                "min_random_delay": self.config.min_random_delay,
                "max_random_delay": self.config.max_random_delay
            },
            "work_time": {
                "hours": f"{self.config.work_hours_start}-{self.config.work_hours_end}",
                "days": self.config.work_days,
                "max_daily_runtime_hours": self.config.max_daily_runtime_hours
            },
            "content_diversification": {
                "prefix_probability": self.config.prefix_probability,
                "suffix_probability": self.config.suffix_probability,
                "skip_probability": self.config.random_skip_probability
            },
            "gui_operations": {
                "offset_range": self.config.gui_offset_range,
                "move_duration": f"{self.config.gui_move_duration_min}-{self.config.gui_move_duration_max}s",
                "pause": f"{self.config.gui_pause_min}-{self.config.gui_pause_max}s"
            }
        })


def start_http_server(
    config: Config,
    controller: WeChatController,
    rate_limiter=None,
    work_time_controller=None
) -> ThreadingHTTPServer:
    """启动 HTTP 服务器。
    
    Args:
        config: 配置对象
        controller: 微信控制器实例
        rate_limiter: 速率限制器实例（可选）
        work_time_controller: 工作时间控制器实例（可选）
    
    Returns:
        ThreadingHTTPServer 实例
    """
    # 设置类级别的共享属性
    WeChatHTTPRequestHandler.controller = controller
    WeChatHTTPRequestHandler.config = config
    WeChatHTTPRequestHandler.rate_limiter = rate_limiter
    WeChatHTTPRequestHandler.work_time_controller = work_time_controller
    
    # 初始化 MCP 服务器实例（持久化）
    if MCPServer:
        WeChatHTTPRequestHandler.mcp_server = MCPServer()
        logger.info("MCP 服务器实例已创建")
    
    # 创建服务器（使用 ThreadingHTTPServer 支持并发连接）
    server_address = ("0.0.0.0", config.http_port)
    httpd = ThreadingHTTPServer(server_address, WeChatHTTPRequestHandler)
    
    # 添加 wechat_controller 属性（共享实例）
    httpd.wechat_controller = controller
    
    # 添加 mcp_request_queue 属性（SSE 请求队列）
    httpd.mcp_request_queue = queue.Queue()
    
    logger.info(f"HTTP 服务器已启动: http://0.0.0.0:{config.http_port}")
    logger.info("可用端点:")
    logger.info("  POST /api/v1/messages/send - 发送消息")
    logger.info("  GET  /api/v1/status - 查询状态")
    logger.info("  GET  /api/v1/anti-ban/stats - 防封号统计")
    logger.info("  GET  /api/v1/anti-ban/config - 防封号配置")
    if MCPServer:
        logger.info("  GET  /mcp/sse - MCP Server-Sent Events")
        logger.info("  POST /mcp/stream - MCP 流式双向通信")
    logger.info("  GET  / - 欢迎页面")
    logger.info("  GET  /test - 测试工具")
    
    return httpd


if __name__ == "__main__":
    # 示例：独立运行 HTTP 服务器
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    config = Config()
    controller = WeChatController()
    
    # 可选：初始化防封号模块
    try:
        from anti_ban.enhanced_rate_limiter import EnhancedRateLimiter
        from anti_ban.work_time_controller import WorkTimeController
        
        rate_limiter = EnhancedRateLimiter(
            limit_per_minute=config.rate_limit_per_minute,
            limit_per_hour=config.rate_limit_per_hour,
            limit_per_day=config.rate_limit_per_day
        )
        work_time_controller = WorkTimeController(
            work_hours_start=config.work_hours_start,
            work_hours_end=config.work_hours_end,
            work_days=config.work_days,
            max_daily_runtime_hours=config.max_daily_runtime_hours
        )
        
        httpd = start_http_server(config, controller, rate_limiter, work_time_controller)
    except ImportError:
        logger.warning("防封号模块未加载，相关端点将不可用")
        httpd = start_http_server(config, controller)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务器...")
        httpd.shutdown()
        logger.info("HTTP 服务器已关闭")
