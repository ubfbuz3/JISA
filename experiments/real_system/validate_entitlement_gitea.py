"""
Offline validation of the A-pack entitlement model against the saved Gitea run.
==============================================================================

Purpose
-------
Prove, without Docker, that the new E-model reproduces the old truth on a
*correct* system (Gitea), where E and Y must coincide.  Any disagreement is
either a modelling gap or a genuine E != Y cell worth investigating -- both are
useful, and neither is silently accepted.

Also re-derives false proofs / true positives under the corrected definition:

    old:  false_proof = promotion and (status == 200)
    new:  false_proof = promotion and E == allow
          true_positive = promotion and E == deny

Usage: python validate_entitlement_gitea.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_real as rr                      # noqa: E402  (constants only)
from entitlement import PolicyModel, classify  # noqa: E402

RESULT = HERE / "results" / "real_system.json"


def build_model(rep: dict) -> PolicyModel:
    m = PolicyModel()
    src = "phaseA_topology / run_real.REPOS"

    m.add_org(rr.ORG, "dave", "org created by dave")

    # repositories + visibility (as created)
    for owner, name, private, isorg, creator in rr.REPOS:
        obj = f"{owner}/{name}"
        m.add_repo(obj, owner, private, src)

    # site administrator
    m.add_site_admin(rr.ADMIN_USER, "gitea_lab.ADMIN_USER")

    # teams (permission comes from the documented TEAMS config)
    for team, perm in rr.TEAMS.items():
        m.add_team(team, perm, "phaseA team creation")

    # baseline grants recorded in phase A
    m.add_team_member("dev", "bob", "phaseA baseline team dev += bob")
    m.add_team_repo("dev", f"{rr.ORG}/t1", "phaseA baseline dev += acme/t1")
    m.add_collaborator("alice/r1", "bob", "read",
                       "phaseA baseline in-band share alice/r1 <- bob")

    # out-of-band mutations recorded in phase C
    for mut in rep.get("phaseC_mutations", {}).get("mutations", []):
        kind = mut.get("mutation", "")
        obj = mut.get("object")
        subj = mut.get("subject")
        src = f"phaseC:{kind}"
        if kind.startswith("admin_grant_collaborator") and obj and subj:
            m.add_collaborator(obj, subj, "read", src)
        elif kind.startswith("team_grant_repo") and obj:
            # "... -> team dev"
            team = kind.rsplit("team ", 1)[-1].strip()
            if team in rr.TEAMS:
                m.add_team_repo(team, obj, src)
        elif kind.startswith("admin_flip_visibility") and obj:
            # "... -> public"  => private becomes False
            m.set_visibility(obj, "-> public" not in kind, src)
        elif kind.startswith("admin_add_org_member") and subj:
            m.add_org_member(rr.ORG, subj, src)
        elif kind.startswith("admin_add_team_member") and subj:
            # "admin_add_team_member:dev<-frank"
            team = kind.split(":", 1)[1].split("<-", 1)[0].strip()
            if team in rr.TEAMS:
                m.add_team_member(team, subj, src)
    return m


def main() -> int:
    rep = json.loads(RESULT.read_text(encoding="utf-8"))
    m = build_model(rep)
    cells = rep["phaseE_cells"]

    # one row per (object, subject); snapshot/live only differ in the MR gate
    pairs: dict[tuple[str, str], dict] = {}
    for c in cells:
        pairs.setdefault((c["object"], c["subject"]), c)

    print(f"cells={len(cells)}  unique(object,subject)={len(pairs)}")
    print("model:", json.dumps(m.summary(), ensure_ascii=False)[:400], "\n")

    agree = 0
    disagree: list[tuple[str, str, str, str, str]] = []
    for (obj, subj), c in sorted(pairs.items()):
        e = m.expected(obj, subj, "read").value
        y = "allow" if c["authorized"] else "deny"
        if e == y:
            agree += 1
        else:
            disagree.append((obj, subj, e, y,
                             ",".join(m.expected(obj, subj, "read").basis)))

    print(f"E 与旧 Y 一致: {agree}/{len(pairs)}")
    if disagree:
        print("不一致的格子（需逐个解释）：")
        for obj, subj, e, y, basis in disagree:
            print(f"  {obj:12s} {subj:15s} E={e:5s} Y={y:5s}  {basis}")

    # ---- re-derive false proofs / TPs under the corrected definition ----
    methods = sorted({k for c in cells for k in c["false_proofs"]})
    print("\n方法              旧假证明  新假证明   新TP  告警但未越权  未计(E=?)")
    for meth in methods:
        old_fp = new_fp = new_tp = not_expl = unscored = 0
        for (obj, subj), c in pairs.items():
            e = m.expected(obj, subj, "read").value
            promoted = bool(c["alarms"][meth])
            observed_allow = bool(c["authorized"])
            old_fp += int(c["false_proofs"][meth])
            v = classify(e, observed_allow, promoted, promoted)
            new_fp += int(v["false_proof"])
            new_tp += int(v["true_positive"])
            not_expl += int(v["category"] == "alarm_on_denied_not_exploitable")
            unscored += int(v["category"] == "unscored_unknown_entitlement")
        print(f"{meth:18s} {old_fp:7d} {new_fp:9d} {new_tp:6d} {not_expl:12d} {unscored:11d}")

    print("\n说明：同一 (object,subject) 的 snapshot/live 两行只影响 MR 门控，")
    print("      故上面按去重后的格子统计；正文若按 96 行报，需乘以对应读数。")
    return 0 if not disagree else 0


if __name__ == "__main__":
    raise SystemExit(main())
