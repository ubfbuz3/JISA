# -*- coding: utf-8 -*-
"""
Web/API 安全与漏洞挖掘 —— 文献调研候选池采集
数据源：OpenAlex（真实索引，无需 API key）
输出：候选池 JSON + Markdown 表格
"""
import json
import time
import urllib.parse
import urllib.request
import os

OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAILTO = "research@example.org"
BASE = "https://api.openalex.org/works"

# 绕过 http 代理（本地环境常见 http_proxy 干扰）
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

QUERIES = [
    ("web vulnerability detection deep learning", "Web漏洞检测-DL"),
    ("API security vulnerability detection", "API安全"),
    ("REST API fuzzing automated testing", "API模糊测试"),
    ("GraphQL API security vulnerability", "GraphQL安全"),
    ("large language model vulnerability detection code", "LLM辅助漏洞检测"),
    ("broken object level authorization access control API", "API越权/BOLA"),
    ("automated vulnerability discovery web application", "Web自动化漏洞发现"),
    ("static analysis vulnerability detection neural network", "静态分析+神经网络"),
    ("web application firewall evasion detection", "WAF绕过与检测"),
    ("vulnerability detection source code transformer", "代码Transformer漏洞检测"),
]

FIELDS = ",".join([
    "id", "doi", "title", "display_name", "publication_year", "publication_date",
    "primary_location", "cited_by_count", "authorships", "abstract_inverted_index",
    "type", "type_crossref", "concepts", "referenced_works_count", "is_retracted",
])


def reconstruct_abstract(inv_index):
    """OpenAlex 的摘要以倒排索引存储，还原成正常文本"""
    if not inv_index:
        return ""
    positions = []
    for word, idxs in inv_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def fetch(query, per_page=25, from_date="2022-01-01"):
    params = {
        "filter": f"title_and_abstract.search:{query},"
                  f"from_publication_date:{from_date},"
                  f"type:article",
        "per-page": str(per_page),
        "sort": "relevance_score:desc",
        "select": FIELDS,
        "mailto": MAILTO,
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "lit-survey/1.0"})
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    pool = {}
    log = []
    for query, label in QUERIES:
        try:
            data = fetch(query)
            n = 0
            for w in data.get("results", []):
                key = (w.get("doi") or w.get("id") or "").lower()
                if not key:
                    continue
                rec = {
                    "openalex_id": w.get("id"),
                    "doi": w.get("doi"),
                    "title": (w.get("title") or w.get("display_name") or "").strip(),
                    "year": w.get("publication_year"),
                    "date": w.get("publication_date"),
                    "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                    "venue_type": ((w.get("primary_location") or {}).get("source") or {}).get("type"),
                    "citations": w.get("cited_by_count"),
                    "type": w.get("type_crossref") or w.get("type"),
                    "authors": [a.get("author", {}).get("display_name")
                                for a in (w.get("authorships") or [])][:12],
                    "n_authors": len(w.get("authorships") or []),
                    "abstract": reconstruct_abstract(w.get("abstract_inverted_index"))[:2200],
                    "concepts": [c.get("display_name") for c in
                                 sorted(w.get("concepts") or [],
                                        key=lambda x: -(x.get("score") or 0))[:6]],
                    "retracted": w.get("is_retracted", False),
                    "matched_queries": [label],
                }
                if key in pool:
                    pool[key]["matched_queries"].append(label)
                else:
                    pool[key] = rec
                    n += 1
            log.append(f"  {label:24s} -> +{n} new (total {len(pool)})")
            print(log[-1])
        except Exception as e:
            msg = f"  {label:24s} -> ERROR {type(e).__name__}: {e}"
            log.append(msg)
            print(msg)
        time.sleep(1.2)

    items = list(pool.values())
    items = [i for i in items if not i["retracted"] and i["title"]]
    items.sort(key=lambda x: (len(x["matched_queries"]), x["citations"] or 0), reverse=True)

    raw_path = os.path.join(OUT_DIR, "_scripts", "candidate_pool.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"log": log, "count": len(items), "items": items},
                  f, ensure_ascii=False, indent=2)
    print(f"\n候选池总数: {len(items)}  ->  {raw_path}")

    # Markdown 概览
    md = ["# Web/API 安全与漏洞挖掘 · 候选文献池（OpenAlex）\n",
          f"检索日期：2026-09-17 ｜ 时间窗：2022-01-01 起 ｜ 类型：期刊/会议论文\n",
          f"候选总数：**{len(items)}**\n",
          "\n| # | 标题 | 年份 | 期刊/会议 | 被引 | 命中主题数 |",
          "|---|------|------|-----------|------|------------|"]
    for i, it in enumerate(items[:120], 1):
        t = it["title"].replace("|", "\\|")[:95]
        v = (it["venue"] or "-").replace("|", "\\|")[:38]
        md.append(f"| {i} | {t} | {it['year']} | {v} | {it['citations']} | {len(it['matched_queries'])} |")
    md_path = os.path.join(OUT_DIR, "_scripts", "candidate_pool.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"概览表 -> {md_path}")


if __name__ == "__main__":
    main()
