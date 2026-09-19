"""
统一指标计算 · 全部分析数字的唯一来源
========================================
原则（项目硬约束）:
  1. 正文**禁止手敲任何数字**。全部数字由本脚本写入 results/numbers.tex 宏，正文只引用宏。
  2. 本脚本**重算**既有结论，并与已落盘的 JSON 交叉校验（assert）。不一致即报错，
     不允许"正文一个数、数据另一个数"。
  3. 所有比例同时给出 Wilson 95% 区间；方法间差异给出 Newcombe 混合评分区间。
  4. 口径分歧必须并列报出，不得只报对己方有利的一支。

数据来源（全部为已落盘的真实运行记录，无任何人工填入）:
  experiments/results/raw_matrix.jsonl              合成受控矩阵（576 条）
  experiments/results/ablation_direct.json          direct-only 消融（含 probe_cache）
  experiments/results/ablation_direct_observe.json  direct-observe 对照消融
  experiments/results/alt_matrix.jsonl              第二实现一致性
  experiments/real_system/results/real_system.json  Gitea 1.22.6 真实系统对照

用法: python compute_all.py
输出: results/metrics.json, results/numbers.tex
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
EXP = PROJ / "experiments"
RES = EXP / "results"
REAL = EXP / "real_system" / "results"
OUT = HERE.parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REP_PV, REP_GM = "raw", "aware"          # "代表切片" = 最忠实 MST-wi 原始行为的设定
E3_SC = ("S3", "S4", "S5", "S6", "S7")
SCEN_ORDER = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
Z = 1.959963985                           # 95%

PROBLEMS: list[str] = []                  # 收集校验失败


# ---------------------------------------------------------------- 统计工具

def wilson(k: int, n: int, z: float = Z):
    """Wilson score interval（无需 scipy）。返回 (p, lo, hi)，n=0 时返回 (None,None,None)。"""
    if n == 0:
        return None, None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(p, 4), round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)


def rd_ci(k1: int, n1: int, k2: int, n2: int, z: float = Z):
    """Newcombe 混合评分法：两独立比例之差的 95% 区间。"""
    p1, l1, u1 = wilson(k1, n1, z)
    p2, l2, u2 = wilson(k2, n2, z)
    if p1 is None or p2 is None:
        return None, None, None
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return round(d, 4), round(lo, 4), round(hi, 4)


def prf(t: dict):
    tp, fp, fn = t.get("TP", 0), t.get("FP", 0), t.get("FN", 0)
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f1 = (2 * p * r / (p + r)) if (p and r) else None
    return p, r, f1


def ratio(k: int, n: int):
    return round(k / n, 4) if n else None


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def check(name: str, got, want, tol=1e-9):
    ok = (got == want) if isinstance(want, (int, str, bool, type(None))) else abs(got - want) <= tol
    if not ok:
        PROBLEMS.append(f"[校验失败] {name}: 重算={got} 落盘={want}")
    return ok


def pct(x):
    return None if x is None else round(100 * x, 2)


# ---------------------------------------------------------------- 主流程

def main():
    allrecs = load_jsonl(RES / "raw_matrix.jsonl")
    errs = [r for r in allrecs if "error" in r]
    recs = [r for r in allrecs if "error" not in r]
    rep = [r for r in recs if r["precond_variant"] == REP_PV and r["gui_mode"] == REP_GM]
    labels = sorted({r["config"]["label"] for r in recs})

    M: dict = {}
    M["meta"] = {
        "synthetic_records_total": len(allrecs),
        "synthetic_records_ok": len(recs),
        "synthetic_errors": len(errs),
        "configs": labels,
        "scenarios": SCEN_ORDER,
        "representative_slice": {"precond_variant": REP_PV, "gui_mode": REP_GM, "n": len(rep)},
        "truth_domain": sorted({r["truth"]["truth"] for r in recs}),
        "adjudicators": sorted(recs[0]["verdicts"].keys()),
    }

    # ============ 设计结构：有效独立单元（统计诚实性的前置量） ==============
    #  576 条**不是** 576 次独立重复，而是固定设计矩阵的确定性枚举：
    #    (情景 × 配置) 设计格 × MR × precond_variant × gui_mode。
    #  其中 precond_variant / gui_mode 是被刻意拨动的**确定性开关**（例外阶梯、
    #  GUI 模型读法），不是随机重复。故任何 Wilson/Newcombe 区间在记录级都
    #  **乐观**（高估精度），必须显式声明，并把有效 n 一并报出。
    import collections as _c
    cell_key = lambda r: (r["scenario"], json.dumps(r["config"], sort_keys=True))
    cells = {cell_key(r) for r in recs}
    mrs = {r["mr"] for r in recs}
    pvs = sorted({r["precond_variant"] for r in recs})
    gms = sorted({r["gui_mode"] for r in recs})
    per_cell = _c.Counter(cell_key(r) for r in recs)
    # 每格适用的 MR 数：绝大多数格 MR-002 与 MR-004 都适用（2），
    # S5 的全部格仅 MR-002 适用（1）——这是 576 公式中乘子不一致的根因。
    cell_mrs = _c.defaultdict(set)
    for r in recs:
        cell_mrs[cell_key(r)].add(r["mr"])
    n_two = sum(1 for v in cell_mrs.values() if len(v) == 2)
    n_one = sum(1 for v in cell_mrs.values() if len(v) == 1)
    M["design_structure"] = {
        "records": len(recs),
        "design_cells": len(cells),
        "cells_with_two_mrs": n_two,
        "cells_with_one_mr": n_one,
        "cells_with_one_mr_scenario": sorted({k[0] for k, v in cell_mrs.items() if len(v) == 1}),
        "mrs": sorted(mrs),
        "n_mrs": len(mrs),
        "precond_variants": pvs,
        "gui_modes": gms,
        "records_per_cell": sorted(set(per_cell.values())),
        "min_records_per_cell": min(per_cell.values()),
        "max_records_per_cell": max(per_cell.values()),
        "scenarios": SCEN_ORDER,
        "n_scenarios": len(SCEN_ORDER),
        "cell_expansion": len(pvs) * len(gms),
        "independence_verdict": (
            "记录之间**不独立**：同一设计格内的记录共享对象图、setup 与真值，"
            "仅由 precond_variant 与 gui_mode 两个确定性开关区分。"),
        "interval_warning": (
            "★ 本工作报出的 Wilson / Newcombe 区间是**约定性**的：它们假设记录为"
            "独立伯努利抽样，而本设计是固定矩阵的确定性枚举，故区间**系统性偏窄**。"
            "正因如此：(1) 每条计数都要同时给出其**设计格数**而非仅记录数；"
            "(2) 区间只用于说明**量级**与**不确定方向**，不得用于跨方法显著性主张；"
            "(3) 唯一的例外是 Block 9 的 Newcombe 差值区间——它同样偏窄，"
            "所以其「不显著」结论是**稳健**的（偏窄只会更容易判显著）。"),
        "effective_replication_statement": (
            "有效重复层级：设计格 {} 个 / MR {} 条 / 情景 {} 个 / 真实系统 1 个；"
            "对「MST-wi 的 MR 总体」的外推上界即 MR 条数。").format(
                len(cells), len(mrs), len(SCEN_ORDER)),
    }

    # ================= Block 0 · 2x2（通道可见性 × 应用授权正确性） =========
    grid = []
    for lab, vis, auth in (("V-E3-vuln0-unlisted", "unlisted", "correct"),
                           ("V-E3-vuln0-listed", "listed", "correct"),
                           ("V-E3-vuln1-unlisted", "unlisted", "violating"),
                           ("V-E3-vuln1-listed", "listed", "violating")):
        sel = [r for r in rep if r["config"]["label"] == lab and r["scenario"] in E3_SC]
        c = Counter(r["confusion"] for r in sel)
        n = len(sel)
        fp_r = wilson(c["FP"], n)
        grid.append({"config": lab, "channel_visibility": vis, "app_authorization": auth,
                     "cases": n, "FP": c["FP"], "FN": c["FN"], "TP": c["TP"], "TN": c["TN"],
                     "FP_rate": fp_r[0], "FP_ci": [fp_r[1], fp_r[2]],
                     "FN_rate": ratio(c["FN"], n)})
    # 诚实修正：原摘要称"没有一格是零错误"，复核数据后不成立——listed×correct 格为零错误。
    # 但该格之所以零错误，是因为 MR 在该格**完全不触发**（无告警 ⇒ 无 FP；vuln0 ⇒ 无真 BOLA ⇒ 无 FN）。
    # 同一机制在配对的 listed×violating 格产生 FN。故正确表述是：
    #   零错误格 = 因 MR 静默而平凡地零错误，且该静默在配对格转为漏报。
    clean = [g for g in grid if g["FP"] + g["FN"] == 0]
    M["block0_2x2"] = {
        "grid": grid,
        "scope": "仅含存在对象级共享的场景 S3–S7；代表切片 raw+GUI-aware",
        "cells_with_any_error": sum(1 for g in grid if g["FP"] + g["FN"] > 0),
        "cells_total": len(grid),
        "clean_cells": [g["config"] for g in clean],
        "clean_cells_are_trivially_clean": True,
        "note": ("复核后修正：原摘要『四个格子无一零错误』**不成立**——listed×correct 格 FP=FN=0。"
                 "但该格零错误是**平凡**的：MR 在该格完全不触发（无告警 ⇒ 无 FP；vuln=0 ⇒ 无真 BOLA ⇒ 无 FN）。"
                 "同一机制在配对的 listed×violating 格转为漏报（见该格 FN）。"
                 "真正可支撑的结论是：**避免误报与保住检测力由同一个开关控制，无法同时达成**"
                 "（unlisted 格 FP>0 而 FN=0；listed 格 FP=0 而 FN>0）。"),
    }

    # ================= Block 2 · 主锚点（FP_E3 / 基线 / 对照） ==============
    def frac(lab, sc, pred=None):
        sel = [r for r in rep if r["config"]["label"] == lab and r["scenario"] == sc]
        if pred:
            sel = [r for r in sel if pred(r)]
        return sum(1 for r in sel if r["mr_result"]["triggered"]), len(sel)

    f_n, f_d = frac("V-E3-vuln0-unlisted", "S3")
    b_n, b_d = frac("V-noE3-vuln0", "S1")
    l_n, l_d = frac("V-E3-vuln0-listed", "S3")
    fp_e3 = wilson(f_n, f_d)
    M["block2"] = {
        "FP_E3": {"hits": f_n, "total": f_d, "rate": fp_e3[0], "ci": [fp_e3[1], fp_e3[2]],
                  "config": "V-E3-vuln0-unlisted", "scenario": "S3",
                  "meaning": "存在 E3 例外（合法共享）且应用授权正确 ⇒ MR 触发即误报"},
        "baseline_FP": {"hits": b_n, "total": b_d, "rate": ratio(b_n, b_d),
                        "config": "V-noE3-vuln0", "scenario": "S1"},
        "listed_control_FP": {"hits": l_n, "total": l_d, "rate": ratio(l_n, l_d),
                              "config": "V-E3-vuln0-listed", "scenario": "S3"},
        "recall_vuln1_unlisted": {
            sc: dict(zip(("hits", "total", "rate"),
                         (*(lambda t: (t[0], t[1], ratio(t[0], t[1])))(frac("V-E3-vuln1-unlisted", sc)),)))
            for sc in ("S2", "S4", "S5")},
    }
    check("FP_E3 rate", M["block2"]["FP_E3"]["rate"], 1.0)

    # ================= Block 3 · 例外谓词层级消融 ==========================
    abl3 = {}
    for pv in ("raw", "e1", "e1e2"):
        sel = [r for r in recs if r["precond_variant"] == pv and r["gui_mode"] == REP_GM
               and r["config"]["label"] == "V-E3-vuln0-unlisted" and r["scenario"] == "S3"]
        hit = sum(1 for r in sel if r["mr_result"]["triggered"])
        abl3[pv] = {"hits": hit, "total": len(sel), "rate": ratio(hit, len(sel))}
    M["block3_exception_ladder"] = {
        **abl3,
        "conclusion": "E1/E2 例外谓词对 FP_E3 无改善（1.00 → 1.00 → 1.00）——构造性结论",
    }

    # ================= Block 4 · 裁决质量（收益/代价） ======================
    def grades(adj: str, cfg: str | None = None):
        agg = defaultdict(int)
        for r in rep:
            if cfg and r["config"]["label"] != cfg:
                continue
            for k, v in r["grades"][adj].items():
                agg[k] += int(bool(v))
        return dict(agg)

    def with_rates(a: dict):
        d_ra = a.get("raw_false_alarm", 0)
        d_trig = a.get("detection_kept", 0) + a.get("costly_downgrade", 0)
        d_bola = d_trig + a.get("missed", 0)
        return {**a,
                "recovery_rate": ratio(a.get("recovered", 0), d_ra),
                "detection_keep_rate": ratio(a.get("detection_kept", 0), d_trig),
                "cost_rate": ratio(a.get("costly_downgrade", 0), d_trig),
                "fn_rate_among_bola": ratio(a.get("missed", 0), d_bola)}

    M["block4_verdict_quality_all"] = {a: with_rates(grades(a))
                                       for a in ("v1", "v2", "v3", "degrade_all")}

    # ================= 目录普查（MST-wi 公开制品，实例无关） =================
    import csv
    cen_p = PROJ / "refine-logs" / "catalog_census.csv"
    if cen_p.exists():
        with cen_p.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        def truthy(v):
            return str(v).strip().lower() in ("true", "1", "yes")
        authz_name = sum(1 for r in rows if truthy(r["name_contains_OTG_AUTHZ"]))
        cc = sum(1 for r in rows if truthy(r["calls_changeCredentials"]))
        union = [r for r in rows if truthy(r["name_contains_OTG_AUTHZ"])
                 or truthy(r["calls_changeCredentials"])]
        gui_only = sum(1 for r in rows if truthy(r["gates_on_GUI_derived(ucrc|crtg|isSupervisorOf)"]))
        any_pred = sum(1 for r in rows if truthy(r["gates_on_any_identity_or_gui_predicate"]))
        M["catalog_census"] = {
            "mr_total": len(rows),
            "name_contains_OTG_AUTHZ": authz_name,
            "calls_changeCredentials": cc,
            "union": len(union),
            "union_rate": ratio(len(union), len(rows)),
            "gates_on_GUI_derived": gui_only,
            "gates_on_GUI_derived_rate": ratio(gui_only, len(rows)),
            "gates_on_any_identity_or_gui": any_pred,
            "of_union_gated_on_GUI_or_identity": sum(
                1 for r in union
                if truthy(r["gates_on_GUI_derived(ucrc|crtg|isSupervisorOf)"])
                or truthy(r["calls_isAdmin"]) or truthy(r["calls_isUserIdParameter"])),
            "unchanged_actor": len(rows) - len(union),
            "unchanged_actor_rate": ratio(len(rows) - len(union), len(rows)),
            "source": str(cen_p.relative_to(PROJ)),
            "caveat": ("口径分歧必须并列报出：名称含 OTG_AUTHZ / 调用 changeCredentials / "
                       "两者并集给出不同的分母；并集是授权相关性的**上界**。"),
        }
        txt = PROJ / "01_文献调研" / "mstwi_artifact" / "mstwi_paper_text.txt"
        if txt.exists():
            s = txt.read_text(encoding="utf-8", errors="replace")
            vocab = {k: s.count(k) for k in
                     ("isOwner", "canAccess", "ownerOf", "hasPermission", "ownership",
                      "shares_of", "isSupervisorOf", "cannotReachThroughGUI",
                      "userCanRetrieveContent", "isAdmin")}
            M["catalog_census"]["dsl_vocabulary_counts"] = vocab
            M["catalog_census"]["authorization_state_predicate_hits"] = sum(
                vocab[k] for k in ("isOwner", "canAccess", "ownerOf", "hasPermission",
                                   "ownership", "shares_of"))

    # ================= 制品清单（原生引擎源码，2026-09-18 克隆） ============
    # 目的：把"门控谓词锚在采集期快照"的论证从**论文文字定义**升级为**实现源码**。
    # 全部数字与事实由本块**扫描源码得出**，不手敲；源码不存在时整块跳过（正文宏随之缺失，
    # 由 check_macros.py 报错，而不是静默降级）。
    import re as _re
    MST_SRC = Path(r"C:/Users/Administrator/WorkBuddy/mst_engine/MST")
    if MST_SRC.exists():
        mr_dir = MST_SRC / "src-mrs-icst2020"
        cls_re = _re.compile(r"class\s+(\w+)\s+extends\s+MR\b")
        mr_cls = {}
        for f in sorted(mr_dir.rglob("*.java")):
            t = f.read_text(encoding="utf-8", errors="replace")
            for m in cls_re.finditer(t):
                mr_cls[m.group(1)] = t
        owasp_cls = sorted(k for k in mr_cls if k.startswith("OTG_"))
        authz_cls = [k for k in owasp_cls if k.startswith("OTG_AUTHZ")]
        fam = Counter(k.split("_")[1] for k in owasp_cls)
        g_crtg = [k for k in authz_cls if "cannotReachThroughGUI" in mr_cls[k]]
        g_ucrc = [k for k in authz_cls if "userCanRetrieveContent" in mr_cls[k]]
        gate_union = sorted(set(g_crtg) | set(g_ucrc))
        gate_none = sorted(set(authz_cls) - set(gate_union))

        wp = (MST_SRC / "src/smrl/mr/crawljax/WebProcessor.java").read_text(
            encoding="utf-8", errors="replace")
        wop = (MST_SRC / "src/smrl/mr/crawljax/WebOperationsProvider.java").read_text(
            encoding="utf-8", errors="replace")
        sc = (MST_SRC / "src/smrl/mr/language/SystemConfig.java").read_text(
            encoding="utf-8", errors="replace")

        # F1 缓存从不失效：字段有声明与写入，但全仓无 clear()
        f1 = ("urlsAccessedByUsers" in wp) and ("urlsAccessedByUsers.clear" not in wp)
        # F2 缺数据默认判"不可达"（fail-open to alarm）
        f2_empty = bool(_re.search(r"if\s*\(\s*inputList\.isEmpty\(\)\s*\)", wp))
        f2_null = bool(_re.search(r"if\s*\(\s*user\s*==\s*null\s*\|\|\s*url\s*==\s*null", wp))
        # F4 输出仓库来自文件系统目录且只装载一次
        f4_fs = "getOutputStore()" in wop
        f4_once = "already loaded" in wop
        # F5 角色关系来自静态 JSON 配置
        f5_conf = ('"supervisedUser"' in sc) or ("supervisedUser" in sc and "jsonObject" in sc)
        f5_self = bool(_re.search(r"equals\(\s*username2\.trim\(\)\s*\)", sc))

        # F6 上游 pom 是否把 MR 目录配为源码根。
        # 必须核对 git 里的 pristine 版本——工作区 pom 已被本地修补，直接读会得到假阳性。
        f6 = None
        try:
            import subprocess
            _r = subprocess.run(["git", "-C", str(MST_SRC), "show", "HEAD:pom.xml"],
                                capture_output=True, text=True, timeout=60)
            if _r.returncode == 0:
                f6 = "src-mrs-icst2020" in _r.stdout
        except Exception:
            f6 = None

        M["artifact_inventory"] = {
            "source_root": str(MST_SRC),
            "mr_dir": str(mr_dir.relative_to(MST_SRC)).replace("\\", "/"),
            "owasp_mr_total": len(owasp_cls),
            "authz_mr_total": len(authz_cls),
            "authz_mrs": authz_cls,
            "family_counts": dict(fam),
            "gates_on_cannotReachThroughGUI": len(g_crtg),
            "gates_on_cannotReachThroughGUI_names": g_crtg,
            "gates_on_userCanRetrieveContent": len(g_ucrc),
            "gates_on_userCanRetrieveContent_names": g_ucrc,
            "authz_gated_on_either": len(gate_union),
            "authz_gated_on_neither": len(gate_none),
            "authz_gated_on_neither_names": gate_none,
            "facts": {
                "F1_url_set_memoized_never_invalidated": f1,
                "F2_failopen_when_crawl_input_empty": f2_empty,
                "F2_failopen_when_user_or_url_null": f2_null,
                "F4_output_store_read_from_fs": f4_fs,
                "F4_output_store_loaded_once": f4_once,
                "F5_supervisor_from_static_config": f5_conf,
                "F5_supervisor_true_when_same_account": f5_self,
                # 注：此项为 True 表示**上游**pom 已声明 MR 源码根；False 表示未声明
                #（后者即实测情形：默认 jar 里没有任何 OTG_* 类）。
                **({"F6_upstream_pom_declares_mr_source_root": bool(f6)}
                   if f6 is not None else {}),
            },
            "caveat": ("源码级证据已有运行级补充：本工作在自建 harness（无浏览器，仅替换 HTTP 观测通道）"
                       "下执行了上游 OTG_AUTHZ_* 关系本身；产物与消化脚本见 "
                       "experiments/native_engine/results/native_engine.json 与 "
                       "analysis/ingest_native_engine.py。上游 Java 源码零改动"
                       "（git status 仅 pom.xml，且其改动为一行 <source> 声明）。"
                       "「同一 URL 对拥有者与受让者响应逐字节相同」这条断言另有摘要级凭据："
                       "experiments/native_engine/verify_channel_bytes.py 产出 "
                       "results/channel_bytes.json（sha256 逐格比对，含无权者 404 对照）。"),
        }

    M["block4_verdict_quality_fp_config"] = {
        a: with_rates(grades(a, "V-E3-vuln0-unlisted"))
        for a in ("v1", "v2", "v3", "degrade_all")}

    # ================= Block 6 · 可观测性边界（框架 vs 带外） ==============
    def obs_stats(scen: str):
        sel = [r for r in rep if r["scenario"] == scen and r["config"]["mode"] == "e3"]
        d = {"scenario": scen,
             "share_origin": sorted({r["setup"].get("share_origin", "?") for r in sel}),
             "n": len(sel),
             "triggered": sum(1 for r in sel if r["mr_result"]["triggered"]),
             "bola_total": sum(1 for r in sel if r["truth"]["truth"] == "bola"),
             "framework_log_records": sum(len(r.get("share_log") or []) for r in sel)}
        for adj in ("v1", "v2", "v3"):
            d[f"{adj}_false_alarm_n"] = sum(1 for r in sel if r["grades"][adj]["raw_false_alarm"])
            d[f"{adj}_false_proof_n"] = sum(
                1 for r in sel if r["grades"][adj]["raw_false_alarm"]
                and r["verdicts"][adj]["verdict"] == "violation-proven")
            d[f"{adj}_recovered_n"] = sum(1 for r in sel if r["grades"][adj]["recovered"])
            d[f"{adj}_proven_on_bola_n"] = sum(
                1 for r in sel if r["truth"]["truth"] == "bola"
                and r["verdicts"][adj]["verdict"] == "violation-proven")
        d["v3_abstain_unavailable_n"] = sum(
            1 for r in sel if r["verdicts"]["v3"]["witness"]
            and r["verdicts"]["v3"]["witness"].get("sut_introspection") == "unavailable")
        fa = d["v1_false_alarm_n"]
        # v1 与 v2 在 S3/S6/S7 上同源（同一份框架账本），故并列
        d["v1v2_false_proof_rate"] = ratio(d["v2_false_proof_n"], fa)
        d["v3_false_proof_rate"] = ratio(d["v3_false_proof_n"], fa)
        d["v3_recovery_rate"] = ratio(d["v3_recovered_n"], fa)
        return d

    M["block6_observability"] = {
        "framework_share_legit": obs_stats("S3"),
        "out_of_band_share_legit": obs_stats("S6"),
        "out_of_band_share_bola": obs_stats("S7"),
    }

    # ================= Block 7 · S3/S5 二选一 ==============================
    cross = []
    for lab in ("V-E3-vuln1-unlisted", "V-E3-vuln1-listed"):
        s3 = [r for r in rep if r["config"]["label"] == lab and r["scenario"] == "S3"]
        s5 = [r for r in rep if r["config"]["label"] == lab and r["scenario"] == "S5"]
        s3_ok = bool(s3) and all(not r["mr_result"]["triggered"] for r in s3)
        s5_ok = bool(s5) and all(r["mr_result"]["triggered"] for r in s5)
        cross.append({"config": lab,
                      "S3_correct_no_trigger": s3_ok,
                      "S3_detail": f"{sum(1 for r in s3 if not r['mr_result']['triggered'])}/{len(s3)}",
                      "S5_correct_trigger": s5_ok,
                      "S5_detail": f"{sum(1 for r in s5 if r['mr_result']['triggered'])}/{len(s5)}",
                      "both_correct": bool(s3_ok and s5_ok)})
    M["block7_s3_s5_dilemma"] = {"rows": cross,
                                 "any_config_correct": any(c["both_correct"] for c in cross)}
    check("Block7 any_config_correct", M["block7_s3_s5_dilemma"]["any_config_correct"], False)

    # ================= Block 8 · v3 的可容许性边界 =========================
    def v3_by_intro(intro: str):
        sel = [r for r in rep if r["config"]["mode"] == "e3"
               and r["config"].get("introspection", "on") == intro
               and r["scenario"] in E3_SC]
        fa = sum(1 for r in sel if r["grades"]["v1"]["raw_false_alarm"])
        bola_trig = sum(1 for r in sel
                        if r["truth"]["truth"] == "bola" and r["mr_result"]["triggered"])
        d = {"introspection": intro, "n": len(sel), "false_alarm_n": fa, "bola_trig_n": bola_trig}
        for adj in ("v2", "v3"):
            d[f"{adj}_recovered_n"] = sum(1 for r in sel if r["grades"][adj]["recovered"])
            d[f"{adj}_false_proof_n"] = sum(
                1 for r in sel if r["grades"][adj]["raw_false_alarm"]
                and r["verdicts"][adj]["verdict"] == "violation-proven")
            d[f"{adj}_proven_on_bola_n"] = sum(
                1 for r in sel if r["truth"]["truth"] == "bola"
                and r["verdicts"][adj]["verdict"] == "violation-proven")
        d["v3_abstain_unavailable_n"] = sum(
            1 for r in sel if r["verdicts"]["v3"]["witness"]
            and r["verdicts"]["v3"]["witness"].get("sut_introspection") == "unavailable")
        d["v3_recovery_rate"] = ratio(d["v3_recovered_n"], fa)
        d["v3_false_proof_rate"] = ratio(d["v3_false_proof_n"], fa)
        d["v3_detection_keep_rate"] = ratio(d["v3_proven_on_bola_n"], bola_trig)
        d["v2_false_proof_rate"] = ratio(d["v2_false_proof_n"], fa)
        return d

    M["block8_introspection_boundary"] = {"on": v3_by_intro("on"), "off": v3_by_intro("off")}

    # ================= Block 9 · direct_observe 支配性（决定性消融） =======
    probe = json.loads((RES / "ablation_direct.json").read_text(encoding="utf-8"))["probe_cache"]

    def confused(truth: str, alarm: bool) -> str:
        if truth == "bola":
            return "TP" if alarm else "FN"
        return "FP" if alarm else "TN"

    ADJ = ("v1", "v2", "v3", "degrade_all", "direct_only", "direct_observe")
    tally = {a: defaultdict(int) for a in ADJ}
    per_scen = {a: defaultdict(lambda: defaultdict(int)) for a in ADJ}
    agree = defaultdict(int)
    for r in recs:
        truth = r["truth"]["truth"]
        sc = r["scenario"]
        st = probe.get(f'{r["config"]["label"]}|{sc}', {}).get(r["action"]["op"], "unavailable")
        obs200 = bool(r["truth"]["app_allowed"])
        alarms = {a: r["verdicts"][a]["verdict"] == "violation-proven" for a in ("v1", "v2", "v3", "degrade_all")}
        alarms["direct_only"] = (st == "none")
        alarms["direct_observe"] = (st == "none") and obs200
        if st == "unavailable":
            alarms["direct_only"] = False
            alarms["direct_observe"] = False
        for a in ADJ:
            cell = confused(truth, alarms[a])
            tally[a][cell] += 1
            per_scen[a][sc][cell] += 1
        agree["same"] += int(alarms["v3"] == alarms["direct_observe"])
        agree["diff"] += int(alarms["v3"] != alarms["direct_observe"])

    b9 = {}
    for a in ADJ:
        t = dict(tally[a])
        p, rr, f1 = prf(t)
        n_bola = t.get("TP", 0) + t.get("FN", 0)
        n_norm = t.get("FP", 0) + t.get("TN", 0)
        prec_ci = wilson(t.get("TP", 0), t.get("TP", 0) + t.get("FP", 0))
        b9[a] = {**{k: t.get(k, 0) for k in ("TP", "FP", "FN", "TN")},
                 "precision": p, "recall": rr, "f1": f1,
                 "precision_ci": [prec_ci[1], prec_ci[2]],
                 "recall_ci": list(wilson(t.get("TP", 0), n_bola)[1:]),
                 "n_bola": n_bola, "n_normal": n_norm}
    # 交叉校验：与落盘 JSON 一致
    stored = json.loads((RES / "ablation_direct_observe.json").read_text(encoding="utf-8"))["tally"]
    for a in ("v3", "direct_only", "direct_observe"):
        for k in ("TP", "FP", "FN", "TN"):
            check(f"Block9 {a}.{k}", b9[a][k], stored[a].get(k, 0))
    rd = rd_ci(b9["direct_observe"]["TP"], b9["direct_observe"]["n_bola"],
               b9["v3"]["TP"], b9["v3"]["n_bola"])
    # 不一致分解：v3 与 direct_observe 裁决不同的记录落在哪里
    diff_records = []
    for r in recs:
        st = probe.get(f'{r["config"]["label"]}|{r["scenario"]}', {}).get(r["action"]["op"], "unavailable")
        v3a = r["verdicts"]["v3"]["verdict"] == "violation-proven"
        doa = (st == "none") and bool(r["truth"]["app_allowed"])
        if v3a != doa:
            diff_records.append({"config": r["config"]["label"], "scenario": r["scenario"],
                                 "mr": r["mr"], "gui_mode": r["gui_mode"],
                                 "precond_variant": r["precond_variant"],
                                 "truth": r["truth"]["truth"],
                                 "v3_alarm": v3a, "direct_observe_alarm": doa,
                                 "mr_triggered": r["mr_result"]["triggered"],
                                 "precondition_met": r["mr_result"].get("precondition_met")})
    M["block9_direct_observe"] = {
        "methods": b9,
        "recall_difference_direct_observe_minus_v3": {"diff": rd[0], "ci": [rd[1], rd[2]],
                                                      "significant_at_95": not (rd[1] <= 0 <= rd[2])},
        "point_estimate_dominates": (b9["direct_observe"]["FP"] <= b9["v3"]["FP"]
                                     and b9["direct_observe"]["TP"] >= b9["v3"]["TP"]
                                     and (b9["direct_observe"]["TP"] > b9["v3"]["TP"])),
        "disagreement_records": diff_records,
        "disagreement_mechanism": (
            "全部 3 条不一致落在 V-E3-vuln1-listed/S5：MR 因 GUI 可达性前置条件不成立而**不触发**"
            "（listed ⇒ cannotReachThroughGUI=False），故 v3 无告警；direct_observe 不依赖 MR 触发，"
            "仍能告警。即差异由**本文核心机制**（判定外包给 GUI 可达性）产生，而非随机噪声。"),
        "agreement_v3_vs_direct_observe": dict(agree),
        "f1_of_v3": b9["v3"]["f1"],
        "construction_caveat": (
            "direct_observe 的两个输入（普通请求 200、授权面报 none）与 truth 的定义"
            "（bola ⟺ ¬should_allow ∧ app_allowed）同源 ⇒ 该对照与真值**部分同构**，"
            "其支配性是**构造性**的，不能读作『一个独立方法更优』。"),
        "statistical_caveat": (
            "★ 第二轮修正：第七轮以『严格支配』表述该结果，但 TP 差异 108 vs 105 的 95% 区间"
            "包含 0（不显著）。正确表述是**点估计不劣于**（同 FP、TP 略高但差异不显著），"
            "而不是『严格支配』。差异虽小，但其 3 条记录有共同且可解释的机制（见 disagreement_mechanism）。"),
    }
    check("Block9 point_estimate_dominates",
          M["block9_direct_observe"]["point_estimate_dominates"], True)

    # ================= M4 · specificity 口径复现（近似） ===================
    spec = []
    for lab in ("V-noE3-vuln0", "V-E3-vuln0-unlisted", "V-E3-vuln0-listed"):
        sel = [r for r in rep if r["config"]["label"] == lab]
        fp = sum(1 for r in sel if r["grades"]["v1"]["raw_false_alarm"])
        n_fu = 2 * len(sel)
        spec.append({"config": lab, "cases": len(sel), "false_alarms": fp,
                     "followup_inputs_approx": n_fu,
                     "specificity": round(1 - fp / n_fu, 6) if n_fu else None})
    M["m4_specificity_reproduction"] = {
        "rows": spec,
        "caveat": ("分母按 MST-wi 定义为 follow-up 输入数；此处以每 case 2 条 follow-up 输入近似，"
                   "**不是原引擎的精确输入计数**，只用于说明该口径为何掩盖失效模式。"),
    }

    # ================= M5 · 第二实现一致性 =================================
    alt_p = RES / "alt_matrix.jsonl"
    if alt_p.exists():
        alt = [r for r in load_jsonl(alt_p) if "error" not in r]
        ag = di = 0
        mism = []
        for r in alt:
            lab, sc = r["config"]["label"], r["scenario"]
            for mr_id, gm, av in (("MR-002", "blind", r.get("alt_triggered_MR002")),
                                  ("MR-004", "aware", r.get("alt_triggered_MR004"))):
                if av is None:
                    continue
                sel = [x for x in recs if x["config"]["label"] == lab and x["scenario"] == sc
                       and x["mr"] == mr_id and x["precond_variant"] == REP_PV and x["gui_mode"] == gm]
                if not sel:
                    continue
                mv = sel[0]["mr_result"]["triggered"]
                if mv == av:
                    ag += 1
                else:
                    di += 1
                    mism.append({"config": lab, "scenario": sc, "mr": mr_id,
                                 "main": mv, "alt": av})
        M["m5_second_implementation"] = {"compared": ag + di, "agree": ag, "disagree": di,
                                         "agreement_rate": ratio(ag, ag + di),
                                         "agreement_ci": list(wilson(ag, ag + di)),
                                         "mismatches": mism,
                                         "caveat": "同一模型编写的独立实现，只排除实现偶然性，不排除共同盲点。"}
        check("M5 agreement_rate", M["m5_second_implementation"]["agreement_rate"], 1.0)

    # ================= 真实系统（Gitea 1.22.6） =============================
    rs_p = REAL / "real_system.json"
    if rs_p.exists():
        rs = json.loads(rs_p.read_text(encoding="utf-8"))
        m1 = rs["M1_grant_mechanism_census"]
        cells = rs["phaseE_cells"]
        fid = rs["M3_introspection_fidelity"]

        def snap(rd):
            return [c for c in cells if c["reading"] == rd]
        s_cells = snap("snapshot")
        l_cells = snap("live")

        def mismatch(cs):
            return [c for c in cs if c["cannotReachThroughGUI"] and c["authorized"]]

        def alarms(cs, key):
            return sum(1 for c in cs if c["alarms"].get(key))

        def falseproof(cs, key):
            return sum(1 for c in cs if c.get("false_proofs", {}).get(key))

        auth_cells = [c for c in s_cells if c["authorized"]]
        methods = {}
        for k in ("mr_bookkeeping", "v3", "v3_self", "direct_only", "direct_observe",
                  "direct_observe_self"):
            methods[k] = {"alarms_snapshot": alarms(s_cells, k),
                          "false_proofs_snapshot": falseproof(s_cells, k),
                          "false_proof_rate_on_authorized": ratio(falseproof(s_cells, k), len(auth_cells)),
                          "alarms_live": alarms(l_cells, k),
                          "false_proofs_live": falseproof(l_cells, k)}
        # 自视点可读性分解
        self_read = [f for f in fid if f.get("readable_self")]
        # 自视点可读性分解：区分"特权自身"（对象拥有者 / 站点管理员）与"黑箱自身"
        ADMIN = "root"
        self_cells = [f for f in fid if not f["is_acting_credential"] and f["subject"] != ADMIN]
        self_read_bb = [f for f in self_cells if f.get("readable_self")]
        # 一致性只在 authorized 有定义的单元格上判定（is_acting_credential 单元格不参与换凭证测试）
        fid_valid = [f for f in fid if f.get("authorized") is not None]
        M["real_system"] = {
            "version": rs["meta"]["gitea_version"],
            "generated_by": rs["meta"]["generated_by"],
            "honesty_boundary": rs["meta"]["honesty_boundary"],
            "cells_total": len(cells),
            "cells_per_reading": {"snapshot": len(s_cells), "live": len(l_cells)},
            "M1_grant_endpoints": {
                "swagger_total_paths": m1["swagger_total_paths"],
                "grant_endpoints_total": m1["grant_endpoints_total"],
                "revoke_endpoints_total": m1.get("revoke_endpoints_total"),
                "without_site_admin": m1["grant_endpoints_without_site_admin"],
                "predicate": m1["predicate"],
                "framework_log_coverage_upper_bound": 1,
            },
            "M2_readability": {
                "owner_admin_readable": sum(1 for f in fid if f.get("readable")),
                "owner_admin_total": len(fid),
                "self_readable": len(self_read),
                "self_total": len(fid),
                "self_readable_subjects": sorted({f["subject"] for f in self_read},
                                                 key=str),
                "blackbox_self_cells": len(self_cells),
                "blackbox_self_readable": len(self_read_bb),
                "self_readable_only_for_object_owner_or_site_admin": (
                    all(f["is_acting_credential"] or f["subject"] == ADMIN for f in self_read)),
                "readable_perm_values": sorted({str(f.get("permission_self")) for f in self_read}),
            },
            "M3_fidelity": {
                "consistent": sum(1 for f in fid_valid
                                  if bool(f["authorized"]) == bool(f["permission"] and f["permission"] != "none")),
                "total": len(fid_valid),
                "not_applicable": len(fid) - len(fid_valid),
                "not_applicable_reason": "is_acting_credential 单元格（执行者读自己的单元格）不参与换凭证一致性判定",
                "raw_consistent_over_all": sum(
                    1 for f in fid
                    if bool(f["authorized"]) == bool(f["permission"] and f["permission"] != "none")),
                "raw_total": len(fid),
            },
            "M4_snapshot_mismatch": {
                "snapshot": len(mismatch(s_cells)), "live": len(mismatch(l_cells)),
                "denominator": len(s_cells)},
            "M5_methods": methods,
            "M5_authorized_cells": len(auth_cells),
            "M6_provenance": dict(Counter(x["channel"] for x in rs["M6_provenance"])),
            "M6_authorized_out_of_band": sum(
                1 for c in s_cells if c["authorized"] and c.get("provenance") == "out_of_band"),
            "endogenous_control": {},
        }
        # 内生对照：pub1（自始公开） vs r4（采集后转公开）
        for obj, tag in (("alice/pub1", "public_from_start"), ("alice/r4", "public_after_crawl")):
            sub = [c for c in s_cells if c["object"] == obj]
            M["real_system"]["endogenous_control"][tag] = {
                "object": obj, "cells": len(sub),
                "cannotReach_true": sum(1 for c in sub if c["cannotReachThroughGUI"]),
                "mr_fires": sum(1 for c in sub if c["mr_fires"])}
        # M6 授权通道分解：框架自带共享动作（in_band_share）是唯一对框架账本可观测的通道
        prov = M["real_system"]["M6_provenance"]
        non_none = {k: v for k, v in prov.items() if k and k != "none"}
        total_auth = sum(non_none.values())
        in_band = non_none.get("in_band_share", 0)
        M["real_system"]["M6_channel_breakdown"] = {
            "counts": non_none,
            "authorized_total": total_auth,
            "in_band_share": in_band,
            "not_observable_by_framework_log": total_auth - in_band,
            "out_of_band_literal": non_none.get("out_of_band", 0),
            "implicit_derived": (non_none.get("implicit_site_admin", 0)
                                 + non_none.get("implicit_public", 0)),
            "not_observable_rate": ratio(total_auth - in_band, total_auth),
            "out_of_band_literal_rate": ratio(non_none.get("out_of_band", 0), total_auth),
            "caveat": ("这是**构造拓扑的设计参数**，不是野外发生率。"
                       "口径有二：字面 out_of_band 通道，或全部非 in_band 通道（含隐式派生）。"
                       "两者必须分别标注，不得混用。"),
        }

    # ================= 文献常数（MST-wi 自报值，带逐条来源标注） ============
    #  这些数字**不是**本工作算出来的，一律标注来源，禁止与自测数字混用口径。
    #  出处均为 01_文献调研/mstwi_artifact/mstwi_paper_text.txt（原文抽取文本）。
    M["literature"] = {
        "mstwi_mr_catalog": {
            "value": 76, "unit": "MRs",
            "source": "mstwi_paper_text.txt：'a catalog of system-agnostic metamorphic "
                      "relations'；文献调研报告_v2.md line 237 '76 个系统无关 metamorphic relations'",
            "note": "与 refine-logs/catalog_census.csv 实测计数一致（76），可互证。",
        },
        "smrl_web_functions": {
            "value": 55, "unit": "functions",
            "source": "mstwi_paper_text.txt：'Table 2 describes a portion of the 55 "
                      "Web-specific functions in SMRL'",
            "note": "SMRL DSL 的全部内建谓词即此 55 个；授权制品状态谓词不在其中。",
        },
        "reported_detection": {
            "value": 85, "unit": "%",
            "source": "mstwi_paper_text.txt 摘要：'It automatically detected 85% of their "
                      "vulnerabilities'（Jenkins + Joomla）",
            "note": "工程级检出率，非按 CWE 逐项。",
        },
        "reported_specificity": {
            "value": 99.81, "unit": "%",
            "source": "mstwi_paper_text.txt 摘要：'showed a high specificity (99.81% of the "
                      "generated inputs do not lead to a false positive)'",
            "note": "★ 分母原文明确为 'the generated inputs' —— 输入级口径。"
                    "本工作边界 (iii) 即针对该口径的结构性盲区。",
        },
        "authorize_actors_coverage": {
            "weaknesses_all": 60, "covered_generic": 55, "addressed": 34,
            "addressed_pct": 57, "rank": 3,
            "source": "mstwi_paper_text.txt TABLE 8 行 'Authorize Actors 60 55 34 (57%) 3rd'",
            "note": "★ MST-wi 自陈的授权类 CWE 覆盖：60 个中命中 34（57%），"
                    "在 12 个设计原则中排第 3 —— 即原文并未主张授权覆盖薄弱。"
                    "此条用于**拒斥**'授权覆盖薄'叙事，不得反向引用。",
        },
        "mai19_predecessor": {
            "mr_count": 22, "specificity_pct": 99.50, "false_alarms": 32,
            "generated_inputs": 6401, "sensitivity_num": 10, "sensitivity_den": 12,
            "source": "01_文献调研/Undermind_全文精读.md 与 文献调研报告_v2.md 对 "
                      "Mai2019Metamorphic（Metamorphic Security Testing for Web Systems）的记录",
            "note": "★★ 与本工作边界 (ii)/(iii) 直接呼应：该文自陈其 32 例误报"
                    "**主要成因**是 'limitations in the crawler (Crawljax) failing to "
                    "traverse all URLs for all users' —— 即 **GUI 可达性模型本身失效**，"
                    "且误报分母同样是 'generated inputs'（输入级）。"
                    "这是边界 (ii) 的**独立文献佐证**（不是本工作的发现）。",
        },
    }

    # ================= 写盘 ================================================
    M["meta"]["validation_problems"] = PROBLEMS
    (OUT / "metrics.json").write_text(json.dumps(M, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "numbers.tex").write_text(build_tex(M), encoding="utf-8")

    print(f"[ok] {OUT/'metrics.json'}")
    print(f"[ok] {OUT/'numbers.tex'}")
    if PROBLEMS:
        print("\n!! 校验失败:")
        for p in PROBLEMS:
            print("  ", p)
    else:
        print("[ok] 所有交叉校验通过（重算 == 落盘）")


# ---------------------------------------------------------------- LaTeX 宏

def _f(x, nd=2):
    return "---" if x is None else f"{x:.{nd}f}"


_DIGIT_WORDS = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four",
                "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}


def tex_name(name: str) -> str:
    """把宏名净化成 TeX 可用的形式。

    TeX 的控制词只由字母（catcode 11）构成，实测（xelatex）确认：
      * `\\ResAbV3FP`  -> 切成 `\\ResAbV` + 字面量 `3FP`，
        \\newcommand 报 "Command \\ResAbV already defined"；
      * `\\ResVocabshares_of` 里的 `_`（catcode 8，下标符）同样使宏名不可调用。
    故：数字拼写出来，其余非字母字符一律删除。
    """
    out = []
    for c in name:
        if c.isdigit():
            out.append(_DIGIT_WORDS[c])
        elif c.isalpha():
            out.append(c)
        # 其余（_、-、空格等）丢弃
    return "".join(out)


def build_tex(M: dict) -> str:
    L = ["% 由 04_绘图与分析/analysis/compute_all.py 自动生成，请勿手改。",
         "% 正文禁止手敲任何数字，一律引用本文件的宏。",
         "% 宏名内的数字已拼写（V3 -> VThree），因为 TeX 控制词不含数字。", ""]
    a = L.append
    _seen = {}

    def cmd(name, val):
        nm = "Res" + tex_name(name)
        if nm in _seen:
            raise RuntimeError(f"宏名冲突（净化后重复）：{nm} <- {name} & {_seen[nm]}")
        _seen[nm] = name
        a(f"\\newcommand{{\\{nm}}}{{{val}}}")

    lit = M.get("literature", {})
    if lit:
        a("% ---- 文献常数（MST-wi 自报值；非本工作实测，引用须标注来源） ----")
        cmd("LitMrCatalog", lit["mstwi_mr_catalog"]["value"])
        cmd("LitSmrlFunctions", lit["smrl_web_functions"]["value"])
        cmd("LitReportedDetection", lit["reported_detection"]["value"])
        cmd("LitReportedSpecPct", lit["reported_specificity"]["value"])
        aa = lit["authorize_actors_coverage"]
        cmd("LitAuthzWeakAll", aa["weaknesses_all"])
        cmd("LitAuthzCovered", aa["covered_generic"])
        cmd("LitAuthzAddressed", aa["addressed"])
        cmd("LitAuthzAddressedPct", aa["addressed_pct"])
        cmd("LitAuthzRank", aa["rank"])
        mp = lit.get("mai19_predecessor")
        if mp:
            cmd("LitMaiMrCount", mp["mr_count"])
            cmd("LitMaiSpecPct", mp["specificity_pct"])
            cmd("LitMaiFalseAlarms", mp["false_alarms"])
            cmd("LitMaiGenInputs", mp["generated_inputs"])
            cmd("LitMaiSensNum", mp["sensitivity_num"])
            cmd("LitMaiSensDen", mp["sensitivity_den"])

    mt = M["meta"]
    a("% ---- 元数据 ----")
    cmd("SynRecords", mt["synthetic_records_total"])
    cmd("SynOk", mt["synthetic_records_ok"])
    cmd("SynErrors", mt["synthetic_errors"])
    cmd("SynConfigs", len(mt["configs"]))
    cmd("RepSliceN", mt["representative_slice"]["n"])

    ds = M.get("design_structure")
    if ds:
        a("% ---- 设计结构（有效独立单元；区间解读的前置约束） ----")
        cmd("DesignCells", ds["design_cells"])
        cmd("DesignMrs", ds["n_mrs"])
        cmd("DesignCellsTwoMr", ds["cells_with_two_mrs"])
        cmd("DesignCellsOneMr", ds["cells_with_one_mr"])
        cmd("DesignPrecondVariants", len(ds["precond_variants"]))
        cmd("DesignGuiModes", len(ds["gui_modes"]))
        cmd("DesignScenarios", ds["n_scenarios"])
        cmd("DesignMinPerCell", ds["min_records_per_cell"])
        cmd("DesignMaxPerCell", ds["max_records_per_cell"])
        cmd("DesignCellExpansion", ds["cell_expansion"])

    b0 = M["block0_2x2"]
    a("% ---- Block 0：2x2 ----")
    for g in b0["grid"]:
        key = g["config"].replace("V-", "").replace("-", "")
        for k, v in (("Fp", g["FP"]), ("Fn", g["FN"]), ("Tp", g["TP"]), ("Tn", g["TN"]),
                     ("Cases", g["cases"]), ("FpPct", pct(g["FP_rate"])),
                     ("FpLo", pct(g["FP_ci"][0])), ("FpHi", pct(g["FP_ci"][1]))):
            cmd(f"B{key}{k}", v)
    cmd("GridCellsWithError", b0["cells_with_any_error"])
    cmd("GridCellsTotal", b0["cells_total"])
    cmd("GridCellsClean", len(b0["clean_cells"]))

    b2 = M["block2"]
    a("% ---- Block 2：主锚点 ----")
    cmd("FpEthree", _f(b2["FP_E3"]["rate"]))
    cmd("FpEthreeHits", b2["FP_E3"]["hits"])
    cmd("FpEthreeTotal", b2["FP_E3"]["total"])
    cmd("FpEthreePct", pct(b2["FP_E3"]["rate"]))
    cmd("FpEthreeLo", pct(b2["FP_E3"]["ci"][0]))
    cmd("FpEthreeHi", pct(b2["FP_E3"]["ci"][1]))
    cmd("BaseFpHits", b2["baseline_FP"]["hits"])
    cmd("BaseFpTotal", b2["baseline_FP"]["total"])
    cmd("BaseFpRate", _f(b2["baseline_FP"]["rate"]))
    cmd("ListedCtlFpHits", b2["listed_control_FP"]["hits"])
    cmd("ListedCtlFpTotal", b2["listed_control_FP"]["total"])
    cmd("ListedCtlFpRate", _f(b2["listed_control_FP"]["rate"]))
    for sc, d in b2["recall_vuln1_unlisted"].items():
        cmd(f"Recall{sc}", _f(d["rate"]))

    b3 = M["block3_exception_ladder"]
    a("% ---- Block 3：例外层级 ----")
    for k in ("raw", "e1", "e1e2"):
        cmd(f"Ladder{k}Rate", _f(b3[k]["rate"]))

    cen = M.get("catalog_census")
    if cen:
        a("% ---- 目录普查（MST-wi 公开制品，实例无关） ----")
        cmd("CatalogMrTotal", cen["mr_total"])
        cmd("CatalogAuthzName", cen["name_contains_OTG_AUTHZ"])
        cmd("CatalogChangeCred", cen["calls_changeCredentials"])
        cmd("CatalogUnion", cen["union"])
        cmd("CatalogUnionPct", pct(cen["union_rate"]))
        cmd("CatalogGuiDerived", cen["gates_on_GUI_derived"])
        cmd("CatalogGuiDerivedPct", pct(cen["gates_on_GUI_derived_rate"]))
        cmd("CatalogAnyPred", cen["gates_on_any_identity_or_gui"])
        cmd("CatalogUnionGated", cen["of_union_gated_on_GUI_or_identity"])
        cmd("CatalogUnchangedActor", cen["unchanged_actor"])
        cmd("CatalogUnchangedActorPct", pct(cen["unchanged_actor_rate"]))
        cmd("CatalogAuthzStateHits", cen.get("authorization_state_predicate_hits", 0))
        for k, v in (cen.get("dsl_vocabulary_counts") or {}).items():
            cmd(f"Vocab{k}", v)

    art = M.get("artifact_inventory")
    if art:
        a("% ---- 制品清单（原生引擎源码实测；非论文自报） ----")
        cmd("ArtMrTotal", art["owasp_mr_total"])
        cmd("ArtAuthzMrTotal", art["authz_mr_total"])
        cmd("ArtAuthzGatedCrtg", art["gates_on_cannotReachThroughGUI"])
        cmd("ArtAuthzGatedUcrc", art["gates_on_userCanRetrieveContent"])
        cmd("ArtAuthzGatedEither", art["authz_gated_on_either"])
        cmd("ArtAuthzGatedNeither", art["authz_gated_on_neither"])
        for k, v in (art.get("family_counts") or {}).items():
            cmd(f"ArtFam{k}", v)
        # 事实以 0/1 输出（macro 名带完整键，避免前缀重复导致宏名冲突）
        for k, v in (art.get("facts") or {}).items():
            cmd("ArtFact" + k, 1 if v else 0)

    b4 = M["block4_verdict_quality_all"]
    a("% ---- Block 4：裁决质量（全配置） ----")
    for adj in ("v1", "v2", "v3", "degrade_all"):
        d = b4[adj]
        tag = adj.replace("_", "").capitalize()
        for k, v in (("FalseAlarm", d.get("raw_false_alarm", 0)),
                     ("Recovered", d.get("recovered", 0)),
                     ("DetectionKept", d.get("detection_kept", 0)),
                     ("Missed", d.get("missed", 0)),
                     ("RecoveryRate", _f(d["recovery_rate"])),
                     ("KeepRate", _f(d["detection_keep_rate"])),
                     ("CostRate", _f(d["cost_rate"])),
                     ("FnAmongBola", _f(d["fn_rate_among_bola"]))):
            cmd(f"Vd{tag}{k}", v)

    b6 = M["block6_observability"]
    a("% ---- Block 6：可观测性边界 ----")
    for tag, k in (("Fw", "framework_share_legit"), ("Oob", "out_of_band_share_legit"),
                   ("OobBola", "out_of_band_share_bola")):
        d = b6[k]
        for kk, vv in (("FalseAlarm", d["v1_false_alarm_n"]),
                       ("VoneProvenBola", d["v1_proven_on_bola_n"]),
                       ("VtwoFalseProof", d["v2_false_proof_n"]),
                       ("VtwoProvenBola", d["v2_proven_on_bola_n"]),
                       ("VtwoFpRate", _f(d["v1v2_false_proof_rate"])),
                       ("VthreeFalseProof", d["v3_false_proof_n"]),
                       ("VthreeFpRate", _f(d["v3_false_proof_rate"])),
                       ("VthreeProvenBola", d["v3_proven_on_bola_n"]),
                       ("VthreeAbstain", d["v3_abstain_unavailable_n"]),
                       ("BolaTotal", d["bola_total"]),
                       ("Triggered", d["triggered"]),
                       ("N", d["n"]),
                       ("LogRecords", d["framework_log_records"])):
            cmd(f"Obs{tag}{kk}", vv)

    b7 = M["block7_s3_s5_dilemma"]
    cmd("SthreeSfiveAnyCorrect", str(b7["any_config_correct"]))
    for i, r in enumerate(b7["rows"]):
        cmd(f"SthreeSfiveRow{i}SthreeOk", str(r["S3_correct_no_trigger"]))
        cmd(f"SthreeSfiveRow{i}SfiveOk", str(r["S5_correct_trigger"]))

    b8 = M["block8_introspection_boundary"]
    a("% ---- Block 8：v3 可容许性边界 ----")
    for tag, k in (("On", "on"), ("Off", "off")):
        d = b8[k]
        for kk, vv in (("N", d["n"]), ("FalseAlarm", d["false_alarm_n"]),
                       ("BolaTrig", d["bola_trig_n"]),
                       ("VthreeRecoveryRate", _f(d["v3_recovery_rate"])),
                       ("VthreeFpRate", _f(d["v3_false_proof_rate"])),
                       ("VthreeKeepRate", _f(d["v3_detection_keep_rate"])),
                       ("VthreeFpN", d["v3_false_proof_n"]),
                       ("VthreeProvenBola", d["v3_proven_on_bola_n"]),
                       ("VtwoFpN", d["v2_false_proof_n"]),
                       ("VtwoProvenBola", d["v2_proven_on_bola_n"]),
                       ("Abstain", d["v3_abstain_unavailable_n"])):
            cmd(f"Intro{tag}{kk}", vv)

    b9 = M["block9_direct_observe"]["methods"]
    a("% ---- Block 9：决定性消融 ----")
    for adj in ("v1", "v2", "v3", "degrade_all", "direct_only", "direct_observe"):
        d = b9[adj]
        tag = "".join(w.capitalize() for w in adj.split("_"))
        for k in ("TP", "FP", "FN", "TN"):
            cmd(f"Ab{tag}{k}", d[k])
        for k, v in (("Prec", d["precision"]), ("Rec", d["recall"]), ("Fone", d["f1"]),
                     ("PrecLo", d["precision_ci"][0]), ("PrecHi", d["precision_ci"][1]),
                     ("RecLo", d["recall_ci"][0]), ("RecHi", d["recall_ci"][1])):
            cmd(f"Ab{tag}{k}", _f(v))
    rd = M["block9_direct_observe"]["recall_difference_direct_observe_minus_v3"]
    cmd("AbRecallDiff", _f(rd["diff"], 4))
    cmd("AbRecallDiffLo", _f(rd["ci"][0], 4))
    cmd("AbRecallDiffHi", _f(rd["ci"][1], 4))
    cmd("AbRecallDiffSignificant", str(rd["significant_at_95"]))
    cmd("AbDisagreementN", len(M["block9_direct_observe"]["disagreement_records"]))
    cmd("AbNBola", b9["v1"]["n_bola"])
    cmd("AbNNormal", b9["v1"]["n_normal"])

    if "m4_specificity_reproduction" in M:
        a("% ---- M4：specificity 口径 ----")
        for i, r in enumerate(M["m4_specificity_reproduction"]["rows"]):
            cmd(f"SpecRow{i}Cases", r["cases"])
            cmd(f"SpecRow{i}Fa", r["false_alarms"])
            cmd(f"SpecRow{i}Spec", _f(r["specificity"], 6))
            cmd(f"SpecRow{i}SpecPct", _f(100 * r["specificity"], 2))

    if "m5_second_implementation" in M:
        m5 = M["m5_second_implementation"]
        a("% ---- M5：第二实现 ----")
        cmd("AltCompared", m5["compared"])
        cmd("AltAgree", m5["agree"])
        cmd("AltDisagree", m5["disagree"])
        cmd("AltAgreeRate", _f(m5["agreement_rate"]))
        cmd("AltAgreeRateLo", f"{m5['agreement_ci'][1]:.3f}")   # lo (lower bound)
        cmd("AltAgreeRateHi", f"{m5['agreement_ci'][2]:.3f}")    # hi (upper bound)

    if "real_system" in M:
        rs = M["real_system"]
        a("% ---- 真实系统（Gitea） ----")
        cmd("RsVersion", rs["version"])
        cmd("RsCells", rs["cells_total"])
        cmd("RsCellsSnapshot", rs["cells_per_reading"]["snapshot"])
        m1 = rs["M1_grant_endpoints"]
        cmd("RsSwaggerPaths", m1["swagger_total_paths"])
        cmd("RsGrantEndpoints", m1["grant_endpoints_total"])
        cmd("RsRevokeEndpoints", m1["revoke_endpoints_total"])
        cmd("RsGrantNoAdmin", m1["without_site_admin"])
        m2 = rs["M2_readability"]
        cmd("RsOwnerReadable", m2["owner_admin_readable"])
        cmd("RsOwnerReadableTotal", m2["owner_admin_total"])
        cmd("RsSelfReadable", m2["self_readable"])
        cmd("RsSelfTotal", m2["self_total"])
        cmd("RsBlackboxSelfCells", m2["blackbox_self_cells"])
        cmd("RsBlackboxSelfReadable", m2["blackbox_self_readable"])
        m3 = rs["M3_fidelity"]
        cmd("RsFidelityConsistent", m3["consistent"])
        cmd("RsFidelityTotal", m3["total"])
        cmd("RsFidelityNa", m3["not_applicable"])
        m4 = rs["M4_snapshot_mismatch"]
        cmd("RsMismatchSnapshot", m4["snapshot"])
        cmd("RsMismatchLive", m4["live"])
        cmd("RsMismatchDenom", m4["denominator"])
        cmd("RsAuthorizedCells", rs["M5_authorized_cells"])
        for k in ("mr_bookkeeping", "v3", "v3_self", "direct_only", "direct_observe"):
            d = rs["M5_methods"][k]
            tag = "".join(w.capitalize() for w in k.split("_"))
            cmd(f"Rs{tag}Alarms", d["alarms_snapshot"])
            cmd(f"Rs{tag}Fp", d["false_proofs_snapshot"])
            cmd(f"Rs{tag}FpRate", _f(d["false_proof_rate_on_authorized"], 4))
            cmd(f"Rs{tag}AlarmsLive", d["alarms_live"])
            cmd(f"Rs{tag}FpLive", d["false_proofs_live"])
        m6 = rs["M6_channel_breakdown"]
        cmd("RsChannelAuthorizedTotal", m6["authorized_total"])
        cmd("RsChannelInBand", m6["in_band_share"])
        cmd("RsChannelNotObservable", m6["not_observable_by_framework_log"])
        cmd("RsChannelNotObservableRate", _f(m6["not_observable_rate"], 4))
        cmd("RsChannelOobLiteral", m6["out_of_band_literal"])
        cmd("RsChannelOobLiteralRate", _f(m6["out_of_band_literal_rate"], 4))
        cmd("RsChannelImplicit", m6["implicit_derived"])
        for tag, k in (("FromStart", "public_from_start"), ("AfterCrawl", "public_after_crawl")):
            d = rs["endogenous_control"][k]
            cmd(f"RsEndo{tag}Cells", d["cells"])
            cmd(f"RsEndo{tag}Reach", d["cannotReach_true"])
            cmd(f"RsEndo{tag}Fires", d["mr_fires"])

    a("% ---- 校验 ----")
    cmd("ValidationProblems", len(M["meta"]["validation_problems"]))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
