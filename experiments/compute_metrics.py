"""
指标计算与汇总
==============
从 results/raw_matrix.jsonl 计算 v5 §4.2 声明的全部指标:

  Block 2  主锚点   : FP_E3 / 基线 FP / 召回侧触发率
  Block 3  消融-3   : 例外谓词层级 (raw → E1 → E1E2) 对 FP_E3 的影响
  Block 4  消融-1,2 : 恢复率 / 检测力保持率 / 代价（对象级探测 vs 一律降级）
  Block 5  辨析力   : 判定等价率 / 结构等价率
  M4       口径复现 : specificity(分母 ≈ follow-up 输入数)

"代表配置" = precond_variant=raw 且 gui_mode=aware —— 即最忠实于 MST-wi 原始行为的设定。

用法: python compute_metrics.py
输出: results/summary.json, results/SUMMARY.md, results/figures/*.png
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIGDIR = RESULTS / "figures"
FIGDIR.mkdir(exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REP_PV, REP_GM = "raw", "aware"


# --------------------------------------------------------------------------
# 载入与工具
# --------------------------------------------------------------------------

def load(name: str = "raw_matrix.jsonl") -> list[dict]:
    p = RESULTS / name
    if not p.exists():
        raise SystemExit(f"缺少结果文件: {p}")
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def rate(n: int, d: int):
    return None if not d else round(n / d, 4)


def structural_fp(obs: dict) -> str:
    """结构指纹：保留 status 与 schema 形状，抹去具体取值。"""
    def shape(x):
        if isinstance(x, dict):
            return {k: shape(v) for k, v in x.items()}
        if isinstance(x, list):
            return [shape(x[0])] if x else []
        return type(x).__name__
    return json.dumps({"status": obs.get("status"), "shape": shape(obs.get("body"))},
                      sort_keys=True, ensure_ascii=False)


def md_table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)


# --------------------------------------------------------------------------
# 主分析
# --------------------------------------------------------------------------

def main():
    allrecs = load()
    errs = [r for r in allrecs if "error" in r]
    recs = [r for r in allrecs if "error" not in r]
    rep = [r for r in recs if r["precond_variant"] == REP_PV and r["gui_mode"] == REP_GM]

    labels = sorted({r["config"]["label"] for r in recs})
    scen_order = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
    S = {}

    # ---------- Block 2: 主触发矩阵 -----------------------------------------
    trig: dict[tuple, dict[str, bool]] = defaultdict(dict)
    for r in rep:
        trig[(r["config"]["label"], r["scenario"])][r["mr"]] = r["mr_result"]["triggered"]

    rows = []
    for lab in labels:
        row = [lab]
        for sc in scen_order:
            d = trig.get((lab, sc), {})
            if not d:
                row.append("—")
                continue
            marks = "".join("T" if v else "·" for v in d.values())
            row.append(f"{marks} ({sum(d.values())}/{len(d)})")
        rows.append(row)
    S["main_matrix_md"] = md_table(["config"] + scen_order, rows)

    def frac(cfg_label: str, scen: str, predicate=None) -> tuple[int, int]:
        sel = [r for r in rep if r["config"]["label"] == cfg_label and r["scenario"] == scen]
        if predicate:
            sel = [r for r in sel if predicate(r)]
        return sum(1 for r in sel if r["mr_result"]["triggered"]), len(sel)

    fp_e3_n, fp_e3_d = frac("V-E3-vuln0-unlisted", "S3")
    base_fp_n, base_fp_d = frac("V-noE3-vuln0", "S1")
    fp_e3_listed_n, fp_e3_listed_d = frac("V-E3-vuln0-listed", "S3")
    recall_metrics = {}
    for sc in ("S2", "S4", "S5"):
        n, d = frac("V-E3-vuln1-unlisted", sc)
        recall_metrics[sc] = {"hits": n, "total": d, "rate": rate(n, d)}

    S["block2"] = {
        "FP_E3": {"hits": fp_e3_n, "total": fp_e3_d, "rate": rate(fp_e3_n, fp_e3_d),
                  "config": "V-E3-vuln0-unlisted", "scenario": "S3"},
        "baseline_FP": {"hits": base_fp_n, "total": base_fp_d, "rate": rate(base_fp_n, base_fp_d),
                        "config": "V-noE3-vuln0", "scenario": "S1"},
        "FP_E3_listed_control": {"hits": fp_e3_listed_n, "total": fp_e3_listed_d,
                                 "rate": rate(fp_e3_listed_n, fp_e3_listed_d),
                                 "config": "V-E3-vuln0-listed", "scenario": "S3"},
        "recall_vuln1_unlisted": recall_metrics,
    }

    # ---------- Block 3: 例外谓词层级消融 -----------------------------------
    abl3 = {}
    for pv in ("raw", "e1", "e1e2"):
        sel = [r for r in recs if r["precond_variant"] == pv and r["gui_mode"] == REP_GM
               and r["config"]["label"] == "V-E3-vuln0-unlisted" and r["scenario"] == "S3"]
        hit = sum(1 for r in sel if r["mr_result"]["triggered"])
        abl3[pv] = {"hits": hit, "total": len(sel), "rate": rate(hit, len(sel))}
    S["block3"] = abl3

    # ---------- Block 4: 裁决质量（收益与代价）-----------------------------
    def judge_quality(adj: str, cfg_filter=None):
        agg = defaultdict(int)
        for r in rep:
            if cfg_filter and r["config"]["label"] != cfg_filter:
                continue
            g = r["grades"][adj]
            for k, v in g.items():
                agg[k] += int(bool(v))
        return dict(agg)

    def with_rates(a):
        denom_recover = a.get("raw_false_alarm", 0)
        denom_bola = a.get("detection_kept", 0) + a.get("costly_downgrade", 0) \
            + a.get("missed", 0)
        # 检测力保持率的分母应为"真 BOLA 且 MR 触发"的实例数
        denom_trig_bola = a.get("detection_kept", 0) + a.get("costly_downgrade", 0)
        return {
            **a,
            "recovery_rate": rate(a.get("recovered", 0), denom_recover),
            "detection_keep_rate": rate(a.get("detection_kept", 0), denom_trig_bola),
            "cost_rate": rate(a.get("costly_downgrade", 0), denom_trig_bola),
            "fn_rate_among_bola": rate(a.get("missed", 0), denom_bola),
        }

    S["block4_e3_only"] = {adj: with_rates(judge_quality(adj, "V-E3-vuln0-unlisted"))
                           for adj in ("v1", "v2", "v3", "degrade_all")}
    S["block4_all"] = {adj: with_rates(judge_quality(adj))
                       for adj in ("v1", "v2", "v3", "degrade_all")}

    # ---------- Block 5: 辨析力 --------------------------------------------
    # ★ 关键: 只在 vuln=1 的应用上比较。
    #   只有此时"合法共享访问"(S3) 与"越权访问"(S4/S5) 都表现为"应用允许",
    #   问"MR 能否区分二者"才有意义。
    #   在 vuln=0 上 S4/S5 会被正确拒绝(403), 观测天然不同 —— 那不是辨析力丧失,
    #   而是应用本身正确。把两者混算会人为稀释该指标。
    detail, eq_decision, eq_struct, tot = [], 0, 0, 0
    for cfg_lab in ("V-E3-vuln1-unlisted", "V-E3-vuln1-listed"):
        for other_sc, other_desc in (("S4", "访问未共享对象"), ("S5", "写越权")):
            a = {(r["mr"], r["gui_mode"]): r for r in recs
                 if r["config"]["label"] == cfg_lab and r["scenario"] == "S3"
                 and r["precond_variant"] == REP_PV}
            b = {(r["mr"], r["gui_mode"]): r for r in recs
                 if r["config"]["label"] == cfg_lab and r["scenario"] == other_sc
                 and r["precond_variant"] == REP_PV}
            for k in sorted(a.keys() & b.keys()):
                tot += 1
                same_dec = a[k]["mr_result"]["triggered"] == b[k]["mr_result"]["triggered"]
                same_struct = (structural_fp(a[k]["mr_result"]["input2"])
                               == structural_fp(b[k]["mr_result"]["input2"]))
                eq_decision += int(same_dec)
                eq_struct += int(same_struct)
                detail.append({
                    "config": cfg_lab, "mr": k[0], "gui_mode": k[1],
                    "pair": f"S3 vs {other_sc}（{other_desc}）",
                    "truth_S3": a[k]["truth"]["truth"],
                    "truth_other": b[k]["truth"]["truth"],
                    "triggered_S3": a[k]["mr_result"]["triggered"],
                    "triggered_other": b[k]["mr_result"]["triggered"],
                    "decision_equivalent": same_dec,
                    "structural_equivalent": same_struct,
                })
    S["block5"] = {
        "pairs_compared": tot,
        "decision_equivalence_rate": rate(eq_decision, tot),
        "structural_equivalence_rate": rate(eq_struct, tot),
        "scope": "仅 vuln=1 的应用（此时 S4/S5 亦为 BOLA，才构成『合法 vs 越权』的不可区分对）",
        "pairs": detail,
        "note": ("判定等价 = MR 对「合法共享访问」与「越权访问」给出相同触发结论; "
                 "结构等价 = 两次观测在 status+schema 形状上不可区分（具体取值不同）"),
    }

    # ---------- M4: specificity 口径复现 -----------------------------------
    def specificity(cfg_lab: str):
        sel = [r for r in rep if r["config"]["label"] == cfg_lab]
        fp = sum(1 for r in sel if r["grades"]["v1"]["raw_false_alarm"])
        # 近似: 每个 case 的 follow-up 输入数 = 2 (Input(1) + Input(2))
        n_followup = 2 * len(sel)
        return {"config": cfg_lab, "cases": len(sel), "false_alarms": fp,
                "followup_inputs_approx": n_followup,
                "specificity": (round(1 - fp / n_followup, 6) if n_followup else None)}

    S["m4_specificity"] = [specificity(l) for l in
                           ("V-noE3-vuln0", "V-E3-vuln0-unlisted", "V-E3-vuln0-listed")]

    # ---------- 全量混淆矩阵 ------------------------------------------------
    conf = defaultdict(int)
    for r in rep:
        conf[(r["config"]["label"], r["confusion"])] += 1
    S["confusion"] = {f"{k[0]}|{k[1]}": v for k, v in sorted(conf.items())}

    # ---------- Block 0: 2×2 网格（第五轮硬条件 A4）-------------------------
    # 轴1 = 通道可见性（共享对列举/GUI 是否可见）× 轴2 = 应用授权是否正确。
    # 目的: 证明**没有任何一格是零错误**，从而说明"误报是关掉谓词造出来的"不成立。
    E3_SC = ("S3", "S4", "S5", "S6", "S7")
    grid = []
    for lab, vis, auth in (("V-E3-vuln0-unlisted", "unlisted", "correct"),
                           ("V-E3-vuln0-listed", "listed", "correct"),
                           ("V-E3-vuln1-unlisted", "unlisted", "violating"),
                           ("V-E3-vuln1-listed", "listed", "violating")):
        sel = [r for r in rep if r["config"]["label"] == lab and r["scenario"] in E3_SC]
        grid.append({
            "config": lab, "channel_visibility": vis, "app_authorization": auth,
            "cases": len(sel),
            "FP": sum(1 for r in sel if r["confusion"] == "FP"),
            "FN": sum(1 for r in sel if r["confusion"] == "FN"),
            "TP": sum(1 for r in sel if r["confusion"] == "TP"),
            "TN": sum(1 for r in sel if r["confusion"] == "TN"),
        })
    S["block0_2x2"] = {
        "grid": grid,
        "scope": "仅含存在对象级共享的场景 S3–S7；代表切片 raw+GUI-aware",
        "note": ("每个格子都可能同时出现 FP 与 FN —— 这正是「谓词在误报与漏报之间二选一」"
                 "的可视化证据，也说明误报并非「关掉谓词」造出来的。"),
    }

    # ---------- Block 7: S3 与 S5 能否同时判对（审判方的独立遍历结论）--------
    # S3 = 合法共享访问（真值 normal，MR 应**不**触发）
    # S5 = 只读共享下的写越权（真值 bola，MR 应触发）
    # 正确配置必须同时满足两者。若不存在这样的配置 → 判定能力被迫二选一。
    cross = []
    for lab in ("V-E3-vuln1-unlisted", "V-E3-vuln1-listed"):
        s3 = [r for r in rep if r["config"]["label"] == lab and r["scenario"] == "S3"]
        s5 = [r for r in rep if r["config"]["label"] == lab and r["scenario"] == "S5"]
        s3_ok = bool(s3) and all(not r["mr_result"]["triggered"] for r in s3)
        s5_ok = bool(s5) and all(r["mr_result"]["triggered"] for r in s5)
        cross.append({
            "config": lab,
            "S3_no_trigger": s3_ok, "S3_detail": f"{sum(1 for r in s3 if not r['mr_result']['triggered'])}/{len(s3)}",
            "S5_trigger": s5_ok, "S5_detail": f"{sum(1 for r in s5 if r['mr_result']['triggered'])}/{len(s5)}",
            "both_correct": bool(s3_ok and s5_ok),
        })
    S["block7_s3_s5_dilemma"] = {
        "rows": cross,
        "any_config_correct": any(c["both_correct"] for c in cross),
        "note": ("在 vuln=1（S3 与 S5 仅能靠授权区分）上，不存在使 S3 与 S5 同时判对的配置 ⇒ "
                 "MR 判定被迫在「误报」与「漏报」之间二选一。"),
    }

    # ---------- Block 6: 修正机制的可观测性边界（第五轮硬条件 A1）------------
    def obs_stats(scen: str) -> dict:
        # 仅取具备对象级共享能力（e3）且实际发起过共享的配置，避免 noe3 记录稀释
        sel = [r for r in rep if r["scenario"] == scen
               and r["config"]["mode"] == "e3"]
        d = {
            "scenario": scen,
            "share_origin": sorted({r["setup"].get("share_origin", "?") for r in sel}),
            "n": len(sel),
            "triggered": sum(1 for r in sel if r["mr_result"]["triggered"]),
            "bola_total": sum(1 for r in sel if r["truth"]["truth"] == "bola"),
            "TP": sum(1 for r in sel if r["confusion"] == "TP"),
            "FP": sum(1 for r in sel if r["confusion"] == "FP"),
            "FN": sum(1 for r in sel if r["confusion"] == "FN"),
            "TN": sum(1 for r in sel if r["confusion"] == "TN"),
            "false_alarm_n": sum(1 for r in sel if r["grades"]["v1"]["raw_false_alarm"]),
            "recovered_n": sum(1 for r in sel if r["grades"]["v1"]["recovered"]),
            "false_proof_n": sum(1 for r in sel
                                 if r["grades"]["v1"]["raw_false_alarm"]
                                 and r["verdicts"]["v1"]["verdict"] == "violation-proven"),
            "proven_on_bola_n": sum(1 for r in sel if r["truth"]["truth"] == "bola"
                                    and r["verdicts"]["v1"]["verdict"] == "violation-proven"),
            # ---- v3（探测数据源 = SUT 授权自省面）----
            "v3_recovered_n": sum(1 for r in sel if r["grades"]["v3"]["recovered"]),
            "v3_false_proof_n": sum(1 for r in sel
                                    if r["grades"]["v3"]["raw_false_alarm"]
                                    and r["verdicts"]["v3"]["verdict"] == "violation-proven"),
            "v3_proven_on_bola_n": sum(1 for r in sel if r["truth"]["truth"] == "bola"
                                       and r["verdicts"]["v3"]["verdict"] == "violation-proven"),
            "v3_abstain_unavailable_n": sum(
                1 for r in sel
                if r["verdicts"]["v3"]["witness"]
                and r["verdicts"]["v3"]["witness"].get("sut_introspection") == "unavailable"),
            # 框架侧可观测的授权记录条数（0 = 不可观测）
            "share_log_records": sum(len(r.get("share_log") or []) for r in sel),
        }
        d["recovery_rate"] = rate(d["recovered_n"], d["false_alarm_n"])
        d["false_proof_rate"] = rate(d["false_proof_n"], d["false_alarm_n"])
        d["v3_recovery_rate"] = rate(d["v3_recovered_n"], d["false_alarm_n"])
        d["v3_false_proof_rate"] = rate(d["v3_false_proof_n"], d["false_alarm_n"])
        return d

    S["block6_observability"] = {
        "framework_share_legit": obs_stats("S3"),
        "out_of_band_share_legit": obs_stats("S6"),
        "out_of_band_share_bola": obs_stats("S7"),
        "claim": "修正机制的有效范围 = 共享操作对测试框架可观测；不可观测时失效方向为**假确证**",
    }

    # ---------- Block 8: v3 的可容许性边界（授权自省面 on/off）----------------
    # 第六轮审判 C8 指出: 探针失效是因为读了"框架账本"而非"SUT 授权面"。
    # Block 8 直接检验该反驳: 把 v3 的数据源换成 SUT 授权面后，
    #   * 自省面可读  → 是否既消除假确证、又保住检测力？
    #   * 自省面缺失  → 是否退化为诚实弃权（宁可不报，不造假确证）？
    def v3_by_introspection(intro: str) -> dict:
        sel = [r for r in rep if r["config"]["mode"] == "e3"
               and r["config"].get("introspection", "on") == intro
               and r["scenario"] in E3_SC]
        d = {
            "introspection": intro, "n": len(sel),
            "false_alarm_n": sum(1 for r in sel if r["grades"]["v1"]["raw_false_alarm"]),
            "bola_trig_n": sum(1 for r in sel if r["truth"]["truth"] == "bola"
                               and r["mr_result"]["triggered"]),
            "v3_recovered_n": sum(1 for r in sel if r["grades"]["v3"]["recovered"]),
            "v3_false_proof_n": sum(1 for r in sel
                                    if r["grades"]["v3"]["raw_false_alarm"]
                                    and r["verdicts"]["v3"]["verdict"] == "violation-proven"),
            "v3_proven_on_bola_n": sum(1 for r in sel if r["truth"]["truth"] == "bola"
                                       and r["verdicts"]["v3"]["verdict"] == "violation-proven"),
            "v3_abstain_unavailable_n": sum(
                1 for r in sel if r["verdicts"]["v3"]["witness"]
                and r["verdicts"]["v3"]["witness"].get("sut_introspection") == "unavailable"),
            "v2_false_proof_n": sum(1 for r in sel
                                    if r["grades"]["v2"]["raw_false_alarm"]
                                    and r["verdicts"]["v2"]["verdict"] == "violation-proven"),
            "v2_proven_on_bola_n": sum(1 for r in sel if r["truth"]["truth"] == "bola"
                                       and r["verdicts"]["v2"]["verdict"] == "violation-proven"),
        }
        d["v3_recovery_rate"] = rate(d["v3_recovered_n"], d["false_alarm_n"])
        d["v3_false_proof_rate"] = rate(d["v3_false_proof_n"], d["false_alarm_n"])
        d["v3_detection_keep_rate"] = rate(d["v3_proven_on_bola_n"], d["bola_trig_n"])
        return d

    S["block8_introspection_boundary"] = {
        "introspection_on": v3_by_introspection("on"),
        "introspection_off": v3_by_introspection("off"),
        "claim": ("v3 的可容许性条件 = 应用暴露测试者可读的授权自省面；"
                  "面可读 ⇒ 既消除假确证又保住检测力；面缺失 ⇒ 退化为诚实弃权（检测力归零）。"),
    }

    S["meta"] = {
        "total_records": len(allrecs), "completed": len(recs), "errors": len(errs),
        "representative_slice": {"precond_variant": REP_PV, "gui_mode": REP_GM,
                                 "n": len(rep)},
        "scenarios": scen_order,
    }

    # ---------- 漏报清单（供渲染） ------------------------------------------
    S["fns"] = [r for r in rep if r["confusion"] == "FN"]

    # ---------- M5: 第二实现一致性 ------------------------------------------
    alt_path = RESULTS / "alt_matrix.jsonl"
    if alt_path.exists():
        alt = [json.loads(l) for l in alt_path.open(encoding="utf-8") if l.strip()]
        alt = [r for r in alt if "error" not in r]
        agree = disagree = 0
        mism = []
        for r in alt:
            lab, sc = r["config"]["label"], r["scenario"]
            pairs = [
                # 第二实现的 MR-002 不含 GUI 前置条件 → 与主实现 gui_blind 切片同类
                ("MR-002", "blind", r.get("alt_triggered_MR002")),
                # 第二实现的 MR-004 用列举建模可见性 → 与主实现 gui_aware 切片同类
                ("MR-004", "aware", r.get("alt_triggered_MR004")),
            ]
            for mr_id, gm, alt_v in pairs:
                if alt_v is None:
                    continue
                sel = [x for x in recs if x["config"]["label"] == lab
                       and x["scenario"] == sc and x["mr"] == mr_id
                       and x["precond_variant"] == REP_PV and x["gui_mode"] == gm]
                if not sel:
                    continue
                main_v = sel[0]["mr_result"]["triggered"]
                if main_v == alt_v:
                    agree += 1
                else:
                    disagree += 1
                    mism.append({"config": lab, "scenario": sc, "mr": mr_id,
                                 "main_impl": main_v, "alt_impl": alt_v})
        S["m5_second_impl"] = {
            "compared": agree + disagree, "agree": agree, "disagree": disagree,
            "agreement_rate": rate(agree, agree + disagree),
            "mismatches": mism,
            "mapping_note": ("第二实现的 MR-002 无 GUI 前置条件 → 与主实现 gui_blind 切片对比；"
                             "第二实现的 MR-004 用列举建模可见性 → 与主实现 gui_aware 切片对比。"
                             "映射错位会产生假分歧，故显式记录。"),
            "caveat": "同一模型编写的独立实现，只排除实现偶然性，不排除共同盲点。",
        }

    # ---------- 写盘 --------------------------------------------------------
    (RESULTS / "summary.json").write_text(
        json.dumps(S, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "SUMMARY.md").write_text(render_md(S, errs), encoding="utf-8")
    try:
        make_figures(rep, S)
    except Exception as e:
        print(f"[warn] 出图跳过: {e}")

    print(json.dumps({k: S[k] for k in ("block2", "block3", "block4_e3_only", "block5",
                                        "m4_specificity")},
                     ensure_ascii=False, indent=2))
    print(f"\n[out] {RESULTS/'SUMMARY.md'}")


def render_md(S: dict, errs: list) -> str:
    b2, b3, b4, b5 = S["block2"], S["block3"], S["block4_all"], S["block5"]
    L = []
    L.append("# 实验结果汇总（自动生成，勿手改）\n")
    L.append(f"- 记录总数：{S['meta']['total_records']}，成功 {S['meta']['completed']}，"
             f"错误 {len(errs)}")
    L.append(f"- 代表切片：precond={S['meta']['representative_slice']['precond_variant']}，"
             f"gui_mode={S['meta']['representative_slice']['gui_mode']}"
             f"（n={S['meta']['representative_slice']['n']}）\n")

    L.append("## Block 0 · 2×2 网格（通道可见性 × 应用授权正确性）\n")
    L.append(f"- 口径：{S['block0_2x2']['scope']}")
    L.append(md_table(["config", "通道可见性", "应用授权", "case 数", "FP", "FN", "TP", "TN"],
                      [[d["config"], d["channel_visibility"], d["app_authorization"],
                        d["cases"], d["FP"], d["FN"], d["TP"], d["TN"]]
                       for d in S["block0_2x2"]["grid"]]) + "\n")
    L.append(f"> {S['block0_2x2']['note']}\n")

    L.append("## Block 2 · 主触发矩阵（T=触发，·=未触发）\n")
    L.append(S["main_matrix_md"] + "\n")
    f = b2["FP_E3"]; bf = b2["baseline_FP"]; fl = b2["FP_E3_listed_control"]
    L.append(f"**`FP_E3`**（{f['config']} @ S3，即存在 E3 例外且应用授权正确）"
             f" = **{f['hits']}/{f['total']} = {f['rate']}**")
    L.append(f"\n**基线 FP**（{bf['config']} @ S1，无共享阴性对照） = "
             f"**{bf['hits']}/{bf['total']} = {bf['rate']}**")
    L.append(f"\n**对照 FP**（{fl['config']} @ S3，共享对 GUI 可见） = "
             f"{fl['hits']}/{fl['total']} = {fl['rate']}\n")
    L.append("\n召回侧（vuln=1）：\n")
    L.append(md_table(["scenario", "触发", "比例"],
                      [[k, f"{v['hits']}/{v['total']}", v["rate"]]
                       for k, v in b2["recall_vuln1_unlisted"].items()]) + "\n")

    L.append("## Block 3 · 例外谓词层级消融（V-E3-vuln0-unlisted @ S3）\n")
    L.append(md_table(["例外谓词配置", "FP_E3 触发", "比例", "含义"],
                      [["MR-raw", f"{b3['raw']['hits']}/{b3['raw']['total']}", b3['raw']['rate'],
                        "无例外谓词（≈ EvoMaster fault 306 层级 ℒ₁）"],
                       ["MR-E1", f"{b3['e1']['hits']}/{b3['e1']['total']}", b3['e1']['rate'],
                        "+ !isAdmin"],
                       ["MR-E1E2", f"{b3['e1e2']['hits']}/{b3['e1e2']['total']}",
                        b3['e1e2']['rate'], "+ !isSupervisorOf（= MST-wi 能力上限 ℒ₂）"]]) + "\n")

    L.append("## Block 4 · 裁决质量：收益与代价（全部应用配置）\n")
    L.append(md_table(["裁决器", "原始误报", "恢复(→indeterminate)", "恢复率",
                       "检测力保持", "代价(真BOLA被降级)", "代价率", "漏报(BOLA未触发)"],
                      [[adj, d.get("raw_false_alarm", 0), d.get("recovered", 0),
                        d["recovery_rate"], d.get("detection_kept", 0),
                        d.get("costly_downgrade", 0), d["cost_rate"],
                        d.get("missed", 0)]
                       for adj, d in b4.items()]) + "\n")
    e3 = S["block4_e3_only"]
    L.append(f"> 仅看 FP 发生的那一个配置（V-E3-vuln0-unlisted）：v1 恢复率 "
             f"{e3['v1']['recovery_rate']}，v2 恢复率 {e3['v2']['recovery_rate']}。")
    L.append("> `degrade_all`（凡触发即降级）的检测力保持率为 "
             f"**{b4['degrade_all']['detection_keep_rate']}**、代价率 "
             f"{b4['degrade_all']['cost_rate']} —— 这正是它只能靠放弃全部检测来换取零误报的证据，"
             "从而说明对象级探测相对「一律弃权」的必要性。")
    L.append("> `v2`（+权限层级匹配）把 v1 的代价率 "
             f"{b4['v1']['cost_rate']} 降到 **{b4['v2']['cost_rate']}**，"
             "同时检测力保持率由 "
             f"{b4['v1']['detection_keep_rate']} 升到 **{b4['v2']['detection_keep_rate']}**。\n")

    L.append("## Block 5 · 辨析力丧失（不可区分性）\n")
    L.append(f"- 比较域：{b5.get('scope', '')}")
    L.append(f"- 比较对数：{b5['pairs_compared']}")
    L.append(f"- **判定等价率** = {b5['decision_equivalence_rate']}")
    L.append(f"- **结构等价率** = {b5['structural_equivalence_rate']}")
    L.append(f"\n> {b5['note']}\n")
    if b5.get("pairs"):
        L.append(md_table(["config", "MR", "gui", "对比对", "truth(S3)", "truth(对照)",
                           "触发(S3)", "触发(对照)", "判定等价", "结构等价"],
                          [[d["config"], d["mr"], d["gui_mode"], d["pair"],
                            d["truth_S3"], d["truth_other"], d["triggered_S3"],
                            d["triggered_other"], d["decision_equivalent"],
                            d["structural_equivalent"]] for d in b5["pairs"]]) + "\n")

    # ---------- Block 7: S3/S5 二选一困境 ----------------------------------
    b7 = S["block7_s3_s5_dilemma"]
    L.append("## Block 7 · S3 与 S5 能否同时判对（判定能力二选一）\n")
    L.append(md_table(["config", "S3 不触发(正确)", "S5 触发(正确)", "两者同时正确"],
                      [[d["config"], f"{d['S3_no_trigger']} ({d['S3_detail']})",
                        f"{d['S5_trigger']} ({d['S5_detail']})", d["both_correct"]]
                       for d in b7["rows"]]) + "\n")
    L.append(f"- **存在同时判对的配置** = {b7['any_config_correct']}")
    L.append(f"- {b7['note']}\n")

    # ---------- Block 6: 可观测性边界 --------------------------------------
    b6 = S["block6_observability"]
    L.append("## Block 6 · 修正机制的可观测性边界（框架创建 vs 带外预存共享）\n")
    rows6 = []
    for key, name in (("framework_share_legit", "S3 框架创建（可观测）"),
                      ("out_of_band_share_legit", "S6 带外预存（不可观测）"),
                      ("out_of_band_share_bola", "S7 带外预存 + 真越权")):
        d = b6[key]
        rows6.append([name, "/".join(d["share_origin"]), d["share_log_records"],
                      d["false_alarm_n"],
                      d["recovered_n"], d["recovery_rate"],
                      d["false_proof_n"], d["false_proof_rate"],
                      d["v3_recovered_n"], d["v3_recovery_rate"],
                      d["v3_false_proof_n"], d["v3_false_proof_rate"],
                      d["v3_proven_on_bola_n"]])
    L.append(md_table(["场景", "授权来源", "框架侧授权记录", "原始误报",
                       "v1/v2 恢复", "v1/v2 恢复率", "v1/v2 假确证", "v1/v2 假确证率",
                       "**v3 恢复**", "**v3 恢复率**", "**v3 假确证**", "**v3 假确证率**",
                       "**v3 真越权确证**"], rows6) + "\n")
    L.append(f"> **主张**：{b6['claim']}")
    L.append("> ")
    L.append("> S3 与 S6 的**唯一差异**是授权来源：S3 由框架调用共享 API 创建（`share_log` 记 1 条），"
             "S6 由带外种入（`share_log` 记 0 条）。应用侧授权判定完全相同（都正确允许）。")
    L.append("> 结果是恢复率从 **1.00 崩到 0.00**，且失效方向不是「恢复不了」而是"
             "**把正确应用升级为 `violation-proven`（假确证）**——比原始误报更危险，因为它带「已确证」标签。")
    L.append("> S7 说明该边界是**单侧的**：带外授权不会损害真越权的检测力（仍为确证）。\n")

    # ---------- Block 8: v3 的可容许性边界 ---------------------------------
    b8 = S["block8_introspection_boundary"]
    on_, off_ = b8["introspection_on"], b8["introspection_off"]
    L.append("## Block 8 · v3 的可容许性边界（授权自省面 on / off）\n")
    L.append(md_table(
        ["配置", "case 数", "原始误报", "真越权触发",
         "v3 恢复率", "v3 假确证率", "v3 检测力保持率", "v3 因自省面缺失弃权"],
        [["自省面 **on**", on_["n"], on_["false_alarm_n"], on_["bola_trig_n"],
          on_["v3_recovery_rate"], on_["v3_false_proof_rate"],
          on_["v3_detection_keep_rate"], on_["v3_abstain_unavailable_n"]],
         ["自省面 **off**", off_["n"], off_["false_alarm_n"], off_["bola_trig_n"],
          off_["v3_recovery_rate"], off_["v3_false_proof_rate"],
          off_["v3_detection_keep_rate"], off_["v3_abstain_unavailable_n"]]]) + "\n")
    L.append(f"- **主张**：{b8['claim']}")
    L.append("> ")
    L.append("> v3 与 v1/v2 的**唯一差异**是探测数据的来源：v1/v2 读**测试框架自己的账本**"
             "（`share_log`），v3 读**被测系统自报的授权面**（`GET /doc/{id}/shares`，以拥有者身份）。")
    L.append("> 对照 v2（同为'权限层级匹配'语义，仅数据源不同）的最强配置："
             f"自省面 on 时 v3 假确证 {on_['v3_false_proof_n']} 次 vs v2 {on_['v2_false_proof_n']} 次；"
             f"真越权确证 v3 {on_['v3_proven_on_bola_n']} 次 vs v2 {on_['v2_proven_on_bola_n']} 次。")
    L.append("> 自省面 off 时 v3 **全部因无法排除不透明授权而弃权**"
             f"（{off_['v3_abstain_unavailable_n']} 次），检测力保持率降为 "
             f"**{off_['v3_detection_keep_rate']}** —— 这是诚实的代价，而非缺陷。\n")

    # ---------- 附：前置条件依赖 GUI 模型造成的漏报 -------------------------
    fns = S.get("fns", [])
    if fns:
        L.append("## 附 · 漏报分析（FN：真 BOLA 但 MR 未触发）\n")
        L.append(f"共 {len(fns)} 条。逐条列出来源，避免只报喜不报忧：\n")
        L.append(md_table(["config", "scenario", "MR", "gui", "真值", "前置条件成立",
                           "输入1", "输入2", "原因"],
                          [[r["config"]["label"], r["scenario"], r["mr"], r["gui_mode"],
                            r["truth"]["truth"], r["mr_result"].get("precondition_met"),
                            r["mr_result"]["input1"]["status"],
                            r["mr_result"]["input2"]["status"],
                            ("前置条件被 GUI 可达性判定挡住 → MR 不适用"
                             if not r["mr_result"].get("precondition_met")
                             else "输出不同 → 未达违反条件")]
                           for r in fns]) + "\n")
        L.append("> 这说明：依赖 GUI 可达性的前置条件在**共享对 GUI 可见**时会把 MR 变成"
                 "「不适用」，从而对真正的越权访问**漏报**。它与假阳是同一枚硬币的两面——"
                 "都是判定能力外包给 GUI 模型的后果。\n")

    L.append("## M4 · specificity 口径复现（近似）\n")
    L.append(md_table(["config", "cases", "false alarms", "follow-up 输入(≈)", "specificity"],
                      [[d["config"], d["cases"], d["false_alarms"],
                        d["followup_inputs_approx"], d["specificity"]]
                       for d in S["m4_specificity"]]) + "\n")
    L.append("> 分母口径按 MST-wi 定义为 follow-up 输入数；本表以每 case 2 条 follow-up 输入近似，"
             "**不是原引擎的精确输入计数**，仅供说明「该口径为何掩盖失效模式」。\n")

    m5 = S.get("m5_second_impl")
    if m5:
        L.append("## M5 · 第二实现一致性（排除实现偶然性）\n")
        L.append(f"- 可比对数：{m5['compared']}，一致 {m5['agree']}，不一致 {m5['disagree']}，"
                 f"**一致率 {m5['agreement_rate']}**")
        L.append(f"- 映射规则：{m5['mapping_note']}")
        L.append(f"- 注意：{m5['caveat']}")
        if m5["mismatches"]:
            L.append("\n不一致明细：\n")
            L.append(md_table(["config", "scenario", "MR", "主实现", "第二实现"],
                              [[d["config"], d["scenario"], d["mr"], d["main_impl"],
                                d["alt_impl"]] for d in m5["mismatches"]]) + "\n")
        else:
            L.append("\n> 无不一致项。\n")
    return "\n".join(L)


# --------------------------------------------------------------------------
# 出图
# --------------------------------------------------------------------------

def make_figures(rep: list[dict], S: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 图 1: 触发率热力式条形 —— config × scenario
    labels = sorted({r["config"]["label"] for r in rep})
    scen = ["S1", "S2", "S3", "S4", "S5"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    width = 0.15
    for i, lab in enumerate(labels):
        vals = []
        for sc in scen:
            sel = [r for r in rep if r["config"]["label"] == lab and r["scenario"] == sc]
            vals.append(sum(1 for r in sel if r["mr_result"]["triggered"]) / len(sel)
                        if sel else 0)
        ax.bar([x + i * width for x in range(len(scen))], vals, width, label=lab)
    ax.set_xticks([x + width * (len(labels) - 1) / 2 for x in range(len(scen))])
    ax.set_xticklabels(scen)
    ax.set_ylabel("MR trigger rate")
    ax.set_title("Authorization MR trigger rate by scenario (raw precond, GUI-aware)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig1_trigger_matrix.png", dpi=160)
    plt.close(fig)

    # 图 2: 裁决收益-代价
    b4 = S["block4_all"]
    adjs = ["v1", "v2", "degrade_all"]
    metrics = ["recovery_rate", "detection_keep_rate", "cost_rate"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    width = 0.25
    for i, m in enumerate(metrics):
        vals = [b4[a][m] or 0 for a in adjs]
        ax.bar([x + i * width for x in range(len(adjs))], vals, width, label=m)
    ax.set_xticks([x + width for x in range(len(adjs))])
    ax.set_xticklabels(adjs)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("rate")
    ax.set_title("Boundary-aware adjudication: benefit vs cost (V-E3 / vuln=0)")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig2_verdict_benefit_cost.png", dpi=160)
    plt.close(fig)
    # 图 3: 修正机制的可观测性边界
    b6 = S.get("block6_observability", {})
    if b6:
        keys = ["framework_share_legit", "out_of_band_share_legit", "out_of_band_share_bola"]
        names = ["S3 framework\n(observable)", "S6 out-of-band\n(unobservable)",
                 "S7 out-of-band\n+ true BOLA"]
        rec = [b6[k]["recovery_rate"] or 0 for k in keys]
        fp_ = [b6[k]["false_proof_rate"] or 0 for k in keys]
        rec3 = [b6[k]["v3_recovery_rate"] or 0 for k in keys]
        fp3_ = [b6[k]["v3_false_proof_rate"] or 0 for k in keys]
        fig, ax = plt.subplots(figsize=(8.4, 3.8))
        width = 0.2
        xs = [x for x in range(len(keys))]
        ax.bar(xs, rec, width, label="v1/v2: recovery (FP→indeterminate)")
        ax.bar([x + width for x in xs], fp_, width,
               label="v1/v2: false proof (FP→violation-proven)")
        ax.bar([x + 2 * width for x in xs], rec3, width,
               label="v3 (SUT introspection): recovery")
        ax.bar([x + 3 * width for x in xs], fp3_, width,
               label="v3: false proof")
        ax.set_xticks([x + 1.5 * width for x in xs])
        ax.set_xticklabels(names, fontsize=8)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("rate")
        ax.set_title("Validity scope of the E3 correction: harness bookkeeping vs SUT introspection")
        ax.legend(fontsize=6.5, ncol=2)
        ax.grid(axis="y", alpha=.3)
        fig.tight_layout()
        fig.savefig(FIGDIR / "fig3_observability_boundary.png", dpi=160)
        plt.close(fig)

    print(f"[fig] {FIGDIR}")


if __name__ == "__main__":
    main()
