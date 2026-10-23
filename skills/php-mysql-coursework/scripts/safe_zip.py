#!/usr/bin/env python3
"""
把文件/文件夹打包成 zip，确保非 ASCII（中文等）文件名在 Windows 上解压不乱码。

背景：macOS 自带的 `zip` 命令行工具在打包含中文的文件名时，不会正确设置
Zip 格式里的 UTF-8 文件名标记位（general purpose bit flag 第11位），
不管怎么调 locale、传 -UN=UTF8 参数都绕不过去（Apple 那个编译版本就是这样）。
Windows 上大多数解压工具（包括系统自带的）看到没打这个标记位的中文文件名，
会按本地代码页（GBK等）硬解，直接变成一堆问号或乱码。

Python 3.7+ 的 zipfile 模块在写入非 ASCII 文件名时会自动正确设置这个标记位，
所以用它打包就没有这个问题，不需要额外参数。

用法：
    python3 safe_zip.py 输出.zip 要打包的文件或文件夹 [更多文件或文件夹 ...]

例：
    python3 safe_zip.py 课程设计提交.zip admission_query_system 设计说明书.docx

会自动跳过 .DS_Store、__pycache__、.git 等无关文件，并在打包后自动校验
每一个含非 ASCII 字符的条目是否都带上了 UTF-8 标记位。
"""
import sys
import os
import zipfile

SKIP_NAMES = {".DS_Store", "__pycache__", ".git", "Thumbs.db"}


def should_skip(name: str) -> bool:
    return name in SKIP_NAMES


def add_path(zf: zipfile.ZipFile, path: str) -> None:
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not should_skip(d)]
            for f in files:
                if should_skip(f):
                    continue
                full = os.path.join(root, f)
                zf.write(full, full)
    elif os.path.isfile(path):
        zf.write(path, path)
    else:
        raise FileNotFoundError(f"路径不存在: {path}")


def verify_utf8_flags(zip_path: str) -> None:
    z = zipfile.ZipFile(zip_path)
    bad = []
    for info in z.infolist():
        if not info.filename.isascii() and not (info.flag_bits & 0x800):
            bad.append(info.filename)
    total = len(z.infolist())
    if bad:
        print(f"警告：以下 {len(bad)} 个条目包含非 ASCII 字符但未设置 UTF-8 标记位，"
              f"Windows 上可能显示乱码：")
        for b in bad:
            print("  -", b)
    else:
        non_ascii = sum(1 for i in z.infolist() if not i.filename.isascii())
        print(f"校验通过：共 {total} 个条目，其中 {non_ascii} 个含非 ASCII 文件名，"
              f"全部正确设置了 UTF-8 标记位。")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    out_zip = sys.argv[1]
    sources = sys.argv[2:]

    if os.path.exists(out_zip):
        os.remove(out_zip)

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for src in sources:
            add_path(zf, src)

    size_kb = os.path.getsize(out_zip) / 1024
    print(f"已生成: {out_zip} ({size_kb:.0f} KB)")
    verify_utf8_flags(out_zip)


if __name__ == "__main__":
    main()
