"""
把「真实 vulnerable/fixed 配对」并入论文数字流水线。
=====================================================

输入：experiments/real_system/results/cve_pair.json（run_cve_pair.py 的产物）
输出：04_绘图与分析/results/cve_pair_numbers.tex  —— 宏 \\Cve*
      04_绘图与分析/results/cve_pair_table.tex    —— 两行结果表

本脚本是 fail-closed 的：任何对照偏离、标签缺失或重复、恢复失败、以及
"缓存字段与按内容复算的结果不一致"，都**报错退出**（宁可构建失败，也不把
偏离当结果发出去）。

校验分四层，缺一不可：
  L1 必需标签集合与唯一性：每版必须恰好有 1 个 MAIN + 5 个对照，不多不少；
  L2 对照响应：每个已知标签的状态码必须映射到预期类别；
  L3 恢复：两版都必须恢复成功，且校验读取为 2xx；
  L4 内容复算：不看写入状态码，用拥有者复读正文重算 Y，再经**同一个**
     classify() 重算分类，与记录里的缓存字段逐一核对。
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

MAIN_LABEL = "cross_repo_object_id"

# 对照探针的预期（两版都必须如此）；主探针按版本单独判
CONTROL_EXPECT = {
    "own_comment": ("ok", "有权者改自己的对象应成功"),
    "correct_path_private_repo": ("denied", "走正确路径访问私有对象应被拒"),
    "cross_repo_third_user": ("denied", "第三方借他人路径应被拒"),
    "anonymous": ("denied", "匿名应被拒"),
    "absent_id": ("denied", "不存在的 id 应 404"),
}
REQUIRED_LABELS = {MAIN_LABEL} | set(CONTROL_EXPECT)

# E 的权威来源：运行时的授权台账，而不是 main 里的缓存字段
LEDGER_KEY = "bob_writes_alice_secret"


def kind(status: int) -> str:
    if 200 <= status < 300:
        return "ok"
    if status in (401, 403, 404):
        return "denied"
    return "other"


def classify(expected: str, observed_allow: bool, alarm: bool,
             promotion: bool) -> dict:
    """与 experiments/real_system/entitlement.py 中的 classify 逐字一致。

    这里重复实现而不是 import：摄入脚本必须能在**没有实验依赖**的环境下
    复算，且重复实现的任何偏离都会被 L4 的一致性检查抓住。
    """
    if promotion and not alarm:
        raise ValueError("promotion without a raw alarm (H => A violated)")
    if not alarm:
        return {"category": "no_alarm", "true_positive": False,
                "false_proof": False}
    if expected == "unknown":
        return {"category": "unscored_unknown_entitlement",
                "true_positive": False, "false_proof": False}
    if expected == "allow":
        return {"category": "false_proof" if promotion else "alarm_on_legitimate",
                "true_positive": False, "false_proof": bool(promotion)}
    if observed_allow:
        return {"category": "true_positive" if promotion else "alarm_on_denied",
                "true_positive": bool(promotion), "false_proof": False}
    return {"category": "alarm_on_denied_not_exploitable",
            "true_positive": False, "false_proof": False}


def esc(s) -> str:
    return (str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_")
            .replace("&", r"\&").replace("%", r"\%").replace("#", r"\#"))


def validate(run: dict) -> list[str]:
    """对单个版本的运行记录做四层校验，返回问题列表（空 = 通过）。"""
    v = run["version"]
    bad: list[str] = []

    # ---- L1 必需标签集合与唯一性 ----
    probes = run.get("probes") or []
    labels = [p.get("label") for p in probes]
    dup = sorted({l for l in labels if labels.count(l) > 1})
    if dup:
        bad.append(f"{v}: 标签重复 {dup}")
    missing = sorted(REQUIRED_LABELS - set(labels))
    if missing:
        bad.append(f"{v}: 缺少必需标签 {missing}")
    extra = sorted(set(labels) - REQUIRED_LABELS)
    if extra:
        bad.append(f"{v}: 出现未登记标签 {extra}")
    if len(probes) != len(REQUIRED_LABELS):
        bad.append(f"{v}: 探针数 {len(probes)} != 应有 {len(REQUIRED_LABELS)}")
    if bad:
        return bad

    main_p = next(p for p in probes if p["label"] == MAIN_LABEL)

    # ---- L2 对照响应 ----
    for p in probes:
        exp = CONTROL_EXPECT.get(p["label"])
        if exp and kind(p["status"]) != exp[0]:
            bad.append(f"{v} {p['label']}: {p['status']} != {exp[0]}")

    # ---- L3 恢复 ----
    rs = run.get("restore") or {}
    if not rs.get("restored"):
        bad.append(f"{v}: 恢复未成功（restored={rs.get('restored')!r}）")
    if kind(rs.get("verify_status", 0)) != "ok":
        bad.append(f"{v}: 恢复校验读取异常（verify_status={rs.get('verify_status')}）")

    # ---- L4 内容复算 ----
    st = run.get("state") or {}
    main = run.get("main") or {}
    if kind(st.get("status", 0)) != "ok":
        bad.append(f"{v}: 拥有者复读失败（status={st.get('status')}）")
        return bad

    bob_mark = main_p.get("body_sent")
    if not bob_mark:
        bad.append(f"{v}: 主探针缺 body_sent，无法按内容复算")
        return bad
    if main.get("body_sent") != bob_mark:
        bad.append(f"{v}: main.body_sent 与主探针 body_sent 不一致")

    # Y 的真值 = 拥有者复读里有没有 bob 的标记；写入状态码不参与
    y = bob_mark in (st.get("body") or "")
    if y != bool(st.get("contains_bob_mark")):
        bad.append(f"{v}: contains_bob_mark 与复读正文不符"
                   f"（缓存 {st.get('contains_bob_mark')} vs 复算 {y}）")
    if y != bool(main.get("Y_allow")):
        bad.append(f"{v}: Y_allow 与复读正文不符"
                   f"（缓存 {main.get('Y_allow')} vs 复算 {y}）")

    # E 取自台账，与缓存字段互核
    ledger = (run.get("ledger") or {}).get(LEDGER_KEY) or {}
    e_ledger = ledger.get("expected_entitlement")
    if e_ledger != main.get("E_object"):
        bad.append(f"{v}: E_object 与台账不符"
                   f"（缓存 {main.get('E_object')} vs 台账 {e_ledger}）")
    if e_ledger is None:
        bad.append(f"{v}: 台账缺 {LEDGER_KEY}")
        return bad

    # 用同一个 classify 重算分类，逐字段核对缓存值
    alarm = y
    try:
        rec = classify(e_ledger, y, alarm=alarm, promotion=alarm)
    except ValueError as exc:
        bad.append(f"{v}: classify 拒绝该组合（{exc}）")
        return bad
    for f in ("category", "true_positive", "false_proof"):
        if rec[f] != main.get(f):
            bad.append(f"{v}: 缓存 {f}={main.get(f)!r} 与复算 {rec[f]!r} 不符")
    if main.get("alarm") != alarm:
        bad.append(f"{v}: 缓存 alarm={main.get('alarm')!r} 与复算 {alarm!r} 不符")
    return bad


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

    # ---- 一致性闸门：四层校验必须全部通过 ----
    bad: list[str] = []
    for r in (vuln, fixed):
        bad.extend(validate(r))
    if bad:
        print("!! 配对记录未通过校验，拒绝生成数字：")
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
                            if p["label"] != MAIN_LABEL),
        "CveRestoreChecks": sum(1 for r in (vuln, fixed)
                                if (r.get("restore") or {}).get("restored")),
        "CveProbes": sum(len(r["probes"]) for r in (vuln, fixed)),
        "CveRestored": sum(1 for r in (vuln, fixed)
                           if (r.get("restore") or {}).get("restored")),
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
    print(f"  四层校验通过：标签集合+唯一性 / 对照响应 / 恢复 / 内容复算")
    print(f"  对照 {M['CveControls']} 条响应对照 + {M['CveRestoreChecks']} 条恢复检查"
          f" = {M['CveControls'] + M['CveRestoreChecks']} 项全部符合预期")
    print(f"写出 {RESULTS / 'cve_pair_numbers.tex'}")
    print(f"     {RESULTS / 'cve_pair_table.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
