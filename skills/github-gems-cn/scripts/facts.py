"""核对一个或几个仓库写帖子要用的事实，输出 JSON。

用法：
    python3 facts.py owner/repo [owner/repo ...]

每个仓库给出：星数、创建日期、上线天数、协议、主页、最新版本、各平台安装包大小、
README 前 60 行（去掉图片和徽章）、README 里有没有提到 AI 写代码。
帖子里的数字只能从这里来，不要凭印象写。
"""
import base64
import datetime as dt
import json
import re
import subprocess
import sys


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


PLATFORM = [("mac", r"mac|osx|darwin|\.dmg"), ("windows", r"win|\.exe|\.msi"),
            ("linux", r"linux|\.deb|\.rpm|appimage|flatpak"), ("android", r"\.apk|android"), ("ios", r"\.ipa|ios")]
AI_WORDS = re.compile(r"written (?:entirely |mostly )?(?:by|with) (?:ai|claude|codex|gpt|an llm)|vibe.?cod|"
                      r"built (?:with|using) (?:claude|codex|cursor|ai)|ai[- ]generated code|co-?authored by claude", re.I)


def facts(name):
    repo = gh(f"repos/{name}")
    if not repo:
        return {"repo": name, "error": "找不到这个仓库"}
    created = dt.date.fromisoformat(repo["created_at"][:10])
    out = {
        "repo": name,
        "url": f"github.com/{name}",
        "stars": repo["stargazers_count"],
        "created": created.isoformat(),
        "days_online": (dt.date.today() - created).days,
        "license": (repo.get("license") or {}).get("spdx_id"),
        "license_name": (repo.get("license") or {}).get("name"),
        "homepage": repo.get("homepage"),
        "description": repo.get("description"),
        "archived": repo.get("archived"),
        "checked_on": dt.date.today().isoformat(),
    }
    rel = gh(f"repos/{name}/releases/latest")
    if rel:
        out["release"] = rel.get("tag_name")
        sizes = {}
        for a in rel.get("assets", []):
            n = a["name"].lower()
            if n.endswith((".sha256", ".txt", ".zsync", ".sig", ".asc", ".blockmap", ".yml")):
                continue
            for plat, pat in PLATFORM:
                if re.search(pat, n):
                    mb = round(a["size"] / 1048576, 1)
                    sizes.setdefault(plat, []).append(f"{a['name']} {mb}MB")
                    break
        out["installers"] = sizes
    readme = gh(f"repos/{name}/readme")
    if readme:
        text = base64.b64decode(readme["content"]).decode("utf-8", "ignore")
        lines = [l for l in text.splitlines()
                 if l.strip() and not re.match(r"\s*(<|!\[|\[!\[)", l) and "shields.io" not in l]
        out["readme_head"] = "\n".join(lines[:60])
        hits = sorted({m.group(0) for m in AI_WORDS.finditer(text)})
        out["readme_says_ai_wrote_code"] = hits or False
    return out


if __name__ == "__main__":
    print(json.dumps([facts(n) for n in sys.argv[1:]], ensure_ascii=False, indent=2))
