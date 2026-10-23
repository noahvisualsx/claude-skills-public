# 基础：颜色、字体、布局、深色模式、动效、材质、辅助功能

来源：HIG「Color」「Typography」「Layout」「Dark Mode」「Motion」「Materials」「Accessibility」「Writing」「Feedback」「Loading」。以下是提炼后的规则和官方数值，不是原文。

---

## 颜色

**原则**
- 一种颜色只表达一种含义。用品牌色表示「可点」，就别再拿它给不可点的文字上色。
- 每个颜色都要有 **浅色 / 深色 / 浅色高对比 / 深色高对比** 四个变体。即使 app 只支持一种外观，也要给全，玻璃的自适应会用到。
- 不要把颜色当成唯一的信息载体（色盲用户）：状态再配图标 / 文字 / 形状。红绿、蓝橙是最容易混淆的组合。
- 颜色有文化含义（红色在一些地方是警告，在另一些地方是喜庆），国际化时注意。
- 让用户选颜色时用系统的 `ColorPicker`。

**系统色**
- **不要把系统色写成十六进制常量** —— 每个系统版本都会微调。用 API：SwiftUI `.red/.orange/.yellow/.green/.mint/.teal/.cyan/.blue/.indigo/.purple/.pink/.brown/.gray`。
- 用**语义色**表达用途，而不是外观：
  - SwiftUI：`.primary` `.secondary` `.tertiary` `.quaternary`（前景层级）、`.tint`、`Color(.windowBackgroundColor)` 等。
  - macOS AppKit 常用：`labelColor` / `secondaryLabelColor` / `tertiaryLabelColor` / `quaternaryLabelColor`（文字四级）、`controlAccentColor`（用户选的强调色）、`controlBackgroundColor`（表格、浏览器这类大块控件的底）、`windowBackgroundColor`、`separatorColor`、`selectedContentBackgroundColor` / `unemphasizedSelectedContentBackgroundColor`（选中行，key 窗口 / 非 key 窗口）、`linkColor`、`placeholderTextColor`、`findHighlightColor`、`keyboardFocusIndicatorColor`。
  - iOS：`systemBackground` / `secondarySystemBackground` / `tertiarySystemBackground`（普通），`systemGroupedBackground` 三级（分组表格），`label` 四级、`separator` / `opaqueSeparator`、`link`、`placeholderText`；灰阶 `systemGray`…`systemGray6`。
- **别挪用语义**：不要把 separator 色当文字色，不要把 secondaryLabel 当背景。
- macOS **App 强调色**：用户在「系统设置 → 外观 → 强调色」选「多色」时才用你的 accent；选了具体颜色就会覆盖你的。侧边栏图标默认跟随强调色；只有少数需要表达固定含义的图标（比如 Mail 的 VIP 黄星）才固定颜色。

**Liquid Glass 上的颜色** → 见 `liquid-glass.md` §6。

**色彩管理**
- 图片嵌入颜色描述文件；默认 sRGB。
- 广色域（Display P3，16 bit/通道，PNG）用于照片、视频、需要更鲜明的数据可视化；在资源目录里为 sRGB 和 P3 分别提供版本，防止渐变在 sRGB 屏上断层。
- 在强光、暗光、True Tone 开 / 关下都看一眼。

---

## 字体

**字号底线**

| 平台 | 默认 | 最小 |
|---|---|---|
| iOS / iPadOS | 17 pt | 11 pt |
| macOS | 13 pt | 10 pt |
| tvOS | 29 pt | 23 pt |
| visionOS | 17 pt | 12 pt |
| watchOS | 16 pt | 12 pt |

**原则**
- 避免 Ultralight / Thin / Light 做正文和小字；用 Regular / Medium / Semibold / Bold。
- 层级靠 **字重 + 字号 + 颜色** 组合表达；字体家族尽量少（通常一个 SF 就够，要衬线用 New York）。
- **优先用文本样式**（`.largeTitle` `.title` `.title2` `.title3` `.headline` `.body` `.callout` `.subheadline` `.footnote` `.caption` `.caption2`），而不是写死字号：自动支持 Dynamic Type / 粗体文本等辅助设置。
- 需要再加一级层级时用 symbolic traits（`.bold()`、`.leading(.tight/.loose)`），不要另起字号。三行以上的文字不要用 tight 行距。
- 系统字体**不要打包进 app**，用 `Font.Design`（`.default` SF、`.serif` NY、`.rounded`、`.monospaced` SF Mono）。
- 系统字体是可变字体、自带「动态光学尺寸」，运行时会自动按字号调字距；只有做**设计稿**时才需要手动查字距表。
- 数字对齐用 `.monospacedDigit()`。
- SF Symbols 和 SF 字重一一对应，图文混排时符号会自动对齐字重和基线。

**macOS 内置文本样式**（macOS 没有 Dynamic Type）

