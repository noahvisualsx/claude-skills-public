/**
 * 课程设计说明书 排版工具函数库 —— 可以整段复制到新项目里直接用。
 *
 * 这份文件本身跟业务无关（不含任何具体项目的表名/字段名/模块名），
 * 是纯排版脚手架：中文标题字体、代码块、图表、封面表格、表格生成器。
 * 复用规则很简单：这个文件（辅助函数）原样复制过去；调用这些函数
 * 传入的具体内容（封面信息、摘要文字、每一节讲什么、贴哪几段代码、
 * 截哪几张图）必须为新项目重新写，不能把上一个项目的说明书文字改
 * 几个词就当新报告交上去——那样报告里会出现对不上号的业务描述。
 *
 * 用法：
 *   1. npm install docx  （如果 require('docx') 失败再装，环境里可能已经有）
 *   2. 把这个文件复制到工作目录，改名或保留都行
 *   3. 写一个 build.js，require 这里的函数，拼出封面/摘要/正文/参考文献
 *   4. 最后用 Document + Packer.toBuffer() 组装、写文件
 *      （组装/写文件这部分因为要拼所有 section 的顺序，建议在业务项目的
 *       build.js/assemble.js 里现写，不放进这个通用文件）
 *
 * 完整的实战示例（怎么组织 build.js / assemble.js、怎么定义 Document 的
 * styles 覆盖 Heading1/2/3 和 TOC 的字体）参考同目录下这次实际用过的写法，
 * 或者直接问 Claude "参考 php-mysql-coursework 技能之前生成报告的方式"。
 */
const {
  Document, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, BorderStyle, ImageRun,
  PageBreak, ShadingType, VerticalAlign, TableOfContents,
} = require("docx");
const fs = require("fs");
const path = require("path");

// ---------- 按需修改的排版参数 ----------
const CN_FONT = "宋体";      // 正文中文字体
const HEI_FONT = "黑体";     // 标题字体
const CODE_FONT = "Consolas"; // 代码块字体

function bodyPara(text, opts = {}) {
  return new Paragraph({
    indent: opts.noIndent ? undefined : { firstLine: 420 }, // 首行缩进2字符
    spacing: { line: 360, after: 120 },
    alignment: opts.align || AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, font: CN_FONT, size: 21, bold: opts.bold || false })],
  });
}

function centerPara(text, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: opts.after ?? 120, before: opts.before ?? 0 },
    children: [new TextRun({ text, font: opts.font || CN_FONT, size: opts.size || 21, bold: opts.bold || false })],
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 340, after: 200 },
    children: [new TextRun({ text, font: HEI_FONT, size: 32, bold: true })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 160 },
    children: [new TextRun({ text, font: HEI_FONT, size: 26, bold: true })],
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, font: HEI_FONT, size: 22, bold: true })],
  });
}

// 代码块：灰底表格模拟，等宽字体，每行一个 Paragraph（docx 不支持 \n 换行）。
// 关键坑：Table 必须显式给 columnWidths，TableCell 也必须显式给 width，
// 只设 Table 整体的 PERCENTAGE 宽度是不够的——docx-js/Word 在只有一列时会
// 把列宽退化成默认的很窄的值，代码块会渲染成每行只有一个字符宽的竖条
// （每个字符各占一行），必须两边都显式指定同一个 DXA 宽度才会撑满。
function codeBlock(lines) {
  const totalW = 9070; // 与 simpleTable 保持一致，对应 A4+标准页边距下的可用宽度
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: [totalW],
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: "D0D0D0" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "D0D0D0" },
      left: { style: BorderStyle.SINGLE, size: 4, color: "D0D0D0" },
      right: { style: BorderStyle.SINGLE, size: 4, color: "D0D0D0" },
      insideHorizontal: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
      insideVertical: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: totalW, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, fill: "F5F5F7" },
            margins: { top: 120, bottom: 120, left: 160, right: 160 },
            children: lines.map(
              (l) =>
                new Paragraph({
                  spacing: { after: 20 },
                  children: [new TextRun({ text: l.length ? l : " ", font: CODE_FONT, size: 18 })],
                })
            ),
          }),
        ],
      }),
    ],
  });
}

function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 240 },
    children: [new TextRun({ text, font: CN_FONT, size: 18, color: "555555" })],
  });
}

// 插入一张截图 + 图注。fileBase 不带扩展名，从 imgDir/fileBase.png 读取。
// 会自动读 PNG 文件头拿到原始宽高，按 displayWidthPx 等比缩放。
function figure(imgDir, fileBase, displayWidthPx, capText) {
  const filePath = path.join(imgDir, fileBase + ".png");
  const data = fs.readFileSync(filePath);
  const w = data.readUInt32BE(16);
  const h = data.readUInt32BE(20);
  const dispW = displayWidthPx || 520;
  const dispH = Math.round((dispW * h) / w);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 0 },
      children: [new ImageRun({ data, transformation: { width: dispW, height: dispH }, type: "png" })],
    }),
    caption(capText),
  ];
}

