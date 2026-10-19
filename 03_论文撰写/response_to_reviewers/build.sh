#!/usr/bin/env bash
# 重投三件套之一：逐条回复信（response_to_reviewers.pdf）
# 依赖：MiKTeX pdflatex；中文路径 ⇒ 必须在纯 ASCII 目录编译。
set -euo pipefail

PROJ="C:/Users/Administrator/WorkBuddy/3区论文"
SRC="$PROJ/03_论文撰写/response_to_reviewers/response_to_reviewers.tex"
SRC_DIR="$PROJ/03_论文撰写/response_to_reviewers"
NUM="$PROJ/04_绘图与分析/results"
BUILD="${1:-C:/Users/Administrator/WorkBuddy/rl_build}"
PYBIN="${PYTHON:-C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe}"
command -v "$PYBIN" >/dev/null 2>&1 || PYBIN=python

mkdir -p "$BUILD"
cp "$SRC" "$BUILD/"
# 回信引用的数字宏必须来自生成器，不能手抄
cp "$NUM/native_engine_numbers.tex" "$NUM/temporal_numbers.tex" \
   "$NUM/baseline_numbers.tex" "$NUM/gogs_channel_numbers.tex" "$BUILD/"
cd "$BUILD"
pdflatex -interaction=nonstopmode response_to_reviewers.tex >p1.log 2>&1 || true
pdflatex -interaction=nonstopmode response_to_reviewers.tex >p2.log 2>&1 || true
if grep -q '^!' p2.log; then
    echo "[fail] 回复信编译有错误，见 $BUILD/p2.log" >&2
    grep -n '^!' -A 3 p2.log | head -20 >&2
    exit 1
fi
if grep -q "Undefined control sequence" p2.log; then
    echo "[fail] 回复信有未定义命令（缺宏或宏名写错），见 $BUILD/p2.log" >&2
    grep -n "Undefined control sequence" -A 2 p2.log | head -12 >&2
    exit 1
fi
cp response_to_reviewers.pdf "$PROJ/03_论文撰写/response_to_reviewers/"

# 回信前言承诺「每个数字都对着制品核过」；这一步就是那个核对，且是硬门槛：
# 生成器输出变了而信没跟上（或反之），这里必须失败，而不是等读者发现。
if "$PYBIN" "$SRC_DIR/check_letter_numbers.py"; then
    echo "[ok] 回信承重数字与生成器当前输出一致"
else
    echo "[fail] 回信承重数字与生成器不一致：先改信或改生成器，再编译" >&2
    exit 1
fi
# 表号/页码引用与 main.pdf 对账（缺 PyMuPDF 时明确报 skip，不冒充通过）
REFSPY="$PYBIN"
command -v "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe" >/dev/null 2>&1 \
  && "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe" -c "import pymupdf" >/dev/null 2>&1 \
  && REFSPY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
refs_rc=0
refs_out="$("$REFSPY" "$SRC_DIR/check_letter_refs.py" 2>&1)" || refs_rc=$?
if [ "$refs_rc" != "0" ]; then
    echo "$refs_out" >&2
    echo "[fail] 回信表号/页码引用与 main.pdf 不一致" >&2
    exit 1
fi
if printf '%s' "$refs_out" | grep -q "\[skip\]"; then
    echo "[skip] 回信表号/页码引用未核对（缺 PyMuPDF；装上即可核对）"
else
    printf '%s\n' "$refs_out"
    echo "[ok] 回信表号/页码引用与 main.pdf 一致"
fi
echo "[ok] response_to_reviewers.pdf 页数 $(pdfinfo response_to_reviewers.pdf | awk '/^Pages/{print $2}')"
