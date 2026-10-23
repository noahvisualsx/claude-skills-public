#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
face_privacy_tool.py — 裁头 / 遮脸 小工具

给 AI 生图当"服装/妆造参考图"用之前，先把图里的脸处理掉，
避免脸和你的"人物母图"打架、被模型偷走身份。

两种模式：
  crophead   裁头：把脸和头整个裁掉，只留脖子以下（衣服款式参考最推荐）
  maskface   遮脸：只把五官盖成灰色柔边色块，保留发型/头饰/发际线
             （头饰、发冠长在头上、裁不掉头的场合用这个）

用法：
  单张：
    python3 face_privacy_tool.py crophead 输入.jpg
    python3 face_privacy_tool.py maskface 输入.jpg

  批量处理整个文件夹：
    python3 face_privacy_tool.py crophead --batch 输入文件夹 输出文件夹
    python3 face_privacy_tool.py maskface --batch 输入文件夹 输出文件夹

  自动人脸检测失败 / 检测框不准时，手动指定人脸框（像素坐标 x,y,w,h）：
    python3 face_privacy_tool.py maskface 输入.jpg --bbox 385,378,359,359

  常用微调参数（不满意可以调）：
    maskface:
      --expand-w 1.05     遮罩宽度倍数（相对检测到的脸宽）
      --expand-h 1.35     遮罩高度倍数（相对检测到的脸高，决定盖多深到下巴）
      --down-shift 0.12   遮罩中心整体下移比例（脸型偏长可以调大）
      --blur 22           遮罩边缘柔化程度，越大越柔
      --color 120,118,116 遮罩颜色，默认中性灰
    crophead:
      --margin 0.5         在检测到的下巴下方再留多少（相对脸高）才裁切，
                            数值越大留的脖子越多

  一次性看看检测框准不准（不生成文件，只打印坐标 + 存一张标注预览图）：
    python3 face_privacy_tool.py detect 输入.jpg

