---
name: apple-ui-design
description: 按 Apple 最新设计规范（HIG 2026 / Liquid Glass / iOS·macOS 26–27）设计、实现、审查 Apple 平台界面。用户说"做成苹果风格""按 HIG 改""升级到 Liquid Glass / 液态玻璃""这个界面像不像原生""帮我审一下 UI""设计一个 macOS / iOS 界面""SwiftUI 界面美化""图标 / 配色 / 字号 / 间距对不对"时使用；写或改任何 SwiftUI / AppKit / UIKit 视图代码、需要判断该不该上玻璃、用哪个系统组件、颜色字号怎么取时也使用。写简体中文界面文案（按钮用词、引号、省略号、中英文间距）、设计聊天助手 / 翻译 / 生成内容这类 AI 功能的界面、排查 SwiftUI Mac app 切页面崩溃时也使用。也适用于做仿 Apple 风格的网页 / 原型。
---

# Apple UI 设计技能

把 Apple 官方《Human Interface Guidelines》（2026 年 6 月 WWDC 版 + 9 月更新）和 Liquid Glass 开发文档浓缩成可执行的规则。
**先读这一页**，需要细节时再按下面的索引打开 `references/` 里的文件。

| 要做的事 | 打开 |
|---|---|
| 上 Liquid Glass：该不该用、用哪种、代码怎么写、版本判断 | `references/liquid-glass.md` |
| 颜色 / 字体字号 / 布局间距 / 深色模式 / 动效 / 材质 / 辅助功能数值 | `references/foundations.md` |
| 按钮、工具栏、侧边栏、菜单、弹出框、面板、Sheet、滚动边缘效果、标准图标 | `references/components.md` |
| macOS 专项：菜单栏、窗口、浮动面板 / HUD、刘海类应用、键盘 | `references/macos.md` |
| 2026 年（iOS / macOS 27）HIG 改了什么 | `references/whats-new-2026.md` |
| 审查一个现有界面，出问题清单 | `references/audit-checklist.md`（先跑 `scripts/audit_swiftui.py`） |
| SwiftUI 做 Mac app 的工程陷阱（切页崩溃、分栏尺寸）、品牌配色四变体、不改系统设置验证深色 / 高对比 | `references/swiftui-macos.md` |
| 简体中文界面：引号、省略号、中英文间距、Apple 的标准译法、宋体 / 苹方怎么用 | `references/chinese-ui.md` |
| 聊天助手、翻译、摘要、生成内容这类 AI 功能 | `references/generative-ai.md` |

工具：
- `python3 scripts/audit_swiftui.py <源码目录>`：静态扫 SwiftUI 代码，按 P0 / P1 / P2 列出违规写法（写死颜色和字号、缺 tooltip、条件工具栏、中文标点…）。`--list` 看全部规则；改完规则跑 `python3 scripts/test_audit_swiftui.py` 自测。
- `python3 scripts/contrast.py <前景色> <背景色> [前景透明度]`：验对比度。
- `python3 scripts/fetch_hig.py <输出目录> --changes 2026`：把官方 HIG 全部抓到本地（约 170 页）并列出今年的更新，用来查证和发现新变化。

---

## 1. 心法：Apple 2026 的八条设计原则

2026 年 HIG 重新引入了「设计原则」页。做每个取舍时拿这八个词对一下：

1. **Purpose 目的** —— 先想清楚这东西为谁解决什么，把最重要的那件事做到极致，其余让位。
2. **Agency 主导权** —— 别挡路；不锁死流程；任何操作都能撤销、能退出。
3. **Responsibility 责任** —— 隐私和安全优先；要权限时说清为什么；只收必要的数据。
4. **Familiarity 熟悉** —— 用人们已经懂的系统模式；同一个东西全 app 长一个样、同一种反馈。
5. **Flexibility 灵活** —— 适配所有输入方式（触控、指针、键盘、语音）、所有尺寸、所有辅助功能设置。
6. **Simplicity 简洁** —— 简洁 ≠ 极简；每个元素都要"挣到"它的位置；建立清晰层级。
7. **Craft 工艺** —— 细节体现用心：动画顺滑、文案精确、跟上最新平台能力，发布不是终点。
8. **Delight 愉悦** —— 先定要唤起的情绪，再设计"关键时刻"；**愉悦不是装饰**，不能妨碍任务。

