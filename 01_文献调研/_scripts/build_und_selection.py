# -*- coding: utf-8 -*-
"""
把 get_paper_info 的输出 _um_last.json 解析成与 final_selection.json 同构的
und_selection.json，供 zotero_import 复用。

输入文本格式:
  [Hua24] Title (2024)
  Venue
  Date: 2024-12-02
  By A, B, C - 15 citations - 8.4 cit./yr
  DOI: 10.1145/xxx
  PDF ✓

  <abstract 段落>
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

raw = json.load(open(os.path.join(HERE, "_um_last.json"), encoding="utf-8"))
txt = "".join(c.get("text", "") for c in raw.get("content", []) if c.get("type") == "text")

# tag 归类比（按 cite_key）
TAGS = {
    "Hua24": "API-越权", "Dha25": "API-越权", "Liu25b": "API-越权",
    "Liu25e": "API-越权", "Shi25": "API-越权", "Fen25": "API-越权",
    "Sch25": "API-越权", "Arc25": "API-模糊测试", "Che25c": "API-越权",
    "Zuo17": "经典-越权", "Ber20": "策略推断", "Zha24b": "策略推断",
    "Le21": "策略推断",
    "Cha22": "Oracle-理论", "Mai19": "Oracle-理论", "Atl19": "API-模糊测试",
    "Sun25b": "LLM-越权", "Wan24b": "LLM-越权", "Wen24": "LLM-规格",
    "Udd26": "LLM-越权", "Wan25d": "LLM-越权",
    "Wan26": "LLM-评测", "Lec25": "LLM-评测",
    "Cro23": "数据集-质量", "Li26g": "Agentic分析",
}

blocks = re.split(r"\n(?=\[[A-Za-z][A-Za-z]*\d+[a-z]?\]\s)", "\n" + txt)

# Arc25 (ICST 2025) 与已在 Zotero 的 Sah26 (JSS 2026) 是同一工作的会议版/期刊版，
# 期刊版更可引，去掉会议版避免同一工作入库两次。
SKIP = {"Arc25"}

recs = []
for b in blocks:
    b = b.strip()
    if not b.startswith("["):
        continue
    head = re.match(r"^\[([A-Za-z][A-Za-z]*\d+[a-z]?)\]\s+(.+?)\s*\((\d{4})\)\s*$", b.split("\n")[0])
    if not head:
        continue
    ck, title, year = head.group(1), head.group(2).strip(), int(head.group(3))
    if ck in SKIP:
        continue
    lines = b.split("\n")
    venue = lines[1].strip() if len(lines) > 1 else ""
    date = ""
    authors = []
    cites = 0
    doi = ""
    has_pdf = False
    for ln in lines[1:12]:
        ln = ln.strip()
        if ln.startswith("Date:"):
            date = ln[5:].strip()
        elif ln.startswith("By "):
            seg = re.sub(r"\s*-\s*[\d,]+\s*citations?.*$", "", ln[3:]).strip()
            seg = re.sub(r"\s*-\s*[\d.]+\s*cit\./yr$", "", seg).strip()
            seg = re.sub(r"\.\.\.\d+ more\.\.\.", "", seg)
            authors = [a.strip().rstrip(",") for a in seg.split(",") if a.strip()]
        elif ln.startswith("DOI:"):
            doi = ln[4:].strip()
        elif ln.startswith("PDF"):
            has_pdf = "✓" in ln
    m = re.search(r"-\s*([\d,]+)\s*citations?", b)
    if m:
        cites = int(m.group(1).replace(",", ""))
    # 摘要：第一个空行之后的全部
    body = b.split("\n\n", 1)
    abstract = body[1].strip() if len(body) > 1 else ""
    if abstract.lower().startswith("doi:'"):
        abstract = ""
    venue_l = venue.lower()
    is_conf = any(k in venue_l for k in [
        "conference", "symposium", "workshop", "usenix", "ndss", "ccs", "sp)",
        "icse", "fse", "issta", "ase", "esorics", "acsac", "raid", "arxiv",
        "proceedings",
    ])
    recs.append({
        "openalex_id": "",                      # Undermind 来源，无 OpenAlex ID
        "doi": ("https://doi.org/" + doi) if doi else "",
        "title": title,
        "year": year,
        "date": date,
        "venue": venue,
        "venue_type": "conference" if is_conf else "journal",
        "citations": cites,
        "type": "article",
        "authors": authors,
        "n_authors": len(authors),
        "abstract": abstract,
        "has_pdf": has_pdf,
        "cite_key": ck,
        "source": "undermind",
        "_tag": TAGS.get(ck, "其他"),
    })

out = {"core": recs, "reserve": []}
json.dump(out, open(os.path.join(HERE, "und_selection.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

print("解析到", len(recs), "篇")
for r in recs:
    print("  %-8s %d  pdf=%-5s cites=%-5d %-16s %s" % (
        r["cite_key"], r["year"], "Y" if r["has_pdf"] else "N", r["citations"],
        r["venue"][:16], r["title"][:66]))
missing = [r["cite_key"] for r in recs if not r["abstract"]]
print("\n缺摘要:", missing)
print("有 PDF:", sum(1 for r in recs if r["has_pdf"]), "/", len(recs))
