"""
R1.13 · 弃权、覆盖率、选择性风险与运行成本
============================================================
审稿原文:
    "The state-calibrated method achieves perfect precision in the pooled table
     by abstaining when the oracle is unavailable, while missing 111 true
     violations. Precision and recall alone do not adequately characterize this
     selective behavior. Please report coverage, selective risk, abstention
     rate, and detection performance conditional on oracle availability,
     alongside execution time and request overhead. The discussion should also
     distinguish a safe abstention from a successful detection and avoid ranking
     methods primarily by metrics that reward non-decision."

为什么要另立一张表:
    Table tab:ablation 是**关于告警**的 2x2 混淆：弃权被记成"未告警"，于是
    落在 TN 或 FN 里，精度 1.00 看上去像能力。本表改按**裁决**计分：
      decided   = verdict ∈ {pass, violation-proven}
      abstained = verdict = indeterminate
      coverage  = decided / N
      selective risk = (FP + FN among decided) / decided
    并把弃权按"弃在违规上/弃在正常上"以及 v3 的两种理由拆开。

口径:
    * v3 的弃权有两种理由（见 boundary_aware.adjudicate）：
        - 自省面不可读                      -> 结构性弃权
        - 自省面可读，且显示存在可覆盖授权   -> 把本会是假确证的告警降级
      后一种不是"没得读"，恰恰是精度 1.00 的另一半来源，必须单列。
    * direct_only / direct_observe 与 v3 共用同一条"不可读则弃权"合同：
      探针返回 unavailable 时它们**不裁决**（原直接裁决代码即如此，真值表也
      把该层的 D 记为 undefined）。故 coverage = 312/576。
      若需要二值参照，另列 direct_observe（forced negative）：不可读时判"无违规"，
      coverage 才是 1，其 108 个漏报是**被迫判负**的产物，不能当作该方法的能力。
    * 运行时间：构造研究是离线重放同一条记录交换，墙钟时间只反映重放循环，
      不作为系统成本上报。真正端到端跑过的是时序闭环，其分段耗时从
      temporal_*.json 的 t_freeze/t_mutation/t_recrawl/t_probe 直接算出。

用法: python ingest_coverage.py
输出: results/coverage_numbers.tex, results/coverage_table.tex
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
RES = PROJ / "experiments" / "results"
OUT = HERE.parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROBLEMS: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        PROBLEMS.append(f"[FAIL] {name}: recomputed={got!r} != on-disk={want!r}")
        print(f"  !! {name}: {got!r} != {want!r}")
    else:
        print(f"  ok {name} = {got!r}")


def macro(path: Path, name: str):
    if not path.exists():
        return None
    m = re.search(rf"\\newcommand{{\\{name}\}}{{([^}}]*)}}", path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def f2(x: float) -> str:
    return f"{x:.2f}"


def load() -> list[dict]:
    rows = [json.loads(l) for l in (RES / "raw_matrix.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if "error" not in r]


def main() -> None:
    rows = load()
    N = len(rows)
    nums = OUT / "numbers.tex"

    # ---------- direct_* 的二值判据（与 compute_all.py Block 9 同规则） ----------
    probe = json.loads((RES / "ablation_direct.json").read_text(encoding="utf-8"))["probe_cache"]

    def state(r):
        return probe.get(f'{r["config"]["label"]}|{r["scenario"]}', {}).get(r["action"]["op"], "unavailable")

    # ---------- 逐方法计分 ----------
    METHODS = ("raw", "v1", "v2", "v3", "degrade_all", "direct_only",
               "direct_observe", "obs_forced")
    tally = {m: Counter() for m in METHODS}
    joint_decided = 0

    for r in rows:
        bola = r["truth"]["truth"] == "bola"
        for m in ("raw", "v1", "v2", "v3", "degrade_all"):
            v = r["verdicts"][m]["verdict"]
            if v == "indeterminate":
                tally[m]["abstain_bola" if bola else "abstain_normal"] += 1
            elif v == "violation-proven":
                tally[m]["TP" if bola else "FP"] += 1
            else:
                tally[m]["FN" if bola else "TN"] += 1
        s = state(r)
        ok = bool(r["truth"]["app_allowed"])
        # ★ 两个 direct 方法的判据必须与 compute_all.py Block 9 的原定义逐字一致：
        #   direct_only    = 仅 oracle 报 none（不看请求是否成功）
        #   direct_observe = oracle 报 none 且普通请求成功
        # 早先版本把 ok 条件同时加给了两者，等于给 direct_only 偷换了判定规则
        # （把 108 条"无实际越权效果的无效违规声明"悄悄清零）。
        alarm_direct = s == "none"
        alarm_obs = s == "none" and ok
        if s == "unavailable":
            # 与直接裁决代码一致：不可读 -> indeterminate，不强行判负
            for m in ("direct_only", "direct_observe"):
                tally[m]["abstain_bola" if bola else "abstain_normal"] += 1
            tally["direct_only"]["forced"] += 1
        else:
            tally["direct_only"]["TP" if (bola and alarm_direct)
                                  else "FN" if bola
                                  else "FP" if alarm_direct else "TN"] += 1
            if alarm_direct and not bola:
                # FP 细分：请求实际被拒（无越权效果）= 无效违规声明；
                # 请求实际被允许且无授权依据 = 严格假确证（E=allow 方向）。
                tally["direct_only"]["fp_no_effect" if not ok else "fp_effect"] += 1
            tally["direct_observe"]["TP" if (bola and alarm_obs)
                                    else "FN" if bola
                                    else "FP" if alarm_obs else "TN"] += 1
        # 明确命名的二值参照：不可读时判"无违规"（与 direct_observe 同判据）
        tally["obs_forced"]["TP" if (bola and alarm_obs) else "FN" if bola else "FP" if alarm_obs else "TN"] += 1
        # 共同判定集合：v3 与 direct_only 都做出裁决的记录数
        if r["verdicts"]["v3"]["verdict"] != "indeterminate" and s != "unavailable":
            joint_decided += 1

    summary = {}
    for m in METHODS:
        t = tally[m]
        dec = t["TP"] + t["FP"] + t["FN"] + t["TN"]
        abst = t["abstain_bola"] + t["abstain_normal"]
        err = t["FP"] + t["FN"]
        summary[m] = {
            "decided": dec, "abstained": abst,
            "abst_bola": t["abstain_bola"], "abst_normal": t["abstain_normal"],
            "TP": t["TP"], "FP": t["FP"], "FN": t["FN"], "TN": t["TN"],
            "coverage": dec / N, "risk": err / dec if dec else 0.0,
        }
        s = summary[m]
        print(f"  {m:15} decided={s['decided']:3} cover={s['coverage']:.3f} abst={s['abstained']:3} "
              f"({s['abst_bola']}/{s['abst_normal']}) TP={s['TP']:3} FP={s['FP']:3} "
              f"FN={s['FN']:3} risk={s['risk']:.3f}")

    # 与已落盘宏交叉校验（表 tab:ablation / tab:stratum 的数必须一致）
    check("AbRawFP", summary["raw"]["FP"], int(macro(nums, "ResAbRawFP")))
    check("AbVThreeTP", summary["v3"]["TP"], int(macro(nums, "ResAbVThreeTP")))
    # 已落盘的 FN 宏把弃权也算作 FN（2x2 是关于告警的）；本表只把 pass 记作 FN。
    # 二者之差必须正好等于"弃在违规上"的条数，否则口径对不上。
    check("AbVThreeFN = pass-miss + abstain-on-violation",
          summary["v3"]["FN"] + summary["v3"]["abst_bola"], int(macro(nums, "ResAbVThreeFN")))
    check("AbDirectObserveTP", summary["direct_observe"]["TP"], int(macro(nums, "ResAbDirectObserveTP")))
    check("AbDirectObserveFP", summary["direct_observe"]["FP"], int(macro(nums, "ResAbDirectObserveFP")))
    # ★ 跨表方法判定一致性（R1.13 整改）：tab:coverage 与 tab:ablation 对同一方法
    #   必须使用同一判据。tab:ablation（compute_all Block 9）把不可读记为"未告警"
    #   （落在 FN/TN），tab:coverage 把不可读记为弃权，故两表的 decided 单元
    #   （TP/FP）必须相等，且 FN/TN 之差必须正好等于弃权拆分。
    stored_abl = json.loads((RES / "ablation_direct_observe.json").read_text(encoding="utf-8"))["tally"]
    for m in ("direct_only", "direct_observe"):
        check(f"XTable {m}.TP", summary[m]["TP"], stored_abl[m].get("TP", 0))
        check(f"XTable {m}.FP", summary[m]["FP"], stored_abl[m].get("FP", 0))
        check(f"XTable {m}.FN + abstain_bola", summary[m]["FN"] + summary[m]["abst_bola"],
              stored_abl[m].get("FN", 0))
        check(f"XTable {m}.TN + abstain_normal", summary[m]["TN"] + summary[m]["abst_normal"],
              stored_abl[m].get("TN", 0))
    assert summary["v3"]["abstained"] == 228, summary["v3"]

    # ---------- v3 弃权按理由拆 ----------
    reason = Counter()
    for r in rows:
        v = r["verdicts"]["v3"]
        if v["verdict"] != "indeterminate":
            continue
        kind = ((v.get("witness") or {}).get("sut_introspection") or "?")
        reason[(kind, r["truth"]["truth"])] += 1
    unread = reason[("unavailable", "bola")] + reason[("unavailable", "normal")]
    cover = reason[("readable", "bola")] + reason[("readable", "normal")]
    print(f"  v3 abstentions: unreadable={unread} covering={cover}")
    assert unread + cover == summary["v3"]["abstained"]
    assert reason[("readable", "bola")] == 0

    # ---------- v2 的假确证被 v3 以何种方式避免 ----------
    # 这是"精度 1.00 从哪来"的精确回答：v2 的 60 个假确证，v3 用两种弃权各挡掉一部分。
    v2_fp = [r for r in rows if r["truth"]["truth"] == "normal"
             and r["verdicts"]["v2"]["verdict"] == "violation-proven"]
    cov_reason = {}
    for r in v2_fp:
        v = r["verdicts"]["v3"]
        w = v.get("witness") or {}
        cov_reason[(v["verdict"], w.get("sut_introspection"))] = cov_reason.get(
            (v["verdict"], w.get("sut_introspection")), 0) + 1
    fp_unread = cov_reason.get(("indeterminate", "unavailable"), 0)
    fp_cover = cov_reason.get(("indeterminate", "readable"), 0)
    print(f"  v2 false proofs {len(v2_fp)}: v3 declines {fp_unread} as unreadable, "
          f"{fp_cover} as covering")
    assert fp_unread + fp_cover + cov_reason.get(("violation-proven", None), 0) + \
        cov_reason.get(("pass", None), 0) == len(v2_fp), cov_reason

    # ---------- 成本 ----------
    reqs = [r["http_requests"] for r in rows]
    probe_cells = len(probe)
    probe_gets = sum(len(v) for v in probe.values())
    print(f"  requests total={sum(reqs)} median={statistics.median(reqs)} range={min(reqs)}-{max(reqs)}")
    print(f"  probe cells={probe_cells} gets={probe_gets}")

    # 时序闭环的分段耗时（真实执行，非重放）
    loops = {}
    for name in ("gitea", "gitlab"):
        p = RES.parent / "real_system" / "results" / "temporal" / f"temporal_{name}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        tot = []
        for t in d["transitions"]:
            a, b, c, e = (datetime.fromisoformat(t[k]) for k in
                          ("t_freeze", "t_mutation", "t_recrawl", "t_probe"))
            tot.append(((b - a).total_seconds(), (c - b).total_seconds(),
                        (e - c).total_seconds(), (e - a).total_seconds()))
        loops[name] = {
            "n": len(tot),
            "med_total": statistics.median(x[3] for x in tot),
            "med_mutation": statistics.median(x[0] for x in tot),
            "med_recrawl": statistics.median(x[1] for x in tot),
            "med_probe": statistics.median(x[2] for x in tot),
        }
        print(f"  loop {name}: {loops[name]}")

    # ---------- 宏 ----------
    M = {"CvgN": N, "CvgMethods": len(METHODS),
         "CvgReqTotal": sum(reqs), "CvgReqMean": f2(sum(reqs) / N),
         "CvgReqMin": min(reqs), "CvgReqMax": max(reqs),
         "CvgReqMedian": int(statistics.median(reqs)),
         "CvgProbeCells": probe_cells, "CvgProbeGets": probe_gets,
         "CvgProbePerRecord": f2(probe_gets / N),
         "CvgForced": tally["direct_only"]["forced"],
         "CvgVthreeUnread": unread, "CvgVthreeUnreadBola": reason[("unavailable", "bola")],
         "CvgVthreeUnreadNormal": reason[("unavailable", "normal")],
         "CvgVthreeCover": cover, "CvgVthreeCoverNormal": reason[("readable", "normal")],
         "CvgVthreeMissed": summary["v3"]["FN"],
         "CvgVthreeDetected": summary["v3"]["TP"],
         "CvgVthreeRisk": f2(summary["v3"]["risk"]),
         "CvgVthreeDecided": summary["v3"]["decided"],
         "CvgVthreeAbstain": summary["v3"]["abstained"],
         "CvgVthreeAbstBola": summary["v3"]["abst_bola"],
         "CvgVthreeAbstNormal": summary["v3"]["abst_normal"],
         "CvgVthreeCoveragePct": f"{100 * summary['v3']['coverage']:.2f}",
         "CvgVthreeRiskPct": f"{100 * summary['v3']['risk']:.2f}",
         "CvgObsRiskPct": f"{100 * summary['direct_observe']['risk']:.2f}",
         "CvgForcedObsRisk": f2(summary["obs_forced"]["risk"]),
         "CvgDegradeRiskPct": f"{100 * summary['degrade_all']['risk']:.2f}",
         "CvgDegradeCoveragePct": f"{100 * summary['degrade_all']['coverage']:.2f}",
         "CvgObsDecided": summary["direct_observe"]["decided"],
         "CvgObsCoveragePct": f"{100 * summary['direct_observe']['coverage']:.2f}",
         "CvgObsAbstain": summary["direct_observe"]["abstained"],
         "CvgObsAbstBola": summary["direct_observe"]["abst_bola"],
         "CvgObsAbstNormal": summary["direct_observe"]["abst_normal"],
         "CvgForcedObsTP": summary["obs_forced"]["TP"],
         "CvgForcedObsFN": summary["obs_forced"]["FN"],
         "CvgForcedObsFP": summary["obs_forced"]["FP"],
         "CvgForcedObsRiskPct": f"{100 * summary['obs_forced']['risk']:.2f}",
         "CvgVthreeFNunproven": summary["v3"]["FN"] + summary["v3"]["abst_bola"],
         "CvgDetectGap": summary["direct_observe"]["TP"] - summary["v3"]["TP"],
         # --- direct_only（原定义：仅 oracle，不看请求结果）---
         "CvgDirOnlyDecided": summary["direct_only"]["decided"],
         "CvgDirOnlyTP": summary["direct_only"]["TP"],
         "CvgDirOnlyFP": summary["direct_only"]["FP"],
         "CvgDirOnlyFN": summary["direct_only"]["FN"],
         "CvgDirOnlyTN": summary["direct_only"]["TN"],
         "CvgDirOnlyRiskPct": f"{100 * summary['direct_only']['risk']:.2f}",
         "CvgDirOnlyFpNoEffect": tally["direct_only"]["fp_no_effect"],
         "CvgDirOnlyFpEffect": tally["direct_only"]["fp_effect"],
         "CvgJointVthreeDirect": joint_decided,
         "CvgVthreeCoverage": f2(summary["v3"]["coverage"]),
         "CvgObsDetected": summary["direct_observe"]["TP"],
         "CvgObsMissed": summary["direct_observe"]["FN"],
         "CvgObsRisk": f2(summary["direct_observe"]["risk"]),
         "CvgDegradeRisk": f2(summary["degrade_all"]["risk"]),
         "CvgDegradeCoverage": f2(summary["degrade_all"]["coverage"]),
         "CvgDegradeDetected": summary["degrade_all"]["TP"],
         "CvgRawRisk": f2(summary["raw"]["risk"]),
         "CvgVtwoRisk": f2(summary["v2"]["risk"]),
         "CvgVtwoFP": len(v2_fp),
         "CvgVtwoFPUnread": fp_unread,
         "CvgVtwoFPCover": fp_cover,
         "CvgViolations": sum(1 for r in rows if r["truth"]["truth"] == "bola"),
         "CvgLoopGiteaTotal": f"{loops['gitea']['med_total']:.1f}",
         "CvgLoopGiteaMut": f"{loops['gitea']['med_mutation']:.2f}",
         "CvgLoopGiteaRecrawl": f"{loops['gitea']['med_recrawl']:.2f}",
         "CvgLoopGiteaProbe": f"{loops['gitea']['med_probe']:.1f}",
         "CvgLoopGitlabTotal": f"{loops['gitlab']['med_total']:.1f}",
         "CvgLoopGitlabMut": f"{loops['gitlab']['med_mutation']:.2f}",
         "CvgLoopGitlabRecrawl": f"{loops['gitlab']['med_recrawl']:.2f}",
         "CvgLoopGitlabProbe": f"{loops['gitlab']['med_probe']:.1f}",
         "CvgLoopN": loops["gitea"]["n"],
         }
    lines = ["% 由 ingest_coverage.py 生成，勿手改"]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in M.items()]
    (OUT / "coverage_numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote coverage_numbers.tex")

    # ---------- 表 ----------
    NAMES = {
        "raw": r"\texttt{raw}",
        "v1": r"v1 (existence filter)",
        "v2": r"v2 (existence + coverage)",
        "v3": r"v3 (state-calibrated)",
        "degrade_all": r"\texttt{degrade\_all}",
        "direct_only": r"\texttt{direct\_only}",
        "direct_observe": r"\texttt{direct\_observe}",
        "obs_forced": r"\quad\texttt{direct\_observe}, forced negative",
    }
    def pc(x: float) -> str:
        return f"{100 * x:.2f}"

    tab = [
        "% 由 ingest_coverage.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{The same \CvgN{} records scored on the decision rather than on the "
        r"alarm. Coverage is the share of records on which a method asserts either a "
        r"violation or its absence; the abstention column gives the count and, in "
        r"parentheses, its rate, split by whether the record held a true violation. "
        r"\emph{FP claims} (invalid violation claims) and \emph{misses} are the two error counts among decided "
        r"records, and \emph{risk} is their sum over that denominator---comparable "
        r"across methods only at equal coverage, which these methods do not have. "
        r"A passed record is one on which the method did not fire, not a certificate "
        r"of safety. \texttt{direct\_only} and \texttt{direct\_observe} abstain when "
        r"the probe is unreadable, as the direct adjudicator does, so their coverage is "
        r"\CvgObsCoveragePct{}\%. The two differ in adjudication rule, not in scoring "
        r"convention: \texttt{direct\_only} asserts a violation whenever the "
        r"authorization surface reports no granting channel, regardless of the request "
        r"outcome; \texttt{direct\_observe} additionally requires the ordinary request "
        r"to succeed. All \CvgDirOnlyFP{} FP claims of \texttt{direct\_only} fall on "
        r"requests the server in fact denied. These are invalid violation claims without "
        r"unauthorized-access effect. Strict false proofs, defined elsewhere as promoted "
        r"claims on entitled access ($E{=}\mathrm{allow}$), are a different subclass; "
        r"both subclasses count as incorrect claims for the binary risk in this table. "
        r"The last row is a clearly labelled binary reference "
        r"that forces a negative verdict on those cells, and its misses are the price "
        r"of that forcing, not a property of the method. Panel (b) splits v3's "
        r"abstentions by reason: only the first row is the availability gate the method "
        r"is named for.}"
        ,
        r"\label{tab:coverage}",
        r"\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{@{}p{0.225\textwidth}rrrrrrr@{}}",
        r"\toprule",
        r"method & coverage (\%) & abstained & on violation & on normal & "
        r"FP claims & misses & risk (\%) \\",
        r"\midrule",
    ]
    for m in METHODS:
        s_ = summary[m]
        rate = s_["abstained"] / N
        tab.append(
            f"{NAMES[m]} & {pc(s_['coverage'])} & "
            f"{s_['abstained']} ({pc(rate)}) & {s_['abst_bola']} & {s_['abst_normal']} & "
            f"{s_['FP']} & {s_['FN']} & {pc(s_['risk'])} \\\\")
    un_line = "{} ({} / {})".format(unread, reason[("unavailable", "bola")],
                                     reason[("unavailable", "normal")])
    cov_line = "{} ({} / {})".format(cover, reason[("readable", "bola")],
                                     reason[("readable", "normal")])
    tab += [
        r"\midrule",
        r"\multicolumn{8}{@{}l}{(b) v3's abstentions by reason}\\[1pt]",
        r"reason & \multicolumn{4}{@{}l}{abstentions (on violation / on normal)} & "
        r"\multicolumn{3}{l}{} \\",
        r"\midrule",
        "surface unreadable & \\multicolumn{4}{@{}l}{" + un_line
        + "} & \\multicolumn{3}{l}{nothing to consult} \\\\",
        "surface readable, covering grant & \\multicolumn{4}{@{}l}{" + cov_line
        + "} & \\multicolumn{3}{l}{a false proof converted into a non-decision} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (OUT / "coverage_table.tex").write_text("\n".join(tab) + "\n", encoding="utf-8")
    print("wrote coverage_table.tex")

    if PROBLEMS:
        print("\n".join(PROBLEMS))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
