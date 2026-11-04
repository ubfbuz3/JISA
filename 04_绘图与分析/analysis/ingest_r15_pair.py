"""R1.5 配对实验 → LaTeX 宏（正文只引宏，不手敲数字）。

输入：results/r15_pair.json（由 run_r15_pair.py 生成）
输出：results/r15_pair_numbers.tex

断言：
  * 三臂都在快照里不可见（否则不能算"快照后授予"）；
  * 每臂实际可读（repo 200 且 README 200 且有内容哈希）；
  * 重爬修复的臂，其对象必须出现在重爬 urls 里；未修复的臂必须不在；
  * 报警数 = 固定升格策略 P1 下的错误证明数（该主体对三个对象都有合法授权）。
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
assert len(arms) == 3, f"期望三臂，实得 {len(arms)}"
for a in arms:
    assert not a["in_snapshot_crawl"], f"{a['arm']} 在快照里可见，不能算快照后授予"
    assert a["readable"], f"{a['arm']} 实际不可读，臂不成立"
    assert a["file_sha"], f"{a['arm']} 读到空内容"
    assert a["in_recrawl"] == a["repaired_by_recrawl"] or True  # 语义见下
    if a["repaired_by_recrawl"]:
        assert a["in_recrawl"], f"{a['arm']} 说修好了但重爬没列出"
    else:
        assert not a["in_recrawl"], f"{a['arm']} 说没修好但重爬列出了"

snap = sum(a["alarm_snapshot"] for a in arms)
after = sum(a["alarm_after_recrawl"] for a in arms)
repaired = sum(a["repaired_by_recrawl"] for a in arms)
persist = after
assert data["totals"]["alarms_snapshot"] == snap
assert data["totals"]["alarms_after_recrawl"] == after

by = {a["arm"]: a for a in arms}
assert by["S"]["repaired_by_recrawl"] and by["T"]["repaired_by_recrawl"]
assert not by["C"]["repaired_by_recrawl"], "公开臂被修好了，结论要重写"
named = data["name_query"]["found"]
assert named, "按名字查询没找到公开库，边界句不成立"

macros = {
    "RfArms": len(arms),
    "RfSnapAlarms": snap,
    "RfAfterAlarms": after,
    "RfRepaired": repaired,
    "RfPersisting": persist,
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
