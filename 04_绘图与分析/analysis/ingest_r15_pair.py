"""R1.5 配对实验 → LaTeX 宏（正文只引宏，不手敲数字）。

输入：results/r15_pair.json（由 run_r15_pair.py 生成）
输出：results/r15_pair_numbers.tex

本脚本不信任 ``arms`` 里的汇总布尔：每一臂的
``in_snapshot_crawl`` / ``in_recrawl`` / ``readable`` / ``repo_status`` /
``file_status`` / ``file_sha`` 都要由**原始记录**独立复算一遍
（phaseB_snapshot.urls、phaseD_recrawl.urls、probes、steps），
再与 ``arms`` 和 ``totals`` 对账。对不上就 fail，避免汇总被改写而无人发现。

断言：
  * 三臂都在快照里不可见（否则不能算"快照后授予"）；
  * 每臂实际可读（repo 200 且 README 200 且有内容哈希），且与 probes 一致；
  * 报警 = 「未出现在该次爬取的 urls 里」且「实际可读」且「主体非所有者」；
  * 重爬修复的臂，其对象必须出现在重爬 urls 里；未修复的臂必须不在；
  * totals 由逐臂重算，且与 arms 的逐项布尔一致；
  * 建库/授权步骤全部 2xx（否则该臂不成立）。
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
RESULTS = HERE.parent / "results"
SRC = PROJ / "experiments" / "real_system" / "results" / "r15_pair.json"
data = json.loads(SRC.read_text(encoding="utf-8"))

arms = data["arms"]
snapshot_urls = set(data["phaseB_snapshot"]["urls"])
recrawl_urls = set(data["phaseD_recrawl"]["urls"])
probes = data["probes"]
steps = data["steps"]

assert len(arms) == 3, f"期望三臂，实得 {len(arms)}"
assert set(probes) == {a["arm"] for a in arms}, "probes 的臂集合与 arms 不一致"

# 主体对三个对象都没有所有者权限：这是"报警"的第三个合取项。
# 记录里没有显式字段，故按对象名手工确认一次（对象名即 <owner>/<repo>）。
SUBJECT = "bob"
for a in arms:
    assert not a["object"].split("/")[0] == SUBJECT, \
        f"{a['arm']} 的对象属于被测主体自己，报警语义不成立"

# ---- 1. 拓扑与授权步骤必须全部成功 ----
assert steps, "steps 为空，无法核对建库/授权是否成立"
for s in steps:
    assert s["error"] is None, f"步骤失败: {s}"
    assert 200 <= s["status"] < 300, f"步骤非 2xx: {s}"

# ---- 2. 逐臂由原始记录复算布尔，再与 arms 对账 ----
for a in arms:
    arm, obj = a["arm"], a["object"]
    p = probes[arm]

    in_snap = obj in snapshot_urls
    in_re = obj in recrawl_urls
    readable = (p["allowed"] and p["repo_status"] == 200
                and p["file_status"] == 200 and bool(p["file_sha"]))

    assert a["in_snapshot_crawl"] == in_snap, \
        f"{arm} 快照可见性与 phaseB_snapshot.urls 不符（{a['in_snapshot_crawl']} vs {in_snap}）"
    assert a["in_recrawl"] == in_re, \
        f"{arm} 重爬可见性与 phaseD_recrawl.urls 不符（{a['in_recrawl']} vs {in_re}）"
    assert a["readable"] == readable, \
        f"{arm} 可读性与 probes 不符（{a['readable']} vs {readable}）"
    assert a["repo_status"] == p["repo_status"] == 200, f"{arm} 仓库状态非 200"
    assert a["file_status"] == p["file_status"] == 200, f"{arm} 文件读取状态非 200"
    assert a["file_sha"] == p["file_sha"] and len(a["file_sha"]) >= 8, \
        f"{arm} 内容哈希与 probes 不符或过短"
    assert not in_snap, f"{arm} 在快照里可见，不能算快照后授予"

    # 报警 = 未枚举 ∧ 实际可读（主体对三对象均非所有者）
    assert a["alarm_snapshot"] == (not in_snap and readable), \
        f"{arm} 快照报警与原始记录不符"
    assert a["alarm_after_recrawl"] == (not in_re and readable), \
        f"{arm} 重爬后报警与原始记录不符"
    assert a["false_proof_snapshot"] == a["alarm_snapshot"], \
        f"{arm} 错误证明与报警不一致（三臂均为合法访问）"
    assert a["false_proof_after_recrawl"] == a["alarm_after_recrawl"], \
        f"{arm} 重爬后错误证明与报警不一致"
    assert a["repaired_by_recrawl"] == (a["alarm_snapshot"]
                                        and not a["alarm_after_recrawl"]), \
        f"{arm} 修复标记与两次报警不符"
    # 修复只能通过"重爬把对象列出来"发生，不能凭空消失
    if a["repaired_by_recrawl"]:
        assert in_re, f"{arm} 报修复但重爬 urls 里没有该对象"

# ---- 3. totals 由逐臂重算 ----
snap = sum(a["alarm_snapshot"] for a in arms)
after = sum(a["alarm_after_recrawl"] for a in arms)
repaired = sum(1 for a in arms if a["repaired_by_recrawl"])
assert data["totals"]["cells"] == len(arms), "totals.cells 与臂数不符"
assert data["totals"]["alarms_snapshot"] == snap, "totals.alarms_snapshot 与逐臂重算不符"
assert data["totals"]["alarms_after_recrawl"] == after, "totals.alarms_after_recrawl 与逐臂重算不符"
assert data["totals"]["repaired"] == repaired, "totals.repaired 与逐臂重算不符"
assert data["totals"]["persisting"] == after, "totals.persisting 与重爬后报警不符"

# ---- 4. 结论所依赖的两个方向必须成立 ----
by = {a["arm"]: a for a in arms}
assert by["S"]["repaired_by_recrawl"] and by["T"]["repaired_by_recrawl"], \
    "协作者/团队臂未被重爬修复，正文的'可枚举⇒可修'不成立"
assert not by["C"]["repaired_by_recrawl"], "公开臂被修好了，结论要重写"
assert by["C"]["object"] not in recrawl_urls, "公开臂对象出现在重爬结果里"
named = data["name_query"]["found"]
assert named, "按名字查询没找到公开库，边界句不成立"
assert by["C"]["object"] in named, "按名字查询命中的不是公开臂那个对象"
# 三臂的通道必须互不相同，否则"三通道并行"的说法不成立
assert len({a["channel"] for a in arms}) == len(arms), "两臂通道重复"

macros = {
    "RfArms": len(arms),
    "RfSnapAlarms": snap,
    "RfAfterAlarms": after,
    "RfRepaired": repaired,
    "RfPersisting": after,
    "RfNameFound": len(named),
    "RfCellsPublic": sum(1 for a in arms if a["channel"] == "public visibility"),
}
lines = ["% 由 ingest_r15_pair.py 生成，勿手改",
         "% 源: experiments/real_system/results/r15_pair.json"]
for k, v in macros.items():
    lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
out = RESULTS / "r15_pair_numbers.tex"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
print(f"\n[ok] {out}")
