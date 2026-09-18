# -*- coding: utf-8 -*-
"""
解析 _um_ds_results.json：
  - 拆出每路 deep search 的研究摘要
  - 抽出全部论文条目 (cite_key, relevance, title, year, 所属检索)
  - 与 final_selection.json 已有 15 篇去重
输出:
  _um_all_papers.json    全部条目
  _um_all_papers.md      人类可读清单
  _um_summaries.md       三路研究摘要
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)

raw = json.load(open(os.path.join(HERE, "_um_ds_results.json"), encoding="utf-8"))
txt = raw["content"][0]["text"]


def norm_title(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ---------- 1) 拆分段 ----------
# 分段以 "\n/<folder>/<name> (status:" 开头
parts = re.split(r"\n(?=/\d\d-)", "\n" + txt)
sections = []
for p in parts[1:]:
    m = re.match(r"/([^\n(]+)\s*\(status:\s*(\w+)", p)
    if not m:
        continue
    path = m.group(1).strip()
    body = p
    # 研究摘要
    sm = re.search(r"Summary of results.*?```\n(.*?)\n\s*```", body, re.S)
    summary = sm.group(1).strip() if sm else ""
    # 总条数
    tm = re.search(r"Relevant Papers \(showing \d+-\d+ of (\d+)\)", body)
    total = int(tm.group(1)) if tm else 0
    sections.append({"path": path, "summary": summary, "total_reported": total})

# ---------- 2) 抽论文条目 ----------
pat = re.compile(
    r"^\s*\[([A-Za-z][A-Za-z]*\d+[a-z]?)\]\s*r=([0-9.]+)\s*-\s*(.+?)\s*\((\d{4})\)\s*$",
    re.M,
)
# 需要知道每条属于哪一路：按分段位置切
papers = []
pos = 0
marks = []
cur = None
for line in txt.splitlines():
    hm = re.match(r"^(/\d\d-[^\n(]+)\s*\(status:", line)
    if hm:
        cur = hm.group(1).strip()
    pm = pat.match(line)
    if pm:
        papers.append({
            "cite_key": pm.group(1),
            "relevance": float(pm.group(2)),
            "title": pm.group(3).strip(),
            "year": int(pm.group(4)),
            "search": cur,
        })

# 去重（同一篇可能被多路命中）
by_key = {}
for p in papers:
    k = p["cite_key"]
    if k in by_key:
        if p["search"] not in by_key[k]["searches"]:
            by_key[k]["searches"].append(p["search"])
        by_key[k]["relevance"] = max(by_key[k]["relevance"], p["relevance"])
    else:
        p["searches"] = [p["search"]]
        by_key[k] = p

# ---------- 3) 与已有 15 篇去重 ----------
sel_path = os.path.join(HERE, "final_selection.json")
existing_titles = set()
existing_dois = set()
if os.path.exists(sel_path):
    sel = json.load(open(sel_path, encoding="utf-8"))
    for it in sel.get("core", []) + sel.get("reserve", []):
        existing_titles.add(norm_title(it.get("title")))
        d = (it.get("doi") or "").replace("https://doi.org/", "").lower()
        if d:
            existing_dois.add(d)

for p in by_key.values():
    p["already_in_zotero"] = norm_title(p["title"]) in existing_titles

uniq = sorted(by_key.values(), key=lambda x: (-x["relevance"], -x["year"]))

out = {
    "sections": sections,
    "total_unique": len(uniq),
    "papers": uniq,
}
json.dump(out, open(os.path.join(HERE, "_um_all_papers.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# ---------- 4) 人类可读 ----------
lines = ["# Undermind 三路深挖 · 候选池", ""]
for s in sections:
    lines.append("## %s" % s["path"])
    lines.append("- 检索报告命中总数：%d" % s["total_reported"])
    lines.append("")
lines.append("---")
lines.append("")
lines.append("## 去重后全部条目（按相关度排序）")
lines.append("")
lines.append("| # | cite_key | 相关度 | 年份 | 标题 | 命中检索 | 已在 Zotero |")
lines.append("|---|---|---|---|---|---|---|")
for i, p in enumerate(uniq, 1):
    lines.append("| %d | %s | %.2f | %d | %s | %s | %s |" % (
        i, p["cite_key"], p["relevance"], p["year"], p["title"],
        "; ".join(x.split("/")[1] if "/" in x else x for x in p["searches"]),
        "是" if p["already_in_zotero"] else ""))
open(os.path.join(HERE, "_um_all_papers.md"), "w", encoding="utf-8").write("\n".join(lines))

smd = ["# 三路深挖 · 研究摘要", ""]
for s in sections:
    smd += ["## %s" % s["path"], "", s["summary"], ""]
open(os.path.join(HERE, "_um_summaries.md"), "w", encoding="utf-8").write("\n".join(smd))

print("分段:", len(sections))
for s in sections:
    print("  %-40s 命中 %d" % (s["path"], s["total_reported"]))
print("\n抽取条目(原始):", len(papers), " 去重后:", len(uniq))
print("其中已在现有 15 篇内:", sum(1 for p in uniq if p["already_in_zotero"]))
print("\n新增候选 Top 40:")
n = 0
for p in uniq:
    if p["already_in_zotero"]:
        continue
    n += 1
    if n > 40:
        break
    print("  %-8s r=%-6.2f %d  %s" % (p["cite_key"], p["relevance"], p["year"], p["title"][:86]))
