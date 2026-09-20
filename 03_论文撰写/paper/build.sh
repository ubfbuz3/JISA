#!/usr/bin/env bash
# =====================================================================
#  编译 JISA 论文。会把源码装配到纯 ASCII 工作目录再编译，
#  以避开中文路径在 MiKTeX / BibTeX 下的各类问题。
#
#  用法:  bash 03_论文撰写/paper/build.sh
#  产物:  03_论文撰写/paper/main.pdf  （以及 ASCII 目录下的日志）
#  失败:  非 0 退出，并打印日志中的报错行。
# =====================================================================
set -uo pipefail

SRC_PAPER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="$(cd "$SRC_PAPER/../.." && pwd)"
BUILD="/c/Users/Administrator/WorkBuddy/jisa_paper_build"

ENGINE="${LATEX_ENGINE:-pdflatex}"

echo "== [1/5] 前置检查 =="
command -v "$ENGINE" >/dev/null 2>&1 || { echo "!! 找不到 $ENGINE，请确认 MiKTeX 在 PATH 中"; exit 1; }
command -v bibtex  >/dev/null 2>&1 || { echo "!! 找不到 bibtex"; exit 1; }

# 数字与引用必须先由分析管线生成
for f in "$PROJ/04_绘图与分析/results/numbers.tex" \
         "$PROJ/04_绘图与分析/results/native_engine_numbers.tex" \
         "$PROJ/04_绘图与分析/results/native_engine_table.tex" \
         "$PROJ/04_绘图与分析/results/gogs_numbers.tex" \
         "$PROJ/04_绘图与分析/results/gogs_cross_table.tex" \
         "$PROJ/04_绘图与分析/results/gitlab_numbers.tex" \
         "$PROJ/04_绘图与分析/results/seeded_table.tex" \
         "$PROJ/04_绘图与分析/results/m2_stratum.tex" \
         "$SRC_PAPER/refs.bib"; do
  [ -f "$f" ] || { echo "!! 缺少 $f，请先跑 analysis/compute_all.py ingest_native_engine.py ingest_gogs.py ingest_gitlab.py ingest_seeded.py"; exit 1; }
done

# refs.bib 的**字段值**里不能有非 ASCII（BibTeX 会原样写进 .bbl，
# pdflatex 遇 CJK 直接 Fatal error）。注释行允许中文。
PYBIN="${PYTHON:-python}"
if command -v cygpath >/dev/null 2>&1; then
  REFS_WIN="$(cygpath -w "$SRC_PAPER/refs.bib")"
else
  REFS_WIN="$SRC_PAPER/refs.bib"
fi
if "$PYBIN" - "$REFS_WIN" <<'PY'
import sys
p = sys.argv[1]
bad = []
for i, line in enumerate(open(p, encoding="utf-8"), 1):
    s = line.strip()
    if s.startswith("%"):
        continue
    # 允许 ASCII 与拉丁补充（U+00A0–U+00FF，人名重音等 pdflatex 可处理）；
    # 其余（CJK 等）会让 pdflatex 报 Unicode character not set up。
    illegal = sorted({c for c in line
                      if ord(c) > 127 and not (0xA0 <= ord(c) <= 0xFF)})
    if illegal:
        bad.append((i, "".join(illegal), line.rstrip()[:90]))
if bad:
    print("!! refs.bib 含 pdflatex 不支持的字符:")
    for i, ch, t in bad:
        print(f"   line {i} [{ch}]: {t}")
    sys.exit(1)
PY
then :; else echo "!! refs.bib 校验不通过"; exit 1; fi

echo "== [2/5] 装配到纯 ASCII 目录: $BUILD =="
rm -rf "$BUILD"
mkdir -p "$BUILD/sections" "$BUILD/figures" "$BUILD/thumbnails"

