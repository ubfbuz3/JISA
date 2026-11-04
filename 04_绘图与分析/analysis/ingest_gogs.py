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


def channel_split(gogs: dict, cells: list[dict], pred) -> Counter:
    """把满足 ``pred`` 的格子按 M6 记录的通道归类（机械查表，不猜）。"""
    ch = {(r["cell"], r["subject"]): r["channel"] for r in gogs["M6_provenance"]}
    return Counter(ch.get((c["object"], c["subject"]), "?")
                   for c in cells if pred(c))


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
        f"\\newcommand{{\\{PFX}LiveMismatchPublic}}{{{vals['g_live_mm'].get('implicit_public', 0)}}}",
        f"\\newcommand{{\\{PFX}LiveMismatchSiteAdmin}}{{{vals['g_live_mm'].get('implicit_site_admin', 0)}}}",
        f"\\newcommand{{\\{PFX}LiveMismatchOther}}{{{vals['g_live_mm_other']}}}",
        f"\\newcommand{{\\{PFX}LiveFpPublic}}{{{vals['g_live_fp']['implicit_public']}}}",
        f"\\newcommand{{\\{PFX}LiveFpOther}}{{{vals['g_live_fp_other']}}}",
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

    # live 读法下残差与假确证的通道归因（供正文/related work 直接引宏）
    live_cells = [c for c in g_cells if c["reading"] == "live"]
    g_live_mm = channel_split(gogs, live_cells,
                              lambda c: c["cannotReachThroughGUI"] and c["authorized"])
    g_live_fp = channel_split(gogs, live_cells, lambda c: c["false_proofs"]["v3"])

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
        "g_live_mm": dict(g_live_mm),
        "g_live_mm_other": sum(v for k, v in g_live_mm.items()
                               if k not in ("implicit_public", "implicit_site_admin")),
        "g_live_fp": dict(g_live_fp),
        "g_live_fp_other": sum(v for k, v in g_live_fp.items()
                               if k != "implicit_public"),
        "g_m6": dict(m6_channels(gogs)),
        "t_route_paths": gitea_m1["meta"]["swagger_paths_total"],
        "t_grant_endpoints": gitea_m1["grant_endpoints_total"],
        "t_grant_no_admin": gitea_m1["grant_endpoints_without_site_admin"],
        "t_snap": t_snap, "t_live": t_live,
        "t_m6": dict(m6_channels(gitea)),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    macros = OUT / "gogs_numbers.tex"
    macros.write_text(emit_macros(vals), encoding="utf-8")

    # 注意：`gogs_cross_table.tex`（Table 16）**只由 ingest_gitlab.py 产出**——它
    # 把 gitea/gogs/gitlab 三列合并。本脚本早期版本也写同名文件（两列版），一旦在
    # ingest_gitlab.py 之后运行，就会把 GitLab 列静默冲掉（2026-11-04 实际发生）。
    # 因此这里只核验、不写：文件存在却缺 GitLab 列时直接报错，而不是悄悄覆盖。
    cross = OUT / "gogs_cross_table.tex"
    if cross.is_file():
        body = cross.read_text(encoding="utf-8")
        assert "GitLab" in body, (
            "gogs_cross_table.tex 缺少 GitLab 列（两列中间版残留）——"
            "请按 build.sh 的顺序，在 ingest_gogs.py 之后运行 ingest_gitlab.py")

    # ---- 人读小结 ----
    print("[ingest_gogs] 数字已生成:")
    print("  ", macros)
    print(f"   （Table 16 三系统对照表由 ingest_gitlab.py 生成：{cross.name}）")
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
    print(f"live 残差通道: {dict(g_live_mm)}；live v3 假确证通道: {dict(g_live_fp)}")

    # ---- 一致性哨兵：live 残差/假确证的通道归因必须闭合 ----
    # 正文与 Section IX 按通道点名"残留只在公开可见性与站点管理员两处"，
    # 一旦归因不闭合（出现 '?' 或 third channel），那句话就不成立。
    assert sum(g_live_mm.values()) == g_live["mismatch"], \
        f"live 残差通道求和 {sum(g_live_mm.values())} != {g_live['mismatch']}"
    assert "?" not in g_live_mm and "?" not in g_live_fp, \
        f"有格子未能归入 M6 通道: {dict(g_live_mm)} / {dict(g_live_fp)}"
    assert vals["g_live_mm_other"] == 0, \
        f"live 残差出现在公开/站点管理员之外的通道: {dict(g_live_mm)}"
    assert vals["g_live_fp_other"] == 0 and "implicit_public" in g_live_fp, \
        f"live 假确证不只在公开可见性通道: {dict(g_live_fp)}"
    assert sum(g_live_fp.values()) == g_live["fp_v3"], \
        f"live v3 假确证通道求和 {sum(g_live_fp.values())} != {g_live['fp_v3']}"

    # 一致性哨兵：v3 假确证必须全部落在 oracle 假阴性的触发格上
    v3_fp = g_snap["fp_v3"]
    fn_fire = sum(1 for c in g_cells if c["reading"] == "snapshot"
                  and c["false_proofs"]["v3"])
    assert v3_fp == fn_fire, f"v3 FP 口径不一致: {v3_fp} != {fn_fire}"
    # 哨兵：Gitea 侧同协议口径必须复现既有结论（v3 假确证 0）
    assert t_snap["fp_v3"] == 0, "Gitea 侧 v3 假确证非 0，与既有结果冲突"


if __name__ == "__main__":
    main()
