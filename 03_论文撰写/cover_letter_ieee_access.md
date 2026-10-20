# Cover letter — IEEE Access

**To:** The Editor-in-Chief, *IEEE Access*
**Article type:** Research Article (Original Research)
**Manuscript title:** *Two Reachability-Gated Relations in MST-wi: Temporal Mismatch, Oracle Admissibility, and Measurement Limits*

---

Dear Editor,

We resubmit the enclosed manuscript (Access-2026-49387) as a Research Article in
*IEEE Access*, together with a point-by-point response to the two reports. It reports an empirical study, spanning both constructed and real
Web systems, of what metamorphic testing can and cannot establish when it is used
to detect **broken object-level authorization (BOLA)** — the top-ranked API
security risk in the OWASP API Security Top 10.

**The problem.** Authorization faults are an oracle problem: a vulnerable system
and a correct one answer the same request identically, so detection cannot rely
on a ground-truth oracle. Metamorphic testing is a leading substitute. For the
published object-level-authorization relations we study, their predicates
delegate the verdict to a *GUI-reachability model* — a crawl-time snapshot of
what the interface permits. We instantiate those relations as defined and drive
constructed and real systems through crawl, out-of-band change, and execution.

**What we find.** Three limits, each answering one research question:
1. **Temporal reachability (RQ1).** Access granted out of band *after* the crawl
   is reported as a *proven* violation — a *false proof*. The reason is
   structural: the predicate's two representations can each express an
   out-of-band grant, but only the wrong one, so the error is a property of the
   relation, not of the system under test.
2. **Oracle admissibility (RQ2).** When a readable, sound authorization oracle
   that fully resolves the proposition is available, the metamorphic step adds no
   observed adjudication information beyond that oracle plus the request outcome;
   the paired methods disagree on only a handful of true-violation records, all
   favouring the direct request.
3. **Measurement resolution (RQ3).** The reported specificity is not conditioned
   on an explicit check that the reachability model coincides with the
   authorization state, and its input-level denominator cannot register a
   scenario-uniform failure.

The findings come from a 576-record scenario/configuration study on Gitea 1.22.6,
extended to Gogs 0.14.3 and GitLab 17.11.7, with an endogenous control holding
final visibility fixed; executing the published relations on the native engine
reproduces the false proof within the gated subset that fires.

**Fit with *IEEE Access*.** The work sits at the intersection of two of the
journal's core areas — **security and privacy of networked and Web/API systems**
(authentication and authorization) and **software engineering / software
testing** — and is applications-oriented and empirical, which matches the
multidisciplinary, applications-focused remit of *IEEE Access*. It informs not
only API-security practitioners (who need to know what a "proven violation"
from these relations actually means) but also the software-testing community
that maintains and applies metamorphic relations.

**Honest scope.** We are explicit about the boundaries of the claims: they cover
the reachability-gated authorization relations examined here, instantiated as two
metamorphic relations across three self-hosted platforms; the positive control is
a controlled research artefact, not a production deployment, and we do **not**
claim a real-world CVE against Gitea. The paper uses descriptive point estimates
and makes no sensitivity/specificity inferential, non-inferiority, or
domination claims.

**Reproducibility.** The companion repository is publicly archived
(GitHub tag `artifact-v1`; byte-identical Zenodo copy, DOI
10.5281/zenodo.22859942). No number in the manuscript is hand-typed: every value
is recomputed from the raw records by a single analysis pipeline, one command
regenerates all outputs and the PDF, and a self-check script asserts the SHA-256
of every raw record and byte-reproducible output.

**Declarations.** The manuscript is original, has not been published previously,
and is not under consideration elsewhere. All authors have approved the
submission and declare no competing interests; the work received no specific
funding. The use of a generative-AI assistant (limited to literature
cross-checking, analysis-script development, and language polishing, with all
computation independently verified by the authors) is disclosed in the
Declarations section.

We would be glad to address any questions.

Sincerely,
Qiulong Lin and Nanlei Chen
Yango University, Fuzhou, China / Sogang University, Seoul, Republic of Korea
Corresponding author: Nanlei Chen — ubfbzu3@163.com
