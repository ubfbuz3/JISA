# Immutable review packet

Review target is Git commit `8e2c706` (full revision is resolved from Git), not subsequent audit files. Working directory is `C:/Users/Administrator/WorkBuddy/3区论文`. Do not edit manuscript, experiments, correspondence, or Git state.

User asks to verify the latest revision package and also review the manuscript. Journal is IEEE Access, rejection with one resubmission opportunity. Do not impose Nature journal selectivity or invent reviewer identities. Apply nature-reviewer grounding, concern severity, resolution tests and reviewer isolation. These are simulated independent assessments, not actual journal reviewer decisions.

Common source basis:
- `03_论文撰写/paper/main.tex`, `sections/*.tex`, generated inputs from `04_绘图与分析/results/`, and `main.pdf` (current manuscript).
- `experiments/` code and raw records, `04_绘图与分析/analysis/`, `reproduce.sh`, `verify_artifact.sh`, provenance manifests, `ARTIFACT.md`.
- Original decision/review text `06_论文追踪/2026-10-18_IEEEAccess重投诊断/本轮决定信与审稿意见_原文.txt`.
- Initial manuscript `03_论文撰写/response_to_reviewers/baseline/submitted_main.pdf`, source ZIP in the same directory. Verify provenance from repository and manuscript metadata if needed; do not assume file labels establish portal provenance.
- Current response letter `03_论文撰写/response_to_reviewers/response_to_reviewers.tex` and PDF can be checked against the manuscript. It is an author statement, not independent evidence.

Do not read any prior review reports, audit reports, status trackers, other agents' reports, or conversation notes as analytical input. Derive concerns independently from the common source basis. Do not use other reviewers' findings or infer agreement. Keep your report unchanged after delivering it, unless correcting an objective factual transcription error.

Review original and current scientific case under five axes: originality relative to declared scope, scientific importance for its intended security-testing audience, technical soundness, evidence-to-claim fit, and readability. Use concern taxonomy as an internal coverage check, not a quota. Do not require tests or experiments merely to fill gaps beyond the actual claims/reviewer requests. Distinguish unmet explicit requests from defensible scope disagreement.

Each report must include: overall assessment; genuine strengths; major concerns with stable ID, Blocking Yes/No, exact manuscript claim pointer and code/data evidence pointer, implication and resolution test; minor comments; unresolved/unsupported or unassessable items; bounded recommendation. Use verified file line numbers or PDF pages. Do not predict acceptance probability.

All findings must be reproducible/read-only. If you need temporary analyses, write only inside your assigned output directory under this audit folder. Bundled Python: `C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` with pypdf/pdfplumber. Use `-X utf8`. Git executable `C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe`; add `-c safe.directory=C:/Users/Administrator/WorkBuddy/3区论文` per command.

Emphasis briefs fixed before review:
1. Reviewer A: theoretical statements, E/Y/O/A/H/T definitions, truth/independence, domain restrictions and mathematical validity.
2. Reviewer B: experiment integrity, raw-to-claim calculations, controlled comparisons, cost/abstention, implementation/protocol alignment and reproducibility.
3. Reviewer C: narrative, novelty and prior-work positioning, manuscript consistency and readability, original-to-current claim changes, response coverage and scope.

These emphases are lenses, not identities. All receive exactly this packet and may independently examine any source in the common source basis. Write only your own report. Primary agent will synthesize only after all reports are frozen.
