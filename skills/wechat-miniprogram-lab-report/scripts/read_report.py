#!/usr/bin/env python3
"""读取实验报告 docx：打印所有段落/表格单元格文字，并把内嵌图片（题目效果图）导出，方便 AI 查看。
用法: python3 read_report.py 报告.docx [图片导出目录]
"""
import sys, os, zipfile, docx

path = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(path)[0] + "_media"
d = docx.Document(path)

print("==== 正文段落 ====")
for i, p in enumerate(d.paragraphs):
    if p.text.strip():
        print(f"P{i}: {p.text}")

print("\n==== 表格单元格（合并单元格只显示一次）====")
for ti, t in enumerate(d.tables):
    seen = set()
    for ri, r in enumerate(t.rows):
        for ci, c in enumerate(r.cells):
            if c._tc in seen:
                continue
            seen.add(c._tc)
            txt = "\n    ".join(p.text for p in c.paragraphs)
            has_img = len(c._tc.xpath('.//pic:pic')) > 0
            print(f"[T{ti} R{ri} C{ci}]{' (含图片)' if has_img else ''}\n    {txt}")

os.makedirs(out, exist_ok=True)
with zipfile.ZipFile(path) as z:
    imgs = [n for n in z.namelist() if n.startswith("word/media/") and not n.endswith("/")]
    for n in imgs:
        with open(os.path.join(out, os.path.basename(n)), "wb") as f:
            f.write(z.read(n))
print(f"\n导出 {len(imgs)} 张内嵌图片到: {out}  (按文档出现顺序大致为 image1, image2 ...)")
