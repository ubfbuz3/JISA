"""
Offline validation of the A-pack entitlement model on all three labs.
=====================================================================

For each saved run we rebuild the authorisation ledger from the recorded
phase-A transactions and phase-C mutations, derive E, and compare it with the
old `authorized` field (which was Y = status==200).

On a *correct* system E and Y must coincide, so agreement is the expected
result; any disagreement is either a modelling gap or a genuine E != Y cell.
Neither is silently accepted.

We also re-derive false proofs and true positives under the corrected
definitions (see entitlement.classify).

Usage: python validate_entitlement.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from entitlement import classify                      # noqa: E402
import manifests as mf                                # noqa: E402


def load(name: str) -> dict:
    return json.loads((HERE / "results" / name).read_text(encoding="utf-8"))


def build(system: str):
    if system == "gitea":
        import run_real as r
        rep = load("real_system.json")
        model = mf.gitea_model(rep["phaseA_topology"], rep["phaseC_mutations"],
                               repos=r.REPOS, teams=r.TEAMS, org=r.ORG,
                               admin_user=r.ADMIN_USER)
    elif system == "gogs":
        import run_gogs as r
        import gogs_lab as gl
        rep = load("gogs_real_system.json")
        model = mf.gogs_model(rep["phaseC_mutations"], repos=r.REPOS,
                              teams=r.TEAMS, org=r.ORG,
                              admin_user=gl.ADMIN_USER)
    elif system == "gitlab":
        import run_gitlab as r
        import gitlab_lab as gl
        rep = load("gitlab_real_system.json")
        model = mf.gitlab_model(rep["phaseC_mutations"], repos=r.REPOS,
                                org=r.ORG, admin_user=gl.ADMIN_USER,
                                baselines=r.BASELINES)
    else:
        raise ValueError(system)
    return rep, model


def main() -> int:
    for system in ("gitea", "gogs", "gitlab"):
        rep, model = build(system)
        cells = rep["phaseE_cells"]
        pairs: dict[tuple[str, str], dict] = {}
        for c in cells:
            pairs.setdefault((c["object"], c["subject"]), c)

        agree, disagree = 0, []
        for (obj, subj), c in sorted(pairs.items()):
            d = model.expected(obj, subj, "read")
            e = d.value
            y = "allow" if c["authorized"] else "deny"
            if e == y:
                agree += 1
            else:
                disagree.append((obj, subj, e, y, ",".join(d.basis)))

        print(f"\n===== {system} =====")
        print(f"cells={len(cells)}  pairs={len(pairs)}  E==Y: {agree}/{len(pairs)}")
        if disagree:
            for obj, subj, e, y, basis in disagree:
                print(f"  {obj:12s} {subj:10s} E={e:5s} Y={y:5s}  {basis}")
        else:
            print("  （全部一致）")

        methods = sorted({k for c in cells for k in c["false_proofs"]})
        print(f"  {'method':22s} {'oldFP':>6s} {'newFP':>6s} {'TP':>5s} {'notExpl':>8s}")
        for meth in methods:
            old_fp = new_fp = tp = not_expl = 0
            for c in pairs.values():
                e = model.expected(c["object"], c["subject"], "read").value
                promoted = bool(c["alarms"][meth])
                old_fp += int(c["false_proofs"][meth])
                v = classify(e, bool(c["authorized"]), promoted, promoted)
                new_fp += int(v["false_proof"])
                tp += int(v["true_positive"])
                not_expl += int(v["category"] == "alarm_on_denied_not_exploitable")
            print(f"  {meth:22s} {old_fp:6d} {new_fp:6d} {tp:5d} {not_expl:8d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
