#!/usr/bin/env python3
"""
Nuitka 编译脚本
将微信 MCP 服务器编译为独立的 Windows 可执行文件（单文件模式）。

使用方法：
    python build.py            # 默认 onefile 模式编译
    python build.py --standalone  # standalone 目录模式（调试用）

前提条件：
    - pip install nuitka
    - C 编译器：MSVC（Visual Studio Build Tools）或 MinGW64（Nuitka 首次运行可自动下载）
"""

import os
import shutil
import subprocess
import sys


def check_nuitka() -> bool:
    """检测 Nuitka 是否已安装。"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            print(f"[OK] Nuitka 已安装: {version}")
            return True
    except Exception:
        pass

    print("[ERROR] Nuitka 未安装！")
    print("  请运行: pip install nuitka")
    return False


def check_compiler() -> bool:
    """检测 C 编译器是否可用。"""
    # 检测 MSVC (cl.exe)
    try:
        result = subprocess.run(
            ["cl"], capture_output=True, text=True,
        )
        print("[OK] 检测到 MSVC 编译器")
        return True
    except FileNotFoundError:
        pass

    # 检测 GCC (MinGW64)
    try:
        result = subprocess.run(
            ["gcc", "--version"], capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("[OK] 检测到 GCC 编译器")
            return True
    except FileNotFoundError:
        pass

    print("[WARN] 未检测到 C 编译器（MSVC 或 MinGW64）")
    print("  Nuitka 首次运行时会尝试自动下载 MinGW64 gcc。")
    print("  如果下载失败，请手动安装：")
    print("  - MSVC: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    print("  - MinGW64: https://www.mingw-w64.org/")
    return True  # 不阻塞编译，Nuitka 可自动下载


def build(standalone_only: bool = False) -> None:
    """执行 Nuitka 编译。

    Args:
        standalone_only: 仅编译为 standalone 目录模式（不打包为单文件）
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(project_root, "src", "mcp_server.py")
    output_dir = os.path.join(project_root, "dist")
    icon_path = os.path.join(project_root, "assets", "icon.ico")
    static_dir = os.path.join(project_root, "static")
    data_dir = os.path.join(project_root, "data")
    assets_dir = os.path.join(project_root, "assets")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 构建 Nuitka 命令
    cmd = [
        sys.executable, "-m", "nuitka",
        # 编译模式
        "--mode=onefile" if not standalone_only else "--mode=standalone",
        # 输出目录
        f"--output-dir={output_dir}",
        # 输出文件名
        "--output-filename=chatwe-automate.exe",
        # Windows 隐藏控制台窗口
        "--windows-console-mode=disable",
        # 跟随所有导入
        "--follow-imports",
    ]

    # 可执行文件图标
    if os.path.isfile(icon_path):
        cmd.append(f"--windows-icon-from-ico={icon_path}")
        print(f"[OK] 使用图标: {icon_path}")
    else:
        print("[WARN] 图标文件不存在，将使用默认图标")

    # 打包静态文件
    if os.path.isdir(static_dir):
        cmd.append(f"--include-data-dir={static_dir}=static")
        print(f"[OK] 打包静态文件: {static_dir}")

    # 打包配置模板文件（仅模板，不包含运行时配置）
    config_templates = [
        "config.conservative.json",
        "config.moderate.json",
        "config.aggressive.json",
    ]
    for tmpl in config_templates:
        tmpl_path = os.path.join(data_dir, tmpl)
        if os.path.isfile(tmpl_path):
            cmd.append(f"--include-data-files={tmpl_path}=data/{tmpl}")

    # 打包 assets 目录（图标等资源）
    if os.path.isdir(assets_dir):
        cmd.append(f"--include-data-dir={assets_dir}=assets")
        print(f"[OK] 打包资源文件: {assets_dir}")

    # 排除测试文件
    cmd.append("--nofollow-import-to=test_*")
    cmd.append("--nofollow-import-to=tests")

    # 启用 anti-bloat 插件（减小体积）
    cmd.append("--enable-plugin=anti-bloat")

    # 产品信息
    cmd.append("--company-name=ChatWE")
    cmd.append("--product-name=ChatWE Automate")
    cmd.append("--product-version=1.0.0")
    cmd.append("--file-description=微信 MCP 服务器 - 系统托盘应用")

    # onefile 模式的临时目录配置
    if not standalone_only:
        cmd.append(
            '--onefile-tempdir-spec={CACHE_DIR}/ChatWE/ChatWE-Automate/{VERSION}'
        )

    # 主脚本
    cmd.append(main_script)

    print()
    print("=" * 60)
    mode = "standalone (目录模式)" if standalone_only else "onefile (单文件模式)"
    print(f"  开始编译 — 模式: {mode}")
    print("=" * 60)
    print()
    print("命令:")
    print(f"  {' '.join(cmd)}")
    print()

    # 执行编译
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("=" * 60)
        print("  编译成功！")
        print(f"  输出目录: {output_dir}")
        # 列出输出文件
        for f in os.listdir(output_dir):
            fpath = os.path.join(output_dir, f)
            if os.path.isfile(fpath):
                size_mb = os.path.getsize(fpath) / (1024 * 1024)
                print(f"  - {f} ({size_mb:.1f} MB)")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print(f"  编译失败！退出码: {result.returncode}")
        print("=" * 60)
        sys.exit(result.returncode)


def main() -> None:
    """编译脚本入口点。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="将微信 MCP 服务器编译为独立可执行文件"
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="仅编译为 standalone 目录模式（用于调试，不打包为单文件）",
    )
    args = parser.parse_args()

    print("微信 MCP 服务器 — Nuitka 编译脚本")
    print()

    # 环境检查
    if not check_nuitka():
        sys.exit(1)

    check_compiler()
    print()

    # 执行编译
    build(standalone_only=args.standalone)


if __name__ == "__main__":
    main()
