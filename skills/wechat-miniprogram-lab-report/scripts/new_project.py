#!/usr/bin/env python3
"""创建一个"不使用云服务、不使用模板"的最小微信小程序项目骨架。
用法: python3 new_project.py 项目目录 --appid wx... [--name 项目名] [--pages index,logs,route]
之后由 AI 按题目要求覆盖 app.json / 各页面四件套。
"""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--appid", default="touristappid")
ap.add_argument("--name", default=None)
ap.add_argument("--pages", default="index")
a = ap.parse_args()

pages = [p.strip() for p in a.pages.split(",") if p.strip()]
os.makedirs(a.dir, exist_ok=True)

def w(rel, content):
    p = os.path.join(a.dir, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        return
    with open(p, "w", encoding="utf-8") as f:
        f.write(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2))

w("app.js", "App({})\n")
w("app.json", {"pages": [f"pages/{p}/{p}" for p in pages],
               "window": {"navigationBarBackgroundColor": "#ffffff", "navigationBarTextStyle": "black",
                          "navigationBarTitleText": a.name or "小程序"},
               "style": "v2", "sitemapLocation": "sitemap.json"})
w("app.wxss", "page {\n  font-size: 30rpx;\n}\n")
w("sitemap.json", {"rules": [{"action": "allow", "page": "*"}]})
w("project.config.json", {"appid": a.appid, "projectname": a.name or os.path.basename(os.path.abspath(a.dir)),
                          "compileType": "miniprogram", "libVersion": "trial",
                          "setting": {"es6": True, "postcss": True, "minified": True, "enhance": True,
                                      "urlCheck": False},
                          "condition": {}, "editorSetting": {"tabIndent": "insertSpaces", "tabSize": 2}})
for p in pages:
    w(f"pages/{p}/{p}.js", "Page({\n  data: {}\n})\n")
    w(f"pages/{p}/{p}.json", {"usingComponents": {}})
    w(f"pages/{p}/{p}.wxml", f"<view class=\"container\">{p} 页面</view>\n")
    w(f"pages/{p}/{p}.wxss", ".container {\n  padding: 30rpx;\n}\n")
print("项目已创建:", os.path.abspath(a.dir))
