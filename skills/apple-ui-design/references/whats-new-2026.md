# 2026 年（iOS / macOS 27）HIG 与平台变化

来源：HIG 各页底部的 Change log（抓取于 2026-09-18，2026-09-23 复查：09-17 之后没有新的更新），加上 Xcode 27 SDK 里标注 `macOS 27` / `iOS 27` 可用的 API。
刷新方法：`python3 scripts/fetch_hig.py /tmp/hig && grep -h "2026 |" /tmp/hig/*.md`。

## 时间线

### 2025-06-09（WWDC25，26 系统）—— Liquid Glass 登场
- Materials、Color、Layout 加入 Liquid Glass 指引；App Icons 改为分层图标 + Icon Composer，支持默认 / 深色 / 透明 / 着色四种外观。
- Buttons 更新按钮样式；Toolbars 加入分组、符号用法，并入原 Navigation bars 页；Sidebars 加入「内容延伸到侧栏下面」。
- Search fields：iOS 搜索位置、tokens；Windows：iPadOS 可自由调整大小的窗口；The menu bar：iPadOS 也有菜单栏。
- 新页面：Generative AI。Accessibility 加入 Assistive Access、Switch Control、辅助功能营养标签。
- 2025-07-28：Menus 加入「菜单项图标」指引。

### 2026-03-24
- Sheets：更新按钮摆放；Scroll views：visionOS「看向滚动」。

### 2026-06-08（WWDC26，27 系统）
| 页面 | 变化 |
|---|---|
| **Design principles** | **重新引入设计原则**：Purpose、Agency、Responsibility、Familiarity、Flexibility、Simplicity、Craft、Delight（见 SKILL.md §1） |
| App icons | 细化 Liquid Glass 图标指引 |
| Menus | 更新菜单项图标指引（少而有目的、同组统一、标准操作用标准图标） |
| Scroll views | 更新滚动边缘效果指引（优先 automatic、只在控件下有滚动内容时用、每视图一个） |
| Sidebars | 更新侧栏图标颜色（跟随强调色，固定色只用于表达含义）、澄清 adaptable 侧栏样式 |
| Tab bars | 更新术语和配图 |
| Search fields / Searching | 更新术语；细化「搜索作为 iOS 标签页」 |
| Generative AI | 新增：让人细化结果、生成过程中给反馈；更新「如何选择模型类型」（本机 vs 服务器） |
| App Shortcuts | 新增：采用 app schemas |
| Siri | 针对「Siri AI」全面修订 |
| **Snippets** | **新页面**：Siri / Spotlight / 快捷指令里的确认型、结果型小卡片（高度 ≤ 400 pt、内容简洁、主按钮用具体动词） |
| Apple Pay / Wallet | 新外观、iOS 27、Pass Designer app |
| Machine learning | 文字澄清 |

### 2026-09-09（iPhone Duo 发布）
| 页面 | 变化 |
|---|---|
| **Designing for iPhone Duo** | **新页面**：双屏设备姿态、跨双屏的动态布局、竖向（侧边）工具栏和标签栏 |
| Layout | 更新为当前最佳实践 |
| Branding | 细化品牌色的使用 |
| SharePlay | 重组最佳实践、扩展 visionOS、自定义模板 |

### 2026-09-17
- In-App Purchase 更名为 Apple In-App Purchase，并更新最佳实践。

## 27 系统新增的、和界面相关的 API（Xcode 27 SDK 核对）

| API | 用途 | 可用 |
|---|---|---|
| SwiftUI `DynamicViewContent.reorderable()` + `View.reorderContainer(for:…) { ReorderDifference in … }` | 列表 / 网格原生拖动排序（`difference.sources` 被拖的 id，`destination.position` 为 `.before(id)` 或 `.end`） | iOS / macOS 27 |
| `NSGlassEffectView.effectIsInteractive` | AppKit 玻璃作为可交互控件底板时的按压反馈 | macOS 27 |
| `TabContent.help(_:)` | 标签页的 tooltip | 27 |
| `ToolbarContent.visibilityPriority(_:)` + `ToolbarItemVisibilityPriority`（`.low` / `.high` / `init(lowerThan:)` / `init(higherThan:)`） | 窗口变窄时决定哪些工具栏项先收进溢出菜单；关键项设 `.high` | 27 |
| `View.swipeActionsContainer()`、`swipeActions(…, onPresentationChanged:)` | 自定义容器里的滑动操作，并知道滑动菜单何时展开 / 收起 | 27 |
| `ReadableDocument` / `WritableDocument` / `Document` 协议 + `DocumentGroup` 支持 `@Observable` 文档类 | 新的文档模型（异步读写、`DocumentReader` / `DocumentWriter`、`FileWrapperDocumentReader/Writer`） | 27 |
| `TabsPickerStyle` | 新的标签式 Picker 样式 | 27 |
| `AnyNavigationTransition` | 类型擦除的导航转场 | 27 |
| FoundationModels `PrivateCloudComputeLanguageModel` / `LanguageModel` 协议 / `LanguageModelSession(model:instructions:)` | 苹果云端大模型（需申请受管权限）；本机模型 `SystemLanguageModel` 是 26 起 | 27 |
| Vision `GenerateIterativeSegmentationRequest`、`RecognizeAnimalsRequest` 新增识别对象 | 交互式抠图 / 识别 | 27 |
| AppKit `NotificationCenter` 的类型化消息（`NSWindow.didBecomeKey` 等 `.Message` 形式） | 替代字符串通知名 | 27 |

26 系统起就有、仍然是「新设计」核心的 API：`glassEffect`、`GlassEffectContainer`、`glassEffectID/Union/Transition`、`.buttonStyle(.glass / .glassProminent / .glass(_:))`、`scrollEdgeEffectStyle`、`safeAreaBar`、`backgroundExtensionEffect`、`ConcentricRectangle`、`ToolbarSpacer`、`sidebarAdaptable`、Translation 框架 `TranslationSession(installedSource:target:)`、Speech 框架 `SpeechAnalyzer` / `SpeechTranscriber`。

## 对现有 app 的影响（升级清单）

1. 用 Xcode 27 重新编译，先看系统组件自动带来的变化（更大的窗口 / Sheet 圆角、更高的列表行、分区标题不再全大写、控件更圆）。
2. 删掉工具栏、侧栏、弹出框、Sheet 上的自定义背景；自定义浮动栏改用 `safeAreaBar` 拿到滚动边缘效果。
3. 菜单项图标按新规则审一遍：同组统一、标准操作用标准图标、找不到贴切图标就不放。
4. 侧栏图标颜色：改成跟随强调色，只保留有语义的固定色。
5. 有 AI 功能的：标明哪里用了 AI、生成中给具体进度文案、结果旁给「重试 / 编辑 / 撤销」、允许反馈、没有 AI 时也能用。
6. 支持 iPhone 的 app：检查 iPhone Duo 的双屏、折叠区和竖向工具栏。
7. 列表能排序的地方考虑 `reorderable()`（注意和已有的拖出手势冲突）。
