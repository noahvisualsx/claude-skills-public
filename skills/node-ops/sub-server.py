#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""订阅服务器 —— 多格式 + UA 自动识别
   /            落地页 (含二维码)
   /sub         按客户端 UA 自动返回格式  <- 一个链接通吃
   /clash /singbox /conf /base64 /surge /loon /quanx  指定格式
"""
import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# -*- coding: utf-8 -*-
"""节点定义与规则集 —— 所有订阅格式共用这一份数据"""

# ---- 节点参数从 JSON 配置加载, 跨机器复用无需改代码 ----
CFG_PATH = os.environ.get("NODE_OPS_CFG", "/usr/local/etc/node-ops/nodes.json")
with open(CFG_PATH, encoding="utf-8") as _f:
    _C = json.load(_f)

IP = _C["ip"]
PORT = int(_C.get("port", 2097))
UUID1, PBK1, SID1 = _C["uuid1"], _C["pbk1"], _C["sid1"]
UUID2, PBK2, SID2 = _C["uuid2"], _C["pbk2"], _C["sid2"]
HY2PW = _C["hy2pw"]
SNI = _C.get("sni", "www.apple.com")
TAG = _C.get("tag", "NODE")

N1 = "%s-01-直连" % TAG
N2 = "%s-02-智能分流-推荐" % TAG
N3 = "%s-03-Hy2-抗丢包" % TAG

GRP_MAIN = "节点选择"
GRP_AI = "AI"
GRP_STREAM = "流媒体"
GRP_AUTO = "自动选择"

AI_DOMAINS = [
    "openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com", "sora.com",
    "anthropic.com", "claude.ai", "claudeusercontent.com",
    # Gemini 系不放这里: WARP 出口被 Google 判定为 RU, 会触发"地区不支持";
    # 移除后它们由 google.com / googleapis.com 规则兜到"节点选择"(直连出口, 判定 US)。
    "perplexity.ai", "x.ai", "grok.com", "poe.com", "copilot.microsoft.com",
    "githubcopilot.com", "cursor.sh", "midjourney.com",
]

STREAM_DOMAINS = [
    "netflix.com", "nflxvideo.net", "nflximg.net", "nflxext.com", "nflxso.net",
    "disneyplus.com", "disney-plus.net", "dssott.com", "bamgrid.com",
    "hbomax.com", "max.com", "hbo.com", "primevideo.com", "aiv-cdn.net",
    "youtube.com", "googlevideo.com", "ytimg.com", "youtu.be",
    "spotify.com", "scdn.co", "tiktokv.com", "twitch.tv", "ttvnw.net",
]

FOREIGN_DOMAINS = [
    "google.com", "gstatic.com", "googleapis.com", "googleusercontent.com",
    "google-analytics.com", "ggpht.com", "withgoogle.com",
    "github.com", "githubusercontent.com", "githubassets.com", "ghcr.io",
    "twitter.com", "x.com", "twimg.com", "t.co",
    "facebook.com", "fbcdn.net", "instagram.com", "cdninstagram.com",
    "telegram.org", "t.me", "telesco.pe", "telegram.me",
    "wikipedia.org", "wikimedia.org", "reddit.com", "redd.it", "redditstatic.com",
    "medium.com", "quora.com", "stackoverflow.com", "stackexchange.com",
    "cloudflare.com", "docker.com", "npmjs.com", "pypi.org", "python.org",
    "rust-lang.org", "golang.org", "go.dev", "jsdelivr.net", "unpkg.com",
    "discord.com", "discordapp.com", "discord.gg", "whatsapp.com", "line.me",
    "notion.so", "figma.com", "vercel.com", "vercel.app", "netlify.app",
    "bing.com", "duckduckgo.com", "protonmail.com", "proton.me",
    "nytimes.com", "bbc.com", "bbc.co.uk", "cnn.com", "reuters.com",
]

# Apple 系必须直连: 从国外 IP 访问会触发地区不符 (Apple Music 用不了)
APPLE_DIRECT = [
    "apple.com", "icloud.com", "mzstatic.com", "aaplimg.com",
    "cdn-apple.com", "apple-cloudkit.com", "itunes.com", "me.com",
]

# Kakao / 韩国系必须直连: 从美国 IP 访问触发地区锁, KakaoTalk 登录不上/反复重连
# (2026-08-31 实测: katalk.kakao.com 走代理后 575 次重复连接失败)
KAKAO_DIRECT = [
    "kakao.com", "kakaocdn.net", "kakaopay.com", "kakaocorp.com",
    "kakao.co.kr", "onkakao.net", "kakaogame.com", "kakaoenterprise.com",
    "daum.net", "daumcdn.net", "kakaoicloud.com",
]
# 注意: naver / line / melon 故意不放进来 —— 它们在国内是被墙的,
# 改 DIRECT 会让它们彻底不可用; line.me 还与"国外常用→代理"规则冲突。

CN_DOMAINS = [
    "baidu.com", "qq.com", "weixin.qq.com", "taobao.com", "tmall.com", "alipay.com",
    "alicdn.com", "aliyun.com", "aliyuncs.com", "jd.com", "163.com", "126.com",
    "126.net", "netease.com", "bilibili.com", "hdslb.com",
    "zhihu.com", "zhimg.com", "douban.com", "weibo.com", "sina.com.cn", "sinaimg.cn",
    "douyin.com", "bytedance.com", "byteimg.com", "ixigua.com", "toutiao.com",
    "iqiyi.com", "youku.com", "mgtv.com", "qqmail.com", "meituan.com", "dianping.com",
    "xiaohongshu.com", "xhscdn.com", "pinduoduo.com", "yangkeduo.com", "ctrip.com",
    "12306.cn", "unionpay.com", "cmbchina.com", "icbc.com.cn", "gov.cn", "edu.cn",
    "org.cn", "com.cn", "net.cn", "cn",
]

PRIVATE_CIDR = [
    "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12", "127.0.0.0/8",
    "100.64.0.0/10", "224.0.0.0/4", "17.0.0.0/8",
]

# ============================================================
#  各客户端格式生成器
# ============================================================
import base64 as _b64
import json as _json
from urllib.parse import quote as _q


def _uris():
    """通用分享链接 (v2rayN / v2rayNG / NekoBox / Shadowrocket 扫码均可)"""
    return [
        "vless://%s@%s:443?encryption=none&flow=xtls-rprx-vision&security=reality"
        "&sni=%s&fp=chrome&pbk=%s&sid=%s&type=tcp#%s" % (UUID1, IP, SNI, PBK1, SID1, _q(N1)),
        "vless://%s@%s:2053?encryption=none&flow=xtls-rprx-vision&security=reality"
        "&sni=%s&fp=chrome&pbk=%s&sid=%s&type=tcp#%s" % (UUID2, IP, SNI, PBK2, SID2, _q(N2)),
        "hysteria2://%s@%s:8443/?insecure=1&sni=%s#%s" % (HY2PW, IP, SNI, _q(N3)),
    ]


def build_base64():
    return _b64.b64encode("\n".join(_uris()).encode()).decode()


def build_plain():
    return "\n".join(_uris()) + "\n"


# ---------- Clash.Meta / mihomo ----------
def build_clash():
    L = []
    L.append("# Clash.Meta (mihomo) 配置 —— 需要 Meta 内核, 原版 Clash 不支持 VLESS/Reality/Hysteria2")
    L.append("mixed-port: 7890")
    L.append("allow-lan: false")
    L.append("mode: rule")
    L.append("log-level: info")
    L.append("unified-delay: true")
    L.append("tcp-concurrent: true")
    L.append("find-process-mode: strict")
    L.append("profile:")
    L.append("  store-selected: true")
    L.append("  store-fake-ip: true")
    L.append("dns:")
    L.append("  enable: true")
    L.append("  listen: 0.0.0.0:1053")
    L.append("  ipv6: false")
    L.append("  enhanced-mode: fake-ip")
    L.append("  fake-ip-range: 198.18.0.1/16")
    L.append("  fake-ip-filter:")
    L.append("    - '*.lan'")
    L.append("    - '*.local'")
    L.append("    - 'localhost.ptlogin2.qq.com'")
    L.append("  default-nameserver:")
    L.append("    - 223.5.5.5")
    L.append("  nameserver:")
    L.append("    - https://223.5.5.5/dns-query")
    L.append("    - https://1.1.1.1/dns-query")
    L.append("  proxy-server-nameserver:")
    L.append("    - https://223.5.5.5/dns-query")
    L.append("")
    L.append("proxies:")
    L.append("  - name: \"%s\"" % N1)
    L.append("    type: vless")
    L.append("    server: %s" % IP)
    L.append("    port: 443")
    L.append("    uuid: %s" % UUID1)
    L.append("    network: tcp")
    L.append("    udp: true")
    L.append("    tls: true")
    L.append("    flow: xtls-rprx-vision")
    L.append("    servername: %s" % SNI)
    L.append("    client-fingerprint: chrome")
    L.append("    reality-opts:")
    L.append("      public-key: %s" % PBK1)
    L.append("      short-id: \"%s\"" % SID1)
    L.append("  - name: \"%s\"" % N2)
    L.append("    type: vless")
    L.append("    server: %s" % IP)
    L.append("    port: 2053")
    L.append("    uuid: %s" % UUID2)
    L.append("    network: tcp")
    L.append("    udp: true")
    L.append("    tls: true")
    L.append("    flow: xtls-rprx-vision")
    L.append("    servername: %s" % SNI)
    L.append("    client-fingerprint: chrome")
    L.append("    reality-opts:")
    L.append("      public-key: %s" % PBK2)
    L.append("      short-id: \"%s\"" % SID2)
    L.append("  - name: \"%s\"" % N3)
    L.append("    type: hysteria2")
    L.append("    server: %s" % IP)
    L.append("    port: 8443")
    L.append("    password: \"%s\"" % HY2PW)
    L.append("    sni: %s" % SNI)
    L.append("    skip-cert-verify: true")
    L.append("    udp: true")
    L.append("")
    L.append("proxy-groups:")
    L.append("  - name: \"%s\"" % GRP_MAIN)
    L.append("    type: select")
    L.append("    proxies: [\"%s\", \"%s\", \"%s\", \"%s\", DIRECT]" % (N2, N1, GRP_AUTO, N3))
    L.append("  - name: \"%s\"" % GRP_AI)
    L.append("    type: select")
    L.append("    proxies: [\"%s\", \"%s\", \"%s\"]" % (N2, N3, N1))
    L.append("  - name: \"%s\"" % GRP_STREAM)
    L.append("    type: select")
    L.append("    proxies: [\"%s\", \"%s\", \"%s\", \"%s\"]" % (N2, N1, N3, GRP_AUTO))
    L.append("  - name: \"%s\"" % GRP_AUTO)
    L.append("    type: url-test")
    L.append("    proxies: [\"%s\", \"%s\", \"%s\"]" % (N2, N1, N3))
    L.append("    url: http://www.gstatic.com/generate_204")
    L.append("    interval: 600")
    L.append("    tolerance: 100")
    L.append("")
    L.append("rules:")
    for c in PRIVATE_CIDR:
        L.append("  - IP-CIDR,%s,DIRECT,no-resolve" % c)
    for d in AI_DOMAINS:
        L.append("  - DOMAIN-SUFFIX,%s,%s" % (d, GRP_AI))
    for d in STREAM_DOMAINS:
        L.append("  - DOMAIN-SUFFIX,%s,%s" % (d, GRP_STREAM))
    for d in FOREIGN_DOMAINS:
        L.append("  - DOMAIN-SUFFIX,%s,%s" % (d, GRP_MAIN))
    for d in APPLE_DIRECT + KAKAO_DIRECT:
        L.append("  - DOMAIN-SUFFIX,%s,DIRECT" % d)
    for d in CN_DOMAINS:
        L.append("  - DOMAIN-SUFFIX,%s,DIRECT" % d)
    L.append("  # Kakao LOCO 协议二段连接是裸 IP 无域名, 域名规则抓不到, 靠 GEOIP 兜底")
    L.append("  - GEOIP,KR,DIRECT")
    L.append("  - GEOIP,CN,DIRECT")
    L.append("  - MATCH,%s" % GRP_MAIN)
    return "\n".join(L) + "\n"


# ---------- sing-box (SFI/SFA/SFM, Hiddify, Karing) ----------
def build_singbox():
    out_v1 = {
        "type": "vless", "tag": N1, "server": IP, "server_port": 443,
        "uuid": UUID1, "flow": "xtls-rprx-vision",
        "tls": {"enabled": True, "server_name": SNI,
                "utls": {"enabled": True, "fingerprint": "chrome"},
                "reality": {"enabled": True, "public_key": PBK1, "short_id": SID1}},
    }
    out_v2 = {
        "type": "vless", "tag": N2, "server": IP, "server_port": 2053,
        "uuid": UUID2, "flow": "xtls-rprx-vision",
        "tls": {"enabled": True, "server_name": SNI,
                "utls": {"enabled": True, "fingerprint": "chrome"},
                "reality": {"enabled": True, "public_key": PBK2, "short_id": SID2}},
    }
    out_h = {
        "type": "hysteria2", "tag": N3, "server": IP, "server_port": 8443,
        "password": HY2PW,
        "tls": {"enabled": True, "server_name": SNI, "insecure": True},
    }
    names = [N2, N1, N3]
    cfg = {
        "log": {"level": "warn", "timestamp": True},
        "dns": {
            "servers": [
                {"tag": "dns-remote", "address": "https://1.1.1.1/dns-query",
                 "detour": GRP_MAIN},
                {"tag": "dns-direct", "address": "https://223.5.5.5/dns-query",
                 "detour": "direct"},
            ],
            "rules": [{"rule_set": "geosite-cn", "server": "dns-direct"}],
            "final": "dns-remote", "strategy": "ipv4_only",
        },
        "inbounds": [{
            "type": "mixed", "tag": "mixed-in",
            "listen": "127.0.0.1", "listen_port": 2080,
        }],
        "outbounds": [
            {"type": "selector", "tag": GRP_MAIN,
             "outbounds": [GRP_AUTO] + names + ["direct"], "default": N2},
            {"type": "selector", "tag": GRP_AI, "outbounds": [N2, N3, N1], "default": N2},
            {"type": "selector", "tag": GRP_STREAM,
             "outbounds": names + [GRP_AUTO], "default": N2},
            {"type": "urltest", "tag": GRP_AUTO, "outbounds": names,
             "url": "http://www.gstatic.com/generate_204", "interval": "10m",
             "tolerance": 100},
            out_v1, out_v2, out_h,
            {"type": "direct", "tag": "direct"},
        ],
        "route": {
            "rules": [
                {"action": "sniff"},
                {"protocol": "dns", "action": "hijack-dns"},
                {"ip_is_private": True, "outbound": "direct"},
                {"domain_suffix": AI_DOMAINS, "outbound": GRP_AI},
                {"domain_suffix": STREAM_DOMAINS, "outbound": GRP_STREAM},
                {"domain_suffix": FOREIGN_DOMAINS, "outbound": GRP_MAIN},
                {"domain_suffix": APPLE_DIRECT + KAKAO_DIRECT, "outbound": "direct"},
                {"domain_suffix": CN_DOMAINS, "outbound": "direct"},
                {"rule_set": "geoip-kr", "outbound": "direct"},
                {"rule_set": "geoip-cn", "outbound": "direct"},
            ],
            "rule_set": [
                {"type": "remote", "tag": "geosite-cn", "format": "binary",
                 "url": "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-cn.srs",
                 "download_detour": GRP_MAIN},
                {"type": "remote", "tag": "geoip-cn", "format": "binary",
                 "url": "https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/geoip-cn.srs",
                 "download_detour": GRP_MAIN},
                {"type": "remote", "tag": "geoip-kr", "format": "binary",
                 "url": "https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/geoip-kr.srs",
                 "download_detour": GRP_MAIN},
            ],
            "final": GRP_MAIN,
            "auto_detect_interface": True,
        },
        "experimental": {
            "cache_file": {"enabled": True, "store_fakeip": False},
            "clash_api": {"external_controller": "127.0.0.1:9090"},
        },
    }
    return _json.dumps(cfg, indent=2, ensure_ascii=False)


# ---------- Surge (仅 Hysteria2, Surge 不支持 VLESS/Reality) ----------
def build_surge():
    L = []
    L.append("#!MANAGED-CONFIG http://%s:%d/surge interval=43200 strict=false" % (IP, PORT))
    L.append("# 注意: Surge 不支持 VLESS / Reality, 因此只有 Hysteria2 节点可用")
    L.append("# 需要 Surge 5.8+ 才支持 hysteria2")
    L.append("")
    L.append("[General]")
    L.append("dns-server = system")
    L.append("skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10, 17.0.0.0/8, localhost, *.local")
    L.append("ipv6 = false")
    L.append("")
    L.append("[Proxy]")
    L.append("%s = hysteria2, %s, 8443, password=%s, sni=%s, skip-cert-verify=true, download-bandwidth=200"
             % (N3, IP, HY2PW, SNI))
    L.append("")
    L.append("[Proxy Group]")
    L.append("%s = select, %s, DIRECT" % (GRP_MAIN, N3))
    L.append("")
    L.append("[Rule]")
    for c in PRIVATE_CIDR:
        L.append("IP-CIDR,%s,DIRECT,no-resolve" % c)
    for d in AI_DOMAINS + STREAM_DOMAINS + FOREIGN_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,%s" % (d, GRP_MAIN))
    for d in APPLE_DIRECT + KAKAO_DIRECT + CN_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,DIRECT" % d)
    L.append("GEOIP,KR,DIRECT")
    L.append("GEOIP,CN,DIRECT")
    L.append("FINAL,%s" % GRP_MAIN)
    return "\n".join(L) + "\n"


# ---------- Loon ----------
def build_loon():
    L = []
    L.append("#!MANAGED-CONFIG http://%s:%d/loon interval=43200 strict=false" % (IP, PORT))
    L.append("[General]")
    L.append("dns-server = system")
    L.append("ipv6 = false")
    L.append("skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, localhost, *.local")
    L.append("")
    L.append("[Proxy]")
    L.append("%s = vless,%s,443,\"%s\",transport=tcp,over-tls=true,tls-name=%s,flow=xtls-rprx-vision,"
             "public-key=%s,short-id=%s,udp=true" % (N1, IP, UUID1, SNI, PBK1, SID1))
    L.append("%s = vless,%s,2053,\"%s\",transport=tcp,over-tls=true,tls-name=%s,flow=xtls-rprx-vision,"
             "public-key=%s,short-id=%s,udp=true" % (N2, IP, UUID2, SNI, PBK2, SID2))
    L.append("%s = Hysteria2,%s,8443,\"%s\",sni=%s,skip-cert-verify=true,udp=true"
             % (N3, IP, HY2PW, SNI))
    L.append("")
    L.append("[Proxy Group]")
    L.append("%s = select,%s,%s,%s,%s,DIRECT" % (GRP_MAIN, N2, N1, GRP_AUTO, N3))
    L.append("%s = select,%s,%s,%s" % (GRP_AI, N2, N3, N1))
    L.append("%s = select,%s,%s,%s" % (GRP_STREAM, N2, N1, N3))
    L.append("%s = url-test,%s,%s,%s,url=http://www.gstatic.com/generate_204,interval=600"
             % (GRP_AUTO, N2, N1, N3))
    L.append("")
    L.append("[Rule]")
    for c in PRIVATE_CIDR:
        L.append("IP-CIDR,%s,DIRECT,no-resolve" % c)
    for d in AI_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,%s" % (d, GRP_AI))
    for d in STREAM_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,%s" % (d, GRP_STREAM))
    for d in FOREIGN_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,%s" % (d, GRP_MAIN))
    for d in APPLE_DIRECT + KAKAO_DIRECT + CN_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,DIRECT" % d)
    L.append("GEOIP,KR,DIRECT")
    L.append("GEOIP,CN,DIRECT")
    L.append("FINAL,%s" % GRP_MAIN)
    return "\n".join(L) + "\n"


# ---------- Quantumult X ----------
def build_quanx():
    L = []
    L.append("; Quantumult X 配置片段")
    L.append("; VLESS/Reality 支持取决于 QuanX 版本, 若节点不可用请改用 Hysteria2 那条")
    L.append("")
    L.append("[server_local]")
    L.append("vless=%s:443, method=none, password=%s, obfs=over-tls, obfs-host=%s, "
             "tls-verification=true, fast-open=false, udp-relay=true, tag=%s"
             % (IP, UUID1, SNI, N1))
    L.append("vless=%s:2053, method=none, password=%s, obfs=over-tls, obfs-host=%s, "
             "tls-verification=true, fast-open=false, udp-relay=true, tag=%s"
             % (IP, UUID2, SNI, N2))
    L.append("hysteria2=%s:8443, password=%s, tls-host=%s, tls-verification=false, "
             "fast-open=false, udp-relay=true, tag=%s" % (IP, HY2PW, SNI, N3))
    L.append("")
    L.append("[policy]")
    L.append("static=%s, %s, %s, %s, direct" % (GRP_MAIN, N2, N1, N3))
    L.append("static=%s, %s, %s, %s" % (GRP_AI, N2, N3, N1))
    L.append("")
    L.append("[filter_local]")
    for d in AI_DOMAINS:
        L.append("host-suffix, %s, %s" % (d, GRP_AI))
    for d in STREAM_DOMAINS + FOREIGN_DOMAINS:
        L.append("host-suffix, %s, %s" % (d, GRP_MAIN))
    for d in APPLE_DIRECT + KAKAO_DIRECT + CN_DOMAINS:
        L.append("host-suffix, %s, direct" % d)
    L.append("geoip, kr, direct")
    L.append("geoip, cn, direct")
    L.append("final, %s" % GRP_MAIN)
    return "\n".join(L) + "\n"


# ---------- Shadowrocket ----------
def build_shadowrocket():
    L = []
    L.append("#!MANAGED-CONFIG http://%s:%d/conf interval=43200 strict=false" % (IP, PORT))
    L.append("")
    L.append("[General]")
    L.append("bypass-system = true")
    L.append("skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, "
             "100.64.0.0/10, 17.0.0.0/8, localhost, *.local, captive.apple.com")
    L.append("tun-excluded-routes = 239.255.255.250/32")
    L.append("dns-server = system")
    L.append("ipv6 = false")
    L.append("prefer-ipv6 = false")
    L.append("dns-direct-system = true")
    L.append("icmp-auto-reply = true")
    L.append("always-reject-url-rewrite = false")
    L.append("private-ip-answer = true")
    L.append("dns-direct-fallback-proxy = true")
    L.append("udp-policy-not-supported-behaviour = REJECT")
    L.append("")
    L.append("[Proxy]")
    L.append("%s = vless,%s,443,method=none,uuid=%s,obfs=none,tls13=true,peer=%s,"
             "flow=xtls-rprx-vision,public-key=%s,short-id=%s,fingerprint=chrome"
             % (N1, IP, UUID1, SNI, PBK1, SID1))
    L.append("%s = vless,%s,2053,method=none,uuid=%s,obfs=none,tls13=true,peer=%s,"
             "flow=xtls-rprx-vision,public-key=%s,short-id=%s,fingerprint=chrome"
             % (N2, IP, UUID2, SNI, PBK2, SID2))
    L.append("%s = hysteria2,%s,8443,password=%s,sni=%s,skip-cert-verify=true,"
             "download-bandwidth=200,upload-bandwidth=50" % (N3, IP, HY2PW, SNI))
    L.append("")
    L.append("[Proxy Group]")
    L.append("%s = select, %s, %s, %s, %s, DIRECT" % (GRP_MAIN, N2, N1, GRP_AUTO, N3))
    L.append("%s = select, %s, %s, %s" % (GRP_AI, N2, N3, N1))
    L.append("%s = select, %s, %s, %s, %s" % (GRP_STREAM, N2, N1, N3, GRP_AUTO))
    L.append("%s = url-test, %s, %s, %s, url=http://www.gstatic.com/generate_204, "
             "interval=600, tolerance=100" % (GRP_AUTO, N2, N1, N3))
    L.append("")
    L.append("[Rule]")
    for d in ["localhost", "captive.apple.com"]:
        L.append("DOMAIN-SUFFIX,%s,DIRECT" % d)
    for c in PRIVATE_CIDR:
        L.append("IP-CIDR,%s,DIRECT,no-resolve" % c)
    for d in AI_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,%s" % (d, GRP_AI))
    for d in STREAM_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,%s" % (d, GRP_STREAM))
    for d in FOREIGN_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,%s" % (d, GRP_MAIN))
    for d in APPLE_DIRECT + KAKAO_DIRECT:
        L.append("DOMAIN-SUFFIX,%s,DIRECT" % d)
    for d in CN_DOMAINS:
        L.append("DOMAIN-SUFFIX,%s,DIRECT" % d)
    L.append("GEOIP,KR,DIRECT")
    L.append("GEOIP,CN,DIRECT")
    L.append("FINAL,%s" % GRP_MAIN)
    L.append("")
    L.append("[Host]")
    L.append("localhost = 127.0.0.1")
    return "\n".join(L) + "\n"


# ============================================================
#  UA 自动识别
# ============================================================
# /sub 的自动识别: 只在"订阅类"格式之间切换 (base64 / Clash / sing-box)。
#
# !! 重要 !! 绝不能在 /sub 上返回 MANAGED-CONFIG 这类"配置文件"格式
# (Shadowrocket / Surge / Loon / QuanX)。这些客户端的订阅栏期待的是节点列表,
# 喂给它配置文件会解析失败 -> 节点全部消失。配置文件只走各自固定路径
# (/conf /surge /loon /quanx), 由用户显式选择导入方式。
SUB_UA_MAP = [
    (("clash-verge", "clashmeta", "clash.meta", "clash-meta", "mihomo",
      "clashforandroid", "clashforwindows", "clashx", "stash", "clash"), "clash"),
    (("sing-box", "singbox", "sfi", "sfa", "sfm", "hiddify", "karing"), "singbox"),
]


def detect_format(ua):
    """给 /sub 用。识别不出来 -> base64 节点列表 (兼容性最好, 也是历史行为)"""
    ua = (ua or "").lower()
    for keys, fmt in SUB_UA_MAP:
        for k in keys:
            if k in ua:
                return fmt
    return "base64"


BUILDERS = {
    "base64": (build_base64, "text/plain; charset=utf-8"),
    "plain": (build_plain, "text/plain; charset=utf-8"),
    "clash": (build_clash, "text/yaml; charset=utf-8"),
    "singbox": (build_singbox, "application/json; charset=utf-8"),
    "shadowrocket": (build_shadowrocket, "text/plain; charset=utf-8"),
    "surge": (build_surge, "text/plain; charset=utf-8"),
    "loon": (build_loon, "text/plain; charset=utf-8"),
    "quanx": (build_quanx, "text/plain; charset=utf-8"),
}

# 路径别名 -> 格式
ROUTES = {
    "/base64": "base64", "/v2ray": "base64", "/v2rayn": "base64",
    "/plain": "plain", "/txt": "plain",
    "/clash": "clash", "/meta": "clash", "/mihomo": "clash",
    "/singbox": "singbox", "/sing-box": "singbox", "/hiddify": "singbox",
    "/conf": "shadowrocket", "/shadowrocket": "shadowrocket", "/rocket": "shadowrocket",
    "/surge": "surge",
    "/loon": "loon",
    "/quanx": "quanx", "/qx": "quanx",
}


# ============================================================
#  二维码 (扫码导入单个节点)
# ============================================================
def qr_svg(text):
    try:
        p = subprocess.run(["qrencode", "-t", "SVG", "-m", "2", "-s", "4", "-o", "-"],
                           input=text.encode(), stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=8)
        if p.returncode == 0:
            return p.stdout.decode("utf-8", "replace")
    except Exception:
        pass
    return None


# ============================================================
#  落地页
# ============================================================
def build_index(host):
    base = "http://%s" % host
    rows = [
        ("Clash 系", "Clash Verge / ClashX Meta / Clash for Android / Stash / OpenClash",
         "/clash", "需 Meta(mihomo) 内核，原版 Clash 不支持 VLESS/Reality"),
        ("sing-box 系", "sing-box / SFI / SFA / SFM / Hiddify / Karing",
         "/singbox", "需 sing-box 1.11+"),
        ("Shadowrocket", "小火箭 (iOS)", "/conf", "含完整分流规则，可自动更新"),
        ("通用 base64", "v2rayN / v2rayNG / NekoBox / NekoRay / V2Box / Streisand",
         "/base64", "只有节点，无分流规则"),
        ("Loon", "Loon (iOS)", "/loon", "VLESS 支持取决于版本"),
        ("Quantumult X", "圈X (iOS)", "/quanx", "VLESS 支持取决于版本"),
        ("Surge", "Surge (iOS/macOS)", "/surge",
         "⚠ Surge 不支持 VLESS/Reality，只有 Hysteria2 一个节点可用"),
    ]
    h = []
    h.append("<!doctype html><html lang=zh-CN><head><meta charset=utf-8>")
    h.append("<meta name=viewport content='width=device-width,initial-scale=1'>")
    h.append("<title>订阅导入</title><style>")
    h.append("""
