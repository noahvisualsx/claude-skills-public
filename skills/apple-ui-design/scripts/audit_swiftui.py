#!/usr/bin/env python3
"""静态扫一遍 SwiftUI / AppKit 代码，找出违反 HIG 或容易出事的写法，给人工审查当起点。

用法：
    python3 audit_swiftui.py <目录或文件> [...]            # 文本报告，按严重度分组
    python3 audit_swiftui.py <目录> --json                  # 机器可读
    python3 audit_swiftui.py <目录> --min P1                # 只看 P0 / P1
    python3 audit_swiftui.py <目录> --rules zh-quote,font-size   # 只跑部分规则
    python3 audit_swiftui.py --list                         # 列出全部规则

某一行确实是有意为之：在行尾加注释 `// audit:ignore`（全部规则）或 `// audit:ignore zh-space`（指定规则）。
`#if DEBUG … #endif` 里的代码默认跳过。

这是启发式扫描：会有漏报和误报。每条结果都要回到代码里确认，再按 references/audit-checklist.md 下结论。
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
CJK = "\u4e00-\u9fff\u3400-\u4dbf"

RULES = {
    "toolbar-conditional": ("P0", "窗口工具栏的内容随页面 / 状态条件增删",
                            "切页时往窗口工具栏增删项，工具栏会跟着焦点反复刷新，AppKit 布局次数超限直接崩溃"
                            "（Update Constraints in Window）。工具栏项保持固定，页面专属按钮放进页面自己的顶栏。"),
    "inspector-conditional": ("P0", ".inspector 的显示条件绑定到页面 / 分区",
                              "按页面开关检查器分栏同样会触发布局死循环。检查器只跟随用户的显示 / 隐藏操作；"
                              "只属于某个页面的侧栏做成页面里的一栏（HStack + Divider）。"),
    "searchable-multi": ("P0", "多个视图各自用 .searchable",
                         "每个子页面都会往窗口工具栏插一个搜索框，切页时出现重复搜索项并可能崩溃。"
                         "搜索框挂在一处（通常是 NavigationSplitView 本身），或者页面内用普通 TextField。"),
    "destructive-default": ("P0", "破坏性按钮绑定了回车（默认操作）",
                            "HIG › Buttons：破坏性操作永远不给 primary 角色，人会不看就按回车。"),
    "font-too-small": ("P0", "字号低于平台下限",
                       "HIG › Typography：macOS 最小 10 pt，iOS 最小 11 pt。"),
    "font-fixed": ("P2", "写死字号而不是文本样式",
                   "HIG › Typography：优先 .body / .headline / .caption 等文本样式，跟随系统文字大小和粗体文本设置。"
                   "品牌标题可以例外，但正文和小字用系统样式。"),
    "font-thin": ("P1", "小字用了 Ultralight / Thin / Light",
                  "HIG › Typography：细字重在小字号上难读，用 Regular 及以上。"),
    "color-hardcoded": ("P1", "写死的 RGB / 十六进制颜色，没有深色 / 高对比变体",
                        "HIG › Color / Dark Mode：每个自定义色要有浅色、深色、高对比变体。"
                        "用 Asset Catalog 或 NSColor(name:dynamicProvider:)，见 references/swiftui-macos.md。"),
    "appearance-override": ("P1", "在 app 内覆盖系统外观",
                            "HIG › Dark Mode：不要另做浅色 / 深色开关覆盖系统设置。"),
    "icon-button-help": ("P2", "纯图标按钮缺少 .help 提示",
                         "HIG › Buttons / Offering help：macOS 纯图标按钮要有 tooltip；"
                         "同时确认有文字标题（Label 的标题会成为 VoiceOver 标签）。"),
    "prominent-many": ("P2", "同一个视图文件里醒目按钮较多，复查同一屏是否超过 2 个",
                       "HIG › Buttons：一个视图里 prominent 按钮 1–2 个，只给最可能的操作。"
                       "按文件计数：不同状态（空状态 / 正常状态）各有一个是允许的，要回到界面确认同屏数量。"),
    "ok-button": ("P2", "按钮文字是「确定 / OK / 提交」这类空话",
                  "HIG › Writing / Alerts：按钮用动词短语说清结果（「删除 3 项」「导出」）；纯告知弹窗可用「好」。"),
    "ellipsis-missing": ("P2", "打开 Sheet / 窗口 / 选择文件的按钮标题没有「…」",
                         "HIG › Buttons（macOS）/ Menus：需要进一步输入或打开新视图的命令，标题末尾加省略号。"),
    "timed-dismiss": ("P1", "提示信息定时自动消失",
                      "HIG › Accessibility：少用限时界面。错误、需要阅读的结果不能只靠几秒后消失的浮层；"
                      "至少悬停时保持，或者在界面里另有地方能找回。"),
    "glass-content": ("P1", "内容层（列表行 / 卡片）上用了 glassEffect",
                      "HIG › Materials：Liquid Glass 只用于功能层（导航、控件）；内容层用标准材质或纯色。"),
    "zh-quote": ("P2", "简体中文界面用了「」引号",
                 "Apple 简体中文界面一律用 “” 弯引号（系统 app 本地化统计：“” 875 处，「」0 处）。"),
    "zh-dots": ("P2", "用三个英文句点代替省略号",
                "用单个省略号字符「…」（U+2026），不要 “...”。"),
    "zh-space": ("P2", "中文和英文 / 数字之间手动加了空格",
                 "macOS 文字排版会在中文与西文、数字之间自动加约 1/8 字宽的间距（实测 13pt 每侧约 1.6pt）；"
                 "手动空格会把间距放大一倍多。Apple 简体中文界面字符串里几乎不手动加空格（1292:6）。"),
    "zh-halfwidth": ("P2", "中文句子里用了半角标点",
                     "中文界面用全角 ，：？！（系统 app 本地化统计：全角逗号 641 处，半角 2 处）。"),
}

# ------------------------------------------------------------------ helpers

STRING_RE = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def strip_comment(line):
    """去掉 // 注释（不处理字符串里的 //，够用）。"""
    out, in_str, i = [], False, 0
    while i < len(line):
        c = line[i]
        if c == '"' and (i == 0 or line[i - 1] != "\\"):
            in_str = not in_str
        if not in_str and line.startswith("//", i):
            break
        out.append(c)
        i += 1
    return "".join(out)


