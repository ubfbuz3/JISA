"""把修订稿中相对初投稿版新增或改写的行加黄色高亮批注。

基线 = baseline/submitted_main.pdf（git 157edec，Access-2026-49387 初投稿版，
16 页旧标题）。脚本启动时校验其 SHA-256，不符即拒绝运行。

判定分三级，目的是不漏掉"轻微但实质"的改动：
  1. 归一化后与旧版某行完全一致            -> 未改
  2. 否则取最相似的旧行；若相似度 >= SIM 且差异只涉及非显著词元（功能词）-> 未改
  3. 其余一律判为改写/新增                  -> 高亮
显著词元 = 含数字的词元、长度 >= 4 的非功能词。单个数字、否定词、量词、
运算符、专有名词的变化因此都会被抓到。短行（<3 词元）只有完全一致才放行。

删除的句子无法在 PDF 里高亮，单独列在报告的 DELETED 段，供回复信点名。
"""
import difflib
import hashlib
import re
import sys
from collections import Counter, defaultdict

import pymupdf

BASE = r"C:/Users/Administrator/WorkBuddy/3区论文/03_论文撰写/response_to_reviewers"
NEW = r"C:/Users/Administrator/WorkBuddy/3区论文/03_论文撰写/paper/main.pdf"
OLD = BASE + r"/baseline/submitted_main.pdf"
OUT = BASE + r"/main_highlighted.pdf"
REPORT = BASE + r"/highlight_report.txt"

OLD_SHA256 = "d641e6dad6899658385f5eb8aac008069ee5ac83ef4233d29a554d780c3d440c"

SIM = 0.80

# 功能词表：不含否定词与量词，它们必须算显著差异。
STOP = set(
    """a an the of to in on for and or is are be been being by with that this these those
    we our us it its as at from into onto over under than then so such which who whom whose
    while when where whether both each few more most other some any all can could may might
    will would shall should do does did done have has had having i you your he she they them
    their his her there here also very just only about after before between during if
    """.split()
)


def norm(s: str) -> str:
    s = s.replace("\u00ad", "")
    s = re.sub(r"-\s+", "", s)  # 连接断字
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    return " ".join(s.lower().split())


def toks(s: str):
    return s.split()


def salient(tokens) -> bool:
    for t in tokens:
        if any(c.isdigit() for c in t):
            return True
        if len(t) >= 4 and t not in STOP:
            return True
    return False


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
    # --- 基线校验 ---
    digest = hashlib.sha256(open(OLD, "rb").read()).hexdigest()
    if digest != OLD_SHA256:
        print(f"[FATAL] baseline sha256 mismatch\n  want {OLD_SHA256}\n  got  {digest}")
        return 2

    old = pymupdf.open(OLD)
    new = pymupdf.open(NEW)

    old_raw = [t for _, t, _ in lines_of(old) if not is_header_footer(t)]
    old_lines = [norm(t) for t in old_raw]
    old_pool = Counter(old_lines)          # 旧版可用行（可消耗）
    old_tok = [set(l.split()) for l in old_lines]

    index = defaultdict(list)
    for i, ws in enumerate(old_tok):
        for w in ws:
            index[w].append(i)

    new_lines = lines_of(new)

    changed = 0
    skipped_short = 0
    per_page = defaultdict(int)
    report = []
    used_old = Counter()

    for pno, text, rect in new_lines:
        if is_header_footer(text):
            continue
        n = norm(text)
        short = len(n.split()) < 3
        if not n:
            continue

        # 1) 完全一致
        if n in old_pool:
            old_pool[n] -= 1
            used_old[n] += 1
            continue

        if short:
            # 短行没有完全对应即视为改动（表格单元、数字、标签）
            skipped_short += 1
            page = new[pno - 1]
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=(1, 1, 0))
            annot.set_opacity(0.55)
            annot.update()
            changed += 1
            per_page[pno] += 1
            report.append(f"p{pno}\t[short]\t{text.strip()[:110]}")
            continue

        # 2) 相似度 + 显著差异
        ws = set(n.split())
        cand = set()
        for w in ws:
            if len(index.get(w, ())) <= 400:
                cand.update(index.get(w, ()))
        nlist = n.split()
        best, best_i = 0.0, -1
        for i in cand:
            if abs(len(old_lines[i].split()) - len(nlist)) > 0.5 * len(nlist) + 4:
                continue
            r = difflib.SequenceMatcher(None, nlist, old_lines[i].split()).ratio()
            if r > best:
                best, best_i = r, i
                if best >= SIM:
                    break
        if best >= SIM and best_i >= 0:
            a = set(nlist)
            b = set(old_lines[best_i].split())
            diff = (a - b) | (b - a)
            if not salient(diff):
                old_pool[old_lines[best_i]] -= 1
                used_old[old_lines[best_i]] += 1
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

    # --- 删除的行：旧版中未在新版找到对应者的行 ---
    new_norm = [norm(t) for _, t, _ in new_lines if not is_header_footer(t)]
    new_set = set(new_norm)
    deleted = []
    for raw, n in zip(old_raw, old_lines):
        if not n or len(n.split()) < 3:
            continue
        if n in new_set:
            continue
        # 模糊兜底：新版里有没有高相似行
        ok = False
        for m in new_norm:
            if len(m.split()) < 3:
                continue
            if abs(len(m.split()) - len(n.split())) > 0.5 * len(n.split()) + 4:
                continue
            if difflib.SequenceMatcher(None, n.split(), m.split()).ratio() >= SIM:
                a, b = set(n.split()), set(m.split())
                if not salient((a - b) | (b - a)):
                    ok = True
                    break
        if not ok:
            deleted.append(raw.strip()[:160])

    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(f"baseline sha256 : {digest}\n")
        fh.write(f"baseline pages  : {len(old)} ; revised pages : {len(new)}\n")
        fh.write(f"changed lines   : {changed} (of which short lines: {skipped_short})\n")
        fh.write(f"deleted lines   : {len(deleted)}\n")
        for p in sorted(per_page):
            fh.write(f"page {p}: {per_page[p]}\n")
        fh.write("\n===== CHANGED =====\n")
        for line in report:
            fh.write(line + "\n")
        fh.write("\n===== DELETED (cannot be highlighted in the PDF) =====\n")
        for line in deleted:
            fh.write(line + "\n")

    print(f"highlighted {changed} lines over {len(per_page)} pages -> {OUT}")
    print(f"deleted lines: {len(deleted)} ; baseline {len(old)}p -> revised {len(new)}p")
    return 0


if __name__ == "__main__":
    sys.exit(main())
