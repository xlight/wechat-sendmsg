#!/usr/bin/env python3
"""
路径工具模块
提供在源码运行模式和 Nuitka 编译模式下均能正确定位资源文件的工具函数。
"""

import os
import sys


def is_compiled() -> bool:
    """检测当前是否在 Nuitka 编译模式下运行。

    Returns:
        True 表示以编译后的可执行文件运行，False 表示以 Python 源码运行
    """
    return "__compiled__" in dir()


def get_base_dir() -> str:
    """获取项目基准目录。

    - 源码模式: 通过 __file__ 定位到 src/ 的上级目录（项目根目录）
    - 编译模式: 通过 sys.argv[0] 定位到可执行文件所在目录

    Returns:
        项目基准目录的绝对路径
    """
    if is_compiled():
        # 编译模式：可执行文件所在目录即为基准目录
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        # 源码模式：本文件位于 src/paths.py，上级目录为项目根目录
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    """获取数据目录路径（data/）。

    Returns:
        data/ 目录的绝对路径
    """
    return os.path.join(get_base_dir(), "data")


def get_static_dir() -> str:
    """获取静态文件目录路径（static/）。

    Returns:
        static/ 目录的绝对路径
    """
    return os.path.join(get_base_dir(), "static")


def get_assets_dir() -> str:
    """获取资源文件目录路径（assets/）。

    Returns:
        assets/ 目录的绝对路径
    """
    return os.path.join(get_base_dir(), "assets")


def get_config_path() -> str:
    """获取配置文件路径（data/config.json）。

    Returns:
        配置文件的绝对路径
    """
    return os.path.join(get_data_dir(), "config.json")


def get_db_path() -> str:
    """获取消息队列数据库路径（data/messages.db）。

    Returns:
        数据库文件的绝对路径
    """
    return os.path.join(get_data_dir(), "messages.db")
