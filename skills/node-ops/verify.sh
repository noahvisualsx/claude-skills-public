#!/bin/bash
# node-ops 端到端验证 —— 在目标 VPS 上运行, 用真实客户端跑通每个节点
# 这是唯一能证明节点真能用的测试 (openssl 握手只证明 Reality 在, 不证明能代理)
CFG=/usr/local/etc/node-ops/nodes.json
eval $(python3 -c "
import json;c=json.load(open('$CFG'))
for k in ['ip','uuid1','pbk1','sid1','uuid2','pbk2','sid2','hy2pw','sni']:
    print('%s=%s'%(k.upper(),c[k]))")

mkcli(){ cat > /tmp/nv$4.json <<EOF
{ "inbounds":[{"port":$4,"listen":"127.0.0.1","protocol":"socks","settings":{"udp":true}}],
  "outbounds":[{"protocol":"vless",
    "settings":{"vnext":[{"address":"$IP","port":$1,
      "users":[{"id":"$2","flow":"xtls-rprx-vision","encryption":"none"}]}]},
    "streamSettings":{"network":"tcp","security":"reality",
      "realitySettings":{"serverName":"$SNI","fingerprint":"chrome",
        "publicKey":"$3","shortId":"$5","spiderX":""}}}] }
EOF
}
mkcli 443 "$UUID1" "$PBK1" 10908 "$SID1"
mkcli 2053 "$UUID2" "$PBK2" 10909 "$SID2"
cat > /tmp/nvhy.yaml <<EOF
server: $IP:8443
auth: $HY2PW
tls: { sni: $SNI, insecure: true }
socks5: { listen: 127.0.0.1:10910 }
EOF
xray run -config /tmp/nv10908.json >/dev/null 2>&1 &
xray run -config /tmp/nv10909.json >/dev/null 2>&1 &
hysteria client --config /tmp/nvhy.yaml >/dev/null 2>&1 &
sleep 8

T=https://www.cloudflare.com/cdn-cgi/trace
P=0; F=0
chk(){ # $1=名称 $2=socks端口 $3=url $4=期望关键字
  # 单核小内存机同时跑 3 个测试客户端时偶发抢资源拿到空结果, 失败自动重试 2 次, 避免假故障
  for try in 1 2 3; do
    R=$(curl -s -m 25 --socks5-hostname 127.0.0.1:$2 "$3" 2>/dev/null)
    echo "$R" | grep -q "$4" && break
    sleep 3
  done
  if echo "$R" | grep -q "$4"; then echo "  ✅ $1"; P=$((P+1))
  else echo "  ❌ $1  (拿到: $(echo "$R"|grep -E '^ip=|^warp='|tr '\n' ' '))"; F=$((F+1)); fi
}
echo "===== 端到端验证 ====="
chk "01 直连443  出口=本机IP"      10908 "$T" "ip=$IP"
chk "02 智能分流 普通站=本机IP"     10909 "$T" "ip=$IP"
chk "02 智能分流 AI站=WARP"        10909 "https://claude.ai/cdn-cgi/trace" "warp=on"
chk "03 Hy2      出口=本机IP"      10910 "$T" "ip=$IP"
chk "本地代理1082 =WARP"           40000 "$T" "warp=on"

echo "===== 带宽 (直连 vs WARP, WARP 只该用于 AI) ====="
printf "  直连出口 : "; curl -s -o /dev/null -w "%{speed_download} B/s\n" -m 30 "https://speed.cloudflare.com/__down?bytes=10000000"
printf "  WARP出口 : "; curl -s -o /dev/null -w "%{speed_download} B/s\n" -m 30 --socks5-hostname 127.0.0.1:40000 "https://speed.cloudflare.com/__down?bytes=10000000"

echo "===== 订阅各格式 ====="
for u in "Shadowrocket/2.2:base64" "clash-verge/1.5:clash" "sing-box 1.11:singbox" "curl/8:base64"; do
  ua=${u%:*}; exp=${u#*:}
  curl -s -m 10 -A "$ua" "http://127.0.0.1:2097/sub" -o /tmp/nvsub.txt
  got=$(head -c 200 /tmp/nvsub.txt)
  if   echo "$got" | grep -q "^mixed-port\|^# Clash"; then g=clash
  elif echo "$got" | head -1 | grep -q "^{"; then g=singbox
  elif echo "$got" | grep -q "MANAGED-CONFIG"; then g="配置文件(错!)"
  else g=base64; fi
  [ "$g" = "$exp" ] && { echo "  ✅ $ua -> $g"; P=$((P+1)); } || { echo "  ❌ $ua -> $g (期望 $exp)"; F=$((F+1)); }
done

pkill -f 'nv1090' 2>/dev/null; pkill -f nvhy.yaml 2>/dev/null
rm -f /tmp/nv1090*.json /tmp/nvhy.yaml /tmp/nvsub.txt
echo
echo "===== 通过 $P 项, 失败 $F 项 ====="
[ "$F" -eq 0 ] && echo "全部通过 ✅" || echo "有失败项, 见上 ❌"
