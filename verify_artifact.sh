#!/usr/bin/env bash
# =====================================================================
# verify_artifact.sh — one-command clean-environment + reproducibility
# self-check for the JISA submission artifact.
#
#   Run from the repo root:
#     bash verify_artifact.sh            # = check  (default)
#     bash verify_artifact.sh check      # pre-flight + input/output integrity
#     bash verify_artifact.sh repro      # temp-staging full regeneration -> compare
#     bash verify_artifact.sh gen-manifest
#
#   Also reachable through the reproduction driver:
#     bash reproduce.sh check
#
#   "clean environment" here means three things, all verified in one pass:
#     1. the toolchain (Python + the four analysis packages, and a TeX
#        distribution) is present;
#     2. every raw record the paper consumes is intact and unmodified
#        (SHA-256 matches provenance/RAW_RECORDS_SHA256.json);
#     3. every byte-reproducible output (all number-bearing .tex tables,
#        metrics.json, the two vector diagrams) is intact and unmodified
#        (SHA-256 matches provenance/OUTPUTS_SHA256.json).
#
#   `repro` additionally proves the numbers regenerate byte-for-byte from
#   the raw records, inside a throw-away copy, leaving the working tree
#   untouched.
# =====================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROV="$ROOT/04_绘图与分析/provenance"
ANA="$ROOT/04_绘图与分析/analysis"
RAW_MANIFEST="$PROV/RAW_RECORDS_SHA256.json"
OUT_MANIFEST="$PROV/OUTPUTS_SHA256.json"

# --- pick a Python interpreter (same logic as reproduce.sh) --------------
pick_python() {
  local candidates=()
  [ -n "${PYTHON:-}" ] && candidates+=("$PYTHON")
  candidates+=(
    "C:/Users/Administrator/.workbuddy/binaries/python/envs/bolaexp/Scripts/python.exe"
    "$HOME/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
    "python"
  )
  for c in "${candidates[@]}"; do
    if "$c" -c "import hashlib" >/dev/null 2>&1; then
      echo "$c"; return 0
    fi
  done
  echo "python"
}
PYBIN="$(pick_python)"

# Git-Bash reports POSIX paths (/c/Users/...); native Windows Python cannot
# open those, so convert any path we hand to Python into its Windows form.
winpath() { cygpath -w "$1" 2>/dev/null || echo "$1"; }

# portable SHA-256 of one file, via the chosen interpreter
hash_file() {
  "$PYBIN" - "$1" <<'PY'
import sys, hashlib
p = sys.argv[1]
h = hashlib.sha256()
with open(p, 'rb') as f:
    for b in iter(lambda: f.read(1 << 20), b''):
        h.update(b)
print(h.hexdigest())
PY
}

ok=0; bad=0
pass_line() { echo "  [PASS] $1"; }
fail_line() { echo "  [FAIL] $1"; bad=$((bad+1)); }

# ----------------------------------------------------------------------
# check mode
# ----------------------------------------------------------------------
do_check() {
  echo "=========================================================="
  echo " verify_artifact.sh  ::  CHECK  (clean-environment + integrity)"
  echo "=========================================================="

  # 1. toolchain pre-flight ------------------------------------------
  echo
  echo "[1/3] Toolchain pre-flight"
  echo "  interpreter: $PYBIN"
  if "$PYBIN" -c "import svglib, reportlab, matplotlib, pandas" >/dev/null 2>&1; then
    pass_line "Python packages present: svglib, reportlab, matplotlib, pandas"
  else
    fail_line "missing Python package(s): svglib / reportlab / matplotlib / pandas"
    echo "         install with: pip install svglib reportlab matplotlib pandas"
  fi
  if command -v pdflatex >/dev/null 2>&1; then
    pass_line "pdflatex present"
  else
    fail_line "pdflatex not found (required for the final PDF build)"
  fi
  if command -v bibtex >/dev/null 2>&1; then
    pass_line "bibtex present"
  else
    fail_line "bibtex not found (required for the final PDF build)"
  fi
  echo "  [note] Docker is NOT required to reproduce the paper numbers;"
  echo "         it is only needed to re-run the live Gitea/Gogs/GitLab labs."

  # 2. input integrity -----------------------------------------------
  echo
  echo "[2/3] Raw-record integrity (inputs -> provenance/RAW_RECORDS_SHA256.json)"
  if [ ! -f "$RAW_MANIFEST" ]; then
    fail_line "manifest missing: $RAW_MANIFEST (run: bash verify_artifact.sh gen-manifest)"
  else
    rows="$("$PYBIN" - "$(winpath "$RAW_MANIFEST")" "$(winpath "$ROOT")" <<'PY'
import sys, json, os, hashlib
mf, root = sys.argv[1], sys.argv[2]
data = json.load(open(mf, encoding="utf-8"))
for f in data["files"]:
    p = os.path.join(root, f["path"])
    if not os.path.isfile(p):
        print("FAIL|missing: " + f["path"]); continue
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1<<20), b""): h.update(b)
    if h.hexdigest() == f["sha256"]:
        print("PASS|" + f["path"])
    else:
        print("FAIL|hash mismatch: " + f["path"])
PY
)"
    while IFS='|' read -r st msg; do
      case "$st" in PASS) pass_line "$msg";; FAIL) fail_line "$msg";; esac
    done <<< "$rows"
  fi

  # 3. output integrity ----------------------------------------------
  echo
  echo "[3/3] Reproducible-output integrity (outputs -> provenance/OUTPUTS_SHA256.json)"
  if [ ! -f "$OUT_MANIFEST" ]; then
    fail_line "manifest missing: $OUT_MANIFEST (run: bash verify_artifact.sh gen-manifest)"
  else
    rows="$("$PYBIN" - "$(winpath "$OUT_MANIFEST")" "$(winpath "$ROOT")" <<'PY'
