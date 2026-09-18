# -*- coding: utf-8 -*-
"""
合并 final_selection.json(OpenAlex 15 篇) + und_selection.json(Undermind 24 篇)，
生成给 Codex 用的材料：
  for_codex/zotero_snapshot.md   全量元数据 + 摘要
  for_codex/references.bib       BibTeX
  for_codex/_digest_inline.txt   精简版（编号 + cite_key，供内联进 prompt）
按 DOI / 归一化标题去重。
"""
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
CDIR = os.path.join(BASE, "for_codex")
os.makedirs(CDIR, exist_ok=True)


def norm_title(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_doi(d):
    d = (d or "").lower().strip()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d).strip()


def load(path):
    p = os.path.join(HERE, path)
    if not os.path.exists(p):
        return []
    return json.load(open(p, encoding="utf-8")).get("core", [])


merged, seen_doi, seen_title = [], set(), set()
for src, rows in (("OpenAlex", load("final_selection.json")),
                  ("Undermind", load("und_selection.json"))):
    for it in rows:
        it = dict(it)
        it.setdefault("cite_key", "")
        d, t = norm_doi(it.get("doi")), norm_title(it.get("title"))
        if (d and d in seen_doi) or (t and t in seen_title):
            continue
        if d:
            seen_doi.add(d)
        if t:
            seen_title.add(t)
        it["_src"] = src
        merged.append(it)

print("合并后:", len(merged), "篇  (OpenAlex %d + Undermind %d)" % (
    sum(1 for x in merged if x["_src"] == "OpenAlex"),
    sum(1 for x in merged if x["_src"] == "Undermind")))

# ---------- 1) snapshot.md ----------
L = ["# Zotero 集合快照：WebAPI安全与漏洞挖掘_JISA_2026",
     "",
     "来源：本地 Zotero 集合 `4VUU5LNB`。元数据来自 OpenAlex（真实索引，摘要经 Crossref/出版社页补齐）",
     "与 Undermind 深度检索（`mcp.undermind.ai`）。共 %d 篇。" % len(merged),
     ""]
for i, it in enumerate(merged, 1):
    L += ["## [%d] %s" % (i, it["title"]),
          "",
          "- **cite_key**: `%s`" % (it.get("cite_key") or "-"),
          "- **year**: %s | **venue**: %s" % (it.get("year"), it.get("venue") or "-"),
          "- **authors**: %s" % (", ".join(it.get("authors") or []) or "-"),
          "- **doi**: %s" % (it.get("doi") or "-"),
          "- **cited-by**: %s | **source**: %s | **tag**: %s" % (
              it.get("citations", 0), it["_src"], it.get("_tag", "-")),
          "- **pdf**: %s" % ("有" if it.get("has_pdf") else "-"),
          "",
          "> " + (it.get("abstract") or "(无摘要)").replace("\n", " "),
          ""]
open(os.path.join(CDIR, "zotero_snapshot.md"), "w", encoding="utf-8").write("\n".join(L))

# ---------- 2) references.bib ----------
CONF_KW = ["symposium", "conference", "workshop", "usenix", "ndss", "ccs", "icse",
           "fse", "issta", "ase", "esorics", "acsac", "raid", "arxiv",
           "proceedings", "annual meeting"]


def ascii_slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s)


def make_key(it, used):
    au = it.get("authors") or []
    a = ascii_slug(au[0].split()[-1]) if au else "anon"
    w = re.findall(r"[A-Za-z]+", it["title"] or "")
    w = ascii_slug(w[0]) if w else "paper"
    base = "%s%s%s" % (a, it.get("year"), w)
    k, i = base, ord("a")
    while k in used:
        k = base + chr(i)
        i += 1
    used.add(k)
    return k


used, entries = set(), []
for it in merged:
    doi = norm_doi(it.get("doi"))
    venue = it.get("venue") or ""
    is_conf = any(k in venue.lower() for k in CONF_KW)
    au = it.get("authors") or []
    authors = " and ".join(au) if au else "Anonymous"
    if it.get("n_authors", 0) > len(au):
        authors += " and others"
    f = "inproceedings" if is_conf else "article"
    vfield = "booktitle" if is_conf else "journal"
    entries.append(
        "@%s{%s,\n  author       = {%s},\n  title        = {%s},\n  %s = {%s},\n"
        "  year         = {%s},\n  doi          = {%s},\n  url          = {%s},\n"
        "  note         = {source: %s; cited-by: %s; tag: %s; citekey: %s},\n}\n" % (
            f, make_key(it, used), authors, it["title"], vfield, venue,
            it.get("year"), doi, it.get("doi") or "",
            it["_src"], it.get("citations", 0), it.get("_tag", "-"),
            it.get("cite_key") or "-"))
open(os.path.join(CDIR, "references.bib"), "w", encoding="utf-8").write("\n".join(entries))

# ---------- 3) digest（内联用，控制长度） ----------
D = []
for i, it in enumerate(merged, 1):
    ab = (it.get("abstract") or "(无摘要)").replace("\n", " ")
    if len(ab) > 1400:
        ab = ab[:1400] + " ...[truncated]"
    D.append("[%d] %s\n    cite_key=%s | venue=%s | year=%s | cites=%s | src=%s | tag=%s\n"
             "    doi=%s\n    abstract: %s" % (
                 i, it["title"], it.get("cite_key") or "-", it.get("venue") or "-",
                 it.get("year"), it.get("citations", 0), it["_src"],
                 it.get("_tag", "-"), it.get("doi") or "-", ab))
digest = "\n\n".join(D)
open(os.path.join(CDIR, "_digest_inline.txt"), "w", encoding="utf-8").write(digest)

print("snapshot.md / references.bib / _digest_inline.txt 已更新")
print("digest 长度:", len(digest), "字符")