## 2. 结构心法：两层模型（Liquid Glass 时代最核心的一条）

界面分两层，**永远不要混**：

- **功能层（Liquid Glass）**：导航和控件 —— 工具栏、标签栏、侧边栏、弹出框、菜单、浮动按钮、HUD。浮在内容上方，透出内容。
- **内容层（标准材质 / 纯色 / 内容本身）**：列表、卡片、正文、图片、背景。

硬规则：
- **内容层不上玻璃。** 卡片、列表行、正文容器用标准材质或纯色；唯一例外是滑块、开关这类控件在"按住拖动的那一瞬间"会自己变成玻璃。
- **玻璃上不叠玻璃。** 玻璃里的子元素用填充色 / vibrancy，不要再套一层 `glassEffect`。
- **少用。** 系统组件自带玻璃；自定义控件只给最重要的一两个功能元素加。
- **别给系统栏自己画背景。** 工具栏、侧边栏、标签栏、Sheet、弹出框的自定义背景要删掉，让系统画；内容滚到控件下面时用"滚动边缘效果"保证可读，而不是垫一块半透明色。
- **内容铺到栏下面。** 全幅背景要延伸到侧边栏 / 工具栏底下；侧边栏挡住图片时用 `backgroundExtensionEffect()`。

## 3. 动手前的决策顺序

1. **能用系统组件就用系统组件**（`NavigationSplitView`、`.toolbar`、`Form`、`Menu`、`.popover`、`.sheet`、`Button` 的系统样式）。用最新 Xcode 重新编译，它们会自动换成新外观。**不要硬编码它们的尺寸、圆角、间距**，否则会错过系统更新。
2. **系统组件不够用时**，再做自定义视图，并且：
   - 颜色用语义色（`.primary`、`.secondary`、`Color(nsColor: .labelColor)`、`.tint`），自定义色必须提供 浅色 / 深色 / 高对比 三套；
   - 字体用文本样式（`.body`、`.headline`、`.caption`），不用写死的字号，除非有充分理由；
   - 图标用 SF Symbols，名字优先查 `references/components.md` 里的标准图标表；
   - 圆角和容器同心（`ConcentricRectangle` / `.rect(corners:isUniform:)`），不要各画各的；
   - 需要玻璃时按 `references/liquid-glass.md` 的决策树选 regular / clear / tint / interactive，多个玻璃元素放进 `GlassEffectContainer`。
3. **每个自定义控件都要有**：按下状态、悬停状态（macOS）、禁用状态、键盘可达、VoiceOver 标签、tooltip（macOS 纯图标按钮）。
4. **验证**：先跑 `audit_swiftui.py`；浅色 / 深色 / 提高对比度 / 降低透明度 / 减少动态效果 各截一张（不改系统设置的办法见 `references/swiftui-macos.md` §4）；最大、最小窗口各看一遍；对比度过 `contrast.py`；改了窗口结构（工具栏、分栏、检查器）就跑一遍自动切页压力测试。

**有品牌风格时**（2026-09 Branding 页）：品牌色少用在控件上，只给主操作和状态标识，更多放进内容层；自定义 / 衬线字体只做标题，正文用系统字体；组件的尺寸、位置、行为保持平台惯例。同一个品牌色通常要拆成「填充用」和「文字用」两个版本，文字版才能过 4.5:1。

## 4. 必记数字（macOS / iOS）

| 项目 | macOS | iOS / iPadOS |
|---|---|---|
| 正文默认字号 | 13 pt | 17 pt |
| 最小字号 | **10 pt** | 11 pt |
| 控件默认尺寸 | 28×28 pt | 44×44 pt |
| 控件最小尺寸 | 20×20 pt | 28×28 pt |
| 按钮点击区建议 | ≥ 44×44 pt（所有平台的通用建议） | 同左 |
| 带边框元素周围留白 | 约 12 pt | 约 12 pt |
| 文字对比度 | ≤17pt 常规字 ≥ **4.5:1**；≥18pt 或粗体 ≥ 3:1；自定义色小字争取 7:1 | 同左 |
| 放大文字 | 支持到 200%（watchOS 140%）；macOS 没有 Dynamic Type，但要跟随系统文字大小 / 侧边栏图标大小设置 | Dynamic Type 全档位 |
| 透明玻璃 `clear` 下面是亮内容时 | 加 **35%** 黑色压暗层 | 同左 |
| 窗口 / 视图标题 | 15 个字符以内，别用 app 名当标题 | 同左 |
| 一个视图里的醒目（prominent）按钮 | 1–2 个 | 同左 |
| 工具栏分组 | 最多约 3 组 | 同左 |

