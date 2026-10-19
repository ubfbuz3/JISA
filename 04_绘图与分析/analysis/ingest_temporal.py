"""
B · temporal experiment -> paper numbers and table (Gitea + GitLab).

Reads
  experiments/real_system/results/temporal/temporal_gitea.json
  experiments/real_system/results/temporal/temporal_gitlab.json
and emits
  04_绘图与分析/results/temporal_numbers.tex
  04_绘图与分析/results/temporal_table.tex

Macro families
  Tmp*      Gitea 1.22.6 (kept stable: existing text refers to them)
  TmpG*     GitLab CE 17.11.7
  TmpBoth*  the two systems pooled

No number in the paper is typed by hand: every macro is derived here.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
BASE = PROJ / "experiments" / "real_system" / "results" / "temporal"
SRC_G = BASE / "temporal_gitea.json"
SRC_L = BASE / "temporal_gitlab.json"
OUT = PROJ / "04_绘图与分析" / "results" / "temporal_numbers.tex"
TABLE = PROJ / "04_绘图与分析" / "results" / "temporal_table.tex"
CHANNEL = PROJ / "04_绘图与分析" / "results" / "temporal_channel_table.tex"

LABEL = {
    "grant_collaborator": r"direct grant",
    "revoke_collaborator": r"direct revoke",
    "team_repo_attach": r"team attach",
    "team_member_remove": r"team member remove",
    "group_share": r"group share",
    "group_member_remove": r"group member remove",
    "visibility_public": r"private$\to$public",
    "visibility_private": r"public$\to$private",
    "role_write": r"role read$\to$write",
    "site_admin": r"site admin grant",
}


CHANNELS = ["site_admin", "public", "collaborator", "team", "none"]


def channel_stats(d: dict) -> dict:
    """每个台账通道上，oracle 与 E 的对照（只统计换凭证格）。"""
    out: dict[str, dict] = {}
    for cy in d["transitions"]:
        for c in cy["cells"]:
            if c["role"] != "cross" or c["abstain_reason"] is not None:
                continue
            ch = c["expected_channel"]
            r = out.setdefault(ch, {"n": 0, "answered": 0, "correct": 0,
                                    "allow_agree": 0, "deny_agree": 0,
                                    "false_allow": 0, "false_deny": 0})
            r["n"] += 1
            o, e = c["oracle_answer"], c["expected_entitlement"]
            if o not in ("allow", "deny"):
                continue
            r["answered"] += 1
            if (o == "allow") == (e == "allow"):
                r["correct"] += 1
                r["allow_agree" if o == "allow" else "deny_agree"] += 1
            elif o == "allow":
                r["false_allow"] += 1
            else:
                r["false_deny"] += 1
    return out


def load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"缺产物: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def literal_sensitivity(d: dict) -> dict:
    """协议字面 vs 实现的双口径敏感性（R1.2 整改）。

    实现：closed-world default-deny —— 台账无授予渠道即 E=deny，全部格可评分。
    协议字面（c_protocol.json 的 unknown_policy）：已建模无授予渠道 -> E=unknown，
    该格不进真值表、不可评分。本函数按字面规则重标每条换凭证格，输出两种口径的
    评分集合与陈旧假确证落点，供正文双口径对账，不得只报其一。
    """
    scored = unknown = 0
    allow_cells = 0
    ey_known = 0
    stale_fp_recorded = stale_fp_known = live_fp = 0
    deny_without_none_channel = 0
    for cy in d["transitions"]:
        for c in cy["cells"]:
            if c["role"] != "cross" or c["abstain_reason"] is not None:
                continue
            scored += 1
            e = c["expected_entitlement"]
            ch = c["expected_channel"]
            if e == "deny" and ch == "none":
                # 协议字面：已建模无渠道 -> unknown，不评分
                unknown += 1
                # 该格在两种口径下都不可能是严格假确证（E≠allow）；
                # 若出现 stale 告警落在这里，实现口径下也必须如实计。
                if c["T_stale"] == "false_proof":
                    stale_fp_recorded += 1
                if c["T_live"] == "false_proof":
                    live_fp += 1
                continue
            if e == "deny" and ch != "none":
                deny_without_none_channel += 1
            if e == "allow":
                allow_cells += 1
            # 字面口径下 E 已知且可评分的格
            ey_known += int((e == "allow") == (c["observed_effect"] == "allow"))
            if c["T_stale"] == "false_proof":
                stale_fp_recorded += 1
                if e == "allow":
                    stale_fp_known += 1
            if c["T_live"] == "false_proof":
                live_fp += 1
    return {"scored": scored, "literal_unknown": unknown,
            "literal_known": scored - unknown, "allow_cells": allow_cells,
            "ey_known_agree": ey_known,
            "stale_fp_recorded": stale_fp_recorded,
            "stale_fp_within_known": stale_fp_known,
            "live_fp": live_fp,
            "deny_without_none_channel": deny_without_none_channel}


def macros(t: dict, cycles: list[dict], cal: dict, meta: dict) -> dict:
    over = sum(c["summary"]["stale_over_after_revoke"] for c in cycles)
    disagree = sum(c["summary"].get("oracle_disagrees_with_E", 0) for c in cycles)
    by_ch: dict[str, int] = {}
    for cy in cycles:
        for c in cy["cells"]:
            if c["role"] == "cross" and c.get("oracle_matches_E") is False:
                by_ch[c["expected_channel"]] = by_ch.get(c["expected_channel"], 0) + 1
    return {
        "Cycles": t["cycles"],
        "ScoredCycles": t["cycles_scored"],
        "Cells": t["cells"],
        "EAllow": t["E_allow"],
        "EDeny": t["E_deny"],
        "YAllow": t["Y_allow"],
        "EeqY": t["E_eq_Y"],
        "StaleFP": t["stale_false_proofs"],
        "LiveFP": t["live_false_proofs"],
        "Fixed": t["recrawl_fixed"],
        "StillMiss": t["recrawl_still_misses"],
        "TruePos": t["true_positives"],
        "Abstain": t["abstained_cells"],
        "OverRevoke": over,
        "OracleReadable": t["oracle_readable"],
        "OracleUnreadable": t["cells"] - t["oracle_readable"],
        "OracleSelfReadable": t["oracle_self_readable"],
        "OracleSelfUnreadable": t["cells"] - t["oracle_self_readable"],
        "OracleDisagree": disagree,
        "OracleDisagreePublic": by_ch.get("public", 0),
        "OracleDisagreeAdmin": by_ch.get("site_admin", 0),
        "CalChecks": len(cal["checks"]),
        "CalGateChecks": sum(1 for c in cal["checks"] if c.get("gate", True)),
        "CalPassed": 1 if cal["passed"] else 0,
        "PolicyEvents": sum(1 for e in meta["_events"] if e["committed"]),
        "PolicyFailed": sum(1 for e in meta["_events"] if not e["committed"]),
        "Hv": cycles[-1]["hv_after"],
        "MzeroVerified": sum(1 for c in cycles if c["M0_verified_unchanged"]),
        "VersionConsistent": sum(1 for c in cycles if c["version_consistent"]),
        "Version": meta["version"],
        "RunId": meta["run_id"],
        "Protocol": meta["protocol_sha256"][:12],
    }


def main() -> None:
    dg = load(SRC_G)
    dl = load(SRC_L)
    for d in (dg, dl):
        d["meta"]["_events"] = d["policy_events"]

    g = macros(dg["totals"], dg["transitions"], dg["calibration"], dg["meta"])
    l = macros(dl["totals"], dl["transitions"], dl["calibration"], dl["meta"])

    # 双口径敏感性（协议字面 unknown vs 实现 default-deny）
    sg = literal_sensitivity(dg)
    sl = literal_sensitivity(dl)
    # 交叉校验：逐格重算的陈旧假确证必须与 totals 相同；无渠道 deny 之外
    # 不允许出现其他形态的 deny（否则字面重标规则覆盖不全，需先修本函数）。
    assert sg["stale_fp_recorded"] == dg["totals"]["stale_false_proofs"], sg
    assert sl["stale_fp_recorded"] == dl["totals"]["stale_false_proofs"], sl
    assert sg["deny_without_none_channel"] == 0, sg
    assert sl["deny_without_none_channel"] == 0, sl
    assert sg["scored"] == dg["totals"]["cells"] and sl["scored"] == dl["totals"]["cells"]

    M = {
        "TmpRunId": g["RunId"],
        "TmpVersion": g["Version"],
        "TmpCycles": g["Cycles"],
        "TmpScoredCycles": g["ScoredCycles"],
        "TmpCells": g["Cells"],
        "TmpEAllow": g["EAllow"],
        "TmpEDeny": g["EDeny"],
        "TmpYAllow": g["YAllow"],
        "TmpEeqY": g["EeqY"],
        "TmpStaleFP": g["StaleFP"],
        "TmpLiveFP": g["LiveFP"],
        "TmpFixed": g["Fixed"],
        "TmpStillMiss": g["StillMiss"],
        "TmpTruePos": g["TruePos"],
        "TmpAbstain": g["Abstain"],
        "TmpOverRevoke": g["OverRevoke"],
        "TmpOracleReadable": g["OracleReadable"],
        "TmpOracleUnreadable": g["OracleUnreadable"],
        "TmpOracleSelfReadable": g["OracleSelfReadable"],
        "TmpOracleSelfUnreadable": g["OracleSelfUnreadable"],
        "TmpOracleDisagree": g["OracleDisagree"],
        "TmpCalChecks": g["CalChecks"],
        "TmpCalPassed": g["CalPassed"],
        "TmpPolicyEvents": g["PolicyEvents"],
        "TmpPolicyFailed": g["PolicyFailed"],
        "TmpHv": g["Hv"],
        "TmpMzeroVerified": g["MzeroVerified"],
        "TmpVersionConsistent": g["VersionConsistent"],
        "TmpProtocol": g["Protocol"],

        # ---- GitLab CE 17.11.7 ----
        "TmpGRunId": l["RunId"],
        "TmpGVersion": l["Version"],
        "TmpGProtocol": l["Protocol"],
        "TmpGCycles": l["Cycles"],
        "TmpGCells": l["Cells"],
        "TmpGEAllow": l["EAllow"],
        "TmpGEDeny": l["EDeny"],
        "TmpGYAllow": l["YAllow"],
        "TmpGEeqY": l["EeqY"],
        "TmpGStaleFP": l["StaleFP"],
        "TmpGLiveFP": l["LiveFP"],
        "TmpGFixed": l["Fixed"],
        "TmpGStillMiss": l["StillMiss"],
        "TmpGOverRevoke": l["OverRevoke"],
        "TmpGOracleReadable": l["OracleReadable"],
        "TmpGOracleSelfReadable": l["OracleSelfReadable"],
        "TmpGOracleDisagree": l["OracleDisagree"],
        "TmpGOracleDisagreePublic": l["OracleDisagreePublic"],
        "TmpGOracleDisagreeAdmin": l["OracleDisagreeAdmin"],
        "TmpGCalGateChecks": l["CalGateChecks"],
        "TmpGPolicyEvents": l["PolicyEvents"],
        "TmpGHv": l["Hv"],
        "TmpGMzeroVerified": l["MzeroVerified"],
        "TmpGVersionConsistent": l["VersionConsistent"],

        # ---- pooled ----
        "TmpBothCycles": g["Cycles"] + l["Cycles"],
        "TmpBothCells": g["Cells"] + l["Cells"],
        "TmpBothEeqY": g["EeqY"] + l["EeqY"],
        "TmpBothStaleFP": g["StaleFP"] + l["StaleFP"],
        "TmpBothFixed": g["Fixed"] + l["Fixed"],
        "TmpBothStillMiss": g["StillMiss"] + l["StillMiss"],
        "TmpBothLiveFP": g["LiveFP"] + l["LiveFP"],
        "TmpBothTruePos": g["TruePos"] + l["TruePos"],
        "TmpBothPolicyEvents": g["PolicyEvents"] + l["PolicyEvents"],
        "TmpBothMzeroVerified": g["MzeroVerified"] + l["MzeroVerified"],
        "TmpBothVersionConsistent": g["VersionConsistent"] + l["VersionConsistent"],
        "TmpBothOracleReadable": g["OracleReadable"] + l["OracleReadable"],
        "TmpBothOracleDisagree": g["OracleDisagree"] + l["OracleDisagree"],
        "TmpBothOverRevoke": g["OverRevoke"] + l["OverRevoke"],
        "TmpGOracleFalseDeny": sum(v["false_deny"] for v in channel_stats(dl).values()),
        "TmpOracleFalseDeny": sum(v["false_deny"] for v in channel_stats(dg).values()),
        "TmpGOracleAnswered": sum(v["answered"] for v in channel_stats(dl).values()),
        "TmpOracleAnswered": sum(v["answered"] for v in channel_stats(dg).values()),
        # 未作答格（oracle 无确定答案，anonymous 视点）：显式披露，不并入 deny
        "TmpUnansGitea": sum(v["n"] - v["answered"] for v in channel_stats(dg).values()),
        "TmpUnansGitlab": sum(v["n"] - v["answered"] for v in channel_stats(dl).values()),
        "TmpCellsTotal": g["Cells"] + l["Cells"],
        # ---- 协议字面 vs 实现的双口径敏感性 ----
        "TmpLitUnk": sg["literal_unknown"],
        "TmpLitKnown": sg["literal_known"],
        "TmpLitKnownAllow": sg["allow_cells"],
        "TmpLitEeqY": sg["ey_known_agree"],
        "TmpLitStaleKnown": sg["stale_fp_within_known"],
        "TmpGLitUnk": sl["literal_unknown"],
        "TmpGLitKnown": sl["literal_known"],
        "TmpGLitKnownAllow": sl["allow_cells"],
        "TmpGLitEeqY": sl["ey_known_agree"],
        "TmpGLitStaleKnown": sl["stale_fp_within_known"],
        "TmpBothLitUnk": sg["literal_unknown"] + sl["literal_unknown"],
        "TmpBothLitKnown": sg["literal_known"] + sl["literal_known"],
        "TmpBothLitEeqY": sg["ey_known_agree"] + sl["ey_known_agree"],
        "TmpBothLitStaleKnown": sg["stale_fp_within_known"] + sl["stale_fp_within_known"],
    }

    lines = ["% 由 04_绘图与分析/analysis/ingest_temporal.py 生成，勿手改"]
    for k, v in M.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------------- Table: per transition, two products ----------------
    gy = {c["seq"]: c for c in dg["transitions"]}
    ly = {c["seq"]: c for c in dl["transitions"]}
    order = [c["seq"] for c in dg["transitions"]]

    tl = [
        "% 由 ingest_temporal.py 生成，勿手改",
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{Temporal transitions on two products with the same pre-registered "
        "protocol. \\emph{Stale FP}: the frozen pre-change model does not list a "
        "resource the subject may legitimately read, so the relation would report a "
        "false proof. \\emph{Fixed}: a recrawl with the same credential lists it "
        "again. \\emph{Missed}: the recrawl also fails to list it. Each product has "
        "its own mechanism per row (team attach $\\leftrightarrow$ project-group "
        "share; team member removal $\\leftrightarrow$ group member removal), its "
        "own cell count (\\TmpCells{} on Gitea, \\TmpGCells{} on GitLab) and its own "
        "decision-time ledger; no row is pooled across products.}",
        "\\label{tab:temporal}",
        "\\small",
        "\\begin{tabular}{lrrrrrr}",
        "\\toprule",
        " & \\multicolumn{3}{c}{Gitea \\TmpVersion} & "
        "\\multicolumn{3}{c}{GitLab CE \\TmpGVersion} \\\\",
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}",
        "Transition & Stale FP & Fixed & Missed & Stale FP & Fixed & Missed \\\\",
        "\\midrule",
    ]
    for seq in order:
        cg, cl = gy[seq], ly[seq]
        sg, sl = cg["summary"], cl["summary"]
        tl.append(f"{LABEL.get(cg['kind'], cg['kind'])} & "
                  f"{sg['stale_false_proofs']} & {sg['recrawl_fixed']} & "
                  f"{sg['recrawl_still_misses']} & "
                  f"{sl['stale_false_proofs']} & {sl['recrawl_fixed']} & "
                  f"{sl['recrawl_still_misses']} \\\\")
    tl += [
        "\\midrule",
        f"Total & {g['StaleFP']} & {g['Fixed']} & {g['StillMiss']} & "
        f"{l['StaleFP']} & {l['Fixed']} & {l['StillMiss']} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
    ]
    TABLE.write_text("\n".join(tl) + "\n", encoding="utf-8")

    # ---------------- Table: oracle fidelity by channel ----------------
    # Full four-cell confusion per channel, one panel per product: the reviewer
    # asked for TP/TN/FP/FN rather than a single disagreement count.
    cg, cl = channel_stats(dg), channel_stats(dl)
    order = [("site_admin", "site administrator"), ("public", "public visibility"),
             ("collaborator", "direct collaborator"), ("team", "team / group"),
             ("none", "no channel")]

    def panel(st: dict, head: str) -> list[str]:
        lines = [r"\multicolumn{7}{l}{" + head + r"}\\", r"\addlinespace[2pt]",
                 r"Channel & cells & allow & deny & f.\ allow & f.\ deny & unans. \\",
                 r"\addlinespace[2pt]"]
        tot = {"n": 0, "allow_agree": 0, "deny_agree": 0,
               "false_allow": 0, "false_deny": 0}
        for ch, label in order:
            r = st.get(ch)
            if not r:
                continue
            un = r["n"] - r["answered"]
            lines.append(f"{label} & {r['n']} & {r['allow_agree']} & "
                         f"{r['deny_agree']} & {r['false_allow']} & "
                         f"{r['false_deny']} & {un} \\\\")
            for k in tot:
                tot[k] += r[k]
        un = tot["n"] - tot["allow_agree"] - tot["deny_agree"] - tot["false_allow"] - tot["false_deny"]
        lines.append(r"\addlinespace[2pt]")
        lines.append(f"\\emph{{total}} & {tot['n']} & {tot['allow_agree']} & "
                     f"{tot['deny_agree']} & {tot['false_allow']} & "
                     f"{tot['false_deny']} & {un} \\\\")
        return lines

    ct = [
        "% 由 ingest_temporal.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Oracle fidelity by granting channel, over the same transition "
        r"cells as Table~\ref{tab:temporal}: a confusion matrix of the owner-vantage "
        r"oracle against the ledger, per channel and per product. \emph{allow} and "
        r"\emph{deny} count cells where the oracle agrees with the ledger; "
        r"\emph{f.\ allow} and \emph{f.\ deny} are the two error directions; "
        r"\emph{unans.} counts cells where the surface returns no definite answer "
        r"(anonymous readers). A false deny is an oracle that answers deny on a "
        r"legitimately readable cell. Neither product produces a single false "
        r"allow: the membership surface errs only by omission, and public and "
        r"site-admin cells are exactly the channels that are not group or "
        r"repository membership. The ``no channel'' row is the default-deny "
        r"stratum: no grant of any kind is recorded for those cells, so the "
        r"ledger denies them.}",
        r"\label{tab:oracle-channel}",
        r"\small",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
    ]
    ct += panel(cg, r"(a) Gitea \TmpVersion")
    ct += [r"\midrule"]
    ct += panel(cl, r"(b) GitLab CE \TmpGVersion")
    ct += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    CHANNEL.write_text("\n".join(ct) + "\n", encoding="utf-8")

    # ---------------- Table: literal-protocol vs implementation dual caliber ----------------
    # 同一批记录在两种 unknown 规则下的评分集合对账（R1.2 整改）。
    sens = [
        "% 由 ingest_temporal.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{The same transition cells under the two \emph{unknown} rules of "
        r"Section~\ref{sec:protocol}. The implementation scores every committed cell "
        r"by closed-world default deny; the protocol's literal \emph{unknown} policy "
        r"marks modelled-no-channel cells $E$-unknown and excludes them from "
        r"scoring. The rule changes the scorable set, the $E$ classification and "
        r"the $E/Y$ denominator; it does not move the stale false proofs, all of "
        r"which fall on $E$-allow cells inside the literal-known set.}",
        r"\label{tab:unknown-sensitivity}",
        r"\small",
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrrr@{}}",
        r"\toprule",
        r" & \multicolumn{3}{c}{implementation (default deny)} & "
        r"\multicolumn{3}{c}{literal protocol ($E$ unknown)} \\",
        r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
        r"Product & scored & $E$ allow & stale FP & scorable & $E/Y$ agree & stale FP \\",
        r"\midrule",
        f"Gitea \\TmpVersion & \\TmpCells & \\TmpEAllow & \\TmpStaleFP & "
        f"\\TmpLitKnown & \\TmpLitEeqY & \\TmpLitStaleKnown \\\\",
        f"GitLab CE \\TmpGVersion & \\TmpGCells & \\TmpGEAllow & \\TmpGStaleFP & "
        f"\\TmpGLitKnown & \\TmpGLitEeqY & \\TmpGLitStaleKnown \\\\",
        r"\midrule",
        f"Total & \\TmpBothCells & --- & \\TmpBothStaleFP & "
        f"\\TmpBothLitKnown & \\TmpBothLitEeqY & \\TmpBothLitStaleKnown \\\\",
        r"\bottomrule",
        r"\end{tabular*}",
        r"\end{table*}",
    ]
    (PROJ / "04_绘图与分析" / "results" / "temporal_sensitivity_table.tex").write_text(
        "\n".join(sens) + "\n", encoding="utf-8")

    print("=== temporal numbers ===")
    for k, v in M.items():
        print(f"  {k:28s} {v}")
    print(f"\n-> {OUT}\n-> {TABLE}\n-> {CHANNEL}")


if __name__ == "__main__":
    main()
