# Cover Letter — Computer Networks

**To:** The Editors-in-Chief, *Computer Networks* (Elsevier)
**Manuscript type:** Regular research article (submitted manuscript, no number yet)
**Title:** *Limits of Metamorphic Testing for Object-Level Authorization: Temporal
Reachability, Oracle Admissibility, and Measurement Resolution*

---

Dear Editors,

We submit the above manuscript for your consideration as a regular research
article in *Computer Networks*.

## 1. Why this paper belongs in *Computer Networks*

Our work studies **broken object-level authorization (BOLA)** — the
top-ranked risk in the OWASP API Security Top 10 — and the dominant automated
technique used to test for it, **metamorphic testing (MT)**. We characterize the
limits of that technique when it is applied to authorization in **Web/API
systems**. This sits directly within three of the journal's stated subject
areas:

- **Network Security and Privacy** (Aims & Scope item 4), which explicitly
  lists *authentication* and *authorization*: object-level authorization is the
  per-object enforcement of "is this authenticated subject entitled to this
  object," the core access-control problem in networked applications.
- **Network Services and Applications** (item 3), which covers the *Web*:
  the systems we study are Web/API services, and the failure we expose is a
  web/API security failure.
- **Communication Network Protocols** (item 2), which includes *protocol
  specification, testing and verification*: our method is a security-testing
  and verification study of how an authorization protocol predicate behaves
  under out-of-band state change.

The paper is therefore a **security-testing contribution for networked
Web/API authorization**, using MT as the technique — not a pure
software-engineering methodology study. We believe *Computer Networks*' broader
remit (network/cyber security + web services + protocol testing) is the correct
home for it.

## 2. What the paper does (and does not) claim

We instantiate a published MT relation set for object-level authorization *as
defined* and drive constructed and real systems (Gitea, extended to Gogs and
GitLab) through three phases — **crawl, out-of-band authorization change,
execute** — the middle phase being the one the original evaluation never
exercised. Three findings follow, each bounded to the evidence:

1. **Temporal.** A legitimate access granted out of band after the crawl is
   reported as a *proven* violation (a deterministic false proof), because the
   reachability predicate's two representations cannot describe an out-of-band
   grant. The error is a property of *when the model was read*, not of the
   system.
2. **Oracle.** When a readable, sound authorization oracle is available, the
   metamorphic step adds no observed adjudication information beyond the oracle
   and the request outcome (a necessary condition we formalize).
3. **Measurement.** A published specificity figure is not conditioned on a check
   that the reachability model equals the authorization state, and its
   input-level denominator cannot register a class-uniform failure.

We do **not** claim MT is wrong, and we do **not** claim our results generalize
beyond the reachability-gated authorization relations we actually examined; the
manuscript states where the transfer stops. No new detector is proposed — the
contribution is a characterization with internal controls, an endogenous
control, a seeded-vulnerability positive control, source reading, native
execution of the library's own relations, and an independent second
implementation.

## 3. Compliance statements

- **Originality / no duplicate submission:** The work is original and is not
  under consideration elsewhere. It was previously submitted to a
  security-*applications* journal and declined without review as out of that
  journal's scope; that decision concerned venue fit, not quality, and the
  manuscript has been reframed for *Computer Networks*.
- **Authorship / conflicts:** All authors have approved the submission. There
  are no competing interests.
- **Funding:** The manuscript reports no funding (stated in the declarations).
- **Ethics:** No human or animal subjects are involved. All testing was
  performed only on self-hosted instances of open-source software; no
  third-party or production system was tested without authorization.
- **Data / code availability:** The scenario/configuration record, the
  experimental scripts, and the analysis code are archived with a persistent
  DOI (Zenodo: 10.5281/zenodo.22859942) and a tagged GitHub release, so the
  figures and all reported numbers are reproducible from source.

We suggest the manuscript is in scope for the journal's Network Security and
Privacy / Web-services tracks and would be of interest to readers building or
testing access control in networked systems. Thank you for your consideration.

Sincerely,

Qiulong Lin (corresponding author)
Nanlei Chen
Yango University, Fuzhou, China; Sogang University, Seoul, Republic of Korea
