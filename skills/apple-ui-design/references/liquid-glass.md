# Liquid Glass 实战手册

来源：HIG「Materials」「Color → Liquid Glass color」「Layout」「Toolbars」「Scroll views」，开发文档「Adopting Liquid Glass」「Applying Liquid Glass to custom views」。API 已在 Xcode 27 / macOS 27 SDK 核对过。

## 1. 它是什么

- 动态材质：模糊背后的内容、反射周围的颜色和光，会随触摸 / 指针实时反应。
- 本身**没有颜色**，颜色来自背后的内容；小元素（工具栏、标签栏）会根据背后内容自动在浅 / 深之间切换，上面的文字和符号自动变黑或变白。
- 大元素（侧边栏）更不透明，保证复杂背景上的可读性。
- 用户可以在系统设置里选玻璃的「偏好外观」，也可以开「降低透明度」「提高对比度」「减少动态效果」—— 这些都会改变玻璃的样子，**必须逐一测**。

## 2. 该不该用：决策树

```
这个元素是导航 / 控件 / 浮在内容上的功能层吗？
├─ 否（卡片、列表行、正文、背景）→ 不用玻璃。用标准材质（.regularMaterial 等）或纯色。
└─ 是
   ├─ 是系统组件（toolbar、sidebar、sheet、popover、menu、Button 系统样式）？
   │    → 什么都不用做，重新编译就有。删掉你给它加的自定义背景。
   └─ 是自定义控件
        ├─ 它是这个界面最重要的一两个功能元素之一吗？ 否 → 不上玻璃（避免满屏玻璃）
        └─ 是 →
             ├─ 背后是照片 / 视频等「视觉很丰富」的内容，且想让内容更显眼？ → .clear（亮内容下加 35% 黑色压暗层）
             ├─ 上面有较多文字（弹窗、侧栏、浮层面板）或背景可能影响可读性？ → .regular（默认）
             ├─ 是主操作（完成、提交）需要强调？ → .regular.tint(accent)，只给一个元素染色
             └─ 可以点 / 拖？ → 加 .interactive()
```

## 3. SwiftUI（iOS / macOS 26+）

### 3.1 单个元素

```swift
// 默认：regular 玻璃，胶囊形
Label("翻译", systemImage: "character.bubble")
    .padding(.horizontal, 14).padding(.vertical, 8)
    .glassEffect()

// 大一点的元素用圆角矩形，别硬套胶囊
panelContent
    .padding(16)
    .glassEffect(.regular, in: .rect(cornerRadius: 20))

// 主操作：染色 + 可交互（按下有果冻反馈）
Image(systemName: "checkmark")
    .frame(width: 44, height: 44)
    .glassEffect(.regular.tint(.accentColor).interactive(), in: .circle)
```

`Glass` 的全部选项：`.regular`、`.clear`、`.identity`（不画玻璃，做开关切换时用），再链式 `.tint(Color?)`、`.interactive(Bool)`。

**`glassEffect` 要放在其它影响外观的修饰符之后**（padding、frame、font 之后），它会捕获前面的内容。

### 3.2 按钮直接用系统玻璃样式（优先于手写 glassEffect）

```swift
Button("取消") { … }.buttonStyle(.glass)
Button("完成") { … }.buttonStyle(.glassProminent)   // 主操作，系统用 accent 色染底
Button { … } label: { Image(systemName: "xmark") }
    .buttonStyle(.glass(.clear))                     // 放在图片 / 视频上
```

AppKit：`NSButton.bezelStyle = .glass`。UIKit：`UIButton.Configuration.glass()` / `.prominentGlass()` / `.clearGlass()` / `.prominentClearGlass()`。

### 3.3 多个玻璃元素：一定放进容器

```swift
@Namespace private var glassSpace
@State private var expanded = false

GlassEffectContainer(spacing: 24) {          // spacing 越大，越早融合
    HStack(spacing: 24) {
        toolButton("pencil")
            .glassEffectID("pencil", in: glassSpace)
        if expanded {
            toolButton("eraser")
                .glassEffectID("eraser", in: glassSpace)   // 出现 / 消失时会从 pencil 里「长」出来
        }
    }
}
```

- 容器能合并渲染，**性能更好**；也让相邻玻璃在动画中融合、分离（「液态」的来源）。
- 容器 `spacing` > 内部 HStack 的 spacing 时，静止状态下也会粘在一起。
- 想让几个不相邻的元素合成一块玻璃：`.glassEffectUnion(id:namespace:)`。
- 出现 / 消失的过渡：`.glassEffectTransition(.matchedGeometry)`（默认，距离近时）或 `.materialize`（距离远时）；配合 `withAnimation`。
- 同屏玻璃效果数量要克制；别创建很多个容器。

### 3.4 滚动内容在控件下面

```swift
ScrollView { … }
    .scrollEdgeEffectStyle(.automatic, for: .top)   // .automatic / .soft / .hard；优先 automatic
    .scrollEdgeEffectHidden(false, for: .top)

// 自定义的底部 / 顶部栏，注册成「栏」，系统会自动给它加滚动边缘效果
content
    .safeAreaBar(edge: .bottom) { MyBottomBar() }
```

