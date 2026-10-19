# -*- coding: utf-8 -*-
"""
R1.8：Gogs 的按渠道混淆矩阵（渠道标签来自独立台账，不来自被测自省面）
====================================================================
审稿意见 R1.8 要求按渠道拆分的混淆矩阵，区分直接成员、团队继承、管理员授予、
公开可见与带外共享。原稿以「Gogs API 不输出渠道细分」为由没有做；该理由不成立：
渠道标签是**授权台账**的属性（entitlement.py 从拓扑配置 + 成文继承规则 + 带外
变更事件推出，从不读探针响应），不是被测自省面的输出。Gogs 真正缺的是
`/collaborators/{u}/permission` 这个逐对象成员路由，它决定的是**自省面能否
看见某种授予**，不是渠道能否被标注。

本脚本从既有 raw 记录重建该矩阵，不重启实例、不改原始数据：

输入（实测产物）：
  * experiments/real_system/results/gogs_real_system.json —— run_gogs.py 的产物
      - phaseE_cells：每格带 expected_channel / expected_basis（台账侧）、
        observed_effect（E）、introspection_*（oracle 侧）

输出：
  * 04_绘图与分析/results/gogs_channel_numbers.tex —— 宏定义（\\GgCh*）
  * 04_绘图与分析/results/gogs_channel_table.tex   —— 双面板表（booktabs）
  * stdout: 人读小结

设计约束：
  1. 行标签取台账的 expected_channel（最强授予渠道）。一个格子的
     expected_basis 可能含多条规则；多渠道重叠格按「最强优先」计入一行，
     并在宏里单独披露重叠格数，保证各行相加等于格数而非规则数。
  2. 来源轴（面板 b）同样从 expected_basis 的规则文本推出，**不用** runner 的
     M6_provenance 启发式桶：该桶把「非 alice/r1 的 collaborator 授予」也归为
     out_of_band（3 格），与台账矛盾。脚本对 M6 归因做交叉核对：在 oracle
     假阴性这 17 格上两者必须一致（8/5/4），否则报错退出。
  3. 任何未识别的规则字符串直接失败，不静默落桶。
  4. snapshot 与 live 两种读法都算；若边际计数不一致，报错退出。

用法:
  python analysis/ingest_gogs_channel.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # 3区论文/
RS = ROOT / "experiments" / "real_system" / "results"
OUT = HERE.parent / "results"

GOGS_JSON = RS / "gogs_real_system.json"

# 面板 (a) 行序：与 temporal_channel_table.tex 保持同一读序
CHANNELS = ["site_admin", "public", "team", "collaborator", "none"]
CHANNEL_LABEL = {
    "site_admin": "site administrator",
    "public": "public visibility",
    "team": "team / group",
    "collaborator": "direct collaborator",
    "none": "no channel",
}

# 面板 (b) 来源轴：台账规则文本 -> 机制类别。
#   collaborator：经协作端点授予，逐对象自省面**能**枚举
#   team / public / site_admin： respectively 团队继承、仓库可见性开关、
#       站点管理员身份，都不在逐对象协作端点里
SOURCE_ORDER = ["collaborator", "team", "public", "site_admin", "none"]
SOURCE_LABEL = {
    "collaborator": "direct collaborator (collaboration endpoint)",
    "team": "team membership (inherited)",
    "public": "repository visibility flag",
    "site_admin": "site-administrator status",
    "none": "no grant recorded",
}

# 已记录的自省面探测（api_surface_probe）：用来说明白区是「选中的自省面」的属性，
# 不是整个 API 的属性。路径 -> 宏名。
PROBE_PATHS = [
    ("/api/v1/repos/{o}/{r}/collaborators/{u}/permission", "GgChProbePermSuffix"),
    ("/api/v1/repos/{o}/{r}/collaborators/{u}", "GgChProbeCollabGet"),
    ("/api/v1/teams/{id}/members/{u}", "GgChProbeTeamMember"),
    ("/api/v1/orgs/{org}/teams", "GgChProbeOrgTeams"),
]

# 台账规则文本 -> (渠道, 来源)。规则文本是 entitlement.py 的 rule chain，
# 只认这几个成文规则；出现新字符串就失败，不猜。
RULE_MAP = [
    (re.compile(r"collaborator (read|write)"), "collaborator"),
    (re.compile(r"team \S+ (read|write)"), "team"),
    (re.compile(r"site administrator"), "site_admin"),
    (re.compile(r"\S+ is public"), "public"),
    (re.compile(r"no granting channel for (read|write)"), "none"),
]


def esc(s: str) -> str:
    return s.replace("_", "\\_")


def rule_to_channel(rule: str) -> str:
    for pat, ch in RULE_MAP:
        if pat.search(rule):
            return ch
    raise SystemExit(f"[FATAL] 未识别的台账规则文本: {rule!r}；"
                     "若是新增规则，请先更新 RULE_MAP 再出数")


# 渠道强度序（用于多渠道重叠格取最强）；与 CHANNELS 的权威读序一致
STRENGTH = {ch: i for i, ch in enumerate(CHANNELS)}


def primary_channel(cell: dict) -> str:
    """台账自身已给出 expected_channel（最强授予渠道）；这里与规则链交叉核对。"""
    declared = cell["expected_channel"]
    chans = [rule_to_channel(r) for r in cell["expected_basis"]]
    if not chans:
        raise SystemExit(f"[FATAL] {cell['object']}|{cell['subject']} 的 "
                         "expected_basis 为空")
    strongest = min(chans, key=lambda ch: STRENGTH[ch])
    if declared != strongest:
        raise SystemExit(
            f"[FATAL] 渠道标签不一致: {cell['object']}|{cell['subject']} "
            f"台账写 {declared}，规则链推出 {strongest}（{cell['expected_basis']}）")
    return declared


def says_none(cell: dict) -> bool:
    """oracle 判「无权限」= permission=='none'，或协作端点 404。
    与 ingest_gogs.py / run_gogs.py 同一规则，从同样字段重推。"""
    pm = cell["introspection_permission"]
    st = cell["introspection_status"]
    return pm == "none" or (pm is None and st == 404)


def oracle_answer(cell: dict) -> str:
    """O：allow / deny / no_answer（不可读即无回答）。"""
    if not cell["introspection_readable"]:
        return "no_answer"
    return "deny" if says_none(cell) else "allow"


def matrix(cells: list[dict]) -> dict:
    """渠道 x E x O，外加来源轴与重叠披露。"""
    rows = {ch: Counter() for ch in CHANNELS}
    src = {s: Counter() for s in SOURCE_ORDER}
    multi = 0
    for c in cells:
        ch = primary_channel(c)
        e = c["observed_effect"]
        o = oracle_answer(c)
        rows[ch][(e, o)] += 1
        # 来源轴：同样按最强优先计入一行，保证各行相加等于格数
        chans = [rule_to_channel(r) for r in c["expected_basis"]]
        src[min(chans, key=lambda x: STRENGTH[x])][(e, o)] += 1
        if len(chans) > 1:
            multi += 1
    return {"channel": rows, "source": src, "multi_basis": multi}


def col(row: Counter, e: str, o: str) -> int:
    return row.get((e, o), 0)


def emit_table(m: dict, live: dict, cells: dict) -> str:
    L = []
    L.append("% 由 analysis/ingest_gogs_channel.py 自动生成 —— 勿手改")
    L.append("% 来源: experiments/real_system/results/gogs_real_system.json (phaseE_cells)")
    L.append(r"\begin{table*}[t]")
    L.append(r"\centering")
    L.append(r"\caption{Oracle fidelity by granting channel on Gogs \GgVersion{}, over the "
             r"same \GgChCells{} snapshot cells as Table~\ref{tab:gogs-cross}. "
             r"Channel labels come from the entitlement ledger, which is built from the lab "
             r"topology, the documented inheritance rules and the recorded out-of-band grant "
             r"events, and never from a probe response; they are therefore available even "
             r"though the product's own API exposes no per-object membership route that "
             r"separates direct from inherited grants. \emph{allow} and \emph{deny} count "
             r"cells where the owner-vantage introspection surface agrees with the ledger; "
             r"\emph{f.\ deny} is the surface answering deny on a cell the ledger allows; "
             r"\emph{unans.} counts cells with no definite answer. On this product the "
             r"observed effect $E$ coincides with the ledger entitlement on every cell, so "
             r"the same table reads as $E{\times}O$. Panel~(b) re-groups the same cells by "
             r"the mechanism that produced the entitlement: the owner-vantage per-object "
             r"collaboration route that the oracle consults represents direct collaborators "
             r"only, so team membership, the repository visibility flag and "
             r"site-administrator status are invisible to it. Whether some other endpoint in "
             r"the same API could represent those grants is a separate question, and not the "
             r"one a surface-gated adjudicator asks. "
             r"One cell carries two ledger rules (site administrator and public visibility) "
             r"and is counted once, under the stronger rule, so the rows sum to "
             r"\GgChCells{} cells rather than to the \GgChRules{} recorded rules.}")
    L.append(r"\label{tab:gogs-channel}")
    L.append(r"\small")
    L.append(r"\begin{tabular}{lrrrrr}")
    L.append(r"\toprule")
    L.append(r"\multicolumn{6}{l}{(a) by granting channel (ledger)}\\")
    L.append(r"\addlinespace[2pt]")
    L.append(r"Channel & cells & allow & deny & f.\ deny & unans. \\")
    L.append(r"\addlinespace[2pt]")
    for ch in CHANNELS:
        row = m["channel"][ch]
        n = sum(row.values())
        L.append(f"{CHANNEL_LABEL[ch]} & {n} & "
                 f"{col(row, 'allow', 'allow')} & {col(row, 'deny', 'deny')} & "
                 f"{col(row, 'allow', 'deny')} & {col(row, 'deny', 'no_answer') + col(row, 'allow', 'no_answer')} \\\\")
    L.append(r"\addlinespace[2pt]")
    tot = m["channel"]
    tn = sum(sum(r.values()) for r in tot.values())
    L.append(f"\\emph{{total}} & {tn} & "
             f"{sum(col(r, 'allow', 'allow') for r in tot.values())} & "
             f"{sum(col(r, 'deny', 'deny') for r in tot.values())} & "
             f"{sum(col(r, 'allow', 'deny') for r in tot.values())} & "
             f"{sum(col(r, 'allow', 'no_answer') + col(r, 'deny', 'no_answer') for r in tot.values())} \\\\")
    L.append(r"\midrule")
    L.append(r"\multicolumn{6}{l}{(b) by granting mechanism (same cells)}\\")
    L.append(r"\addlinespace[2pt]")
    L.append(r"Mechanism & cells & agree & f.\ allow & f.\ deny & f.\ deny (\%) \\")
    L.append(r"\addlinespace[2pt]")
    for s in SOURCE_ORDER:
        row = m["source"][s]
        n = sum(row.values())
        agree = col(row, "allow", "allow") + col(row, "deny", "deny")
        fa = col(row, "deny", "allow")
        fd = col(row, "allow", "deny")
        pct = f"{100.0 * fd / n:.2f}" if n else "--"
        L.append(f"{SOURCE_LABEL[s]} & {n} & {agree} & {fa} & {fd} & {pct} \\\\")
    L.append(r"\bottomrule")
    L.append(r"\end{tabular}")
    L.append(r"\end{table*}")
    return "\n".join(L) + "\n"


def emit_macros(v: dict) -> str:
    L = [
        "% 由 analysis/ingest_gogs_channel.py 自动生成 —— 勿手改",
        "% 来源: experiments/real_system/results/gogs_real_system.json (phaseE_cells)",
        "",
        f"\\newcommand{{\\GgChCells}}{{{v['cells']}}}",
        f"\\newcommand{{\\GgChReadings}}{{{v['readings']}}}",
        f"\\newcommand{{\\GgChRules}}{{{v['rules']}}}",
        f"\\newcommand{{\\GgChMultiBasis}}{{{v['multi_basis']}}}",
    ]
    for ch in CHANNELS:
        L.append(f"\\newcommand{{\\GgCh{ch.title().replace('_', '')}}}{{{v['channel_n'][ch]}}}")
        row = v["channel"][ch]
        L.append(f"\\newcommand{{\\GgCh{ch.title().replace('_', '')}Agree}}"
                 f"{{{col(row, 'allow', 'allow') + col(row, 'deny', 'deny')}}}")
        L.append(f"\\newcommand{{\\GgCh{ch.title().replace('_', '')}FalseDeny}}"
                 f"{{{col(row, 'allow', 'deny')}}}")
    for s in SOURCE_ORDER:
        row = v["source"][s]
        agree = col(row, "allow", "allow") + col(row, "deny", "deny")
        wrong = col(row, "allow", "deny") + col(row, "deny", "allow")
        L.append(f"\\newcommand{{\\GgChSrc{s.title().replace('_', '')}}}{{{sum(row.values())}}}")
        L.append(f"\\newcommand{{\\GgChSrc{s.title().replace('_', '')}Agree}}{{{agree}}}")
        L.append(f"\\newcommand{{\\GgChSrc{s.title().replace('_', '')}Wrong}}{{{wrong}}}")
    L += [
        f"\\newcommand{{\\GgChAgree}}{{{v['agree']}}}",
        f"\\newcommand{{\\GgChFalseDeny}}{{{v['false_deny']}}}",
        f"\\newcommand{{\\GgChFalseAllow}}{{{v['false_allow']}}}",
        f"\\newcommand{{\\GgChUnans}}{{{v['unans']}}}",
        f"\\newcommand{{\\GgChLiveFalseDeny}}{{{v['live_false_deny']}}}",
        f"\\newcommand{{\\GgChLiveAgree}}{{{v['live_agree']}}}",
        f"\\newcommand{{\\GgChFnSiteAdminLedger}}{{{v['fn_ledger']['site_admin']}}}",
        f"\\newcommand{{\\GgChFnPublicLedger}}{{{v['fn_ledger']['public']}}}",
        f"\\newcommand{{\\GgChFnTeamLedger}}{{{v['fn_ledger']['team']}}}",
        f"\\newcommand{{\\GgChFnCollabLedger}}{{{v['fn_ledger']['collaborator']}}}",
    ]
    L += v["probe_macros"]
    return "\n".join(L) + "\n"


def main() -> int:
    if not GOGS_JSON.exists():
        raise SystemExit(f"缺产物: {GOGS_JSON}")
    d = json.loads(GOGS_JSON.read_text(encoding="utf-8"))
    cells = d["phaseE_cells"]
    snap = [c for c in cells if c["reading"] == "snapshot"]
    live = [c for c in cells if c["reading"] == "live"]
    if len(snap) != len(live):
        raise SystemExit(f"[FATAL] snapshot {len(snap)} 格 != live {len(live)} 格")

    ms, ml = matrix(snap), matrix(live)

    # 两种读法的渠道分解必须一致，否则说明矩阵依赖读法，不能合并陈述
    for ch in CHANNELS:
        if ms["channel"][ch] != ml["channel"][ch]:
            raise SystemExit(f"[FATAL] 渠道 {ch} 在 snapshot/live 下分解不一致: "
                             f"{dict(ms['channel'][ch])} vs {dict(ml['channel'][ch])}")

    # 表题声称「E 与台账在本产品每格一致」；这是可验证的前提，先断言再写题
    for c in cells:
        if c["observed_effect"] != c["expected_entitlement"]:
            raise SystemExit(
                f"[FATAL] E 与台账不一致: {c['object']}|{c['subject']} "
                f"E={c['observed_effect']} 台账={c['expected_entitlement']}；"
                "表题与 E×O 读法都需要改写")

    agree = sum(col(r, "allow", "allow") + col(r, "deny", "deny")
                for r in ms["channel"].values())
    false_deny = sum(col(r, "allow", "deny") for r in ms["channel"].values())
    false_allow = sum(col(r, "deny", "allow") for r in ms["channel"].values())
    unans = sum(col(r, "allow", "no_answer") + col(r, "deny", "no_answer")
                for r in ms["channel"].values())

    # 与 M6_provenance 启发式归因交叉核对：在 oracle 假阴性格上必须同数。
    # M6 的 else 桶会把「非 alice/r1 的 collaborator 授予」误记为 out_of_band，
    # 因此本表的行标签一律取自台账；这个核对只是证明已发布的 FN 归因未受其害。
    m6 = {(r["cell"], r["subject"]): r["channel"] for r in d["M6_provenance"]}
    M6MAP = {"implicit_site_admin": "site_admin", "implicit_public": "public",
             "out_of_band": "team", "in_band_share": "collaborator", "none": "none"}
    fn_cells = [c for c in snap
                if c["introspection_readable"] and says_none(c) and c["authorized"]]
    fn_ledger = Counter(primary_channel(c) for c in fn_cells)
    fn_m6 = Counter(M6MAP.get(m6.get((c["object"], c["subject"]), "?"), "?")
                    for c in fn_cells)
    if dict(fn_ledger) != dict(fn_m6):
        raise SystemExit(f"[FATAL] 台账归因 {dict(fn_ledger)} 与 M6 归因 "
                         f"{dict(fn_m6)} 不一致；先查清再出数")

    rules = sum(len(c["expected_basis"]) for c in snap)
    # 已记录的自省面探测状态码（同一条 raw 记录，不新开探测）
    probe = {r["path"]: r["status"] for r in d.get("api_surface_probe", [])}
    probe_macros = []
    for path, name in PROBE_PATHS:
        if path not in probe:
            raise SystemExit(f"[FATAL] api_surface_probe 缺少 {path}；"
                             "正文要引用它的状态码，不能改述")
        probe_macros.append(f"\\newcommand{{\\{name}}}{{{probe[path]}}}")
    vals = {
        "cells": len(snap),
        "readings": len({c["reading"] for c in cells}),
        "rules": rules,
        "multi_basis": ms["multi_basis"],
        "channel": ms["channel"],
        "channel_n": {ch: sum(ms["channel"][ch].values()) for ch in CHANNELS},
        "source": ms["source"],
        "agree": agree, "false_deny": false_deny,
        "false_allow": false_allow, "unans": unans,
        "live_agree": sum(col(r, "allow", "allow") + col(r, "deny", "deny")
                          for r in ml["channel"].values()),
        "live_false_deny": sum(col(r, "allow", "deny") for r in ml["channel"].values()),
        "fn_ledger": {ch: fn_ledger.get(ch, 0) for ch in CHANNELS},
        "probe_macros": probe_macros,
    }

    (OUT / "gogs_channel_numbers.tex").write_text(emit_macros(vals), encoding="utf-8")
    (OUT / "gogs_channel_table.tex").write_text(
        emit_table(ms, ml, vals), encoding="utf-8")

    print(f"Gogs {d['meta'].get('gogs_version', '?')} 渠道矩阵：{len(snap)} 格 x "
          f"{vals['readings']} 种读法")
    for ch in CHANNELS:
        n = vals["channel_n"][ch]
        if not n:
            continue
        row = ms["channel"][ch]
        print(f"  {CHANNEL_LABEL[ch]:22s} n={n:3d} 一致="
              f"{col(row, 'allow', 'allow') + col(row, 'deny', 'deny'):3d} "
              f"假拒绝={col(row, 'allow', 'deny'):3d}")
    print(f"  合计：一致 {agree}，假拒绝 {false_deny}，假允许 {false_allow}，"
          f"无回答 {unans}")
    print(f"  live 读法：一致 {vals['live_agree']}，假拒绝 {vals['live_false_deny']}")
    print(f"  多渠道重叠格 {ms['multi_basis']} 个（记录规则共 {rules} 条 > "
          f"{len(snap)} 格，按最强优先计一行）")
    print(f"  FN 渠道归因（台账）: {dict(fn_ledger)}；M6 交叉核对一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
