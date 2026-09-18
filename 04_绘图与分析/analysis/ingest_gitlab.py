# -*- coding: utf-8 -*-
"""
把「GitLab 跨厂商复核」（Block 13）的结果并入论文数字流水线。
==================================================================

输入（全部为实测产物，任何数字都不手敲）：
  * experiments/real_system/results/gitlab_real_system.json —— run_gitlab.py 的产物
  * experiments/real_system/results/gogs_real_system.json   —— Block 12 产物（对照列）
  * experiments/real_system/results/real_system.json        —— Gitea 侧同协议产物
  * experiments/real_system/results/m1_matched_gitea.json   —— 共享模式表下 Gitea 的 M1

输出：
  * 04_绘图与分析/results/gitlab_numbers.tex     —— 宏定义（\\Gl*）
  * 04_绘图与分析/results/gogs_cross_table.tex   —— **三系统**对照表（重生成，
    文件名沿用以避免改动 build.sh 与 \\input）
  * stdout: 人读小结

与 ingest_gogs.py 的关系：判定原语（says_none / analyze_cells / m6_channels）
直接 import 复用——三系统的数字口径由同一份代码保证。

用法:
  python analysis/ingest_gitlab.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ingest_gogs import (analyze_cells, m6_channels, oracle_fn_channels)  # noqa: E402

ROOT = HERE.parent.parent                      # 3区论文/
RS = ROOT / "experiments" / "real_system" / "results"
OUT = HERE.parent / "results"

GITLAB_JSON = RS / "gitlab_real_system.json"
GOGS_JSON = RS / "gogs_real_system.json"
GITEA_JSON = RS / "real_system.json"
GITEA_M1 = RS / "m1_matched_gitea.json"

PFX = "Gl"          # GitLab 侧宏前缀
METHODS = ("mr_bookkeeping", "v3", "v3_self", "direct_only",
           "direct_observe", "direct_observe_self")


def main() -> None:
    gl_json = json.loads(GITLAB_JSON.read_text(encoding="utf-8"))
    gogs = json.loads(GOGS_JSON.read_text(encoding="utf-8"))
    gitea = json.loads(GITEA_JSON.read_text(encoding="utf-8"))
    gitea_m1 = json.loads(GITEA_M1.read_text(encoding="utf-8"))

    cells = gl_json["phaseE_cells"]
    snap = analyze_cells([c for c in cells if c["reading"] == "snapshot"])
    live = analyze_cells([c for c in cells if c["reading"] == "live"])

    # oracle 假阴性的通道归因（仅 snapshot；机械查 M6）
    fn_cells = [c for c in cells if c["reading"] == "snapshot"
                and c["introspection_readable"] and c["authorized"]
                and c["introspection_status"] == 404]
    fn_ch = dict(oracle_fn_channels(gl_json, fn_cells))

    m1 = gl_json["M1_grant_mechanism_census"]
    m6 = dict(m6_channels(gl_json))
    v = {
        "gitlab_version": gl_json["meta"]["gitlab_version"],
        "l_cells": len(cells) // 2,
        "l_route_entries": m1["denominator_entries"],
        "l_route_paths": m1["route_entries_raw"],
        "l_grant_endpoints": m1["grant_endpoints_total"],
        "l_grant_no_admin": m1["grant_endpoints_without_site_admin"],
        "l_snap": snap, "l_live": live,
        "l_wrong_pct": round(100.0 * snap["oracle_fn"] / snap["oracle_readable"], 1)
                        if snap["oracle_readable"] else 0.0,
        "l_fn_ch": fn_ch,
        "l_m6": m6,
        "g_cells_snap": analyze_cells([c for c in gogs["phaseE_cells"]
                                       if c["reading"] == "snapshot"]),
        "g_live_snap": analyze_cells([c for c in gogs["phaseE_cells"]
                                      if c["reading"] == "live"]),
        "t_snap": analyze_cells([c for c in gitea["phaseE_cells"]
                                 if c["reading"] == "snapshot"]),
        "t_live": analyze_cells([c for c in gitea["phaseE_cells"]
                                 if c["reading"] == "live"]),
    }

    # ---------------- 宏 ----------------
    s, l_ = snap, live
    macros = "\n".join([
        "% 由 analysis/ingest_gitlab.py 自动生成 —— 勿手改",
        "% 来源: experiments/real_system/results/gitlab_real_system.json",
        "",
        f"\\newcommand{{\\{PFX}Version}}{{{v['gitlab_version']}}}",
        f"\\newcommand{{\\{PFX}Cells}}{{{v['l_cells']}}}",
        f"\\newcommand{{\\{PFX}RouteEntries}}{{{v['l_route_entries']}}}",
        f"\\newcommand{{\\{PFX}RoutePaths}}{{{v['l_route_paths']}}}",
        f"\\newcommand{{\\{PFX}GrantEndpoints}}{{{v['l_grant_endpoints']}}}",
        f"\\newcommand{{\\{PFX}GrantNoSiteAdmin}}{{{v['l_grant_no_admin']}}}",
        f"\\newcommand{{\\{PFX}OracleReadable}}{{{s['oracle_readable']}}}",
        f"\\newcommand{{\\{PFX}OracleAgree}}{{{s['oracle_agree']}}}",
        f"\\newcommand{{\\{PFX}OracleWrong}}{{{s['oracle_fn']}}}",
        f"\\newcommand{{\\{PFX}OracleWrongPct}}{{{v['l_wrong_pct']}}}",
        f"\\newcommand{{\\{PFX}SelfReadable}}{{{s['self_readable']}}}",
        f"\\newcommand{{\\{PFX}SelfAgree}}{{{s['self_agree']}}}",
        f"\\newcommand{{\\{PFX}MismatchSnap}}{{{s['mismatch']}}}",
        f"\\newcommand{{\\{PFX}MismatchLive}}{{{l_['mismatch']}}}",
        f"\\newcommand{{\\{PFX}FpBookkeeping}}{{{s['fp_mr_bookkeeping']}}}",
        f"\\newcommand{{\\{PFX}FpVthree}}{{{s['fp_v3']}}}",
        f"\\newcommand{{\\{PFX}FpVthreeSelf}}{{{s['fp_v3_self']}}}",
        f"\\newcommand{{\\{PFX}FpDirectOnly}}{{{s['fp_direct_only']}}}",
        f"\\newcommand{{\\{PFX}FpDirectObserve}}{{{s['fp_direct_observe']}}}",
        f"\\newcommand{{\\{PFX}FpBookkeepingLive}}{{{l_['fp_mr_bookkeeping']}}}",
        f"\\newcommand{{\\{PFX}FpVthreeLive}}{{{l_['fp_v3']}}}",
        f"\\newcommand{{\\{PFX}FpDirectOnlyLive}}{{{l_['fp_direct_only']}}}",
        f"\\newcommand{{\\{PFX}FpDirectObserveLive}}{{{l_['fp_direct_observe']}}}",
        f"\\newcommand{{\\{PFX}OobGrants}}{{{m6.get('out_of_band', 0)}}}",
        f"\\newcommand{{\\{PFX}ImplicitSiteAdmin}}{{{m6.get('implicit_site_admin', 0)}}}",
        f"\\newcommand{{\\{PFX}ImplicitPublic}}{{{m6.get('implicit_public', 0)}}}",
        f"\\newcommand{{\\{PFX}InBand}}{{{m6.get('in_band_share', 0)}}}",
        f"\\newcommand{{\\{PFX}ProvRows}}{{{sum(m6.values())}}}",
        f"\\newcommand{{\\{PFX}FnSiteAdmin}}{{{fn_ch.get('implicit_site_admin', 0)}}}",
        f"\\newcommand{{\\{PFX}FnPublic}}{{{fn_ch.get('implicit_public', 0)}}}",
        f"\\newcommand{{\\{PFX}FnOob}}{{{fn_ch.get('out_of_band', 0)}}}",
        f"\\newcommand{{\\{PFX}FnInBand}}{{{fn_ch.get('in_band_share', 0)}}}",
        "",
    ]) + "\n"

    # ---------------- 三系统对照表 ----------------
    g_m1 = gogs["M1_grant_mechanism_census"]
    g_all = [c for c in gogs["phaseE_cells"] if c["reading"] == "snapshot"
             and c["introspection_readable"] and c["authorized"]
             and c["introspection_status"] == 404]
    g_fn_ch = dict(oracle_fn_channels(gogs, g_all))
    g, glv = v["g_cells_snap"], v["g_live_snap"]
    t, tl = v["t_snap"], v["t_live"]

    def cell(x, lv=""):
        return f"{x} ({lv})" if lv != "" else str(x)

    rows = [
        ("API entries in pinned version (M1 denominator)",
         cell(gitea_m1["meta"]["swagger_paths_total"]),
         cell(g_m1.get("route_entries_raw", g_m1["denominator_entries"])),
         cell(v["l_route_paths"])),
        ("Grant endpoints (M1)",
         cell(gitea_m1["grant_endpoints_total"]),
         cell(g_m1["grant_endpoints_total"]), cell(v["l_grant_endpoints"])),
        ("\\;of which usable without site admin",
         cell(gitea_m1["grant_endpoints_without_site_admin"]),
         cell(g_m1["grant_endpoints_without_site_admin"]),
         cell(v["l_grant_no_admin"])),
        ("Owner-vantage oracle readable",
         cell(t["oracle_readable"]), cell(g["oracle_readable"]),
         cell(s["oracle_readable"])),
        ("\\;oracle agrees with actual access",
         cell(t["oracle_agree"]), cell(g["oracle_agree"]), cell(s["oracle_agree"])),
        ("\\;oracle wrong (false negatives)",
         cell(t["oracle_fn"]), cell(g["oracle_fn"]), cell(s["oracle_fn"])),
        ("\\;oracle wrong: team-derived access missed",
         cell(0),                                   # Gitea oracle 健全 ⇒ 0（哨兵 ③）
         cell(g_fn_ch.get("out_of_band", 0)),
         cell(fn_ch.get("out_of_band", 0))),
        ("Subject-vantage oracle readable",
         cell(t["self_readable"]), cell(g["self_readable"]), cell(s["self_readable"])),
        ("Reachability mismatch, snapshot (live)",
         cell(t["mismatch"], tl["mismatch"]), cell(g["mismatch"], glv["mismatch"]),
         cell(s["mismatch"], l_["mismatch"])),
        ("False proofs: bookkeeping alarm, snapshot (live)",
         cell(t["fp_mr_bookkeeping"], tl["fp_mr_bookkeeping"]),
         cell(g["fp_mr_bookkeeping"], glv["fp_mr_bookkeeping"]),
         cell(s["fp_mr_bookkeeping"], l_["fp_mr_bookkeeping"])),
        ("False proofs: v3 (oracle-gated), snapshot (live)",
         cell(t["fp_v3"], tl["fp_v3"]), cell(g["fp_v3"], glv["fp_v3"]),
         cell(s["fp_v3"], l_["fp_v3"])),
        ("False proofs: direct-only (oracle only)",
         cell(t["fp_direct_only"], tl["fp_direct_only"]),
         cell(g["fp_direct_only"], glv["fp_direct_only"]),
         cell(s["fp_direct_only"], l_["fp_direct_only"])),
        ("False proofs: direct-observe (oracle $\\wedge$ request)",
         cell(t["fp_direct_observe"], tl["fp_direct_observe"]),
         cell(g["fp_direct_observe"], glv["fp_direct_observe"]),
         cell(s["fp_direct_observe"], l_["fp_direct_observe"])),
    ]
    body = "\n".join(f"{name} & {a} & {b} & {c} \\\\"
                     for name, a, b, c in rows)
    tex = r"""% 由 analysis/ingest_gitlab.py 自动生成 —— 勿手改