:root{--bg:#0f1115;--fg:#e6e8ec;--mut:#9aa3b2;--card:#171a21;--line:#252a34;--acc:#4c8dff}
*{box-sizing:border-box}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:860px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--mut);font-size:13px;margin-bottom:22px}
.hero{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:22px}
.hero b{color:var(--acc)}
.u{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
code{background:#0b0d11;border:1px solid var(--line);border-radius:7px;padding:7px 10px;
font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:#cfe0ff;word-break:break-all;flex:1;min-width:200px}
button{background:var(--acc);color:#fff;border:0;border-radius:7px;padding:8px 14px;
font-size:13px;cursor:pointer;white-space:nowrap}
button:active{opacity:.7}
table{width:100%;border-collapse:collapse;background:var(--card);
border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{text-align:left;padding:11px 13px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#1c2029;font-size:13px;color:var(--mut);font-weight:600}
tr:last-child td{border-bottom:0}
.nm{font-weight:600;white-space:nowrap}
.app{color:var(--mut);font-size:12.5px}
.note{color:#c9a227;font-size:12px;display:block;margin-top:3px}
a{color:var(--acc);text-decoration:none;font:13px ui-monospace,Menlo,monospace}
h2{font-size:16px;margin:28px 0 10px}
.qr{display:flex;gap:14px;flex-wrap:wrap}
.qrc{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;text-align:center}
.qrc svg{width:150px;height:150px;background:#fff;border-radius:6px;display:block}
.qrc div{font-size:12px;color:var(--mut);margin-top:7px}
.tip{color:var(--mut);font-size:12.5px;margin-top:8px}
""")
    h.append("</style></head><body><div class=wrap>")
    h.append("<h1>订阅导入</h1>")
    h.append("<div class=sub>节点 %s · 共 %d 个</div>" % (IP, len(_uris())))

    h.append("<div class=hero>")
    h.append("<b>通用订阅链接</b><br>")
    h.append("<span class=app>粘到客户端的<b>订阅</b>栏。Clash 系和 sing-box 系会自动"
             "拿到对应格式的完整配置；其余客户端拿到通用 base64 节点列表。</span>")
    h.append("<div class=u><code id=au>%s/sub</code>"
             "<button onclick=\"cp('%s/sub',this)\">复制</button></div>" % (base, base))
    h.append("<div class=tip>Shadowrocket / Surge / Loon / 圈X 想要<b>带分流规则的完整配置</b>，"
             "请用下表里各自的地址，别用这个。</div>")
    h.append("</div>")

    h.append("<h2>按客户端指定格式</h2>")
    h.append("<table><tr><th>客户端</th><th>适用软件</th><th>订阅地址</th></tr>")
    for nm, app, path, note in rows:
        h.append("<tr><td class=nm>%s</td><td class=app>%s%s</td>"
                 "<td><a href='%s'>%s</a><br>"
                 "<button onclick=\"cp('%s%s',this)\">复制</button></td></tr>"
                 % (nm, app,
                    ("<span class=note>%s</span>" % note) if note else "",
                    path, path, base, path))
    h.append("</table>")

    h.append("<h2>扫码导入单个节点</h2>")
    h.append("<div class=qr>")
    names = [N1, N2, N3]
    for i, u in enumerate(_uris()):
        s = qr_svg(u)
        if s:
            s = s[s.find("<svg"):]
            h.append("<div class=qrc>%s<div>%s</div></div>" % (s, names[i]))
    h.append("</div>")
    h.append("<div class=tip>小火箭 / v2rayNG / NekoBox 都支持扫码或从剪贴板导入单个节点。</div>")

    h.append("<script>function cp(t,b){navigator.clipboard.writeText(t).then(()=>{"
             "var o=b.textContent;b.textContent='已复制';setTimeout(()=>b.textContent=o,1200)})}</script>")
    h.append("</div></body></html>")
    return "\n".join(h)


# ============================================================
#  HTTP 服务
# ============================================================
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


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "sub"

    def _send(self, body, ctype="text/plain; charset=utf-8", code=200):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Profile-Update-Interval", "12")
        self.send_header("Subscription-Userinfo", userinfo())
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        ua = self.headers.get("User-Agent", "")

        if path in ("/", "/index.html"):
            return self._send(build_index(self.headers.get("Host", "%s:%d" % (IP, PORT))),
                              "text/html; charset=utf-8")

        if path in ("/sub", "/subscribe"):
            fmt = detect_format(ua)
        elif path in ROUTES:
            fmt = ROUTES[path]
        elif path == "/health":
            return self._send("ok\n")
        else:
            return self._send("404\n", code=404)

        self._rec(path, fmt, ua)
        fn, ctype = BUILDERS[fmt]
        try:
            body = fn()
        except Exception as e:
            return self._send("build error: %r\n" % (e,), code=500)
        self._send(body, ctype)

    def log_message(self, fmt, *args):
        pass

    def _rec(self, path, fmt, ua):
        try:
            with open("/var/log/sub-server.log", "a") as f:
                f.write("%s %s %s -> %s | %s\n" % (
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    self.client_address[0], path, fmt, (ua or "-")[:120]))
        except Exception:
            pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
