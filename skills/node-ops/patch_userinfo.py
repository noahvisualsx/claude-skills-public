#!/usr/bin/env python3
# 给 sub-server.py 加真实的 Subscription-Userinfo 头（小火箭/Clash 显示的流量和到期）。
# 用法: python3 patch_userinfo.py <sub-server.py 路径>   幂等, 已打过补丁就跳过。
import sys

path = sys.argv[1]
src = open(path, encoding="utf-8").read()

if "def userinfo():" in src:
    print("already patched")
    sys.exit(0)

OLD_HDR = 'self.send_header("Subscription-Userinfo", "upload=0; download=0; total=0; expire=0")'
assert src.count(OLD_HDR) == 1, "header line not found exactly once"
assert src.count("\nclass H(") == 1, "handler class not found exactly once"

FUNC = '''
# ---------- 订阅头里的流量信息 (小火箭/Clash 顶部的 ↑ ↓ TOT EXPIRE) ----------
# 用量读 vnstat 的本月统计 (重启不丢); 额度和到期写在 nodes.json:
#   "quota_gb": 服务商每月流量额度 (GB), 0 = 未知
#   "expire":   到期时间 Unix 时间戳, 0 = 不显示 (按量付费的机器填 0)
QUOTA_GB = float(_C.get("quota_gb", 0) or 0)
EXPIRE = int(_C.get("expire", 0) or 0)
_UI_CACHE = [0.0, ""]


def userinfo():
    if _UI_CACHE[1] and time.time() - _UI_CACHE[0] < 60:
        return _UI_CACHE[1]
    up = down = 0
    try:
        r = subprocess.run(["ip", "route", "show", "default"],
                           stdout=subprocess.PIPE, universal_newlines=True, timeout=5).stdout.split()
        dev = r[r.index("dev") + 1]
        out = subprocess.run(["vnstat", "--json", "m", "-i", dev],
                             stdout=subprocess.PIPE, universal_newlines=True, timeout=5).stdout
        t = json.loads(out)["interfaces"][0]["traffic"]
        now = time.localtime()
        for m in t.get("month") or t.get("months") or []:
            if m["date"]["year"] == now.tm_year and m["date"]["month"] == now.tm_mon:
                # 服务器收到的算上行, 发出的算下行 (服务商一般按出站计费, 对应 ↓)
                up, down = int(m["rx"]), int(m["tx"])
    except Exception:
        pass
    s = "upload=%d; download=%d; total=%d; expire=%d" % (
        up, down, int(QUOTA_GB * 1024 ** 3), EXPIRE)
    _UI_CACHE[:] = [time.time(), s]
    return s

'''

src = src.replace(OLD_HDR, 'self.send_header("Subscription-Userinfo", userinfo())')
src = src.replace("\nclass H(", FUNC + "\nclass H(", 1)
open(path, "w", encoding="utf-8").write(src)
print("patched")
