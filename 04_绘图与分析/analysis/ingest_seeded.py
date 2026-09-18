# -*- coding: utf-8 -*-
"""
把「受控脆弱性靶机阳性对照」（run_seeded.py 的产物）并入论文数字流水线。
==========================================================================

输入（全部为实测产物，任何数字都不手敲）：
  * experiments/real_system/results/seeded.json —— run_seeded.py 的产物

输出：
  * 04_绘图与分析/results/seeded_table.tex —— 宏定义（\\Seed*）+ 阳性对照表体

设计：靶机复刻 Gitea 的对象级授权 API 契约，植入确定性 BOLA 缺陷，
真值由 SEED_FLAWS 单一来源提供；四方法裁决公式与 run_real.py 同代码路径。
本脚本只负责把 (TP/FN/FP/TN) 重算为宏，不引入新判定逻辑。

用法:
  python analysis/ingest_seeded.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # 3区论文/
RS = ROOT / "experiments" / "real_system" / "results"
OUT = HERE.parent / "results"
SEED_JSON = RS / "seeded.json"

PFX = "Seed"
# 宏名安全化：TeX 控制词不含下划线与数字（V3 -> VThree，同 numbers.tex 约定）
MACRO_NAME = {
    "mr_bookkeeping": "MrBookkeeping",
    "v3": "VThree",
    "v3_self": "VThreeSelf",
    "direct_only": "DirectOnly",
    "direct_observe": "DirectObserve",
    "direct_observe_self": "DirectObserveSelf",
}
METHODS = tuple(MACRO_NAME)


def main() -> None:
    data = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    perf = data["positive_control_TP_FN_FP"]
    seeded = data["seeded_truth"]
    bfla = data["bfla_probe"]

    n_bola = len(seeded["bola"])
    lines = []
    def cmd(k: str, v: str) -> None:
        lines.append(f"\\newcommand{{\\{PFX}{k}}}{{{v}}}")

    cmd("BolaN", n_bola)
    cmd("BflaActor", bfla["actor"])
    cmd("BflaStatus", bfla["unauthorized_grant_status"])
    cmd("BflaPresent", "true" if bfla["vulnerable_present"] else "false")

    for m in METHODS:
        d = perf[m]
        name = MACRO_NAME[m]
        cmd(f"TP{name}", d["TP"])
        cmd(f"FN{name}", d["FN"])
        cmd(f"FP{name}", d["FP"])
        cmd(f"TN{name}", d["TN"])

    out = OUT / "seeded_table.tex"
    header = (
        "% 来源: experiments/real_system/results/seeded.json (run_seeded.py)\n"
        "% 阳性对照：受控脆弱性靶机（复刻 Gitea API 契约，植入确定性 BOLA 缺陷）\n"
        "% 四方法裁决公式与 run_real.py 同代码路径；数字由本脚本重算，绝不手敲。\n"
    )
    out.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")

    print(f"[ok] -> {out} ({out.stat().st_size} bytes)")
    print(f"植入 BOLA 缺陷 = {n_bola}; direct_observe TP/FN/FP = "
          f"{perf['direct_observe']['TP']}/{perf['direct_observe']['FN']}/{perf['direct_observe']['FP']}; "
          f"direct_only FP = {perf['direct_only']['FP']}")


if __name__ == "__main__":
    main()
