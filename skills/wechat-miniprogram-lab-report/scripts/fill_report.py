#!/usr/bin/env python3
"""按 content.json 填写实验报告 docx（保留原模板格式，只改指定区域）。
用法: python3 fill_report.py 模板.docx content.json 输出.docx

content.json:
{
  "replace": {"时间:2026-9-15": "时间:2026-9-22", "第3周": "第4周"},   // 整段文字包含 key 就替换（表头信息）
  "sections": {
    "4": [ {"h": "2、创建项目"}, {"p": "打开微信开发者工具……"},
           {"code": "Page({ ... })", "label": "index.js"} ],
    "5": [ {"h": "2、"}, {"img": "/abs/shots/2.png", "width_cm": 6}, {"p": "说明文字"} ],
    "6": [ {"p": "本次实验……"} ]
  },
  "date": [2026, 9, 22],     // 可选：填"实验日期：  年 月 日"那一行
  "cells": [[1, 1, "张三"], [1, 6, "2400000001"]]   // 可选：直接改第一个表格(行,列)单元格文字，
                                                    // 用于表头是 XXX 这类占位（同一个词出现多次 replace 分不开）
}
"imgs": 多张图放同一行并排（手机截图 2~3 张一行，width_cm 4.5~5）。
每个 section 会清空对应单元格里"标题行 + （按题目序号…）提示行"之后的旧内容，再写入新内容。
"""
import sys, json, re, copy, docx
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

tpl, content_path, out = sys.argv[1:4]
C = json.load(open(content_path, encoding="utf-8"))
d = docx.Document(tpl)

def all_cells():
    seen = set()
    for t in d.tables:
        for r in t.rows:
            for c in r.cells:
                if c._tc not in seen:
                    seen.add(c._tc)
                    yield c

def set_text(p, text):
    runs = p.runs
    if not runs:
        runs = [p.add_run()]
    runs[0].text = text
    rpr = runs[0]._r.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = rpr.makeelement(qn("w:rFonts"), {}); rpr.insert(0, rf)
    for k in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(k), "宋体")
    for r in runs[1:]:
        r._r.getparent().remove(r._r)

# 0) 指定单元格
for r, col, text in C.get("cells", []):
    set_text(d.tables[0].cell(r, col).paragraphs[0], text)

# 1) 简单替换
for old, new in C.get("replace", {}).items():
    targets = list(d.paragraphs) + [p for c in all_cells() for p in c.paragraphs]
    for p in targets:
        if old in p.text:
            set_text(p, p.text.replace(old, new))

def style_run(r, size=10.5, font="宋体", bold=False, mono=False):
    # 用户要求：填入的所有文字（包括代码里的英文）一律宋体；mono 只影响字号
    r.font.size = Pt(size)
    r.bold = bold
    r.font.name = font
    rpr = r._r.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = rpr.makeelement(qn("w:rFonts"), {}); rpr.append(rf)
    for k in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(k), font)

def new_para_after(anchor, template_p):
    el = copy.deepcopy(template_p._p)
    for child in list(el):
        if child.tag != qn("w:pPr"):
            el.remove(child)
    anchor._p.addnext(el)
    p = Paragraph(el, anchor._parent)
    pf = p.paragraph_format
    pf.first_line_indent = None
    return p

# 2) 分区填写
for key, blocks in C.get("sections", {}).items():
    cell = next((c for c in all_cells()
                 if c.paragraphs and re.match(rf"^\s*{key}\s*[．.、]", c.paragraphs[0].text)), None)
    if cell is None:
        print(f"!! 没找到第 {key} 部分的单元格"); continue
    ps = cell.paragraphs
    keep = 1
    if len(ps) > 1 and ps[1].text.strip().startswith(("（", "(")):
        keep = 2
    body_tpl = ps[keep] if len(ps) > keep else ps[keep - 1]
    for p in ps[keep:]:
        # 第 6 部分：保留"实验日期"及之后的内容
        if key == "6" and "实验日期" in p.text:
            break
        p._p.getparent().remove(p._p)
    anchor = cell.paragraphs[keep - 1]
    for b in blocks:
        if "code" in b:
            if b.get("label"):
                anchor = new_para_after(anchor, body_tpl)
                style_run(anchor.add_run(b["label"] + "："), bold=True)
            for line in b["code"].rstrip("\n").split("\n"):
                anchor = new_para_after(anchor, body_tpl)
                anchor.paragraph_format.space_after = Pt(0)
                anchor.paragraph_format.space_before = Pt(0)
                anchor.paragraph_format.line_spacing = 1.0
                style_run(anchor.add_run(line.replace("\t", "  ")), size=9, mono=True)
        elif "img" in b:
            anchor = new_para_after(anchor, body_tpl)
            anchor.add_run().add_picture(b["img"], width=Cm(b.get("width_cm", 6)))
        elif "imgs" in b:  # 同一行并排放多张图
            anchor = new_para_after(anchor, body_tpl)
            for i, f in enumerate(b["imgs"]):
                if i:
                    anchor.add_run("  ")
                anchor.add_run().add_picture(f, width=Cm(b.get("width_cm", 4.5)))
        else:
            anchor = new_para_after(anchor, body_tpl)
            text = b.get("h") or b.get("p", "")
            style_run(anchor.add_run(text), bold="h" in b)
            if "p" in b and key == "6":
                anchor.paragraph_format.first_line_indent = Pt(21)

# 3) 实验日期
if C.get("date"):
    y, m, dd = C["date"]
    for c in all_cells():
        for p in c.paragraphs:
            if re.search(r"实验日期", p.text):
                set_text(p, f"实验日期 ：  {y}   年   {m}  月   {dd}  日")

d.save(out)
print("已保存:", out)