def ignored(raw, rule):
    m = re.search(r"//\s*audit:ignore\b(.*)$", raw)
    if not m:
        return False
    rest = m.group(1).strip()
    ids = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", rest)  # 规则 id 后面可以跟中文说明
    return not ids or rule in ids


def string_literals(code):
    return [m.group(1) for m in STRING_RE.finditer(code)]


def visible_text(s):
    """字符串字面量里去掉插值 \\(...) 之后的可见文字（插值内容未知，当作占位）。"""
    out, i, depth = [], 0, 0
    while i < len(s):
        if s.startswith("\\(", i):
            depth, i = 1, i + 2
            while i < len(s) and depth:
                depth += {"(": 1, ")": -1}.get(s[i], 0)
                i += 1
            out.append("\uFFFC")  # 插值占位
            continue
        out.append(s[i])
        i += 1
    return "".join(out)


def has_cjk(s):
    return re.search(f"[{CJK}]", s) is not None


# ------------------------------------------------------------------ scanner

class Finding:
    def __init__(self, rule, path, line, snippet, detail=""):
        self.rule, self.path, self.line = rule, path, line
        self.snippet = snippet.strip()[:160]
        self.detail = detail
        self.severity = RULES[rule][0]

    def as_dict(self):
        sev, title, why = RULES[self.rule]
        return {"rule": self.rule, "severity": sev, "title": title, "why": why, "file": self.path,
                "line": self.line, "code": self.snippet, "detail": self.detail}


