"""把修订稿中标出「相对原始投稿版新增或改写的行」，加黄色高亮批注。

基线 = git 89f3f96（Access-2026-49387 原始投稿版）的 main.pdf。
判定：行的归一化词序列在旧版中找不到高相似匹配（>=0.80）即视为改动。
删除的句子无法在 PDF 里高亮，只在报告里计数。
"""
import re
import sys
import difflib
from collections import defaultdict

import pymupdf

NEW = r"C:/Users/Administrator/WorkBuddy/3区论文/03_论文撰写/paper/main.pdf"
OLD = r"C:/Users/Administrator/WorkBuddy/rl_build/submitted.pdf"
OUT = r"C:/Users/Administrator/WorkBuddy/3区论文/03_论文撰写/response_to_reviewers/main_highlighted.pdf"
REPORT = r"C:/Users/Administrator/WorkBuddy/rl_build/highlight_report.txt"

SIM = 0.80


def norm(s: str) -> str:
    s = s.replace("\u00ad", "")
    s = re.sub(r"-\s+", "", s)          # 连接断字
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    return " ".join(s.lower().split())


def lines_of(doc):
    """返回 [(page_no, text, rect)]，一行一条。"""
    out = []
    for pno, page in enumerate(doc, 1):
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = "".join(sp.get("text", "") for sp in spans)
                if not text.strip():
                    continue
                r = pymupdf.Rect(spans[0]["bbox"])
                for sp in spans[1:]:
                    r |= pymupdf.Rect(sp["bbox"])
                out.append((pno, text, r))
    return out


def is_header_footer(text: str) -> bool:
    t = text.strip()
    return bool(
        re.fullmatch(r"VOLUME \d+, \d{4}", t)
        or re.fullmatch(r"\d{1,3}", t)
        or t in ("IEEE Access",)
        or t.startswith("Lin and Chen: ")
        or t.startswith("Digital Object Identifier")
    )


def main() -> int:
    old = pymupdf.open(OLD)
    new = pymupdf.open(NEW)

    old_lines = [norm(t) for _, t, _ in lines_of(old)]
    old_words = [set(l.split()) for l in old_lines]
    old_blob = " " + " ".join(old_lines) + " "

    # 词 -> 旧行索引，用于候选筛选
    index = defaultdict(list)
    for i, ws in enumerate(old_words):
        for w in ws:
            index[w].append(i)

    changed = 0
    skipped_short = 0
    per_page = defaultdict(int)
    report = []

    for pno, text, rect in lines_of(new):
        if is_header_footer(text):
            skipped_short += 1
            continue
        n = norm(text)
        if len(n) < 12 or len(n.split()) < 3:
            skipped_short += 1
            continue
        if f" {n} " in old_blob:
            continue
        ws = set(n.split())
        cand = set()
        for w in ws:
            if len(index.get(w, ())) <= 400:
                cand.update(index.get(w, ()))
        best = 0.0
        nlist = n.split()
        for i in cand:
            if abs(len(old_lines[i].split()) - len(nlist)) > 0.5 * len(nlist) + 4:
                continue
            r = difflib.SequenceMatcher(None, nlist, old_lines[i].split()).ratio()
            if r > best:
                best = r
                if best >= SIM:
                    break
        if best >= SIM:
            continue
        page = new[pno - 1]
        annot = page.add_highlight_annot(rect)
        annot.set_colors(stroke=(1, 1, 0))
        annot.set_opacity(0.55)
        annot.update()
        changed += 1
        per_page[pno] += 1
        report.append(f"p{pno}\t{text.strip()[:110]}")

    new.save(OUT, garbage=3, deflate=True)

    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(f"changed lines: {changed}\n")
        fh.write(f"skipped short lines: {skipped_short}\n")
        for p in sorted(per_page):
            fh.write(f"page {p}: {per_page[p]}\n")
        fh.write("\n")
        for line in report:
            fh.write(line + "\n")

    print(f"highlighted {changed} lines over {len(per_page)} pages -> {OUT}")
    print(f"old pages {len(old)} ; new pages {len(new)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