- 滚动边缘效果**不是装饰**，只在「可滚动内容在浮动控件下面」时用；每个视图只用一个；分栏布局里各栏高度保持一致。
- **不要**在控件下面垫一块半透明色来提高可读性 —— 那是旧做法。

### 3.5 背景延伸到侧边栏下面

```swift
NavigationSplitView {
    Sidebar()
} detail: {
    Image("hero").resizable().scaledToFill()
        .backgroundExtensionEffect()   // 镜像 + 模糊，让图片看起来铺到了侧栏底下
}
```

AppKit：`NSBackgroundExtensionView`；UIKit：`UIBackgroundExtensionView`。

### 3.6 同心圆角

硬件的圆角决定窗口的圆角，窗口决定控件的圆角 —— 嵌套元素的圆角要「同心」（内层半径 = 外层半径 − 间距）。

```swift
RoundedRectangle… // ✗ 各写各的半径
ConcentricRectangle()                       // ✓ 自动与容器同心
    .fill(.quaternary)
Rectangle().fill(.tint)
    .clipShape(.rect(corners: .concentric, isUniform: true))
```

容器侧需要 `.containerShape(...)` 声明形状，内部的 `ConcentricRectangle` 才知道和谁同心。

### 3.7 工具栏分组

```swift
.toolbar {
    ToolbarItemGroup { undoButton; redoButton }   // 同一块玻璃
    ToolbarSpacer(.fixed)                          // 固定间隔：分成两块玻璃
    ToolbarItem { shareButton }
    ToolbarItem(placement: .primaryAction) {
        Button("完成") { … }.buttonStyle(.glassProminent)   // 主操作放最后，只有一个
    }
}
```

- 同一块玻璃里不要混文字按钮和图标按钮；图标按钮不要再套圆圈边框（`circle` 系列符号）。
- 隐藏工具栏项要隐藏整个 item（`.hidden()`），别只隐藏里面的视图，否则会留一个空玻璃。

## 4. AppKit（macOS 26+）

```swift
let glass = NSGlassEffectView()
glass.style = .regular            // .regular / .clear
glass.cornerRadius = 16
glass.tintColor = .controlAccentColor.withAlphaComponent(0.3)   // 可选
glass.contentView = hostingView   // 只保证 contentView 在玻璃里；别往 glass 上 addSubview
if #available(macOS 27, *) {
    glass.effectIsInteractive = true   // 27 新增：作为可交互控件底板时打开
}

let container = NSGlassEffectContainerView()   // 多个玻璃合并渲染 / 靠近时融合
container.spacing = 12
container.contentView = stackOfGlassViews
```

- 系统 `NSToolbar`、`NSSplitViewController`（含 inspector）、`NSPopover`、Sheet 已自带；删掉你塞进去的 `NSVisualEffectView`。
- 滚动边缘：`NSScrollEdgeEffectStyle`（头文件 `NSScrollEdgeEffect.h`）。

## 5. UIKit

`UIGlassEffect`（放进 `UIVisualEffectView`）、`UIGlassContainerEffect`、`UIScrollEdgeElementContainerInteraction`、`UIBackgroundExtensionView`、`cornerConfiguration` / `UICornerConfiguration`、`UITabBarController.Mode.tabSidebar`。

## 6. 颜色与玻璃

- 默认让玻璃上的文字、符号保持**单色**（系统会自动黑白切换）。
- 要强调就给**背景**染色（prominent 样式），而不是给文字 / 图标染色；一个视图最多一个染色控件。
- 内容本身很花哨时，控件保持单色，或选一个跟内容区分度大的 accent。
- 内容在「静止状态」（比如滚动到顶）必须保证控件清晰，偶尔滚过去的彩色内容可以接受。

## 7. 兼容和退化

```swift
extension View {
    @ViewBuilder
    func panelGlass<S: Shape>(in shape: S, tint: Color? = nil) -> some View {
        if #available(macOS 26, iOS 26, *) {
            glassEffect(.regular.tint(tint), in: shape)
        } else {
            background(.regularMaterial, in: shape)   // 老系统退回标准材质
        }
    }
}
```

- `@Environment(\.accessibilityReduceTransparency)` 为 true 时，系统玻璃会自己变实；**自定义的半透明层也要跟着变实**。
- `@Environment(\.accessibilityReduceMotion)` 为 true 时，去掉装饰性的变形 / 弹跳动画。
- 暂缓全面换新外观：Info.plist 加 `UIDesignRequiresCompatibility`（YES）。

## 8. 透明窗口 / 浮动面板上的玻璃（刘海类、菜单栏类 app）

- 背景完全透明的 `NSPanel`（`isOpaque = false`、`backgroundColor = .clear`）上，玻璃会透出**桌面和其它窗口**，这正是想要的效果；但背后内容不可控（可能是纯白网页），所以：
  - 文字多的面板用 `.regular`，并给玻璃加一层足够深的 tint，用 `scripts/contrast.py` 按「背后是纯白」的最坏情况算：白字 ≥ 4.5:1；
  - 不要用 `.clear` 承载大段文字。
- 面板内部的卡片、列表不要再套玻璃（内容层）。
- 面板阴影可以比不透明面板更轻，玻璃自带边缘高光。
