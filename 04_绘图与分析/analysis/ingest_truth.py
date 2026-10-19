"""
R1.2 / R1.5 / R2.3 · 两条关系的显式谓词与真值表
================================================================

审稿人原话（本轮决定信 §5）：

    "A truth-table derivation or explicit functional representation of each
     predicate would make the argument more rigorous and clarify its
     applicability beyond the particular implementation."

以及 §2：

    "Define the decision variables and truth conditions for every possible
     combination of request outcome, actual entitlement, oracle response, and
     detector verdict."

本脚本做三件事，缺一不可：

1. **把判定式写成布尔函数**，并在**全部已落盘记录**上复核它逐条成立
   （合成研究 576 条、真时序 712 格）。不是"我们认为它是这样"，是"它在每条
   记录上都等于记录下来的 triggered"。
2. **枚举真值表**：E（台账授权）× Y（请求效果）× M（爬取期可达模型）×
   O（oracle 答案，含"无 definite answer"）。每一行同时给出 A（关系报警）
   与 D（直接裁决器）的值，以及该行在实测数据里落了多少格。
3. **导出 LaTeX**（表 + 宏）。表里的数字全部由数据算出，宏亦然。

记号
----
  y = 1  ⟺ 普通请求成功（未返回错误）
  m = 1  ⟺ 爬取期可达模型把该对象列给该主体
  o = 1  ⟺ oracle 回答 allow；o = ⊥ ⟺ 不给出确定答案
  A      = 关系报警（MR-002 与 MR-004 在本域上同为一个函数）
  D      = 直接裁决器：o = deny ∧ y
  E      = 台账授权（allow / deny），只用于裁决，不进入 A 或 D

关键结论（代数部分，仅为两行）
------------------------------
  A = y ∧ ¬m        D = y ∧ ¬o   ⇒   A = D  ⟺  m = o
所以命题 2 的全部内容在经验前提"m = o"，不在代数。表的作用是把这条前提和它
失效的两行摆出来，并指出这两行分别对应**两种不同的失效机制**：
  row 6（m=1, o=0）：模型对、oracle 错 → 只有 D 假报警（oracle 不健全）
  row 7（m=0, o=1）：模型错、oracle 对 → 只有 A 假报警（模型陈旧）

用法: python 04_绘图与分析/analysis/ingest_truth.py
"""

from __future__ import annotations

import json
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
MATRIX = PROJ / "experiments" / "results" / "raw_matrix.jsonl"
TEMP = PROJ / "experiments" / "real_system" / "results" / "temporal"
OUT_NUM = PROJ / "04_绘图与分析" / "results" / "truth_numbers.tex"
OUT_TAB = PROJ / "04_绘图与分析" / "results" / "truth_table.tex"

# 真值表的 12 行：(y, m, o) —— o 取 "allow" / "deny" / None(⊥)
ROWS = [
    (0, 0, "deny"), (0, 1, "deny"),
    (0, 0, "allow"), (0, 1, "allow"),
    (1, 0, "deny"), (1, 1, "deny"),
    (1, 0, "allow"), (1, 1, "allow"),
    (0, 0, None), (0, 1, None),
    (1, 0, None), (1, 1, None),
]

# 每一行在台账上的读法，按 E 分列（与 n_deny / n_allow 两列一一对应）
CLASS = {
    (0, 0, "deny"):  r"no access",
    (0, 1, "deny"):  r"no access",
    (0, 0, "allow"): r"no access",
    (0, 1, "allow"): r"no access",
    (1, 0, "deny"):  r"true positive / false proof",
    (1, 1, "deny"):  r"miss / false proof by $D$",
    (1, 0, "allow"): r"true positive / false proof",
    (1, 1, "allow"): r"miss / correct silence",
    (0, 0, None):    r"no oracle; no access",
    (0, 1, None):    r"no oracle; no access",
    (1, 0, None):    r"no oracle; alarm",
    (1, 1, None):    r"no oracle; miss / silence",
}


def load_matrix() -> list[dict]:
    rows = [json.loads(l) for l in MATRIX.open(encoding="utf-8") if l.strip()]
    return [r for r in rows if "error" not in r]


def verify_predicates(recs: list[dict]) -> dict:
    """把两条关系写成布尔函数，在每条记录上与记录的 triggered 比对。"""
    bad002 = bad004 = 0
    flat002 = flat_bad = 0
    for r in recs:
        m = r["mr_result"]
        if m["mr"] == "MR-002":
            f = (m["precondition_met"] and not m["isError_out1"]
                 and m["out1_equals_out2"])
            if f != m["triggered"]:
                bad002 += 1
            # 本域上的简化式 A = y ∧ ¬m
            y = m["input2"]["status"] < 400
            mm = m["ph_gui_reachable_for_follower"]
            if (y and not mm) != m["triggered"]:
                flat_bad += 1
            flat002 += 1
        else:
            f = (not m["isError_out2"]) and (not m["userCanRetrieveContent"])
            if f != m["triggered"]:
                bad004 += 1
    return {"bad002": bad002, "bad004": bad004, "flat_bad": flat_bad,
            "n002": flat002, "n": len(recs)}