| 样式 | 字重 | 字号 | 行高 | 强调字重 |
|---|---|---|---|---|
| Large Title | Regular | 26 | 32 | Bold |
| Title 1 | Regular | 22 | 26 | Bold |
| Title 2 | Regular | 17 | 22 | Bold |
| Title 3 | Regular | 15 | 20 | Semibold |
| Headline | Bold | 13 | 16 | Heavy |
| Body | Regular | 13 | 16 | Semibold |
| Callout | Regular | 12 | 15 | Semibold |
| Subheadline | Regular | 11 | 14 | Semibold |
| Footnote | Regular | 10 | 13 | Semibold |
| Caption 1 | Regular | 10 | 13 | Medium |
| Caption 2 | Medium | 10 | 13 | Semibold |

macOS 和系统控件保持一致的字体：`NSFont.systemFont / boldSystemFont / controlContentFont / labelFont / menuFont / menuBarFont / messageFont / paletteFont / titleBarFont / toolTipsFont / userFont / userFixedPitchFont(ofSize:)`。

**macOS 设计稿字距**（1/1000 em → pt，节选）：10pt +12 · 11pt +6 · 12pt 0 · 13pt −6 (−0.08) · 14pt −11 · 15pt −16 · 16pt −20 · 17pt −26 (−0.43) · 20pt −23 · 22pt −12 · 24pt +3 · 26pt +8 · 28pt +14。完整表：`fetch_hig.py` 抓下来后看 `typography.md`。

**iOS Dynamic Type**：布局要适配所有档位；大字号时横排改竖排、行高变高、表格单行变多行；重要图标跟着放大（SF Symbols 自动）；尽量不截断；保持信息层级（主要元素始终在上面）。不是所有文字都要等比放大（标签页标题可以不变）。

---

## 布局

- **按重要性排序**：阅读顺序是从上到下、从前到后（leading → trailing），最重要的放上方前侧。支持从右到左语言：用 leading/trailing 而不是 left/right。
- **对齐**让内容可扫读；**缩进**表达从属；**分组**用留白、容器形状或分隔线。
- **渐进式披露**：折叠三角、菜单、下一级视图，初始只放必要的。
- **控件和内容要分开**：控件放在 Liquid Glass 功能层；不要在控件下垫实色 / 半透明色，用滚动边缘效果；全屏背景延伸到侧栏、工具栏、标签栏下面。
- **适配**：按可用空间（iOS 的 size class）而不是设备型号或方向来决定布局；空间变化时**功能不变，只变可见多少**（比如宽了把标签栏换成侧边栏、把溢出菜单里的东西摆出来）。
- 尊重安全区、布局边距、可读宽度指南（`readableContentGuide`）。
- 先用最大和最小的布局测，再测中间。
- 背景图换比例时不要拉伸，按比例放大铺满；超宽 / 超高窗口要准备好更大的画面。
- **macOS**：关键控件和信息**别放在窗口底部**（窗口常被拖到屏幕下沿外）；别把内容放到顶部摄像头 / 刘海区域后面（`NSPrefersDisplaySafeAreaCompatibilityMode`）。
- **iPhone Duo（2026 年 9 月新设备）**：双屏 + 多种姿态；外屏更宽更矮，工具栏 / 标签栏会竖着放到侧边（顶部是返回 / 关闭，其后是主操作，溢出从下往上）；折叠区要避开；折叠时只做小幅调整不要大重排；用 split / overlay 两种 arrangement view；导航容器放在 arrangement 外面。

---

## 深色模式

- **不要在 app 里另做外观开关**覆盖系统设置 —— 用户会以为你的 app 坏了。只有沉浸式媒体类可以常驻深色。
- 两种外观都要好看，并且要能在 app 运行中途切换（系统「自动」外观会在一天中切换）。
- 深色不是简单反色：背景更暗、前景更亮，有些颜色不反转。
- 自定义颜色放 Asset Catalog 的 Color Set，填亮 / 暗两个变体。
- 对比度：最低 **4.5:1**，自定义前景 / 背景争取 **7:1**（尤其小字）。
- 深色下的白底图片稍微压暗，避免"发光"。
- iOS 深色有 **base / elevated** 两套背景：弹出框、Sheet 用 elevated（更亮）表示「在上面」；用系统背景色才能自动获得。
- macOS 选「石墨」强调色时窗口会**跟随桌面图片着色**（desktop tinting）：自定义组件在**中性状态**下带一点透明，就能跟着染；有颜色的状态不要透明（否则颜色会随桌面漂移）。
- 同时开「提高对比度 + 降低透明度」再检查一遍深色，暗字暗底最容易出问题。

---

## 动效

