"""把修订稿中相对初投稿版新增或改写的行加黄色高亮批注。

基线 = baseline/submitted_main.pdf（git 157edec，Access-2026-49387 初投稿版，
16 页旧标题）。脚本启动时校验其 SHA-256，不符即拒绝运行。

判定分两级，保守标记（宁可多标，不可漏标）：
  1. 归一化后与旧版某行完全一致            -> 未改
  2. 其余一律判为改写/新增                  -> 高亮
不做任何功能词/显著词过滤：插入 not、量词变化、<= 与 >= 互换这类"轻"
改动都要求被标出（增量复核反例：相似度 0.941、差异仅 {not}，旧逻辑漏标）。
归一化把 <=/>=/</>/= 保留为独立词元（le/ge/lt/gt/eq），运算符改动在
第一层就不会被抹掉。短行（<3 词元）只有完全一致才放行。

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

# 运算符必须作为独立词元存活到比较层，否则 x <= y 与 x >= y 归一化后相同，
# 运算符改动会在第一层被抹掉（增量复核反例）。
_OPS = [(r"<=", " le "), (r">=", " ge "), (r"<", " lt "), (r">", " gt "), (r"=", " eq "),
        (r"\u2264", " le "), (r"\u2265", " ge "), (r"\u2260", " ne ")]


def norm(s: str) -> str:
    s = s.replace("\u00ad", "")
    s = re.sub(r"-\s+", "", s)  # 连接断字
    for pat, rep in _OPS:
        s = re.sub(pat, rep, s)
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    return " ".join(s.lower().split())


def toks(s: str):
    return s.split()


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
            # 顺序与重复次数敏感的对比：旧分支按“词元集合相同”跳过，
            # 会漏掉角色对调、重复次数变化等改动——已删除。
            if nlist == old_lines[best_i].split():
                # 完全一致（含顺序与次数）——按未改处理，消耗旧行额度
                old_pool[old_lines[best_i]] -= 1
                used_old[old_lines[best_i]] += 1
                continue
            # 有任何词元差异（含顺序对调、重复、not、量词、运算符）→ 保守高亮，不做过滤

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
                # 存在足够相似的对应行 = 被改写而非被删除（改写已在新版高亮）
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
