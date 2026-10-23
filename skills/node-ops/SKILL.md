---
name: node-ops
description: 自建代理 VPS 节点的搭建、巡检、排查、订阅运维（Xray VLESS-Reality + Cloudflare WARP 解锁 + Hysteria2 + 多格式订阅服务器）。当用户"给一个 IP 和 root 密码"要求搭节点、或说"搭建/新建节点""检查/巡检节点""节点连不上/超时/很慢/用不了""换 IP/重装后重建""加/删节点""订阅导入失败/客户端没节点""订阅迁移到另一台机器"时使用。
---

# node-ops：自建代理节点运维手册

自包含运维能力：**搭建**（新机器从零建整套，约 10 分钟）、**巡检**、**排查**、**订阅运维**。

## 触发即执行：用户只给 IP + 密码

用户发来 `IP + root密码` 就是要搭节点，**不用再问要什么协议/端口**，直接按 §2 全自动流程走完，最后把订阅地址和密钥交给用户。唯一需要确认的是：如果机器上**已有正在运行的服务**（`ss -tlnp` 看到 443/2053 被占、或已有 xray），先问清楚是重建还是共存，别直接覆盖。

配套技术栈（每台机器一套）：
- **Xray VLESS + Reality**（XTLS Vision）— 443/TCP 全程直连；2053/TCP **仅 AI 域名走 WARP，其余直连**
- **Cloudflare WARP** — `warp-svc` proxy 模式，socks5 在 `127.0.0.1:40000`，给 AI 站提供住宅级出口
- **Hysteria2** — 8443/UDP，自签证书伪装 www.apple.com，抗丢包
- **本地 HTTP 代理** — Xray http 入站 `127.0.0.1:1082` → WARP（给本机应用/机器人用）
- **多格式订阅服务器** — 2097，8 种格式 + UA 自动识别 + 落地页/二维码
- **BBR + fq** 内核调优、**ufw** 防火墙、WARP 每日重启 cron

配套脚本（与本文件同目录，用 `base64 | ssh` 传到目标机执行）：
- `build.sh` — 一键搭建，幂等可重跑
- `verify.sh` — 端到端验证（**搭完必跑**）
- `inspect.sh` — 巡检
- `sub-server.py` — 订阅服务器（读 `/usr/local/etc/node-ops/nodes.json`，跨机器复用不改代码）

---

## 0. 连接与访问

密钥优先：`ssh -i ~/.ssh/jp_vps -o IdentitiesOnly=yes root@<IP>`。新机器先用密码把公钥推上去（macOS 无 sshpass，用 `expect`）：

```bash
ssh-keygen -t ecdsa -b 256 -f ~/.ssh/jp_vps -N "" -C "claude-access"   # 没有就现生成
```
```expect
#!/usr/bin/expect -f
set timeout 40
spawn ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no root@[lindex $argv 0] \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '[lindex $argv 2]' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo KEY_PUSHED_OK"
expect { -re "(P|p)assword:" { send "[lindex $argv 1]\r"; exp_continue }
         "KEY_PUSHED_OK" {} timeout { exit 1 } eof {} }
expect eof
```

之后包一个 `vps` 脚本反复用：
```bash
#!/bin/bash
exec ssh -i ~/.ssh/jp_vps -o IdentitiesOnly=yes -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=15 \
  -o ServerAliveInterval=15 root@<IP> "$@"
```

### SSH 老毛病（都不是真故障）
- `Connection lost before handshake` / banner timeout / **exit 255** → **重试即可**，5-10s 内成功。别当故障排查。
- 重装后主机密钥变 → 先 `ssh-keygen -R <IP>`。
- 密码登录被 cloud-init 关 → VNC 里 `sed -i 's/^PasswordAuthentication no/yes/' /etc/ssh/sshd_config.d/*.conf && systemctl restart ssh`。
- VNC "发送文本"：>70 字符会截断，拆短；**Caps Lock 会把命令变全大写**。
- 怀疑被 fail2ban 封先查 `fail2ban-client status sshd` 再下结论（多半封的是扫描 IP，不是你）。

