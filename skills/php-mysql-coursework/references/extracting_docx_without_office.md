# 没有 Word / LibreOffice / pandoc 时怎么读 docx

`.docx` 本质是一个 zip 包，正文在 `word/document.xml` 里。环境里如果 `pandoc`、
`soffice`（LibreOffice）都不存在，不用干等或瞎猜，直接解包读 XML 就够用了。

## 提取纯文本（最常用）

```bash
rm -rf /tmp/tmpldoc && mkdir /tmp/tmpldoc && cd /tmp/tmpldoc
unzip -q "任务书.docx" -d unpacked
python3 -c "
import re
with open('unpacked/word/document.xml', encoding='utf-8') as f:
    content = f.read()
# 按段落切开，每个 <w:p>...</w:p> 是一段
paras = re.split(r'</w:p>', content)
out = []
for p in paras:
    texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)
    line = ''.join(texts)
    if line.strip():
        out.append(line)
print('\n'.join(out))
"
```

**局限**：表格单元格里的文字也能这样提出来，但表格的行列结构会丢失，输出里
会夹杂裸露的 `<w:tblPr>...` 之类 XML 片段（表格属性标签本身不含 `<w:t>` 所以
不会被提取成文字，但表格开始/结束的位置在纯文本流里看不出来）。如果任务书里
有关键信息在表格中（比如提交要求列表、学生作品分享表），读的时候留意一下
上下文，别漏看表格里的内容。

## 看一眼 docx 首页长什么样（不用装 Word）

macOS 自带 QuickLook 可以直接把 docx 渲染成缩略图，不需要装任何 Office 软件：

```bash
qlmanage -t -s 1600 -o /tmp/preview "文件.docx"
# 会在 /tmp/preview 下生成一张 "文件.docx.png"，通常是首页
```

这个方法救过一次场：任务书模板封面里印着一个真实的学校校徽图片和已经填好的
学院名/指导教师名字，只用正则提文字的话根本看不出"这是图片"这件事，也分不清
哪些字段是真的要填、哪些是模板已经填好的默认值。渲染成图片看一眼，立刻就清楚了。

## 结构性读取（要保留表格、样式信息时）

如果需要精确知道某段是不是标题、字号多大、表格有几列，装 `python-docx`
（`pip3 install python-docx`，如果网络不好导致安装失败，退回用上面的正则方案，
够用大部分场景）：

```python
from docx import Document
doc = Document("文件.docx")
for p in doc.paragraphs:
    print(p.style.name if p.style else "", "|", p.text)
for t in doc.tables:
    for row in t.rows:
        print([c.text for c in row.cells])
```

## 验证自己生成的 docx 没坏

同样不需要 Word：

1. 用 `python-docx` 读回来，打印段落数、表格数、标题大纲，跟预期核对
   （标题层级、表格数量、图片数量是否符合预期）。
2. `unzip -l 文件.docx` 看 `word/media/` 下的图片文件数量和大小是否合理。
3. `python3 -c "import xml.dom.minidom as md; md.parse('word/document.xml')"`
   确认 XML 没有损坏（能正常解析就说明不是残缺文件）。
4. `qlmanage -t -s 1600 -o 输出目录 文件.docx` 出一张缩略图肉眼确认封面/排版
   没有明显错位。

这四步加起来跑得很快，比"生成完直接扔给用户，祈祷它是对的"靠谱得多。
