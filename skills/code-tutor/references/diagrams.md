# 画内存图：用 HTML/SVG，不要用 ASCII

ASCII 画的内存图又丑又难读，学生要先解码字符艺术才能看到内容，反而增加负担。一律用真正的图形。

## 用哪个工具

按顺序试：

1. **Visualizer**（`show_widget`）—— 首选。SVG 直接嵌在对话里，不打断讲课节奏。调用前先 `read_me(["diagram"])` 拿到当前的 CSS 变量名。
2. **Artifact 发布** —— Visualizer 不可用时（服务 400、工具没加载）用这个。写一个自包含 HTML 存到 `/mnt/user-data/outputs/`，然后 `Artifact` publish。一节课里多张图，用同一个 url 反复更新，不要每张图开一个新 artifact。
3. **都不行才退回文字** —— 这时候用表格而不是 ASCII 画框。

不要问学生"要不要画图"，直接画。

## 一张内存图必须有的东西

新手看不懂指针，根源是心智模型缺了具体性（du Boulay 的 notional machine）。所以每张图都要满足：

- **真实地址数字**，用 `0x100`、`0x104`、`0x200` 这种能心算的，不要用真实长地址，也不要写"某个地址"
- **字节格子分开画**，一个字节一个格子。`short` 画 2 格，`int` 画 4 格。字节数是很多问题的真正答案，不能糊掉
- **未初始化的内存画 `?`**，不要画 0。C 的局部变量不清零，这本身就是个要纠正的错误认知
- **指针变量自己也要有一行**，有自己的地址、自己的内容（内容是另一个地址）。只画一支箭头会强化"指针不占内存"的错误模型
- **高亮当前这一步在动的那个格子**，用不同底色。一张图里高亮不超过 2 处

## 通用样式骨架

所有图共用这套。颜色走 CSS 变量并带 fallback，这样浅色深色模式都能看。

```html
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>内存图</title>
<style>
  :root {
    --ink: #1a1915; --dim: #6b6759; --line: #c9c6ba;
    --cell: #f5f3ec; --hot: #e8d5a8; --arrow: #4a7fb5; --bad: #bf4d43;
    box-sizing: border-box;
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
  :root:not([data-theme="light"]) {
    @media (prefers-color-scheme: dark) {
      --ink: #eae7dd; --dim: #9a958a; --line: #4a473f;
      --cell: #2a2822; --hot: #5c4d2c; --arrow: #7aa8d8;
    }
  }
  body {
    margin: 0; padding: 24px;
    background: transparent; color: var(--ink);
    font: 15px/1.6 ui-sans-serif, system-ui, "PingFang SC", "Microsoft YaHei", sans-serif;
  }
  .wrap { max-width: 100%; overflow-x: auto; }
  .mono { font-family: ui-monospace, "SF Mono", Consolas, monospace; }
  .addr { color: var(--dim); font-size: 13px; }
  .byte {
    display: inline-block; width: 42px; height: 34px; line-height: 34px;
    text-align: center; border: 1.5px solid var(--line);
    background: var(--cell); margin-left: -1.5px;
    font-family: ui-monospace, monospace; font-size: 13px;
  }
  .byte.hot { background: var(--hot); }
  .byte.unset { color: var(--bad); }
  .row { display: flex; align-items: center; gap: 14px; margin: 14px 0; }
  .name { width: 92px; text-align: right; font-weight: 600; }
  .note { color: var(--dim); font-size: 13px; }
</style>
</head>
<body>
<div class="wrap">
  <!-- 内容 -->
</div>
</body>
</html>
```

## 模板一：变量的字节格子

```html
<div class="row">
  <div class="name">short c</div>
  <div>
    <div class="addr mono">0x100</div>
    <div><span class="byte">64</span><span class="byte">00</span></div>
  </div>
  <div class="note">2 个字节</div>
</div>

<div class="row">
  <div class="name">int e</div>
  <div>
    <div class="addr mono">0x200</div>
    <div><span class="byte">64</span><span class="byte">00</span><span class="byte">00</span><span class="byte">00</span></div>
  </div>
  <div class="note">4 个字节</div>
</div>
```

讲赋值方向时，把「执行前 / 执行后」两张并排，被覆盖的格子加 `hot`。

