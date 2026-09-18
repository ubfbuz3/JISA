# -*- coding: utf-8 -*-
"""从精选文献元数据生成 BibTeX（数据源 OpenAlex，字段真实可溯源）"""
import json
import os
import re
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sel = json.load(open(os.path.join(BASE, "_scripts", "final_selection.json"), encoding="utf-8"))

CONF_KW = ["symposium", "conference", "workshop", "usenix", "ndss", "ccs",
           "icse", "fse", "issta", "ase", "esorics", "acsac", "raid"]


def ascii_slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z]", "", s)


def make_key(it, used):
    a = ascii_slug(it["authors"][0].split()[-1]) if it["authors"] else "anon"
    w = re.findall(r"[A-Za-z]+", it["title"])
    w = ascii_slug(w[0]) if w else "paper"
    base = f"{a}{it['year']}{w}"
    k, i = base, ord("a")
    while k in used:
        k = base + chr(i); i += 1
    used.add(k)
    return k


used = set()
entries = []
for it in sel["core"]:
    doi = it["doi"].replace("https://doi.org/", "")
    venue = it.get("venue") or ""
    is_conf = any(k in venue.lower() for k in CONF_KW)
    authors = " and ".join(it["authors"]) if it["authors"] else "Anonymous"
    if it["n_authors"] > len(it["authors"]):
        authors += " and others"
    f = "inproceedings" if is_conf else "article"
    vfield = "booktitle" if is_conf else "journal"
    entries.append(
        f"@{f}{{{make_key(it, used)},\n"
        f"  author       = {{{authors}}},\n"
        f"  title        = {{{it['title']}}},\n"
        f"  {vfield} = {{{venue}}},\n"
        f"  year         = {{{it['year']}}},\n"
        f"  doi          = {{{doi}}},\n"
        f"  url          = {{{it['doi']}}},\n"
        f"  note         = {{OpenAlex cited-by: {it['citations']}; tag: {it['_tag']}}},\n"
        f"}}\n"
    )

cdir = os.path.join(BASE, "for_codex")
os.makedirs(cdir, exist_ok=True)
out = os.path.join(cdir, "references.bib")
open(out, "w", encoding="utf-8").write("\n".join(entries))
print(f"{len(entries)} 条 BibTeX -> {out}\n")
print("\n".join(entries[:2]))
