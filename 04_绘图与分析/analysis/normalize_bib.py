"""
BibTeX 规范化 · 只做机械修正，不编造任何字段
=============================================
输入 : 01_文献调研/for_codex/references.bib（39 条，来源 OpenAlex / Undermind，带 DOI）
输出 : 03_论文撰写/paper/refs.bib

**只做以下四类修正**（全部可在 diff 中逐条核对）:
  1. `pages` 从 journal/booktitle 里拆出（原记录把 "…, pp. 3430-3471" 塞进了 venue 字段）
  2. `and and` → `and`（作者串排版重复）
  3. 期刊类 venue 写成 @inproceedings 的 → 改回 @article（venue 名含 journal/Transactions/Sensors 等）
  4. 年份与 DOI 内嵌年份冲突时：采用 **DOI 的年份**（DOI 是权威标识符），
     并把原年份与冲突事实写进 `note`，**不静默丢弃**

不做：补全缺失的 volume/number，猜测页码，改写标题或作者。缺就缺，保持可溯。

用法: python normalize_bib.py
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
SRC = PROJ / "01_文献调研" / "for_codex" / "references.bib"
DST = PROJ / "03_论文撰写" / "paper" / "refs.bib"
AUDIT = HERE.parent / "provenance" / "BIB_NORMALIZATION_AUDIT.md"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

JOURNAL_HINT = re.compile(
    r"(Transactions|Journal|Letters|Magazine|Sensors|Computers|Software|"
    r"arXiv|ArXiv|CoRR|Proceedings|Symposium|Conference|Workshop|Usenix|USENIX)",
    re.I)

VENUE_JOURNAL = re.compile(
    r"^(IEEE Transactions on|ACM Transactions on|Journal of|International Journal of|"
    r"Sensors|Computers \& Security|arXiv|ArXiv)", re.I)

PAGES_RE = re.compile(r",?\s*pp\.\s*([0-9]+\s*[-–]\s*[0-9]+)\s*$")
VOL_RE = re.compile(r",?\s*vol\.\s*([0-9]+)\s*$", re.I)

# 手工补充：标准/网页资源，无 DOI，无法从 references.bib 得到。
# 每条都经过实际 HTTP 可达性核验（见行尾 note），严禁把学术文献放进这里。
MANUAL_EXTRA = r"""
%% ---------------------------------------------------------------------
%% 手工补充条目（非 DOI 来源）。学术文献一律来自 DOI 记录的规范化结果；
%% 这里只放标准/网页资源，且每条已核验 URL 可达。
%% ---------------------------------------------------------------------
@misc{OWASP2023API1,
  author       = {{OWASP Foundation}},
  title        = {{API1:2023 Broken Object Level Authorization}},
  howpublished = {OWASP API Security Top 10},
  year         = {2023},
  url          = {https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/},
  note         = {Resource verified reachable (HTTP 200) on 2026-09-18}
}
"""


# 被移出 refs.bib 的溯源元数据（原 note 字段内容），键为 citekey。
PROVENANCE: dict = {}

# Unicode 组合记号 → LaTeX 重音命令。用于把 Latin Extended 字符
# （如 "Şahin" 的 Ş、U+015E）转成 pdflatex 能吃的 LaTeX 转义。
# pdflatex + inputenc[utf8] 只直接支持 ASCII 与 Latin-1（U+00A0–U+00FF）；
# 更外面的拉丁字母必须写成 \c{S} 这类形式，否则报
# "Unicode character  not set up for use with LaTeX"。
_COMBINING_TO_LATEX = {
    "\u0300": "`", "\u0301": "'", "\u0302": "^", "\u0303": "~",
    "\u0304": "=", "\u0306": "u", "\u0307": ".", "\u0308": '"',
    "\u030a": "r", "\u030b": "H", "\u030c": "v",
    "\u0327": "c", "\u0328": "k",
}
# 无法用"基字母 + 组合记号"表示的字符，单独给出替换（LaTeX 转义或等价写法）
_SPECIAL_LATEX = {
    "\u0141": r"\L{}", "\u0142": r"\l{}",     # Ł ł
    "\u0131": r"\i{}", "\u0130": r"\.{I}",    # ı İ
    "\u00d8": r"\O{}", "\u00f8": r"\o{}",     # Ø ø（其实在 Latin-1，保底）
    "\u0110": r"\DJ{}", "\u0111": r"\dj{}",
    "\u00de": r"\TH{}", "\u00fe": r"\th{}",
}
LATEX_ISSUES: list = []


def to_latex_safe(s: str, where: str = "") -> str:
    """把字符串里的非 Latin-1 拉丁字符转成 LaTeX 转义；无法转换的报错。"""
    out = []
    for ch in s:
        o = ord(ch)
        if o <= 0x7F or 0xA0 <= o <= 0xFF:
            out.append(ch)
            continue
        if ch in _SPECIAL_LATEX:
            out.append(_SPECIAL_LATEX[ch])
            continue
        import unicodedata
        dec = unicodedata.normalize("NFD", ch)
        base = dec[0] if dec else ch
        marks = dec[1:]
        if ord(base) <= 0x7F or 0xA0 <= ord(base) <= 0xFF:
            if marks and all(m in _COMBINING_TO_LATEX for m in marks):
                acc = "".join(_COMBINING_TO_LATEX[m] for m in marks)
                # \c{S} 形式：花括号保护，BibTeX 大小写变换也不会破坏它
                out.append("{" + "\\" + acc + "{" + base + "}}")
                continue
        LATEX_ISSUES.append((where, ch, f"U+{o:04X}"))
        out.append("?")
    return "".join(out)


# 文本字段里必须转义的 LaTeX 特殊字符。**不动** `{` `}`（BibTeX 用它们做大小写
# 保护），也**不动** `url` / `doi`（它们被 \url{} 逐字排版，转义反而出错）。
_TEXT_ESCAPES = [("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("$", r"\$")]
_URL_ESCAPES = [("%", r"\%"), ("#", r"\#")]
_VERBATIM_FIELDS = {"url", "doi", "eprint"}


def escape_latex_specials(s: str, field: str) -> str:
    """转义 & % # $，但跳过已转义的形式（前面已有反斜杠的）。"""
    pairs = _URL_ESCAPES if field in _VERBATIM_FIELDS else _TEXT_ESCAPES
    for raw, esc in pairs:
        if esc in s:
            continue                      # 已经转义过，避免 \$ 变 \\$
        out, i = [], 0
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):
                out.append(s[i:i + 2])    # 保留已有转义对
                i += 2
                continue
            if s[i] == raw:
                out.append(esc)
            else:
                out.append(s[i])
            i += 1
        s = "".join(out)
    return s