macOS 文本样式（点数 / 行高）：Large Title 26/32 · Title1 22/26 · Title2 17/22 · Title3 15/20 · Headline 13/16 粗 · **Body 13/16** · Callout 12/15 · Subheadline 11/14 · Footnote 10/13 · Caption 10/13。完整字距表见 `references/foundations.md`。

## 5. 最常见的错误（看到就改）

- 在卡片 / 列表行 / 正文区上 `glassEffect` —— 内容层不上玻璃。
- 给工具栏、侧边栏、Sheet、弹出框自己垫背景色或 `NSVisualEffectView` —— 删掉，交给系统。
- 同一个视图里好几个彩色背景的按钮 —— 只留主操作一个。
- 用颜色作为唯一的信息载体（红 = 错误）—— 加图标或文字。
- 写死 `Color(red:…)` 且没有深色 / 高对比变体。
- 字号小于 macOS 10 pt / iOS 11 pt；用 Ultralight / Thin / Light 做小字。
- 自己画 Back / Close 按钮还写文字"返回""关闭" —— 用系统符号。
- 纯图标按钮没有 `accessibilityLabel` 和 tooltip（`.help()`）。
- 在 macOS 窗口 / 侧边栏**底部**放关键操作 —— 窗口常被拖到屏幕下沿之外。
- 在 app 里另做一个"浅色 / 深色"开关覆盖系统外观 —— HIG 明确不建议；要做"主题"，也应在跟随系统的前提下提供。
- 定时自动消失的提示承载了关键信息 —— 需要读的内容不能只靠定时浮层。
- 动画只是为了好看、而且出现在高频操作上 —— 高频交互别加额外动效，且动画要能被打断。
- 按钮文字说"确定 / OK"之类的空话 —— 用动词短语说清做什么（"导出""删除3项"）；打开新窗口 / 需要进一步输入的按钮文字末尾加省略号"…"。
- 按当前页面增删窗口工具栏项、开关 `.inspector`、多个页面各自 `.searchable` —— macOS 上会触发布局死循环崩溃；窗口结构保持固定，页面专属的按钮放进页面顶栏（`references/swiftui-macos.md` §1）。
- 简体中文界面用「」当引号、用 "..."、中文和英文 / 数字之间手动加空格 —— Apple 用 “”、…，并且不手动加空格，系统排版会自动留细间距（`references/chinese-ui.md`）。
- AI 功能把日记、笔记、个人资料发到云端前没问过用户；AI 直接执行删除 / 发送 / 下载而不确认（`references/generative-ai.md`）。

## 6. 版本与兼容

- Liquid Glass 的 SwiftUI API（`glassEffect`、`GlassEffectContainer`、`.buttonStyle(.glass)`、`backgroundExtensionEffect`、`safeAreaBar`、`ConcentricRectangle`、`ToolbarSpacer`）都是 **iOS / macOS 26+**；最低支持版本更低的项目用 `if #available(macOS 26, *)` 分支，老系统走原来的材质 / 纯色。
- 暂时不想换新外观：Info.plist 加 `UIDesignRequiresCompatibility = YES`（过渡用，不是长久之计）。
- 2026（27 系统）新增的相关 API 见 `references/whats-new-2026.md`（例如 SwiftUI `reorderable()` 拖动排序、`NSGlassEffectView.effectIsInteractive`）。
- 写代码前先到本机 SDK 核对 API 是否存在：
  `grep -n "func glassEffect" $(xcrun --show-sdk-path)/System/Library/Frameworks/SwiftUICore.framework/Modules/SwiftUICore.swiftmodule/arm64e-apple-macos.swiftinterface`

## 7. 做完怎么交付

- 说清楚改了哪些界面、依据的是哪条规则（引用 HIG 页面名即可，不要大段抄原文）。
- 说清楚在哪些外观 / 辅助功能设置下验证过、哪些没验证；附上 `audit_swiftui.py` 修改前后的计数。
- 最低系统版本以下会怎样退化。