---

## 1. 传文件与远程执行的坑（血泪，务必遵守）

- **scp 不稳** → 一律 `base64 -i 本地文件 | vps 'base64 -d > /远程路径'`。
- **`&` 会把整条命令链都后台化**：`vps 'A && B && nohup C & echo LAUNCHED'` 里 A/B 也进了后台，ssh 一退就死，脚本根本没跑。
  → **上传和启动必须分成两次 ssh 调用**，上传那次确认输出再启动。
- **`pkill -f "关键字"` 会杀掉自己**：ssh 执行的 `bash -c '<整段脚本>'` 命令行里含该关键字，pkill 把自己干掉 → **exit 255**，看着像 SSH 断了。
  → 用 `pgrep -f xxx | xargs -r kill`，或把关键字拆开写 `"c""li1080"`。
- 长命令跑一半 ssh 断但**命令仍在后台跑** → 用 `setsid nohup` + poll `/tmp/*-done` 哨兵文件。
- **写 Python 文件别用 sed/正则改字符串**（`\n` 转义极易搞坏）→ 整份覆盖重写，写完 `python3 -c "import ast; ast.parse(open('文件').read())"` 验语法。
- 单核小内存机上**别并发跑多个 xray 客户端 + 测速**，会互相抢资源测出 `0 B/s` 的假故障；一个一个测。

---

## 2. 搭建（全自动）

```bash
# 1) 推公钥 (见 §0)
# 2) 传脚本 —— 上传和启动分开两次调用!
base64 -i sub-server.py | vps 'base64 -d > /tmp/sub-server.py'
base64 -i build.sh      | vps 'base64 -d > /tmp/build.sh && chmod +x /tmp/build.sh && echo UPLOADED'
# 3) 后台跑 (约 10 分钟), 然后 poll 哨兵
vps 'rm -f /tmp/node-ops-done; setsid nohup bash /tmp/build.sh US </dev/null >/dev/null 2>&1 & sleep 3; echo LAUNCHED'
# poll: test -f /tmp/node-ops-done
# 4) 验证 —— 必做
base64 -i verify.sh | vps 'base64 -d > /tmp/verify.sh'
vps 'bash /tmp/verify.sh'
```

`build.sh` 顺序：swap → 解 apt 锁 → 依赖 → Xray → 生成密钥到 `nodes.json` → Xray 配置 → WARP → Hysteria2 → 订阅服务器 → BBR → ufw。**幂等**，已有 `nodes.json` 就复用密钥不重新生成。

密钥材料落在目标机 `/usr/local/etc/node-ops/nodes.json`（600）。**同时必须拉回本地存一份**（`~/Downloads/<IP>_keys.txt`，scratchpad 会随会话清理）。重装即失，别信记忆里的旧值；pbk 拿不准永远 `xray x25519 -i <私钥>` 现推。

### 搭完必须做的事
1. 跑 `verify.sh`，**每一项都要 ✅**。openssl 握手成功只证明 Reality 在，不证明能代理。
2. 把订阅地址 + 密钥文件位置交给用户，并说明**哪个节点是主力**（`-02-智能分流`）。
3. 写进本地记忆 `vps-proxy-nodes.md`。

---

## 3. 关键设计决策（都是踩坑换来的，别改回去）

### 3.1 ⚠ WARP 只能解锁 AI，绝不能扛流量
实测同一台机器：**直连出口 65–90 MB/s，WARP 出口 0.42–0.54 MB/s，差 150 倍。**

> **⚠ 2026-09-12 更正：这个"WARP 一定慢"的结论只对那台 LAX 机器成立，不是通例。**
> 同样是 MASQUE 协议，SJC 那台（164.92.93.79）实测 WARP 出口 **44-46 MB/s**，比 LAX 的 0.5MB/s 快约 90 倍。
> 所以慢的根源是**那台机器所在网络到 Cloudflare 边缘的链路**，不是 MASQUE 协议本身。
> **新机器必须实测再下结论**，别照搬"WARP 很慢"的假设（`verify.sh` 已经会打印两个出口的带宽对比）。

