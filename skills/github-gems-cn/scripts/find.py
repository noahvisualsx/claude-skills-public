"""在 GitHub 上找最近新建、星数涨得快、适合写推荐帖的开源项目。

用法：
    python3 find.py                      默认最近 60 天，星数 500 以上
    python3 find.py --days 30 --min 1000
    python3 find.py --query "video editor"   再加一组关键词搜索
输出 TSV：星数、仓库、创建日期、协议、语言、一周涨速（星/天）、简介。
已经推荐过的（已推荐清单.md 里出现的仓库名）会被排除。
依赖：已登录的 gh 命令行。
"""
import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

POSTED = Path.home() / "图文创作/00-素材库/GitHub开源推荐/已推荐清单.md"

# 默认几组搜索：泛搜 + 平替 + Mac 应用 + 创作者工具
BASE_QUERIES = [
    "",
    "alternative",
    "topic:macos",
    "editor",
    "open-source app",
]

# 不适合发的方向：模型推理框架、游戏破解、下载器、加密货币、成人内容、纯学术
SKIP = re.compile(
    r"inference|benchmark|dataset|paper|crack|piracy|torrent|emulat|\broms?\b|nsfw|crypto|token sale|wallet|"
    r"downloader|无水印|下载|破解|免费不限量|jailbreak|\bNSP\b|switch games|compatibility layer for|games? natively",
    re.I,
)


def search(q, days, min_stars):
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    full = f"created:>{since} stars:>{min_stars} {q}".strip()
    out = subprocess.run(
        ["gh", "api", "-X", "GET", "search/repositories", "-f", f"q={full}", "-f", "sort=stars",
         "-f", "per_page=50"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out).get("items", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--min", type=int, default=500)
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--all", action="store_true", help="不排除已推荐和不适合的方向")
    a = ap.parse_args()

    posted = POSTED.read_text("utf-8").lower() if POSTED.exists() else ""
    seen, rows = set(), []
    for q in BASE_QUERIES + a.query:
        for it in search(q, a.days, a.min):
            name = it["full_name"]
            if name in seen:
                continue
            seen.add(name)
            desc = (it.get("description") or "").replace("\t", " ").replace("\n", " ")
            if not a.all and (name.lower() in posted or SKIP.search(desc) or it.get("fork")):
                continue
            created = dt.date.fromisoformat(it["created_at"][:10])
            age = max(1, (dt.date.today() - created).days)
            rows.append((it["stargazers_count"], name, created.isoformat(),
                         (it.get("license") or {}).get("spdx_id") or "-", it.get("language") or "-",
                         round(it["stargazers_count"] / age), desc[:110]))
    rows.sort(key=lambda r: -r[5])
    print("星数\t仓库\t创建\t协议\t语言\t星/天\t简介")
    for r in rows:
        print("\t".join(str(x) for x in r))


if __name__ == "__main__":
    main()
