"""
R1.6 · 完整因子设计、混淆检查、代表网格对账
============================================================
审稿原文（R1.6）:
    "The 576 records form a fixed enumeration, but the manuscript does not
     present a sufficiently transparent mapping from configurations and
     scenarios to all records. Please provide the complete factorial design,
     explain how each factor is varied, and demonstrate that the reported
     effects can be attributed to crawl timing, exception handling, and oracle
     readability without confounding. The earlier representative 36-record
     readable and 18-record unreadable grids should also be reconciled
     explicitly with the later 312/264-record partition."

四条要交付的东西，一一对应：
  1. 完整因子表     -> results/design_table.tex        (tab:design)
  2. 配置×情景人口普查 -> results/design_census_table.tex (tab:design-census)
  3. 三机制的配对归因 -> results/attribution_table.tex  (tab:attribution)
     配对（只在**只差一个开关**的记录之间比）才是"无混淆"的证据；
     若两机制的效应落在同一批记录上，配对表会立刻显示两个方向都有变动。
  4. 36/18 与 312/264 对账 -> results/reconcile_table.tex (tab:reconcile)

全部数字由脚本从 experiments/results/raw_matrix.jsonl 重算，并在出表前与
已落盘宏（numbers.tex / m2_stratum.tex）交叉校验；不一致即报错退出。

用法: python ingest_design.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
RES = PROJ / "experiments" / "results"
OUT = HERE.parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCEN = ("S1", "S2", "S3", "S4", "S5", "S6", "S7")
# 顺序即正文出现顺序；标签与 run_matrix.py 的 CONFIGS 一致
CFG_ORDER = (
    "V-E3-vuln0-unlisted",
    "V-E3-vuln1-unlisted",
    "V-E3-vuln0-listed",
    "V-E3-vuln1-listed",
    "V-E3-vuln0-unlisted-nointro",
    "V-E3-vuln1-unlisted-nointro",
    "V-noE3-vuln0",
    "V-noE3-vuln1",
)
PVS = ("raw", "e1", "e1e2")
GUIS = ("blind", "aware")

PROBLEMS: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        PROBLEMS.append(f"[FAIL] {name}: recomputed={got!r} != on-disk={want!r}")
        print(f"  !! {name}: {got!r} != {want!r}")
    else:
        print(f"  ok {name} = {got!r}")


def load() -> list[dict]:
    rows = [json.loads(l) for l in (RES / "raw_matrix.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if "error" not in r]


def readable(r: dict) -> bool:
    """有效可读性：与 ingest_m2_stratum.py 同一定义（配置标记不等于面可读）。

    no-exception 配置在 config 里标 introspection="on"，但其 probe 实为
    unavailable —— 故按 mode/introspection 判定，与 B 包分层一致。
    """
    c = r["config"]
    return not (c["mode"] == "noe3" or c.get("introspection", "on") == "off")


def fp(r: dict, adj: str = "v2") -> bool:
    return r["truth"]["truth"] == "normal" and r["verdicts"][adj]["verdict"] == "violation-proven"


def hit(r: dict, adj: str = "v2") -> bool:
    return r["truth"]["truth"] == "bola" and r["verdicts"][adj]["verdict"] == "violation-proven"


def paired(a_rows, b_rows, key, outcome):
    """同一 key 下 A/B 两组的 2x2 配对计数。"""
    A = {key(r): r for r in a_rows}
    B = {key(r): r for r in b_rows}
    common = set(A) & set(B)
    c = Counter()
    for k in common:
        c[(outcome(A[k]), outcome(B[k]))] += 1
    return c, len(common)


def main() -> None:
    rows = load()
    N = len(rows)
    print(f"records {N}")

    # ---------------- 设计格：可采纳的 (配置, 情景) 组合 ----------------
    cells = Counter((r["config"]["label"], r["scenario"]) for r in rows)
    n_cells = len(cells)
    print(f"admissible cells {n_cells}")

    # ---------------- 因子层级计数 ----------------
    lv = {
        "scenario": Counter(r["scenario"] for r in rows),
        "mode": Counter(r["config"]["mode"] for r in rows),
        "vuln": Counter(r["config"]["vulnerable"] for r in rows),
        "vis": Counter(r["config"]["share_visibility"] for r in rows),
        "intro": Counter(r["config"].get("introspection", "on") for r in rows),
        "readable": Counter(readable(r) for r in rows),
        "mr": Counter(r["mr"] for r in rows),
        "pv": Counter(r["precond_variant"] for r in rows),
        "gui": Counter(r["gui_mode"] for r in rows),
    }
    for k, v in lv.items():
        print(f"  {k}: {dict(v)}")

    # ---------------- 平衡性：3 例外 × 2 读法 × 2 可读性 ----------------
    bal = Counter((r["precond_variant"], r["gui_mode"], readable(r)) for r in rows)
    print("balance (pv, gui, readable):")
    for k in sorted(bal):
        print("   ", k, bal[k])
    # 平衡性断言：每个 (例外策略, 读法) 切片内，可读/不可读的记录数恒定
    for r_flag in (True, False):
        vals = {bal[(pv, gm, r_flag)] for pv in PVS for gm in GUIS}
        assert len(vals) == 1, (r_flag, vals)

    # ---------------- 与已落盘宏交叉校验 ----------------
    def macro(path: Path, name: str):
        m = re.search(rf"\\newcommand{{\\{name}\}}{{([^}}]*)}}", path.read_text(encoding="utf-8"))
        return m.group(1) if m else None

    nums = OUT / "numbers.tex"
    mii = OUT / "m2_stratum.tex"
    if nums.exists():
        check("ResSynRecords", N, int(macro(nums, "ResSynRecords")))
        check("ResDesignCells", n_cells, int(macro(nums, "ResDesignCells")))
        check("ResDesignCellsTwoMr", sum(1 for k, v in cells.items() if k[1] != "S5"), int(macro(nums, "ResDesignCellsTwoMr")))
        check("ResDesignCellsOneMr", sum(1 for k in cells if k[1] == "S5"), int(macro(nums, "ResDesignCellsOneMr")))
    if mii.exists():
        check("MiiNOn", lv["readable"][True], int(macro(mii, "MiiNOn")))
        check("MiiNOff", lv["readable"][False], int(macro(mii, "MiiNOff")))

    # ---------------- 归因：配对差异 ----------------
    key_no_gui = lambda r: (r["config"]["label"], r["scenario"], r["mr"], r["precond_variant"])
    key_no_pv = lambda r: (r["config"]["label"], r["scenario"], r["mr"], r["gui_mode"])

    frozen = [r for r in rows if r["gui_mode"] == "blind"]
    live = [r for r in rows if r["gui_mode"] == "aware"]

    c_fp, n_gui = paired(frozen, live, key_no_gui, fp)
    c_tp, _ = paired(frozen, live, key_no_gui, hit)
    print("gui fp", dict(c_fp), "tp", dict(c_tp), n_gui)

    exc = {}
    for a, b in (("raw", "e1"), ("e1", "e1e2")):
        c, n = paired([r for r in rows if r["precond_variant"] == a],
                      [r for r in rows if r["precond_variant"] == b],
                      key_no_pv, fp)
        exc[(a, b)] = (c, n)
        print(f"exc {a}->{b}", dict(c), n)

    read = {}
    for v in (0, 1):
        on = [r for r in rows if r["config"]["label"] == f"V-E3-vuln{v}-unlisted"]
        off = [r for r in rows if r["config"]["label"] == f"V-E3-vuln{v}-unlisted-nointro"]
        key = lambda r: (r["scenario"], r["mr"], r["precond_variant"], r["gui_mode"])
        c, n = paired(off, on, key, lambda r: r["verdicts"]["v3"]["verdict"] == "violation-proven")
        read[v] = (c, n)
        print(f"readability vuln{v} unreadable->readable hit", dict(c), n)

    # 硬校验：三条归因都必须单向或零差异，否则"无混淆"的说法不成立
    assert c_fp[(False, True)] == 0, dict(c_fp)
    assert c_tp[(False, True)] == 0, dict(c_tp)
    for ab, (c, n) in exc.items():
        assert c[(True, False)] == 0 and c[(False, True)] == 0, (ab, dict(c))
    assert read[0][0][(True, True)] == 0 and read[0][0][(False, True)] == 0

    # ---------------- 对账阶梯 ----------------
    def tally(sel):
        r = sum(1 for x in sel if readable(x))
        return r, len(sel) - r, len(sel)

    grid = [x for x in rows if x["config"]["mode"] == "e3" and x["scenario"] in ("S1", "S2", "S3", "S4", "S5")
            and x["precond_variant"] == "raw" and x["gui_mode"] == "aware"]
    other_sw = [x for x in rows if x["config"]["mode"] == "e3" and x["scenario"] in ("S1", "S2", "S3", "S4", "S5")
                and not (x["precond_variant"] == "raw" and x["gui_mode"] == "aware")]
    s67 = [x for x in rows if x["config"]["mode"] == "e3" and x["scenario"] in ("S6", "S7")]
    noe3 = [x for x in rows if x["config"]["mode"] == "noe3"]

    ladder = [("representative grid", tally(grid)),
              ("other switch settings", tally(other_sw)),
              ("S6--S7, six e3 configurations", tally(s67)),
              ("all e3 records", tally([x for x in rows if x["config"]["mode"] == "e3"])),
              ("two no-exception configurations", tally(noe3)),
              ("all records", tally(rows))]
    for name, t in ladder:
        print(f"  ladder {name}: {t}")
    assert ladder[0][1] == (36, 18, 54), ladder[0]
    assert ladder[3][1] == (312, 156, 468), ladder[3]
    assert ladder[5][1] == (312, 264, 576), ladder[5]
    assert sum(x[1][2] for x in ladder[:2]) == 324

    # ---------------- 宏 ----------------
    M = {
        "DsgRecords": N,
        "DsgCells": n_cells,
        "DsgCellsTwoMr": sum(1 for k in cells if k[1] != "S5"),
        "DsgCellsOneMr": sum(1 for k in cells if k[1] == "S5"),
        "DsgMrTwo": lv["mr"]["MR-002"],
        "DsgMrFour": lv["mr"]["MR-004"],
        "DsgScen": len(SCEN),
        "DsgCfg": len(CFG_ORDER),
        "DsgRecScenMin": min(lv["scenario"].values()),
        "DsgRecScenMax": max(lv["scenario"].values()),
        "DsgRecPerCellMin": min(cells.values()),
        "DsgRecPerCellMax": max(cells.values()),
        "DsgGuiPairs": n_gui,
        "DsgGuiFixedFP": c_fp[(True, False)],
        "DsgGuiNewFP": c_fp[(False, True)],
        "DsgGuiKeptFP": c_fp[(True, True)],
        "DsgGuiKeptTP": c_tp[(True, True)],
        "DsgGuiLostTP": c_tp[(True, False)],
        "DsgGuiLostFP": c_fp[(True, True)] - c_fp[(True, False)],
        "DsgExcPairs": exc[("raw", "e1")][1],
        "DsgExcDiscordant": 0,
        "DsgExcKeptFP": exc[("raw", "e1")][0][(True, True)],
        "DsgReadPairs": read[1][1],
        "DsgReadGained": read[1][0][(False, True)],
        "DsgReadLost": read[1][0][(True, False)],
        "DsgReadNullPairs": read[0][1],
        "DsgGridN": ladder[0][1][2],
        "DsgGridOn": ladder[0][1][0],
        "DsgGridOff": ladder[0][1][1],
        "DsgOtherN": ladder[1][1][2],
        "DsgOtherOn": ladder[1][1][0],
        "DsgOtherOff": ladder[1][1][1],
        "DsgSixSevenN": ladder[2][1][2],
        "DsgSixSevenOn": ladder[2][1][0],
        "DsgSixSevenOff": ladder[2][1][1],
        "DsgEthreeN": ladder[3][1][2],
        "DsgEthreeOn": ladder[3][1][0],
        "DsgEthreeOff": ladder[3][1][1],
        "DsgNoeThreeN": ladder[4][1][2],
        "DsgNoeThreeOn": ladder[4][1][0],
        "DsgNoeThreeOff": ladder[4][1][1],
        "DsgFullOn": ladder[5][1][0],
        "DsgFullOff": ladder[5][1][1],
        "DsgBalOn": bal[("raw", "aware", True)],
        "DsgBalOff": bal[("raw", "aware", False)],
    }

    lines = ["% 由 ingest_design.py 生成，勿手改"]
    for k, v in M.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    (OUT / "design_numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote design_numbers.tex")

    # ---------------- 表 1：因子表 ----------------
    # 行终止符单独定义：f-string 里直接写反斜杠转义极易出错（本文件踩过两次），
    # 统一由 rrow() 追加，正文里就不再出现行尾反斜杠。
    END = "\\\\"

    def rrow(*cells: str) -> str:
        return " & ".join(cells) + END

    tab = [
        "% 由 ingest_design.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{The complete design. Every record is one point of the cross "
        r"scenario $\times$ configuration $\times$ relation $\times$ exception "
        r"policy $\times$ crawl reading; the last two are deliberately thrown "
        r"switches, not replicates, so the enumeration carries no sampling error. "
        r"``Records'' gives the count at each level of the factor, and the last "
        r"column states what the factor is crossed with. Only the "
        r"listed-with-introspection cell is missing, and "
        r"Section~\ref{sec:identify} says what that costs.}",
        r"\label{tab:design}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{@{}p{0.145\textwidth}p{0.105\textwidth}p{0.385\textwidth}rp{0.185\textwidth}@{}}",
        r"\toprule",
        rrow("factor", "levels", "how it is varied", "records", "crossed with"),
        r"\midrule",
        r"\multicolumn{5}{@{}l}{\emph{scenario}}" + END,
        rrow("scenario", "7",
             "the origin of the share and the ground truth: no shared object "
             "(S1, S2); a share made through the framework's own facility (S3); "
             "an unshared violation (S4); a read-only share plus a write "
             "violation (S5); a share made out of band (S6); out of band plus a "
             "violation (S7)",
             f"{M['DsgRecScenMin']}--{M['DsgRecScenMax']}",
             "all configuration levels where admissible"),
        r"\addlinespace[2pt]",
        r"\multicolumn{5}{@{}l}{\emph{configuration}}" + END,
        rrow("instantiation", "2",
             "whether the application offers a legitimate-sharing facility at "
             "all (e3) or not (no-e3)",
             f"{lv['mode']['e3']} / {lv['mode']['noe3']}",
             "enforcement, visibility; undefined under S6--S7"),
        rrow("enforcement", "2",
             "the application either enforces object ownership (correct) or "
             "serves the object to any authenticated subject (violating)",
             f"{lv['vuln'][0]} / {lv['vuln'][1]}", "full"),
        rrow("channel visibility", "2",
             "whether the share is written to the framework's own log (listed) "
             "or not (unlisted)",
             f"{lv['vis']['unlisted']} / {lv['vis']['listed']}",
             "e3 only; no share exists to list under no-e3"),
        rrow("introspection", "2",
             "whether the application exposes a readable per-object share list "
             "(on) or not (off)",
             f"{lv['intro']['on']} / {lv['intro']['off']}",
             r"\emph{listed exists only with introspection on}"),
        r"\addlinespace[2pt]",
        r"\multicolumn{5}{@{}l}{\emph{expansion}}" + END,
        rrow("relation", "2",
             "the metamorphic relation evaluated: MR-002 or MR-004",
             f"{lv['mr']['MR-002']} / {lv['mr']['MR-004']}",
             "S5 carries MR-002 only"),
        rrow("exception policy", "3",
             "how many MST-wi exception predicates are thrown before the "
             "relation fires: none (raw), one (e1), two (e1e2)",
             f"{lv['pv']['raw']} / {lv['pv']['e1']} / {lv['pv']['e1e2']}", "full"),
        rrow("crawl reading", "2",
             "whether the reachability model is the frozen crawl-time snapshot "
             "(frozen) or the execution-time state (live)",
             f"{lv['gui']['blind']} / {lv['gui']['aware']}", "full"),
        r"\midrule",
        r"\multicolumn{5}{@{}l}{$"
        + f"{M['DsgCellsTwoMr']}" + r"\cdot 2\cdot 3\cdot 2 + "
        + f"{M['DsgCellsOneMr']}" + r"\cdot 3\cdot 2 = "
        + f"{M['DsgRecords']}" + r"$ records over $"
        + f"{M['DsgCells']}" + r"$ cells}" + END,
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (OUT / "design_table.tex").write_text("\n".join(tab) + "\n", encoding="utf-8")
    print("wrote design_table.tex")

    # ---------------- 表 2：配置 × 情景人口普查 ----------------
    cen = [
        "% 由 ingest_design.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{The enumeration itself: records under each configuration and "
        r"scenario. A dash is an inadmissible combination, not a missing run---the "
        r"no-exception configurations have no legitimate-sharing facility, so S6 and "
        r"S7, which are defined by a share the facility did not record, are "
        r"undefined for them. Each populated cell holds six exception-policy "
        r"$\times$ crawl-reading records per relation.}"
        ,
        r"\label{tab:design-census}",
        r"\small",
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrrrrr}",
        r"\toprule",
        r"configuration & " + " & ".join(SCEN) + r" & total \\",
        r"\midrule",
    ]
    for lab in CFG_ORDER:
        vals = [cells.get((lab, s), 0) for s in SCEN]
        cells_s = " & ".join(str(v) if v else r"\textemdash" for v in vals)
        cen.append(f"\\texttt{{{lab.replace('_', chr(92) + '_')}}} & {cells_s} & {sum(vals)} \\\\")
    cen += [
        r"\midrule",
        "records & " + " & ".join(str(lv["scenario"][s]) for s in SCEN) + f" & {N} \\\\",
        r"cells & " + " & ".join(str(sum(1 for (l, s2) in cells if s2 == s)) for s in SCEN) + f" & {n_cells} \\\\",
        r"\bottomrule",
        r"\end{tabular*}",
        r"\end{table*}",
    ]
    (OUT / "design_census_table.tex").write_text("\n".join(cen) + "\n", encoding="utf-8")
    print("wrote design_census_table.tex")

    # ---------------- 表 3：配对归因 ----------------
    def row(contrast, outcome, c, n, note):
        first_only = c[(True, False)]
        second_only = c[(False, True)]
        both = c[(True, True)]
        neither = c[(False, False)]
        return (f"{contrast} & {outcome} & {n} & {first_only} & {second_only} & {both} & "
                f"{neither} & {note} \\\\")

    att = [
        "% 由 ingest_design.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Attribution by matched pairs. Each row compares two records that "
        r"differ in exactly one switch, holding configuration, scenario, relation and "
        r"exception policy (or crawl reading) fixed, so the contrast cannot be carried "
        r"by any other factor. ``First only'' and ``second only'' are the discordant "
        r"pairs: a one-way count means the switch moves the outcome in one direction "
        r"only, and a zero means it does not move it at all. The two switches that "
        r"were hypothesised to matter are separated in the first two blocks; the third "
        r"shows the effect is confined to violations that a readable surface can "
        r"resolve.}"
        ,
        r"\label{tab:attribution}",
        r"\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{@{}lrrrrrrp{0.225\textwidth}@{}}",
        r"\toprule",
        r"contrast & outcome & pairs & first only & second only & both & neither & reading \\",
        r"\midrule",
        row("frozen $\\rightarrow$ live", "false proof", c_fp, n_gui,
            f"live reading removes {c_fp[(True, False)]} false proofs, adds {c_fp[(False, True)]}"),
        row("frozen $\\rightarrow$ live", "violation detected", c_tp, n_gui,
            f"and costs {c_tp[(True, False)]} detections"),
        r"\addlinespace[3pt]",
        row("raw $\\rightarrow$ e1", "false proof", exc[("raw", "e1")][0], exc[("raw", "e1")][1],
            "no discordant pair: the ladder changes nothing"),
        row("e1 $\\rightarrow$ e1e2", "false proof", exc[("e1", "e1e2")][0], exc[("e1", "e1e2")][1],
            "no discordant pair: the second predicate adds nothing"),
        r"\addlinespace[3pt]",
        row("unreadable $\\rightarrow$ readable", "verdict of violation-proven",
            read[1][0], read[1][1],
            f"all {read[1][0][(False, True)]} changes are detections gained, none lost"),
        row("unreadable $\\rightarrow$ readable", "verdict of violation-proven",
            read[0][0], read[0][1],
            "no change where there is no violation to detect"),
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (OUT / "attribution_table.tex").write_text("\n".join(att) + "\n", encoding="utf-8")
    print("wrote attribution_table.tex")

    # ---------------- 表 4：36/18 与 312/264 对账 ----------------
    rec = [
        "% 由 ingest_design.py 生成，勿手改",
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Reconciling the representative grid with the full partition. The "
        r"grid of Section~\ref{sec:synthetic} is one point of the switch space, not a "
        r"smaller version of the partition: it fixes the exception policy at raw and "
        r"the crawl reading at live, keeps the six e3 configurations, and stops at S5. "
        r"Adding the rest of the enumeration reproduces the 312/264 partition exactly.}"
        ,
        r"\label{tab:reconcile}",
        r"\footnotesize",
        r"\begin{tabular}{@{}p{0.47\columnwidth}rrr@{}}",
        r"\toprule",
        r"subset & readable & unreadable & records \\",
        r"\midrule",
        f"representative grid & {M['DsgGridOn']} & {M['DsgGridOff']} & {M['DsgGridN']}" + END,
        f"$+$ other five switch settings & {M['DsgOtherOn']} & {M['DsgOtherOff']} & {M['DsgOtherN']}" + END,
        f"$+$ S6--S7, six e3 configurations & {M['DsgSixSevenOn']} & {M['DsgSixSevenOff']} & {M['DsgSixSevenN']}" + END,
        f"$=$ all e3 records & {M['DsgEthreeOn']} & {M['DsgEthreeOff']} & {M['DsgEthreeN']}" + END,
        f"$+$ two no-exception configurations & {M['DsgNoeThreeOn']} & {M['DsgNoeThreeOff']} & {M['DsgNoeThreeN']}" + END,
        f"$=$ all records & {M['DsgFullOn']} & {M['DsgFullOff']} & {N}" + END,
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    (OUT / "reconcile_table.tex").write_text("\n".join(rec) + "\n", encoding="utf-8")
    print("wrote reconcile_table.tex")

    if PROBLEMS:
        print("\n".join(PROBLEMS))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
