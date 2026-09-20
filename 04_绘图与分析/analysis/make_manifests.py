#!/usr/bin/env python
# =====================================================================
# make_manifests.py
#   (Re)compute the SHA-256 checksums of (a) every raw record the paper
#   reproduction pipeline consumes and (b) every byte-reproducible output
#   it emits, and write them to provenance/*.json.
#
#   These manifests are the reference the one-command self-check
#   (verify_artifact.sh) compares against.  Re-run this script ONLY after
#   a *legitimate* change to the raw records or to a generation script;
#   commit the refreshed manifest together with that change so the
#   self-check stays meaningful.
#
#   Usage:  python make_manifests.py
#   Deps:   stdlib only.
# =====================================================================
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # .../3区论文
PROV = ROOT / "04_绘图与分析" / "provenance"
PROV.mkdir(parents=True, exist_ok=True)

# --- (a) raw records consumed by the pipeline (input integrity) ----------
# compute_all.py  (RES = experiments/results)
RAW_INPUTS = [
    "experiments/results/raw_matrix.jsonl",
    "experiments/results/ablation_direct.json",
    "experiments/results/ablation_direct_observe.json",
    "experiments/results/alt_matrix.jsonl",
    # compute_all.py  (REAL = experiments/real_system/results)
    "experiments/real_system/results/real_system.json",
    # ingest_native_engine.py  (ENGINE_RESULTS = experiments/native_engine/results)
    "experiments/native_engine/results/native_engine.json",
    "experiments/native_engine/results/seedcheck.json",
    "experiments/native_engine/results/channel_bytes.json",
    # ingest_gogs.py / ingest_gitlab.py / ingest_seeded.py
    #   (RS = experiments/real_system/results)
    "experiments/real_system/results/gogs_real_system.json",
    "experiments/real_system/results/m1_matched_gitea.json",
    "experiments/real_system/results/gitlab_real_system.json",
    "experiments/real_system/results/seeded.json",
]

# --- (b) byte-reproducible outputs the pipeline emits (output integrity) -
# All number-bearing .tex tables + the machine-readable summary, plus the
# two reportlab-invariant vector diagrams (see ARTIFACT.md §2).
REPRO_OUTPUTS = [
    "04_绘图与分析/results/numbers.tex",
    "04_绘图与分析/results/native_engine_numbers.tex",
    "04_绘图与分析/results/native_engine_table.tex",
    "04_绘图与分析/results/gogs_numbers.tex",
    "04_绘图与分析/results/gogs_cross_table.tex",
    "04_绘图与分析/results/gitlab_numbers.tex",
    "04_绘图与分析/results/seeded_table.tex",
    "04_绘图与分析/results/metrics.json",
    "04_绘图与分析/figures/fig1_protocol.pdf",
    "04_绘图与分析/figures/fig7_boundaries.pdf",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def build(group: str, rel_paths) -> dict:
    files = []
    missing = []
    for rel in rel_paths:
        p = ROOT / rel
        if not p.is_file():
            missing.append(rel)
            continue
        files.append({
            "path": rel,
            "sha256": sha256_of(p),
            "bytes": p.stat().st_size,
        })
    if missing:
        sys.exit(f"[make_manifests] MISSING {len(missing)} file(s):\n  "
                 + "\n  ".join(missing))
    return {"generated_by": "make_manifests.py", "files": files}


def main() -> None:
    raw = build("raw", RAW_INPUTS)
    out = build("output", REPRO_OUTPUTS)
    (PROV / "RAW_RECORDS_SHA256.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (PROV / "OUTPUTS_SHA256.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[ok] {len(raw['files'])} raw records -> "
          f"{PROV / 'RAW_RECORDS_SHA256.json'}")
    print(f"[ok] {len(out['files'])} reproducible outputs -> "
          f"{PROV / 'OUTPUTS_SHA256.json'}")


if __name__ == "__main__":
    main()
