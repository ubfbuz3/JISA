"""Reviewer A read-only checks. Writes no manuscript, raw-data or generated result files."""
from pathlib import Path
import collections
import itertools
import json
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "04_绘图与分析/analysis"))
import ingest_truth
result = {"matrix_predicates": ingest_truth.verify_predicates(ingest_truth.load_matrix()), "temporal": {}}
for system in ("gitea", "gitlab"):
    path = ROOT / "experiments/real_system/results/temporal" / f"temporal_{system}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    cells = [c for tr in raw["transitions"] for c in tr["cells"] if c["role"] == "cross"]
    tally = collections.Counter()
    for c in cells:
        y = c["observed_effect"] == "allow"
        m = c["M0_reachable"]
        e = c["expected_entitlement"]
        a = y and not m
        tally["cross_cells"] += 1
        tally["EY_agree"] += (e == "allow") == y
        tally["flat_alarm_disagreement"] += a != c["A_stale"]
        tally["E_deny"] += e == "deny"
        tally["E_allow"] += e == "allow"
        tally["no_grant_channel"] += c["expected_channel"] == "none"
        tally["literal_protocol_scoreable"] += c["expected_channel"] != "none"
        tally["stale_false_proofs"] += bool(a and e == "allow")
        tally["live_false_proofs"] += bool(c["A_live"] and e == "allow")
    result["temporal"][system] = dict(tally)
result["boolean_rows"] = []
for y,m,o in itertools.product((0,1), repeat=3):
    a = bool(y and not m)
    d = bool(y and not o)
    h = bool(a and not o)
    assert (a == d) == (not y or m == o)
    assert not h or d
    result["boolean_rows"].append(dict(Y=y, M=m, O=o, A=int(a), D=int(d), H_v3=int(h)))
print(json.dumps(result, ensure_ascii=False, indent=2))
