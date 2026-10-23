#!/usr/bin/env python3
"""WCAG 对比度计算，支持半透明前景 / 叠加层，按 HIG 的门槛给结论。

用法：
    python3 contrast.py <前景> <背景> [前景透明度]
    python3 contrast.py "#FFFFFF" "#241C4A"           # 白字在深紫上
    python3 contrast.py "#FFFFFF" "#241C4A" 0.8       # 80% 白字
    python3 contrast.py "#FFFFFF" "#241C4A@0.82/#FFFFFF"
        # 背景写成「颜色@透明度/底色」表示叠加：82% 的 #241C4A 盖在纯白上
        # （例如：玻璃 tint 盖在最坏情况的白色壁纸上）
    python3 contrast.py "#FFFFFF" "#FFFFFF@0.09/#241C4A@0.82/#FFFFFF"
        # 可以多层：9% 白色卡片 → 82% 深紫玻璃 → 白色壁纸

门槛（HIG Accessibility / Dark Mode）：
    ≤17pt 常规字 ≥ 4.5:1；≥18pt 或粗体 ≥ 3:1；自定义色小字争取 7:1。
"""
import sys


def parse_hex(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"颜色要写成 #RRGGBB：{s}")
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


def blend(fg, alpha, bg):
    return tuple(f * alpha + b * (1 - alpha) for f, b in zip(fg, bg))


def parse_stack(spec):
    """'#A@0.5/#B@0.8/#C' → 从最底层往上合成出的不透明颜色"""
    layers = spec.split("/")
    color = parse_hex(layers[-1].split("@")[0])
    for layer in reversed(layers[:-1]):
        hex_part, _, a = layer.partition("@")
        color = blend(parse_hex(hex_part), float(a or 1), color)
    return color


def luminance(rgb):
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    bg = parse_stack(sys.argv[2])
    alpha = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    fg = blend(parse_hex(sys.argv[1]), alpha, bg)
    r = ratio(fg, bg)
    print(f"对比度 {r:.2f}:1")
    for need, label in ((7.0, "小字理想值 7:1"), (4.5, "正文 ≤17pt 常规字 4.5:1"), (3.0, "≥18pt 或粗体 3:1")):
        print(f"  {'✓' if r >= need else '✗'} {label}")
    sys.exit(0 if r >= 4.5 else 2)


if __name__ == "__main__":
    main()