def scan_file(path, rel, enabled):
    try:
        raw_lines = open(path, encoding="utf-8").read().split("\n")
    except (UnicodeDecodeError, OSError):
        return [], {}
    findings = []
    stats = defaultdict(int)

    # 标记 #if DEBUG 块
    debug = [False] * len(raw_lines)
    stack = []
    for i, l in enumerate(raw_lines):
        s = l.strip()
        if s.startswith("#if"):
            stack.append("DEBUG" in s and "!DEBUG" not in s)
        elif s.startswith("#else") and stack:
            stack[-1] = False
        elif s.startswith("#endif") and stack:
            stack.pop()
        debug[i] = any(stack)

    code_lines = [strip_comment(l) for l in raw_lines]

    def add(rule, i, detail=""):
        if rule in enabled and not debug[i] and not ignored(raw_lines[i], rule):
            findings.append(Finding(rule, rel, i + 1, raw_lines[i], detail))

    file_has_dynamic_color = bool(re.search(r"dynamicProvider|colorScheme\s*==|NSAppearance|bestMatch", "\n".join(code_lines)))

    for i, code in enumerate(code_lines):
        window = "\n".join(code_lines[i:i + 8])

        # --- 结构 / 稳定性
        if re.search(r"\.toolbar\s*\{", code):
            body = "\n".join(code_lines[i + 1:i + 4])
            if re.search(r"^\s*if\s", body, re.M) or re.search(r"^\s*switch\s", body, re.M):
                add("toolbar-conditional", i)
        if re.search(r"\.inspector\(\s*isPresented:", code):
            if re.search(r"&&|==|\.section|\.tab|\.page", code):
                add("inspector-conditional", i)
        if re.search(r"\.searchable\(", code):
            if not debug[i] and not ignored(raw_lines[i], "searchable-multi"):
                stats.setdefault("searchable_at", []).append(i)
        if "role: .destructive" in code or "role:.destructive" in code:
            if re.search(r"\.defaultAction|\.return\b", "\n".join(code_lines[i:i + 3])):
                add("destructive-default", i)

        # --- 字体
        for m in re.finditer(r"\.system\(\s*size:\s*([0-9.]+)", code):
            size = float(m.group(1))
            if size < 10:
                add("font-too-small", i, f"{size:g} pt")
            else:
                add("font-fixed", i, f"{size:g} pt")
        for m in re.finditer(r"\.font\(\.custom\([^)]*size:\s*([0-9.]+)(?![^)]*relativeTo)", code):
            add("font-fixed", i, f"custom {m.group(1)} pt，没有 relativeTo")
        m = re.search(r"\.(ultraLight|thin|light)\b", code)
        if m and re.search(r"weight|\.font|fontWeight", code):
            size = re.search(r"size:\s*([0-9.]+)", code)
            # 大号装饰符号（空状态插图等）用细字重没问题；只管正文尺寸的字
            if not size or float(size.group(1)) < 20:
                add("font-thin", i)

        # --- 颜色
        if re.search(r"\b(Color|NSColor|UIColor)\(\s*(red|srgbRed|calibratedRed|deviceRed|hex|\.sRGB)\s*:", code) \
                or re.search(r"#colorLiteral", code):
            if not file_has_dynamic_color:
                add("color-hardcoded", i)
        if re.search(r"\.preferredColorScheme\(\s*\.(dark|light)|NSApp(lication\.shared)?\.appearance\s*=", code):
            add("appearance-override", i)

        # --- 按钮
        # 只在按钮本身这一行判断（往后看几行拼出 label），免得按钮上面几行也被算进去
        if ".labelStyle(.iconOnly)" in code or (re.search(r"\bButton\s*\{", code)
                                                 and re.search(r"Button\s*\{[^}]*\}\s*label:\s*\{\s*Image\(systemName:", window)):
            # 往前后几行找 .help(
            # label 里的图片可能占好几行，.help 常在按钮收尾之后
            ctx = "\n".join(code_lines[max(0, i - 4):i + 9])
            if ".help(" not in ctx:
                add("icon-button-help", i)
        if re.search(r"\.buttonStyle\(\.(borderedProminent|glassProminent)\)", code) \
                and not debug[i] and not ignored(raw_lines[i], "prominent-many"):
            # 行尾写了 audit:ignore prominent-many（比如和另一个按钮二选一）就不计数
            stats["prominent"] += 1
            stats.setdefault("prominent_line", i)
        for m in re.finditer(r'Button\(\s*"(确定|OK|Ok|提交|Submit|是|Yes)"', code):
            add("ok-button", i, m.group(1))
        m = re.search(r'Button\(\s*"([^"\\]+)"\s*(?:,[^)]*)?\)\s*\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*true\s*\}', code)
        if m and not m.group(1).endswith("…") and re.search(r"(sheet|editing|creating|importing|exporting|presented|showing|picker|chooser|dialog)", m.group(2), re.I):
            add("ellipsis-missing", i, m.group(1))
        if re.search(r'Button\(\s*"[^"…]*(选择文件|导入|导出|另存为|打开)[^"…]*"\s*\)', code) and "…" not in code:
            # Sheet 里完成操作的确认按钮（会 dismiss / 绑回车）不需要省略号
            if not re.search(r"dismiss\(\)|\.defaultAction", "\n".join(code_lines[i:i + 8])):
                add("ellipsis-missing", i)

        # --- 定时消失
        if re.search(r"Task\.sleep|asyncAfter", code):
            after = "\n".join(code_lines[i:i + 4])
            if re.search(r"\b\w*(message|toast|error|notice|banner|status)\w*\s*=\s*nil", after, re.I):
                add("timed-dismiss", i)

        # --- 玻璃用在内容层
        if ".glassEffect(" in code:
            ctx = "\n".join(code_lines[max(0, i - 12):i])
            if re.search(r"ForEach|List\s*\(|List\s*\{|LazyVGrid|LazyVStack", ctx):
                add("glass-content", i)

        # --- 中文文案
        for lit in string_literals(code):
            text = visible_text(lit)
            if not has_cjk(text):
                continue
            if "「" in text or "」" in text:
                add("zh-quote", i, lit[:40])
            if "..." in text:
                add("zh-dots", i, lit[:40])
            no_url = re.sub(r"[A-Za-z][A-Za-z0-9+.-]*://\S+", "§", text)  # 网址两边留空格方便选中，不算
            if re.search(f"[{CJK}] [A-Za-z0-9\uFFFC]|[A-Za-z0-9\uFFFC] [{CJK}]", no_url):
                add("zh-space", i, lit[:40])
            if re.search(f"[{CJK}][,:?!;]|[,:?!;][{CJK}]", text):
                add("zh-halfwidth", i, lit[:40])

    return findings, stats


