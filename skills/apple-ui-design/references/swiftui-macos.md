# SwiftUI 做 Mac app：工程陷阱、品牌配色、外观验证

HIG 讲「应该长什么样」，这一页讲「在 SwiftUI / macOS 上怎么做才不出事、怎么验证」。
内容来自真实项目踩过的坑和本机 SDK（Xcode 27 / macOS 27）核对，2026-09 整理。

---

## 1. 窗口结构要稳定：别按页面增删工具栏项、开关检查器（会崩）

**现象**：侧边栏切页面时偶发崩溃，崩溃报告是 AppKit 抛的异常：

```
-[NSWindow(NSDisplayCycle) _postWindowNeedsUpdateConstraints]   ← 或 _postWindowNeedsLayout
... SwiftUI Toolbar.LocationStorage.updatedVendedItems(newFocusedValues:)
... NSView setFrameSize → _invalidateFocus → NSViewHierarchyNoteGeometryInWindowDidChange
```

意思是：一次布局里窗口被反复标记「还要再布局」，次数超过窗口里的视图数量，AppKit 判定死循环直接崩溃（Update Constraints in Window / Layout Window pass）。

**原因**：窗口级结构随页面变化。常见三种写法：

| 写法 | 为什么出事 |
|---|---|
| `NavigationSplitView { … } detail: { … }.toolbar { if section == .x { ToolbarItem … } }` | 切页时往窗口工具栏增删项；工具栏会跟着焦点值（focused values）刷新，焦点在切页时也在变，两者互相触发 |
| `.inspector(isPresented: Binding(get: { show && section == .x }, …))` | 检查器是分栏的一列，按页面开关等于每次切页都改分栏结构 |
| 多个子页面各自 `.searchable(…)` | 每个页面都往窗口工具栏插一个搜索项，切页时重复 / 增删 |
| 分栏里的内容报上去的最小尺寸随内容变化 | 分栏视图读取每栏最小尺寸，内容一变就推动分栏重新布局 |

**做法**：

- 窗口工具栏的项**固定不变**（可以 `.disabled`，不要 `if` 掉）。只属于某个页面的操作，放进页面自己的顶栏（`VStack { 顶栏 HStack; Divider(); 内容 }`）。
- 只属于某个页面的检查器，做成页面里的一栏：`HStack(spacing: 0) { 内容.frame(maxWidth: .infinity); if show { Divider(); Inspector().frame(width: 280) } }`。`.inspector` 只用于「全窗口共享、只由用户显示 / 隐藏」的检查器。
- 搜索：要么只在 `NavigationSplitView` 上挂一个 `.searchable`，内容按当前页面过滤；要么页面内用普通 `TextField` 做搜索框。
- 每一栏用常量钳住尺寸：`.frame(minWidth: 520, maxWidth: .infinity, minHeight: 360, maxHeight: .infinity)`，侧栏 `.navigationSplitViewColumnWidth(min:ideal:max:)` 也用常量。
- `scripts/audit_swiftui.py` 的 `toolbar-conditional`、`inspector-conditional`、`searchable-multi` 规则会找出这些写法。

**怎么验证**：做一个只在 DEBUG 生效的「自动切页」开关，定时器每 0.3 秒切一个页面，每切一轮打一条日志；连续跑 5–6 次、每次 40 秒以上。这类崩溃常常只在**第一轮**（页面第一次创建时）出现，只跑一次容易漏。

```swift
#if DEBUG
if ProcessInfo.processInfo.environment["APP_CYCLE"] == "1" {
    Timer.scheduledTimer(withTimeInterval: 0.3, repeats: true) { _ in
        MainActor.assumeIsolated {
            let all = Section.allCases
            let next = ((all.firstIndex(of: model.section) ?? 0) + 1) % all.count
            model.section = all[next]
            NSLog("切到 %@", String(describing: all[next]))   // 崩溃时看最后一条就知道是哪一页
        }
    }
}
#endif
```

