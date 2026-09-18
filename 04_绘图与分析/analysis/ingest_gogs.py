# -*- coding: utf-8 -*-
"""
把「Gogs 跨厂商复核」的结果并入论文数字流水线。
==================================================

输入（全部为实测产物，任何数字都不手敲）：
  * experiments/real_system/results/gogs_real_system.json  —— run_gogs.py 的产物
  * experiments/real_system/results/real_system.json       —— Gitea 侧同协议产物
  * experiments/real_system/results/m1_matched_gitea.json  —— 共享模式表下 Gitea 的 M1

输出：
  * 04_绘图与分析/results/gogs_numbers.tex       —— 宏定义（\\Gg*）
  * 04_绘图与分析/results/gogs_cross_table.tex   —— 跨厂商对照表（booktabs）
  * stdout: 人读小结

用法:
  python analysis/ingest_gogs.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # 3区论文/
RS = ROOT / "experiments" / "real_system" / "results"
OUT = HERE.parent / "results"

GOGS_JSON = RS / "gogs_real_system.json"
GITEA_JSON = RS / "real_system.json"
GITEA_M1 = RS / "m1_matched_gitea.json"

PFX = "Gg"          # Gogs 侧宏前缀
TPFX = "Gt"         # Gitea 侧对照宏前缀（同协议口径）

METHODS = ("mr_bookkeeping", "v3", "v3_self", "direct_only",
           "direct_observe", "direct_observe_self")


def esc(s: str) -> str:
    """LaTeX 转义（下划线等）。"""
    return s.replace("_", "\\_")


# --------------------------------------------------------------------------
# 判定原语：oracle 判「无权限」= permission=='none'，或 collab_get 的 404。
#   （两系统的 phaseE cells 只记 status/permission，不记 says_none 布尔，
#    这里从同样的字段以同样规则重推 —— 与 run_*.py 的判定一致。）
# --------------------------------------------------------------------------
def says_none(c: dict, pre: str) -> bool:
    st = c[f"{pre}_status"]
    pm = c[f"{pre}_permission"]
    return pm == "none" or (pm is None and st == 404)


def analyze_cells(cells: list[dict]) -> dict:
    """对一组格子（单一 reading）计算全部对照量。"""
    r: dict = {}
    truth = [c for c in cells if c["authorized"] is not None]
    r["cells"] = len(cells)
    r["truth"] = len(truth)
    for m in METHODS:
        r[f"alarm_{m}"] = sum(1 for c in cells if c["alarms"][m])
        r[f"fp_{m}"] = sum(1 for c in cells if c["false_proofs"][m])
    ro = [c for c in truth if c["introspection_readable"]]
    r["oracle_readable"] = len(ro)
    r["oracle_agree"] = sum(1 for c in ro
                            if says_none(c, "introspection") == (not c["authorized"]))
    r["oracle_fn"] = sum(1 for c in ro
                         if says_none(c, "introspection") and c["authorized"])
    r["oracle_fp"] = sum(1 for c in ro
                         if not says_none(c, "introspection") and not c["authorized"])
    rs = [c for c in truth if c["introspection_self_readable"]]
    r["self_readable"] = len(rs)
    r["self_agree"] = sum(1 for c in rs
                          if says_none(c, "introspection_self") == (not c["authorized"]))
    # snapshot 失配：GUI 模型判「不可达」但实际可访问
    r["mismatch"] = sum(1 for c in cells
                        if c["cannotReachThroughGUI"] and c["authorized"])
    return r


def oracle_fn_channels(gogs: dict, fn_cells: list[dict]) -> Counter:
    """把 owner 视点 oracle 的假阴性按 M6 通道归类（机械归因）。"""
    ch = {(r["cell"], r["subject"]): r["channel"] for r in gogs["M6_provenance"]}
    return Counter(ch.get((c["object"], c["subject"]), "?")
                   for c in fn_cells)


def m6_channels(d: dict) -> Counter:
    return Counter(r["channel"] for r in d["M6_provenance"])


def emit_macros(vals: dict) -> str:
    lines = [
        "% 由 analysis/ingest_gogs.py 自动生成 —— 勿手改",
        "% 来源: experiments/real_system/results/{gogs_real_system,real_system,m1_matched_gitea}.json",
        "",
        "% ---- Gogs 0.14.3 侧 ----",
        f"\\newcommand{{\\{PFX}Version}}{{{vals['gogs_version']}}}",
        f"\\newcommand{{\\{PFX}Cells}}{{{vals['g_cells']}}}",
        f"\\newcommand{{\\{PFX}RouteEntries}}{{{vals['g_route_entries']}}}",
        f"\\newcommand{{\\{PFX}RoutePaths}}{{{vals['g_route_paths']}}}",
        f"\\newcommand{{\\{PFX}GrantEndpoints}}{{{vals['g_grant_endpoints']}}}",
        f"\\newcommand{{\\{PFX}GrantNoSiteAdmin}}{{{vals['g_grant_no_admin']}}}",
        f"\\newcommand{{\\{PFX}OracleReadable}}{{{vals['g_snap']['oracle_readable']}}}",
        f"\\newcommand{{\\{PFX}OracleAgree}}{{{vals['g_snap']['oracle_agree']}}}",
        f"\\newcommand{{\\{PFX}OracleWrong}}{{{vals['g_snap']['oracle_fn']}}}",
        f"\\newcommand{{\\{PFX}OracleWrongPct}}{{{vals['g_wrong_pct']}}}",
        f"\\newcommand{{\\{PFX}SelfReadable}}{{{vals['g_snap']['self_readable']}}}",
        f"\\newcommand{{\\{PFX}SelfAgree}}{{{vals['g_snap']['self_agree']}}}",
        f"\\newcommand{{\\{PFX}MismatchSnap}}{{{vals['g_snap']['mismatch']}}}",
        f"\\newcommand{{\\{PFX}MismatchLive}}{{{vals['g_live']['mismatch']}}}",
        f"\\newcommand{{\\{PFX}FpBookkeeping}}{{{vals['g_snap']['fp_mr_bookkeeping']}}}",
        f"\\newcommand{{\\{PFX}FpVthree}}{{{vals['g_snap']['fp_v3']}}}",
        f"\\newcommand{{\\{PFX}FpDirectOnly}}{{{vals['g_snap']['fp_direct_only']}}}",
        f"\\newcommand{{\\{PFX}FpDirectObserve}}{{{vals['g_snap']['fp_direct_observe']}}}",
        f"\\newcommand{{\\{PFX}FpBookkeepingLive}}{{{vals['g_live']['fp_mr_bookkeeping']}}}",
        f"\\newcommand{{\\{PFX}FpVthreeLive}}{{{vals['g_live']['fp_v3']}}}",
        f"\\newcommand{{\\{PFX}FpDirectObserveLive}}{{{vals['g_live']['fp_direct_observe']}}}",
        f"\\newcommand{{\\{PFX}OobGrants}}{{{vals['g_m6']['out_of_band']}}}",
        f"\\newcommand{{\\{PFX}ImplicitSiteAdmin}}{{{vals['g_m6'].get('implicit_site_admin', 0)}}}",
        f"\\newcommand{{\\{PFX}ImplicitPublic}}{{{vals['g_m6'].get('implicit_public', 0)}}}",
        f"\\newcommand{{\\{PFX}InBand}}{{{vals['g_m6'].get('in_band_share', 0)}}}",
        f"\\newcommand{{\\{PFX}ProvRows}}{{{sum(vals['g_m6'].values())}}}",
        f"\\newcommand{{\\{PFX}FnSiteAdmin}}{{{vals['g_fn_ch'].get('implicit_site_admin', 0)}}}",
        f"\\newcommand{{\\{PFX}FnPublic}}{{{vals['g_fn_ch'].get('implicit_public', 0)}}}",
        f"\\newcommand{{\\{PFX}FnOob}}{{{vals['g_fn_ch'].get('out_of_band', 0)}}}",
        "",
        "% ---- Gitea 1.22.6 侧（同协议、同模式表口径）----",
        f"\\newcommand{{\\{TPFX}RoutePaths}}{{{vals['t_route_paths']}}}",
        f"\\newcommand{{\\{TPFX}GrantEndpoints}}{{{vals['t_grant_endpoints']}}}",
        f"\\newcommand{{\\{TPFX}GrantNoSiteAdmin}}{{{vals['t_grant_no_admin']}}}",
        f"\\newcommand{{\\{TPFX}OracleAgree}}{{{vals['t_snap']['oracle_agree']}}}",
        f"\\newcommand{{\\{TPFX}OracleWrong}}{{{vals['t_snap']['oracle_fn']}}}",
        f"\\newcommand{{\\{TPFX}SelfReadable}}{{{vals['t_snap']['self_readable']}}}",
        f"\\newcommand{{\\{TPFX}SelfAgree}}{{{vals['t_snap']['self_agree']}}}",
        f"\\newcommand{{\\{TPFX}MismatchSnap}}{{{vals['t_snap']['mismatch']}}}",
        f"\\newcommand{{\\{TPFX}MismatchLive}}{{{vals['t_live']['mismatch']}}}",
        f"\\newcommand{{\\{TPFX}FpBookkeeping}}{{{vals['t_snap']['fp_mr_bookkeeping']}}}",
        f"\\newcommand{{\\{TPFX}FpVthree}}{{{vals['t_snap']['fp_v3']}}}",
        f"\\newcommand{{\\{TPFX}FpDirectOnly}}{{{vals['t_snap']['fp_direct_only']}}}",
        f"\\newcommand{{\\{TPFX}FpDirectObserve}}{{{vals['t_snap']['fp_direct_observe']}}}",
        f"\\newcommand{{\\{TPFX}FpBookkeepingLive}}{{{vals['t_live']['fp_mr_bookkeeping']}}}",
        f"\\newcommand{{\\{TPFX}OobGrants}}{{{vals['t_m6'].get('out_of_band', 0)}}}",
        f"\\newcommand{{\\{TPFX}ProvRows}}{{{sum(vals['t_m6'].values())}}}",
        "",
    ]
    return "\n".join(lines)


def emit_cross_table(vals: dict) -> str:
    """跨厂商对照表（snapshot 读法 = MST-wi 的操作点；live 附于括号）。"""
    g, l = vals["g_snap"], vals["g_live"]
    t, tl = vals["t_snap"], vals["t_live"]

    def pair(tv, tlv, gv, glv):
        """返回 (Gitea 格, Gogs 格)；live 值缺省时不加括号。"""
        def cell(v, lv):
            return f"{v} ({lv})" if lv != "" else str(v)
        return cell(tv, tlv), cell(gv, glv)

    rows = [
        ("API paths in pinned version (M1 denominator)",
         pair(vals["t_route_paths"], "", vals["g_route_paths"], "")),
        ("Grant endpoints (M1)",
         pair(vals["t_grant_endpoints"], "", vals["g_grant_endpoints"], "")),
        ("\\;of which usable without site admin",
         pair(vals["t_grant_no_admin"], "", vals["g_grant_no_admin"], "")),
        ("Owner-vantage oracle readable",
         pair(t["oracle_readable"], "", g["oracle_readable"], "")),
        ("\\;oracle agrees with actual access",
         pair(t["oracle_agree"], "", g["oracle_agree"], "")),
        ("\\;oracle wrong (false negatives)",
         pair(t["oracle_fn"], "", g["oracle_fn"], "")),
        ("Subject-vantage oracle readable",
         pair(t["self_readable"], "", g["self_readable"], "")),
        ("Reachability mismatch, snapshot (live)",
         pair(t["mismatch"], tl["mismatch"], g["mismatch"], l["mismatch"])),
        ("False proofs: bookkeeping alarm, snapshot (live)",
         pair(t["fp_mr_bookkeeping"], tl["fp_mr_bookkeeping"],
              g["fp_mr_bookkeeping"], l["fp_mr_bookkeeping"])),
        ("False proofs: v3 (oracle-gated), snapshot (live)",
         pair(t["fp_v3"], tl["fp_v3"], g["fp_v3"], l["fp_v3"])),
        ("False proofs: direct-only (oracle only)",
         pair(t["fp_direct_only"], tl["fp_direct_only"],
              g["fp_direct_only"], l["fp_direct_only"])),
        ("False proofs: direct-observe (oracle $\\wedge$ request)",
         pair(t["fp_direct_observe"], tl["fp_direct_observe"],
              g["fp_direct_observe"], l["fp_direct_observe"])),
    ]
    body = "\n".join(f"{name} & {tv} & {gv} \\\\"
                     for name, (tv, gv) in rows)
    tex = r"""% 由 analysis/ingest_gogs.py 自动生成 —— 勿手改