LAX 那台上试过 `warp-cli tunnel protocol set WireGuard` → **完全连不上**（机房挡 WireGuard UDP 端点），只能 `set MASQUE` + `systemctl restart warp-svc` 回滚。

**但「AI-only 走 WARP」这个设计依然要保持**，理由与带宽无关：WARP 出口是共享 IP，**地区判定会漂移**（见 §3.4b，同一 IP 昨天判 RU 今天判 US），普通流量挂在上面等于把稳定性交给运气。

**因此 2053 入站绝不能整个路由到 WARP**，必须按域名分流：
```json
{"type":"field","inboundTag":["reality-warp"],"domain":["domain:openai.com", ...],"outboundTag":"warp"},
{"type":"field","inboundTag":["reality-warp"],"outboundTag":"direct"}
```
> 曾经把整个入站丢给 WARP，用户拿它当主节点，**全部流量被卡在 0.5MB/s**。access.log 里 `[reality-warp -> warp]` 占了 346/349 条就是这个症状。改成 AI-only 后普通站 54 MB/s。

### 3.2 ⚠ `/sub` 绝不能返回"配置文件"格式
`/sub` 只能返回**订阅类**格式：base64 节点列表 / Clash YAML / sing-box JSON。

**Shadowrocket / Surge / Loon / 圈X 的订阅栏期待节点列表**，喂给它 `#!MANAGED-CONFIG` 配置文件会解析失败 → **节点全部消失**。配置文件只走各自固定路径 `/conf` `/surge` `/loon` `/quanx`，由用户显式选择。
> 曾经把 UA 识别做到了配置文件格式上，用户一刷新订阅节点就全没了。

### 3.3 BBR 必开
新机器默认 `cubic`。美中链路 RTT 200ms+ 且有丢包，cubic 表现远差于 BBR。`build.sh` 已含 `/etc/sysctl.d/99-net-tune.conf`（BBR + fq + 大缓冲区 + `tcp_mtu_probing`）。

### 3.4 地区锁服务必须 DIRECT（不止 Apple）
`apple.com` `icloud.com` `mzstatic.com` `aaplimg.com` 等走代理会触发地区不符，Apple Music 直接用不了。

**同一类问题不止 Apple 一家**：2026-08-31 实测 `katalk.kakao.com` 走代理后 **575 次重复连接失败**（access.log 里同一域名反复出现就是信号，正常应用不会对同一 host 建这么多次连接）。服务器本身到 Kakao 是通的（`www.kakao.com` HTTP 302），说明不是网络不通，是**从美国 IP 访问触发了地区锁**，逻辑和 Apple Music 完全一样。已加 `KAKAO_DIRECT` 列表（`kakao.com` `kakaocdn.net` `kakaopay.com` `daum.net` 等）到所有格式的规则集。

**排查这类问题的通用方法**：`grep -ic "<服务名>" access.log` 看有没有异常多的重复连接 → 服务器 `curl -s -o /dev/null -w "%{http_code}"` 测该服务的域名，通就说明不是网络问题 → 域名加进对应的 DIRECT 列表。

**加白名单时要检查是否与其他规则冲突**：韩国/日本系服务里 `naver.com` `line.me` `melon.com` 在国内本身被墙，**不能**跟着 Kakao 一起改 DIRECT（会让它们从能通过代理用变成彻底不可用）；`line.me` 还已经在 `FOREIGN_DOMAINS`（→走代理）里，两条规则会冲突。改名单前用脚本跑一遍交集检查：
```python
set(NEW_LIST) & (set(FOREIGN_DOMAINS)|set(STREAM_DOMAINS)|set(AI_DOMAINS)|set(CN_DOMAINS))
```