崩溃报告在 `~/Library/Logs/DiagnosticReports/<App>-*.ips`，JSON 里 `asiBacktraces` 有异常的调用栈。

---

## 2. 品牌风格和 HIG 共存（2026-09 Branding 页更新）

HIG 允许有品牌感，但有边界：

- **品牌色少用在控件上**：只给主操作、状态标识（未读角标、选中项）；想表达品牌色，放进**内容层**（插图、卡片里的强调），让它在玻璃控件下面被透出来。
- **自定义字体用在标题**，正文和小字用系统字体（系统字体在小字号上最清楚）；自定义字体也要支持粗体文本、跟随文字大小。
- **用熟悉的组件表达品牌**：可以改颜色、字体，但尺寸、位置、行为保持平台惯例。
- 品牌让位于内容：不要为了放 logo 占地方；不要做启动画面品牌秀。

### 2.1 自定义颜色：四个变体

每个自定义色给 浅 / 深 / 浅·高对比 / 深·高对比 四个值。AppKit 动态色在 SwiftUI 里也能用，并且随窗口外观自动切换：

```swift
extension Color {
    /// 浅 / 深 / 高对比（可选）四个变体；SwiftUI 按视图所在窗口的外观取值
    static func adaptive(light: UInt32, dark: UInt32, lightHC: UInt32? = nil, darkHC: UInt32? = nil) -> Color {
        Color(nsColor: NSColor(name: nil) { appearance in
            let match = appearance.bestMatch(from: [.aqua, .darkAqua,
                                                    .accessibilityHighContrastAqua, .accessibilityHighContrastDarkAqua])
            let hex: UInt32 = switch match {
            case .darkAqua?: dark
            case .accessibilityHighContrastAqua?: lightHC ?? light
            case .accessibilityHighContrastDarkAqua?: darkHC ?? dark
            default: light
            }
            return NSColor(srgbRed: CGFloat(hex >> 16 & 0xff) / 255, green: CGFloat(hex >> 8 & 0xff) / 255,
                           blue: CGFloat(hex & 0xff) / 255, alpha: 1)
        })
    }
}
```

- `.accessibilityHighContrast*` 这几个名字**只能用于 `bestMatch(from:)` 匹配**，`NSAppearance(named:)` 传它们会返回 nil（头文件注释写明），所以不能用它们「强制」高对比外观，测试方法见 §4。
- 强调色另外放一份到 Asset Catalog 的 `AccentColor`（带 Dark / High Contrast 变体），系统控件（`.borderedProminent`、选中态、链接）会用它。
- 同一个品牌色往往要拆成两个用途：**填充用**（按钮底、角标）和**文字用**（小字链接、强调文字）。文字用的版本在浅色下更深、深色下更浅，才能过 4.5:1。用 `scripts/contrast.py` 逐对测：

```
python3 scripts/contrast.py "#C96442" "#FAF9F5"   # 陶土色小字在米白底上 3.70:1 ✗ → 文字版要更深
python3 scripts/contrast.py "#FFFFFF" "#C96442"   # 白字在陶土色按钮上 3.90:1 ✗ → 按钮底要更深，或字加粗且 ≥ 3:1
```

### 2.2 字体

| 设计 | 西文 | 中文实际回落到 |
|---|---|---|
| `.default` | SF Pro | 苹方 PingFang SC |
| `.serif` | New York | **宋体 Songti SC** |
| `.rounded` | SF Pro Rounded | 苹方 |
| `.monospaced` | SF Mono | 苹方 |

（本机用 `CTFontCreateForString` 实测。）所以 `.system(size:weight:design: .serif)` 做中文标题是「宋体 + New York」，风格统一；但宋体笔画细，**只用于 17pt 以上的标题**，正文和小字用 `.default`。