cp "$SRC_PAPER/main.tex"           "$BUILD/"
cp "$SRC_PAPER/cas-dc.cls"         "$BUILD/"
cp "$SRC_PAPER/cas-common.sty"     "$BUILD/"
cp "$SRC_PAPER/cas-model2-names.bst" "$BUILD/"
cp "$PROJ/04_绘图与分析/results/numbers.tex" "$BUILD/"
cp "$PROJ/04_绘图与分析/results/native_engine_numbers.tex" "$BUILD/"
cp "$PROJ/04_绘图与分析/results/native_engine_table.tex" "$BUILD/"
cp "$PROJ/04_绘图与分析/results/gogs_numbers.tex" "$BUILD/"
cp "$PROJ/04_绘图与分析/results/gogs_cross_table.tex" "$BUILD/"
cp "$PROJ/04_绘图与分析/results/gitlab_numbers.tex" "$BUILD/"
cp "$PROJ/04_绘图与分析/results/seeded_table.tex" "$BUILD/"
cp "$PROJ/04_绘图与分析/results/m2_stratum.tex" "$BUILD/"
cp "$SRC_PAPER/refs.bib"           "$BUILD/"
cp "$SRC_PAPER"/sections/*.tex     "$BUILD/sections/"
# 只装配矢量 PDF 图（无 AI 生成像素；矢量可无限缩放）
cp "$PROJ"/04_绘图与分析/figures/*.pdf "$BUILD/figures/"
# CAS 模板的通讯图标（email/url 缩略图，模板自带资源，非 AI 像素）
cp "$SRC_PAPER"/thumbnails/*.jpeg "$BUILD/thumbnails/"

echo "   装配清单:"
( cd "$BUILD" && find . -type f | sort | sed 's/^/     /' )

echo "== [3/5] 编译（$ENGINE -> bibtex -> $ENGINE x2）=="
cd "$BUILD"
# 可复现构建：固定构建时间戳，使 pdfTeX 生成确定的 trailer /ID（否则每次编译都
# 不同）。main.tex 已用 \pdfinfoomitdate 省略 PDF 的日期字段，故该取值不出现在
# 产物里，同一份源码在任何机器上都能得到字节一致的 main.pdf。
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"
run() { "$ENGINE" -interaction=nonstopmode -halt-on-error main.tex >"$1.log" 2>&1; echo $?; }

rc=$(run pass1); [ "$rc" = "0" ] || { echo "!! 第一遍 $ENGINE 失败"; grep -n -m 15 '^! ' pass1.log || true; exit 1; }

bibtex main >bibtex.log 2>&1 || {
  echo "!! bibtex 失败"; cat bibtex.log | head -30; exit 1; }

rc=$(run pass2); [ "$rc" = "0" ] || { echo "!! 第二遍 $ENGINE 失败"; grep -n -m 15 '^! ' pass2.log || true; exit 1; }
rc=$(run pass3); [ "$rc" = "0" ] || { echo "!! 第三遍 $ENGINE 失败"; grep -n -m 15 '^! ' pass3.log || true; exit 1; }

echo "== [4/5] 校验 =="
fail=0

# 未定义引用 / 未定义宏
for pat in 'LaTeX Warning: Reference' 'LaTeX Warning: Citation' 'Undefined control sequence'; do
  n=$(grep -c "$pat" pass3.log || true)
  if [ "$n" != "0" ]; then echo "!! 命中 $n 处: $pat"; grep -m 8 "$pat" pass3.log; fail=1; fi
done

# 未解析的交叉引用
if grep -q "There were undefined references" pass3.log; then
  echo "!! 存在未解析的交叉引用"; grep -m 10 "undefined" pass3.log; fail=1
fi
# bibtex 未解析的条目
if [ -f main.blg ] && grep -qi "didn't find a database entry\|I found no" main.blg; then
  echo "!! bibtex 有未解析条目"; grep -i -m 10 "warning" main.blg; fail=1
fi
# 浮动体未放置
if grep -q "LaTeX Warning: Float too large\|LaTeX Warning:.*float" pass3.log; then
  echo "!! 有浮动体告警"; grep -m 5 "float" pass3.log
fi

[ -f main.pdf ] || { echo "!! 未生成 main.pdf"; fail=1; }

echo "== [5/5] 回写产物 =="
if [ "$fail" = "0" ]; then
  cp main.pdf "$SRC_PAPER/main.pdf"
  pages=$(grep -ao "Output written on main.pdf ([0-9]* pages" pass3.log | grep -ao "[0-9]*" | tail -1)
  echo "[ok] $SRC_PAPER/main.pdf"
  echo "     页数 $pages ; 字节 $(wc -c <main.pdf) ; 编译日志 $BUILD/pass3.log"
else
  echo "!! 校验未通过，未回写 PDF。日志: $BUILD/pass3.log"
  exit 1
fi
