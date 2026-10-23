#!/bin/bash
# 截微信开发者工具整个窗口（编辑器 + 模拟器），用于"开发界面""配置文件截图"这类题。
# 用法: bash ide_shot.sh 项目目录 输出.png [等待秒数，默认8]
# 编辑器里显示哪个文件：开发者工具会恢复该项目上次打开的文件；要换文件见 SKILL.md「开发者工具界面截图」。
set -e
CLI=/Applications/wechatwebdevtools.app/Contents/MacOS/cli
DIR="$(cd "$(dirname "$0")" && pwd)"
"$CLI" open --project "$1" >/dev/null 2>&1
sleep "${3:-8}"
WID=$(swift "$DIR/window_id.swift")
if [ -z "$WID" ] || [ "$WID" = "0" ]; then echo "没找到开发者工具窗口"; exit 1; fi
screencapture -x -o -l "$WID" "$2"
echo "窗口 $WID 已截图: $2"