标题这类品牌字号可以写死（`.system(size: 28, design: .serif)`），正文、说明、按钮用文本样式（`.body` `.callout` `.caption`），这样才跟随系统设置。

---

## 3. 常用结构写法

- **页面顶栏**（代替按页面变化的窗口工具栏）：左边标题（可用品牌衬线），右边 2–3 个无边框图标按钮，每个都有 `.help`；下面一条 `Divider()`。
- **空状态**：`ContentUnavailableView("还没有待办", systemImage: "checklist", description: Text("在上面输入一句话就能添加。"))`，并给出下一步按钮。
- **表单**：`Form { … }.formStyle(.grouped)`，拿到系统的新行高和圆角。
- **提示条（toast）**：只用于「成功了」这类可以错过的确认；错误和需要读的结果放在界面里（行内红字、结果区），或者提示条悬停时不消失、有关闭按钮。
- **图标按钮**：`Button("复制", systemImage: "doc.on.doc") { … }.labelStyle(.iconOnly).help("复制这条回复")` —— 标题给 VoiceOver，`.help` 给鼠标悬停。
- **键盘**：主操作 `.keyboardShortcut(.defaultAction)`，取消 `.keyboardShortcut(.cancelAction)`，破坏性按钮不绑回车。
- 数字列 `.monospacedDigit()`；长列表的行高保持一致。

---

## 4. 外观和辅助功能怎么验证（不改系统设置）

改系统设置会影响用户的整台机器，自动化验证时不要动。可用的办法：

| 要验证的 | 办法 |
|---|---|
| 深色 | DEBUG 下读环境变量，在根视图 `onAppear` 里设 `NSApp.appearance = NSAppearance(named: .darkAqua)`。（启动参数 `-AppleInterfaceStyle Dark` 在 macOS 27 上**无效**，实测仍是浅色） |
| 提高对比度（SwiftUI 部分） | 根视图 `.environment(\._colorSchemeContrast, .increased)` —— 下划线开头的是给测试 / 预览用的可写版本，**不要发布到正式版** |
| 降低透明度 | `.environment(\._accessibilityReduceTransparency, true)` |
| 减少动态效果 | `.environment(\._accessibilityReduceMotion, true)` |
| 不仅靠颜色区分 | `.environment(\._accessibilityDifferentiateWithoutColor, true)` |
| 高对比下的 AppKit 动态色 | 上面的环境值不影响 `NSColor` 的 `bestMatch`；把高对比取值的逻辑写成可以用 DEBUG 开关强制走高对比分支 |
| 大 / 小窗口 | DEBUG 下 `window.setContentSize(_:)` 设到最小和很宽两种 |

**截图**：app 内自己截（不需要屏幕录制权限），DEBUG 下遍历窗口：

```swift
for window in NSApp.windows where window.isVisible {
    guard let view = window.contentView?.superview ?? window.contentView,
          let rep = view.bitmapImageRepForCachingDisplay(in: view.bounds) else { continue }
    view.cacheDisplay(in: view.bounds, to: rep)
    try? rep.representation(using: .png, properties: [:])?.write(to: outputURL)
}
```

注意 `cacheDisplay` 画不出系统的模糊材质 / 玻璃（侧边栏会显示成空白），截图里侧栏空白不代表出错；需要看玻璃效果时让人工在真机上看。

每次打磨界面后至少截：浅色、深色、深色 + 提高对比度 三张；改了布局再加最小窗口一张。

---

## 5. 启动和性能

- 主线程只做界面：读大文件、解析、建索引、排版关系图放到 `Task.detached` / 后台 actor，结果回主线程赋值。
- 用户说「卡死」时先抓现场再重启：`sample <pid> 3 -file out.txt`，看主线程是在等事件（空闲，说明是界面状态问题，比如被一个看不见的 Sheet / 浮层挡住）还是忙在某个函数里。
- 列表用 `LazyVStack` / `List`；Charts 数据点多时先聚合。