依赖：pip install opencv-python-headless pillow  (二选一 opencv 版本均可)
"""

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

try:
    import cv2
    import numpy as np
except ImportError:
    print("需要 opencv-python 和 numpy：pip install opencv-python-headless numpy --break-system-packages")
    sys.exit(1)

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

_CASCADE = None


def _get_cascade():
    global _CASCADE
    if _CASCADE is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _CASCADE = cv2.CascadeClassifier(path)
    return _CASCADE


def detect_face_bbox(pil_img):
    """返回最大的人脸框 (x, y, w, h)，检测不到返回 None。

    注意：不做直方图均衡化——对高调柔光/古风妆造这类高亮画面，
    equalizeHist 反而会把检测框带偏（实测会跑去饰品/项链上）。
    做法是多个 scaleFactor 各跑一遍，把所有候选框汇总，取面积最大的一个，
    面积最大的框在人像图里几乎总是真正的脸，比"第一个非空结果"更稳。
    """
    arr = np.array(pil_img.convert("RGB"))[:, :, ::-1]  # RGB -> BGR
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    cascade = _get_cascade()

    min_side = max(40, int(min(pil_img.size) * 0.08))
    candidates = []
    for scale_factor in (1.05, 1.08, 1.1, 1.12, 1.2):
        found = cascade.detectMultiScale(
            gray, scaleFactor=scale_factor, minNeighbors=5,
            minSize=(min_side, min_side),
        )
        candidates.extend(found)

    if not candidates:
        return None

    candidates.sort(key=lambda f: f[2] * f[3], reverse=True)
    x, y, w, h = candidates[0]
    return int(x), int(y), int(w), int(h)


def parse_bbox(s):
    parts = [int(p.strip()) for p in s.split(",")]
    if len(parts) != 4:
        raise ValueError("--bbox 需要 4 个数：x,y,w,h")
    return tuple(parts)


def parse_color(s):
    parts = [int(p.strip()) for p in s.split(",")]
    if len(parts) != 3:
        raise ValueError("--color 需要 3 个数：R,G,B")
    return tuple(parts)


def get_bbox(pil_img, manual_bbox):
    if manual_bbox:
        return manual_bbox
    bbox = detect_face_bbox(pil_img)
    if bbox is None:
        raise RuntimeError(
            "没有自动检测到人脸。用 `detect` 子命令先看看图，"
            "或者直接用 --bbox x,y,w,h 手动指定人脸框。"
        )
    return bbox


def mask_face(pil_img, bbox, expand_w=1.05, expand_h=1.35, down_shift=0.12,
              blur=22, color=(120, 118, 116)):
    x, y, w, h = bbox
    cx = x + w / 2
    cy = y + h / 2 + h * down_shift
    ew = w * expand_w
    eh = h * expand_h

    box = (cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2)

    im = pil_img.convert("RGB")
    m = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(m)
    d.ellipse(box, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(blur))

    flat = Image.new("RGB", im.size, color)
    return Image.composite(flat, im, m)


def crop_head(pil_img, bbox, margin=0.5):
    x, y, w, h = bbox
    crop_y = int(y + h * (1 + margin))
    crop_y = max(0, min(crop_y, pil_img.height - 1))
    return pil_img.crop((0, crop_y, pil_img.width, pil_img.height))


def draw_debug(pil_img, bbox):
    im = pil_img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    x, y, w, h = bbox
    d.rectangle((x, y, x + w, y + h), outline=(255, 0, 0), width=4)
    return im


def process_one(mode, in_path, out_path, args):
    im = Image.open(in_path)
    bbox = get_bbox(im, args.bbox)

    if mode == "maskface":
        out = mask_face(
            im, bbox,
            expand_w=args.expand_w, expand_h=args.expand_h,
            down_shift=args.down_shift, blur=args.blur, color=args.color,
        )
    elif mode == "crophead":
        out = crop_head(im, bbox, margin=args.margin)
    elif mode == "detect":
        out = draw_debug(im, bbox)
        print(f"{in_path} -> 人脸框 x={bbox[0]} y={bbox[1]} w={bbox[2]} h={bbox[3]}")
    else:
        raise ValueError(mode)

    out.save(out_path)
    print(f"已保存: {out_path}")


def default_out_path(in_path, mode, out_dir=None):
    p = Path(in_path)
    suffix = {"maskface": "_遮脸", "crophead": "_裁头", "detect": "_检测框"}[mode]
    name = p.stem + suffix + ".png"
    if out_dir:
        return str(Path(out_dir) / name)
    return str(p.parent / name)


def main():
    parser = argparse.ArgumentParser(
        description="裁头/遮脸小工具：处理服装参考图里的脸，避免和人物母图打架。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("mode", choices=["crophead", "maskface", "detect"])
    parser.add_argument("input", help="输入图片路径，或配合 --batch 时的输入文件夹")
    parser.add_argument("batch_out", nargs="?", default=None,
                         help="仅批量模式使用：输出文件夹")
    parser.add_argument("-o", "--output", default=None, help="单张模式的输出路径")
    parser.add_argument("--batch", action="store_true", help="批量处理 input 文件夹下所有图片")
    parser.add_argument("--bbox", type=parse_bbox, default=None,
                         help="手动指定人脸框 x,y,w,h，跳过自动检测")

    # maskface 参数
    parser.add_argument("--expand-w", type=float, default=1.05)
    parser.add_argument("--expand-h", type=float, default=1.35)
    parser.add_argument("--down-shift", type=float, default=0.12)
    parser.add_argument("--blur", type=int, default=22)
    parser.add_argument("--color", type=parse_color, default=(120, 118, 116))

    # crophead 参数
    parser.add_argument("--margin", type=float, default=0.5)

    args = parser.parse_args()

    if args.batch:
        if not args.batch_out:
            print("批量模式需要指定输出文件夹：--batch 输入文件夹 输出文件夹")
            sys.exit(1)
        in_dir, out_dir = args.input, args.batch_out
        os.makedirs(out_dir, exist_ok=True)
        files = [f for f in sorted(os.listdir(in_dir))
                 if Path(f).suffix.lower() in IMG_EXTS]
        if not files:
            print(f"{in_dir} 下没有找到图片")
            sys.exit(1)
        ok, fail = 0, 0
        for f in files:
            in_path = str(Path(in_dir) / f)
            out_path = default_out_path(in_path, args.mode, out_dir)
            try:
                process_one(args.mode, in_path, out_path, args)
                ok += 1
            except Exception as e:
                print(f"跳过 {f}：{e}")
                fail += 1
        print(f"完成：成功 {ok} 张，失败/跳过 {fail} 张。")
    else:
        out_path = args.output or default_out_path(args.input, args.mode)
        try:
            process_one(args.mode, args.input, out_path, args)
        except Exception as e:
            print(f"出错：{e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
