#!/usr/bin/env bash
# 安装本地 Git 钩子（提交信息校验）。每个成员克隆仓库后运行一次。
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC="$ROOT/tools/hooks/commit-msg"
DEST="$ROOT/.git/hooks/commit-msg"

if [ ! -f "$SRC" ]; then
  echo "[mcm] 找不到 $SRC" >&2
  exit 1
fi
if [ ! -d "$ROOT/.git" ]; then
  echo "[mcm] $ROOT 不是 Git 仓库" >&2
  exit 1
fi

cp "$SRC" "$DEST"
chmod +x "$DEST"
echo "[mcm] 已安装 commit-msg 钩子：$DEST"
echo "[mcm] 提交信息格式：type(scope): 说明，例如 paper(p2): 补充模型推导"