**⚠ 域名 DIRECT 规则加了还是不生效, 先排除这两个原因再怀疑规则本身写错**（2026-09-03 实测 Kakao 案例）：

1. **客户端在"全局/Global"模式，根本不读规则表。** 判断方法：挑一个**早就配了 DIRECT 且理论上肯定生效**的域名（比如 `apple-relay.apple.com`）去 access.log 里查，如果它也在走隧道 `[reality-warp -> xxx]`，说明是客户端全局模式的问题，不是这条新规则本身的问题——**换哪个域名都没用，因为规则整体没被读取**。这一步能几分钟内把"规则写错"和"客户端模式不对"两种可能分开，不用来回改配置瞎试。此问题只能用户自己在客户端里把模式从「全局」切到「规则」，服务端/订阅配置什么都改不了。
2. **协议本身走的是裸 IP，没有域名可匹配。** 有些 App（典型是 KakaoTalk 的 LOCO 协议）先用域名做一次"打票"请求，后续真正的数据连接直接连一个裸 IP、无 TLS SNI（access.log 里会看到 `tcp:121.53.xxx.xxx:995` 这种没有域名的记录，往往伴随非常规端口如 995/8080）。这种连接 DOMAIN-SUFFIX 规则天生抓不到，**必须加 `GEOIP,KR,DIRECT`（或对应国家码）兜底**，放在 `GEOIP,CN,DIRECT` 之前。sing-box 对应加 `geoip-kr` 远程规则集（`https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/geoip-kr.srs`，用前 `curl -I` 确认 200 再接，域名不存在会导致客户端拉规则集失败）。

### 3.4b ⚠ WARP 出口被 Google 判定为 RU —— Gemini 绝不能走 WARP

2026-09-09 实测（同一台机器，结果稳定复现）：

| 出口 | IP | Google 产品级判定 `gl` |
|---|---|---|
| 直连 | 23.224.152.83 | **US** ✅ |
| WARP | 104.28.195.192 | **RU** ❌ |

Gemini 在俄罗斯不提供服务，所以只要 Gemini 走 WARP，就会显示「Gemini 目前不支持你所在的地区」。
**把 Gemini 放进 AI-WARP 名单是帮倒忙** —— 它和 OpenAI/Anthropic 不一样，直连的数据中心 IP 反而是被认作美国的正常出口。

因此 `gemini.google.com` / `bard.google.com` / `generativelanguage.googleapis.com` / `deepmind.com`
**必须排除在 WARP 名单之外**（服务端 xray routing + 客户端 AI 组都要排除），
让它们由 `google.com` / `googleapis.com` 规则兜底走直连出口。ChatGPT/Claude 等仍留在 WARP 名单里，不受影响。

**测 Google 产品级国家判定的方法**（关键工具，别用错接口）：
```bash
curl -s -A "<浏览器UA>" https://www.youtube.com/ | grep -oE '"GL":"[A-Z]{2}"' | head -1
```
- ✅ YouTube 页面里的 `"GL"` 字段 = Google **产品级**地区判定，Gemini/YouTube 等的可用性按它算。
- ❌ **别用 `redirector.gvt1.com/report_mapping`** —— 那是 **CDN 边缘路由**（按网络拓扑/延迟选机房），
  本次它把 WARP 出口映射到 `sfo03s28`（旧金山），看着像美国，**但产品判定其实是 RU**，会把人带偏。
  两套系统结论可以完全相反，排查地区问题只认 `GL`。

**地区类问题的通用分诊**（比反复改配置快得多）：
1. 报错文案是「不支持你所在的地区」这类**明确的地区提示** → 是产品地区判定，不是网络故障，别去查丢包/延迟。
2. 用上面的 `GL` 方法逐个出口测，找出哪个出口的判定是坏的。
3. 服务器上匿名 `curl` 拿到的 HTML **可能完全正常**（本次两个出口都是 HTTP 200、843KB、无拦截文案），
   因为地区拦截是登录后由 JS 渲染的 —— **HTML 干净不能证明没被地区限制**，必须用 `GL` 字段判断。

