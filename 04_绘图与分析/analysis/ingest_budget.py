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


def recompute(recs: list[dict]) -> dict:
    """从逐格记录独立重算汇总（不复用 run_baseline.aggregate）。

    与缓存 summary 交叉校验：两份实现不一致就拒绝出数，避免"汇总与逐例脱节"。
    """
    out: dict[str, dict] = {}
    names = [n for n in ORDER if any(n in r.get("methods", {}) for r in recs)]
    for name in names:
        c = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "abstain": 0}
        req = 0
        for r in recs:
            m = r["methods"][name]
            for k in c:
                c[k] += int(bool(m[k]))
            req += r["budget"]["probe_requests"]
            if name == "ours_mr_v3":
                req += r["budget"]["ours_extra_requests"]
            if name == "B3r_diff_reach":
                req += r["budget"]["reach_extra_requests"]
        n = len(recs)
        n_viol = sum(1 for r in recs if r.get("truth") == "bola")
        decided = c["tp"] + c["fn"]
        claimed = c["tp"] + c["fp"]
        out[name] = {
            **c,
            "cells": n,
            "claimed": claimed,
            "violation_cells": n_viol,
            "abstained_violations": sum(
                1 for r in recs
                if r.get("truth") == "bola" and r["methods"][name]["abstain"]),
            "coverage": round((n - c["abstain"]) / n, 4) if n else None,
            "precision_on_claims": round(c["tp"] / claimed, 4) if claimed else None,
            "recall_on_decided": round(c["tp"] / decided, 4) if decided else None,
            "recall_all_violations": round(c["tp"] / n_viol, 4) if n_viol else None,
            "false_proof_rate": round(c["fp"] / n, 4) if n else None,
            "requests_total": req,
        }
    return out


SCALARS = ("tp", "fp", "fn", "tn", "abstain", "cells", "claimed",
           "violation_cells", "abstained_violations", "coverage",
           "precision_on_claims", "recall_on_decided", "recall_all_violations",
           "false_proof_rate", "requests_total")


def cross_check(cap: int, cached: dict, recs: list[dict]) -> dict:
    """逐字段比对"缓存 summary"与"从记录重算"；有分歧直接抛错，不出数。"""
    fresh = recompute(recs)
    for name, got in fresh.items():
        want = cached.get(name)
        if want is None:
            raise SystemExit(f"[FAIL] cap={cap}: method {name} in records but not in summary")
        for k in SCALARS:
            if got[k] != want[k]:
                raise SystemExit(
                    f"[FAIL] cap={cap} {name} {k}: records say {got[k]!r}, "
                    f"summary says {want[k]!r} -- refusing to emit numbers")
    if set(fresh) != {k for k in cached if not k.startswith("_")}:
        raise SystemExit(f"[FAIL] cap={cap}: method sets differ between records and summary")
    return fresh


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    s2, s3 = d["sweeps"]["2"], d["sweeps"]["3"]
    # 先做逐格重算 ↔ 缓存 summary 的交叉校验，再取数排版。
    for cap, s in ((2, s2), (3, s3)):
        if "records" not in s:
            raise SystemExit(f"[FAIL] cap={cap}: no per-cell records in {SRC.name}")
        cross_check(cap, s["summary"], [r for r in s["records"] if "error" not in r])
    a2, a3 = s2["summary"], s3["summary"]
    cells = s2["cells"]
    n_viol = a3["ours_mr_v3"]["violation_cells"]
    # 成本口径：ours 的额外读取只在 MR 触发时发生；未触发的格直接 pass、不读面。
    pass2 = sum(1 for r in s2["records"]
                if r.get("methods", {}).get("ours_mr_v3", {}).get("verdict") == "pass")
    pass3 = sum(1 for r in s3["records"]
                if r.get("methods", {}).get("ours_mr_v3", {}).get("verdict") == "pass")
    read2 = sum(1 for r in s2["records"] if r.get("budget", {}).get("oracle_read"))
    read3 = sum(1 for r in s3["records"] if r.get("budget", {}).get("oracle_read"))

    lines: list[str] = []

    def cmd(k: str, v) -> None:
        lines.append(f"\\newcommand{{\\{PFX}{k}}}{{{v}}}")

    cmd("Cells", cells)
    cmd("Violations", n_viol)
    cmd("OursPassCapTwo", pass2)
    cmd("OursPassCapThree", pass3)
    cmd("OursOracleReadCapTwo", read2)
    cmd("OursOracleReadCapThree", read3)
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
        r"credentials. \emph{cap} is the total request budget per cell. At cap~2 only the "
        r"owner/actor probe pair fits: our method keeps its own order---it passes on the "
        r"\BgtOursPassCapTwo{} cells where the relation does not trigger, reading no surface, "
        r"and abstains on the rest, where the relation does trigger and no request is left to "
        r"read the surface. At cap~3 each method may spend one further observation of its own "
        r"choosing---ours reads the authorization surface, B3r enumerates the actor's visible "
        r"objects---while B1--B3 spend nothing extra and are reported as under budget. No "
        r"method is given padding requests. Ours therefore does not dominate: at the same "
        r"ceiling B3r reaches \BgtBthreeRTpCapThree{} of \BgtViolations{} with "
        r"\BgtBthreeRFpCapThree{} false proofs, ours \BgtOursTpCapThree{} with "
        r"\BgtOursFpCapThree{} and \BgtOursAbstainCapThree{} abstentions, and where the surface "
        r"is unreadable ours refuses to claim rather than guessing. Ours spends "
        r"\BgtOursReqCapThree{} of the \BgtCells{}$\times$3 requests the ceiling allows because "
        r"the \BgtOursPassCapTwo{} untriggered cells never read the surface---not because an "
        r"abstaining cell is free: it still pays for its probe pair, and for the surface read "
        r"whenever the relation triggers under a ceiling that reaches it.}")
    rows.append(r"\label{tab:budget}")
    rows.append(r"\small")
    rows.append(r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llrrrrrr}")
    rows.append(r"\toprule")
    rows.append(r"cap & method & TP & FN & FP & TN & abstain & requests \\")
    rows.append(r"\midrule")
    for cap, agg in ((2, a2), (3, a3)):
        for m in ORDER:
            if m not in agg:
                continue
            v = agg[m]
            rows.append(f"{cap} & {LABEL[m]} & {v['tp']} & {v['fn']} & {v['fp']} & "
                        f"{v['tn']} & {v['abstain']} & {v['requests_total']} \\\\")
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
        "% 宏由调用方在导言区 \\input{budget_numbers.tex} 加载（main.tex 已加载）；\n"
        "% 此处不再重复：\\newcommand 重复定义会报 Command already defined，\n"
        "% 而 ZIP 打包器只从 main.tex 的 \\input 推导依赖，表内 \\input 会让宏文件漏装。\n"
        + "\n".join(rows) + "\n", encoding="utf-8")
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