def temporal_cells() -> list[dict]:
    out = []
    for name in ("gitea", "gitlab"):
        d = json.loads((TEMP / f"temporal_{name}.json").read_text(encoding="utf-8"))
        for t in d["transitions"]:
            for c in t["cells"]:
                if c["role"] != "cross":
                    continue
                o = c.get("oracle_answer")
                if o not in ("allow", "deny"):
                    o = None
                y = 1 if c["observed_effect"] == "allow" else 0
                m = 1 if c["M0_reachable"] else 0
                e = "allow" if c["expected_entitlement"] == "allow" else "deny"
                a = 1 if c["A_stale"] else 0
                # 逐格复核 A = y ∧ ¬m
                assert a == (y and not m), (name, c["case_id"], a, y, m)
                out.append({"system": name, "e": e, "y": y, "m": m,
                            "o": o, "a": a, "cell": c})
    return out


def tally(cells: list[dict]) -> dict:
    t = {k: {"deny": 0, "allow": 0} for k in ROWS}
    for c in cells:
        t[(c["y"], c["m"], c["o"])][c["e"]] += 1
    return t


def main() -> None:
    recs = load_matrix()
    ver = verify_predicates(recs)
    cells = temporal_cells()
    t = tally(cells)

    total = sum(v["deny"] + v["allow"] for v in t.values())
    assert total == len(cells), (total, len(cells))

    # ---- 派生量 -------------------------------------------------------
    readable = sum(v["deny"] + v["allow"] for k, v in t.items() if k[2] is not None)
    unread = total - readable
    # 一致性按**裁决**比，不按 (m,o) 比：y=0 时 A=D=0 恒成立，即使 m≠o。
    agree = sum(v["deny"] + v["allow"] for k, v in t.items()
                if k[2] is not None
                and int(k[0] and not k[1]) == int(k[0] and k[2] == "deny"))
    disagree = readable - agree
    model_wrong = t[(1, 0, "allow")]["deny"] + t[(1, 0, "allow")]["allow"]
    oracle_wrong = t[(1, 1, "deny")]["deny"] + t[(1, 1, "deny")]["allow"]
    both_wrong = t[(1, 0, "deny")]["deny"] + t[(1, 0, "deny")]["allow"]
    alarms = sum(v["deny"] + v["allow"] for k, v in t.items() if k[0] == 1 and k[1] == 0)

    # ---- 合成研究：aware / blind 两种模型语义的对照 --------------------
    def conf(mode: str) -> tuple[int, int, int, int]:
        tp = fp = fn = tn = 0
        for r in recs:
            if r["gui_mode"] != mode:
                continue
            e = r["truth"]["should_allow"]
            y = r["truth"]["app_allowed"]
            a = r["mr_result"]["triggered"]
            if not e and y and a:
                tp += 1
            elif not e and y and not a:
                fn += 1
            elif e and y and a:
                fp += 1
            else:
                tn += 1
        return tp, fp, fn, tn

    aw = conf("aware")
    bl = conf("blind")

    print("=" * 72)
    print("谓词复核")
    print("=" * 72)
    print(f"  记录 {ver['n']} 条：MR-004 全式不符 {ver['bad004']} 条，"
          f"MR-002 全式不符 {ver['bad002']} 条")
    print(f"  MR-002 简化式 A=y∧¬m 在 {ver['n002']} 条上不符 {ver['flat_bad']} 条")
    assert ver["bad002"] == ver["bad004"] == ver["flat_bad"] == 0, ver
    print("  ⇒ 两条关系的判定式与实现逐条一致")

    print("=" * 72)
    print("真值表（时序 712 格）")
    print("=" * 72)
    print(f"  {'Y':>6} {'M':>7} {'O':>6} {'A':>2} {'D':>2}  {'E=deny':>7} {'E=allow':>7}")
    for k in ROWS:
        y, m, o = k
        d = "-" if o is None else int(y and o == "deny")
        a = int(y and not m)
        print(f"  {['deny','allow'][y]:>6} {'block' if not m else 'reach':>7} "
              f"{o or '--':>6} {a:>2} {d:>2}  {t[k]['deny']:>7} {t[k]['allow']:>7}")
    print(f"  合计 {total}（可读 oracle {readable}，不可读 {unread}）")
    print(f"  裁决一致 {agree} 格，不一致 {disagree} 格")
    print(f"    失真来源：模型错、oracle 对 {model_wrong}；oracle 错、模型对 {oracle_wrong}；"
          f"两者同错 {both_wrong}")
    print(f"  关系报警总数 {alarms}")
    assert agree + disagree == readable
    assert disagree == model_wrong + oracle_wrong, (disagree, model_wrong, oracle_wrong)
    assert alarms == 29, alarms

    print("=" * 72)
    print("合成研究：模型语义对照（各 288 条）")
    print("=" * 72)
    print(f"  aware  TP{aw[0]} FP{aw[1]} FN{aw[2]} TN{aw[3]}")
    print(f"  blind  TP{bl[0]} FP{bl[1]} FN{bl[2]} TN{bl[3]}")
    print(f"  ⇒ 可达模型项：少 {bl[0]-aw[0]} 个检出，少 {bl[1]-aw[1]} 个假告警")

    # ---- 宏 -----------------------------------------------------------
    M = {
        "TvtRecords": ver["n"],
        "TvtMrTwo": ver["n002"],
        "TvtCells": total,
        "TvtReadable": readable,
        "TvtUnreadable": unread,
        "TvtAgree": agree,
        "TvtDisagree": disagree,
        "TvtModelWrong": model_wrong,
        "TvtOracleWrong": oracle_wrong,
        "TvtBothWrong": both_wrong,
        "TvtAlarms": alarms,
        "TvtUnreadAlarms": t[(1, 0, None)]["allow"] + t[(1, 0, None)]["deny"],
        "TvtConAware": sum(aw),
        "TvtConTP": aw[0], "TvtConFP": aw[1], "TvtConFN": aw[2], "TvtConTN": aw[3],
        "TvtBlindTP": bl[0], "TvtBlindFP": bl[1],
        "TvtBlindFN": bl[2], "TvtBlindTN": bl[3],
        "TvtModelCostTP": bl[0] - aw[0],
        "TvtModelSaveFP": bl[1] - aw[1],
    }
    lines = ["% 由 04_绘图与分析/analysis/ingest_truth.py 生成，勿手改",
             "% R1.2 / R1.5 / R2.3：两条关系的判定式复核与真值表人口普查"]
    for k, v in M.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    OUT_NUM.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- 表 -----------------------------------------------------------
    def cell(v: int) -> str:
        return str(v) if v else r"\textperiodcentered"

    tab = [
        "% 由 04_绘图与分析/analysis/ingest_truth.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{The truth table of the two relations, with the temporal cells "
        r"that fall in each row. $Y$: the ordinary request succeeds. $M$: the "
        r"crawl-time model lists the object for the subject. $O$: the "
        r"introspection surface's answer, an em dash meaning it returns no "
        r"definite answer. $A$: the alarm of either relation; on this domain both "
        r"reduce to $y\wedge\neg m$. $D$: the direct adjudicator, "
        r"$y\wedge\neg o$, undefined in rows 9--12. The count columns split each "
        r"row by the ledger's entitlement $E$, so every row states its truth "
        r"conditions for both values of $E$; a dot is an unrealised combination, "
        r"and in the verdict column the first term reads $E{=}$deny and the "
        r"second $E{=}$allow. Where $D$ is defined the two verdicts coincide "
        r"whenever $Y{=}$deny or $M{=}O$, and part only in the two rows with "
        r"$Y{=}$allow and $M\ne O$---\TvtDisagree{} of the \TvtReadable{} "
        r"readable cells. Those two rows are the two failure mechanisms that "
        r"Section~\ref{sec:gogs} keeps apart: in row 6 the model is right and the "
        r"oracle wrong, so $D$ alone raises a false proof; in row 7 the model is "
        r"stale and the oracle right, so the relation alone does. Row 5 is the "
        r"case neither explains---both surfaces answer \emph{deny} on a cell the "
        r"ledger allows, both verdicts are false proofs, and their agreement "
        r"certifies nothing.}",
        r"\label{tab:truth}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llllccp{1.60in}rr@{}}",
        r"\toprule",
        r"$Y$ & $M$ & $O$ & $A$ & $D$ & verdict at the ledger "
        r"& $E{=}\mathrm{deny}$ & $E{=}\mathrm{allow}$ \\",
        r"\midrule",
    ]
    for i, k in enumerate(ROWS):
        y, m, o = k
        if i == 8:
            tab.append(r"\midrule")
        a = int(y and not m)
        d = r"\textemdash" if o is None else str(int(y and o == "deny"))
        tab.append(
            f"{['deny','allow'][y]} & {'reach' if m else 'blocked'} & "
            f"{o or r'\textemdash'} & {a} & {d} & {CLASS[k]} & {cell(t[k]['deny'])} & "
            f"{cell(t[k]['allow'])} \\\\")
    tab += [
r"\bottomrule", r"\end{tabular*}", r"\end{table*}"]
    OUT_TAB.write_text("\n".join(tab) + "\n", encoding="utf-8")

    print("=" * 72)
    print(f"写出 {OUT_NUM.name}（{len(M)} 个宏）与 {OUT_TAB.name}（12 行）")


if __name__ == "__main__":
    main()
