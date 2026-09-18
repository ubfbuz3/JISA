"""
第七轮追加消融 #2 · direct-observe（**用普通请求替代 MR**）
==========================================================
回应审判方对作者答辩 §1.4 的裁定（`17_答辩审判_v7.md`）：

> 「direct-only 的 108 个 FP 是『忽略访问结果』的产物，而非『缺 MR』的产物；
>   真正相关的对照（alarm ⟺ observed-200 AND introspection-none）作者未跑，
>   而 MR 触发所依赖的『访问证据』本身即非变形的状态码。」

因此本脚本补跑该对照。三个方法的区别只在**访问证据从哪来**：

  v3            : 访问证据 = **MR 触发**（变形关系被违反）  ∧ 授权面 = none
  direct_only   : 访问证据 = **无**（只看授权面）            ∧ 授权面 = none
  direct_observe: 访问证据 = **普通请求的 HTTP 200**（非变形） ∧ 授权面 = none

若 direct_observe 支配 v3 ⇒ **MR 是冗余的**（可用普通请求替代），
则"变形测试"在本问题上不承担工作，贡献塌缩（审判方 Q4/U9 成立）。
若 direct_observe 不支配 v3 ⇒ 需说明差在哪。

诚实声明：本实验中 `truth` 的定义为
    bola ⟺ (¬should_allow) ∧ app_allowed,   其中 app_allowed ⟺ observed_status == 200
因此若 (授权面说 none) 恰等价于 (¬should_allow)，则 direct_observe **按构造**与真值同构。
本脚本的目的正是**把这一同构暴露出来**，而不是回避它。

用法: python ablate_direct_observe.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADJ = ("v3", "direct_only", "direct_observe")


def confused(truth: str, alarm: bool) -> str:
    if truth == "bola":
        return "TP" if alarm else "FN"
    return "FP" if alarm else "TN"


def main():
    recs = [json.loads(l) for l in (RESULTS / "raw_matrix.jsonl").open(encoding="utf-8") if l.strip()]
    recs = [r for r in recs if "error" not in r]
    probe_cache = json.loads((RESULTS / "ablation_direct.json").read_text(encoding="utf-8"))["probe_cache"]

    tally = {a: defaultdict(int) for a in ADJ}
    per_scen = {a: defaultdict(lambda: defaultdict(int)) for a in ADJ}
    agree = defaultdict(int)   # v3 与 direct_observe 的裁决一致性

    for r in recs:
        truth = r["truth"]["truth"]
        sc = r["scenario"]
        st = probe_cache.get(f'{r["config"]["label"]}|{sc}', {}).get(r["action"]["op"], "unavailable")
        observed_200 = bool(r["truth"]["app_allowed"])          # = 普通请求是否 200

        alarms = {
            "v3": r["verdicts"]["v3"]["verdict"] == "violation-proven",
            "direct_only": st == "none",
            "direct_observe": (st == "none") and observed_200,
        }
        # 若授权面不可读，direct 两法均弃权
        if st == "unavailable":
            alarms["direct_only"] = False
            alarms["direct_observe"] = False

        for a in ADJ:
            cell = confused(truth, alarms[a])
            tally[a][cell] += 1
            per_scen[a][sc][cell] += 1

        agree["same"] += int(alarms["v3"] == alarms["direct_observe"])
        agree["diff"] += int(alarms["v3"] != alarms["direct_observe"])

    print("=" * 70)
    print("端到端混淆矩阵（alarm = 升级为 violation-proven）")
    print("=" * 70)
    for a in ADJ:
        t = tally[a]
        tp, fp, fn, tn = t["TP"], t["FP"], t["FN"], t["TN"]
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        print(f"{a:16s} TP={tp:4d} FP={fp:4d} FN={fn:4d} TN={tn:4d}  "
              f"P={prec:.4f}  R={rec:.4f}")

    print("\n" + "=" * 70)
    print("逐场景")
    print("=" * 70)
    print(f"{'scen':6s} | {'v3':>18s} | {'direct_only':>18s} | {'direct_observe':>18s}")
    for sc in sorted({r["scenario"] for r in recs}):
        def cell(a):
            d = per_scen[a][sc]
            return f"{d['TP']:>3d}/{d['FP']:>3d}/{d['FN']:>3d}/{d['TN']:>3d}"
        print(f"{sc:6s} | {cell('v3'):>18s} | {cell('direct_only'):>18s} | {cell('direct_observe'):>18s}")

    print(f"\nv3 vs direct_observe 裁决一致: {agree['same']} / 不一致: {agree['diff']}")

    out = {"note": "direct_observe = 用普通请求的 HTTP 200 作访问证据（非变形）",
           "tally": {a: dict(tally[a]) for a in ADJ},
           "per_scenario": {a: {sc: dict(per_scen[a][sc]) for sc in per_scen[a]} for a in ADJ},
           "agreement_v3_vs_direct_observe": dict(agree)}
    (RESULTS / "ablation_direct_observe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] -> {RESULTS / 'ablation_direct_observe.json'}")


if __name__ == "__main__":
    main()
