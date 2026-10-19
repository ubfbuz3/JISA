# -*- coding: utf-8 -*-
"""
R1.7 等总预算比较 —— 并入数字流水线。
==================================

输入：experiments/results/baseline_budget.json (run_baseline.py --budget)
输出：04_绘图与分析/results/budget_table.tex （宏 + 表体）

口径：每个方法在同一格上的**总请求数上限**相同（cap=2 只够探测对，cap=3 多一次
额外观测）；实际支出如实记账，不向基线补发无用请求。真值与主实验同一口径。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE.parent / "results"
SRC = ROOT / "experiments" / "results" / "baseline_budget.json"

PFX = "Bgt"
LABEL = {
    "B1_status_only": "B1 status-only",
    "B2_diff_equal": "B2 diff-equal",
    "B3_diff_inband": "B3 diff+in-band",
    "B3r_diff_reach": "B3r diff+in-band+reach",
    "ours_mr_v3": "ours (MR + v3)",
}
ORDER = ["B1_status_only", "B2_diff_equal", "B3_diff_inband",
         "B3r_diff_reach", "ours_mr_v3"]


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    s2, s3 = d["sweeps"]["2"], d["sweeps"]["3"]
    a2, a3 = s2["summary"], s3["summary"]
    cells = s2["cells"]
    n_viol = a3["ours_mr_v3"]["violation_cells"]

    lines: list[str] = []

    def cmd(k: str, v) -> None:
        lines.append(f"\\newcommand{{\\{PFX}{k}}}{{{v}}}")

    cmd("Cells", cells)
    cmd("Violations", n_viol)
    for cap, agg, tag in ((2, a2, "CapTwo"), (3, a3, "CapThree")):
        o = agg["ours_mr_v3"]
        cmd(f"OursTp{tag}", o["tp"])
        cmd(f"OursFp{tag}", o["fp"])
        cmd(f"OursFn{tag}", o["fn"])
        cmd(f"OursAbstain{tag}", o["abstain"])
        cmd(f"OursReq{tag}", o["requests_total"])
        cmd(f"OursRecall{tag}", f"{o['recall_all_violations']:.2f}")
        for m, short in (("B3_diff_inband", "Bthree"), ("B3r_diff_reach", "BthreeR"),
                         ("B1_status_only", "Bone")):
            if m in agg:
                cmd(f"{short}Tp{tag}", agg[m]["tp"])
                cmd(f"{short}Fp{tag}", agg[m]["fp"])
                cmd(f"{short}Fn{tag}", agg[m]["fn"])
                cmd(f"{short}Req{tag}", agg[m]["requests_total"])

    rows = []
    rows.append(r"\begin{table*}[t]")
    rows.append(r"\centering")
    rows.append(
        r"\caption{Equal-budget comparison on the same \BgtCells{} cells and the same "
        r"credentials. \emph{cap} is the total request budget per cell: at cap~2 only the "
        r"owner/actor probe pair fits, so any method that must consult the authorization "
        r"surface has to abstain; at cap~3 each method may spend one further observation of "
        r"its own choosing---ours reads the authorization surface, B3r enumerates the actor's "
        r"visible objects---while B1--B3 spend nothing extra and are reported as under budget. "
        r"No method is given padding requests. Ours therefore does not dominate: at the same "
        r"ceiling B3r reaches \BgtBthreeRTpCapThree{} of \BgtViolations{} with "
        r"\BgtBthreeRFpCapThree{} false proofs, ours \BgtOursTpCapThree{} with "
        r"\BgtOursFpCapThree{} and \BgtOursAbstainCapThree{} abstentions, and where the surface "
        r"is unreadable ours refuses to claim rather than guessing. Ours also spends "
        r"\BgtOursReqCapThree{} of the \BgtCells{}$\times$3 requests the ceiling allows, because "
        r"an abstaining cell costs nothing.}")
    rows.append(r"\label{tab:budget}")
    rows.append(r"\small")
    rows.append(r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llrrrrr}")
    rows.append(r"\toprule")
    rows.append(r"cap & method & TP & FN & FP & abstain & requests \\")
    rows.append(r"\midrule")
    for cap, agg in ((2, a2), (3, a3)):
        for m in ORDER:
            if m not in agg:
                continue
            v = agg[m]
            rows.append(f"{cap} & {LABEL[m]} & {v['tp']} & {v['fn']} & {v['fp']} & "
                        f"{v['abstain']} & {v['requests_total']} \\\\")
        if cap == 2:
            rows.append(r"\midrule")
    rows.append(r"\bottomrule")
    rows.append(r"\end{tabular*}")
    rows.append(r"\end{table*}")

    header = (
        "% 由 analysis/ingest_budget.py 自动生成 —— 勿手改\n"
        "% 来源: experiments/results/baseline_budget.json (run_baseline.py --budget)\n"
        "% 等总预算上限；真值与主实验同口径（动作级构造式真值）。\n"
    )
    (OUT / "budget_numbers.tex").write_text(
        header + "\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "budget_table.tex").write_text(
        "% 由 analysis/ingest_budget.py 自动生成 —— 勿手改\n"
        "\\input{budget_numbers.tex}\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"[ok] -> {OUT / 'budget_table.tex'}")
    print(f"cells={cells} violations={n_viol} "
          f"ours@cap3 TP={a3['ours_mr_v3']['tp']} FP={a3['ours_mr_v3']['fp']} "
          f"abstain={a3['ours_mr_v3']['abstain']} req={a3['ours_mr_v3']['requests_total']}")
    # 自检：任何方法的支出不得超过 cap*cells
    for cap, agg in ((2, a2), (3, a3)):
        for m, v in agg.items():
            if m.startswith("_"):
                continue
            assert v["requests_total"] <= cap * cells, f"{m} exceeded budget at cap={cap}"


if __name__ == "__main__":
    main()
