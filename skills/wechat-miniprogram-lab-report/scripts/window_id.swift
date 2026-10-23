// 打印微信开发者工具主窗口的 CGWindowID（给 screencapture -l 用）
import CoreGraphics
let list = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as! [[String: Any]]
var best: (Int, Double) = (0, 0)
for w in list {
    let owner = w[kCGWindowOwnerName as String] as? String ?? ""
    guard owner.contains("wechatwebdevtools") || owner.contains("微信开发者工具") else { continue }
    guard (w[kCGWindowLayer as String] as? Int ?? 1) == 0 else { continue }
    let b = w[kCGWindowBounds as String] as? [String: Double] ?? [:]
    let area = (b["Width"] ?? 0) * (b["Height"] ?? 0)
    if area > best.1 { best = (w[kCGWindowNumber as String] as? Int ?? 0, area) }
}
print(best.0)
