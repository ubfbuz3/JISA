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
#        (SHA-256 matches provenance/OUTPUTS_SHA256.json);
#     4. every load-bearing number quoted in the response letter matches
#        the current generator output (check_letter_numbers.py), which is
#        the check the letter's preface commits to.
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
  echo "[1/4] Toolchain pre-flight"
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
  echo "[2/4] Raw-record integrity (inputs -> provenance/RAW_RECORDS_SHA256.json)"
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
  echo "[3/4] Reproducible-output integrity (outputs -> provenance/OUTPUTS_SHA256.json)"
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

  # 4. response-letter numbers ---------------------------------------
  # 回信前言承诺每个承重数字都对着制品核过；这一步在本地树上重跑那个核对。
  echo
  echo "[4/4] Response-letter numbers vs generator output"
  local letter_dir="$ROOT/03_论文撰写/response_to_reviewers"
  if [ -f "$letter_dir/check_letter_numbers.py" ]; then
    if ( cd "$letter_dir" && "$PYBIN" check_letter_numbers.py ); then
      pass_line "response letter: every load-bearing number matches the generator"
    else
      fail_line "check_letter_numbers.py: letter numbers drifted from the generator"
    fi
  else
    fail_line "missing: 03_论文撰写/response_to_reviewers/check_letter_numbers.py"
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
    echo "          outputs are intact, and the response letter's numbers"
    echo "          match the generator. Run 'bash reproduce.sh' to rebuild."
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
  # 外部依赖先点名：MST 引擎源码在包外（绝对路径），ResLit*/ResArt* 宏由扫描它
  # 得出。缺它时 compute_all.py 直接失败；这里先明确报出，避免把"缺依赖"
  # 误读成"数字漂移"。
  local mst="C:/Users/Administrator/WorkBuddy/mst_engine/MST"
  if [ -d "$mst" ]; then
    echo "  [note] external dependency present: $mst"
  else
    echo "  [FAIL] external dependency missing: $mst" >&2
    echo "         The source-derived macros cannot be regenerated without it;" >&2
    echo "         clone it to the same path, or record this run as excluding" >&2
    echo "         the source-derived macros. Not a silent skip." >&2
    return 1
  fi
  TMP="$(mktemp -d -t jisa_repro.XXXXXX)"
  echo "  staging copy (committed tree via git archive): $TMP"
  # Faithful, working-tree-independent staging: extract the *committed* tree
  # (git archive drops .git and honours .gitignore), then inject the
  # uncommitted reproducibility manifests so repro can compare against them.
  # What this does and does not prove: the pipeline cannot see the working
  # tree, but the comparison manifests themselves are injected from the
  # working tree, and the run reads the external MST source above. It is a
  # same-machine recomputation of the pipeline from the raw records, not a
  # claim that every dependency is packaged inside the artifact.
  git -C "$(winpath "$ROOT")" archive --format=tar HEAD | tar -x -C "$TMP"
  mkdir -p "$TMP/04_绘图与分析/provenance"
  cp "$RAW_MANIFEST" "$TMP/04_绘图与分析/provenance/" 2>/dev/null || true
  cp "$OUT_MANIFEST"  "$TMP/04_绘图与分析/provenance/" 2>/dev/null || true

  # 先删掉 staging 里已提交的生成产物：否则某一步失败时会拿旧文件去比对，
  # 把"没重算"伪装成"逐位一致"。
  echo "  [clr] clearing staged generated outputs before regenerating ..."
  "$PYBIN" - "$(winpath "$OUT_MANIFEST")" "$(winpath "$TMP")" <<'PY'
import sys, json, os
mf, tmp = sys.argv[1], sys.argv[2]
data = json.load(open(mf, encoding="utf-8"))
n = 0
for f in data["files"]:
    p = os.path.join(tmp, f["path"])
    if os.path.isfile(p):
        os.remove(p); n += 1
print(f"  removed {n} staged output file(s)")
PY

  echo "  [run] analysis pipeline inside the temp copy ..."
  pushd "$TMP/04_绘图与分析/analysis" >/dev/null
  # 每一步的退出码都要拦：早先多数步骤只重定向不检查，失败会留旧文件继续走。
  # make_diagrams 只影响插图，保留为告警。
  local step_failed=0
  run_step() {
    local name="$1"; shift
    if ! "$PYBIN" "$@" >/dev/null 2>&1; then
      echo "  [FAIL] $name exited non-zero"
      step_failed=1
    fi
  }
  run_step compute_all.py              compute_all.py
  run_step ingest_native_engine.py     ingest_native_engine.py
  run_step ingest_gogs.py              ingest_gogs.py
  run_step ingest_gogs_channel.py      ingest_gogs_channel.py
  run_step ingest_gitlab.py            ingest_gitlab.py
  run_step ingest_seeded.py            ingest_seeded.py
  run_step ingest_cve_pair.py          ingest_cve_pair.py
  run_step test_cve_pair_validation.py test_cve_pair_validation.py
  run_step ingest_temporal.py          ingest_temporal.py
  run_step ingest_truth.py             ingest_truth.py
  run_step ingest_m2_stratum.py        ingest_m2_stratum.py
  run_step ingest_design.py            ingest_design.py
  run_step ingest_coverage.py          ingest_coverage.py
  run_step ingest_baseline.py          ingest_baseline.py
  run_step ingest_budget.py            ingest_budget.py
  run_step ingest_multiclass.py        ingest_multiclass.py
  if ! "$PYBIN" make_diagrams.py >/dev/null 2>&1; then
    echo "  [WARN] make_diagrams.py (figures) exited non-zero"
  fi
  popd >/dev/null
  if [ "$step_failed" != "0" ]; then
    echo "  [FAIL] at least one generation step failed; see above." >&2
    rm -rf "$TMP"
    return 1
  fi

  echo "  [cmp] regenerated outputs vs provenance/OUTPUTS_SHA256.json"
  bad=0
  # 回信数字必须在**重新生成后的**宏上再核一次（承诺的是"对着制品核过"）
  if [ -f "$TMP/03_论文撰写/response_to_reviewers/check_letter_numbers.py" ]; then
    if ( cd "$TMP/03_论文撰写/response_to_reviewers" && "$PYBIN" check_letter_numbers.py ); then
      echo "  [PASS] response letter numbers match the regenerated generator output"
    else
      echo "  [FAIL] check_letter_numbers.py (letter numbers drifted after regeneration)"
      bad=$((bad+1))
    fi
  else
    echo "  [FAIL] missing check_letter_numbers.py in the staged tree"
    bad=$((bad+1))
  fi
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
