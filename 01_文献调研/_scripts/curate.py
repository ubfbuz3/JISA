# -*- coding: utf-8 -*-
"""候选池加权筛选：venue 档次 + 年份 + 被引 + 主题命中度"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(BASE, "candidate_pool.json"), encoding="utf-8"))
items = data["items"]

# venue 分层（面向 JISA 定位：安全类期刊 ≈ 同级，顶会次之，软件工程类可借鉴）
TIER_A = [
    r"journal of information security and applications",
    r"computers\s*&\s*security",
    r"ieee transactions on information forensics and security",
    r"ieee transactions on dependable and secure computing",
    r"acm transactions on privacy and security",
    r"computers and security",
]
TIER_B = [
    r"empirical software engineering", r"information and software technology",
    r"journal of systems and software", r"automated software engineering",
    r"acm transactions on software engineering", r"ieee transactions on software engineering",
    r"cybersecurity", r"international journal of information security",
    r"security and communication networks", r"future generation computer systems",
    r"computer networks", r"computers and electrical engineering",
]
TIER_C = [  # 顶会
    r"usenix security", r"ndss", r"computer and communications security", r"\bccs\b",
    r"symposium on security and privacy", r"\bs&p\b", r"icse", r"fse", r"esec/fse",
    r"\base\b", r"issta", r"raid", r"dsn", r"acsac", r"esorics", r"asiaccs", r"dimva",
    r"world wide web", r"\bwww\b", r"network and distributed system security",
]

def tier(venue):
    v = (venue or "").lower()
    for p in TIER_A:
        if re.search(p, v): return 4
    for p in TIER_B:
        if re.search(p, v): return 3
    for p in TIER_C:
        if re.search(p, v): return 2
    if not v.strip(): return 0
    return 1

# 主题关键词：命中则加分（贴合"Web/API 安全与漏洞挖掘"）
TOPIC_KW = [
    "api", "rest", "graphql", "endpoint", "web application", "web service",
    "vulnerability", "exploit", "fuzz", "sql injection", "xss", "ssrf",
    "access control", "authorization", "authentication", "owasp",
    "code generation", "program analysis", "large language model", "llm",
    "static analysis", "symbolic execution", "taint",
]
def topic_score(it):
    blob = (it["title"] + " " + it["abstract"]).lower()
    return sum(1 for k in TOPIC_KW if k in blob)

rows = []
for it in items:
    t = tier(it["venue"])
    if t == 0:
        continue
    cites = it["citations"] or 0
    yr = it["year"] or 0
    # 综合分：venue档次权重最高，其次主题贴合度、被引、年份新鲜度
    score = (t * 100) + min(topic_score(it), 12) * 6 + min(cites, 120) * 0.6 + max(0, yr - 2021) * 4
    score += len(it["matched_queries"]) * 5
    rows.append((score, t, cites, yr, topic_score(it), it))

rows.sort(key=lambda x: -x[0])

print(f"有 venue 的候选：{len(rows)} / {len(items)}\n")
print("=" * 130)
for i, (s, t, c, y, ts, it) in enumerate(rows[:60], 1):
    print(f"{i:3d}. [{s:6.1f}] T{t} | {y} | cite={c:4d} | topic={ts:2d} | {(it['venue'] or '?')[:46]}")
    print(f"      {it['title'][:118]}")
    print(f"      DOI: {it['doi']}")

# 导出短名单
out = os.path.join(BASE, "shortlist.json")
json.dump([{**it, "_score": round(s, 1), "_tier": t, "_topic": ts}
           for s, t, c, y, ts, it in rows], open(out, "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\n短名单 -> {out}")