// 通用表格：第一行是表头，rows 是二维数组。widths 不传就按列数平均分。
function simpleTable(headerRow, rows, widths) {
  const totalW = 9070; // A4 双边距各约1701 twips后的可用宽度，够用大部分情况
  const colWidths = widths || headerRow.map(() => Math.floor(totalW / headerRow.length));
  function cell(text, opts = {}) {
    return new TableCell({
      width: { size: opts.w, type: WidthType.DXA },
      shading: opts.header ? { type: ShadingType.CLEAR, fill: "EEF0FA" } : undefined,
      verticalAlign: VerticalAlign.CENTER,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [
        new Paragraph({
          alignment: opts.align || AlignmentType.CENTER,
          children: [new TextRun({ text: String(text), font: CN_FONT, size: 19, bold: !!opts.header })],
        }),
      ],
    });
  }
  const trs = [
    new TableRow({ tableHeader: true, children: headerRow.map((t, i) => cell(t, { header: true, w: colWidths[i] })) }),
  ];
  for (const r of rows) {
    trs.push(new TableRow({ children: r.map((t, i) => cell(t, { w: colWidths[i] })) }));
  }
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: colWidths,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 4, color: "AAAAAA" },
      bottom: { style: BorderStyle.SINGLE, size: 4, color: "AAAAAA" },
      left: { style: BorderStyle.SINGLE, size: 4, color: "AAAAAA" },
      right: { style: BorderStyle.SINGLE, size: 4, color: "AAAAAA" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" },
      insideVertical: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" },
    },
    rows: trs,
  });
}

function spacer(n) {
  return new Paragraph({ spacing: { after: n || 100 }, children: [] });
}

// 封面用的"标签: 值"一行，两栏表格，值那一栏上下加下划线模拟填空线。
function coverRow(label, value) {
  return new TableRow({
    height: { value: 560, rule: "atLeast" },
    children: [
      new TableCell({
        width: { size: 2400, type: WidthType.DXA },
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: label, font: HEI_FONT, size: 24, bold: true })] })],
      }),
      new TableCell({
        width: { size: 5900, type: WidthType.DXA },
        borders: {
          top: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
          bottom: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
          left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
          right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
        },
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: value, font: HEI_FONT, size: 24 })] })],
      }),
    ],
  });
}

// 目录：Word/WPS 打开后要右键"更新域"才会显示正确页码，这是 docx 的固有
// 限制（真正的分页在打开文档、渲染字体之后才能算出来，生成阶段算不出来）。
function tocSection() {
  return [
    centerPara("目　录", { font: HEI_FONT, size: 30, bold: true, after: 300 }),
    new TableOfContents("目录", { hyperlink: true, headingStyleRange: "1-3" }),
    bodyPara("（提示：在 Word / WPS 中打开本文档后，右键点击上方目录区域→“更新域”→“更新整个目录”，即可自动生成正确的页码。）", { noIndent: true }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// Document 的 styles 覆盖：把 Heading1/2/3 和 TOC1/2/3 都改成中文字体黑色，
// 否则 docx 默认用 Calibri + 主题蓝色，中文文档里会很突兀。组装 Document
// 时把这个对象原样传给 `styles` 选项。
const chineseReportStyles = {
  default: {
    document: { run: { font: CN_FONT, size: 21 }, paragraph: { spacing: { line: 360 } } },
  },
  paragraphStyles: [
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { font: HEI_FONT, size: 32, bold: true, color: "000000" },
      paragraph: { spacing: { before: 340, after: 200 }, outlineLevel: 0 } },
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { font: HEI_FONT, size: 26, bold: true, color: "000000" },
      paragraph: { spacing: { before: 260, after: 160 }, outlineLevel: 1 } },
    { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { font: HEI_FONT, size: 22, bold: true, color: "000000" },
      paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    { id: "TOC1", name: "TOC Heading 1", basedOn: "Normal", next: "Normal",
      run: { font: CN_FONT, size: 22, bold: true, color: "000000" }, paragraph: { spacing: { before: 120, after: 80 } } },
    { id: "TOC2", name: "TOC Heading 2", basedOn: "Normal", next: "Normal",
      run: { font: CN_FONT, size: 21, color: "000000" }, paragraph: { spacing: { before: 60, after: 60 }, indent: { left: 220 } } },
    { id: "TOC3", name: "TOC Heading 3", basedOn: "Normal", next: "Normal",
      run: { font: CN_FONT, size: 20, color: "000000" }, paragraph: { spacing: { before: 40, after: 40 }, indent: { left: 440 } } },
  ],
};

// A4 页面设置：组装 Document 的 sections[0].properties.page 时用
const A4_PAGE = {
  size: { width: 11906, height: 16838 },
  margin: { top: 1440, bottom: 1440, left: 1701, right: 1701 },
};

module.exports = {
  h1, h2, h3, bodyPara, centerPara, codeBlock, figure, simpleTable, spacer,
  caption, coverRow, tocSection, chineseReportStyles, A4_PAGE,
  CN_FONT, HEI_FONT, CODE_FONT,
};
