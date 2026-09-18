"""
确定性示意图（figure-spec JSON → SVG → PDF）
=============================================
规则:
  * 图形由 **确定性 JSON 渲染器** 生成，无任何图像生成模型参与像素。
  * SVG 为矢量可编辑源，PDF 供 LaTeX 直接 \\includegraphics。
  * 同一 spec 两次渲染必须逐字节一致。

工具链: figure_renderer.py (SVG) → svglib/reportlab (PDF)
用法  : python make_diagrams.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
FIG = BASE / "figures"
SPECS = FIG / "specs"
PROV = BASE / "provenance"
SPECS.mkdir(parents=True, exist_ok=True)

RENDERER = Path(r"C:\Users\Administrator\.workbuddy\skills\figure-spec\scripts\figure_renderer.py")
PY = sys.executable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

INK = "#2C2C2A"
BLUE, TEAL, AMBER, RED, GRAY = "#185FA5", "#0F6E56", "#854F0B", "#A32D2D", "#5F5E5A"
F_BLUE, F_TEAL, F_AMBER, F_RED, F_GRAY = "#E6F1FB", "#E1F5EE", "#FAEEDA", "#FCEBEB", "#F1EFE8"


# ------------------------------------------------------------------ 图 1
FIG1 = {
    "title": "Three-phase faithful instantiation of the metamorphic-relation protocol",
    "canvas": {"width": 900, "height": 300},
    "style": {"font_family": "DejaVu Sans, Helvetica, Arial, sans-serif",
              "font_size": 14, "bg_color": "#FFFFFF"},
    "nodes": [
        {"id": "phaseA", "label": "Phase A\nCrawl", "sublabel": "freeze the GUI-reachability model",
         "x": 135, "y": 86, "width": 190, "height": 76, "shape": "rounded",
         "fill": F_BLUE, "stroke": BLUE, "text_color": "#042C53"},
        {"id": "phaseB", "label": "Phase B\nMutate", "sublabel": "grant access out of band",
         "x": 450, "y": 86, "width": 190, "height": 76, "shape": "rounded",
         "fill": F_AMBER, "stroke": AMBER, "text_color": "#412402"},
        {"id": "phaseC", "label": "Phase C\nExecute MR", "sublabel": "evaluate predicates vs. frozen model",
         "x": 765, "y": 86, "width": 190, "height": 76, "shape": "rounded",
         "fill": F_BLUE, "stroke": BLUE, "text_color": "#042C53"},
        {"id": "outcome",
         "label": "Legitimate access granted after Phase A looks GUI-unreachable\n"
                  "→ the exception predicate is not discharged → false proof",
         "x": 450, "y": 232, "width": 800, "height": 68, "shape": "rounded",
         "fill": F_RED, "stroke": RED, "text_color": "#501313"},
    ],
    "edges": [
        {"from": "phaseA", "to": "phaseB", "label": "snapshot\nfrozen", "color": "#555555"},
        {"from": "phaseB", "to": "phaseC", "label": "authorization\nchanged", "color": "#555555"},
        {"from": "phaseC", "to": "outcome", "label": "staleness", "style": "dashed",
         "color": RED},
    ],
    "labels": [
        {"text": "predicates read crawler-recorded reachability (userCanRetrieveContent, cannotReachThroughGUI)",
         "x": 450, "y": 30, "font_size": 12, "color": GRAY, "anchor": "middle"},
    ],
}


# ------------------------------------------------------------------ 图 7
FIG7 = {
    "title": "The MR family is squeezed between two boundaries",
    "canvas": {"width": 900, "height": 300},
    "style": {"font_family": "DejaVu Sans, Helvetica, Arial, sans-serif",
              "font_size": 14, "bg_color": "#FFFFFF"},
    "nodes": [
        {"id": "left", "label": "Boundary 1: oracle readable",
         "sublabel": "a plain request with the oracle matches or beats the MR family",
         "x": 230, "y": 96, "width": 400, "height": 92, "shape": "rounded",
         "fill": F_TEAL, "stroke": TEAL, "text_color": "#04342C"},
        {"id": "right", "label": "Boundary 2: oracle absent",
         "sublabel": "MR is the only evidence, but it is a GUI-reachability proxy",
         "x": 670, "y": 96, "width": 400, "height": 92, "shape": "rounded",
         "fill": F_AMBER, "stroke": AMBER, "text_color": "#412402"},
        {"id": "banner", "label": "No regime in which the MR family is the best available method",
         "x": 450, "y": 232, "width": 860, "height": 60, "shape": "rounded",
         "fill": F_RED, "stroke": RED, "text_color": "#501313"},
    ],
    "edges": [
        {"from": "left", "to": "banner", "style": "dotted", "color": "#888780"},
        {"from": "right", "to": "banner", "style": "dotted", "color": "#888780"},
    ],
    "labels": [],
}


def render_svg(spec: dict, stem: str) -> Path:
    sp = SPECS / f"{stem}.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    out = FIG / f"{stem}.svg"
    r = subprocess.run([PY, str(RENDERER), "render", str(sp), "--output", str(out)],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"渲染失败 {stem}:\n{r.stdout}\n{r.stderr}")
    print(f"  [svg] {out.name} ({out.stat().st_size}B)")
    return out


def svg_to_pdf(svg: Path) -> Path:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    pdf = svg.with_suffix(".pdf")
    drawing = svg2rlg(str(svg))
    renderPDF.drawToFile(drawing, str(pdf), autoSize=1)
    print(f"  [pdf] {pdf.name} ({pdf.stat().st_size}B)")
    return pdf


def main():
    prov = {}
    for spec, stem in ((FIG1, "fig1_protocol"), (FIG7, "fig7_boundaries")):
        svg = render_svg(spec, stem)
        pdf = svg_to_pdf(svg)
        prov[stem] = {
            "spec": str(SPECS / f"{stem}.json"),
            "renderer": str(RENDERER),
            "svg_sha256": hashlib.sha256(svg.read_bytes()).hexdigest()[:16],
            "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()[:16],
            "pixels_generated_by_model": False,
        }
    p = PROV / "DIAGRAMS_PROVENANCE.json"
    p.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] {p}")


if __name__ == "__main__":
    main()
