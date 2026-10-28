#!/usr/bin/env bash
# Superpowers for CodeBuddy —— 安装 / 卸载
#
#   ./install.sh                    装到用户级 ~/.codebuddy/skills
#   ./install.sh --project          装到当前项目的 ./.codebuddy/skills
#   ./install.sh --with-hook        额外注册 SessionStart 引导注入（会改 settings.json）
#   ./install.sh --force            跳过冲突确认
#   ./install.sh --uninstall        卸载（用安装清单，不碰别人的目录）
#   ./install.sh --dry-run          只打印将要做什么
#
# 环境变量 CODEBUDDY_DIR 可覆盖 ~/.codebuddy（测试用）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_ROOT/skills"
CB_DIR="${CODEBUDDY_DIR:-$HOME/.codebuddy}"
PKG_DIR="$CB_DIR/superpowers"
MANIFEST="$PKG_DIR/installed.txt"
HOOK_SRC="$REPO_ROOT/hooks/session-start"
HOOK_DEST="$PKG_DIR/hooks/session-start"

SCOPE="user"
WITH_HOOK=0
FORCE=0
UNINSTALL=0
DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project) SCOPE="project"; shift ;;
    --with-hook) WITH_HOOK=1; shift ;;
    --force) FORCE=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "未知参数: $1（-h 看用法）" >&2; exit 2 ;;
  esac
done

if [ "$SCOPE" = "project" ]; then
  DEST="$(pwd)/.codebuddy/skills"
else
  DEST="$CB_DIR/skills"
fi

run() {
  if [ "$DRY" -eq 1 ]; then echo "  [dry-run] $*"; else "$@"; fi
}

# ---------- 卸载 ----------
if [ "$UNINSTALL" -eq 1 ]; then
  if [ ! -f "$MANIFEST" ]; then
    echo "找不到安装清单 ${MANIFEST}，无法确定哪些目录是本工具装的，已中止。" >&2
    echo "如果你要手工删除，目录名都以 superpowers- 开头。" >&2
    exit 1
  fi
  n=0
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    if [ -d "$DEST/$name" ]; then
      run rm -rf "$DEST/$name"
      n=$((n+1))
    fi
  done < "$MANIFEST"
  run rm -f "$MANIFEST"
  echo "已移除 ${n} 个技能目录（${DEST}）"
  if python3 "$REPO_ROOT/adapt/hook_register.py" status --settings "$CB_DIR/settings.json" >/dev/null 2>&1; then
    if [ "$DRY" -eq 1 ]; then
      echo "  [dry-run] 移除 SessionStart hook 注册"
    else
      python3 "$REPO_ROOT/adapt/hook_register.py" remove --settings "$CB_DIR/settings.json"
    fi
  fi
  exit 0
fi

# ---------- 安装前检查 ----------
[ -d "$SRC" ] || { echo "仓库里没有 skills/，请先跑 python3 adapt/generate.py" >&2; exit 1; }

command -v python3 >/dev/null || { echo "需要 python3" >&2; exit 1; }

names=()
for d in "$SRC"/superpowers-*/; do names+=("$(basename "$d")"); done
[ ${#names[@]} -gt 0 ] || { echo "skills/ 里没有技能，先跑生成器" >&2; exit 1; }

conflicts=()
for name in "${names[@]}"; do
  bare="${name#superpowers-}"
  # 官方插件市场 4.0.3 用的是无前缀技能名，两套会同时触发
  if [ -d "$DEST/$bare" ] && [ ! -f "$DEST/$bare/.superpowers-codebuddy" ]; then
    conflicts+=("${bare}（无前缀同名技能，通常是插件市场里的 superpowers 4.0.3）")
  fi
done

if [ ${#conflicts[@]} -gt 0 ]; then
  echo "检测到可能同时生效的旧版技能：" >&2
  printf '  - %s\n' "${conflicts[@]}" >&2
  echo "两套流程同时存在会互相打架。建议先在 CodeBuddy 里禁用插件市场的 superpowers，" >&2
  echo "或删除上述目录后重跑。确认继续请加 --force。" >&2
  if [ "$FORCE" -ne 1 ]; then exit 4; fi
  echo "（已用 --force 继续）"
fi

# ---------- 安装 ----------
echo "安装目标：$DEST"
run mkdir -p "$DEST" "$PKG_DIR"
[ "$DRY" -eq 1 ] || : > "$MANIFEST.tmp"

installed=0
for name in "${names[@]}"; do
  target="$DEST/$name"
  if [ -d "$target" ]; then
    # 不是本工具装的同名目录：先备份再覆盖，绝不静默删除
    if ! grep -qx "$name" "$MANIFEST" 2>/dev/null; then
      bk="$PKG_DIR/backup-$(date +%Y%m%d-%H%M%S)/$name"
      run mkdir -p "$(dirname "$bk")"
      run mv "$target" "$bk"
      echo "  已有同名目录，已备份到 $bk"
    else
      run rm -rf "$target"
    fi
  fi
  run cp -R "$SRC/$name" "$target"
  [ "$DRY" -eq 1 ] || echo "$name" >> "$MANIFEST.tmp"
  installed=$((installed+1))
done

if [ "$DRY" -eq 0 ]; then mv "$MANIFEST.tmp" "$MANIFEST"; fi
echo "已安装 $installed 个技能"

# ---------- 可选：引导注入 ----------
if [ "$WITH_HOOK" -eq 1 ]; then
  if [ "$SCOPE" = "project" ]; then
    echo "--with-hook 只支持用户级安装（settings.json 是用户级的），已跳过" >&2
  else
    run mkdir -p "$(dirname "$HOOK_DEST")"
    run cp "$HOOK_SRC" "$HOOK_DEST"
    run chmod +x "$HOOK_DEST"
    if [ "$DRY" -eq 1 ]; then
      echo "  [dry-run] 注册 SessionStart hook -> $CB_DIR/settings.json"
    else
      python3 "$REPO_ROOT/adapt/hook_register.py" add \
        --script "$HOOK_DEST" --settings "$CB_DIR/settings.json"
    fi
  fi
else
  echo "提示：加 --with-hook 可注册引导注入（每次新会话强制加载技能规则）。"
  echo "      不加也能用，技能靠 description 自动触发，只是不会被强制前置。"
fi

echo
echo "自检：python3 $REPO_ROOT/adapt/verify.py"
