#!/usr/bin/env bash
# =====================================================================
# Reproduce every number and table in the paper from the raw records.
# Run from the project root:  bash reproduce.sh
#
# Steps
#   1. analysis pipeline  -> results/*.tex (all counts, Table 2-11 numbers)
#   2. paper build        -> 03_论文撰写/paper/main.pdf
#   3. response letter    -> response_to_reviewers.pdf, plus the hard gate
#                            that re-checks every load-bearing number in the
#                            letter against the regenerated macros
#
# Prerequisites
#   - Python 3.13 (managed runtime used by the scripts).
#   - Raw records already present under 04_绘图与分析/results/*.json and
#     experiments/real_system/results/*.json (shipped with the artifact).
#   - A TeX distribution; the final build uses the official IEEE Access class
#     (ieeeaccess.cls), vendored under 03_论文撰写/paper/ieeeaccess/.
# =====================================================================
set -euo pipefail

# Self-check shortcut: `bash reproduce.sh check` runs the clean-environment
# + reproducibility self-check without regenerating anything (delegates to
# verify_artifact.sh).  Use `bash reproduce.sh` (no arg) for the full rebuild.
case "${1:-}" in
  check|--check|verify)
    exec bash "$(dirname "${BASH_SOURCE[0]}")/verify_artifact.sh" check ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANA="$ROOT/04_绘图与分析/analysis"
PAPER="$ROOT/03_论文撰写/paper"

# Pick an interpreter that can run the whole pipeline.  make_diagrams.py needs
# svglib + reportlab (to turn the SVG diagrams into PDF for LaTeX), on top of
# matplotlib/pandas used by compute_all.py.  Honour $PYTHON if set, otherwise
# try a list of known-good candidates and keep the first that imports svglib;
# fall back to plain `python`.
pick_python() {
  local candidates=()
  [ -n "${PYTHON:-}" ] && candidates+=("$PYTHON")
  candidates+=(
    "C:/Users/Administrator/.workbuddy/binaries/python/envs/bolaexp/Scripts/python.exe"
    "$HOME/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "python"
  )
  for c in "${candidates[@]}"; do
    if "$c" -c "import svglib, reportlab, matplotlib, pandas" >/dev/null 2>&1; then
      echo "$c"; return 0
    fi
  done
  echo "python"   # last resort; make_diagrams may need `pip install svglib reportlab`
}
PYBIN="$(pick_python)"
echo "[env] using interpreter: $PYBIN"

# [0] 入口完整性校验（R1.14 整改）：任何生成器运行之前，先核对当前输入与
# 已提交的 SHA-256 清单一致。修改过的输入会在入口被拒绝，而不是事后由
# verify 抓住；正文合同因此可以写成"必须先通过本入口校验的流程"。
echo "[0/3] Verifying input integrity against the committed manifests..."
"$PYBIN" "$ANA/make_manifests.py" --check

echo "[1/2] Running analysis pipeline (regenerates all numbers + tables)..."
pushd "$ANA" >/dev/null
"$PYBIN" compute_all.py
"$PYBIN" ingest_native_engine.py
"$PYBIN" ingest_gogs.py
# Gogs 按渠道/按机制的 oracle 保真矩阵（R1.8；只用既有 phaseE 记录）
"$PYBIN" ingest_gogs_channel.py
"$PYBIN" ingest_gitlab.py
"$PYBIN" ingest_seeded.py
# 真实 vulnerable/fixed 配对的数字（cve_pair.json 随包提供，不需重跑实例）
"$PYBIN" ingest_cve_pair.py
# 配对 fail-closed 校验的回归测试（扰动副本，不碰原始 JSON）
"$PYBIN" test_cve_pair_validation.py
# 真时序实验的数字（temporal_gitea.json 随包提供，不需重跑实例）
"$PYBIN" ingest_temporal.py
# 两条关系的显式判定式复核 + 真值表（只读既有 raw_matrix / temporal JSON）
"$PYBIN" ingest_truth.py
# 分层表（m2_stratum.tex）：ingest_design.py 会拿它的 Mii* 宏做交叉校验，必须先跑
"$PYBIN" ingest_m2_stratum.py
# 设计审计：完整因子表、匹配对归因、配置×情景普查、36/18→312/264 对账
"$PYBIN" ingest_design.py
# 决策口径：coverage / 弃权拆分 / 选择性风险 / 请求成本
"$PYBIN" ingest_coverage.py
# 竞争基线：常规多账户差分 vs 关系感知裁决（baseline_compare.json 随包提供）
"$PYBIN" ingest_baseline.py
"$PYBIN" make_diagrams.py
popd >/dev/null

# Regenerate the seeded positive-control raw record (self-contained artifact).
echo "[1b] Seeded positive-control experiment (regenerates seeded.json)..."
SEED_DIR="$ROOT/experiments/real_system"
if [ -f "$SEED_DIR/run_seeded.py" ]; then
  if ( cd "$SEED_DIR" && "$PYBIN" run_seeded.py ); then
    echo "    seeded.json regenerated"
    pushd "$ANA" >/dev/null
    "$PYBIN" ingest_seeded.py
    popd >/dev/null
  elif [ "${ALLOW_STALE:-0}" = "1" ]; then
    echo "    [WARN] seeded run failed; ALLOW_STALE=1, keeping the shipped record"
  else
    echo "    [FAIL] seeded run failed: the positive control would silently reuse" >&2
    echo "           a stale record. Fix it, or set ALLOW_STALE=1 to accept that." >&2
    exit 1
  fi
fi

echo "[2/3] Building the paper (main.pdf)..."
pushd "$PAPER" >/dev/null
bash build.sh
popd >/dev/null

# 回复信与稿件引用同一批生成宏；这一步重建回信，并硬性核对回信里的每个
# 承重数字与刚重算出来的宏一致（check_letter_numbers.py，build.sh 内调用）。
echo "[3/3] Building the response letter + letter-number check..."
bash "$ROOT/03_论文撰写/response_to_reviewers/build.sh"

echo "Done. Inspect main.pdf, response_to_reviewers.pdf and the per-table .tex under results/."
