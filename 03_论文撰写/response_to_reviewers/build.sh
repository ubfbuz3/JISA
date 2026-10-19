#!/usr/bin/env bash
# 重投三件套之一：逐条回复信（response_to_reviewers.pdf）
# 依赖：MiKTeX pdflatex；中文路径 ⇒ 必须在纯 ASCII 目录编译。
set -euo pipefail

PROJ="C:/Users/Administrator/WorkBuddy/3区论文"
SRC="$PROJ/03_论文撰写/response_to_reviewers/response_to_reviewers.tex"
BUILD="${1:-C:/Users/Administrator/WorkBuddy/rl_build}"

mkdir -p "$BUILD"
cp "$SRC" "$BUILD/"
cd "$BUILD"
pdflatex -interaction=nonstopmode response_to_reviewers.tex >p1.log 2>&1 || true
pdflatex -interaction=nonstopmode response_to_reviewers.tex >p2.log 2>&1
if grep -q '^!' p2.log; then
    echo "[fail] 回复信编译有错误，见 $BUILD/p2.log" >&2
    grep -n '^!' -A 3 p2.log | head -20 >&2
    exit 1
fi
cp response_to_reviewers.pdf "$PROJ/03_论文撰写/response_to_reviewers/"
echo "[ok] response_to_reviewers.pdf 页数 $(pdfinfo response_to_reviewers.pdf | awk '/^Pages/{print $2}')"
