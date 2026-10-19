# A2 timestamp note (artifact record, 2026-10-19)

The file `c_protocol_amendment_a2.json` is **not** modified: its sha256
(`c84f5bc08eda7f89708965a005e63ad81e81c9aa2bf6956aa753ce765ac63d06`) is bound in
the reported GitLab run record. This note records an inconsistency in one of its
self-reported fields so that the paper can state what is verifiable and what is not.

## Recorded times (all +08:00)

| event | time | source |
|---|---|---|
| pilot run start (`20261019_021810`) | 02:18:10 | `results/temporal/pilot_cascade/temporal_gitlab_pilot.json` |
| pilot last probe | 02:20:17 | same |
| reported run id (`20261019_022419`) | 02:24:19 | `results/temporal/temporal_gitlab.json` |
| reported run first freeze | 02:25:08.445 | same |
| reported run last probe | 02:26:14.920 | same |
| `written_at` field of A2 | 02:32:00 | `c_protocol_amendment_a2.json` |

## What is verifiable

- The pilot records `amendment_id = ["C-min-A1"]` only.
- The reported run records `amendment_id = ["C-min-A1", "C-min-A2"]` and the
  sha256 of the A2 file as it stands (verified byte-for-byte).
- Therefore A2's **content** existed when the reported run executed, i.e. no
  later than 02:26:14. The `written_at` value of 02:32 is inconsistent with the
  run clock and cannot be used to claim that A2 was written before the first
  transition.

## What is not claimed

We do not claim that the `written_at` field is correct, and we do not correct it
in place: changing it would change the hash bound by the run. The paper relies on
the digest carried by the run record, not on the timestamp.

## How to re-check

```
python - <<'PY'
import json, hashlib, pathlib
print(hashlib.sha256(pathlib.Path("c_protocol_amendment_a2.json").read_bytes()).hexdigest())
for p in ("results/temporal/temporal_gitlab.json",
          "results/temporal/pilot_cascade/temporal_gitlab_pilot.json"):
    m = json.load(open(p))["meta"]
    print(p, m["run_id"], m["amendment_id"], m["amendment_sha256"])
PY
```
