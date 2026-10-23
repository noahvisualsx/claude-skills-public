#!/usr/bin/env python3
"""audit_swiftui.py 的自测：每条规则一个会触发的例子 + 一个不该触发的例子。

用法：python3 test_audit_swiftui.py      # 全部通过时打印 OK
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

BAD = r'''
import SwiftUI
struct Page: View {
    @State private var editing = false
    var body: some View {
        VStack {
            Text("小字").font(.system(size: 9))
            Text("正文").font(.system(size: 14))
            Text("细").font(.system(size: 12, weight: .light))
            Circle().fill(Color(red: 0.2, green: 0.3, blue: 0.4))
            Button("编辑", systemImage: "pencil") { }.labelStyle(.iconOnly)
            Button("确定") { }
            Button("编辑当前 Skill") { editing = true }
            Button("删除", role: .destructive) { }
                .keyboardShortcut(.defaultAction)
            Text("写进系统日历「织知待办」")
            Text("正在加载...")
            Text("今天 \(3) 件")
            Text("出错了,请重试")
            ForEach(0..<3) { i in
                Text("\(i)")
                    .padding()
                    .glassEffect()
            }
        }
        .toolbar {
            if editing {
                ToolbarItem { Button("A") { } }
            }
        }
        .inspector(isPresented: Binding(get: { editing && section == .create }, set: { _ in })) { Text("x") }
        .searchable(text: .constant(""))
        .preferredColorScheme(.dark)
        .task { try? await Task.sleep(for: .seconds(3)); message = nil }
    }
}
struct Other: View {
    var body: some View { List { }.searchable(text: .constant("")) }
}
struct Prominent: View {
    var body: some View {
        Button("A") { }.buttonStyle(.borderedProminent)
        Button("B") { }.buttonStyle(.borderedProminent)
        Button("C") { }.buttonStyle(.borderedProminent)
    }
}
'''

GOOD = r'''
import SwiftUI
struct Page: View {
    @State private var editing = false
    var body: some View {
        VStack {
            Text("标题").font(.title2)
            Image(systemName: "tray").font(.system(size: 40, weight: .light)) // audit:ignore font-fixed（空状态插图）
            Button("编辑", systemImage: "pencil") { }.labelStyle(.iconOnly).help("编辑这条")
            Button("编辑当前Skill…") { editing = true }
            Button("删除", role: .destructive) { }
            Button("导入") { save(); dismiss() }
            Text("写进系统日历“织知待办”")
            Text("正在加载…")
            Text("今天\(3)件")
            Text("出错了，请重试。")
            Text("English text, fine: ok?")
            Text("先到 https://brew.sh 安装")
            #if DEBUG
            Text("调试 \(1) 次").font(.system(size: 8))
            #endif
        }
        .toolbar {
            ToolbarItem { Button("A") { } }
        }
        .inspector(isPresented: $editing) { Text("x") }
    }
}
'''

EXPECT_BAD = {
    "font-too-small", "font-fixed", "font-thin", "color-hardcoded", "icon-button-help", "ok-button",
    "ellipsis-missing", "destructive-default", "zh-quote", "zh-dots", "zh-space", "zh-halfwidth",
    "glass-content", "toolbar-conditional", "inspector-conditional", "searchable-multi",
    "appearance-override", "timed-dismiss", "prominent-many",
}


def run(tmp):
    out = subprocess.run([sys.executable, os.path.join(HERE, "audit_swiftui.py"), tmp, "--json"],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def main():
    with tempfile.TemporaryDirectory() as d:
        bad_dir, good_dir = os.path.join(d, "bad"), os.path.join(d, "good")
        os.makedirs(bad_dir)
        os.makedirs(good_dir)
        open(os.path.join(bad_dir, "Bad.swift"), "w").write(BAD)
        open(os.path.join(good_dir, "Good.swift"), "w").write(GOOD)
        bad = {f["rule"] for f in run(bad_dir)}
        good = run(good_dir)

    failed = False
    missing = EXPECT_BAD - bad
    if missing:
        failed = True
        print("应该报但没报：", ", ".join(sorted(missing)))
    if good:
        failed = True
        print("不该报却报了：")
        for f in good:
            print(f"  {f['rule']}  line {f['line']}: {f['code']}")
    if failed:
        sys.exit(1)
    print(f"OK：{len(EXPECT_BAD)} 条规则都能触发，干净样例没有误报。")


if __name__ == "__main__":
    main()
