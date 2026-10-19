"""
把「真实 vulnerable/fixed 配对」并入论文数字流水线。
=====================================================

输入：experiments/real_system/results/cve_pair.json（run_cve_pair.py 的产物）
输出：04_绘图与分析/results/cve_pair_numbers.tex  —— 宏 \\Cve*
      04_绘图与分析/results/cve_pair_table.tex    —— 两行结果表

任何对照探针不符合预期即**报错退出**（宁可构建失败，也不把偏离当结果发出去）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RESULTS = HERE.parent / "results"
SRC = ROOT / "experiments" / "real_system" / "results" / "cve_pair.json"

# 对照探针的预期（两版都必须如此）；主探针按版本单独判
CONTROL_EXPECT = {
    "own_comment": ("ok", "有权者改自己的对象应成功"),
    "correct_path_private_repo": ("denied", "走正确路径访问私有对象应被拒"),
    "cross_repo_third_user": ("denied", "第三方借他人路径应被拒"),
    "anonymous": ("denied", "匿名应被拒"),
    "absent_id": ("denied", "不存在的 id 应 404"),
}


def kind(status: int) -> str:
    if 200 <= status < 300:
        return "ok"
    if status in (401, 403, 404):
        return "denied"
    return "other"


def esc(s) -> str:
    return (str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_")
            .replace("&", r"\&").replace("%", r"\%").replace("#", r"\#"))


def main() -> int:
    if not SRC.exists():
        print(f"!! 缺少 {SRC}（先跑 run_cve_pair.py）")
        return 2
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    runs = {r["version"]: r for r in doc.get("runs") or []}
    for v in ("1.20.5", "1.20.6"):
        if v not in runs:
            print(f"!! cve_pair.json 缺版本 {v}")
            return 2
    vuln, fixed = runs["1.20.5"], runs["1.20.6"]

    # ---- 一致性闸门：对照必须全部符合预期 ----
    bad = []
    for r in (vuln, fixed):
        for p in r["probes"]:
            exp = CONTROL_EXPECT.get(p["label"])
            if exp and kind(p["status"]) != exp[0]:
                bad.append(f"{r['version']} {p['label']}: {p['status']} != {exp[0]}")
    if bad:
        print("!! 对照探针偏离预期，拒绝生成数字：")
        for b in bad:
            print("   " + b)
        return 3

    mv, mf = vuln["main"], fixed["main"]
    # 主探针的状态码本身不参与判定（判定用拥有者复读）；这里只记录诊断值
    M = {
        "CveVersions": 2,
        "CveVulnVersion": vuln["version"],
        "CveFixedVersion": fixed["version"],
        "CveVulnStatus": mv["write_status"],
        "CveFixedStatus": mf["write_status"],
        "CveVulnChanged": 1 if mv["Y_allow"] else 0,
        "CveFixedChanged": 1 if mf["Y_allow"] else 0,
        "CveTruePositives": sum(1 for m in (mv, mf) if m["category"] == "true_positive"),
        "CveFalseProofs": sum(1 for m in (mv, mf) if m["false_proof"]),
        "CveFixedAlarms": sum(1 for m in (mf,) if m["alarm"]),
        "CveControls": sum(1 for r in (vuln, fixed)
                            for p in r["probes"]
                            if p["label"] != "cross_repo_object_id"),
        "CveProbes": sum(len(r["probes"]) for r in (vuln, fixed)),
        "CveRestored": sum(1 for r in (vuln, fixed) if r["restore"]["restored"]),
        "CveVulnSha": vuln["sha256"][:12],
        "CveFixedSha": fixed["sha256"][:12],
    }

    lines = ["% 由 analysis/ingest_cve_pair.py 自动生成 —— 请勿手改",
             "% 源: experiments/real_system/results/cve_pair.json",
             "% Gitea 1.20.5 (vulnerable) vs 1.20.6 (fixed): "
             "comment permissions fix (#28213 / #28216)", ""]
    for k, v in M.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    (RESULTS / "cve_pair_numbers.tex").write_text("\n".join(lines) + "\n",
                                                  encoding="utf-8")

    tl = ["% 由 analysis/ingest_cve_pair.py 自动生成 —— 请勿手改",
          "\\footnotesize",
          "\\setlength{\\tabcolsep}{4pt}",
          "\\begin{tabular}{@{}llll@{}}", "\\toprule",
          "version & PATCH & re-read & verdict \\\\", "\\midrule"]
    for r, lab in ((vuln, "vulnerable"), (fixed, "fixed")):
        m = r["main"]
        body = "changed" if m["Y_allow"] else "unchanged"
        verdict = ("true positive" if m["category"] == "true_positive"
                   else "no claim" if m["category"] == "no_alarm"
                   else esc(m["category"]))
        tl.append(f"{r['version']} ({lab}) & {m['write_status']} & {body} & {verdict} \\\\")
    tl += ["\\bottomrule", "\\end{tabular}"]
    (RESULTS / "cve_pair_table.tex").write_text("\n".join(tl) + "\n", encoding="utf-8")

    print("真实配对（Gitea comment permissions）")
    for r in (vuln, fixed):
        m = r["main"]
        s = r["state"]
        print(f"  {r['version']}: PATCH={m['write_status']}  "
              f"owner_body={s['body'][:38]!r}  changed={m['Y_allow']}  -> {m['category']}")
    print(f"  true positives={M['CveTruePositives']}  false proofs={M['CveFalseProofs']}  "
          f"alarms on fixed={M['CveFixedAlarms']}")
    print(f"  对照 {M['CveControls']} 条全部符合预期；恢复 {M['CveRestored']}/2")
    print(f"写出 {RESULTS / 'cve_pair_numbers.tex'}")
    print(f"     {RESULTS / 'cve_pair_table.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
