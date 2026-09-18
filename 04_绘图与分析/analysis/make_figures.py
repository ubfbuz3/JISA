"""
出版级矢量图生成 · 全部图形由真实数据确定性生成
================================================
硬规则（项目约束，违者图不可用）:
  1. **禁止任何图像生成模型介入像素级**。所有图由 matplotlib 直接绘制矢量元素，
     或由 figure-spec 的确定性 JSON→SVG 渲染器生成。无 AI 生成位图。
  2. 所有数值**从 results/metrics.json 读取**，脚本内不得出现手写数字常量（除坐标/样式）。
  3. 导出 pdf + svg + png 三种格式；pdf/eps 用 Type42 字体（无 Type3 位图字体）。
  4. 全局禁用 alpha（legend.framealpha=1.0，颜色一律预混成实色），
     以免 PDF 与 EPS 视觉分叉。
  5. 去时间戳，保证同一数据两次运行 **逐字节一致**。

用法: python make_figures.py
输出: ../figures/fig*.{pdf,svg,png} 与 ../provenance/FIGURES_PROVENANCE.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
FIG = BASE / "figures"
PROV = BASE / "provenance"
FIG.mkdir(parents=True, exist_ok=True)
PROV.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---- 全局样式：无 alpha、嵌入 TrueType、无时间戳 -------------------------
matplotlib.rcParams.update({
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "ps.useafm": False,
    "legend.framealpha": 1.0,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "font.size": 8.5,
    "axes.titlesize": 9,
    "axes.labelsize": 8.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.linestyle": ":",
    "grid.linewidth": 0.6,
    "svg.hashsalt": "bola-tse-2026",          # SVG 确定性
})

C = {                                          # 印刷安全、灰度可辨
    "tp": "#3B6FB6", "fp": "#B6453C", "fn": "#C98A3C", "tn": "#BFBFBF",
    "v1": "#8C8C8C", "v2": "#6B8E9E", "v3": "#3B6FB6", "deg": "#C9C9C9",
    "do": "#7A5CA8",
    "ok": "#4E8A5B", "bad": "#B6453C", "warn": "#C98A3C", "neutral": "#7A7A7A",
}


def solid(hexcolor: str, alpha: float, bg: str = "#ffffff") -> str:
    """把 alpha 预混成不透明实色（PS 后端不支持透明）。"""
    f, b = to_rgb(hexcolor), to_rgb(bg)
    return "#%02x%02x%02x" % tuple(
        int(round(255 * (alpha * x + (1 - alpha) * y))) for x, y in zip(f, b))


GRID = solid("#b0b0b0", 0.30)
matplotlib.rcParams["grid.color"] = GRID


def save(fig, stem: str, provenance: dict):
    """三格式导出 + 去时间戳 + 记录哈希。"""
    made = {}
    for ext in ("pdf", "svg", "png"):
        p = FIG / f"{stem}.{ext}"
        if ext == "png":
            fig.savefig(p, metadata={"Software": None})
        elif ext == "svg":
            fig.savefig(p)                                    # SVG 写入器不接受自定义键
        else:
            fig.savefig(p, metadata={"CreationDate": None, "Software": None})
        data = p.read_bytes()
        if ext == "svg":
            # 去掉时间戳与随机 id，保证逐字节可复现
            txt = data.decode("utf-8")
            txt = re.sub(r"<dc:date>[^<]*</dc:date>", "<dc:date></dc:date>", txt)
            txt = re.sub(r"<!--[^>]*-->", "", txt)
            txt = re.sub(r"\bid=\"[a-zA-Z0-9]{8,}\"", 'id=""', txt)
            data = txt.encode("utf-8")
            p.write_bytes(data)
        made[ext] = {"sha256": hashlib.sha256(data).hexdigest()[:16],
                     "bytes": len(data)}
    plt.close(fig)
    provenance[stem] = made
    print(f"  [fig] {stem}: " + " ".join(f"{k}({v['bytes']}B)" for k, v in made.items()))


# ============================================================ 图 2

def fig2_methods(M, prov):
    """端到端混淆矩阵对照（Block 9）。"""
    meth = M["block9_direct_observe"]["methods"]
    order = ["degrade_all", "direct_only", "v3", "direct_observe", "v1", "v2"]
    nice = {"degrade_all": "degrade-all\n(abstain)", "direct_only": "direct-only\n(oracle only)",
            "v3": "v3\n(MR + oracle)", "direct_observe": "direct-observe\n(request + oracle)",
            "v1": "v1\n(bookkeeping)", "v2": "v2\n(bookkeeping+)"}
    fig, ax = plt.subplots(figsize=(7.0, 3.1))
    xs = range(len(order))
    w = 0.26
    for i, (k, c, lab) in enumerate((("TP", C["tp"], "TP (true violations caught)"),
                                     ("FP", C["fp"], "FP (false proofs)"),
                                     ("FN", C["fn"], "FN (missed)"))):
        vals = [meth[m][k] for m in order]
        ax.bar([x + (i - 1) * w for x in xs], vals, w, color=c, label=lab,
               edgecolor="white", linewidth=0.4)
        for x, v in zip(xs, vals):
            ax.annotate(str(v), (x + (i - 1) * w, v), ha="center", va="bottom",
                        fontsize=6.4, color="#333333",
                        xytext=(0, 1), textcoords="offset points")
    for x, m in zip(xs, order):
        d = meth[m]
        f1 = "n/a" if d["f1"] is None else f"{d['f1']:.2f}"
        p = "n/a" if d["precision"] is None else f"{d['precision']:.2f}"
        r_ = "n/a" if d["recall"] is None else f"{d['recall']:.2f}"
        nice[m] = nice[m] + f"\nP={p}\nR={r_}\nF1={f1}"
    ax.set_xticks(list(xs))
    ax.set_xticklabels([nice[m] for m in order], fontsize=6.8)
    ax.set_ylabel("instances (n = 576)")
    ax.set_ylim(0, 262)
    ax.legend(loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.02))
    ax.set_title("Adjudicator comparison: the MR trigger does not carry the work "
                 "(Block 9, synthetic matrix)", pad=16)
    fig.tight_layout()
    save(fig, "fig4_methods", prov)


# ============================================================ 图 3

def fig3_strata(M, prov):
    """v3 按授权自省面可读性分层（Block 8）。"""
    on, off = M["block8_introspection_boundary"]["on"], M["block8_introspection_boundary"]["off"]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.6))
    labels = [f"introspection\nreadable\n(abstain n={on['v3_abstain_unavailable_n']})",
              f"introspection\nabsent\n(abstain n={off['v3_abstain_unavailable_n']})"]
    a = axes[0]
    x = range(2)
    w = 0.36
    a.bar([i - w / 2 for i in x], [on["v2_false_proof_rate"], off["v2_false_proof_rate"]],
          w, color=C["v2"], label="v2 (bookkeeping oracle)", edgecolor="white", linewidth=0.4)
    a.bar([i + w / 2 for i in x], [on["v3_false_proof_rate"], off["v3_false_proof_rate"]],
          w, color=C["v3"], label="v3 (SUT introspection)", edgecolor="white", linewidth=0.4)
    for i, v in zip(x, [on["v2_false_proof_rate"], off["v2_false_proof_rate"]]):
        a.annotate(f"{v:.2f}", (i - w / 2, v), ha="center", va="bottom", fontsize=6.8)
    for i, v in zip(x, [on["v3_false_proof_rate"], off["v3_false_proof_rate"]]):
        a.annotate(f"{v:.2f}", (i + w / 2, v), ha="center", va="bottom", fontsize=6.8)
    a.set_xticks(list(x)); a.set_xticklabels(labels)
    a.set_ylim(0, 1.15); a.set_ylabel("false-proof rate\n(on real false alarms)")
    a.set_title("(a) false proofs", fontsize=8.5)
    a.legend(loc="upper right", frameon=False)

    b = axes[1]
    keep = [on["v3_detection_keep_rate"], off["v3_detection_keep_rate"]]
    b.bar(list(x), keep, 0.5, color=[C["ok"], C["bad"]], edgecolor="white", linewidth=0.4)
    for i, v in enumerate(keep):
        b.annotate(f"{v:.2f}", (i, v), ha="center", va="bottom", fontsize=7)
    b.set_xticks(list(x)); b.set_xticklabels(labels, fontsize=6.8)
    b.set_ylim(0, 1.28); b.set_ylabel("v3 detection-keep rate")
    b.set_title("(b) detection retained by v3", fontsize=8.5)
    fig.suptitle("Admissibility condition is measurable: false proofs vanish only while "
                 "the introspection face is readable", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    save(fig, "fig3_strata", prov)


# ============================================================ 图 4

def fig4_scenarios(M, prov):
    """逐场景错误构成：v2（账本 oracle）vs v3（自省面）。"""
    import collections
    # 从 metrics.json 的 per-scenario 无法直接取得（只存了总量），故由 block9 的原始记录口径重算
    per = M["_per_scenario_v2v3"]
    scen = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.5), sharey=True)
    for ax, meth, title in ((axes[0], "v2", "(a) v2: bookkeeping oracle"),
                            (axes[1], "v3", "(b) v3: SUT introspection")):
        fp = [per[meth].get(s, {}).get("FP", 0) for s in scen]
        fn = [per[meth].get(s, {}).get("FN", 0) for s in scen]
        x = range(len(scen))
        ax.bar([i - 0.19 for i in x], fp, 0.38, color=C["fp"], label="FP", edgecolor="white", linewidth=0.4)
        ax.bar([i + 0.19 for i in x], fn, 0.38, color=C["fn"], label="FN", edgecolor="white", linewidth=0.4)
        for i, v in zip(x, fp):
            if v:
                ax.annotate(str(v), (i - 0.19, v), ha="center", va="bottom", fontsize=6.2)
        for i, v in zip(x, fn):
            if v:
                ax.annotate(str(v), (i + 0.19, v), ha="center", va="bottom", fontsize=6.2)
        ax.set_xticks(list(x)); ax.set_xticklabels(scen, fontsize=7)
        ax.set_title(title, fontsize=8.5)
        ax.legend(frameon=False, loc="upper left")
    axes[0].set_ylabel("error instances")
    axes[0].set_ylim(0, 70)
    axes[1].annotate("S6 = legitimate out-of-band grant\n(single-sided boundary)",
                     (5.15, 34), fontsize=6.2, color="#555555", ha="right")
    fig.suptitle("Errors are scenario-structured: bookkeeping-oracle FPs concentrate on legitimate "
                 "out-of-band grants (S6)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    save(fig, "fig2_scenarios", prov)


# ============================================================ 图 5

def fig5_real(M, prov):
    """真实系统（Gitea 1.22.6）四面板。"""
    r = M["real_system"]
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.35))

    a = axes[0]
    m1 = r["M1_grant_endpoints"]
    vals = [m1["swagger_total_paths"], m1["grant_endpoints_total"], m1["without_site_admin"]]
    labs = ["all API\npaths", "grant\nendpoints", "grantable\nw/o admin"]
    a.bar(range(3), vals, 0.55, color=[C["neutral"], C["tp"], C["warn"]],
          edgecolor="white", linewidth=0.4)
    for i, v in zip(range(3), vals):
        a.annotate(str(v), (i, v), ha="center", va="bottom", fontsize=7)
    a.set_xticks(range(3)); a.set_xticklabels(labs, fontsize=6.6)
    a.set_title("(a) grant-API space", fontsize=8.5)
    a.set_ylim(0, 285)

    b = axes[1]
    m2 = r["M2_readability"]
    vals = [m2["owner_admin_readable"], m2["blackbox_self_readable"]]
    dens = [m2["owner_admin_total"], m2["blackbox_self_cells"]]
    b.bar([0, 1], vals, 0.55, color=[C["ok"], C["bad"]], edgecolor="white", linewidth=0.4)
    for i, (v, d) in enumerate(zip(vals, dens)):
        b.annotate(f"{v}/{d}", (i, v), ha="center", va="bottom", fontsize=7)
    b.set_xticks([0, 1])
    b.set_xticklabels(["owner /\nadmin vantage", "black-box\nsubject vantage"], fontsize=6.6)
    b.set_title("(b) oracle readability", fontsize=8.5)
    b.set_ylim(0, max(dens) * 1.25)

    c = axes[2]
    m4 = r["M4_snapshot_mismatch"]
    vals = [m4["snapshot"], m4["live"]]
    c.bar([0, 1], vals, 0.55, color=[C["bad"], C["tn"]], edgecolor="white", linewidth=0.4)
    for i, v in enumerate(vals):
        c.annotate(f"{v}/{m4['denominator']}", (i, v), ha="center", va="bottom", fontsize=7)
    c.set_xticks([0, 1])
    c.set_xticklabels(["crawl-time\nsnapshot", "live\nenumeration"], fontsize=6.6)
    c.set_title("(c) GUI-model mismatch", fontsize=8.5)
    c.set_ylim(0, m4["denominator"] * 0.42)

    d = axes[3]
    mm = r["M5_methods"]
    keys = ["mr_bookkeeping", "v3", "v3_self", "direct_only", "direct_observe"]
    labs = ["MR\nbookk.", "v3", "v3\nself", "dir.\nonly", "dir.\nobs."]
    fp = [mm[k]["false_proofs_snapshot"] for k in keys]
    al = [mm[k]["alarms_snapshot"] for k in keys]
    x = range(len(keys))
    d.bar([i - 0.19 for i in x], al, 0.38, color=C["tn"], label="alarms", edgecolor="white", linewidth=0.4)
    d.bar([i + 0.19 for i in x], fp, 0.38, color=C["fp"], label="false proofs", edgecolor="white", linewidth=0.4)
    for i, v in zip(x, fp):
        d.annotate(str(v), (i + 0.19, v), ha="center", va="bottom", fontsize=6.2)
    d.set_xticks(list(x)); d.set_xticklabels(labs, fontsize=6.6)
    d.set_title("(d) alarms vs false proofs", fontsize=8.5)
    d.legend(frameon=False, loc="upper right")
    d.set_ylim(0, max(al) * 1.45)

    fig.suptitle("Real system (Gitea 1.22.6): the failure is temporal and the oracle is "
                 "privilege-gated", fontsize=9, y=1.06)
    fig.tight_layout()
    save(fig, "fig5_real_system", prov)


# ============================================================ 图 6（内生对照）

def fig6_endogenous(M, prov):
    """内生对照：同可见性、不同变更时点。"""
    r = M["real_system"]["endogenous_control"]
    keys = ["public_from_start", "public_after_crawl"]
    labs = ["public from crawl\n(alice/pub1)", "public after crawl\n(alice/r4)"]
    reach = [r[k]["cannotReach_true"] for k in keys]
    denom = [r[k]["cells"] for k in keys]
    fires = [r[k]["mr_fires"] for k in keys]
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    x = range(2)
    ax.bar([i - 0.21 for i in x], reach, 0.34, color=C["warn"],
           label="GUI-unreachable\n(but authorized)", edgecolor="white", linewidth=0.4)
    ax.bar([i + 0.21 for i in x], fires, 0.34, color=C["fp"], label="MR fires",
           edgecolor="white", linewidth=0.4)
    for i, (v, d) in enumerate(zip(reach, denom)):
        ax.annotate(f"{v}/{d}", (i - 0.21, v), ha="center", va="bottom", fontsize=7)
    for i, v in zip(x, fires):
        ax.annotate(str(v), (i + 0.21, v), ha="center", va="bottom", fontsize=7)
    ax.set_xticks(list(x)); ax.set_xticklabels(labs, fontsize=7)
    ax.set_ylim(0, 7.2)
    ax.set_ylabel("cells (n = 6 per object)")
    ax.legend(frameon=False, loc="upper left", fontsize=6.4)
    ax.set_title("Identical final visibility, different change time:\n"
                 "the failure is temporal, not about visibility", fontsize=8)
    fig.tight_layout()
    save(fig, "fig6_endogenous_control", prov)


# ============================================================ 主流程

def main():
    M = json.loads((BASE / "results" / "metrics.json").read_text(encoding="utf-8"))
    M["_per_scenario_v2v3"] = load_per_scenario()
    prov: dict = {"_inputs": {}, "_rule": (
        "所有数据点来自 metrics.json 与其上游真实运行记录；"
        "图形为 matplotlib 矢量绘制或 figure-spec 确定性 SVG，"
        "**无任何图像生成模型参与像素**。")}
    for name, p in (("experiments/results/raw_matrix.jsonl", None),
                    ("experiments/results/ablation_direct_observe.json", None),
                    ("experiments/real_system/results/real_system.json", None)):
        fp = BASE.parent / name
        if fp.exists():
            prov["_inputs"][name] = hashlib.sha256(fp.read_bytes()).hexdigest()[:16]

    fig2_methods(M, prov)
    fig3_strata(M, prov)
    fig4_scenarios(M, prov)
    fig5_real(M, prov)
    fig6_endogenous(M, prov)

    (PROV / "FIGURES_PROVENANCE.json").write_text(
        json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] {PROV/'FIGURES_PROVENANCE.json'}")


def load_per_scenario():
    """从原始记录重算 v2/v3 的逐场景 FP/FN —— 与 ablate 脚本同一口径。"""
    import collections
    root = BASE.parent
    recs = [json.loads(l) for l in (root / "experiments/results/raw_matrix.jsonl")
            .open(encoding="utf-8") if l.strip()]
    out = {m: collections.defaultdict(lambda: collections.defaultdict(int)) for m in ("v2", "v3")}
    for r in recs:
        t = r["truth"]["truth"]
        sc = r["scenario"]
        for m in ("v2", "v3"):
            alarm = r["verdicts"][m]["verdict"] == "violation-proven"
            cell = ("TP" if alarm else "FN") if t == "bola" else ("FP" if alarm else "TN")
            out[m][sc][cell] += 1
    return {m: {s: dict(d) for s, d in out[m].items()} for m in out}


if __name__ == "__main__":
    main()
