# -*- coding: utf-8 -*-
"""
把「R1.9 多类独立授权缺陷」实验（run_multiclass.py）并入论文数字流水线。
=====================================================================

输入：experiments/real_system/results/seeded_multiclass.json
输出：04_绘图与分析/results/multiclass_table.tex （宏 + 表体）

设计：每个实例的真值来自靶机正确模型（intended_perm），观测来自实际请求，
与真实系统实验同一套 alarm 公式。误报按**通道**分开：读 23 格、写 16 格、
授予 7 格，读格不能代替写格与授予格。

本脚本**不信任**缓存 summary：先从逐例实例记录与逐条负例记录重算，逐字段与
summary 比对，有任何分歧就拒绝出数（SystemExit）。这样"35/35 逐字节一致"证明的
是管线稳定，而这里的交叉校验证明汇总确实由逐条记录推出。

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
CHANNEL = {"C1": "read", "C2": "write", "C3": "read", "C4": "grant"}
METHODS = ("mr_bookkeeping", "v3", "v3_channel", "direct_observe",
           "direct_observe_channel", "direct_only")


def recompute_per_class(inst: list[dict]) -> dict:
    out = {}
    for cls, _ in ROWS:
        rows = [r for r in inst if r["class"] == cls]
        out[cls] = {
            "n": len(rows),
            "mr_read": sum(1 for r in rows if r["mr_read"]),
            "mr_channel": sum(1 for r in rows if r["mr_channel"]),
            "detected": {m: sum(1 for r in rows if r["alarms"][m]) for m in METHODS},
        }
    return out


def recompute_negatives(neg: dict[str, list], shared: dict | None = None) -> dict:
    shared = shared or {}
    out = {}
    for ch, rows in neg.items():
        n = len(rows)
        out[ch] = {
            "n": n,
            "relation": sum(1 for r in rows if r["alarms"]["relation"]),
            "relation_oracle": sum(1 for r in rows if r["alarms"]["relation_oracle"]),
            "oracle_only": sum(1 for r in rows if r["alarms"]["oracle_only"]),
            "requests": sum(r["requests"] for r in rows) + shared.get(ch, 0),
            "shared_requests": shared.get(ch, 0),
        }
    return out


def recompute_loo(data: dict) -> dict:
    """从 runs 的逐实例记录重算逐方法留一法。"""
    full = data["runs"]["all"]["instances"]
    out: dict = {}
    for cls, _ in ROWS:
        off = data["runs"][f"without_{cls}"]["instances"]
        own_on = [r for r in full if r["class"] == cls]
        own_off = [r for r in off if r["class"] == cls]
        other_off = [r for r in off if r["class"] != cls]
        out[cls] = {}
        for meth in ("mr_read", "v3_channel", "direct_observe_channel"):
            def hit(r, m=meth):
                return bool(r["mr_read"]) if m == "mr_read" else bool(r["alarms"][m])
            out[cls][meth] = {"active": sum(1 for r in own_on if hit(r)),
                              "disabled": sum(1 for r in own_off if hit(r)),
                              "other_retained": sum(1 for r in other_off if hit(r))}
    return out


def cross_check(data: dict) -> tuple[dict, dict, dict]:
    """逐条记录 ↔ 缓存 summary 的机械比对；不一致即拒绝出数。"""
    per = recompute_per_class(data["runs"]["all"]["instances"])
    cached = data["summary"]["per_class"]
    for cls, _ in ROWS:
        for k in ("n", "mr_read", "mr_channel"):
            if per[cls][k] != cached[cls][k]:
                raise SystemExit(f"[FAIL] {cls}.{k}: records {per[cls][k]} vs "
                                 f"summary {cached[cls][k]}")
        for m in METHODS:
            if per[cls]["detected"][m] != cached[cls]["detected"][m]:
                raise SystemExit(f"[FAIL] {cls}.detected.{m}: records "
                                 f"{per[cls]['detected'][m]} vs summary "
                                 f"{cached[cls]['detected'][m]}")

    neg = recompute_negatives(data["runs"]["all"]["negatives"],
                              data["runs"]["all"].get("neg_shared_requests"))
    cneg = data["summary"]["negatives"]
    for ch, got in neg.items():
        if ch not in cneg:
            raise SystemExit(f"[FAIL] channel {ch} in records but not in summary")
        for k, v in got.items():
            if cneg[ch][k] != v:
                raise SystemExit(f"[FAIL] negatives[{ch}].{k}: records {v} vs "
                                 f"summary {cneg[ch][k]}")

    loo = recompute_loo(data)
    cloo = data["summary"].get("leave_one_out_by_method")
    if cloo is None:
        raise SystemExit("[FAIL] summary has no leave_one_out_by_method; re-run "
                         "run_multiclass.py (the per-method split is required by "
                         "Section V-D)")
    for cls, _ in ROWS:
        for meth, vals in loo[cls].items():
            for k, v in vals.items():
                if cloo[cls][meth].get(k) != v:
                    raise SystemExit(f"[FAIL] loo[{cls}][{meth}].{k}: records {v} vs "
                                     f"summary {cloo[cls][meth].get(k)}")
    return per, neg, loo


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    per, neg, loo = cross_check(data)
    fp = data["summary"]["fp"]
    fp_den = data["summary"]["fp_denominator"]
    inst = data["runs"]["all"]["instances"]

    # 每个实例都必须是"正确模型说 none"的正例
    bad = [r for r in inst if r["truth_permission"] != "none"]
    if bad:
        raise SystemExit(f"[FAIL] {len(bad)} instance(s) not unauthorized under the "
                         f"correct model: {[r['object'] for r in bad][:3]}")

    n_total = sum(per[c]["n"] for c, _ in ROWS)
    read_hits = sum(per[c]["mr_read"] for c, _ in ROWS)
    chan_hits = sum(per[c]["mr_channel"] for c, _ in ROWS)
    oracle_read = sum(per[c]["detected"]["direct_observe"] for c, _ in ROWS)
    oracle_chan = sum(per[c]["detected"]["direct_observe_channel"] for c, _ in ROWS)
    v3_read = sum(per[c]["detected"]["v3"] for c, _ in ROWS)
    v3_chan = sum(per[c]["detected"]["v3_channel"] for c, _ in ROWS)

    n_read, n_write, n_grant = neg["read"]["n"], neg["write"]["n"], neg["grant"]["n"]
    fp_rel = {"read": neg["read"]["relation"], "write": neg["write"]["relation"],
              "grant": neg["grant"]["relation"]}
    fp_orc = {"read": neg["read"]["oracle_only"], "write": neg["write"]["oracle_only"],
              "grant": neg["grant"]["oracle_only"]}

    def pct(x: int, n: int) -> str:
        return f"{100.0 * x / n:.2f}" if n else "0.00"

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
    cmd("Classes", len(ROWS))
    cmd("NegRead", n_read)
    cmd("NegWrite", n_write)
    cmd("NegGrant", n_grant)
    cmd("FpRelRead", fp_rel["read"])
    cmd("FpRelWrite", fp_rel["write"])
    cmd("FpRelGrant", fp_rel["grant"])
    cmd("FprRelRead", pct(fp_rel["read"], n_read))
    cmd("FprRelWrite", pct(fp_rel["write"], n_write))
    cmd("FprRelGrant", pct(fp_rel["grant"], n_grant))
    cmd("FpOracleMax", max(fp_orc.values()))
    _rate = max((fp_orc[ch] / neg[ch]["n"] for ch in fp_orc if neg[ch]["n"]), default=0.0)
    cmd("FprOracleMax", f"{100.0 * _rate:.2f}")
    def attributed(meth: str) -> int:
        """有"关掉该类 ⇒ 该链路从有告警变无告警"的类别数。"""
        return sum(1 for c, _ in ROWS
                   if loo[c][meth]["active"] > 0 and loo[c][meth]["disabled"] == 0)

    cmd("LooReadClasses", attributed("mr_read"))
    cmd("LooChannelClasses", attributed("v3_channel"))
    cmd("LooAdjudicatorClasses", attributed("direct_observe_channel"))
    cmd("ReqNegRead", neg["read"]["requests"])
    cmd("ReqNegWrite", neg["write"]["requests"])
    cmd("ReqNegGrant", neg["grant"]["requests"])
    cmd("FpBookkeeping", fp["mr_bookkeeping"])   # 合并读通道口径，供横向对照
    cmd("AuthorizedCells", fp_den)

    # ---- 表体 ----
    body = []
    body.append(r"\begin{table*}[t]")
    body.append(r"\centering")
    body.append(
        r"\caption{Per-class recall and per-channel false alarms of the studied chain on "
        r"the controlled target. Each instance is a cell whose true (correct-model) "
        r"permission is \emph{none} and on which the defect nevertheless lets the access "
        r"succeed. \emph{read gate} is the reachability-gated relation as studied in this "
        r"paper; \emph{channel gate} moves the same relation to the channel the defect "
        r"breaks; the next two columns are the oracle-consuming adjudicator on the read "
        r"channel and on the channel-matched probe. False alarms are counted on authorized "
        r"cells of the \emph{same} channel---\McNegRead{} read, \McNegWrite{} write and "
        r"\McNegGrant{} grant cells---because a read cell cannot stand in for a write or a "
        r"grant: write success is judged by the object's state changing, not by the status "
        r"code, and a grant only counts if the collaborator record appears. C1 and C3 share "
        r"the read negatives (marked $^{\dagger}$); C2 and C4 have their own. The relation "
        r"alarms on \McFpRelRead{} of \McNegRead{}, \McFpRelWrite{} of \McNegWrite{} and "
        r"\McFpRelGrant{} of \McNegGrant{} authorized cells, which is the in-band "
        r"bookkeeping failure the paper already reports; the oracle-based adjudicator "
        r"alarms on \McFpOracleMax{} of them. C1 is the class the gate was designed for. "
        r"C2 breaks a different channel, so the read relation cannot see it and the "
        r"channel-matched relation does. C3 and C4 falsify the antecedent---the subject can "
        r"already see the object---so the gate is silent on them end to end and they remain "
        r"undetected in the overall denominator; that is a mechanism explanation, not a "
        r"removal from the denominator. The oracle answers these recorded cases correctly; "
        r"that is soundness on this target, not independence, and no class is admitted as "
        r"an independent entitlement source under the admission rule of "
        r"Section~\ref{sec:admissibility}. The negative blocks cost \McReqNegRead{} read, "
        r"\McReqNegWrite{} write and \McReqNegGrant{} grant requests, counted at the "
        r"client rather than estimated per cell.}")
    body.append(r"\label{tab:multiclass}")
    body.append(r"\small")
    body.append(r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrrrr}")
    body.append(r"\toprule")
    body.append(r"Class & inst. & read gate & channel gate & oracle (read) & "
                r"oracle (channel) & relation FP & oracle FP \\")
    body.append(r"\midrule")
    for c, label in ROWS:
        e = per[c]
        ch = CHANNEL[c]
        dag = r"$^{\dagger}$" if c in ("C1", "C3") else ""
        body.append(
            f"{c}: {label} & {e['n']} & {e['mr_read']} & {e['mr_channel']} & "
            f"{e['detected']['direct_observe']} & "
            f"{e['detected']['direct_observe_channel']} & "
            f"{fp_rel[ch]}/{neg[ch]['n']}{dag} & {fp_orc[ch]}/{neg[ch]['n']}{dag} \\\\")
    body.append(r"\addlinespace[2pt]")
    body.append(f"\\emph{{total}} & {n_total} & {read_hits} & {chan_hits} & "
                f"{oracle_read} & {oracle_chan} & --- & --- \\\\")
    body.append(r"\bottomrule")
    body.append(r"\end{tabular*}")
    body.append(r"\end{table*}")

    header = (
        "% 由 analysis/ingest_multiclass.py 自动生成 —— 勿手改\n"
        "% 来源: experiments/real_system/results/seeded_multiclass.json (run_multiclass.py)\n"
        "% 真值 = 靶机正确模型 intended_perm；观测 = 实际请求；与真实系统同一套 alarm 公式。\n"
        "% 汇总由逐例/逐条负例记录重算并交叉校验；不一致时本脚本拒绝出数。\n"
    )
    (OUT / "multiclass_numbers.tex").write_text(
        header + "\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "multiclass_table.tex").write_text(
        "% 由 analysis/ingest_multiclass.py 自动生成 —— 勿手改\n"
        "% 宏由调用方在导言区 \\input{multiclass_numbers.tex} 加载；此处不再重复\n"
        "% （\\newcommand 重复定义会报 Command already defined）。\n"
        + "\n".join(body) + "\n", encoding="utf-8")
    print(f"[ok] -> {OUT / 'multiclass_table.tex'}")
    print(f"instances={n_total} read={read_hits} channel={chan_hits} "
          f"oracle_read={oracle_read} oracle_channel={oracle_chan}")
    print(f"negatives: read={n_read} write={n_write} grant={n_grant}; "
          f"relation FP={fp_rel} oracle FP={fp_orc}")
    # 一致性自检：每类实例数必须与登记表一致
    declared = data["meta"]["classes"]
    assert all(len(declared[c]["instances"]) == per[c]["n"] for c, _ in ROWS), \
        "instance count mismatch between registry and results"


if __name__ == "__main__":
    main()