### 3.5 `FINAL` 前必须有 `GEOIP,CN,DIRECT`
否则国内长尾网站全走代理，又慢又坏。

### 3.6 DNS 永远 `system`
绝不用国内 DNS（223.5.5.5 之类），会把国外域名污染解析成国内 IP。

---

## 4. 订阅服务器（8 格式 + UA 自动识别）

| 路径 | 格式 | 客户端 |
|---|---|---|
| `/` | HTML 落地页 | 复制按钮 + 三个节点二维码（需 `qrencode`） |
| `/sub` | **按 UA 自动** | Clash系→YAML，sing-box系→JSON，**其余→base64** |
| `/clash` `/meta` `/mihomo` | Clash YAML | Clash Verge / ClashX Meta / Stash / OpenClash |
| `/singbox` `/hiddify` | sing-box JSON | sing-box / SFI/SFA/SFM / Hiddify / Karing |
| `/conf` `/shadowrocket` | MANAGED-CONFIG | 小火箭 |
| `/base64` `/plain` | 节点列表 | v2rayN / v2rayNG / NekoBox / V2Box |
| `/surge` `/loon` `/quanx` | 各自配置 | Surge / Loon / 圈X |

**客户端支持度的硬限制（要主动告知用户）**：
- **Surge 不支持 VLESS/Reality** → `/surge` 里只有 Hysteria2 一个节点，且需 Surge 5.8+。
- **原版 Clash 不支持 VLESS/Reality/Hy2** → 必须 Meta(mihomo) 内核。
- **Loon / 圈X 的 VLESS 支持随版本变化**，没真机验证过，连不上就退回 `/base64` 或扫码。
- 明文 HTTP 无鉴权 → **国内直连拉订阅常被 GFW 重置**，让用户先连上一个能用的节点再刷订阅。

改配置后：`systemctl restart sub-server`。请求日志 `/var/log/sub-server.log`（时间/来源IP/路径/返回格式/UA）——**用户说"订阅有问题"先看这个**，能直接看出客户端拿到了什么。

---

## 5. 排查

### 5.1 先分类：是服务端、线路、还是客户端配置
```bash
bash inspect.sh          # 服务/端口/WARP/资源/最近活动 一把梭
tail -20 /var/log/xray/access.log        # 有没有该用户的连接? 走的哪个 outbound?
tail -20 /var/log/sub-server.log         # 客户端拉订阅拿到了什么格式?
```
**access.log 的最后一条时间是金线索**：如果流量在某个时刻突然停止，看那一刻发生了什么（尤其 `accepted tcp:<本机IP>:2097` = 用户刚刷新过订阅 → 大概率是订阅/配置问题，不是节点挂了）。

### 5.2 连不上：判断连接有没有到达 + 握手有没有完成
让用户在客户端点测延迟，同时服务器抓包：
```bash
timeout 45 tcpdump -i any -n "tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0 and (dst port 443 or dst port 2053)"
timeout 35 tcpdump -i any -n host <客户端IP>
```
1. **完全没 SYN** → **GFW 封了 IP**。旁证：服务器 ping 国内丢包、境外测 IP 通但国内超时。处理：换 IP（治本）/ CDN 中转（治标）。
2. **SYN 进来但客户端重发** → 回程 SYN-ACK 被丢，**线路丢包**。处理：推 Hy2(UDP)、换网络类型。
3. **有 SYN + access.log 有记录 + 数据双向流动** → 节点在工作，"慢"是线路质量问题。

