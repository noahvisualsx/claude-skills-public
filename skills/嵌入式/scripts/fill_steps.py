#!/usr/bin/env python3
"""把实验步骤写进嵌入式实验报告 docx 的「4．实验方法和步骤（含设计）」一栏。

用法:
  python3 fill_steps.py 报告.docx 步骤.md [--sid 学号] [-o 输出.docx] [--force]

--sid 给了学号时，步骤文本里的 {后4位} 会替换成学号后 4 位（项目名如 0423-test2）。

步骤.md 格式（每行一个段落，空行忽略）:
  # 一、设计思路          -> 加粗小标题
  普通文字               -> 正文段落（首行缩进 2 字）
  ```                    -> 代码块开始/结束，块内每行一个等宽字体段落
默认原地覆盖报告，并在同目录留 .bak 备份；该栏已有内容时需加 --force 才会替换。
"""
import argparse, os, re, shutil, sys, tempfile, zipfile
from xml.sax.saxutils import escape

HINT = '（主要描述'


def para(text, kind):
    ppr = '<w:spacing w:line="360" w:lineRule="auto"/>'
    rpr = '<w:sz w:val="24"/><w:szCs w:val="24"/>'
    if kind == 'h':
        rpr = '<w:rFonts w:hint="eastAsia"/><w:b/><w:bCs/>' + rpr
    elif kind == 'body':
        ppr += '<w:ind w:firstLineChars="200" w:firstLine="480"/>'
        rpr = '<w:rFonts w:hint="eastAsia"/>' + rpr
    else:  # code
        ppr = '<w:spacing w:line="300" w:lineRule="auto"/><w:ind w:left="840"/>'
        rpr = ('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
               '<w:sz w:val="21"/><w:szCs w:val="21"/>')
    return ('<w:p><w:pPr>%s<w:rPr>%s</w:rPr></w:pPr><w:r><w:rPr>%s</w:rPr>'
            '<w:t xml:space="preserve">%s</w:t></w:r></w:p>') % (ppr, rpr, rpr, escape(text))


def parse(md):
    out, code = [], False
    for line in md.splitlines():
        if line.strip().startswith('```'):
            code = not code
            continue
        if code:
            out.append(para(line.rstrip(), 'code'))
        elif not line.strip():
            continue
        elif line.startswith('#'):
            out.append(para(line.lstrip('#').strip(), 'h'))
        else:
            out.append(para(line.strip(), 'body'))
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docx')
    ap.add_argument('steps')
    ap.add_argument('-o', '--out')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--sid')
    a = ap.parse_args()

    with zipfile.ZipFile(a.docx) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    x = dict((i.filename, d) for i, d in items)['word/document.xml'].decode('utf-8')

    h = x.find(HINT)
    if h < 0:
        h = x.find('实验方法和步骤')
    if h < 0:
        sys.exit('找不到「实验方法和步骤」栏')
    a_ = x.find('</w:p>', h) + len('</w:p>')
    b_ = x.find('</w:tc>', a_)
    old = x[a_:b_]
    if re.search(r'<w:t[ >][^<]*\S', old) and not a.force:
        sys.exit('该栏已有内容，确认要替换请加 --force')
    md = open(a.steps, encoding='utf-8').read()
    if a.sid:
        md = md.replace('{后4位}', a.sid[-4:])
    if '{后4位}' in md:
        sys.exit('步骤里还有 {后4位} 占位，请加 --sid 学号')
    x = x[:a_] + parse(md) + x[b_:]

    out = a.out or a.docx
    if out == a.docx:
        shutil.copy2(a.docx, a.docx + '.bak')
    fd, tmp = tempfile.mkstemp(suffix='.docx', dir=os.path.dirname(os.path.abspath(out)))
    os.close(fd)
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            if info.filename == 'word/document.xml':
                data = x.encode('utf-8')
            z.writestr(info, data)
    os.replace(tmp, out)
    print('已写入:', out)


if __name__ == '__main__':
    main()