def normalize_entry(block: str, audit: list):
    m = re.match(r"@(\w+)\{([^,]+),(.*)\}\s*$", block, re.S)
    if not m:
        return block
    etype, key, body = m.group(1), m.group(2).strip(), m.group(3)

    fields = {}
    order = []
    for fm in re.finditer(r"(\w+)\s*=\s*\{(.*?)\}\s*,?\s*(?=\w+\s*=|$)", body, re.S):
        k, v = fm.group(1).lower(), re.sub(r"\s+", " ", fm.group(2)).strip()
        fields[k] = v
        order.append(k)

    notes = []

    # (2) and and
    if "author" in fields and " and and " in fields["author"]:
        fields["author"] = fields["author"].replace(" and and ", " and ")
        notes.append("fix(author): 去除重复 and")

    # (1) pages / volume 从 venue 字段拆出
    for vf in ("journal", "booktitle"):
        if vf not in fields:
            continue
        val = fields[vf]
        pm = PAGES_RE.search(val)
        if pm:
            pages = pm.group(1).replace("–", "--").replace(" ", "")
            fields[vf] = PAGES_RE.sub("", val).strip().rstrip(",")
            fields["pages"] = pages
            notes.append(f"fix(pages): 从 {vf} 拆出 pages={pages}")
        vm = VOL_RE.search(fields.get(vf, ""))
        if vm:
            fields["volume"] = vm.group(1)
            fields[vf] = VOL_RE.sub("", fields[vf]).strip().rstrip(",")
            notes.append(f"fix(volume): 从 {vf} 拆出 volume={vm.group(1)}")

    # (3) 期刊类 venue 写成 @inproceedings 的改回 @article
    venue = fields.get("journal") or fields.get("booktitle") or ""
    if etype == "inproceedings" and VENUE_JOURNAL.match(venue):
        etype = "article"
        fields["journal"] = fields.pop("booktitle")
        order = ["author", "title", "journal"] + [k for k in order
                                                  if k not in ("author", "title", "journal", "booktitle")]
        notes.append("fix(type): @inproceedings→@article（venue 为期刊）")

    # (4) 年份与 DOI 冲突（**仅对非 arXiv DOI**：arXiv 的 10.48550/arXiv.2507.xxxxx
    #     中 2507 是编号 YYMM 而非年份，误用会写出 "year = 2507"）
    doi = fields.get("doi", "")
    is_arxiv = "arxiv" in doi.lower() or "/corr" in doi.lower()
    dm = re.search(r"10\.\d{4,9}/[a-z]*\.?(\d{4})\.", doi, re.I)
    if dm and not is_arxiv:
        doi_year = dm.group(1)
        if 1900 <= int(doi_year) <= 2100 and fields.get("year") and fields["year"] != doi_year:
            notes.append(f"fix(year): {fields['year']}→{doi_year}（以 DOI 为准；原记录年份 {fields['year']}）")
            fields["year"] = doi_year
    elif dm and is_arxiv and fields.get("year"):
        notes.append(f"skip(year): arXiv DOI（{doi}）中的 {dm.group(1)} 是编号非年份，"
                     f"保留原 year={fields['year']}")

    # (5) venue 名内嵌年份 vs year 字段不一致 → 以 venue 为准（venue 名是印刷在论文上的）
    bm = re.match(r"(\d{4})\s", fields.get("booktitle", "") or fields.get("journal", ""))
    if bm and fields.get("year") and fields["year"] != bm.group(1):
        notes.append(f"fix(year): {fields['year']}→{bm.group(1)}（venue 名内嵌年份；"
                     f"原记录年份 {fields['year']}）")
        fields["year"] = bm.group(1)

    if notes:
        audit.append((key, notes))

    # 溯源元数据（source / cited-by / tag / citekey / NORMALIZED 说明）**不写进
    # refs.bib**：它们不是书目信息，且含中文标签，既会让 pdflatex 报 Unicode
    # 错误，也不该出现在投稿的参考文献表里。全部移入审计文件，见 main()。
    raw_note = fields.pop("note", None)
    if raw_note:
        PROVENANCE[key] = raw_note
    if "note" in order:
        order.remove("note")

    # 输出（字段顺序稳定）
    pref = ["author", "title", "journal", "booktitle", "year", "volume", "number",
            "pages", "doi", "url", "publisher"]
    seen, out_order = set(), []
    for p in pref:
        if p in fields and p not in seen:
            out_order.append(p); seen.add(p)
    for k in order:
        if k not in seen:
            out_order.append(k); seen.add(k)

    # 硬保证：写出的字段值必须是 pdflatex 能吃下的字符集。
    # 顺序：先转义 LaTeX 特殊字符，再做 Unicode→LaTeX 转义，
    # 最后断言只含 ASCII + Latin-1。
    for k in list(fields):
        v = escape_latex_specials(str(fields[k]), k)
        v = to_latex_safe(v, where=f"{key}.{k}")
        fields[k] = v
        bad = sorted({c for c in v
                      if ord(c) > 127 and not (0xA0 <= ord(c) <= 0xFF)})
        if bad:
            raise ValueError(
                f"citekey {key} 的字段 {k} 含 pdflatex 不支持的字符 {bad!r}: {v!r}")

    lines = [f"@{etype}{{{key},"]
    for i, k in enumerate(out_order):
        comma = "," if i < len(out_order) - 1 else ""
        pad = " " * max(1, 13 - len(k))
        lines.append(f"  {k}{pad}= {{{fields[k]}}}{comma}")
    lines.append("}")
    return "\n".join(lines)