### 5.3 "慢"的排查顺序
```bash
curl -s -o /dev/null -w "直连 %{speed_download} B/s\n" -m 30 "https://speed.cloudflare.com/__down?bytes=10000000"
curl -s -o /dev/null -w "WARP %{speed_download} B/s\n" -m 30 --socks5-hostname 127.0.0.1:40000 "https://speed.cloudflare.com/__down?bytes=10000000"
ping -c 10 -q baidu.com; ping -c 10 -q taobao.com     # 服务端到国内: 看延迟和丢包
sysctl -n net.ipv4.tcp_congestion_control              # 是不是还在 cubic
grep -c 'reality-warp -> warp' /var/log/xray/access.log  # 是不是全被塞进 WARP 了
```
- **裸带宽正常但用户慢** → 十有八九是流量走了 WARP（见 §3.1），或用户选错节点。
- **服务器 ping 国内 0 丢包、延迟正常** → 问题在用户 ISP 国际路由，服务端改不了。远距离节点（美国 230ms）对国内本来就慢，优先推 Hy2。
- `ping qq.com` 100% 丢包是腾讯挡 ICMP，**不是故障**，别误判。

### 5.4 分流类问题
- **"开代理 XXX 用不了，关了才行"**（Apple Music/网易云/B站）→ 地区锁服务被路由到代理。该域名改 DIRECT。
- **国内长尾站慢/坏** → `FINAL` 前加 `GEOIP,CN,DIRECT`。
- **`/conf` 卡、只有"选代理"才通** → DNS 污染，`dns-server = system`。
- **机器人报 `ECONNREFUSED 127.0.0.1:1082`** → Xray 缺 http 入站，按 §3 加 `http-local` → warp。
- **AI 站登录报错** → 该域名要走 WARP 出口（用 `-02` 节点）。用 curl 测 AI 站返回 403 **不代表被封**：那是 Cloudflare 拦 curl；测 `api.openai.com` 返回 401 就说明网络路径通（只是没 API key）。

---

## 6. 坑速查表

| 症状 | 根因 | 处理 |
|------|------|------|
| 一切正常但用户就是慢 | 流量全走了 WARP 出口(0.5MB/s) | 2053 改 AI-only 分流 §3.1 |
| 刷新订阅后节点全没了 | `/sub` 返回了配置文件格式 | `/sub` 只给订阅类格式 §3.2 |
| 节点全红、抓包无 SYN | GFW 封 IP | 换 IP / CDN 中转 |
| SYN 进来但重发、大量 SACK | 线路丢包(中美/移动网) | 用 Hy2(UDP)、换网络 |
| 长距离节点延迟高 | 物理距离, 非配置问题 | 服务端改不了, 推 Hy2 |
| 开代理某 App 用不了(Apple Music/KakaoTalk等) | 地区锁服务走了代理, access.log 同域名反复重连 | 该域名加进 DIRECT 列表, 先查有无冲突 |
| 国内长尾站慢/坏 | FINAL 兜底把全部走代理 | FINAL 前加 GEOIP,CN,DIRECT |
| AI 站登录报错 | 数据中心 IP 被拦 | 走 WARP 出口节点 |
| Gemini 提示"不支持你所在的地区" | WARP 出口被 Google 判定为 RU | Gemini 系移出 WARP 名单走直连 §3.4b |
| Surge 里只有一个节点 | Surge 不支持 VLESS/Reality | 正常, 只能用 Hy2 |
| Clash 导入后节点全废 | 用了原版 Clash 内核 | 换 Meta(mihomo) 内核 |
| Hy2 握手失败 | 客户端没跳过自签证书校验 | `skip-cert-verify=true` / `insecure=1` |
| 机器人 ECONNREFUSED 1082 | 缺本地 http 代理 | Xray 加 http 入站→WARP |
| 改了 PasswordAuthentication no 仍能密码登录 | cloud-init 的 `50-cloud-init.conf` 写了 yes，sshd 取**第一次出现**的值 | 加固配置放 `00-hardening.conf`；改完用 `sshd -T` 看生效值 |
| 开 fail2ban 后自己连不上服务器 | 从 Mac 连服务器时流量走代理，**来源 IP 是自家节点 IP**，输错几次就被封 | `ignoreip` 加入所有节点 IP |
| 关密码登录前的检查 | 没确认密钥能登就关 = 锁死 | 先确认 `authorized_keys` 有自己的公钥并实测密钥登录；DO 机器还能走网页控制台兜底 |
| apt install 报 lock/exit100 | unattended-upgrades 抢锁 | 停 apt-daily 定时器 + 杀进程 |
| WARP 装不上/找不到包 | apt 源 codename 错 | 用 `. /etc/os-release; $VERSION_CODENAME` |
| WARP 切 WireGuard 后连不上 | 机房挡 WG UDP 端点 | `set MASQUE` + 重启 warp-svc |
| 小内存机 OOM/卡 | 内存不足 | 先加 1G swap |
| ssh 命令 exit 255 | pkill 杀了自己 / SSH 抽风 | 用 pgrep\|xargs kill；重试 |
| 后台脚本没跑起来 | `&` 把整条链后台化了 | 上传与启动分两次 ssh |
| 测速测出 0 B/s / verify 某项拿到空结果 | 单核机并发抢资源（verify 同时起 3 个客户端） | 单独重测该项再下结论；verify.sh 已内置失败重试 2 次 |
| xray 日志无限增长 | 缺 logrotate | 加 `/etc/logrotate.d/xray`，**必须 copytruncate**（xray 不支持信号重开日志，用 create 会让新文件永远为空） |
| `systemctl --failed` 里 logrotate.service 每天失败 | logrotate 配置写成单行 `{ weekly rotate 4 ... }`，报 `bad weekly directive`，**整个 logrotate 停摆**（所有日志都不轮转） | 指令一行一个；巡检时看 `systemctl --failed`，改完 `systemctl start logrotate` 验证（2026-09-22 SJC 踩到，build.sh 已修） |

