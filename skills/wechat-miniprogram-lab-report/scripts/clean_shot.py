#!/usr/bin/env python3
"""模拟器截图四个圆角外有时会带上别的页面的残影，把圆角外涂白。
用法: python3 clean_shot.py a.png b.png ...   （shoot.js 截完会自动调用）"""
import sys
from PIL import Image, ImageDraw
for f in sys.argv[1:]:
    im = Image.open(f).convert('RGB')
    w, h = im.size
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([4, 3, w - 5, h - 1], radius=int(w * 0.09), fill=255)
    Image.composite(im, Image.new('RGB', (w, h), (255, 255, 255)), mask).save(f)
