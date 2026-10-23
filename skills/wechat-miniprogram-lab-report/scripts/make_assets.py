#!/usr/bin/env python3
"""生成小程序用的图片素材（没有老师素材、不能用真人照片时用）。
用法:
  python3 make_assets.py tab   输出目录 名字=emoji ...    # tabBar 图标：名字.png(灰) + 名字_on.png(彩色)，81x81
  python3 make_assets.py icon  输出目录 名字=emoji ...    # 彩色 emoji 图标 96x96（九宫格等）
  python3 make_assets.py banner 输出.jpg "文字" emoji "#4285F4" "#A0C8FF" [宽 高]   # 渐变横幅（轮播图）
  python3 make_assets.py doraemon 输出.jpg                # 多啦A梦头像 600x600（用户要求时用）
  python3 make_assets.py avatar 输出.jpg                  # 卡通女生头像占位图
例: python3 make_assets.py tab images intro=👩 youth=🌸 campus=🧡
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageOps
EMOJI = '/System/Library/Fonts/Apple Color Emoji.ttc'
HEI = '/System/Library/Fonts/Hiragino Sans GB.ttc'

def emoji(ch, size):
    f = ImageFont.truetype(EMOJI, 160)   # 苹果彩色 emoji 只支持 160 号
    im = Image.new('RGBA', (180, 180), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((90, 90), ch, font=f, embedded_color=True, anchor='mm')
    im = im.crop(im.getbbox())
    im.thumbnail((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return out

def gray(im):
    g = ImageOps.grayscale(im.convert('RGB')).point(lambda v: 150 + v * 0.3)
    return Image.merge('RGBA', (g, g, g, im.split()[3]))

def vgrad(w, h, c1, c2):
    im = Image.new('RGB', (w, h)); d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return im

hexc = lambda s: tuple(int(s.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))

def doraemon(path):
    S = 600
    im = Image.new('RGB', (S, S), (255, 240, 245)); d = ImageDraw.Draw(im)
    BLUE, RED, BLACK, WHITE = (0, 160, 233), (230, 0, 18), (30, 30, 30), (255, 255, 255)
    d.ellipse([60, 40, 540, 520], fill=BLUE, outline=BLACK, width=5)
    d.ellipse([110, 150, 490, 510], fill=WHITE, outline=BLACK, width=4)
    d.ellipse([205, 95, 300, 215], fill=WHITE, outline=BLACK, width=4)
    d.ellipse([300, 95, 395, 215], fill=WHITE, outline=BLACK, width=4)
    d.ellipse([260, 150, 288, 185], fill=BLACK); d.ellipse([312, 150, 340, 185], fill=BLACK)
    d.ellipse([268, 158, 278, 170], fill=WHITE); d.ellipse([320, 158, 330, 170], fill=WHITE)
    d.ellipse([272, 200, 328, 256], fill=RED, outline=BLACK, width=3); d.ellipse([285, 212, 300, 227], fill=WHITE)
    d.line([(300, 256), (300, 420)], fill=BLACK, width=4)
    d.chord([165, 250, 435, 440], 0, 180, fill=RED, outline=BLACK, width=4)
    d.chord([240, 360, 360, 440], 180, 360, fill=(255, 120, 120))
    d.arc([165, 250, 435, 440], 0, 180, fill=BLACK, width=4)
    for y, dy in [(265, -20), (300, 0), (335, 20)]:
        d.line([(150, y + dy), (250, y)], fill=BLACK, width=4); d.line([(350, y), (450, y + dy)], fill=BLACK, width=4)
    d.rounded_rectangle([130, 500, 470, 545], radius=20, fill=RED, outline=BLACK, width=4)
    d.ellipse([265, 515, 335, 585], fill=(255, 205, 0), outline=BLACK, width=4)
    d.line([(270, 545), (330, 545)], fill=BLACK, width=4); d.ellipse([292, 555, 308, 571], fill=BLACK)
    d.line([(300, 571), (300, 585)], fill=BLACK, width=4)
    im.save(path, quality=92)

def avatar(path):
    av = vgrad(300, 300, (255, 230, 240), (255, 200, 220)); d = ImageDraw.Draw(av)
    d.ellipse([60, 40, 240, 250], fill=(60, 40, 30)); d.ellipse([85, 80, 215, 225], fill=(255, 224, 200))
    d.pieslice([80, 55, 220, 170], 180, 360, fill=(60, 40, 30))
    d.ellipse([112, 135, 132, 155], fill=(40, 30, 30)); d.ellipse([168, 135, 188, 155], fill=(40, 30, 30))
    d.ellipse([100, 165, 125, 180], fill=(255, 170, 180)); d.ellipse([175, 165, 200, 180], fill=(255, 170, 180))
    d.arc([128, 165, 172, 200], 20, 160, fill=(220, 60, 90), width=5)
    d.rectangle([110, 225, 190, 300], fill=(255, 255, 255)); d.pieslice([40, 240, 260, 420], 180, 360, fill=(255, 90, 140))
    av.save(path, quality=90)

cmd, a = sys.argv[1], sys.argv[2:]
if cmd in ('tab', 'icon'):
    os.makedirs(a[0], exist_ok=True)
    for kv in a[1:]:
        name, ch = kv.split('=', 1)
        if cmd == 'tab':
            ic = emoji(ch, 81); ic.save(f'{a[0]}/{name}_on.png'); gray(ic).save(f'{a[0]}/{name}.png')
        else:
            emoji(ch, 96).save(f'{a[0]}/{name}.png')
elif cmd == 'banner':
    out, text, ch, c1, c2 = a[:5]
    w, h = (int(a[5]), int(a[6])) if len(a) > 6 else (750, 360)
    im = vgrad(w, h, hexc(c1), hexc(c2)).convert('RGBA')
    e = emoji(ch, int(h * 0.5)); im.paste(e, (w - e.width - 70, (h - e.height) // 2), e)
    ImageDraw.Draw(im).text((60, h // 2), text, font=ImageFont.truetype(HEI, int(h * 0.155)), fill='white', anchor='lm')
    im.convert('RGB').save(out, quality=88)
elif cmd == 'doraemon':
    doraemon(a[0])
elif cmd == 'avatar':
    avatar(a[0])
else:
    sys.exit(__doc__)
print('ok')