---

## 7. 订阅迁移（托管机要过期时）

1. 目标机装好 `sub-server.py` + systemd + `ufw allow 2097/tcp`，`nodes.json` 里填目标机 IP。
2. **改 `/conf` 里 MANAGED-CONFIG 自更新地址**指向新机器（`nodes.json` 的 `ip` 改掉即可），否则旧机一挂自动刷新就断。
3. 要过期的机器的节点从节点列表删掉。
4. 用户端**必须删旧订阅、加新订阅 URL**（光刷新没用）。
5. 提醒用户：过期机器上若还托管别的服务（机器人等）会一起停。

---

## 8. 已知短板（想彻底解决要额外条件）

- **全部节点绑在一个裸 IP 上**：IP 被 GFW 封 → 三个节点同时死。补法是加一条 **VLESS + WS + TLS 走 Cloudflare CDN** 的节点（客户端连 CF 的 IP，源站 IP 不暴露），**需要用户有域名托管在 Cloudflare**。定位是保险不是主力，绕一层明显更慢。CF 支持的回源 HTTPS 端口：443 / 2053 / 2083 / 2087 / 2096 / 8443（**TCP 8443 是空的**，Hy2 只占 UDP 8443）。注意 zone 级 SSL 模式是全域共享的，域名上有别的站要先问清楚。
- **Hy2 固定单端口易被 QoS**：可开端口跳跃（UDP 端口段随机跳）缓解。
- **协议选型本身没有升级空间**：VLESS+Reality 是 TCP 类最优（VMess 老旧、Trojan 有 TLS-in-TLS 特征、SS2022 无伪装、NaiveProxy 要域名证书收益不明显）；Hysteria2 是 QUIC 类最优（比 TUIC v5 维护活跃）。别折腾换协议，要提升就补上面两条。

---

## 当前拓扑
存活节点、密钥、IP 见本地记忆 `vps-proxy-nodes.md` 和 `~/Downloads/<IP>_keys.txt`。订阅托管在哪台机器随过期迁移，`/conf` 头部 MANAGED-CONFIG 地址就是当前托管机。
