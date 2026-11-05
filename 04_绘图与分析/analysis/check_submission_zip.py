#!/usr/bin/env python3
"""Verify (or record) the LaTeX source package against the manuscript tree.

Why this exists: `latex_source_files_submission.zip` is a *derived* file. It is
built by `make_submission_zip.py` from the working tree plus the build
directory's `main.bbl`, it is committed, and it is what a reader who downloads
the archive actually builds. Two failure modes had no check:

  (a) the package was rebuilt from older sources (it once carried a 309-word
      abstract and a Data-availability pointer to the previous archive tag while
      the tree already had the final text), and
  (b) nothing tied the package's bytes to the tree at all, so a stale package
      could sit inside a tag whose `main.tex` was correct.

This script closes both: it hashes the package, and it compares **every entry**
against the tree file it is supposed to be a copy of. `--write` refreshes
`provenance/SUBMISSION_SOURCE_SHA256.json`; without it the script only verifies
and exits non-zero on any drift.

Usage (from the repo root):

    python 04_绘图与分析/analysis/check_submission_zip.py --write   # record
    python 04_绘图与分析/analysis/check_submission_zip.py           # verify

`--root` and `--manifest` let `verify_artifact.sh repro` run the same check
inside a staged copy; `--skip-external` keeps it usable where the TeX build
directory does not exist.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

REL_ZIP = "03_论文撰写/paper/latex_source_files_submission.zip"
REL_MANIFEST = "04_绘图与分析/provenance/SUBMISSION_SOURCE_SHA256.json"
REL_PAPER = "03_论文撰写/paper"
REL_RESULTS = "04_绘图与分析/results"
REL_FIGS = "04_绘图与分析/figures"

DEFAULT_BUILD = Path(
    os.environ.get("IEEE_BUILD_DIR", r"C:/Users/Administrator/WorkBuddy/ieee_access_build")
)

# Entries that do not come from a file in the tree.
EXTERNAL = {"main.bbl": "TeX build artefact (bibtex output, not tracked)"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_source(name: str, root: Path) -> Path | None:
    if name in EXTERNAL:
        return None
    candidates = []
    if name.startswith("sections/"):
        candidates.append(root / REL_PAPER / name)
    elif name.startswith("figures/"):
        candidates.append(root / REL_FIGS / name.split("/", 1)[1])
    elif name in ("main.tex", "refs.bib"):
        candidates.append(root / REL_PAPER / name)
    elif name.endswith((".png", ".pfb", ".tfm", ".fd", ".map", ".cls", ".bst", ".sty")):
        candidates.append(root / REL_PAPER / "ieeeaccess" / name)
        candidates.append(root / REL_PAPER / name)
    else:  # generated table / number macro
        candidates.append(root / REL_RESULTS / name)
        candidates.append(root / REL_PAPER / name)
    for c in candidates:
        if c.is_file():
            return c
    return None


def abstract_counts(main_tex: str) -> tuple[int, int]:
    """(whitespace tokens, count with '---' treated as a separator).

    Both are reported because they answer different questions: the first is what
    a word processor or PDF text extraction counts (an em dash joins two words
    without a space, so it stays inside one token); the second is the strictest
    reading. IEEE Access asks for 150--250 words, so both bounds matter.
    """
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", main_tex, re.S)
    if not m:
        raise SystemExit("no abstract environment found in main.tex")
    ab = m.group(1)
    tight = len(ab.split())
    loose = len(re.sub(r"\s+", " ", ab.replace("---", " ")).strip().split())
    return tight, loose


def build(root: Path, skip_external: bool) -> tuple[dict, list[str]]:
    zpath = root / REL_ZIP
    if not zpath.is_file():
        raise SystemExit(f"missing source package: {zpath}")
    raw = zpath.read_bytes()
    zf = zipfile.ZipFile(io.BytesIO(raw))

    entries, problems = [], []
    for info in sorted(zf.infolist(), key=lambda i: i.filename):
        data = zf.read(info.filename)
        rec = {"name": info.filename, "sha256": sha(data), "bytes": len(data)}
        src = resolve_source(info.filename, root)
        if info.filename in EXTERNAL:
            rec["source"] = None
            rec["note"] = EXTERNAL[info.filename]
            ext = DEFAULT_BUILD / info.filename
            rec["external_path"] = str(ext)
            if ext.is_file():
                rec["external_sha256"] = sha_file(ext)
                if rec["external_sha256"] != rec["sha256"]:
                    problems.append(
                        f"main.bbl in the package differs from the current build "
                        f"output ({rec['sha256'][:12]} vs {rec['external_sha256'][:12]}); "
                        f"rebuild the paper and regenerate the package"
                    )
            elif not skip_external:
                print(f"  [note] no build directory at {DEFAULT_BUILD}; "
                      f"main.bbl checked against the recorded hash only")
        else:
            if src is None:
                problems.append(f"no tree file found for archive entry {info.filename}")
                rec["source"] = None
            else:
                rel = src.relative_to(root).as_posix() if str(src).startswith(str(root)) else str(src)
                rec["source"] = rel
                on_disk = sha_file(src)
                if on_disk != rec["sha256"]:
                    problems.append(
                        f"{info.filename}: archive {rec['sha256'][:12]} != tree {on_disk[:12]} ({rel})"
                    )
        entries.append(rec)

    main_tex = (root / REL_PAPER / "main.tex").read_text(encoding="utf-8", errors="ignore")
    tight, loose = abstract_counts(main_tex)

    # The pinned archive tag must match the one the statement names, and it must
    # be *inside* the package too (that is what a reader builds).
    decl = zf.read("sections/10_declarations.tex").decode("utf-8", "ignore") if \
        "sections/10_declarations.tex" in zf.namelist() else ""
    pins = sorted(set(re.findall(r"tag \\texttt\{(access-resubmission-v\d+)\}", decl)))
    tree_pins = sorted(set(re.findall(
        r"tag \\texttt\{(access-resubmission-v\d+)\}",
        (root / REL_PAPER / "sections" / "10_declarations.tex").read_text(encoding="utf-8"))))
    if pins != tree_pins:
        problems.append(f"archive declaration pins {pins}, tree pins {tree_pins}")
    if len(pins) != 1:
        problems.append(f"expected exactly one pinned tag in the declaration, found {pins}")

    manifest = {
        "generated_by": "check_submission_zip.py --write",
        "purpose": (
            "Byte-level binding between the packaged LaTeX sources and the manuscript tree. "
            "Every 'entries' row gives the archive entry, the tree file it must equal, and "
            "the SHA-256 of both the archived bytes and that file; the check fails if any "
            "pair drifts apart, so a package built from older sources cannot ride inside a "
            "tag whose sources are newer."
        ),
        "zip": {
            "path": REL_ZIP,
            "sha256": sha(raw),
            "bytes": len(raw),
            "entries": len(entries),
        },
        "abstract": {
            "source": f"{REL_PAPER}/main.tex",
            "words_whitespace_split": tight,
            "words_em_dash_split": loose,
            "note": (
                "IEEE Access asks for 150-250 words. The first figure is what a word "
                "processor counts ('model---a' is one token); the second treats each of the "
                "em dashes as a separator and is the strictest reading. Both are reported so "
                "neither bound is asserted from a single convention."
            ),
        },
        "pinned_archive_tag": {
            "file": "sections/10_declarations.tex",
            "tag": pins[0] if len(pins) == 1 else None,
        },
        "entries": entries,
    }
    return manifest, problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--skip-external", action="store_true")
    a = ap.parse_args()

    root = Path(a.root).resolve() if a.root else Path(__file__).resolve().parents[2]
    mpath = Path(a.manifest) if a.manifest else root / REL_MANIFEST

    manifest, problems = build(root, a.skip_external)

    if a.write:
        if problems:
            for p in problems:
                print(f"  [FAIL] {p}", file=sys.stderr)
            print("refusing to write a manifest over a package that does not match the tree",
                  file=sys.stderr)
            return 1
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
        z = manifest["zip"]
        print(f"[ok] {mpath}")
        print(f"     {z['entries']} entries ; {z['bytes']} bytes ; sha256={z['sha256'][:16]}")
        print(f"     abstract {manifest['abstract']['words_whitespace_split']} words "
              f"({manifest['abstract']['words_em_dash_split']} with em dashes split) ; "
              f"pins {manifest['pinned_archive_tag']['tag']}")
        return 0

    if not mpath.is_file():
        print(f"[FAIL] manifest missing: {mpath} (run with --write)", file=sys.stderr)
        return 1
    rec = json.loads(mpath.read_text(encoding="utf-8"))

    fails = list(problems)
    z = rec["zip"]
    if z["sha256"] != manifest["zip"]["sha256"]:
        fails.append(f"package sha256 {manifest['zip']['sha256'][:12]} != recorded {z['sha256'][:12]}")
    if z["bytes"] != manifest["zip"]["bytes"]:
        fails.append(f"package size {manifest['zip']['bytes']} != recorded {z['bytes']}")
    if z["entries"] != manifest["zip"]["entries"]:
        fails.append(f"package has {manifest['zip']['entries']} entries, recorded {z['entries']}")
    for key in ("words_whitespace_split", "words_em_dash_split"):
        if rec["abstract"][key] != manifest["abstract"][key]:
            fails.append(f"abstract {key}: {manifest['abstract'][key]} != recorded {rec['abstract'][key]}")
    if rec["pinned_archive_tag"]["tag"] != manifest["pinned_archive_tag"]["tag"]:
        fails.append(f"pinned tag {manifest['pinned_archive_tag']['tag']} != recorded "
                     f"{rec['pinned_archive_tag']['tag']}")

    for f in fails:
        print(f"  [FAIL] {f}")
    if fails:
        return 1
    print(f"  [PASS] source package matches the tree byte-for-byte "
          f"({z['entries']} entries, sha256 {z['sha256'][:12]})")
    print(f"  [PASS] abstract {manifest['abstract']['words_whitespace_split']} words "
          f"({manifest['abstract']['words_em_dash_split']} with em dashes split); "
          f"declaration pins {manifest['pinned_archive_tag']['tag']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
