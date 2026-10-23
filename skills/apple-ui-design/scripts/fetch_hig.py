#!/usr/bin/env python3
"""把 Apple Human Interface Guidelines 全部页面抓到本地，转成 Markdown，方便 grep 查证。

用法：
    python3 fetch_hig.py <输出目录>                  # 抓全部 HIG（约 170 页，十几秒）
    python3 fetch_hig.py <输出目录> --doc swiftui/applying-liquid-glass-to-custom-views
                                                     # 额外抓开发者文档页（路径取 developer.apple.com/documentation/ 之后的部分）
    python3 fetch_hig.py <输出目录> --changes 2026   # 抓完后打印包含该年份的更新记录

数据来自 developer.apple.com 页面背后的 JSON（和网页同源），只供个人查阅，别把抓下来的原文打包分发。
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.request

BASE = "https://developer.apple.com/tutorials/data"
HIG_ROOT = "/design/human-interface-guidelines"


def inline(items, refs):
    out = ""
    for it in items or []:
        t = it.get("type")
        if t == "text":
            out += it["text"]
        elif t in ("emphasis", "strong"):
            mark = "**" if t == "strong" else "*"
            out += mark + inline(it.get("inlineContent"), refs) + mark
        elif t == "codeVoice":
            out += "`" + it.get("code", "") + "`"
        elif t == "reference":
            ref = refs.get(it.get("identifier"), {})
            out += ref.get("title") or it.get("identifier", "").split("/")[-1]
        elif t == "link":
            out += it.get("title", "")
        elif "inlineContent" in it:
            out += inline(it["inlineContent"], refs)
    return out


def block(b, refs, depth=0):
    t = b.get("type")
    pad = "  " * depth
    if t == "heading":
        return "\n" + "#" * min(b.get("level", 2) + 1, 6) + " " + b.get("text", "") + "\n"
    if t == "paragraph":
        return pad + inline(b.get("inlineContent"), refs) + "\n"
    if t == "codeListing":
        return "```" + (b.get("syntax") or "") + "\n" + "\n".join(b.get("code", [])) + "\n```\n"
    if t in ("unorderedList", "orderedList"):
        s = ""
        for i, li in enumerate(b.get("items", [])):
            body = " ".join(block(x, refs, depth + 1).strip() for x in li.get("content", []))
            s += pad + ("- " if t == "unorderedList" else f"{i + 1}. ") + body.strip() + "\n"
        return s
    if t == "aside":
        inner = " ".join(block(x, refs).strip() for x in b.get("content", []))
        return pad + "> **" + (b.get("name") or b.get("style", "Note")) + "**: " + inner + "\n"
    if t == "table":
        return "".join("| " + " | ".join(" ".join(block(x, refs).strip() for x in cell) for cell in row) + " |\n"
                       for row in b.get("rows", []))
    if t == "row":
        return "".join(block(x, refs, depth) for col in b.get("columns", []) for x in col.get("content", []))
    if t == "tabNavigator":
        return "".join("\n**[" + tab.get("title", "") + "]**\n" + "".join(block(x, refs, depth) for x in tab.get("content", []))
                       for tab in b.get("tabs", []))
    if isinstance(b.get("content"), list):
        return "".join(block(x, refs, depth) for x in b["content"])
    return ""


def fetch(path):
    try:
        with urllib.request.urlopen(BASE + path + ".json", timeout=30) as r:
            return path, json.load(r)
    except Exception as e:  # noqa: BLE001 — 单页失败不影响整体
        print(f"跳过 {path}: {e}", file=sys.stderr)
        return path, None


def render(d):
    refs = d.get("references", {})
    title = d.get("metadata", {}).get("title", "")
    abstract = inline(d.get("abstract"), refs)
    decl = ""
    body = ""
    for sec in d.get("primaryContentSections", []):
        if sec.get("kind") == "declarations":
            for dd in sec.get("declarations", []):
                decl += "```swift\n" + "".join(tok.get("text", "") for tok in dd.get("tokens", [])) + "\n```\n"
        for s in sec.get("content", []):
            body += block(s, refs)
    topics = []
    for sec in d.get("topicSections", []):
        topics.append("\n## " + sec.get("title", ""))
        for ident in sec.get("identifiers", []):
            ref = refs.get(ident, {})
            topics.append(f"- {ref.get('title', '')} — {inline(ref.get('abstract'), refs)}")
    return f"# {title}\n\n{abstract}\n\n{decl}{body}" + "\n".join(topics) + "\n", refs, d


def crawl_hig(out):
    seen, frontier, count = set(), [HIG_ROOT], 0
    while frontier:
        batch = [p for p in dict.fromkeys(frontier) if p not in seen]
        frontier = []
        seen.update(batch)
        with cf.ThreadPoolExecutor(12) as ex:
            for path, d in ex.map(fetch, batch):
                if not d:
                    continue
                text, refs, _ = render(d)
                name = path.rstrip("/").split("/")[-1]
                with open(os.path.join(out, name + ".md"), "w") as f:
                    f.write(text)
                count += 1
                for sec in d.get("topicSections", []):
                    for ident in sec.get("identifiers", []):
                        url = refs.get(ident, {}).get("url", "")
                        if url.startswith(HIG_ROOT + "/") and url not in seen:
                            frontier.append(url)
    return count


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--doc", action="append", default=[], help="额外抓取的开发者文档路径，可重复")
    ap.add_argument("--changes", help="打印包含该字符串（如 2026）的更新记录行")
    ap.add_argument("--no-hig", action="store_true", help="只抓 --doc，不抓 HIG")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    if not args.no_hig:
        print(f"HIG：{crawl_hig(args.out)} 页 → {args.out}")
    for doc in args.doc:
        path, d = fetch("/documentation/" + doc.strip("/"))
        if d:
            text, _, _ = render(d)
            name = "doc_" + re.sub(r"[^A-Za-z0-9._-]+", "_", doc.strip("/"))
            with open(os.path.join(args.out, name + ".md"), "w") as f:
                f.write(text)
            print(f"文档：{doc} → {name}.md")

    if args.changes:
        for fn in sorted(os.listdir(args.out)):
            for line in open(os.path.join(args.out, fn)):
                if line.startswith("| ") and args.changes in line and re.search(r"\d{4} \|", line):
                    print(f"{fn[:-3]:32} {line.strip()}")


if __name__ == "__main__":
    main()
