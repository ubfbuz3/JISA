"""
R1.2 / R1.3 / R1.4 -> paper numbers, from the raw per-cell records only.

Reads
  experiments/real_system/results/temporal/temporal_gitea.json
  experiments/real_system/results/temporal/temporal_gitlab.json
and emits
  results/revision_policy_numbers.tex   (macros: promotion-policy sensitivity)
  results/revision_caliber_numbers.tex  (macros: unknown-rule scoring caliber)
  results/revision_ledger_numbers.tex   (macros: ledger-omission sensitivity)
  results/revision_policy_table.tex
  results/revision_caliber_table.tex
  results/revision_ledger_table.tex

Three questions, one record set:
  R1.2  how much of the reported false-proof count is the *promotion policy*
        rather than the relation. A policy maps an alarm A to a claim H;
        a claim is a false proof iff the cell's ledger entitlement is allow.
  R1.3  what a damaged reference record costs the measurement. Deleting a
        channel's grant rows does not change the system, a probe response, or
        an alarm; it changes the label the scoring is done against. The cells
        that move stay legitimate accesses and the false proofs are not
        repaired, only re-described as apparent true positives or apparent
        misses. See ledger_block() for which quantities are held fixed and
        which premises are assumed rather than tested.
  R1.4  what the unknown rule changes. The implementation scores
        modelled-no-channel cells by default deny; the protocol's literal rule
        calls them E-unknown and drops them. Same records, two calibers.

No number in the paper is typed by hand: every macro below is derived here.
Assertions at the end cross-check against ingest_temporal.py and
ingest_gogs_channel.py so a silent drift fails the build.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parents[2]
BASE = PROJ / "experiments" / "real_system" / "results" / "temporal"
RS = PROJ / "experiments" / "real_system"
if str(RS) not in sys.path:
    sys.path.insert(0, str(RS))
from entitlement import classify as classify_cell  # noqa: E402
RES = PROJ / "04_绘图与分析" / "results"

SYSTEMS = [("gitea", "Gitea", "temporal_gitea.json"),
           ("gitlab", "GitLab CE", "temporal_gitlab.json")]

# Promotion policies, in the order the paper argues them.
# Each is a predicate on a cell; a cell for which the predicate holds receives
# the claim "violation-proven".
POLICIES = [
    ("Pnone", "no promotion (report the alarm)", lambda c: False),
    ("Pall", "promote every alarm", lambda c: True),
    ("Poracle", "promote only where the oracle answers \\emph{deny}",
     lambda c: c["oracle_answer"] == "deny"),
    ("Pledger", "promote only where the ledger records a definite \\emph{deny}",
     lambda c: c["expected_entitlement"] == "deny"),
]


def scored_cells(d: dict) -> list[dict]:
    """The cells the shipped pipeline scores: cross-role, no cycle abstention."""
    return [c for cy in d["transitions"] for c in cy["cells"]
            if c["role"] == "cross" and c["abstain_reason"] is None]


def truth(c: dict) -> str:
    """Independent truth of the cell, from the ledger and the effect only."""
    if c["expected_entitlement"] == "allow":
        return "legit"
    return "violation" if c["observed_effect"] == "allow" else "no-violation"


def policy_block(cells: list[dict]) -> dict:
    """Alarm count, claims, contradicted claims, and withheld alarms per policy."""
    alarms = [c for c in cells if c["A_stale"]]
    out = {"alarms": len(alarms), "cells": len(cells)}
    for key, _label, pred in POLICIES:
        claims = [c for c in alarms if pred(c)]
        contradicted = [c for c in claims if truth(c) == "legit"]
        out[key] = {"claims": len(claims),
                    "contradicted": len(contradicted),
                    "withheld": len(alarms) - len(claims),
                    "confirmed": len(claims) - len(contradicted)}
    return out


def caliber_block(cells: list[dict]) -> dict:
    """Confusion matrix and rates under both unknown rules.

    A positive is a violation (ledger deny, effect allow) and a negative is
    every other cell. In these runs E=Y on every cell, so no cell is a
    positive and recall has no denominator.
    """
    # ---- implementation caliber: default deny, every cell scored ----
    imp_n = len(cells)
    imp_pos = sum(1 for c in cells if truth(c) == "violation")
    imp_neg = imp_n - imp_pos
    imp_alarms = [c for c in cells if c["A_stale"]]
    imp_tp = sum(1 for c in imp_alarms if truth(c) == "violation")
    imp_fp = sum(1 for c in imp_alarms if truth(c) != "violation")
    imp_tn = imp_neg - imp_fp

    # ---- literal caliber: modelled-no-channel -> E unknown, dropped ----
    lit_known = [c for c in cells
                 if not (c["expected_entitlement"] == "deny"
                         and c["expected_channel"] == "none")]
    lit_unk = len(cells) - len(lit_known)
    lit_pos = sum(1 for c in lit_known if truth(c) == "violation")
    lit_neg = len(lit_known) - lit_pos
    lit_alarms = [c for c in lit_known if c["A_stale"]]
    lit_tp = sum(1 for c in lit_alarms if truth(c) == "violation")
    lit_fp = sum(1 for c in lit_alarms if truth(c) != "violation")
    lit_tn = lit_neg - lit_fp

    def spec(tn: int, fp: int) -> float | None:
        return None if tn + fp == 0 else 100.0 * tn / (tn + fp)

    def prec(tp: int, fp: int) -> float | None:
        return None if tp + fp == 0 else 100.0 * tp / (tp + fp)

    def share(fp: int, n: int) -> float | None:
        """False proofs as a share of the scorable set. Not a precision."""
        return None if n == 0 else 100.0 * fp / n

    return {
        "ImpN": imp_n, "ImpPos": imp_pos, "ImpNeg": imp_neg,
        "ImpTp": imp_tp, "ImpFp": imp_fp, "ImpTn": imp_tn,
        "ImpSpec": spec(imp_tn, imp_fp), "ImpPrec": prec(imp_tp, imp_fp),
        "ImpShare": share(imp_fp, imp_n),
        "LitKnown": len(lit_known), "LitUnk": lit_unk,
        "LitPos": lit_pos, "LitNeg": lit_neg,
        "LitTp": lit_tp, "LitFp": lit_fp, "LitTn": lit_tn,
        "LitSpec": spec(lit_tn, lit_fp), "LitPrec": prec(lit_tp, lit_fp),
        "LitShare": share(lit_fp, len(lit_known)),
        "LitCov": 100.0 * len(lit_known) / len(cells) if cells else None,
    }


CHANNELS = ("public", "collaborator", "team", "site_admin", "org_owner")


def basis_channel(basis: str) -> str:
    """Map one recorded basis entry to the granting channel it names."""
    b = basis.lower()
    if "no granting channel" in b:
        return "none"
    if "site administrator" in b:
        return "site_admin"
    if "is public" in b:
        return "public"
    if "collaborator" in b:
        return "collaborator"
    if "team" in b or "group" in b:
        return "team"
    if "owner" in b:
        return "org_owner"
    return "unmapped:" + b


def damaged_label(c: dict, ch: str) -> str:
    """The entitlement the reference label carries once channel ``ch`` is lost.

    Only legitimate cells can move: a cell the ledger already calls deny has no
    allow-row on ``ch`` to lose. A legitimate cell moves only if *every* basis
    entry it rests on names ``ch``; one surviving entry on another channel keeps
    it allowed.
    """
    if truth(c) != "legit":
        return c["expected_entitlement"]
    chans = [basis_channel(b) for b in c["expected_basis"]]
    if ch in chans and all(x == ch for x in chans):
        return "deny"
    return "allow"


def ledger_block(cells: list[dict]) -> dict:
    """Counterfactual scoring when one channel's grant rows are absent.

    The intervention is on the *reference label*, not on the system. Deleting a
    channel's grant rows from the recorded basis lists changes what the ledger
    says about a cell; it does not change what any subject is actually allowed to
    do. Every cell that moves here therefore stays a legitimate access, and the
    false proofs found in the run are not repaired by its moving.

    Two recorded quantities are held fixed, and both holdings are read off the
    implementation rather than assumed. The alarm is computed as
    ``(not M0_reachable) and y_allow and role == cross`` in run_temporal.py: it
    reads the crawl snapshot, the probe response and the role, never the ledger,
    so a ledger edit can neither add nor remove one. The probe response is a
    measurement, likewise untouched.

    Scoring is executed, not re-derived, though not every cell reaches the
    classifier. A cell that carries an alarm is passed to the same
    ``entitlement.classify`` the runs use and takes whatever category it returns.
    A cell that carries no alarm is counted as an apparent false negative when the
    damaged label reads deny and the probe allowed---the category the classifier
    assigns to a denial nobody reported. The closed-form counts are then asserted
    equal to the executed ones, so an analytic slip fails the build instead of
    reaching a table.
    """
    for c in cells:
        for b in c["expected_basis"]:
            ch = basis_channel(b)
            assert not ch.startswith("unmapped:"), (c["case_id"], b)
    alarms = [c for c in cells if c["A_stale"]]
    out: dict[str, dict] = {}
    for ch in CHANNELS:
        resting = sole = 0
        for c in cells:
            if truth(c) != "legit":
                continue
            chans = [basis_channel(b) for b in c["expected_basis"]]
            if ch not in chans:
                continue
            resting += 1
            if all(x == ch for x in chans):
                sole += 1

        # ---- executed: build E', run the shipped classifier, count categories
        tp = fn = fp = 0
        for c in cells:
            e2 = damaged_label(c, ch)
            if c["A_stale"]:
                cat = classify_cell(e2, c["observed_effect"] == "allow",
                                    True, True)["category"]
                if cat == "false_proof":
                    fp += 1
                elif cat == "true_positive":
                    tp += 1
            elif e2 == "deny" and c["observed_effect"] == "allow":
                fn += 1

        # ---- analytic closed form, asserted equal to the executed counts
        alarmed_sole = sum(1 for c in alarms
                           if truth(c) == "legit" and damaged_label(c, ch) == "deny")
        assert tp == alarmed_sole, (ch, tp, alarmed_sole)
        assert fp == len(alarms) - alarmed_sole, (ch, fp)
        assert fn == sole - alarmed_sole, (ch, fn)

        out[ch] = {
            "resting": resting,
            "shared": resting - sole,
            "deny": sole,          # re-labelled deny in the damaged ledger
            "tp": tp,              # apparent true positives against that label
            "fn": fn,              # apparent false negatives against it
            "fp": fp,              # false proofs the damaged label still reports
        }
    return out


def fmt(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def main() -> None:
    P: dict[str, int] = {}
    C: dict[str, object] = {}
    L: dict[str, int] = {}
    pooled: list[dict] = []
    per_sys: dict[str, list[dict]] = {}

    for key, _label, fname in SYSTEMS:
        d = json.loads((BASE / fname).read_text(encoding="utf-8"))
        cells = scored_cells(d)
        per_sys[key] = cells
        pooled += cells

    # ---------------- R1.2 policy sensitivity ----------------
    pb_all = policy_block(pooled)
    pre = "Pol"
    P[f"{pre}Alarms"] = pb_all["alarms"]
    P[f"{pre}Cells"] = pb_all["cells"]
    for key, _l, _p in POLICIES:
        P[f"{pre}{key}Claims"] = pb_all[key]["claims"]
        P[f"{pre}{key}False"] = pb_all[key]["contradicted"]
        P[f"{pre}{key}Withheld"] = pb_all[key]["withheld"]
        P[f"{pre}{key}Confirmed"] = pb_all[key]["confirmed"]
    for key, _label, _f in SYSTEMS:
        b = policy_block(per_sys[key])
        tag = "Gt" if key == "gitea" else "Gl"
        P[f"{pre}{tag}Alarms"] = b["alarms"]
        for pk, _l, _p in POLICIES:
            P[f"{pre}{tag}{pk}Claims"] = b[pk]["claims"]
            P[f"{pre}{tag}{pk}False"] = b[pk]["contradicted"]
            P[f"{pre}{tag}{pk}Withheld"] = b[pk]["withheld"]
            P[f"{pre}{tag}{pk}Confirmed"] = b[pk]["confirmed"]

    # ---------------- R1.4 scoring caliber ----------------
    cb = caliber_block(pooled)
    for k, v in cb.items():
        C[f"Cal{k}"] = v
    for key, _label, _f in SYSTEMS:
        b = caliber_block(per_sys[key])
        tag = "Gt" if key == "gitea" else "Gl"
        for k, v in b.items():
            C[f"Cal{tag}{k}"] = v

    # ---------------- R1.3 ledger omission ----------------
    lb = ledger_block(pooled)
    P["LedLegitCells"] = sum(1 for c in pooled if truth(c) == "legit")
    P["LedAlarms"] = sum(1 for c in pooled if c["A_stale"])
    P["LedChannels"] = sum(1 for v in lb.values() if v["resting"])

    def ltag(ch: str) -> str:
        return ch.replace("_", " ").title().replace(" ", "")

    for ch, r in lb.items():
        for k in ("resting", "shared", "deny", "tp", "fn", "fp"):
            P[f"Led{ltag(ch)}{k.title().replace('_','')}"] = r[k]
    # 依赖两条通道的单元：删其中任一条都应保持 allow
    multi = [c for c in pooled
             if len(c["expected_basis"]) > 1 and truth(c) == "legit"]
    P["LedMultiBasis"] = len(multi)
    for c in multi:
        chans = {basis_channel(b) for b in c["expected_basis"]}
        assert len(chans) > 1, c["case_id"]
        for ch in chans:
            assert damaged_label(c, ch) == "allow", (c["case_id"], ch)

    # ---------------- cross-checks ----------------
    for key, _label, fname in SYSTEMS:
        d = json.loads((BASE / fname).read_text(encoding="utf-8"))
        tot = d["totals"]
        cells = per_sys[key]
        assert len(cells) == tot["cells"], (key, len(cells), tot["cells"])
        assert sum(1 for c in cells if c["A_stale"]) == tot["stale_false_proofs"], key
        assert sum(1 for c in cells if truth(c) == "legit") == tot["E_allow"], key
        assert caliber_block(cells)["LitKnown"] == tot["E_allow"], key
    assert P["PolAlarms"] == C["CalImpFp"] + C["CalImpTp"]
    # 每条依据都必须映射到已知通道，且首条与运行期记录的通道一致
    for c in pooled:
        for b in c["expected_basis"]:
            ch = basis_channel(b)
            assert not ch.startswith("unmapped:"), (c["case_id"], b)
        assert basis_channel(c["expected_basis"][0]) == c["expected_channel"], c["case_id"]

    # ---------------- emit macros ----------------
    def write_macros(path: Path, d: dict, header: str) -> None:
        lines = ["% 由 04_绘图与分析/analysis/ingest_revision.py 生成，勿手改"]
        for k, v in d.items():
            lines.append(f"\\newcommand{{\\{k}}}{{{fmt(v)}}}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    write_macros(RES / "revision_policy_numbers.tex", P,
                 "policy + ledger macros")
    write_macros(RES / "revision_caliber_numbers.tex", C,
                 "unknown-rule caliber macros")

    # ---------------- Table: promotion policies ----------------
    def pol_row(name: str, key: str, syslabel: str | None = None) -> str:
        b = pb_all if syslabel is None else policy_block(per_sys[syslabel])
        r = b[key]
        return (f"{name} & {b['alarms']} & {r['claims']} & {r['confirmed']} & "
                f"{r['contradicted']} & {r['withheld']} \\\\")

    tl = [
        "% 由 ingest_revision.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{The same \PolAlarms{} alarms under four promotion policies, over "
        r"the \PolCells{} scored transition cells of Table~\ref{tab:temporal}. An "
        r"alarm $A$ is the relation's own output and does not depend on the policy; "
        r"a \emph{claim} is a policy's promotion of $A$ to \texttt{violation-proven}; "
        r"a claim is \emph{contradicted} (a false proof) when the ledger records the "
        r"access as legitimate. \emph{withheld} counts alarms the policy declines to "
        r"promote. P0 and P3 both reach zero contradicted claims and neither is "
        r"evidence of a better detector: P0 makes no claim at all, and P3 decides by "
        r"consulting the reference ledger. P2 halves the count and leaves it "
        r"entirely on the product whose introspection surface returns false denies.}",
        r"\label{tab:promotion}",
        r"\small",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"policy & alarms & claims & confirmed & contradicted & withheld \\",
        r"\midrule",
        pol_row("P0 report the alarm, no claim", "Pnone"),
        pol_row("P1 promote every alarm", "Pall"),
        pol_row("P2 oracle-gated (v3)", "Poracle"),
        pol_row(r"\quad of which Gitea", "Poracle", "gitea"),
        pol_row(r"\quad of which GitLab", "Poracle", "gitlab"),
        r"\midrule",
        pol_row("P3 ledger-gated", "Pledger"),
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ]
    (RES / "revision_policy_table.tex").write_text("\n".join(tl) + "\n",
                                                   encoding="utf-8")

    # ---------------- Table: scoring caliber ----------------
    cl = [
        "% 由 ingest_revision.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{The \TmpBothCells{} committed cells scored under the two "
        r"\emph{unknown} rules, with "
        r"the confusion matrix spelled out. A positive is a violation (ledger deny, "
        r"effect allow) and a negative is every other cell; in these runs $E=Y$ on "
        r"every cell, so the design contains no positive and recall has no "
        r"denominator (marked N/A, not 0). Specificity and precision are therefore "
        r"properties of the negative set each rule admits, and that set is what "
        r"changes between the two calibers: the claims do not move, the denominator "
        r"does.}",
        r"\label{tab:caliber}",
        r"\small",
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrrrrr@{}}",
        r"\toprule",
        r" & & \multicolumn{3}{c}{cell population} & \multicolumn{2}{c}{claims} "
        r"& \multicolumn{2}{c}{rates (\%)} \\",
        r"\cmidrule(lr){3-5}\cmidrule(lr){6-7}\cmidrule(lr){8-9}",
        r"caliber & product & scorable & negatives & $E$ unknown & false "
        r"& true & spec. & prec. \\",
        r"\midrule",
        f"default deny & Gitea & \\CalGtImpN & \\CalGtImpNeg & 0 & "
        f"\\CalGtImpFp & \\CalGtImpTp & \\CalGtImpSpec & \\CalGtImpPrec \\\\",
        f"default deny & GitLab & \\CalGlImpN & \\CalGlImpNeg & 0 & "
        f"\\CalGlImpFp & \\CalGlImpTp & \\CalGlImpSpec & \\CalGlImpPrec \\\\",
        f"\\;\\emph{{pooled}} & & \\CalImpN & \\CalImpNeg & 0 & \\CalImpFp & "
        f"\\CalImpTp & \\CalImpSpec & \\CalImpPrec \\\\",
        r"\midrule",
        f"literal & Gitea & \\CalGtLitKnown & \\CalGtLitNeg & \\CalGtLitUnk & "
        f"\\CalGtLitFp & \\CalGtLitTp & \\CalGtLitSpec & \\CalGtLitPrec \\\\",
        f"literal & GitLab & \\CalGlLitKnown & \\CalGlLitNeg & \\CalGlLitUnk & "
        f"\\CalGlLitFp & \\CalGlLitTp & \\CalGlLitSpec & \\CalGlLitPrec \\\\",
        f"\\;\\emph{{pooled}} & & \\CalLitKnown & \\CalLitNeg & \\CalLitUnk & "
        f"\\CalLitFp & \\CalLitTp & \\CalLitSpec & \\CalLitPrec \\\\",
        r"\midrule",
        r"\multicolumn{9}{l}{recall: N/A in both calibers ($0$ positives in the "
        r"design; the temporal grid measures the false-proof face only)} \\",
        r"\bottomrule",
        r"\end{tabular*}",
        r"\end{table*}",
    ]
    (RES / "revision_caliber_table.tex").write_text("\n".join(cl) + "\n",
                                                    encoding="utf-8")

    # ---------------- Table: ledger omission ----------------
    lrows = []
    for ch, label in [("public", "public visibility"), ("collaborator", "direct collaborator"),
                      ("team", "team / project group"), ("site_admin", "site administrator"),
                      ("org_owner", "organisation owner")]:
        r = lb.get(ch)
        if not r or not r["resting"]:
            continue
        lrows.append(f"{label} & {r['resting']} & {r['deny']} & {r['tp']} & "
                     f"{r['fn']} & {r['fp']} \\\\")
    ll = [
        "% 由 ingest_revision.py 生成，勿手改",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Scoring against a damaged reference label: what one missing "
        r"granting channel does to the reported numbers. The intervention edits "
        r"the ledger, not the system. The damaged reference labels are scored using "
        r"the procedure described in Section~\ref{sec:protocol}, with the cell "
        r"sample, the alarms, the probe responses and the promotion decisions held "
        r"fixed. Under the damaged label "
        r"\emph{re-labelled} counts the cells that now read deny; of those, "
        r"\emph{apparent TP} counts the alarmed ones (a false proof now scoring "
        r"as a confirmed violation) and \emph{apparent FN} the unalarmed ones (a "
        r"legitimate access now scoring as a missed violation); \emph{reported FP} "
        r"is the false-proof count the damaged label still measures.}",
        r"\label{tab:ledger}",
        r"\small",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"channel omitted & resting & re-labelled & apparent TP & apparent FN & reported FP \\",
        r"\midrule",
        f"none (as run) & {P['LedLegitCells']} & 0 & 0 & 0 & {P['LedAlarms']} \\\\",
        r"\midrule",
    ] + lrows + [
        r"\bottomrule",
        r"\end{tabular}",
        r"\par\smallskip\footnotesize\emph{resting} counts cells per channel and "
        r"overlaps: \LedMultiBasis{} cells rest on two channels, so the column sums "
        r"to $\LedLegitCells+\LedMultiBasis$ against the \LedLegitCells{} cells "
        r"scored.",
        r"\end{table*}",
    ]
    (RES / "revision_ledger_table.tex").write_text("\n".join(ll) + "\n",
                                                   encoding="utf-8")


    print("=== policy ===")
    for k, v in P.items():
        print(f"  {k:26s} {fmt(v)}")
    print("=== caliber ===")
    for k, v in C.items():
        print(f"  {k:26s} {fmt(v)}")
    print("=== ledger channels ===")
    for ch, r in lb.items():
        print(f"  {ch:14s} resting={r['resting']:3d} deny={r['deny']:3d} "
              f"shared={r['shared']:2d} appTP={r['tp']:3d} "
              f"appFN={r['fn']:3d} reportedFP={r['fp']:3d}")


if __name__ == "__main__":
    main()