## 模板二：数组

下标写在格子上方，当前位置用箭头指出来。

```html
<div class="mono" style="display:flex;gap:0;margin-left:2px">
  <span style="width:42px;text-align:center;font-size:12px;color:var(--dim)">0</span>
  <span style="width:42px;text-align:center;font-size:12px;color:var(--dim)">1</span>
  <span style="width:42px;text-align:center;font-size:12px;color:var(--dim)">2</span>
  <span style="width:42px;text-align:center;font-size:12px;color:var(--dim)">3</span>
</div>
<div>
  <span class="byte">42</span><span class="byte">77</span>
  <span class="byte hot">13</span><span class="byte unset">?</span>
</div>
<div class="note" style="margin-top:6px">count = 3，下一个存进下标 3</div>
```

## 模板三：指针（SVG 画箭头）

箭头必须用 SVG，HTML 拼不出好看的曲线。指针变量自己的那一行不能省。

```html
<svg viewBox="0 0 520 190" style="max-width:100%;height:auto"
     font-family="ui-sans-serif, system-ui, 'PingFang SC', sans-serif">
  <defs>
    <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--arrow,#4a7fb5)"/>
    </marker>
  </defs>

  <!-- 被指的变量 -->
  <text x="20" y="46" font-size="15" font-weight="600" fill="var(--ink,#1a1915)">c</text>
  <text x="20" y="64" font-size="12" fill="var(--dim,#6b6759)" font-family="monospace">0x100</text>
  <rect x="70" y="28" width="42" height="34" fill="var(--cell,#f5f3ec)"
        stroke="var(--line,#c9c6ba)" stroke-width="1.5"/>
  <rect x="112" y="28" width="42" height="34" fill="var(--cell,#f5f3ec)"
        stroke="var(--line,#c9c6ba)" stroke-width="1.5"/>
  <text x="84" y="50" font-size="13" font-family="monospace" fill="var(--ink,#1a1915)">64</text>
  <text x="126" y="50" font-size="13" font-family="monospace" fill="var(--ink,#1a1915)">00</text>

  <!-- 指针变量：自己也有地址、也有内容 -->
  <text x="20" y="146" font-size="15" font-weight="600" fill="var(--ink,#1a1915)">p</text>
  <text x="20" y="164" font-size="12" fill="var(--dim,#6b6759)" font-family="monospace">0x108</text>
  <rect x="70" y="128" width="84" height="34" fill="var(--cell,#f5f3ec)"
        stroke="var(--line,#c9c6ba)" stroke-width="1.5"/>
  <text x="82" y="150" font-size="13" font-family="monospace" fill="var(--ink,#1a1915)">0x100</text>

  <!-- 箭头：从 p 的内容指回 c 的地址 -->
  <path d="M158 145 C220 145 220 45 200 45" fill="none"
        stroke="var(--arrow,#4a7fb5)" stroke-width="1.8" marker-end="url(#ah)"/>
  <text x="232" y="100" font-size="13" fill="var(--dim,#6b6759)">p 里装的是 c 的地址</text>
</svg>
```

讲 `*p` 时把三步拆开单独列，不要混成一句：

```html
<ol class="note" style="line-height:2">
  <li>去 p 里面取出地址 → <span class="mono">0x100</span></li>
  <li>到 0x100 这个位置</li>
  <li>从这里读出 <b>2</b> 个字节 → 100</li>
</ol>
```

第 3 步的字节数要加粗——`void*` 报错的原因就藏在这个数字里。

## 模板四：链表

结点画成两格（data + next），next 格里写**真实地址**，箭头指向对应结点的地址标签。

```html
<svg viewBox="0 0 560 130" style="max-width:100%;height:auto">
  <defs>
    <marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--arrow,#4a7fb5)"/>
    </marker>
  </defs>
  <!-- 每个结点一组：两个 rect + data 文本 + next 地址 + 下方地址标签 -->
  <!-- 结点 1 -->
  <rect x="60"  y="40" width="52" height="38" fill="var(--cell,#f5f3ec)" stroke="var(--line,#c9c6ba)" stroke-width="1.5"/>
  <rect x="112" y="40" width="68" height="38" fill="var(--cell,#f5f3ec)" stroke="var(--line,#c9c6ba)" stroke-width="1.5"/>
  <text x="80"  y="64" font-size="14" font-family="monospace">1</text>
  <text x="120" y="64" font-size="12" font-family="monospace">0x200</text>
  <text x="60"  y="96" font-size="11" fill="var(--dim,#6b6759)" font-family="monospace">0x100</text>
  <!-- 结点 2 同理，x 偏移 +200 -->
  <path d="M180 59 L240 59" stroke="var(--arrow,#4a7fb5)" stroke-width="1.8" marker-end="url(#ah2)"/>
</svg>
```

