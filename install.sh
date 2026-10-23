#!/usr/bin/env bash
# 把 skills/ 下的 skill 安装到 ~/.claude/skills，并装好脚本依赖。
#
# 用法：
#   ./install.sh                 # 全部 skill，软链接安装（之后 git pull 即更新）
#   ./install.sh node-ops 嵌入式  # 只装指定的 skill
#   ./install.sh --copy          # 复制而不是软链接（仓库可以删掉）
#   ./install.sh --no-deps       # 不装 npm / pip 依赖
#   ./install.sh --uninstall     # 移除本仓库装进去的 skill
#
# 目标目录可用 CLAUDE_SKILLS_DIR 覆盖，默认 ~/.claude/skills。
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO/skills"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
MODE=link
DEPS=1
UNINSTALL=0
PICK=()

for a in "$@"; do
  case "$a" in
    --copy) MODE=copy ;;
    --no-deps) DEPS=0 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "未知参数: $a" >&2; exit 1 ;;
    *) PICK+=("$a") ;;
  esac
done

if [ ${#PICK[@]} -eq 0 ]; then
  for d in "$SRC"/*/; do PICK+=("$(basename "$d")"); done
fi
for s in "${PICK[@]}"; do
  [ -f "$SRC/$s/SKILL.md" ] || { echo "没有这个 skill: $s" >&2; exit 1; }
done

mkdir -p "$DEST"

if [ $UNINSTALL -eq 1 ]; then
  for s in "${PICK[@]}"; do
    t="$DEST/$s"
    if [ -L "$t" ] && [ "$(readlink "$t")" = "$SRC/$s" ]; then
      rm "$t"; echo "  移除 $s"
    elif [ -f "$t/.installed-from-claude-skills" ]; then
      rm -rf "$t"; echo "  移除 $s"
    fi
  done
  exit 0
fi

BACKUP="$DEST/../skills-backup-$(date +%Y%m%d-%H%M%S)"
echo "安装到 $DEST（$MODE）"
for s in "${PICK[@]}"; do
  t="$DEST/$s"
  if [ -L "$t" ] && [ "$(readlink "$t")" = "$SRC/$s" ] && [ $MODE = link ]; then
    echo "  ✓ $s（已是最新链接）"; continue
  fi
  if [ -e "$t" ] || [ -L "$t" ]; then
    mkdir -p "$BACKUP"; mv "$t" "$BACKUP/"
    echo "  · 已有的 $s 备份到 $BACKUP/"
  fi
  if [ $MODE = link ]; then
    ln -s "$SRC/$s" "$t"
  else
    rsync -a --exclude node_modules --exclude .DS_Store "$SRC/$s/" "$t/"
    touch "$t/.installed-from-claude-skills"
  fi
  echo "  ✓ $s"
done

if [ $DEPS -eq 1 ]; then
  echo
  echo "安装依赖"
  need_py=0
  for s in "${PICK[@]}"; do
    case "$s" in wechat-miniprogram-lab-report|refimg-prompt-cn) need_py=1 ;; esac
  done

  if [[ " ${PICK[*]} " == *" wechat-miniprogram-lab-report "* ]]; then
    dir="$DEST/wechat-miniprogram-lab-report/scripts"
    if command -v npm >/dev/null; then
      (cd "$dir" && npm ci --silent --no-audit --no-fund) && echo "  ✓ npm: miniprogram-automator" \
        || echo "  ! npm 安装失败，稍后手动执行: cd \"$dir\" && npm install"
    else
      echo "  ! 没有 Node.js（brew install node），装好后执行: cd \"$dir\" && npm install"
    fi
  fi

  if [ $need_py -eq 1 ]; then
    if command -v python3 >/dev/null; then
      user=--user; [ -n "${VIRTUAL_ENV:-}" ] && user=
      if python3 -m pip install $user -q -r "$REPO/requirements.txt" 2>/dev/null \
        || python3 -m pip install $user -q --break-system-packages -r "$REPO/requirements.txt"; then
        echo "  ✓ pip: $(grep -v '^#' "$REPO/requirements.txt" | xargs)"
      else
        echo "  ! pip 安装失败，手动执行: python3 -m pip install --user -r \"$REPO/requirements.txt\""
      fi
    else
      echo "  ! 没有 python3（xcode-select --install 或 brew install python）"
    fi
  fi
fi

echo
echo "环境检查"
chk() { if command -v "$1" >/dev/null; then echo "  ✓ $1"; else echo "  ✗ $1 — $2"; fi; }
chk python3 "多数脚本需要"
chk node    "wechat-miniprogram-lab-report 截图、php-mysql-coursework 生成 docx 需要"
chk swift   "wechat-miniprogram-lab-report 取窗口 ID 需要（xcode-select --install）"
chk expect  "node-ops 首次推送 SSH 公钥需要（macOS 自带）"
[ -d "/Applications/wechatwebdevtools.app" ] && echo "  ✓ 微信开发者工具" \
  || echo "  ✗ 微信开发者工具 — wechat-miniprogram-lab-report 需要，并在 设置→安全设置 打开服务端口"

echo
echo "完成。重开 Claude Code 会话后即可使用。"
