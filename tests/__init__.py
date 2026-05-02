#!/usr/bin/env python3
"""
测试初始化 — 路径配置和公共 fixtures
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加 src 到 sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(SRC_DIR))


def temp_config_path():
    """生成临时配置文件路径（测试后清理）。"""
    tmpdir = tempfile.mkdtemp(prefix='wechat_sendmsg_test_')
    return os.path.join(tmpdir, 'config.json'), tmpdir


def temp_db_path():
    """生成临时消息队列数据库路径（测试后清理）。"""
    tmpdir = tempfile.mkdtemp(prefix='wechat_sendmsg_test_')
    return os.path.join(tmpdir, 'messages.db'), tmpdir
