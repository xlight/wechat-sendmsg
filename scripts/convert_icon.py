#!/usr/bin/env python3
"""
将 assets/icon.ico 转换为 assets/icon.png
用于 macOS/Linux 菜单栏图标（不支持 ICO 格式）。
"""

import os, sys

from PIL import Image

assets = os.path.join(os.path.dirname(__file__), '..', 'assets')
ico_path = os.path.join(assets, 'icon.ico')
png_path = os.path.join(assets, 'icon.png')

if not os.path.isfile(ico_path):
    print(f'❌ 未找到: {ico_path}')
    sys.exit(1)

ico = Image.open(ico_path)

frames = []
try:
    while True:
        frames.append(ico.copy())
        ico.seek(ico.tell() + 1)
except EOFError:
    pass

best = max(frames, key=lambda f: f.size[0])
rgba = best.convert('RGBA')
rgba.save(png_path, 'PNG')
print(f'✅ {ico_path} → {png_path} ({best.size[0]}x{best.size[1]})')
