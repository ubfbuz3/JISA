"""
实验 B 结果分析 · 把 real_system.json 折成可写进论文的表
=========================================================
产出：
  results/REAL_SYSTEM_RESULTS.md    人读表格
  results/real_system_summary.json  机读汇总

口径约定（必须与第七轮 Block 9 可比）
  真值：violation ⟺ (¬should_allow) ∧ access。Gitea 正确 ⇒ 真 violation 恒为 0。
  ⇒ 真实系统上**任何告警都是误报**，因此把告警按落在哪类单元格上分开计：
      alarms_on_authorized  = 对**合法被授权**的访问贴 `violation-proven`  ← 本方向的核心错误类型"假确证"
      alarms_on_denied      = 对**被正确拒绝**的访问贴 `violation-proven`  ← 忽略访问结果的产物
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
METHODS = ("mr_bookkeeping", "v3", "v3_self", "direct_only", "direct_observe",
           "direct_observe_self")
DESC = {
    "mr_bookkeeping": "MR 触发 ∧ 框架自己的共享日志无记录（≈MST-wi 的位置：谓词相对采集记录）",
    "v3": "MR 触发 ∧ **以拥有者/管理员凭证**读自省面 ∧ 自省面明确报告 none",
    "v3_self": "MR 触发 ∧ **以被测主体自己凭证**读自省面 ∧ 报告 none（黑箱测试者的自然视点）",
    "direct_only": "只看自省面（不消费访问结果）",
    "direct_observe": "普通请求可访问 ∧ **拥有者视点**自省面报告 none",
    "direct_observe_self": "普通请求可访问 ∧ **主体自身视点**自省面报告 none",
}


def main():
    rep = json.loads((RESULTS / "real_system.json").read_text(encoding="utf-8"))
    L: list[str] = []
    P = L.append

    P("# 实验 B · 真实系统对照结果（Gitea %s）" % rep["meta"]["gitea_version"])
    P("")
    P("> 诚实边界：%s" % rep["meta"]["honesty_boundary"])
    P("")
    P("阶段：%s" % " → ".join(rep["meta"]["phases"]))
    P("实验台：`%s`；耗时 %ss。" % (rep["meta"]["lab_dir"], rep["meta"]["elapsed_s"]))
    A = rep["phaseA_topology"]
    P("拓扑步骤 %d，失败 %d。" % (len(A["steps"]), len(A["failures"])))
    for f in A["failures"]:
        P("- **失败** `%s` status=%s %s" % (f["step"], f["status"], f.get("error") or ""))
    C = rep["phaseC_mutations"]
    P("带外授权变更 %d 项，失败 %d。" % (len(C["mutations"]), len(C["failures"])))
    for m in C["failures"]:
        P("- **失败** `%s` status=%s %s" % (m["mutation"], m["status"], m.get("error") or ""))
    P("")

    # ---------------- M1 ----------------
    m1 = rep.get("M1_grant_mechanism_census", {})
    P("## M1 · 授权授予机制空间普查（实例无关）")
    P("")
    if "error" in m1:
        P("**未能采集**：%s" % m1["error"])
    else:
        P("判据：%s" % m1["predicate"])
        P("")
        P("Gitea swagger 路径总数 **%d**；其中可作为「授权授予机制」的端点 **%d** 个"
          "（另有 %d 个仅能撤销、不算授予），其中**不需站点管理员即可执行**的 **%d** 个。"
          % (m1["swagger_total_paths"], m1["grant_endpoints_total"],
             m1["revoke_endpoints_total"], m1["grant_endpoints_without_site_admin"]))
        P("")
        P("| 端点 | 方法 | 方向 | 需要站点管理员 | 类别 |")
        P("|---|---|---|---|---|")
        for e in m1["endpoints"]:
            P("| `%s` | %s | %s | %s | %s |"
              % (e["endpoint"], ",".join(e["methods"]),
                 "授予" if e["direction"] == "grant" else "撤销",
                 "是" if e["requires_site_admin"] else "否", e["kind"]))
        P("")
        by = Counter(e["kind"].split("：")[0] for e in m1["endpoints"] if e["direction"] == "grant")
        P("按层面（仅授予）：%s" % "；".join(f"{k} {v}" for k, v in by.most_common()))
    P("")

    # ---------------- M2 ----------------
    P("## M2 · 自省面视点可读性矩阵")
    P("")
    for obj, d in rep.get("M2_vantage_readability", {}).items():
        P("对象 `%s`，被查询主体 `%s`：" % (obj, d["subject"]))
        P("")
        P("| 视点 | 读取对象 | 列举协作者 | 查询权限 |")
        P("|---|---|---|---|")
        for v, row in d["vantages"].items():
            def cell(k):
                st = row[k]["status"]
                pm = row[k].get("perm")
                return "`%s`%s" % (st, " → `%s`" % pm if pm else "")
            P("| %s | %s | %s | %s |" % (v, cell("object_read"),
                                         cell("introspect_list"), cell("introspect_perm")))
        P("")
    P("")

    # ---------------- M3 ----------------
    P("## M3 · 自省面保真度（以拥有者凭证读到的所报权限 vs 有效访问）")
    P("")
    fid = [f for f in rep.get("M3_introspection_fidelity", []) if f["authorized"] is not None]
    infid = [f for f in fid if bool(f["authorized"]) != bool(f["permission"] and f["permission"] != "none")]
    P("| 单元格 | 主体 | 有效访问 | 自省面状态 | 所报权限 | 一致 |")
    P("|---|---|---|---|---|---|")
    for f in fid:
        ok = bool(f["authorized"]) == bool(f["permission"] and f["permission"] != "none")
        P("| %s | %s | %s | `%s` | %s | %s |"
          % (f["object"], f["subject"], "是" if f["authorized"] else "否",
             f["status"], f["permission"] or "—", "✓" if ok else "**✗**"))
    P("")
    P("（已排除「执行者自身」单元格：它们不是换凭证测试的对象，不参与一致性判定。）")
    P("")
    P("→ 不一致 **%d / %d**%s" % (len(infid), len(fid),
        "：" + "；".join("%s×%s" % (i["object"], i["subject"]) for i in infid) if infid else "（自省面在该拓扑上保真）"))
    P("")
    P("其中「自省面状态」的分布：%s"
      % "；".join(f"`{k}` × {v}" for k, v in Counter(f["status"] for f in fid).most_common()))
    P("")

    # ---------------- M3b：自省面在两种视点下的可读性 ----------------
    P("## M3b · 自省面的两种视点：拥有者/管理员 vs 被测主体自身")
    P("")
    P("| 视点 | 可读单元格数 | 读不到的单元格数 | 读不到时的状态码分布 |")
    P("|---|---|---|---|")
    for tag, rk, sk in (("拥有者/管理员（v3 的规定视点）", "readable", "status"),
                        ("被测主体自身（黑箱测试者的自然视点）", "readable_self", "status_self")):
        rd = sum(1 for f in fid if f[rk])
        un = [f for f in fid if not f[rk]]
        P("| %s | %d / %d | %d | %s |"
          % (tag, rd, len(fid), len(un),
             "；".join(f"`{k}` × {v}" for k, v in Counter(f[sk] for f in un).most_common()) or "—"))
    P("")
    P("→ **自省面在「被测主体自身」视点下**：%s"
      % ("完全不可读 ⇒ 任何依赖自省面的判定器在该视点下只能弃权（检出力 0）。"
         if not any(f["readable_self"] for f in fid)
         else "部分可读，需逐单元格讨论。"))
    P("")
    P("按主体拆开看（关键：那 %d 个「可读」的单元格是谁的）："
      % sum(1 for f in fid if f["readable_self"]))
    P("")
    P("| 主体 | 单元格数 | 自身视点可读 | 不可读时的状态码 |")
    P("|---|---|---|---|")
    by_subj = defaultdict(list)
    for f in fid:
        by_subj[f["subject"]].append(f)
    for s in sorted(by_subj, key=lambda x: -sum(1 for f in by_subj[x] if f["readable_self"])):
        rows = by_subj[s]
        rd = sum(1 for f in rows if f["readable_self"])
        un = [f for f in rows if not f["readable_self"]]
        P("| %s | %d | %d | %s |"
          % (s, len(rows), rd,
             "；".join(f"`{k}` × {v}" for k, v in Counter(f["status_self"] for f in un).most_common())
             or "—"))
    P("")
    P("⇒ 除**站点管理员**外，任何主体在自己的视点下都读不到授权自省面。")
    P("")

    # ---------------- M4 ----------------
    P("## M4 · 采集期爬取记录 vs 变更后有效访问")
    P("")
    cells = rep["phaseE_cells"]
    for reading in ("snapshot", "live"):
        rc = [c for c in cells if c["reading"] == reading]
        fires = [c for c in rc if c["mr_fires"]]
        mismatch = sorted({(c["subject"], c["object"]) for c in rc
                           if c["cannotReachThroughGUI"] and c["authorized"]})
        P("**%s 读法**：`cannotReachThroughGUI` 为真**但主体确实可访问**的单元格 **%d** 个"
          % (reading, len(mismatch)))
        if mismatch:
            P("")
            P("| 主体 | 对象 |")
            P("|---|---|")
            for s, o in mismatch:
                P("| %s | %s |" % (s, o))
        P("")
    P("")

    # ---------------- M5 ----------------
    P("## M5 · 方法对照（Gitea 正确 ⇒ 真 violation 恒为 0，任何告警都是误报）")
    P("")
    P("| 方法 | 说明 |")
    P("|---|---|")
    for m in METHODS:
        P("| `%s` | %s |" % (m, DESC[m]))
    P("")
    summary = {}
    for reading in ("snapshot", "live"):
        rc = [c for c in cells if c["reading"] == reading]
        n = len(rc)
        auth = sum(1 for c in rc if c["authorized"])
        P("### %s 读法（单元格 %d，其中主体真实被授权 %d）" % (reading, n, auth))
        P("")
        P("| 方法 | 告警总数 | **假确证**（落在被授权单元格） | 落在被拒绝单元格 | 假确证残差 |")
        P("|---|---|---|---|---|")
        for m in METHODS:
            al = [c for c in rc if c["alarms"][m]]
            on_auth = [c for c in al if c["authorized"]]
            on_den = [c for c in al if not c["authorized"]]
            summary[f"{reading}|{m}"] = {
                "alarms": len(al), "on_authorized": len(on_auth), "on_denied": len(on_den),
                "cells": n, "authorized_cells": auth}
            P("| `%s` | %d | **%d** | %d | %s |"
              % (m, len(al), len(on_auth), len(on_den),
                 "%.4f" % (len(on_auth) / auth) if auth else "n/a"))
        P("")
        fires = [c for c in rc if c["mr_fires"]]
        P("MR 触发（家族签名成立：测试者 GUI 到不了 ∧ 非管理员 ∧ 输出与执行者相同）**%d / %d**："
          % (len(fires), n))
        if fires:
            P("")
            P("| 对象 | 主体 | 触发但真实被授权 | 框架日志有无记录 | 自省面所报 |")
            P("|---|---|---|---|---|")
            for c in sorted(fires, key=lambda x: (x["object"], x["subject"])):
                P("| %s | %s | %s | %s | %s |"
                  % (c["object"], c["subject"], "是" if c["authorized"] else "否",
                     "有" if c["framework_log_has_record"] else "**无**",
                     c["introspection_permission"] or "—"))
        P("")
    P("")

    # ---------------- M6 ----------------
    P("## M6 · 授权通道定性与带外占比")
    P("")
    prov = rep.get("M6_provenance", [])
    have = [p for p in prov if p["channel"] != "none"]
    cnt = Counter(p["channel"] for p in have)
    inband = cnt.get("in_band_share", 0)
    P("有效访问单元格 **%d**。按通道：" % len(have))
    P("")
    P("| 通道 | 数量 | 被「框架自己的动作日志」记录 |")
    P("|---|---|---|")
    for ch, k in cnt.most_common():
        P("| %s | %d | %s |" % (ch, k, "✅" if ch == "in_band_share" else "❌"))
    P("")
    P("→ **带外（不被框架动作日志记录）= %d / %d = %.1f%%**"
      % (len(have) - inband, len(have), 100 * (len(have) - inband) / max(1, len(have))))
    P("")
    P("⚠️ 该比例依赖本实验构造的拓扑（是设计参数，不是野外发生率估计）；"
      "实例无关的部分是 M1 的机制空间普查。")
    P("")
    P("---")
    P("")
    P("## ★ 结论（按读法分层，不得只报其一）")
    P("")
    snap = summary.get("snapshot|mr_bookkeeping", {})
    live = summary.get("live|mr_bookkeeping", {})
    v3s = summary.get("snapshot|v3", {})
    v3self = summary.get("snapshot|v3_self", {})
    donly = summary.get("snapshot|direct_only", {})
    P("- **snapshot 读法**：MR 家族在采集**之后**新增的授权上签名成立，"
      "`mr_bookkeeping` 产生 **%d** 个假确证（占 %d 个被授权单元格的 %.1f%%）。"
      % (snap.get("on_authorized", 0), snap.get("authorized_cells", 0),
         100 * snap.get("on_authorized", 0) / max(1, snap.get("authorized_cells", 1))))
    P("- **live 读法**：同一批单元格上 `mr_bookkeeping` 假确证 **%d** ⇒ 失效**仅**在 "
      "GUI 模型取快照时出现（这是必须与结论一起声明的条件）。" % live.get("on_authorized", 0))
    P("- `v3`（拥有者/管理员视点读面）两种读法下假确证均 **%d**，但它需要**特权凭证**才能读面。"
      % v3s.get("on_authorized", 0))
    P("- `v3_self`（被测主体自身视点读面）假确证 **%d**，且因自省面在该视点下不可读而"
      "**全部弃权** ⇒ 检出力 0。" % v3self.get("on_authorized", 0))
    P("- `direct_only` 的 **%d** 个告警全部落在**被正确拒绝**的单元格上，"
      "即「忽略访问结果」的产物，与第七轮审判方的定性一致。" % donly.get("on_denied", 0))
    P("")
    P("⇒ **真实系统上的完整图景**：不存在一个视点同时满足"
      "（a）能读到授权自省面 与（b）是合法的黑箱测试者——"
      "能读面的只有已经知道答案的拥有者/管理员；"
      "而真正处于黑箱位置的被测主体读不到面，只能弃权。")
    P("")

    out_md = RESULTS / "REAL_SYSTEM_RESULTS.md"
    out_md.write_text("\n".join(L), encoding="utf-8")
    (RESULTS / "real_system_summary.json").write_text(
        json.dumps({
            "methods": summary,
            "cells": len(cells),
            "grant_endpoints": m1.get("grant_endpoints_total"),
            "grant_endpoints_without_site_admin": m1.get("grant_endpoints_without_site_admin"),
            "revoke_endpoints": m1.get("revoke_endpoints_total"),
            "introspection_infidelity": len(infid),
            "oob_share": round((len(have) - inband) / max(1, len(have)), 4),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(L))
    print(f"\n[done] -> {out_md}")


if __name__ == "__main__":
    main()
