"""
M2 补充分析 · oracle 缺失层的检测增益（审稿人意见 M2 的核心）
====================================================================
背景（为什么要算这一层）:
    审稿意见 M2 指出：Table 1 中 v2 recall 0.99 与 direct_observe recall 0.50 形成刺眼
    不对称，而"MR 步骤无增量收益"的结论只在 v3 vs direct_observe 之间成立。MR 步骤
    （v1/v2）不需要 oracle，其全部潜在增量价值恰好落在 **oracle 缺失** 的那一层——
    即蜕变测试存在的理由所在的那一层。本文层对该层做**检测**（detection）而非
    **裁决**（adjudication）分析，并把法官(+/-)两边都报出来。

口径一致性（关键）:
    * 每条记录的 v1/v2/v3/degrade_all 告警判定、direct_only / direct_observe 判定，
      均与 compute_all.py Block 9 逐行一致（同为 violation-proven 判据 + probe_cache）。
    * 分层变量用 config.introspection（on/off）；已验证它等价于 probe 返回
      unavailable（156 条完全重合），不存在替代变量歧义。
    * **全部 perturbation 不做**：不重新跑实验，只对既有原始记录做新的聚合。

硬约束:
    * 正文禁止手敲数字 → 本脚本把全部结果写为 results/m2_stratum.tex 宏。
    * 两条分层之和必须与已落盘 JSON 的池化计数完全相同（check），否则报错。

★ 分层变量的选择（审稿人必查，勿省）:
    一开始尝试用 config.introspection（on/off）分层，被脚本自身的校验拦下：
    introspection=on 的记录里仍有 108 条 probe 返回 unavailable。追查后确认原因——
    两个 V-noE3-* 配置在 config 里标记为 introspection="on"，但其 probe 条目实为
    unavailable，即**配置标记不等于 oracle 实际可读**。既然决定 direct_* 方法能否行动
    的变量是 probe 返回值（compute_all.py Block 9 亦然），分层变量必须为
    **有效可读性**（probe_state == "unavailable" 与否），而非配置开关。
    两层人口因此为：可读 312 条（4 个 V-E3-* 配置）／不可读 264 条
    （2 个 -nointro 配置 156 条 + 2 个 V-noE3-* 配置 108 条）。

用法: python ingest_m2_stratum.py
输出: results/m2_stratum.json, results/m2_stratum.tex
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
RES = PROJ / "experiments" / "results"
OUT = HERE.parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

Z = 1.959963985  # 95%
PROBLEMS: list[str] = []


# ---------------------------------------------------------------- 统计工具

def wilson(k: int, n: int, z: float = Z):
    """Wilson score interval（与 compute_all.py 同实现）。n=0 时返回 (None,None,None)。"""
    if n == 0:
        return None, None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(p, 4), round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)


def prf(t: dict) -> tuple:
    tp, fp, fn, tn = (t.get("TP", 0), t.get("FP", 0), t.get("FN", 0), t.get("TN", 0))
    prec = round(tp / (tp + fp), 4) if tp + fp else None
    rec = round(tp / (tp + fn), 4) if tp + fn else None
    f1 = round(2 * prec * rec / (prec + rec), 4) if prec and rec else None
    return prec, rec, f1


def check(name: str, got, want):
    """发现即报错：不允许"正文一个数、数据另一个数"。"""
    if got != want:
        PROBLEMS.append(f"[FAIL] {name}: 由原始记录重算={got!r} ≠ 已落盘={want!r}")
        print(f"  !! {name}: {got!r} != {want!r}")
    else:
        print(f"  ok {name} = {got!r}")


def fmt(x, nd: int = 4) -> str:
    return "---" if x is None else f"{x:.{nd}f}"


# ---------------------------------------------------------------- 载入原始记录

recs = [json.loads(l) for l in (RES / "raw_matrix.jsonl").read_text(encoding="utf-8").splitlines()]
probe = json.loads((RES / "ablation_direct.json").read_text(encoding="utf-8"))["probe_cache"]
stored_direct = json.loads((RES / "ablation_direct.json").read_text(encoding="utf-8"))["tally"]
stored_obs = json.loads((RES / "ablation_direct_observe.json").read_text(encoding="utf-8"))["tally"]

print(f"[载入] raw_matrix.jsonl n={len(recs)}; probe_cache keys={len(probe)}")


def probe_state(r: dict) -> str:
    """与 compute_all.py Block 9 完全相同的 oracle 读数口径。"""
    return probe.get(f'{r["config"]["label"]}|{r["scenario"]}', {}).get(r["action"]["op"], "unavailable")


def confused(truth: str, alarm: bool) -> str:
    return ("TP" if alarm else "FN") if truth == "bola" else ("FP" if alarm else "TN")


# ---------------------------------------------------------------- 逐条构造（与 Block 9 同口径）

ADJ = ("v1", "v2", "v3", "degrade_all", "direct_only", "direct_observe")

def alm(r: dict) -> dict:
    st = probe_state(r)
    obs200 = bool(r["truth"]["app_allowed"])
    a = {k: r["verdicts"][k]["verdict"] == "violation-proven"
         for k in ("v1", "v2", "v3", "degrade_all")}
    a["direct_only"] = (st == "none")
    a["direct_observe"] = (st == "none") and obs200
    if st == "unavailable":
        a["direct_only"] = False
        a["direct_observe"] = False
    return a


def tally_over(sel: list[dict], extra_baselines: bool = False) -> dict:
    """对给定记录子集，按 (方法 → TP/FP/FN/TN) 汇总。"""
    out = {a: defaultdict(int) for a in ADJ}
    if extra_baselines:
        out["always_alarm"] = defaultdict(int)
        out["obs_success"] = defaultdict(int)
    for r in sel:
        truth = r["truth"]["truth"]
        a = alm(r)
        for k in ADJ:
            out[k][confused(truth, a[k])] += 1
        if extra_baselines:
            out["always_alarm"][confused(truth, True)] += 1
            # obs_success：无 oracle、无爬取模型、只用观测到的访问结果
            out["obs_success"][confused(truth, bool(r["truth"]["app_allowed"]))] += 1
    return {k: dict(v) for k, v in out.items()}


def enrich(t: dict) -> dict:
    prec, rec, f1 = prf(t)
    tp, fp, fn, tn = (t.get("TP", 0), t.get("FP", 0), t.get("FN", 0), t.get("TN", 0))
    n_bola, n_norm = tp + fn, fp + tn
    return {**{k: t.get(k, 0) for k in ("TP", "FP", "FN", "TN")},
            "precision": prec, "recall": rec, "f1": f1,
            "precision_ci": list(wilson(tp, tp + fp)[1:]),
            "recall_ci": list(wilson(tp, n_bola)[1:]),
            "prevalence": round(n_bola / (n_bola + n_norm), 4) if n_bola + n_norm else None,
            "n_bola": n_bola, "n_normal": n_norm, "n": n_bola + n_norm}


# ---------------------------------------------------------------- 分层
# 分层变量 = **有效 oracle 可读性**（probe 返回值），不是 config.introspection 开关：
# 后者在两个 V-noE3-* 配置上标记为 on 而 probe 实为 unavailable（见文件头说明）。

readable_recs = [r for r in recs if probe_state(r) != "unavailable"]
unreadable_recs = [r for r in recs if probe_state(r) == "unavailable"]

# 披露：config 标记与实际可读性的分歧规模（若不披露，审稿人会认为是换了一个变量凑结果）
flag_on_but_unavailable = [r for r in unreadable_recs if r["config"]["introspection"] == "on"]
flag_off_but_available = [r for r in readable_recs if r["config"]["introspection"] == "off"]

on_recs, off_recs = readable_recs, unreadable_recs

print(f"[分层] oracle 有效可读 = {len(on_recs)}; 不可读 = {len(off_recs)}; "
      f"合计 = {len(on_recs)+len(off_recs)}")
print(f"[披露] config 标记与有效可读性的分歧: on 但 unavailable = {len(flag_on_but_unavailable)} 条; "
      f"off 但 available = {len(flag_off_but_available)} 条")
check("分层人口守恒", len(on_recs) + len(off_recs), len(recs))
check("分歧均已解释（不可读层里 config=on 的是 V-noE3-* / -nointro 两类）",
      sorted({r["config"]["label"] for r in flag_on_but_unavailable}),
      ["V-noE3-vuln0", "V-noE3-vuln1"])

if PROBLEMS:
    print("\n!! 分层校验未通过，中止。")
    sys.exit(1)

T_on = {k: enrich(v) for k, v in tally_over(on_recs, extra_baselines=True).items()}
T_off = {k: enrich(v) for k, v in tally_over(off_recs, extra_baselines=True).items()}
T_all = {k: enrich(v) for k, v in tally_over(recs).items()}

# 交叉校验：两条分层之和 == 池化 == 已落盘 JSON（口径未曾漂移）
print("[校验] 分层之和 vs 池化 vs 已落盘 JSON")
for m in ADJ:
    for cell in ("TP", "FP", "FN", "TN"):
        s = T_on[m][cell] + T_off[m][cell]
        check(f"pool {m}.{cell} 分层之和", s, T_all[m][cell])
for m in ("v1", "v2", "v3", "degrade_all"):
    for cell in ("TP", "FP", "FN", "TN"):
        check(f"JSON ablation_direct {m}.{cell}", T_all[m][cell], stored_direct[m].get(cell, 0))
# ablation_direct.json 里 direct-only 的键名是 "direct"（非 "direct_only"）
for cell in ("TP", "FP", "FN", "TN"):
    check(f"JSON ablation_direct direct_only.{cell}", T_all["direct_only"][cell],
          stored_direct["direct"].get(cell, 0))
for m in ("v3", "direct_only", "direct_observe"):
    for cell in ("TP", "FP", "FN", "TN"):
        check(f"JSON ablation_direct_observe {m}.{cell}", T_all[m][cell], stored_obs[m].get(cell, 0))

# ---------------------------------------------------------------- M2 核心量

off_bola = T_off["v2"]["n_bola"]
off_norm = T_off["v2"]["n_normal"]
prev_off = T_off["v2"]["prevalence"]

# (a) MR 家族在 oracle 缺失层的**检测**能力 vs 该层的一切 oracle 消费方法（其检测数为 0）
m_off_tp = T_off["v2"]["TP"]
m_off_fp = T_off["v2"]["FP"]
direct_off_tp = T_off["direct_observe"]["TP"]      # 预期 0
always_tp_off = T_off["always_alarm"]["TP"]
always_fp_off = T_off["always_alarm"]["FP"]

# (b) 相对平凡基线（全告警）的精度提升 = lift；相对"仅凭访问结果"基线的净增益
lift_v2 = round(T_off["v2"]["precision"] / prev_off, 4) if prev_off else None
lift_obs = round(T_off["obs_success"]["precision"] / prev_off, 4) if prev_off else None

# (c) MR 相对"仅凭访问结果"增量：在同为非 oracle 的前提下，多检出多少、少误报多少
delta_tp = T_off["v2"]["TP"] - T_off["obs_success"]["TP"]
delta_fp = T_off["v2"]["FP"] - T_off["obs_success"]["FP"]

# (d) 池化 v2 recall 0.99 的来源分解：两层各自的 recall
on_v2_rec, off_v2_rec = T_on["v2"]["recall"], T_off["v2"]["recall"]
on_do_rec, off_do_rec = T_on["direct_observe"]["recall"], T_off["direct_observe"]["recall"]

# (e) 归因：MR 家族相对朴素基线的误报差异落在哪些 scenario（只报计数不算机制）
ATTRIB_SCEN = ("S1", "S2", "S3", "S4", "S5", "S6", "S7")
attrib = {}
for sc in ATTRIB_SCEN:
    sel = [r for r in off_recs if r["scenario"] == sc]
    v2_fp = sum(1 for r in sel if confused(r["truth"]["truth"],
                                           r["verdicts"]["v2"]["verdict"] == "violation-proven") == "FP")
    obs_fp = sum(1 for r in sel if confused(r["truth"]["truth"],
                                            bool(r["truth"]["app_allowed"])) == "FP")
    attrib[sc] = {"n": len(sel), "v2_FP": v2_fp, "obs_success_FP": obs_fp}

# 一致性兜底：归因表的列和必须等于分层汇总（列和不一致即口径漂移）
check("归因合计·记录数", sum(v["n"] for v in attrib.values()), len(off_recs))
check("归因合计·v2 误报", sum(v["v2_FP"] for v in attrib.values()), T_off["v2"]["FP"])
check("归因合计·obs_success 误报",
      sum(v["obs_success_FP"] for v in attrib.values()), T_off["obs_success"]["FP"])

M = {
    "meta": {
        "purpose": "审稿意见 M2：oracle 缺失层的检测增益分析",
        "records_total": len(recs),
        "n_on": len(on_recs), "n_off": len(off_recs),
        "stratum_variable": "config.introspection（已验证 ⟺ probe_state == unavailable）",
        "aggregation": "detection(alarm) 口径：v1/v2/v3/degrade_all 取 violation-proven；"
                       "direct_only / direct_observe 按 compute_all.py Block 9 判定",
        "baselines": {
            "always_alarm": "平凡地板：无条件告警（无非 vote）",
            "obs_success": "朴素黑盒：仅凭观测到的访问成功（无 oracle、无爬取模型）",
        },
        "caveat-partial-isomorphism": (
            "obs_success 与 direct_observe 均消费 app_allowed，而 truth 定义为 "
            "bola ⟺ ¬should_allow ∧ app_allowed ⇒ 二者与真值**部分同构**；"
            "绝对数值不可外推，只能读作『给定同一可观测量的增量』。"),
    },
    "strata": {"on": T_on, "off": T_off, "pooled": T_all},
    "m2_core": {
        "off_true_violations": off_bola,
        "off_normal": off_norm,
        "off_prevalence": prev_off,
        "off_v2_tp": m_off_tp, "off_v2_fp": m_off_fp,
        "off_direct_observe_tp": direct_off_tp,
        "off_always_alarm_tp": always_tp_off, "off_always_alarm_fp": always_fp_off,
        "lift_v2_over_prevalence": lift_v2,
        "lift_obs_success_over_prevalence": lift_obs,
        "delta_tp_v2_minus_obs_success": delta_tp,
        "delta_fp_v2_minus_obs_success": delta_fp,
        "v2_recall_on": on_v2_rec, "v2_recall_off": off_v2_rec,
        "direct_observe_recall_on": on_do_rec, "direct_observe_recall_off": off_do_rec,
    },
    "off_stratum_attribution": attrib,
    "disclosures": {
        "config_flag_is_not_a_proxy": {
            "records": len(flag_on_but_unavailable),
            "labels": sorted({r["config"]["label"] for r in flag_on_but_unavailable}),
            "note": "这些记录 config.introspection=on 但 probe 返回 unavailable；"
                    "故分层变量取 probe 有效可读性，不取配置开关。",
        },
        "partial_isomorphism": (
            "obs_success 与 direct_observe 均消费 app_allowed，而 truth 定义为 "
            "bola ⟺ ¬should_allow ∧ app_allowed ⇒ 二者与真值部分同构；"
            "绝对数值不可外推，只能读作『给定同一可观测量的增量』。"),
    },
}

(OUT / "m2_stratum.json").write_text(json.dumps(M, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------- 控制台报告

print("\n" + "=" * 78)
print("Table A · oracle 缺失层（introspection=off）各方法的检测表现")
print("=" * 78)
hdr = f"{'method':<16}{'TP':>5}{'FP':>5}{'FN':>5}{'TN':>5}{'prec':>8}{'recall':>8}{'F1':>8}"
print(hdr)
for m in list(ADJ) + ["always_alarm", "obs_success"]:
    t = T_off[m]
    print(f"{m:<16}{t['TP']:>5}{t['FP']:>5}{t['FN']:>5}{t['TN']:>5}"
          f"{fmt(t['precision'],2):>8}{fmt(t['recall'],2):>8}{fmt(t['f1'],2):>8}")

print("\n" + "=" * 78)
print("Table B · oracle 可读层（introspection=on）")
print("=" * 78)
print(hdr)
for m in ADJ:
    t = T_on[m]
    print(f"{m:<16}{t['TP']:>5}{t['FP']:>5}{t['FN']:>5}{t['TN']:>5}"
          f"{fmt(t['precision'],2):>8}{fmt(t['recall'],2):>8}{fmt(t['f1'],2):>8}")

print("\n" + "=" * 78)
print("M2 核心量")
print("=" * 78)
print(f"oracle 缺失层: 记录 {len(off_recs)}（真违规 {off_bola}，正常 {off_norm}），"
      f"违规基础率 {fmt(prev_off,4)}")
print(f"  v2              检出 {m_off_tp}/{off_bola}，误报 {m_off_fp}，precision {fmt(T_off['v2']['precision'],4)}，"
      f"recall {fmt(T_off['v2']['recall'],4)}")
print(f"  direct_observe  检出 {direct_off_tp}/{off_bola}（无 oracle 可用 ⇒ 只能弃权）")
print(f"  always_alarm    检出 {always_tp_off}/{off_bola}，误报 {always_fp_off}（平凡地板）")
print(f"  obs_success     检出 {T_off['obs_success']['TP']}/{off_bola}，"
      f"误报 {T_off['obs_success']['FP']}，precision {fmt(T_off['obs_success']['precision'],4)}")
print(f"  精度提升 lift（v2 vs 基础率）      : {fmt(lift_v2,3)}×")
print(f"  精度提升 lift（obs_success vs 基础率）: {fmt(lift_obs,3)}×")
print(f"  净增量 v2 − obs_success            : TP {delta_tp:+d}, FP {delta_fp:+d}")
print(f"  v2 recall  可读层 {fmt(on_v2_rec,4)} / 缺失层 {fmt(off_v2_rec,4)}")
print(f"  DO  recall  可读层 {fmt(on_do_rec,4)} / 缺失层 {fmt(off_do_rec,4)}")

print("\n" + "=" * 78)
print("Table C · 缺失层误报的 scenario 归因（MR 的增量到底买了什么）")
print("=" * 78)
print(f"{'scen':<6}{'n':>6}{'v2_FP':>8}{'obs_success_FP':>18}{'差（MR 省下的误报）':>22}")
for sc in ATTRIB_SCEN:
    v = attrib[sc]
    print(f"{sc:<6}{v['n']:>6}{v['v2_FP']:>8}{v['obs_success_FP']:>18}"
          f"{v['obs_success_FP'] - v['v2_FP']:>22}")
print(f"{'TOTAL':<6}{sum(v['n'] for v in attrib.values()):>6}"
      f"{sum(v['v2_FP'] for v in attrib.values()):>8}"
      f"{sum(v['obs_success_FP'] for v in attrib.values()):>18}"
      f"{sum(v['obs_success_FP']-v['v2_FP'] for v in attrib.values()):>22}")

# ---------------------------------------------------------------- TeX 宏

_seen: dict[str, str] = {}


def tex_name(s: str) -> str:
    out = "".join(ch for ch in s if ch.isalnum())
    for a, b in (("0", "Zero"), ("1", "One"), ("2", "Two"), ("3", "Three"), ("4", "Four"),
                 ("5", "Five"), ("6", "Six"), ("7", "Seven"), ("8", "Eight"), ("9", "Nine")):
        out = out.replace(a, b)
    return out


lines_tex: list[str] = []
lines_tex.append("% 由 analysis/ingest_m2_stratum.py 自动生成 —— 请勿手改")
lines_tex.append("% 审稿意见 M2：oracle 缺失层（introspection=off）的检测增益分析")
lines_tex.append("% 口径与 compute_all.py Block 9 逐条一致；分层之和已与已落盘 JSON 交叉校验")


def cmd(name: str, val):
    nm = "Mii" + tex_name(name)
    if nm in _seen:
        raise RuntimeError(f"宏名冲突：{nm} <- {name} & {_seen[nm]}")
    _seen[nm] = name
    lines_tex.append(f"\\newcommand{{\\{nm}}}{{{val}}}")


# 全部:,///  //// (0)
cmd("NOn", len(on_recs))
cmd("NOff", len(off_recs))
cmd("NTotal", len(recs))

for strat, T in (("On", T_on), ("Off", T_off), ("Pool", T_all)):
    lines_tex.append(f"% ---- {strat} 层 ----")
    methods = list(ADJ) + (["always_alarm", "obs_success"] if strat != "Pool" else [])
    for m in methods:
        mn = "".join(w.capitalize() for w in m.split("_"))
        t = T[m]
        for cell in ("TP", "FP", "FN", "TN"):
            cmd(f"{strat}{mn}{cell}", t[cell])
        cmd(f"{strat}{mn}Prec", fmt(t["precision"]))
        cmd(f"{strat}{mn}Rec", fmt(t["recall"]))
        cmd(f"{strat}{mn}Fone", fmt(t["f1"]))

lines_tex.append("% ---- M2 核心导出量 ----")
cmd("OffNBola", off_bola)
cmd("OffNNormal", off_norm)
cmd("OffPrevalence", fmt(prev_off))
cmd("OffPrevalencePct", fmt(prev_off * 100, 2))
cmd("LiftVTwo", fmt(lift_v2, 3))
cmd("LiftObsSuccess", fmt(lift_obs, 3))
cmd("DeltaTPVTwoMinusObsSuccess", delta_tp)
cmd("DeltaFPVTwoMinusObsSuccess", delta_fp)

lines_tex.append("% ---- 缺失层误报的 scenario 归因 ----")
_scn = {"S1": "One", "S2": "Two", "S3": "Three", "S4": "Four", "S5": "Five", "S6": "Six", "S7": "Seven"}
for sc in ATTRIB_SCEN:
    v = attrib[sc]
    cmd(f"OffScen{_scn[sc]}N", v["n"])
    cmd(f"OffScen{_scn[sc]}VTwoFP", v["v2_FP"])
    cmd(f"OffScen{_scn[sc]}ObsSuccessFP", v["obs_success_FP"])
cmd("OffAttribSavedFPTotal", sum(v["obs_success_FP"] - v["v2_FP"] for v in attrib.values()))

lines_tex.append("% ---- 披露：配置标记不是有效可读性的代理 ----")
cmd("FlagOnButUnavailable", len(flag_on_but_unavailable))
cmd("FlagOffButAvailable", len(flag_off_but_available))

(OUT / "m2_stratum.tex").write_text("\n".join(lines_tex) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- 收尾

print("\n" + "=" * 78)
if PROBLEMS:
    print(f"!! 校验失败 {len(PROBLEMS)} 项：")
    for p in PROBLEMS:
        print("  " + p)
    sys.exit(1)
print("全部交叉校验通过。输出: results/m2_stratum.json, results/m2_stratum.tex")