尾插法要画**三张连续的图**（空表 → 第一个结点 → 第二个结点挂上去），中间那张单独强调 `head` 和 `tail` 同时指向同一个结点。

`tail->next = p;` 和 `tail = p;` 的顺序问题，画成两条不同颜色的箭头，问学生"先画哪条"。

## 追踪表

追踪表用 HTML `<table>`，不要用 SVG。

```html
<table style="border-collapse:collapse;font-size:14px">
  <tr style="color:var(--dim)">
    <th style="padding:6px 14px;text-align:left">轮</th>
    <th style="padding:6px 14px;text-align:left">num</th>
    <th style="padding:6px 14px;text-align:left">查重</th>
    <th style="padding:6px 14px;text-align:left">arr</th>
    <th style="padding:6px 14px;text-align:left">count</th>
  </tr>
  <tr><td style="padding:6px 14px">1</td><td>42</td><td>没撞上</td>
      <td class="mono">[42, ?, ?]</td><td>1</td></tr>
  <tr><td style="padding:6px 14px">2</td><td>77</td><td>没撞上</td>
      <td class="mono">[42, 77, ?]</td><td>2</td></tr>
  <tr style="color:var(--bad)">
      <td style="padding:6px 14px">3</td><td>42</td><td>?</td><td>?</td><td>?</td></tr>
</table>
```

**最后一行留空让学生填**，而且这一行必须安排成有分支的那一轮（撞车了、条件不成立、要退出），不要是平淡的一轮。

## 检查清单

发出去之前对一遍：

- [ ] 地址是 `0x100` 这种能心算的，不是"某地址"
- [ ] 字节按个数画成独立格子，`short` 2 格 `int` 4 格
- [ ] 指针变量自己有地址行，不是只有一支箭
- [ ] 未初始化画 `?` 不画 0
- [ ] 高亮不超过 2 处
- [ ] 图里有留白给学生填，或者图后面紧跟一个可判对错的问题
- [ ] 深色模式下能看（颜色都走了 CSS 变量 + fallback）

---

# 动画与交互

## 铁律：单步 + 预测，不要自动播放

Hundhausen 等人 2002 年对 24 项可视化教学实验做的元分析：让学生在观看之外还做点什么的 12 项研究里，10 项效果显著；单纯看动画的 9 项里只有 3 项显著。结论是「学生怎么用可视化，比可视化展示了什么重要得多」。

**自动播放的动画≈没有效果。** 学生眼睛跟着动，脑子是关的，看完觉得"好像懂了"，下次还是不会。

所以每个动画都必须满足：

1. **由学生点击驱动**，不是 `autoplay`、不是无限循环 `animation-iteration-count: infinite`
2. **走下一步之前先让他猜**——按钮上写「我猜完了，走一步」，或者做一个预测输入框
3. **能退回上一步**，学生看漏了要能重看，不用整个重来
4. 每一步旁边显示**当前正在执行的那一行代码**，把代码和内存变化绑在一起

## 主模板：单步器

这是最常用的形态，讲循环、链表、排序、递归都用它。

```html
<div class="stage">
  <!-- 左边：代码，当前行高亮 -->
  <pre id="code"></pre>
  <!-- 右边：内存图，会变的部分用 transition -->
  <div id="mem"></div>
</div>

<div class="bar">
  <button id="prev">← 上一步</button>
  <span id="step">第 0 / 6 步</span>
  <button id="next">下一步 →</button>
</div>
<p id="ask" class="ask"></p>

<script>
  // 每一步是一个快照，不要写成"在上一步基础上改"
  // 快照式写法出错概率低，而且退回上一步几乎不用写逻辑
  const steps = [
    { line: 2, mem: {...}, ask: "执行完这一行，tail 指向哪里？" },
    { line: 3, mem: {...}, ask: "..." },
  ];
  let i = 0;
  function render() {
    // 高亮 steps[i].line、重绘 mem、显示 ask
    // ask 先显示，学生点下一步才揭晓答案
  }
</script>
```

