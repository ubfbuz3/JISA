#!/usr/bin/env bash
# =====================================================================
# Reproduce every number and table in the paper from the raw records.
# Run from the project root:  bash reproduce.sh
#
# Steps
#   1. analysis pipeline  -> results/*.tex (all counts, Table 2-11 numbers)
#   2. paper build        -> 03_论文撰写/paper/main.pdf
#
# Prerequisites
#   - Python 3.13 (managed runtime used by the scripts).
#   - Raw records already present under 04_绘图与分析/results/*.json and
#     experiments/real_system/results/*.json (shipped with the artifact).
#   - A TeX distribution with the elsarticle class for the final build.
# =====================================================================
set -euo pipefail

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

echo "[1/2] Running analysis pipeline (regenerates all numbers + tables)..."
pushd "$ANA" >/dev/null
"$PYBIN" compute_all.py
"$PYBIN" ingest_native_engine.py
"$PYBIN" ingest_gogs.py
"$PYBIN" ingest_gitlab.py
"$PYBIN" ingest_seeded.py
"$PYBIN" make_diagrams.py
popd >/dev/null

# Regenerate the seeded positive-control raw record (self-contained artifact).
echo "[1b] Seeded positive-control experiment (regenerates seeded.json)..."
SEED_DIR="$ROOT/experiments/real_system"
if [ -f "$SEED_DIR/run_seeded.py" ]; then
  ( cd "$SEED_DIR" && "$PYBIN" run_seeded.py ) \
    && echo "    seeded.json regenerated" \
    || echo "    (seeded run skipped: port busy or dependency missing)"
  # re-ingest so the table reflects the freshly generated record
  pushd "$ANA" >/dev/null
  "$PYBIN" ingest_seeded.py
  popd >/dev/null
fi

echo "[2/2] Building the paper (main.pdf)..."
pushd "$PAPER" >/dev/null
bash build.sh
popd >/dev/null

echo "Done. Inspect main.pdf and the per-table .tex under results/."
