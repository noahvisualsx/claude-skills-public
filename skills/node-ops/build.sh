#!/bin/bash
# node-ops 一键搭建 —— 在目标 VPS 上以 root 运行
#   用法: bash build.sh [节点标签]     例: bash build.sh US
# 全程幂等, 可重复运行。日志 /tmp/node-ops-build.log, 完成后 touch /tmp/node-ops-done
set -o pipefail
exec > >(tee /tmp/node-ops-build.log) 2>&1

TAG="${1:-NODE}"
CFGDIR=/usr/local/etc/node-ops
IP=$(curl -s -m 10 https://api.ipify.org || curl -s -m 10 https://ifconfig.me)
[ -z "$IP" ] && { echo "!! 拿不到公网 IP, 中止"; exit 1; }
echo "===== 目标 $IP  标签 $TAG  $(date -u) ====="

step(){ echo; echo "########## $* ##########"; }

# ---------- 1. swap (小内存机防 OOM) ----------
step "1/10 swap"
MEM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$MEM" -lt 1024 ] && ! swapon --show | grep -q swap; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "已加 1G swap (内存 ${MEM}M)"
else
  echo "跳过 (内存 ${MEM}M, 或已有 swap)"
fi

# ---------- 2. 解除 apt 锁 + 依赖 ----------
step "2/10 依赖"
export DEBIAN_FRONTEND=noninteractive
systemctl disable --now apt-daily.timer apt-daily-upgrade.timer 2>/dev/null
systemctl stop unattended-upgrades 2>/dev/null
pkill -9 -f unattended-upgr; sleep 2; dpkg --configure -a
apt-get update -qq
apt-get install -y -qq curl unzip ufw fail2ban openssl gnupg ca-certificates qrencode python3-yaml

# ---------- 3. Xray ----------
step "3/10 Xray"
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
xray version | head -1

# ---------- 4. 生成密钥 ----------
step "4/10 密钥"
mkdir -p "$CFGDIR"
if [ ! -f "$CFGDIR/nodes.json" ]; then
  U1=$(xray uuid); U2=$(xray uuid)
  K1=$(xray x25519); K2=$(xray x25519)
  P1=$(echo "$K1" | awk '/PrivateKey/{print $2}'); B1=$(echo "$K1" | awk '/Password|PublicKey/{print $NF}' | head -1)
  P2=$(echo "$K2" | awk '/PrivateKey/{print $2}'); B2=$(echo "$K2" | awk '/Password|PublicKey/{print $NF}' | head -1)
  S1=$(openssl rand -hex 8); S2=$(openssl rand -hex 8); HP=$(openssl rand -hex 8)
  cat > "$CFGDIR/nodes.json" <<EOF
{
  "ip": "$IP", "port": 2097, "tag": "$TAG", "sni": "www.apple.com",
  "uuid1": "$U1", "priv1": "$P1", "pbk1": "$B1", "sid1": "$S1",
  "uuid2": "$U2", "priv2": "$P2", "pbk2": "$B2", "sid2": "$S2",
  "hy2pw": "$HP"
}
EOF
  chmod 600 "$CFGDIR/nodes.json"
  echo "已生成新密钥"
else
  echo "复用已有 $CFGDIR/nodes.json"
fi
python3 -c "import json;d=json.load(open('$CFGDIR/nodes.json'));print('  UUID1',d['uuid1']);print('  UUID2',d['uuid2'])"

# ---------- 5. Xray 配置 (关键: 只有 AI 域名走 WARP) ----------
step "5/10 Xray 配置"
python3 - <<'PY'
import json
c = json.load(open("/usr/local/etc/node-ops/nodes.json"))
AI = ["openai.com","chatgpt.com","oaistatic.com","oaiusercontent.com","sora.com",
      "anthropic.com","claude.ai","claudeusercontent.com","perplexity.ai","x.ai",
      "grok.com","poe.com","midjourney.com","cursor.sh","githubcopilot.com",
      "copilot.microsoft.com","stripe.com"]
# 注意: Gemini/Bard/generativelanguage/deepmind 故意不在此列表。
# WARP 出口被 Google 判定为 RU(Gemini 在俄罗斯不可用), 直连出口反而判定为 US。
# 走 WARP 会导致 "Gemini 不支持你所在的地区", 必须让它们走 direct。
def inb(tag, port, uuid, priv, sid):
    return {"tag":tag,"listen":"0.0.0.0","port":port,"protocol":"vless",
      "settings":{"clients":[{"id":uuid,"flow":"xtls-rprx-vision"}],"decryption":"none"},
      "streamSettings":{"network":"tcp","security":"reality",
        "realitySettings":{"dest":c["sni"]+":443","serverNames":[c["sni"]],
          "privateKey":priv,"shortIds":[sid]}},
      "sniffing":{"enabled":True,"destOverride":["http","tls","quic"]}}
cfg = {
 "log":{"loglevel":"warning","access":"/var/log/xray/access.log","error":"/var/log/xray/error.log"},
 "inbounds":[inb("reality-direct",443,c["uuid1"],c["priv1"],c["sid1"]),
             inb("reality-warp",2053,c["uuid2"],c["priv2"],c["sid2"]),
             {"tag":"http-local","listen":"127.0.0.1","port":1082,"protocol":"http","settings":{}}],
 "outbounds":[{"tag":"direct","protocol":"freedom","settings":{"domainStrategy":"UseIP"}},
              {"tag":"warp","protocol":"socks","settings":{"servers":[{"address":"127.0.0.1","port":40000}]}},
              {"tag":"block","protocol":"blackhole"}],
 "routing":{"domainStrategy":"IPIfNonMatch","rules":[
   {"type":"field","inboundTag":["http-local"],"outboundTag":"warp"},
   {"type":"field","inboundTag":["reality-warp"],
    "domain":["domain:"+d for d in AI],"outboundTag":"warp"},
   {"type":"field","inboundTag":["reality-warp"],"outboundTag":"direct"}]}}
json.dump(cfg, open("/usr/local/etc/xray/config.json","w"), indent=2)
print("  写入完成, AI 域名 %d 个走 WARP, 其余 direct" % len(AI))
PY
xray run -test -config /usr/local/etc/xray/config.json | tail -1
systemctl restart xray

# ---------- 6. WARP ----------
step "6/10 Cloudflare WARP"
if ! command -v warp-cli >/dev/null; then
  CODENAME=$(. /etc/os-release; echo "$VERSION_CODENAME")
  echo "  系统 codename: $CODENAME"
  curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $CODENAME main" > /etc/apt/sources.list.d/cloudflare-client.list
  apt-get update -qq && apt-get install -y cloudflare-warp
fi
systemctl enable --now warp-svc; sleep 8
warp-cli --accept-tos registration new 2>/dev/null
sleep 3
warp-cli --accept-tos mode proxy
warp-cli --accept-tos proxy port 40000
warp-cli --accept-tos connect
for i in $(seq 1 12); do sleep 5; warp-cli --accept-tos status 2>&1 | grep -q Connected && break; done
warp-cli --accept-tos status | head -1
curl -s -m 15 --socks5 127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace | grep -E "^warp=|^ip=" || echo "  !! WARP SOCKS 不通"
( crontab -l 2>/dev/null | grep -v 'restart warp-svc'; echo '0 5 * * * systemctl restart warp-svc' ) | crontab -

# ---------- 7. Hysteria2 ----------
step "7/10 Hysteria2"
command -v hysteria >/dev/null || bash <(curl -fsSL https://get.hy2.sh/)
[ -f /etc/hysteria/server.crt ] || openssl req -x509 -nodes -newkey ec \
  -pkeyopt ec_paramgen_curve:prime256v1 -keyout /etc/hysteria/server.key \
  -out /etc/hysteria/server.crt -subj "/CN=www.apple.com" -days 3650
HP=$(python3 -c "import json;print(json.load(open('$CFGDIR/nodes.json'))['hy2pw'])")
cat > /etc/hysteria/config.yaml <<EOF
listen: :8443
tls: { cert: /etc/hysteria/server.crt, key: /etc/hysteria/server.key }
auth: { type: password, password: $HP }
masquerade: { type: proxy, proxy: { url: https://www.apple.com/, rewriteHost: true } }
quic: { initStreamReceiveWindow: 8388608, maxStreamReceiveWindow: 8388608, initConnReceiveWindow: 20971520, maxConnReceiveWindow: 20971520 }
EOF
chown -R hysteria:hysteria /etc/hysteria 2>/dev/null
systemctl enable --now hysteria-server; systemctl restart hysteria-server

# ---------- 8. 订阅服务器 ----------
step "8/10 订阅服务器"
if [ -f /tmp/sub-server.py ]; then install -m 755 /tmp/sub-server.py /usr/local/bin/sub-server.py; fi
python3 -c "import ast; ast.parse(open('/usr/local/bin/sub-server.py').read())" && echo "  语法 OK"
cat > /etc/systemd/system/sub-server.service <<'EOF'
[Unit]
Description=Subscription Server
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/sub-server.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
# 注意: logrotate 指令必须一行一个, 写成单行 {...} 会报 bad weekly directive, 导致整个 logrotate.service 每天失败
cat > /etc/logrotate.d/sub-server <<'EOF'
/var/log/sub-server.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    copytruncate
}
EOF
# xray 日志必须轮转, 否则 access.log 无限增长 (实测 ~2MB/天)。
# 必须用 copytruncate: xray 不支持信号重开日志, 用 create 会导致轮转后写入旧 inode, 新文件永远为空。
cat > /etc/logrotate.d/xray <<'EOF'
/var/log/xray/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
systemctl daemon-reload && systemctl enable --now sub-server && systemctl restart sub-server

# ---------- 9. 内核调优 (BBR) ----------
step "9/10 BBR + 缓冲区"
modprobe tcp_bbr 2>/dev/null; echo tcp_bbr > /etc/modules-load.d/bbr.conf
cat > /etc/sysctl.d/99-net-tune.conf <<'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_fastopen = 3
net.core.somaxconn = 8192
net.ipv4.tcp_max_syn_backlog = 8192
net.core.rmem_default = 2621440
net.core.wmem_default = 2621440
EOF
sysctl -p /etc/sysctl.d/99-net-tune.conf >/dev/null
echo "  拥塞控制: $(sysctl -n net.ipv4.tcp_congestion_control) / qdisc: $(sysctl -n net.core.default_qdisc)"

# ---------- 10. 防火墙 ----------
step "10/10 ufw"
ufw allow 22/tcp >/dev/null; ufw allow 443/tcp >/dev/null; ufw allow 2053/tcp >/dev/null
ufw allow 2097/tcp >/dev/null; ufw allow 8443/udp >/dev/null
ufw --force enable >/dev/null; ufw status | head -8

step "11/11 SSH 加固 (只允许密钥) + fail2ban 白名单"
if [ -s /root/.ssh/authorized_keys ]; then
  # 00- 前缀: 必须先于 cloud-init 的 50-cloud-init.conf 被读到 (sshd 取第一次出现的值, 后者常写 PasswordAuthentication yes)
  printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin prohibit-password\n' > /etc/ssh/sshd_config.d/00-hardening.conf
  sshd -t && { systemctl reload ssh 2>/dev/null || systemctl reload sshd; }
  echo "  $(sshd -T | grep -E '^passwordauthentication ')"
else
  echo "  !! authorized_keys 为空, 跳过关闭密码登录 (否则会把自己锁在外面)"
fi
MYIP=$(echo "$SSH_CLIENT" | awk '{print $1}')
cat > /etc/fail2ban/jail.d/zz-node-ops.conf <<EOF
[DEFAULT]
# 管理连接可能经自家节点出口过来, 永不封禁
ignoreip = 127.0.0.1/8 ::1 $IP ${MYIP}
bantime = 1h
findtime = 10m
maxretry = 5
bantime.increment = true
[sshd]
enabled = true
EOF
systemctl restart fail2ban

step "完成"
for s in xray warp-svc hysteria-server sub-server; do printf "  %-18s %s\n" "$s" "$(systemctl is-active $s)"; done
echo
echo "  落地页  http://$IP:2097/"
echo "  订阅    http://$IP:2097/sub"
echo "  小火箭  http://$IP:2097/conf"
echo
echo "  !! 还没验证能不能真代理, 必须跑 verify.sh !!"
touch /tmp/node-ops-done
