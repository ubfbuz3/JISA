"""
B · temporal experiment -> paper numbers and table.

Reads experiments/real_system/results/temporal/temporal_gitea.json and emits
04_绘图与分析/results/temporal_numbers.tex + temporal_table.tex.

No number in the paper is typed by hand: every macro is derived here.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
SRC = PROJ / "experiments" / "real_system" / "results" / "temporal" / "temporal_gitea.json"
OUT = PROJ / "04_绘图与分析" / "results" / "temporal_numbers.tex"
TABLE = PROJ / "04_绘图与分析" / "results" / "temporal_table.tex"

LABEL = {
    "grant_collaborator": r"direct grant",
    "revoke_collaborator": r"direct revoke",
    "team_repo_attach": r"team attach",
    "team_member_remove": r"team member remove",
    "visibility_public": r"private$\to$public",
    "visibility_private": r"public$\to$private",
    "role_write": r"role read$\to$write",
    "site_admin": r"site admin grant",
}


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    t = d["totals"]
    cycles = d["transitions"]

    over = sum(c["summary"]["stale_over_after_revoke"] for c in cycles)
    m0_ok = sum(1 for c in cycles if c["M0_verified_unchanged"])
    ver_ok = sum(1 for c in cycles if c["version_consistent"])
    cal = d["calibration"]

    M = {
        "TmpRunId": d["meta"]["run_id"],
        "TmpVersion": d["meta"]["version"],
        "TmpCycles": t["cycles"],
        "TmpScoredCycles": t["cycles_scored"],
        "TmpCells": t["cells"],
        "TmpEAllow": t["E_allow"],
        "TmpEDeny": t["E_deny"],
        "TmpYAllow": t["Y_allow"],
        "TmpEeqY": t["E_eq_Y"],
        "TmpStaleFP": t["stale_false_proofs"],
        "TmpLiveFP": t["live_false_proofs"],
        "TmpFixed": t["recrawl_fixed"],
        "TmpStillMiss": t["recrawl_still_misses"],
        "TmpTruePos": t["true_positives"],
        "TmpAbstain": t["abstained_cells"],
        "TmpOverRevoke": over,
        "TmpOracleReadable": t["oracle_readable"],
        "TmpOracleUnreadable": t["cells"] - t["oracle_readable"],
        "TmpOracleSelfReadable": t["oracle_self_readable"],
        "TmpOracleSelfUnreadable": t["cells"] - t["oracle_self_readable"],
        "TmpCalChecks": len(cal["checks"]),
        "TmpCalPassed": 1 if cal["passed"] else 0,
        "TmpPolicyEvents": sum(1 for e in d["policy_events"] if e["committed"]),
        "TmpPolicyFailed": sum(1 for e in d["policy_events"] if not e["committed"]),
        "TmpHv": cycles[-1]["hv_after"],
        "TmpMzeroVerified": m0_ok,
        "TmpVersionConsistent": ver_ok,
        "TmpProtocol": d["meta"]["protocol_sha256"][:12],
    }

    lines = ["% 由 04_绘图与分析/analysis/ingest_temporal.py 生成，勿手改"]
    for k, v in M.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tl = [
        "% 由 ingest_temporal.py 生成，勿手改",
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{Temporal transitions on Gitea \\texttt{%s}. "
        "\\emph{Stale FP}: the frozen pre-change model fails to list a resource that "
        "the subject may legitimately read, so the relation would report a false proof. "
        "\\emph{Fixed}: the same cell is listed again by a recrawl with the same "
        "credential. \\emph{Still missed}: the recrawl also fails to list it. "
        "\\emph{Stale over-approx}: the old model still lists a resource whose access "
        "was revoked; enforcement refuses the request, so this is not a violation and "
        "is not scored as a miss. Every cell is scored against the ledger at the "
        "decision time.}"
        % d["meta"]["version"],
        "\\label{tab:temporal}",
        "\\small",
        "\\begin{tabular}{lrrrrrrr}",
        "\\toprule",
        "Transition & $hv$ & Cells & Stale FP & Fixed & Still missed & Stale over-approx & Live FP \\\\",
        "\\midrule",
    ]
    for c in cycles:
        s = c["summary"]
        hv = f"{c['hv_before']}$\\to${c['hv_after']}" if c["committed"] else "---"
        tl.append(f"{LABEL.get(c['kind'], c['kind'])} & {hv} & {s['cells_cross_scored']} & "
                  f"{s['stale_false_proofs']} & {s['recrawl_fixed']} & "
                  f"{s['recrawl_still_misses']} & {s['stale_over_after_revoke']} & "
                  f"{s['live_false_proofs']} \\\\")
    tl += [
        "\\midrule",
        f"Total & {M['TmpHv']} & {t['cells']} & {t['stale_false_proofs']} & "
        f"{t['recrawl_fixed']} & {t['recrawl_still_misses']} & {over} & "
        f"{t['live_false_proofs']} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
    ]
    TABLE.write_text("\n".join(tl) + "\n", encoding="utf-8")

    print("=== temporal numbers ===")
    for k, v in M.items():
        print(f"  {k:26s} {v}")
    print(f"\n-> {OUT}\n-> {TABLE}")


if __name__ == "__main__":
    main()
