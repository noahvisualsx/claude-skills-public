#!/bin/bash
# node-ops 巡检 —— 快速确认节点健康
echo "########## 服务 ##########"
for s in xray warp-svc hysteria-server sub-server; do
  printf "  %-18s %-8s %s\n" "$s" "$(systemctl is-active $s)" "$(systemctl is-enabled $s 2>/dev/null)"
done
echo "########## 端口 ##########"
ss -tlnp | grep -E ':443|:2053|:2097|:1082' | awk '{print "  TCP",$4}'
ss -ulnp | grep ':8443' | awk '{print "  UDP",$4}'
echo "########## 内核 ##########"
printf "  拥塞控制 %s / qdisc %s\n" "$(sysctl -n net.ipv4.tcp_congestion_control)" "$(sysctl -n net.core.default_qdisc)"
echo "########## WARP ##########"
warp-cli --accept-tos status 2>&1 | head -1 | sed 's/^/  /'
curl -s -m 10 --socks5 127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace | grep -E "^warp=|^ip=" | sed 's/^/  /'
echo "########## 资源 ##########"
free -m | head -2 | sed 's/^/  /'
df -h / | tail -1 | sed 's/^/  /'
echo "########## 订阅 ##########"
printf "  节点数 %s\n" "$(curl -s -m 10 http://127.0.0.1:2097/sub | base64 -d | grep -c '://')"
echo "########## 最近客户端活动 ##########"
echo "  --- xray access.log 末尾 ---"
tail -5 /var/log/xray/access.log 2>/dev/null | sed 's/^/  /'
echo "  --- 订阅请求日志 (客户端拿到了什么格式) ---"
tail -8 /var/log/sub-server.log 2>/dev/null | sed 's/^/  /' || echo "  (无)"