- **有目的才动**；高频操作不要加额外动画（系统控件已经有细微动画了）。
- **动效要可选**：不能只靠动画传达关键信息，配合触感 / 声音；尊重「减少动态效果」。
- 反馈动效要**符合物理直觉、跟随手势**：从上面拉下来的东西，就往上推回去，而不是往侧面划走。
- **短而准**：简短精确的反馈比夸张的动画更有效。
- **可以打断**：别让人等动画播完才能操作。
- 可以用 SF Symbols 的动画（`symbolEffect`：`.bounce`、`.pulse`、`.variableColor`、`.replace` 等）代替自己画。
- Liquid Glass 的形变在触摸时更夸张、用触控板时更克制，这是系统自己处理的。
- 游戏：稳定 30–60 fps；允许用户在画质和续航之间取舍。

---

## 材质（非玻璃）

- 标准材质用于**内容层**的层次区分：iOS 有 ultraThin / thin / regular（默认）/ thick；macOS 有按用途命名的 `NSVisualEffectView.Material`（`.sidebar`、`.menu`、`.popover`、`.hudWindow`、`.headerView`、`.contentBackground`、`.underWindowBackground` 等）。
- **按语义 / 用途选材质**，不是按它看起来什么颜色（系统设置会改变它的外观）。
- 材质上的文字和填充用 **vibrancy**（iOS：label / secondaryLabel / tertiaryLabel / quaternaryLabel、fill 三级、separator 一级；thin 和 ultraThin 上别用 quaternary，对比度太低）。
- 厚材质对比度更好（适合细节多的文字）；薄材质更能透出背景、帮人保持上下文。
- macOS 混合模式：`behindWindow`（透出桌面 / 其它窗口）和 `withinWindow`（只混合本窗口内容）。

---

## 辅助功能（数值 + 必做项）

| 项 | 要求 |
|---|---|
| 文字放大 | 至少支持到 200%（watchOS 140%） |
| 对比度 | ≤17pt 所有字重 4.5:1；18pt 以上 3:1；粗体 3:1 |
| 控件尺寸 | iOS 默认 44×44 / 最小 28×28；**macOS 默认 28×28 / 最小 20×20**；visionOS 60×60 / 28×28；tvOS 66×66 / 56×56；watchOS 44×44 / 28×28 |
| 控件间距 | 有边框的元素周围约 12 pt |

必做：
- 所有图标按钮有 `accessibilityLabel`；自定义控件有正确的 trait / role；VoiceOver 走一遍。
- **全键盘操作**（macOS 开「键盘导航」/ iOS「全键盘控制」）：Tab 能走到所有控件，焦点环可见。
- 手势都要有按钮替代；常用操作用最简单的手势。
- 支持 Voice Control、Switch Control；关键任务接入 Siri / 快捷指令（App Intents）。
- 声音提示配触感 + 视觉提示；音视频提供字幕 / 文字。
- **少用会自动消失的限时界面**（有人需要更长时间阅读）—— 自动消失的浮层至少要能悬停保持、或能在别处找回内容。
- 不自动播放音视频，或提供明显的停止控制；支持「减弱闪烁光」。
- 尊重：降低透明度、提高对比度、减少动态效果、粗体文本、按钮形状、差异化不仅靠颜色（`accessibilityDifferentiateWithoutColor`）。

SwiftUI 读取这些设置：`@Environment(\.accessibilityReduceTransparency)`、`\.accessibilityReduceMotion`、`\.colorSchemeContrast`、`\.accessibilityDifferentiateWithoutColor`、`\.legibilityWeight`。

---

## 文案（Writing）

- 先定 app 的「声音」（面向谁、什么语气），再按场景调整语调：出错时要冷静、成功时可以轻松。
- 清楚 > 巧妙；每个词都要有用；为所有人写（避免术语、俚语、性别预设）。
- **动作导向**：按钮用动词开头，说清结果（「导出12张截图」「删除3项」），不用「确定」「提交」这种空话。
- 同一个概念全 app 用同一个词（语言模式一致）；大小写规则定下来就统一（2026 起列表 / 表单的分区标题系统用标题式大小写，不再全大写）。
- 少用「我的」「你的」。
- **空状态要给下一步**（「还没有收藏 —— 点星标收藏常用内容」+ 按钮）。
- **错误信息**：说发生了什么、为什么、怎么办；不要责怪用户；能提供修复按钮就提供。
- 设置项标签简洁、描述它控制什么；输入框用占位符提示格式。
- 选对通知方式：不是每件事都值得打断人。

## 反馈（Feedback）与加载（Loading）

- 状态反馈尽量**就近融入界面**（按钮旁的小勾、行内进度），而不是弹窗。
- 弹窗（Alert）只用于关键、最好可操作的信息；**可能意外丢失数据且不可撤销**的操作要先警告。
- 重要任务完成时给确认；命令无法执行时说明原因。
- 加载：尽快显示点东西（骨架、占位、已缓存的旧内容）；加载时允许做别的事；说明在加载什么、大概多久（确定进度用进度条，不确定用转圈）；大资源后台下载。
- 生成式 AI 的等待文案要具体（「正在翻译成3种语言」而不是「处理中…」）。