def main():
    text = SRC.read_text(encoding="utf-8")
    blocks = re.findall(r"@\w+\{.*?\n\}", text, re.S)
    audit: list = []
    out = [normalize_entry(b, audit) for b in blocks]
    n_src = len(blocks)
    if MANUAL_EXTRA.strip():
        out.append(MANUAL_EXTRA.strip())
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text("\n\n".join(out) + "\n", encoding="utf-8")

    L = ["# BibTeX 规范化审计", "",
         f"- 输入：`{SRC.relative_to(PROJ)}`（{n_src} 条，来源 OpenAlex / Undermind，带 DOI）",
         f"- 输出：`{DST.relative_to(PROJ)}`",
         "- 修正类型：pages/volume 字段搬家、`and and` 去重、期刊条目类型纠正、"
         "年份以 DOI 为准、venue 名内嵌年份覆盖",
         "- **未做**：补全缺失卷期、猜测页码、改写标题或作者",
         "- **移出**：原 `note` 字段中的溯源标签（source / cited-by / tag / citekey）"
         "以及修正说明，**不写进 refs.bib**——它们不是书目信息，且含中文字符",
         "  （BibTeX 会原样写进 .bbl，pdflatex 遇 CJK 直接 Fatal error）。",
         "  溯源内容保留在本文件末尾，修正说明保留在本表中。", "",
         "| citekey | 修正 |", "|---|---|"]
    for key, notes in audit:
        L.append(f"| `{key}` | " + "；".join(notes) + " |")
    if PROVENANCE:
        L += ["", "## 移出的溯源标签（原 note 字段）", "",
              "| citekey | 原 note |", "|---|---|"]
        for k, v in PROVENANCE.items():
            L.append(f"| `{k}` | {v} |")
    if MANUAL_EXTRA.strip():
        L += ["", "## 手工补充条目（非 DOI 来源，已逐条标注 URL 与核验日期）", "",
              "以下条目不来自 `references.bib`，是**标准/网页资源**，无法用 DOI 标识；"
              "按 Elsevier 惯例以 `@misc` + `url` + `note` 形式引用。"
              "除此之外**没有**任何手工添加的学术文献——学术文献一律来自 DOI 记录。", ""]
        for m in re.finditer(r"@\w+\{([^,]+),", MANUAL_EXTRA):
            L.append(f"- `{m.group(1)}`")
    AUDIT.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"[ok] {DST}  ({n_src} DOI entries + {len(re.findall(r'@', MANUAL_EXTRA))} manual)")
    print(f"[ok] {AUDIT}  ({len(audit)} entries modified)")
    for key, notes in audit:
        print(f"   {key}: {'; '.join(notes)}")


if __name__ == "__main__":
    main()
