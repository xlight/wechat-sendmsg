#!/usr/bin/env python3
"""
HTTP API 服务器
基于 Python 标准库实现 RESTful 接口，提供消息发送和状态查询端点。
"""

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs

from config import Config
from wechat_controller import WeChatController

logger = logging.getLogger(__name__)


class WeChatHTTPRequestHandler(BaseHTTPRequestHandler):
    """处理 HTTP 请求的请求处理器。"""
    
    # 类级别的共享属性（在启动时设置）
    controller: WeChatController = None
    config: Config = None
    rate_limiter = None
    work_time_controller = None
    
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
    
    def do_POST(self) -> None:
        """处理 POST 请求。"""
        try:
            parsed_path = urlparse(self.path)
            
            if parsed_path.path == "/api/v1/messages/send":
                self._handle_send_message()
            else:
                self._send_json_response({"ok": False, "error": "Not found"}, 404)
        
        except Exception as e:
            logger.error(f"处理 POST 请求时出错: {e}")
            self._send_json_response({"ok": False, "error": "Internal server error"}, 500)
    
    def do_GET(self) -> None:
        """处理 GET 请求。"""
        try:
            parsed_path = urlparse(self.path)
            
            if parsed_path.path == "/api/v1/status":
                self._handle_status()
            elif parsed_path.path == "/api/v1/anti-ban/stats":
                self._handle_anti_ban_stats()
            elif parsed_path.path == "/api/v1/anti-ban/config":
                self._handle_anti_ban_config()
            else:
                self._send_json_response({"ok": False, "error": "Not found"}, 404)
        
        except Exception as e:
            logger.error(f"处理 GET 请求时出错: {e}")
            self._send_json_response({"ok": False, "error": "Internal server error"}, 500)
    
    def _handle_send_message(self) -> None:
        """处理发送消息请求。"""
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
        
        # 发送消息
        result = self.controller.send_text_message(contact_name, message)
        
        if result.get("ok"):
            self._send_json_response({"ok": True, "message": "Message sent successfully"})
        else:
            self._send_json_response(
                {"ok": False, "error": "Failed to send message", "details": result}, 500
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
) -> HTTPServer:
    """启动 HTTP 服务器。
    
    Args:
        config: 配置对象
        controller: 微信控制器实例
        rate_limiter: 速率限制器实例（可选）
        work_time_controller: 工作时间控制器实例（可选）
    
    Returns:
        HTTPServer 实例
    """
    # 设置类级别的共享属性
    WeChatHTTPRequestHandler.controller = controller
    WeChatHTTPRequestHandler.config = config
    WeChatHTTPRequestHandler.rate_limiter = rate_limiter
    WeChatHTTPRequestHandler.work_time_controller = work_time_controller
    
    # 创建服务器
    server_address = ("0.0.0.0", config.http_port)
    httpd = HTTPServer(server_address, WeChatHTTPRequestHandler)
    
    logger.info(f"HTTP 服务器已启动: http://0.0.0.0:{config.http_port}")
    logger.info("可用端点:")
    logger.info("  POST /api/v1/messages/send - 发送消息")
    logger.info("  GET  /api/v1/status - 查询状态")
    logger.info("  GET  /api/v1/anti-ban/stats - 防封号统计")
    logger.info("  GET  /api/v1/anti-ban/config - 防封号配置")
    
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
