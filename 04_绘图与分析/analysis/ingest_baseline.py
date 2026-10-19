"""
R1.7 · 竞争基线：常规差分 vs 关系感知裁决
============================================================
审稿原文（R1.7）要求给出与候选、预算匹配的公平基线，而不是只与自己的消融比。

数据来源
--------
  experiments/results/baseline_compare.json   受控 42 格（6 配置 × S1–S7），
                                              四方法共用同一对探测请求
  experiments/real_system/results/real_system.json
                                              Gitea 快照 48 格的同规则复核

口径（与主实验一致）
--------------------
  TP             = E=deny ∧ Y=allow ∧ 方法宣称 violation-proven
  false proof    = E=allow ∧ 方法宣称 violation-proven
  abstain        = 裁决 indeterminate（只有 ours 会弃权）
  coverage       = (N - abstain) / N
  precision      = TP / claims

★ 这张表**不主张检测增益**。基线在 42 格里检出全部 15 个真违规；ours 只在
  自省面可读的 10 格上确证，另 5 格（两个 no-introspection 配置）按合同弃权。
  差异全部落在假确证与覆盖率上，不得写成 "outperforms" / "dominates"。

用法: python ingest_baseline.py
输出: results/baseline_numbers.tex, results/baseline_table.tex
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
RES = PROJ / "experiments" / "results"
REAL = PROJ / "experiments" / "real_system" / "results"
OUT = HERE.parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROBLEMS: list[str] = []


def check(name, got, want):
    if got != want:
        PROBLEMS.append(f"[FAIL] {name}: recomputed={got!r} != expected={want!r}")
        print(f"  !! {name}: {got!r} != {want!r}")
    else:
        print(f"  ok {name} = {got!r}")


def pc(x: float) -> str:
    return f"{100.0 * x:.2f}"


def tally(records: list[dict], method: str) -> dict:
    c = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "abstain": 0}
    for r in records:
        m = r["methods"][method]
        for k in c:
            c[k] += int(m[k])
    c["claims"] = c["tp"] + c["fp"]
    c["cells"] = len(records)
    c["coverage"] = (c["cells"] - c["abstain"]) / c["cells"]
    c["precision"] = c["tp"] / c["claims"] if c["claims"] else None
    return c


def main() -> None:
    data = json.loads((RES / "baseline_compare.json").read_text(encoding="utf-8"))
    recs = [r for r in data["records"] if "error" not in r]
    N = len(recs)

    bola = sum(1 for r in recs if r["truth"] == "bola")
    legit = sum(1 for r in recs
                if r["truth"] == "normal" and r["signals"]["actor_ok"])
    denied = N - bola - legit

    b1 = tally(recs, "B1_status_only")
    b2 = tally(recs, "B2_diff_equal")
    b3 = tally(recs, "B3_diff_inband")
    ours = tally(recs, "ours_mr_v3")
    # 汇总层的条件召回/总召回/弃权真违规，与逐格 tally 分开取
    sm = data["summary"]
    ours_s = sm["ours_mr_v3"]
    b1_s = sm["B1_status_only"]

    # ---- 断言：任何一格与正文口径不符都在这里炸掉 ----------------------
    check("cells", N, 42)
    check("bola cells", bola, 15)
    check("legitimate-access cells", legit, 12)
    check("denied cells", denied, 15)
    check("B1 claims", b1["claims"], 27)
    check("B1 false proofs", b1["fp"], 12)
    check("B2 == B1 claims", b2["claims"], b1["claims"])
    check("B3 false proofs", b3["fp"], 6)
    check("ours TP", ours["tp"], 10)
    check("ours false proofs", ours["fp"], 0)
    check("ours abstain", ours["abstain"], 17)
    check("ours coverage", round(ours["coverage"], 4), round(25 / 42, 4))
    # 两个召回口径必须分开：条件召回（只在作出裁决的格上算）与总召回
    # （分母含被弃权的真违规格）。二者相等仅当没有弃权。
    check("ours recall on decided", round(ours_s["recall_on_decided"], 4), 1.0)
    check("ours total recall", round(ours_s["recall_all_violations"], 4),
          round(10 / 15, 4))
    check("ours abstained violations", ours_s["abstained_violations"], 5)
    check("baselines total recall", round(b1_s["recall_all_violations"], 4), 1.0)
    check("baselines abstain nothing", b1["abstain"], 0)

    # ---- 真实系统：同一规则套到 Gitea 快照 -----------------------------
    rs = json.loads((REAL / "real_system.json").read_text(encoding="utf-8"))
    snap = [c for c in rs["phaseE_cells"] if c["reading"] == "snapshot"]
    rs_allow = sum(1 for c in snap if c["expected_entitlement"] == "allow")
    rs_equal = sum(1 for c in snap if c["output_equal"])
    rs_b3 = sum(1 for c in snap
                if c["output_equal"] and not c["framework_log_has_record"])
    check("gitea snapshot cells", len(snap), 48)
    check("gitea allowed cells", rs_allow, 25)
    check("gitea B2 claims", rs_equal, 25)
    check("gitea B3 claims", rs_b3, 24)

    # ---- 宏 -------------------------------------------------------------
    budget = data["summary"]["_budget"]
    probe_req = budget["probe_requests_per_cell"][0]
    run_seconds = data["elapsed_sec"]
    extra_cells = sum(1 for r in recs if r["budget"]["ours_extra_requests"] >= 1)
    extra_avg = extra_cells / len(recs)
    check("matched probe budget", budget["probe_requests_per_cell"], [2])
    check("extra reads only where a relation alarms",
          sorted({r["budget"]["ours_extra_requests"] for r in recs}), [0, 1])
    check("extra reads on the alarming cells",
          extra_cells, b2["claims"])
    check("harness run time recorded", run_seconds > 0, True)
    # 预算口径：匹配的是探测对，不是总请求数
    check("shared probe requests", budget["shared_probe_requests"], 2 * N)
    check("ours extra requests total",
          budget["ours_extra_requests_total"], extra_cells)
    check("ours total requests", budget["ours_total_requests"],
          budget["shared_probe_requests"] + budget["ours_extra_requests_total"])

    macros = {
        "BlCells": str(N),
        "BlRunSeconds": f"{run_seconds:.1f}",
        "BlOursExtraCells": str(extra_cells),
        "BlOursExtraAvg": f"{extra_avg:.2f}",
        "BlBolaCells": str(bola),
        "BlLegitCells": str(legit),
        "BlDeniedCells": str(denied),
        "BlProbeReq": str(probe_req),
        "BlBOneClaims": str(b1["claims"]),
        "BlBOneTP": str(b1["tp"]),
        "BlBOneFP": str(b1["fp"]),
        "BlBTwoClaims": str(b2["claims"]),
        "BlBTwoTP": str(b2["tp"]),
        "BlBTwoFP": str(b2["fp"]),
        "BlBTwoPrecision": pc(b2["precision"]),
        "BlBThreeClaims": str(b3["claims"]),
        "BlBThreeTP": str(b3["tp"]),
        "BlBThreeFP": str(b3["fp"]),
        "BlBThreePrecision": pc(b3["precision"]),
        "BlOursClaims": str(ours["claims"]),
        "BlOursTP": str(ours["tp"]),
        "BlOursFP": str(ours["fp"]),
        "BlOursAbstain": str(ours["abstain"]),
        "BlOursCoverage": pc(ours["coverage"]),
        "BlOursPrecision": pc(ours["precision"]),
        # 两个召回口径必须同时出现，否则 1.0 会被读成总召回
        "BlOursRecallDecided": pc(ours_s["recall_on_decided"]),
        "BlOursRecallAll": pc(ours_s["recall_all_violations"]),
        "BlOursAbstainViol": str(ours_s["abstained_violations"]),
        "BlBaselineRecallAll": pc(b1_s["recall_all_violations"]),
        # 预算：探测对匹配，总请求数不匹配
        "BlSharedProbes": str(budget["shared_probe_requests"]),
        "BlOursExtraTotal": str(budget["ours_extra_requests_total"]),
        "BlOursRequestsTotal": str(budget["ours_total_requests"]),
        "BlRsCells": str(len(snap)),
        "BlRsAllow": str(rs_allow),
        "BlRsBTwoClaims": str(rs_equal),
        "BlRsBThreeClaims": str(rs_b3),
    }
    lines = ["% 由 analysis/ingest_baseline.py 生成，勿手改"]
    for k, v in macros.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    (OUT / "baseline_numbers.tex").write_text("\n".join(lines) + "\n",
                                              encoding="utf-8")
    print("wrote baseline_numbers.tex")

    # ---- 表 -------------------------------------------------------------
    rows = [
        ("B1 status-only",
         "alarm iff the actor's request returns non-error", b1),
        ("B2 equality replay",
         "alarm iff the owner succeeded and the actor received byte-identical output", b2),
        ("B3 B2 + in-band log",
         "suppress cells covered by the tester's own share log", b3),
        ("Ours: MR-002 + v3",
         "consult the SUT authorization surface; abstain if unreadable", ours),
    ]
    tab = [
        r"% 由 analysis/ingest_baseline.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Competing baselines on the same \BlCells{} cells and the same "
        r"probe pair. The cells comprise \BlBolaCells{} true violations, "
        r"\BlLegitCells{} legitimate accesses through a grant (in-band or "
        r"out-of-band), and \BlDeniedCells{} denials. Every method consumes one "
        r"owner request and one actor request (\BlSharedProbes{} shared probes); "
        r"ours issues one additional read "
        r"of the authorization surface on the \BlOursExtraCells{} cells where a "
        r"relation alarms, and none where it does not "
        r"(\BlOursExtraAvg{} per cell on average, \BlOursExtraTotal{} in total, "
        r"\BlOursRequestsTotal{} against the baselines' \BlSharedProbes{}), so "
        r"total requests and visible information are not matched. A false proof "
        r"is a cell with "
        r"$E=\text{allow}$ that the method still reports as a proven violation. "
        r"Recall is reported twice because the two figures differ exactly where "
        r"a method abstains: \emph{decided} counts only the cells the method "
        r"ruled on, \emph{all} keeps every violation cell in the denominator.}",
        r"\label{tab:baselines}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{@{}p{0.145\textwidth}p{0.300\textwidth}rrrrrrr@{}}",
        r"\toprule",
        r"Method & Decision rule & Claims & TP & False proofs & Abstain & "
        r"Coverage (\%) & Recall: decided / all (\%) \\",
        r"\midrule",
    ]
    for name, rule, c in rows:
        s = sm[{"B1 status-only": "B1_status_only",
                "B2 equality replay": "B2_diff_equal",
                "B3 B2 + in-band log": "B3_diff_inband",
                "Ours: MR-002 + v3": "ours_mr_v3"}[name]]
        tab.append(
            f"{name} & {rule} & {c['claims']} & {c['tp']} & {c['fp']} & "
            f"{c['abstain']} & {pc(c['coverage'])} & "
            f"{pc(s['recall_on_decided'])} / {pc(s['recall_all_violations'])} \\\\")
    tab += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (OUT / "baseline_table.tex").write_text("\n".join(tab) + "\n", encoding="utf-8")
    print("wrote baseline_table.tex")

    if PROBLEMS:
        print("\n".join(PROBLEMS))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