关键设计：

- **快照式存储**。每一步存完整状态，不要存"变化量"。退回上一步就是 `i--` 再 render，不用写反向逻辑
- **问题在前，答案在后**。当前这一步显示的是「下一步会发生什么」的问题，点击才揭晓
- 步数控制在 **5～8 步**。超过 10 步学生会失去位置感，拆成两个单步器

## 让变化被看见：CSS transition

值变了要让眼睛能追上，否则学生不知道哪里动了。

```css
.byte {
  transition: background .35s ease, transform .35s ease;
}
.byte.changed {
  background: var(--hot);
  transform: scale(1.08);
}
/* 新出现的结点 */
.node.enter {
  animation: pop .4s ease-out;
}
@keyframes pop {
  from { opacity: 0; transform: translateY(8px) scale(.94); }
  to   { opacity: 1; transform: none; }
}
```

**一步只高亮一处变化。** 一次亮三个格子，等于没有高亮。

## 指针移动：SVG 路径动画

链表、数组遍历里指针挪位置，用 transform 平移而不是重绘。

```html
<g id="tailPtr" style="transition: transform .4s cubic-bezier(.4,0,.2,1)">
  <path d="M0 0 L0 -18" stroke="var(--arrow)" stroke-width="2" marker-end="url(#ah)"/>
  <text y="16" font-size="12" fill="var(--arrow)">tail</text>
</g>
<script>
  // 移到第 n 个结点下方
  tailPtr.setAttribute('transform', `translate(${80 + n * 200}, 100)`);
</script>
```

指针平移要看得见轨迹，时长别低于 300ms。低于 300ms 眼睛跟不上，等于瞬移。

## 箭头重连：断开 → 移动 → 接上

链表插入删除最关键的瞬间是「指针改指向」。拆成三帧，不要一步跳完。

```javascript
// 第 1 帧：旧箭头变灰 + 虚线，表示"即将断开"
oldArrow.classList.add('dying');     // opacity .3, stroke-dasharray 4 3
// 第 2 帧：新箭头从起点画出来
newArrow.style.strokeDashoffset = 0; // 配合 stroke-dasharray 做描线动画
// 第 3 帧：旧箭头消失
```

描线动画的标准写法：

```css
.arrow-draw {
  stroke-dasharray: 200;
  stroke-dashoffset: 200;
  transition: stroke-dashoffset .5s ease;
}
.arrow-draw.on { stroke-dashoffset: 0; }
```

## 不要做的动画

| 别做 | 原因 |
|---|---|
| 自动播放 / 无限循环 | 学生变成观众，元分析显示基本无效 |
| 旋转、弹跳、闪烁的装饰 | 抢注意力，属于外在认知负担 |
| 一步同时动 3 处以上 | 看不过来，等于没动画 |
| 少于 200ms 的过渡 | 眼睛跟不上，视觉上是瞬移 |
| 超过 800ms 的过渡 | 等待感明显，学生会走神 |
| 用动画表达抽象概念 | 比如"用粒子飞舞表示数据流动"。内存图要的是准确不是好看 |

## 给一节课配几个动画

不是每个知识点都要动画。判断标准：**这个概念的难点是不是"过程"？**

- 值得做动画：链表插入删除、循环的每一轮变化、排序的交换过程、递归的调用栈进出、指针移动
- 不值得做：类型占几个字节（静态图就够）、运算符优先级（表格更好）、语法错误（文字说清即可）

一节课最多两个动画。做多了就变成看演示，而不是学生在动脑。

## 动画的收尾

单步器走完之后，必须给一个**离开动画的动作**，否则学生的理解停留在"我看过了"。

收尾三选一：

```
1. 「现在不看动画，你说一下第 4 步和第 5 步顺序反过来会怎样？」
2. 「把这 6 步对应的代码，按顺序排出来」（排序题）
3. 「这段代码我挖了两个空，就是刚才动画里最关键的两步」（挖空题）
```
