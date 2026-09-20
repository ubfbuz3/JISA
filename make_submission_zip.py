#!/usr/bin/env python3
"""Package the JISA submission LaTeX source files into a single zip.

Deterministic: entries are sorted and given a fixed timestamp so the archive
is byte-stable across runs on the same content. Run from the project root:

    python make_submission_zip.py

Reads the *current working tree* (not the build dir) for paper sources and
result macros, and the compiled .bbl from the build dir. Writes:

    03_论文撰写/paper/latex_source_files_submission.zip
"""
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPER = ROOT / "03_论文撰写" / "paper"
RESULTS = ROOT / "04_绘图与分析" / "results"
FIGURES = ROOT / "04_绘图与分析" / "figures"
BUILD = Path("C:/Users/Administrator/WorkBuddy/jisa_paper_build")
OUT = PAPER / "latex_source_files_submission.zip"

# Fixed timestamp for reproducible archives (2026-09-21 00:00:00).
FIXED_DATE = (2026, 9, 21, 0, 0, 0)

SECTIONS = sorted(p.name for p in (PAPER / "sections").glob("*.tex"))
RESULT_TEX = [
    "numbers.tex",
    "native_engine_numbers.tex",
    "native_engine_table.tex",
    "gogs_numbers.tex",
    "gogs_cross_table.tex",
    "gitlab_numbers.tex",
    "seeded_table.tex",
    "m2_stratum.tex",
]
# Only ship the figure PDFs the manuscript actually \includegraphics{...}es, so
# the package cannot carry orphaned (or superseded) artwork. Extracted from the
# sources, never hand-maintained.
_INCLUDE = re.compile(r"\\includegraphics\s*\[[^\]]*\]\s*\{([^}]+)\}")


def referenced_figures() -> list[str]:
    sources = [PAPER / "main.tex"] + sorted((PAPER / "sections").glob("*.tex"))
    names: set[str] = set()
    for src in sources:
        for m in _INCLUDE.finditer(src.read_text(encoding="utf-8", errors="ignore")):
            n = m.group(1).strip()
            if n.lower().endswith(".pdf"):
                names.add(n)
    for n in sorted(names):
        if not (FIGURES / n).is_file():
            raise SystemExit(f"referenced figure not found: {FIGURES / n}")
    return sorted(names)


FIG_PDF = referenced_figures()
THUMBS = sorted(p.name for p in (PAPER / "thumbnails").glob("*.jpeg"))


def collect() -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = []

    def add(arc: str, src: Path) -> None:
        if not src.is_file():
            print(f"  MISSING {src}", file=sys.stderr)
            raise SystemExit(f"required file missing: {src}")
        items.append((arc, src))

    add("main.tex", PAPER / "main.tex")
    add("main.bbl", BUILD / "main.bbl")
    add("refs.bib", PAPER / "refs.bib")
    for n in RESULT_TEX:
        add(n, RESULTS / n)
    for n in ("cas-dc.cls", "cas-common.sty", "cas-model2-names.bst"):
        add(n, PAPER / n)
    for n in SECTIONS:
        add(f"sections/{n}", PAPER / "sections" / n)
    for n in FIG_PDF:
        add(f"figures/{n}", FIGURES / n)
    for n in THUMBS:
        add(f"thumbnails/{n}", PAPER / "thumbnails" / n)
    return items


def main() -> None:
    items = collect()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for arc, src in sorted(items, key=lambda t: t[0]):
            zi = zipfile.ZipInfo(arc, date_time=FIXED_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zf.writestr(zi, src.read_bytes())
    data = OUT.read_bytes()
    print(f"[ok] {OUT}")
    print(f"     {len(items)} files ; {len(data)} bytes ; sha256={hashlib.sha256(data).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