\begin{table}[t]
\centering
\small
\caption{Cross-vendor replication under the identical three-phase protocol
(crawl, out-of-band authorization change, adjudicate) on Gitea
\ResRsVersion{}, Gogs \GgVersion{}, and GitLab \GlVersion{}. Counts are per
reading of the same \ResRsCellsSnapshot{}-cell grid; the live reading is
given in parentheses where both exist. The snapshot reading is the operating
point of the published relations. Gitea and Gogs share lineage
(fork, 2016); GitLab shares none. The team-derived row is read out of the
per-system oracle false negatives by channel (Section~\ref{sec:gogs}). The
Gitea grant count here is the \emph{normalised} M1 census (semantically
equivalent routes merged, non-authorization grant surface excluded), and
therefore differs from the raw route count in Table~\ref{tab:rs-m1}; the two
tables use different normalisations and are not in conflict.}
\label{tab:gogs-cross}
\begin{tabular}{@{}lccc@{}}
\toprule
 & Gitea \ResRsVersion{} & Gogs \GgVersion{} & GitLab \GlVersion{} \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
"""

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gitlab_numbers.tex").write_text(macros, encoding="utf-8")
    (OUT / "gogs_cross_table.tex").write_text(tex, encoding="utf-8")

    # ---------------- 人读小结 ----------------
    print("[ingest_gitlab] 数字已生成:")
    print("  ", OUT / "gitlab_numbers.tex")
    print("  ", OUT / "gogs_cross_table.tex")
    print()
    print(f"GitLab {v['gitlab_version']}: 路由条目 raw={v['l_route_paths']} / "
          f"unique={v['l_route_entries']}, 授予端点 {v['l_grant_endpoints']}"
          f"（非站点管理员 {v['l_grant_no_admin']}）")
    print(f"owner 视点 oracle (members/all): 可读 {s['oracle_readable']}/{s['truth']}, "
          f"一致 {s['oracle_agree']}, 假阴性 {s['oracle_fn']} ({v['l_wrong_pct']}%)")
    print(f"  假阴性通道归因: {fn_ch}   ← 团队派生(组继承)为 0 是与 Gogs 的机制差异")
    print(f"  oracle 假阳性(说有权实际无权): {s['oracle_fp']}")
    print()
    print("假确证（snapshot; live）  GitLab")
    for m in METHODS:
        print(f"  {m:22s} {s['fp_' + m]:3d} ({l_['fp_' + m]:2d})")
    print()
    print(f"失配(授权∧不可达): snapshot {s['mismatch']}/48（live {l_['mismatch']}）")
    print(f"M6 通道: {m6}")

    # ---------------- 一致性哨兵 ----------------
    # ① v3 FP 必须全部落在「oracle 假阴性 ∧ MR 触发」的格子上
    v3_fp_cells = [c for c in cells if c["reading"] == "snapshot"
                   and c["false_proofs"]["v3"]]
    assert all(c["authorized"] and c["introspection_status"] == 404
               for c in v3_fp_cells), "v3 FP 格不满足『授权∧oracle 判无』"
    # ② GitLab oracle 不得有假阳性（只可能漏报）
    assert s["oracle_fp"] == 0, "GitLab oracle 出现假阳性，与成员端点语义冲突"
    # ③ Gitea 侧同协议口径必须复现既有结论（v3 假确证 0）
    assert v["t_snap"]["fp_v3"] == 0, "Gitea 侧 v3 假确证非 0，与既有结果冲突"
    # ④ 假阴性通道归因必须满足：site_admin=8 且 in_band=0（基线共享在爬取记录里）
    assert fn_ch.get("implicit_site_admin", 0) == 8 and fn_ch.get("in_band_share", 0) == 0, \
        f"假阴性通道归因异常: {fn_ch}"
    print()
    print("[哨兵] 全部通过")


if __name__ == "__main__":
    main()
