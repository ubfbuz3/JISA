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
# Explicit for the files that existed before; the temporal directory is globbed
# so that a new run cannot enter the pipeline without entering the manifest.
RAW_INPUTS = [
    "experiments/results/raw_matrix.jsonl",
    "experiments/results/ablation_direct.json",
    "experiments/results/ablation_direct_observe.json",
    "experiments/results/alt_matrix.jsonl",
    "experiments/results/sanity_matrix.jsonl",
    # compute_all.py  (REAL = experiments/real_system/results)
    "experiments/real_system/results/real_system.json",
    # ingest_native_engine.py  (ENGINE_RESULTS = experiments/native_engine/results)
    "experiments/native_engine/results/native_engine.json",
    "experiments/native_engine/results/seedcheck.json",
    "experiments/native_engine/results/channel_bytes.json",
    # ingest_gogs.py / ingest_gitlab.py / ingest_seeded.py
    #   (RS = experiments/real_system/results)
    "experiments/real_system/results/gogs_real_system.json",
    "experiments/real_system/results/gogs_api_surface.json",
    "experiments/real_system/results/m1_matched_gitea.json",
    "experiments/real_system/results/gitlab_real_system.json",
    "experiments/real_system/results/seeded.json",
    # ingest_cve_pair.py
    "experiments/real_system/results/cve_pair.json",
    # protocol and its amendments: the digests the run records bind
    "experiments/real_system/c_protocol.json",
    "experiments/real_system/c_protocol_amendment_a1.json",
    "experiments/real_system/c_protocol_amendment_a2.json",
    # ingest_temporal.py  (the reported run and the archived pilot)
    "experiments/real_system/results/temporal/temporal_gitea.json",
    "experiments/real_system/results/temporal/temporal_gitlab.json",
    "experiments/real_system/results/temporal/pilot_cascade/temporal_gitlab_pilot.json",
    # ingest_baseline.py  (R1.7 competitive baseline: 42 controlled cells)
    "experiments/results/baseline_compare.json",
]

# --- (b) byte-reproducible outputs the pipeline emits (output integrity) -
# Every .tex under results/ is generated, so it is globbed rather than listed:
# a hand-maintained list is exactly how the earlier manifest went stale. Each
# file is checked for the generator header before it is admitted.
REPRO_OUTPUTS = []   # filled in main() from the glob below
EXTRA_OUTPUTS = [
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


def _generated_outputs():
    res = ROOT / "04_绘图与分析" / "results"
    files = []
    for p in sorted(res.glob("*.tex")):
        head = p.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
        if not head or not ("生成" in head[0] or "来源" in head[0]):
            sys.exit(f"[make_manifests] {p.name} has no generator header; "
                     "refusing to certify an unclassified file")
        files.append(str(p.relative_to(ROOT)))
    return files + EXTRA_OUTPUTS


def main() -> None:
    raw = build("raw", RAW_INPUTS)
    out = build("output", _generated_outputs())
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