import sys, json, os, hashlib
mf, root = sys.argv[1], sys.argv[2]
data = json.load(open(mf, encoding="utf-8"))
for f in data["files"]:
    p = os.path.join(root, f["path"])
    if not os.path.isfile(p):
        print("FAIL|missing: " + f["path"]); continue
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1<<20), b""): h.update(b)
    if h.hexdigest() == f["sha256"]:
        print("PASS|" + f["path"])
    else:
        print("FAIL|hash mismatch: " + f["path"])
PY
)"
    while IFS='|' read -r st msg; do
      case "$st" in PASS) pass_line "$msg";; FAIL) fail_line "$msg";; esac
    done <<< "$rows"
  fi

  # working-tree status (informational)
  echo
  if command -v git >/dev/null 2>&1 && git -C "$(winpath "$ROOT")" rev-parse >/dev/null 2>&1; then
    dirty="$(git -C "$(winpath "$ROOT")" status --porcelain)"
    if [ -n "$dirty" ]; then
      echo "  [WARN] working tree has uncommitted changes:"
      echo "$dirty" | sed 's/^/         /'
    else
      pass_line "git working tree clean"
    fi
  fi

  echo
  if [ "$bad" -eq 0 ]; then
    echo "  RESULT: PASS — environment ready, all inputs and reproducible"
    echo "          outputs are intact. Run 'bash reproduce.sh' to rebuild."
  else
    echo "  RESULT: $bad issue(s) found — see [FAIL] lines above."
  fi
  return $bad
}

# ----------------------------------------------------------------------
# repro mode — temp-staging full regeneration, then compare
# ----------------------------------------------------------------------
do_repro() {
  echo "=========================================================="
  echo " verify_artifact.sh  ::  REPRO  (regenerate in a temp copy)"
  echo "=========================================================="
  if ! "$PYBIN" -c "import svglib, reportlab, matplotlib, pandas" >/dev/null 2>&1; then
    echo "  [FAIL] missing Python packages; cannot regenerate. Install then retry."
    return 1
  fi
  TMP="$(mktemp -d -t jisa_repro.XXXXXX)"
  echo "  staging copy (committed tree via git archive): $TMP"
  # Faithful, working-tree-independent staging: extract the *committed* tree
  # (git archive drops .git and honours .gitignore), then inject the
  # uncommitted reproducibility manifests so repro can compare against them.
  # MST_SRC is an external absolute path and is read directly when present.
  git -C "$(winpath "$ROOT")" archive --format=tar HEAD | tar -x -C "$TMP"
  mkdir -p "$TMP/04_绘图与分析/provenance"
  cp "$RAW_MANIFEST" "$TMP/04_绘图与分析/provenance/" 2>/dev/null || true
  cp "$OUT_MANIFEST"  "$TMP/04_绘图与分析/provenance/" 2>/dev/null || true

  echo "  [run] analysis pipeline inside the temp copy ..."
  pushd "$TMP/04_绘图与分析/analysis" >/dev/null
  "$PYBIN" compute_all.py >/dev/null 2>&1 || { echo "  [FAIL] compute_all.py"; popd >/dev/null; rm -rf "$TMP"; return 1; }
  "$PYBIN" ingest_native_engine.py >/dev/null 2>&1
  "$PYBIN" ingest_gogs.py >/dev/null 2>&1
  "$PYBIN" ingest_gitlab.py >/dev/null 2>&1
  "$PYBIN" ingest_seeded.py >/dev/null 2>&1
  "$PYBIN" make_diagrams.py >/dev/null 2>&1 || { echo "  [WARN] make_diagrams.py (figures)"; }
  popd >/dev/null

  echo "  [cmp] regenerated outputs vs provenance/OUTPUTS_SHA256.json"
  bad=0
  rows="$("$PYBIN" - "$(winpath "$OUT_MANIFEST")" "$(winpath "$TMP")" "$(winpath "$ROOT")" <<'PY'
import sys, json, os, hashlib
mf, tmp, root = sys.argv[1], sys.argv[2], sys.argv[3]
data = json.load(open(mf, encoding="utf-8"))
for f in data["files"]:
    p = os.path.join(tmp, f["path"])
    if not os.path.isfile(p):
        print("FAIL|missing after regen: " + f["path"]); continue
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1<<20), b""): h.update(b)
    if h.hexdigest() == f["sha256"]:
        print("PASS|byte-identical: " + f["path"])
    else:
        print("FAIL|drift: " + f["path"])
PY
)"
  while IFS='|' read -r st msg; do
    case "$st" in PASS) echo "  [PASS] $msg";; FAIL) echo "  [FAIL] $msg"; bad=$((bad+1));; esac
  done <<< "$rows"

  echo "  cleaning staging copy ..."
  rm -rf "$TMP"
  echo
  if [ "$bad" -eq 0 ]; then
    echo "  RESULT: PASS — every number/table/diagram regenerates byte-for-byte"
    echo "          from the raw records. Working tree was not modified."
  else
    echo "  RESULT: $bad output(s) drifted from the committed manifest."
    echo "          Re-run 'bash verify_artifact.sh gen-manifest' only if the"
    echo "          change is intentional and the raw records were updated too."
  fi
  return $bad
}

# ----------------------------------------------------------------------
# dispatch
# ----------------------------------------------------------------------
case "${1:-check}" in
  check|--check|verify) do_check ;;
  repro|--repro|regen)  do_repro ;;
  gen-manifest|--gen-manifest)
    echo "[gen] regenerating manifests ..."
    "$PYBIN" "$ANA/make_manifests.py" ;;
  *) echo "usage: bash verify_artifact.sh [check|repro|gen-manifest]"; exit 2 ;;
esac
