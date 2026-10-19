# -*- coding: utf-8 -*-
"""
把「R1.9 多类独立授权缺陷」实验（run_multiclass.py）并入论文数字流水线。
=====================================================================

输入：experiments/real_system/results/seeded_multiclass.json
输出：04_绘图与分析/results/multiclass_table.tex （宏 + 表体）

设计：每个实例的真值来自靶机正确模型（intended_perm），观测来自实际请求，
与真实系统实验同一套 alarm 公式。本脚本只做重算与排版，不引入新判定逻辑。

用法:  python analysis/ingest_multiclass.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RS = ROOT / "experiments" / "real_system" / "results"
OUT = HERE.parent / "results"
SRC = RS / "seeded_multiclass.json"

PFX = "Mc"
ROWS = [("C1", "read enforcement"),
        ("C2", "modify enforcement"),
        ("C3", "inheritance"),
        ("C4", "privilege escalation")]


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    per = data["summary"]["per_class"]
    fp = data["summary"]["fp"]
    fp_den = data["summary"]["fp_denominator"]
    inst = data["runs"]["all"]["instances"]

    n_total = sum(per[c]["n"] for c, _ in ROWS)
    read_hits = sum(per[c]["mr_read"] for c, _ in ROWS)
    chan_hits = sum(per[c]["mr_channel"] for c, _ in ROWS)
    oracle_read = sum(per[c]["detected"]["direct_observe"] for c, _ in ROWS)
    oracle_chan = sum(per[c]["detected"]["direct_observe_channel"] for c, _ in ROWS)
    v3_read = sum(per[c]["detected"]["v3"] for c, _ in ROWS)
    v3_chan = sum(per[c]["detected"]["v3_channel"] for c, _ in ROWS)

    lines: list[str] = []

    def cmd(k: str, v) -> None:
        lines.append(f"\\newcommand{{\\{PFX}{k}}}{{{v}}}")

    cmd("Instances", n_total)
    cmd("ReadHits", read_hits)
    cmd("ChannelHits", chan_hits)
    cmd("OracleReadHits", oracle_read)
    cmd("OracleChannelHits", oracle_chan)
    cmd("VthreeReadHits", v3_read)
    cmd("VthreeChannelHits", v3_chan)
    cmd("FpBookkeeping", fp["mr_bookkeeping"])
    cmd("AuthorizedCells", fp_den)
    cmd("FpOracle", max(fp["direct_observe"], fp["direct_observe_channel"]))
    cmd("Classes", len(ROWS))

    # ---- 表体 ----
    body = []
    body.append(r"\begin{table*}[t]")
    body.append(r"\centering")
    body.append(
        r"\caption{Per-defect recall of the studied chain on the controlled target, by defect "
        r"class. Each instance is a cell whose true (correct-model) permission is \emph{none} and "
        r"on which the defect nevertheless lets the access succeed. \emph{read gate} is the "
        r"reachability-gated relation as studied in this paper; \emph{channel gate} is the same "
        r"relation moved to the channel the defect actually breaks; the last two columns are the "
        r"oracle-consuming adjudicator on the read channel and on the channel-matched probe. "
        r"Every instance here is one the gate was designed for except C3 and C4, which it cannot "
        r"see: in both, the object is visible to the subject, so the antecedent of the relation "
        r"is false and no alarm is raised---not a tuning problem but the gate reading its own "
        r"premise. The oracle-based adjudicator reaches all \McInstances{} instances once the "
        r"probe is channel-matched. False alarms on the \McAuthorizedCells{} authorized cells: "
        r"\McFpBookkeeping{} for the relation's bookkeeping variant, \McFpOracle{} for the "
        r"oracle-based adjudicator, whose zero is conditional on this target's oracle being "
        r"sound (Section~VI-C reports what happens when it is not).}")
    body.append(r"\label{tab:multiclass}")
    body.append(r"\small")
    body.append(r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrr}")
    body.append(r"\toprule")
    body.append(r"Class & inst. & read gate & channel gate & oracle (read) & oracle (channel) \\")
    body.append(r"\midrule")
    for c, label in ROWS:
        e = per[c]
        body.append(f"{c}: {label} & {e['n']} & {e['mr_read']} & {e['mr_channel']} & "
                    f"{e['detected']['direct_observe']} & "
                    f"{e['detected']['direct_observe_channel']} \\\\")
    body.append(r"\addlinespace[2pt]")
    body.append(f"\\emph{{total}} & {n_total} & {read_hits} & {chan_hits} & "
                f"{oracle_read} & {oracle_chan} \\\\")
    body.append(r"\bottomrule")
    body.append(r"\end{tabular*}")
    body.append(r"\end{table*}")

    header = (
        "% 由 analysis/ingest_multiclass.py 自动生成 —— 勿手改\n"
        "% 来源: experiments/real_system/results/seeded_multiclass.json (run_multiclass.py)\n"
        "% 真值 = 靶机正确模型 intended_perm；观测 = 实际请求；与真实系统同一套 alarm 公式。\n"
    )
    (OUT / "multiclass_numbers.tex").write_text(
        header + "\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "multiclass_table.tex").write_text(
        "% 由 analysis/ingest_multiclass.py 自动生成 —— 勿手改\n"
        "\\input{multiclass_numbers.tex}\n\n" + "\n".join(body) + "\n", encoding="utf-8")
    print(f"[ok] -> {OUT / 'multiclass_table.tex'}")
    print(f"instances={n_total} read={read_hits} channel={chan_hits} "
          f"oracle_read={oracle_read} oracle_channel={oracle_chan} "
          f"fp_book={fp['mr_bookkeeping']}/{fp_den}")
    # 一致性自检：每类实例数必须与登记表一致
    declared = data["meta"]["classes"]
    assert all(len(declared[c]["instances"]) == per[c]["n"] for c, _ in ROWS), \
        "instance count mismatch between registry and results"
    assert all(r["truth_permission"] == "none" for r in inst), \
        "an instance is not unauthorized under the correct model"


if __name__ == "__main__":
    main()
