# R1.4 protocol — errata to `R1.4_oracle_admission_v1.md`

**Applies to:** `R1.4_oracle_admission_v1.md`, sha256
`198f21402fa6d800ffa9015ad378724de78234fc7fb6ea170e5140e5bf8be5b2`.
**This file does not modify the frozen text.** The digest above is unchanged and
`SHA256SUMS` still verifies against it; the errors below are metadata and version
labels, corrected here so that the frozen object is never silently rewritten.

## E1 — the commit pointer in the header is wrong

The header says the protocol was fixed "at commit `cce644d`". That commit does not
contain the file: `git cat-file -e cce644d:…/prereg/R1.4_oracle_admission_v1.md`
fails, and `cce644d` (2026-10-19 21:47:41 +0800) is the v8 artifact commit.

The file first enters the repository at **`a049cb1`** (2026-10-19 21:52:54 +0800,
"R1.4: freeze oracle-independence admission protocol v1 before the new runs"),
and is carried forward by **`2c798fc`** (21:53:02 +0800), which adds
`.gitattributes` entries (`*.md -text`) so that the digest verifies on a fresh
checkout instead of depending on the working copy's line endings.

The precedence claim the protocol exists to support is unaffected: both commits
precede the first matched-budget record (2026-10-19 22:06:51, commit `7a31b9c`)
and the corrected re-run of that experiment (2026-10-19 23:50:35, this commit).
The claim is therefore "frozen before the new results", which is what §"Scope of
the *pre*" asserts — not "frozen at `cce644d`".

## E2 — the register table in §6 lists the wrong Gogs version

§6 lists "Gogs 0.13". Every archived cross-vendor experiment ran **Gogs 0.14.3**
(`gogs_lab.GOGS_VERSION = "0.14.3"`, measured 2026-09-18/19; the version is also
what the manuscript prints as `\GgVersion`). The frozen table is left as written;
`R1.4_application_register_run1.md` row 5 carries the correct version, and its
change log records the correction.

## E3 — what is *not* changed

No criterion, evidence level, threshold, decision rule, scope statement or verdict
is altered by this errata. In particular:

- the four defect classes in §2 are the ones that were run, and no class was added
  or removed after seeing which ones the gate caught;
- the decision procedure in §4 is applied as written, including its one-sided
  preference for `reject`/`unknown`;
- the `pending` rows of §6 are resolved in the application register, and every
  resolved row is `reject` — the rule was not stretched to produce an `admit`.

## E4 — how to verify

```bash
cd experiments/real_system/prereg
sha256sum -c SHA256SUMS                     # frozen protocol, unchanged
git log --follow --format='%h %ci %s' -- R1.4_oracle_admission_v1.md

# from the repository root:
git cat-file -e cce644d:experiments/real_system/prereg/R1.4_oracle_admission_v1.md
echo "exit=$?"                              # non-zero, as E1 says
```

The first command must print `OK`. The second must show `a049cb1` as the
introducing commit and `2c798fc` as the line-ending fix. The third must fail with
"exists on disk, but not in 'cce644d'".
