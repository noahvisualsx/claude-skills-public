#!/bin/bash
# 起一个完全独立于用户机器已有 MySQL 的临时实例，只用于本地测试。
# 不会碰用户已有的数据库/账号密码，测试完直接删掉 $WORKDIR 就是彻底清理干净。
#
# 用法：
#   ./setup_isolated_mysql.sh <workdir> <port> [socket_path]
# 示例：
#   ./setup_isolated_mysql.sh /tmp/mytest-mysql 33061 /tmp/mytest.sock
#
# 起完之后连接方式（PHP 里用 mysqli_connect 时同理）：
#   mysql -u root --socket=/tmp/mytest.sock
#   mysqli_connect("127.0.0.1", "root", "", "数据库名", 33061)
#
# 停止：mysqladmin -u root --socket=<socket_path> shutdown
# 清理：rm -rf <workdir> <socket_path>

set -e

WORKDIR="${1:?用法: setup_isolated_mysql.sh <workdir> <port> [socket_path]}"
PORT="${2:?需要指定端口，例如 33061}"
SOCK="${3:-/tmp/$(basename "$WORKDIR").sock}"

# socket 路径必须短（AF_UNIX 限制约103字符），不要放在很深的临时目录里，
# 否则 mysqld 会报 "socket file path is too long" 直接拒绝启动。
if [ ${#SOCK} -gt 100 ]; then
  echo "警告：socket 路径过长（${#SOCK} 字符），mysqld 可能拒绝启动，建议换成 /tmp/xxx.sock 这种短路径" >&2
fi

DATADIR="$WORKDIR/data"
mkdir -p "$DATADIR"

echo "== 初始化空的 MySQL 数据目录 =="
mysqld --initialize-insecure --datadir="$DATADIR" --basedir="$(brew --prefix mysql 2>/dev/null || echo /usr/local)"

echo "== 启动隔离实例（socket=$SOCK port=$PORT） =="
mysqld \
  --datadir="$DATADIR" \
  --socket="$SOCK" \
  --port="$PORT" \
  --pid-file="$WORKDIR/mysqld.pid" \
  --mysqlx=0 \
  > "$WORKDIR/mysqld.log" 2>&1 &

disown
sleep 3

if mysqladmin -u root --socket="$SOCK" ping 2>/dev/null; then
  echo "== 就绪：mysql -u root --socket=$SOCK =="
  echo "== PHP 连接参数：mysqli_connect(\"127.0.0.1\", \"root\", \"\", \"你的数据库名\", $PORT) =="
else
  echo "启动失败，看日志：$WORKDIR/mysqld.log" >&2
  tail -30 "$WORKDIR/mysqld.log" >&2
  exit 1
fi