def collect(paths):
    files = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".swift"):
            files.append((p, os.path.basename(p)))
        for root, dirs, names in os.walk(p):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("build", "DerivedData", ".build", "Pods", "Carthage", "Tests")
                       and not d.endswith("Tests")]
            for n in names:
                if n.endswith(".swift"):
                    full = os.path.join(root, n)
                    files.append((full, os.path.relpath(full, p)))
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min", default="P2", choices=["P0", "P1", "P2"])
    ap.add_argument("--rules", help="逗号分隔的规则 id，只跑这些")
    ap.add_argument("--list", action="store_true", help="列出全部规则")
    a = ap.parse_args()

    if a.list:
        for rid, (sev, title, why) in sorted(RULES.items(), key=lambda x: (x[1][0], x[0])):
            print(f"{sev}  {rid:22} {title}\n      {why}")
        return
    if not a.paths:
        ap.error("给一个目录或 .swift 文件")

    enabled = set(a.rules.split(",")) if a.rules else set(RULES)
    unknown = enabled - set(RULES)
    if unknown:
        ap.error("未知规则：" + ", ".join(sorted(unknown)))

    findings, searchable_files, prominent = [], [], []
    for full, rel in collect(a.paths):
        f, stats = scan_file(full, rel, enabled)
        findings += f
        for line in stats.get("searchable_at", []):
            searchable_files.append((rel, line))
        if stats.get("prominent", 0) > 2:
            prominent.append((rel, stats["prominent_line"], stats["prominent"]))

    if "searchable-multi" in enabled and len(searchable_files) > 1:
        for rel, line in searchable_files:
            f = Finding("searchable-multi", rel, line + 1, ".searchable(…)", f"共 {len(searchable_files)} 处")
            findings.append(f)
    if "prominent-many" in enabled:
        for rel, line, n in prominent:
            findings.append(Finding("prominent-many", rel, line + 1, ".buttonStyle(.borderedProminent)", f"{n} 个"))

    limit = SEVERITY_ORDER[a.min]
    findings = [f for f in findings if SEVERITY_ORDER[f.severity] <= limit]
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.rule, f.path, f.line))

    if a.json:
        json.dump([f.as_dict() for f in findings], sys.stdout, ensure_ascii=False, indent=1)
        print()
        return

    if not findings:
        print("没有发现问题（启发式扫描，仍需人工审查）。")
        return
    by_rule = defaultdict(list)
    for f in findings:
        by_rule[(f.severity, f.rule)].append(f)
    counts = defaultdict(int)
    for f in findings:
        counts[f.severity] += 1
    print("汇总：" + "  ".join(f"{s} {counts[s]}" for s in ("P0", "P1", "P2") if counts[s]) + f"  （共 {len(findings)} 处）\n")
    for (sev, rid), items in sorted(by_rule.items(), key=lambda x: (SEVERITY_ORDER[x[0][0]], x[0][1])):
        _, title, why = RULES[rid]
        print(f"## {sev} {rid} — {title}（{len(items)} 处）")
        print(f"   {why}")
        for f in items[:40]:
            extra = f"  [{f.detail}]" if f.detail else ""
            print(f"   {f.path}:{f.line}{extra}  {f.snippet}")
        if len(items) > 40:
            print(f"   … 还有 {len(items) - 40} 处")
        print()


if __name__ == "__main__":
    main()