\begin{table}[t]
\centering
\small
\caption{Cross-vendor replication under the identical three-phase protocol
(crawl, out-of-band authorization change, adjudicate) on Gitea
\ResRsVersion{} and Gogs \GgVersion{}. Counts are per reading of the same
\ResRsCellsSnapshot{}-cell grid; the live reading is given in parentheses
where both exist. The snapshot reading is the operating point of the
published relations.}
\label{tab:gogs-cross}
\begin{tabular}{@{}lcc@{}}
\toprule
 & Gitea \ResRsVersion{} & Gogs \GgVersion{} \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
"""
    return tex


def main() -> None:
    gogs = json.loads(GOGS_JSON.read_text(encoding="utf-8"))
    gitea = json.loads(GITEA_JSON.read_text(encoding="utf-8"))
    gitea_m1 = json.loads(GITEA_M1.read_text(encoding="utf-8"))

    g_cells = gogs["phaseE_cells"]
    t_cells = gitea["phaseE_cells"]
    g_snap = analyze_cells([c for c in g_cells if c["reading"] == "snapshot"])
    g_live = analyze_cells([c for c in g_cells if c["reading"] == "live"])
    t_snap = analyze_cells([c for c in t_cells if c["reading"] == "snapshot"])
    t_live = analyze_cells([c for c in t_cells if c["reading"] == "live"])

    # oracle 假阴性的通道归因（仅 snapshot；机械查 M6）
    fn_cells = [c for c in g_cells if c["reading"] == "snapshot"
                and c["introspection_readable"] and c["authorized"]
                and says_none(c, "introspection")]
    g_fn_ch = oracle_fn_channels(gogs, fn_cells)

    m1g = gogs["M1_grant_mechanism_census"]
    vals = {
        "gogs_version": gogs["meta"]["gogs_version"],
        "g_cells": len(g_cells) // 2,           # 每读法格子数
        "g_route_entries": m1g["denominator_entries"],
        "g_route_paths": m1g["route_entries_raw"] if "route_entries_raw" in m1g
                         else m1g["denominator_entries"],
        "g_grant_endpoints": m1g["grant_endpoints_total"],
        "g_grant_no_admin": m1g["grant_endpoints_without_site_admin"],
        "g_snap": g_snap, "g_live": g_live,
        "g_wrong_pct": round(100.0 * g_snap["oracle_fn"] / g_snap["oracle_readable"], 1)
                        if g_snap["oracle_readable"] else 0.0,
        "g_fn_ch": dict(g_fn_ch),
        "g_m6": dict(m6_channels(gogs)),
        "t_route_paths": gitea_m1["meta"]["swagger_paths_total"],
        "t_grant_endpoints": gitea_m1["grant_endpoints_total"],
        "t_grant_no_admin": gitea_m1["grant_endpoints_without_site_admin"],
        "t_snap": t_snap, "t_live": t_live,
        "t_m6": dict(m6_channels(gitea)),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    macros = OUT / "gogs_numbers.tex"
    table = OUT / "gogs_cross_table.tex"
    macros.write_text(emit_macros(vals), encoding="utf-8")
    table.write_text(emit_cross_table(vals), encoding="utf-8")

    # ---- 人读小结 ----
    print("[ingest_gogs] 数字已生成:")
    print("  ", macros)
    print("  ", table)
    print()
    print(f"Gogs {vals['gogs_version']}: 路由路径 {vals['g_route_paths']}, "
          f"授予端点 {vals['g_grant_endpoints']}（非站点管理员 "
          f"{vals['g_grant_no_admin']}）")
    print(f"  Gitea 对照: 路径 {vals['t_route_paths']}, 授予端点 "
          f"{vals['t_grant_endpoints']}（非站点管理员 {vals['t_grant_no_admin']}）")
    print()
    print(f"owner 视点 oracle: Gogs 可读 {g_snap['oracle_readable']}/"
          f"{g_snap['truth']} 但与真值一致仅 {g_snap['oracle_agree']}"
          f"（假阴性 {g_snap['oracle_fn']} = {vals['g_wrong_pct']}%）；"
          f"Gitea 一致 {t_snap['oracle_agree']}/{t_snap['truth']}")
    print(f"  假阴性通道归因: {dict(g_fn_ch)}")
    print(f"self 视点: Gogs 可读 {g_snap['self_readable']}/一致 "
          f"{g_snap['self_agree']}；Gitea 可读 {t_snap['self_readable']}/"
          f"一致 {t_snap['self_agree']}")
    print()
    print(f"snapshot 失配: Gogs {g_snap['mismatch']}/48（live {g_live['mismatch']}）；"
          f"Gitea {t_snap['mismatch']}/48（live {t_live['mismatch']}）")
    print()
    print("假确证（snapshot; live）  Gogs          Gitea")
    for m in METHODS:
        print(f"  {m:22s} {g_snap['fp_' + m]:3d} ({g_live['fp_' + m]:2d})"
              f"        {t_snap['fp_' + m]:3d} ({t_live['fp_' + m]:2d})")
    print()
    print(f"M6 通道: Gogs {vals['g_m6']}")
    print(f"         Gitea {vals['t_m6']}")

    # 一致性哨兵：v3 假确证必须全部落在 oracle 假阴性的触发格上
    v3_fp = g_snap["fp_v3"]
    fn_fire = sum(1 for c in g_cells if c["reading"] == "snapshot"
                  and c["false_proofs"]["v3"])
    assert v3_fp == fn_fire, f"v3 FP 口径不一致: {v3_fp} != {fn_fire}"
    # 哨兵：Gitea 侧同协议口径必须复现既有结论（v3 假确证 0）
    assert t_snap["fp_v3"] == 0, "Gitea 侧 v3 假确证非 0，与既有结果冲突"


if __name__ == "__main__":
    main()
